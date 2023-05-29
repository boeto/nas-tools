from pathlib import Path
from app.plugins.modules.doubanrank import DoubanRank
from app.utils.types import MediaType
from web.backend.web_utils import WebUtils
from app.media import Media

doubanRank = DoubanRank()

current_dir = Path(__file__).resolve().parent

config = {
    "enable": True,
    "onlyonce": False,
    "is_seasons_all": True,
    "is_delete_history_all": False,
    "cron": "1 1 * * *",
    "vote": "0.0",
    "rss_addrs": [],
    "ranks": ["tv_global_best_weekly"],
}


class _TestDoubanRank:
    def _test_media_info(self):
        addr = "https://rsshub.app/douban/movie/weeklytv_global_best_weekly"
        rss_infos = doubanRank.get_rss_info(addr)
        rss_info = rss_infos[0]

        title = rss_info.get("title")
        douban_id = rss_info.get("doubanid")
        mtype = rss_info.get("type")

        # 识别媒体信息
        media_info = None
        if douban_id:
            media_info = WebUtils.get_mediainfo_from_id(
                mtype=mtype, mediaid=f"DB:{douban_id}", wait=True
            )
            doubanRank.info(f"media_info:{media_info}")
            if media_info:
                media_info_dic = media_info.__dict__
                doubanRank.info(f"media_info_dic:{media_info_dic}")
        else:
            doubanRank.error(
                f"无法识别媒体信息：{title} （豆瓣id：{douban_id}）"
            )

        # doubanRank.info("media_info end")
        assert media_info not in [None, {}]

    def _test_add_rss_tv(self):
        doubanRank.init_config(config)

        douban_id = 35774728
        douban_title = "了不起的麦瑟尔夫人 第五季"

        mtype = MediaType.TV
        mediaid = f"DB:{douban_id}"
        media_info = WebUtils.get_mediainfo_from_id(
            mtype=mtype, mediaid=mediaid, wait=True
        )

        if media_info:
            media_info_dic = media_info.__dict__
            # log.info(f"media_info_dic:{media_info_dic}")
            with open(
                current_dir / "media_info_dic.txt", "w", encoding="utf-8"
            ) as m:
                m.write(f"{media_info_dic}")

            if media_info.tmdb_info:
                media_info_tmdb_info_dic = media_info.tmdb_info.__dict__
                with open(
                    current_dir / "media_info_tmdb_info_dic.txt",
                    "w",
                    encoding="utf-8",
                ) as t:
                    t.write(f"{media_info_tmdb_info_dic}")

            seasons = Media().get_tmdb_tv_seasons(media_info.tmdb_info)
            if seasons:
                for season in seasons:
                    media_info.begin_season = season.get("season_number")
                    assert media_info not in [None, {}]
                    # doubanRank.info(f"season:{season}")
                    doubanRank.add_rss(media_info, douban_title)

    def _test_refresh_rss(self):
        doubanRank.init_config(config)
        doubanRank.refresh_rss()

    def _test_rank_delete_history_all(self):
        doubanRank.init_config(config)
        doubanRank.delete_rank_history_all()

    def _test_refresh_rss_delete(self):
        config["is_delete_history_all"] = True
        doubanRank.init_config(config)
        doubanRank.refresh_rss()
