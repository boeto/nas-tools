import re
from typing import Any, Dict, Optional
import xml.dom.minidom
from datetime import datetime, timedelta
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from jinja2 import Template

from app.helper import RssHelper
from app.media import Media
from app.mediaserver import MediaServer
from app.plugins.modules._base import _IPluginModule
from app.subscribe import Subscribe
from app.utils import RequestUtils, DomUtils
from app.utils.types import MediaType, SearchType, RssType
from config import Config
from web.backend.web_utils import WebUtils


class DoubanRank(_IPluginModule):
    _plugin_name = "doubanrank"

    # 插件名称
    module_name = "豆瓣榜单订阅"
    # 插件描述
    module_desc = "监控豆瓣热门榜单，自动添加订阅。"
    # 插件图标
    module_icon = "movie.jpg"
    # 主题色
    module_color = "#01B3E3"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = f"{_plugin_name}_"
    # 加载顺序
    module_order = 16
    # 可使用的用户级别
    auth_level = 2

    # 退出事件
    _event = Event()
    # 私有属性
    mediaserver = None
    subscribe = None
    rsshelper = None
    media = None

    _douban_address = {
        "movie-ustop": "https://rsshub.app/douban/movie/ustop",
        "movie-weekly": "https://rsshub.app/douban/movie/weekly",
        "movie-real-time": (
            "https://rsshub.app/douban/movie/weekly/subject_real_time_hotest"
        ),
        "show-domestic": (
            "https://rsshub.app/douban/movie/weekly/show_domestic"
        ),
        "movie-hot-gaia": (
            "https://rsshub.app/douban/movie/weekly/movie_hot_gaia"
        ),
        "tv-hot": "https://rsshub.app/douban/movie/weekly/tv_hot",
        "tv_global_best_weekly": (
            "https://rsshub.app/douban/movie/weekly/tv_global_best_weekly"
        ),
        "movie-top250": "https://rsshub.app/douban/movie/weekly/movie_top250",
    }
    _enable = False
    _onlyonce = False
    _is_seasons_all = True
    _is_delete_history_all = False
    _cron = ""
    _rss_addrs: list[str] = []
    _ranks: list[str] = []
    _vote = 0.0
    _scheduler = None

    def init_config(self, config: Optional[Dict[str, Any]] = None):
        self.mediaserver = MediaServer()
        self.subscribe = Subscribe()
        self.rsshelper = RssHelper()
        self.media = Media()
        if config:
            self._enable = config.get("enable", False)
            self._onlyonce = config.get("onlyonce", False)

            self._is_seasons_all = config.get("is_seasons_all", True)
            self._is_delete_history_all = config.get(
                "is_delete_history_all", False
            )

            self._cron = config.get("cron", str)
            self._vote = (
                float(config.get("vote", 3.14)) if config.get("vote") else 0.0
            )
            rss_addrs = config.get("rss_addrs")
            if rss_addrs:
                if isinstance(rss_addrs, str):
                    self._rss_addrs = rss_addrs.split("\n")
                else:
                    self._rss_addrs = rss_addrs
            else:
                self._rss_addrs = []
            self._ranks = config.get("ranks") or []

            self.info(f"DoubanRank config: {config}")

        # 停止现有任务
        self.stop_service()

        # 启动服务
        if self.get_state() or self._onlyonce or self._is_delete_history_all:
            self._scheduler = BackgroundScheduler(
                timezone=Config().get_timezone()
            )

            if self._scheduler:
                __tz = Config().get_timezone()
                if __tz:
                    time_now = datetime.now(tz=pytz.timezone(__tz))
                else:
                    time_now = datetime.now()

                if self._cron:
                    self.info(f"订阅服务启动，周期：{self._cron}")
                    self._scheduler.add_job(
                        self.refresh_rss, CronTrigger.from_crontab(self._cron)
                    )

                # 删除全部订阅历史和缓存记录
                if self._is_delete_history_all:
                    self._scheduler.add_job(
                        func=self.delete_rank_history_all,
                        args="",
                        trigger="date",
                        run_date=time_now + timedelta(seconds=3),
                    )

                    # 关闭删除开关
                    self._is_delete_history_all = False
                    self.update_config(
                        {
                            "enable": self._enable,
                            "is_seasons_all": self._is_seasons_all,
                            "is_delete_history_all": False,
                            "onlyonce": self._onlyonce,
                            "cron": self._cron,
                            "ranks": self._ranks,
                            "vote": self._vote,
                            "rss_addrs": "\n".join(self._rss_addrs),
                        }
                    )

                if self._onlyonce:
                    self.info("订阅服务启动，立即运行一次")
                    self._scheduler.add_job(
                        self.refresh_rss,
                        "date",
                        run_date=time_now + timedelta(seconds=3),
                    )
                    # 关闭一次性开关
                    self._onlyonce = False
                    self.update_config(
                        {
                            "enable": self._enable,
                            "is_seasons_all": self._is_seasons_all,
                            "is_delete_history_all": (
                                self._is_delete_history_all
                            ),
                            "onlyonce": False,
                            "cron": self._cron,
                            "ranks": self._ranks,
                            "vote": self._vote,
                            "rss_addrs": "\n".join(self._rss_addrs),
                        }
                    )
                if self._scheduler.get_jobs():
                    # 启动服务
                    self._scheduler.print_jobs()
                    self._scheduler.start()
            else:
                self.error(
                    f"订阅服务启动失败:self._scheduler={self._scheduler}"
                )

    def get_state(self):
        return self._enable and self._cron and (self._ranks or self._rss_addrs)

    @staticmethod
    def get_fields():
        return [
            # 同一板块
            {
                "type": "div",
                "content": [
                    # 同一行
                    [
                        {
                            "title": "开启豆瓣榜单订阅",
                            "required": "",
                            "tooltip": (
                                "开启后，自动监控豆瓣榜单变化，"
                                "有新内容时如媒体服务器不存在且未订阅过，"
                                "则会添加订阅，仅支持rsshub的豆瓣RSS"
                            ),
                            "type": "switch",
                            "id": "enable",
                        },
                        {
                            "title": "立即运行一次",
                            "required": "",
                            "tooltip": (
                                "打开后立即运行一次（点击此对话框的确定按钮后即会运行，"
                                "周期未设置也会运行），"
                                "关闭后将仅按照刮削周期运行（同时上次触发运行的任务如果在运行中也会停止）"
                            ),
                            "type": "switch",
                            "id": "onlyonce",
                        },
                    ],
                    [
                        {
                            "title": "订阅剧集全季度",
                            "required": "",
                            "tooltip": "开启后，订阅剧集时会订阅全季度",
                            "type": "switch",
                            "id": "is_seasons_all",
                        },
                        {
                            "title": "立即删除全部订阅历史和缓存记录",
                            "required": "",
                            "tooltip": "开启后立即删除全部豆瓣的订阅历史和缓存记录，所有订阅将重新解析。",
                            "type": "switch",
                            "id": "is_delete_history_all",
                        },
                    ],
                    [
                        {
                            "title": "刷新周期",
                            "required": "required",
                            "tooltip": (
                                "榜单数据刷新的时间周期，"
                                "支持5位cron表达式；应根据榜单更新的周期合理设置刷新时间，"
                                "避免刷新过于频繁"
                            ),
                            "type": "text",
                            "content": [
                                {
                                    "id": "cron",
                                    "placeholder": "0 0 0 ? *",
                                }
                            ],
                        },
                        {
                            "title": "评分",
                            "required": "",
                            "tooltip": "大于该评分的才会被订阅（以TMDB评分为准），不填则不限制",
                            "type": "text",
                            "content": [
                                {
                                    "id": "vote",
                                    "placeholder": "0.0",
                                }
                            ],
                        },
                    ],
                    [
                        {
                            "title": "RssHub订阅地址",
                            "required": "",
                            "tooltip": (
                                "每一行一个RSS地址，访问"
                                " https://docs.rsshub.app/social-media.html#dou-ban"
                                " 查询可用地址"
                            ),
                            "type": "textarea",
                            "content": {
                                "id": "rss_addrs",
                                "placeholder": "https://rsshub.app/douban/movie/classification/:sort?/:score?/:tags?",
                                "rows": 5,
                            },
                        }
                    ],
                ],
            },
            {
                "type": "details",
                "summary": "热门榜单",
                "tooltip": (
                    "内建支持的豆瓣榜单，使用https://rsshub.app数据源，可直接选择订阅"
                ),
                "content": [
                    # 同一行
                    [
                        {
                            "id": "ranks",
                            "type": "form-selectgroup",
                            "content": {
                                "movie-ustop": {
                                    "id": "movie-ustop",
                                    "name": "北美电影票房榜",
                                },
                                "movie-weekly": {
                                    "id": "movie-weekly",
                                    "name": "一周电影口碑榜",
                                },
                                "movie-real-time": {
                                    "id": "movie-real-time",
                                    "name": "实时热门榜",
                                },
                                "movie-hot-gaia": {
                                    "id": "movie-hot-gaia",
                                    "name": "热门电影",
                                },
                                "movie-top250": {
                                    "id": "movie-top250",
                                    "name": "电影TOP10",
                                },
                                "tv-hot": {
                                    "id": "tv-hot",
                                    "name": "热门剧集",
                                },
                                "tv_global_best_weekly": {
                                    "id": "tv_global_best_weekly",
                                    "name": "全球热门剧集",
                                },
                                "show-domestic": {
                                    "id": "show-domestic",
                                    "name": "热门综艺",
                                },
                            },
                        },
                    ]
                ],
            },
        ]

    def get_page(self):
        """
        插件的额外页面，返回页面标题和页面内容
        :return: 标题，页面内容，确定按钮响应函数
        """
        results = self.get_history() or []
        template = """
<div class="table-responsive table-modal-body">
  <table class="table table-vcenter card-table table-hover table-striped">
    <thead>
      <tr>
        <th></th>
        <th>标题</th>
        <th>类型</th>
        <th>状态</th>
        <th>添加时间</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {% if HistoryCount > 0 %} {% for Item in DoubanRankHistory %}
      <tr id="movie_rank_history_{{ Item.id }}">
        <td class="w-5">
          <img
            class="rounded w-5"
            src="{{ Item.image }}"
            onerror="this.src='../static/img/no-image.png'"
            alt=""
            style="min-width: 50px"
          />
        </td>
        <td>
          <div>{{ Item.name }} ({{ Item.year }})</div>
          {% if Item.rating %}
          <div class="text-muted text-nowrap">评份：{{ Item.rating }}</div>
          {% endif %}
        </td>
        <td>{{ Item.type }}</td>
        <td>
          {% if Item.state == 'DOWNLOADED' %}
          <span class="badge bg-green">已下载</span>
          {% elif Item.state == 'RSS' %}
          <span class="badge bg-blue">已订阅</span>
          {% elif Item.state == 'NEW' %}
          <span class="badge bg-blue">新增</span>
          {% else %}
          <span class="badge bg-orange">处理中</span>
          {% endif %}
        </td>
        <td>
          <small>{{ Item.add_time or '' }}</small>
        </td>
        <td>
          <div class="dropdown">
            <a
              href="#"
              class="btn-action"
              data-bs-toggle="dropdown"
              aria-expanded="false"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="icon icon-tabler icon-tabler-dots-vertical {{ class }}"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                stroke-width="2"
                stroke="currentColor"
                fill="none"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <circle cx="12" cy="12" r="1"></circle>
                <circle cx="12" cy="19" r="1"></circle>
                <circle cx="12" cy="5" r="1"></circle>
              </svg>
            </a>
            <div class="dropdown-menu dropdown-menu-end">
              <a
                class="dropdown-item text-danger"
                href='javascript:DoubanRank_delete_history("{{ Item.id }}", "{{ Item.name }}", "{{ Item.year }}", "{{ Item.douban_id }}", "{{ Item.douban_title }}")'
              >
                删除
              </a>
            </div>
          </div>
        </td>
      </tr>
      {% endfor %} {% else %}
      <tr>
        <td colspan="6" align="center">没有数据</td>
      </tr>
      {% endif %}
    </tbody>
  </table>
</div>
"""  # noqa E501
        return (
            "订阅历史",
            Template(template).render(
                HistoryCount=len(results), DoubanRankHistory=results
            ),
            None,
        )

    @staticmethod
    def get_script():
        """
        删除删除豆瓣的订阅历史和订阅处理记录的JS脚本
        """
        return """
function DoubanRank_delete_history(id, name, year, douban_id, douban_title) {
ajax_post(
    "run_plugin_method",
    {
    plugin_id: "DoubanRank",
    method: "delete_rank_history",
    tmdb_id: id,
    title: name,
    year: year,
    douban_id: douban_id,
    douban_title: douban_title,
    },
    function (ret) {
    $("#movie_rank_history_" + id).remove();
    }
);
}
"""  # noqa E501

    def set_unique_flag(self, douban_title: str, douban_id) -> str:
        """
        返回唯一标识
        """
        return f"{self._plugin_name}: {douban_title} (DB:{douban_id})"

    def delete_rank_history_all(
        self,
    ):
        """
        删除全部订阅历史和缓存记录
        """
        self.info("删除全部豆瓣订阅历史")
        self.delete_history(is_delete_all=True)

        self.info("删除全部豆瓣缓存记录")
        if self.rsshelper:
            self.rsshelper.simple_delete_rss_torrents(
                title=f"{self._plugin_name}",
                enclosure=None,
                contains=True,
            )
        self.info("已删除全部订阅历史和缓存记录")

    def delete_rank_history(
        self, tmdb_id, title, year, douban_id=None, douban_title=None
    ):
        """
        删除豆瓣的订阅历史和缓存记录
        """
        self.debug(
            (
                f"删除的影片信息: tmdb_id={tmdb_id}, title={title},"
                f" year={year}, douban_id={douban_id},"
                f" douban_title={douban_title}"
            ),
        )
        self.info(f"删除 {title} ({year}) 的豆瓣订阅历史...")
        self.delete_history(key=tmdb_id)

        if douban_title:
            self.info(f"删除 {title} ({year}) 的豆瓣缓存记录...")
            if self.rsshelper:
                unique_flag_name = self.set_unique_flag(
                    douban_title, douban_id
                )
                self.rsshelper.simple_delete_rss_torrents(
                    title=unique_flag_name, enclosure=None
                )
        else:
            self.debug("没有记录豆瓣订阅原标题，跳过删除缓存记录")

        self.info(f"已删除: {title} ({year}) 的订阅历史和缓存记录")

    def __update_history(
        self,
        douban_title: str,
        media_info,
        state,
    ):
        """
        插入历史记录
        """
        if not media_info:
            return
        value = {
            "id": media_info.tmdb_id,
            "douban_id": media_info.douban_id,
            "douban_title": douban_title,
            "name": media_info.title,
            "year": media_info.year,
            "type": media_info.type.value,
            "rating": media_info.vote_average or 0,
            "image": media_info.get_poster_image(),
            "state": state,
            "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if self.get_history(key=media_info.tmdb_id):
            self.update_history(key=media_info.tmdb_id, value=value)
        else:
            self.history(key=media_info.tmdb_id, value=value)

    def stop_service(self):
        """
        停止服务
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._event.set()
                    self._scheduler.shutdown()
                    self._event.clear()
                self._scheduler = None
        except Exception as e:
            print(str(e))

    def refresh_rss(self):
        """
        刷新RSS
        """
        self.info("开始刷新RSS ...")
        addr_list = self._rss_addrs + [
            self._douban_address.get(rank) for rank in self._ranks
        ]
        if not addr_list:
            self.info("未设置RSS地址")
            return
        else:
            self.info(f"共 {len(addr_list)} 个RSS地址需要刷新")
        for addr in addr_list:
            if not addr:
                continue
            try:
                self.info(f"获取RSS：{addr} ...")
                rss_infos = self.get_rss_info(addr)
                if not rss_infos:
                    self.error(f"RSS地址：{addr} ，未查询到数据")
                    continue
                else:
                    self.info(f"RSS地址：{addr} ，共 {len(rss_infos)} 条数据")

                for rss_info in rss_infos:
                    if self._event.is_set():
                        self.info("订阅服务停止")
                        return

                    douban_title = rss_info.get("title")
                    douban_id = rss_info.get("doubanid")
                    mtype = rss_info.get("type")
                    unique_flag_name = self.set_unique_flag(
                        douban_title, douban_id
                    )

                    # 检查是否已处理过
                    if self.rsshelper:
                        if self.rsshelper.is_rssd_by_simple(
                            torrent_name=unique_flag_name, enclosure=None
                        ):
                            self.info(
                                f"已处理过：{douban_title} （豆瓣id：{douban_id}）"
                            )
                            continue

                    media_info = None

                    # 识别媒体信息
                    if douban_id:
                        media_info = WebUtils.get_mediainfo_from_id(
                            mtype=mtype, mediaid=f"DB:{douban_id}", wait=True
                        )
                    else:
                        if self.media:
                            media_info = self.media.get_media_info(
                                title=douban_title, mtype=mtype
                            )

                    if not media_info:
                        self.warn(
                            f"未查询到媒体信息：{douban_title} （豆瓣id：{douban_id}）"
                        )
                        continue

                    if (
                        self._vote
                        and media_info.vote_average
                        and media_info.vote_average < self._vote
                    ):
                        self.info(
                            f"{media_info.get_title_string()} 评分"
                            f" {media_info.vote_average} 低于限制"
                            f" {self._vote}，跳过 ．．．"
                        )
                        continue

                    # 如果是剧集且开启全季订阅，则轮流下载每一季
                    if media_info.tmdb_info:
                        if (
                            media_info.tmdb_info["media_type"] == MediaType.TV
                        ) and self._is_seasons_all:
                            seasons = Media().get_tmdb_tv_seasons(
                                media_info.tmdb_info
                            )
                            for season in seasons:
                                media_info.begin_season = season.get(
                                    "season_number"
                                )
                                self.add_rss(media_info, douban_title)
                    else:
                        self.add_rss(media_info, douban_title)

                    # RSS_TORRENTS 添加处理历史
                    if self.rsshelper:
                        self.rsshelper.simple_insert_rss_torrents(
                            title=unique_flag_name, enclosure=None
                        )

            except Exception as e:
                self.error(f"RSS刷新错误: {str(e)}")
        self.info("所有RSS刷新完成")

    def get_rss_info(self, addr):
        """
        获取RSS
        """
        try:
            ret = RequestUtils().get_res(addr)
            if not ret:
                return []
            ret.encoding = ret.apparent_encoding
            ret_xml = ret.text
            ret_array = []
            # 解析XML
            dom_tree = xml.dom.minidom.parseString(ret_xml)
            rootNode = dom_tree.documentElement
            items = rootNode.getElementsByTagName("item")
            for item in items:
                try:
                    # 标题
                    title = DomUtils.tag_value(item, "title", default="")
                    # 链接
                    link = DomUtils.tag_value(item, "link", default="")
                    if not title and not link:
                        self.warn("条目标题和链接均为空，无法处理")
                        continue
                    doubanid = re.findall(r"/(\d+)/", link)
                    if doubanid:
                        doubanid = doubanid[0]
                    if doubanid and not str(doubanid).isdigit():
                        self.warn(f"解析的豆瓣ID格式不正确：{doubanid}")
                        continue
                    # 返回对象
                    ret_array.append(
                        {"title": title, "link": link, "doubanid": doubanid}
                    )
                except Exception as e1:
                    self.error("解析RSS条目失败：" + str(e1))
                    continue
            return ret_array
        except Exception as e:
            self.error("获取RSS失败：" + str(e))
            return []

    # 检查并添加订阅
    def add_rss(self, media_info, douban_title: str):
        # 检查媒体服务器是否存在
        if self.mediaserver:
            item_id = self.mediaserver.check_item_exists(
                mtype=media_info.type,
                title=media_info.title,
                year=media_info.year,
                tmdbid=media_info.tmdb_id,
                season=media_info.get_season_seq(),
            )

            if item_id:  # type: ignore
                self.info(f"媒体服务器已存在：{media_info.get_title_string()}")
                self.__update_history(
                    douban_title,
                    media_info=media_info,
                    state="DOWNLOADED",
                )
                return

        # 检查是否已订阅过
        if self.subscribe:
            if self.subscribe.check_history(
                type_str="MOV" if media_info.type == MediaType.MOVIE else "TV",
                name=media_info.title,
                year=media_info.year,
                season=media_info.get_season_string(),
            ):
                self.info(
                    f"{media_info.get_title_string()}{media_info.get_season_string()} 已订阅过"
                )
                self.__update_history(
                    douban_title, media_info=media_info, state="RSS"
                )
                return

        if self.subscribe:
            # 添加订阅
            code, msg, rss_media = self.subscribe.add_rss_subscribe(
                mtype=media_info.type,
                name=media_info.title,
                year=media_info.year,
                season=media_info.begin_season,
                channel=RssType.Auto,
                in_from=SearchType.PLUGIN,
            )
            if not rss_media or code != 0:
                self.warn(
                    f"{media_info.get_title_string()} {media_info.get_season_string()} "
                    f" 添加订阅失败: {msg}"
                )

                # 订阅已存在
                if code == 9:
                    self.__update_history(
                        douban_title, media_info=media_info, state="RSS"
                    )
            else:
                self.info(
                    f"{media_info.get_title_string()} {media_info.get_season_string()} 添加订阅成功"
                )
                self.__update_history(
                    douban_title,
                    media_info=media_info,
                    state="RSS",
                )
