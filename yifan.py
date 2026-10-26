# coding = utf-8
#!/usr/bin/python
import json
import sys
import requests
import time
import hashlib
from urllib.parse import urlparse
from base.spider import Spider

sys.path.append('..')
session = requests.Session()

class Spider(Spider):
    def __init__(self):
        self.name = "爱壹帆🌸"
        self.hosts = "https://app-m10.tripdata.app"
        self.public_key = ""
        self.private_key = ""
        self.key_loaded = False

        """ 请求工具 """
        self.session = requests.Session()


    def getName(self):
        return self.name

    def init(self, extend=''):
        pass

    def getKey(self):
        publicKeyIndex = int(time.time() * 1000)
        privateKey = [
            'version001', 'vers1on001', 'vers1on00i', 'bersion001',
            'vcrsion001', 'versi0n001', 'versio_001', 'version0o1'
        ]
        key = privateKey[publicKeyIndex % len(privateKey)]
        base_url = self.hosts.rstrip('/') + "/v3/home/config?cinema=1"
        query = urlparse(base_url).query
        o = f"{publicKeyIndex}&{query}&{key}"
        vv = hashlib.md5(o.encode("utf-8")).hexdigest()
        url = f"{base_url}&vv={vv}&pub={publicKeyIndex}"
        try:
            r = self.session.get(url, timeout=15).json()
            pConfig = r["data"]["info"][0]["pConfig"]
            self.public_key  = pConfig.get("publicKey", "")
            self.private_key = (pConfig.get("privateKey") or [""])[0]
            self.key_loaded = bool(self.public_key and self.private_key)
        except Exception as e:
            self.key_loaded = False

    def get_data(self, data, path, use_cache=True):
        try:
            # 1. key 就绪
            if not self.key_loaded:
                self.getKey()

            # 2. 参数 + 签名
            query_str = '&'.join(f"{k}={v}" for k, v in data.items())
            o = f"{self.public_key}&{query_str.lower()}&{self.private_key}"
            vv = hashlib.md5(o.encode("utf-8")).hexdigest()

            # 3. 拼 URL
            base_url = self.hosts.rstrip('/') + path + ('&' if '?' in path else '?')
            url = f"{base_url}{query_str}&vv={vv}&pub={self.public_key}"

            # 4. 发请求
            r = self.session.get(url, timeout=15).json()

            return r
        except Exception as e:
            print(f"[get_data] 失败 path={path}: {e}")  # 建议加
            return None


    # ---------- 首页分类 + 筛选器 ----------
    def homeContent(self, filter):
        result = {}
        classes = [
            {"type_name": "电影", "type_id": "3"},
            {"type_name": "电视剧", "type_id": "4"},
            {"type_name": "综艺", "type_id": "5"},
            {"type_name": "动漫", "type_id": "6"},
            {"type_name": "短剧", "type_id": "8"},
            {"type_name": "纪录片", "type_id": "7"},
        ]
        result['class'] = classes

        filters = {}
        for cate in classes:
            tid = cate['type_id']
            filters[tid] = [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": "0"},
                    {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "日本", "v": "日本"},
                    {"n": "韩国", "v": "韩国"}, {"n": "欧美", "v": "欧美"},
                    {"n": "英国", "v": "英国"}, {"n": "泰国", "v": "泰国"},
                    {"n": "其它", "v": "其它"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": "0"},
                    {"n": "今年", "v": "今年"}, {"n": "去年", "v": "去年"},
                    {"n": "更早", "v": "更早"}, {"n": "90年代", "v": "90年代"},
                    {"n": "80年代", "v": "80年代"}, {"n": "怀旧", "v": "怀旧"}
                ]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "添加时间", "v": "0"}, {"n": "更新时间", "v": "1"}, {"n": "人气高低", "v": "2"}, {"n": "评分高低", "v": "3"}
                ]}
            ]
        result['filters'] = filters
        return result

    # ---------- 首页推荐视频 ----------
    def homeVideoContent(self):
        videos = []
        try:
            base_url = self.hosts.rstrip('/') + "/v3/home/getAllVideo"
            params = {
                "cinema": "1",
                "set": "1",
                "size": "13",
                "isTopic": "1",
                "cacheable": "1"
            }

            r = self.session.get(base_url, params=params, timeout=15).json()

            if r and r.get('ret') == 200:
                info0 = (r.get('data', {}).get('info') or [{}])[0]

                # 把所有分类的列表合并
                all_lists = (
                        (info0.get('filmList') or []) +
                        (info0.get('tvList') or []) +
                        (info0.get('varietyList') or []) +
                        (info0.get('animeList') or [])
                )

                for item in all_lists:
                    videos.append({
                        "vod_id": f"{item.get('key', '')}|{item.get('lastKey', '')}|{item.get('videoClassID', '0,1,0')}",
                        "vod_name": item.get('title', ''),
                        "vod_pic": item.get('image', ''),
                        "vod_remarks": item.get("lastName", "")  # 直接取
                    })

        except Exception as e:
            print(f"[home] 获取失败: {e}")

        return {'list': videos}

    # ---------- 分类内容 ----------
    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        pagecount, total = 9999, 999999
        try:
            params = {
                "cinema": "1",
                "page": str(pg),
                "size": "32",
                "orderby": extend.get('sort', '0') or '0',
                "desc": "1",
                "cid": f"0,1,{tid}",
                "region": extend.get('area', '') or '',
                "isserial": "-1",
                "isIndex": "-1",
                "isfree": "-1",
                "isVertical": "-1",
            }
            data = self.get_data(params, '/api/list/Search')
            if data and data.get('ret') == 200:
                info0 = (data.get('data', {}).get('info') or [{}])[0]
                vod_list = info0.get('result') or []
                recordcount = info0.get('recordcount', 0) or 0
                maxpage = info0.get('maxpage', 0) or 0
                if recordcount:
                    total = recordcount
                if maxpage:
                    pagecount = maxpage

                for item in vod_list:
                    remarks = item.get("lastName", '')

                    videos.append({
                        "vod_id": f"{item.get('key', '')}|{item.get('lastKey', '')}|0,1,{tid}",
                        "vod_name": item.get('title', ''),
                        "vod_pic": item.get('image', ''),
                        "vod_remarks": remarks
                    })
        except Exception as e:
            print(f"获取分类内容失败: {e}")

        return {
            'list': videos,
            'page': int(pg),
            'pagecount': pagecount,
            'limit': 32,
            'total': total
        }

    # ---------- 详情 ----------
    def detailContent(self, ids):

        detail = {}
        try:
            vod_id   = ids[0]
            parts    = vod_id.split('|', 2)
            key      = parts[0] if len(parts) > 0 else ''
            last_key = parts[1] if len(parts) > 1 else ''
            cid      = parts[2] if len(parts) > 2 else ''

            d_params = {
                "cinema": "1",
                "device": "1",
                "player": "CkPlayer",
                "tech": "HLS",
                "country": "HU",
                "lang": "cns",
                "v": "1",
                "id": key,
            }
            d_data = self.get_data(d_params, '/v3/video/detail')
            if d_data  and d_data .get('ret') == 200:
                info = (d_data.get('data', {}).get('info') or [{}])[0]
                stars = info.get('stars') or []
                directors = info.get('directors') or []
                typeName = info.get('channel', '')

                vod_actor = ",".join(stars) if isinstance(stars, list) else str(stars)
                vod_director = ",".join(directors) if isinstance(directors, list) else str(directors)

                p_params = {
                    "cinema": "1",
                    "vid": key,
                    "lsk": "1",
                    "taxis": "0",
                    "cid": cid,
                }
                p_data = self.get_data(p_params, '/v3/video/languagesplaylist')
                vod_play_url = ""
                if p_data and p_data.get('ret') == 200:
                    # 1. 取出 playList 数组
                    info_list = p_data.get('data', {}).get('info') or []
                    if info_list:
                        play_list = info_list[0].get('playList') or []

                        # 2. 遍历拼接
                        play_urls = []
                        for item in play_list:
                            if typeName == '电影':
                                name = '正片'
                            else:
                               name = item.get('name', '')

                            p_key = item.get('key', '')
                            if p_key:
                                # 按格式拼接：name$key
                                play_urls.append(f"{name}${key}|{p_key}")

                        # 3. 用 # 连接起来
                        vod_play_url = "#".join(play_urls)

            # --- 3. 组装 detail ---
            detail = {
                "vod_id": vod_id,
                "vod_name": info.get('title', ''),
                "vod_pic": info.get('imgPath', ''),
                "vod_year": str(info.get('post_Year', '')),
                "vod_area": info.get('regional', ''),
                "vod_actor": vod_actor,
                "vod_director": vod_director,
                "vod_content": info.get('contxt', ''),
                "vod_remarks": info.get('lastName', ''),
                "vod_play_from": "爱壹帆",
                "vod_play_url": vod_play_url,
            }

        except Exception as e:
            print(f"获取详情内容失败: {e}")

        return {'list': [detail]} if detail else {'list': []}


    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg=1):
        videos = []
        try:
            # 1. 搜索参数
            params = {
                "tags": key,
                "orderby": "4",
                "page": str(pg),
                "size": "36",
                "desc": "1",
                "isserial": "-1",
                "v": "1"
            }

            # 2. 发起请求
            base_url = self.hosts.rstrip('/') + "/v3/list/briefsearch"
            r = self.session.get(base_url, params=params, timeout=15).json()

            # 3. 解析数据
            if r and r.get('ret') == 200:
                info0 = (r.get('data', {}).get('info') or [{}])[0]
                vod_list = info0.get('result') or []

                for item in vod_list:
                    videos.append({
                        "vod_id": f"{item.get('contxt', '')}|{item.get('key', '')}|{item.get('cidMapper', '0,1,0')}",
                        "vod_name": item.get('title', ''),
                        "vod_pic": item.get('imgPath', ''),
                        "vod_remarks": item.get("lastName", '')  # 直接取，不判断
                    })
        except Exception as e:
            print(f"搜索失败: {e}")

        return {
            'list': videos,
            'page': int(pg),
            'pagecount': 9999,
            'limit': 36,
            'total': 999999
        }

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|')
            v_key = parts[0] if len(parts) > 0 else ''
            p_key = parts[1] if len(parts) > 1 else ''

            p_params = {
                "cinema": "1",
                "id": p_key,
                "a": "0",
                "usersign": "1",
                "device": "1",
                "isMasterSupport": "1",
            }
            p_data = self.get_data(p_params, '/v3/video/play')

            if p_data and p_data.get('ret') == 200:
                # 1. 拿到 info 列表
                info_list = p_data.get('data', {}).get('info') or []
                if info_list:
                    # 2. 拿到 clarity 列表
                    clarity_list = info_list[0].get('clarity') or []

                    # 3. 过滤掉 path 为空的，并且 path 里有 rtmp 的
                    valid_qualities = []
                    for item in clarity_list:
                        path = item.get('path')
                        if path and isinstance(path, dict):
                            rtmp_url = path.get('rtmp')
                            if rtmp_url:
                                valid_qualities.append(item)

                    # 4. 按 bitrate 从大到小排序
                    valid_qualities.sort(key=lambda x: x.get('bitrate', 0), reverse=True)

                    # 5. 取最高画质的 rtmp
                    if valid_qualities:
                        best_quality = valid_qualities[0]
                        real_url = best_quality['path']['rtmp']

                        return {
                            "parse": 0,
                            "playUrl": "",
                            "url": real_url,
                            "header": json.dumps({
                                "User-Agent": "Lavf/57.83.100",
                                "Referer": "https://app-m10.tripdata.app/"
                            })
                        }

        except Exception as e:
            print(f"播放解析失败: {e}")

        return {"parse": 0, "playUrl": "", "url": ""}

    # ---------- 工具 ----------
    def isVideoFormat(self, url):
        video_formats = ['.m3u8', '.mp4', '.avi', '.mkv', '.flv', '.ts']
        return any(url.lower().endswith(fmt) for fmt in video_formats)

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        return None

if __name__ == '__main__':
    pass