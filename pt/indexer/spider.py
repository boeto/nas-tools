import traceback

import dateparser
import copy
import re
import feapder
from pyquery import PyQuery as pq
from jinja2 import Template

import log
from utils.indexer_conf import IndexerConf


class TorrentSpider(feapder.AirSpider):
    __custom_setting__ = dict(
        USE_SESSION=True,
        SPIDER_MAX_RETRY_TIMES=0,
    )
    is_complete = False
    cookies = None
    config_yaml = None
    keyword = None
    torrents_info_array = []
    indexer = None
    torrents_info = {}
    article_list = None
    fields = None

    def setparam(self, indexer : IndexerConf, keyword):
        if not indexer or not keyword:
            return
        self.keyword = keyword
        self.indexer = indexer
        self.cookies = self.indexer.cookie
        self.torrents_info_array = []

    def start_requests(self):
        domain = self.indexer.domain
        torrentspath = self.indexer.search.get('paths', [{}])[0].get('path')
        searchurl = domain + torrentspath + '?stypes=s&search=' + self.keyword
        yield feapder.Request(searchurl, cookies=self.cookies)

    # def detail_requests(self,download_url):
    #     searchurl=self.indexer.domain+download_url
    #
    #     yield feapder.Request(searchurl, cookies=manual_cookies, callback=self.get_title_optional)

    # def get_title_optional(self, request, response):
    #     article_list = response.extract()
    #     doc = pq(article_list)
    #     t_o=doc(self.fields['title_optional']['selector'])
    #     items = [item.attr(self.fields['title_optional']['attribute']) for item in t_o.items()]
    #     self.title_optional.append(items)

    def Getdownloadvolumefactorselector(self, torrent):
        # self.tor.downloadvolumefactor=[]
        for downloadvolumefactorselector in list(self.fields.get('downloadvolumefactor',
                                                                 {}).get('case',
                                                                         {}).keys()):
            downloadvolumefactor = pq(torrent)(downloadvolumefactorselector)
            if len(downloadvolumefactor) > 0:
                # self.tor.downloadvolumefactor.append(self.fields['downloadvolumefactor']['case'][downloadvolumefactorselector])
                self.torrents_info['downloadvolumefactor'] = self.fields.get('downloadvolumefactor',
                                                                             {}).get('case',
                                                                                     {}).get(downloadvolumefactorselector)
                break

    def Getuploadvolumefactorselector(self, torrent):
        # self.tor.uploadvolumefactor=[]
        for uploadvolumefactorselector in list(self.fields.get('uploadvolumefactor', {}).get('case', {}).keys()):
            uploadvolumefactor = pq(torrent)(uploadvolumefactorselector)
            if len(uploadvolumefactor) > 0:
                # self.tor.uploadvolumefactor.append(self.fields['uploadvolumefactor']['case'][uploadvolumefactorselector])
                self.torrents_info['uploadvolumefactor'] = self.fields.get('uploadvolumefactor',
                                                                           {}).get('case',
                                                                                   {}).get(uploadvolumefactorselector)
                break

    # gettitle
    def Gettitle_default(self, torrent):
        # title_default
        selector = ''
        if "title_default" in self.fields:
            title_default = torrent(self.fields.get('title_default',
                                                    {}).get('selector')).clone()
            selector = self.fields.get('title_default')
        else:
            title_default = torrent(self.fields.get('title',
                                                    {}).get('selector')).clone()
            selector = self.fields.get('title')
        if 'remove' in selector:
            removelist = selector.get('remove', '').split(', ')
            for v in removelist:
                title_default.remove(v)

        items = [item.text() for item in title_default.items() if item]
        # self.tor.title=items
        self.torrents_info['title'] = items[0] if items else ''

    def Getdetails(self, torrent):
        # details
        details = torrent(self.fields.get('details', {}).get('selector'))
        items = [item.attr(self.fields.get('details', {}).get('attribute')) for item in details.items()]
        # self.tor.page_url=self.indexer.domain+items[0]
        # self.tor.details=items
        self.torrents_info['details'] = items[0] if items else ''
        self.torrents_info['page_url'] = self.indexer.domain + items[0] if items else ''

    def Getdownload(self, torrent):
        # download link
        download = torrent(self.fields.get('download', {}).get('selector'))
        items = [item.attr(self.fields.get('download', {}).get('attribute')) for item in download.items()]
        # self.tor.download=items
        self.torrents_info['download'] = items[0] if items else 0

    def Getimdbid(self, torrent):
        # imdb
        if "imdbid" in self.fields:
            imdbid = torrent(self.fields.get('imdbid', {}).get('selector'))
            items = [item.attr(self.fields.get('imdbid', {}).get('attribute')) for item in imdbid.items()]
            # self.tor.imdbid=items
            if len(items) > 0:
                self.torrents_info['imdbid'] = items[0]

    def Getsize(self, torrent):
        # torrent size
        size = torrent(self.fields.get('size', {}).get('selector'))
        items = [item.text() for item in size.items() if item]
        # self.tor.size=items
        if len(items) > 1:
            size = items[0].split("\n")
            if size[1] == 'GB':
                size = float(size[0]) * 1073741824
            else:
                size = float(size[0]) * 1048576
            self.torrents_info['size'] = size

    def Getleechers(self, torrent):
        # torrent leechers
        leechers = torrent(self.fields.get('leechers', {}).get('selector'))
        items = [item.text() for item in leechers.items() if item]
        # self.tor.leechers=items
        # self.tor.peers=items
        self.torrents_info['leechers'] = items[0] if items else 0
        self.torrents_info['peers'] = items[0] if items else 0

    def Getseeders(self, torrent):
        # torrent leechers
        seeders = torrent(self.fields.get('seeders', {}).get('selector'))
        items = [item.text() for item in seeders.items() if item]
        # self.tor.seeders=items
        self.torrents_info['seeders'] = items[0] if items else 0

    def Getgrabs(self, torrent):
        # torrent grabs
        grabs = torrent(self.fields.get('grabs', {}).get('selector'))
        items = [item.text() for item in grabs.items() if item]
        # self.tor.grabs=items
        self.torrents_info['grabs'] = items[0] if items else ''

    def Gettitle_optional(self, torrent, fields):
        # title_optional
        if "selector" in self.fields.get('description'):
            selector = self.fields.get('description')
            t_o = torrent(selector.get('selector', '')).clone()
            items = ''
            if 'attribute' in selector:
                items = [item.attr(self.fields.get('description', {}).get('attribute')) for item in t_o.items()]

            if 'remove' in selector:
                removelist = selector.get('remove', '').split(', ')
                for v in removelist:
                    t_o.remove(v)

            if "contents" in selector:
                if selector['selector'].find("td.embedded") != -1:
                    t_o = t_o("span")
                items = [item.text() for item in t_o.items() if item]
                items = items[selector.get("contents")]
                # t_o = t_o("span")[selector["contents"]]
                # items = t_o.text
            elif "index" in selector:
                items = [item.text() for item in t_o.items() if item]
                items = items[selector.get("index")]

            # self.tor.description=items
            self.torrents_info['description'] = items

        if "text" in self.fields.get('description'):
            template = Template(self.fields.get('description', {}).get('text'))

            # template.render(fields=self.fields)
            tags = torrent(self.fields.get('tags', {}).get('selector', '')).text()
            subject = torrent(self.fields.get('subject', {}).get('selector', '')).text()
            render_dict = {'tags': tags, 'subject': subject}
            title = template.render(fields=render_dict)
            self.torrents_info['description'] = title
            # exec(self.fields['description']['text'])

        # items = [item.text() for item in t_o.items()]

        # self.tor.description=[]
        # for i in range(int(len(items)/3)):

    def Getdate_added(self, torrent):
        # date_added
        selector = torrent(self.fields.get('date_elapsed', {}).get('selector', ''))
        items = [item.attr(self.fields.get('date_elapsed', {}).get('attribute', '')) for item in selector.items()]
        # self.tor.date_added=items
        self.torrents_info['date_added'] = items[0] if items else ''

    def Getdate_elapsed(self, torrent):
        # date_added
        selector = torrent(self.fields.get('date_elapsed', {}).get('selector', ''))
        items = [item.text() for item in selector.items()]
        # self.tor.date_elapsed=items
        self.torrents_info['date_elapsed'] = items[0] if items else ''

    def Getcategory(self, torrent):
        # date_added
        selector = torrent(self.fields.get('category', {}).get('selector', ''))
        items = [item.attr(self.fields.get('category', {}).get('attribute')) for item in selector.items()]
        if "filters" in self.fields.get('category') or []:
            for c_filter in self.fields.get('category', {}).get('filters'):
                if c_filter.get('name') == "replace":
                    arg1 = c_filter.get('args', [])[0]
                    arg2 = c_filter.get('args', [])[1]
                    for i in range(len(items)):
                        items[i] = items[i].replace(arg1, arg2)
                if c_filter.get('name') == "querystring":
                    arg1 = c_filter.get('args')
                    str = items[0]
                    str = "car=daasd$dada=dasda"

                    # items=querystring.parse_qs(str)

        # self.tor.category=items[0]
        self.torrents_info['category'] = items[0] if items else ''

    def Getfree_deadline(self, torrent):
        # date_added
        selector = torrent(self.fields.get('free_deadline', {}).get('selector', ''))
        # items = [item.text() for item in selector.items()]
        items = [item.attr(self.fields.get('free_deadline', {}).get('attribute')) for item in selector.items()]
        # print(items)
        # print(len(items))
        if len(items) > 0 and items is not None:
            if items[0] is not None:
                # print(len(items))
                if "filters" in self.fields.get('free_deadline'):
                    itemdata = items[0]
                    for f_filter in self.fields.get('free_deadline', {}).get('filters') or []:
                        if f_filter.get('name') == "re_search":
                            arg1 = f_filter.get('args', [])[0]
                            arg2 = f_filter.get('args', [])[1]
                            items = re.search(arg1, itemdata, arg2)[0]
                        if f_filter.get('name') == "dateparse":
                            arg1 = f_filter.get('args')
                            items = dateparser.parse(itemdata, date_formats=[arg1])

        # self.tor.free_deadline=items
        self.torrents_info['free_deadline'] = items

    def Getinfo(self, torrent):
        self.Gettitle_default(torrent)
        self.Gettitle_optional(torrent, self.fields)
        self.Getgrabs(torrent)
        self.Getleechers(torrent)
        self.Getseeders(torrent)
        self.Getsize(torrent)
        self.Getimdbid(torrent)
        self.Getdownload(torrent)
        self.Getdetails(torrent)
        self.Getdownloadvolumefactorselector(torrent)
        self.Getuploadvolumefactorselector(torrent)
        self.Getdate_added(torrent)
        self.Getdate_elapsed(torrent)
        self.Getcategory(torrent)
        self.Getfree_deadline(torrent)
        return self.torrents_info

    def parse(self, request, response):
        try:
            # 获取网站信息
            self.article_list = response.extract()
            # 获取站点种子xml
            self.fields = self.indexer.torrents.get('fields')
            doc = pq(self.article_list)
            # 种子筛选器
            torrents_selector = self.indexer.torrents.get('list', {}).get('selector')

            str_list = list(torrents_selector)
            # 兼容选择器中has()函数 部分情况下无双引号会报错
            has_index = torrents_selector.find('has')

            # 存在has() 添加双引号
            flag = 0
            if has_index != -1:
                str_list.insert(has_index + 4, '"')
                for i in range(len(str_list)):
                    if i > has_index + 2:
                        n = str_list[i]
                        if n == '(':
                            flag = flag + 1
                        if n == ')':
                            flag = flag - 1
                        if flag == 0:
                            str_list.insert(i, '"')
                torrents_selector = "".join(str_list)

            # 获取种子html列表
            torrents = doc(torrents_selector)
            self.torrents_info = {}

            # title_default
            # 遍历种子html列表
            for torn in torrents:
                torn = pq(torn)
                # self.tor.indexer=self.indexer.id
                self.torrents_info['indexer'] = self.indexer.id
                self.torrents_info_array.append(copy.deepcopy(self.Getinfo(torn)))
        except Exception as err:
            log.warn("【SPLIDER】错误：%s - %s" % (str(err), traceback.format_exc()))
        finally:
            self.is_complete = True
