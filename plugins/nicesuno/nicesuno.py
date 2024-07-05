# encoding:utf-8
import os
import re
import json
import time
import requests
import threading
from typing import List
from pathvalidate import sanitize_filename
from datetime import datetime

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *

@plugins.register(
    name="NiceSuno",
    desire_priority=100,
    hidden=False,
    desc="使用Suno创作音乐。",
    version="1.5",
    author="空心菜",
)
class NiceSuno(Plugin):
    def __init__(self):
        super().__init__()
        try:
            # 加载配置
            conf = super().load_config()
            # 配置不存在则使用默认配置
            if not conf:
                logger.debug("[Nicesuno] config.json not found, config.json.template used.")
                curdir = os.path.dirname(__file__)
                config_path = os.path.join(curdir, "config.json.template")
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        conf = json.load(f)
            self.suno_api_bases = conf.get("suno_api_bases", [])
            self.music_create_prefixes = conf.get("music_create_prefixes", [])
            self.instrumental_create_prefixes = conf.get("instrumental_create_prefixes", [])
            self.lyrics_create_prefixes = conf.get("lyrics_create_prefixes", [])
            self.music_output_dir = conf.get("music_output_dir", "/tmp")
            self.is_send_lyrics = conf.get("is_send_lyrics", True)
            self.is_send_covers = conf.get("is_send_covers", True)
            if not os.path.exists(self.music_output_dir):
                logger.info(f"[Nicesuno] music_output_dir={self.music_output_dir} not exists, create it.")
                os.makedirs(self.music_output_dir)
            if self.suno_api_bases and isinstance(self.suno_api_bases, List) \
                    and self.music_create_prefixes and isinstance(self.music_create_prefixes, List):
                self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
                logger.info("[Nicesuno] inited")
            else:
                logger.warn("[Nicesuno] init failed because suno_api_bases or music_create_prefixes is incorrect.")
            # Suno账号信息
            self.accounts_info = dict()
            for suno_api_base in self.suno_api_bases:
                self.accounts_info[suno_api_base] = {
                    "last_time": datetime.min,
                    "last_status": "",
                    "used_count": 0,
                    "daily_limit": 5
                }
        except Exception as e:
            logger.error(f"[Nicesuno] init failed, ignored.")
            raise e

    def on_handle_context(self, e_context: EventContext):
        try:
            # 判断是否是TEXT类型消息
            context = e_context["context"]
            if context.type != ContextType.TEXT:
                return
            content = context.content
            logger.debug(f"[Nicesuno] on_handle_context.")

            # 查询Suno账户信息的请求
            content_lower = content.strip().lower()
            if content_lower.startswith('&suno'):
                action = content_lower[5:].strip()
                if action in ["view", "read", "info", ""]:
                    result = self.view_account_info()
                    reply = Reply(ReplyType.INFO, result)
                else:
                    reply = Reply(ReplyType.ERROR, "指令有误，当前仅支持&sunoinfo指令！")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

            # 判断是否包含创作的前缀
            make_instrumental, make_lyrics = False, False
            music_create_prefix = self._check_prefix(content, self.music_create_prefixes)
            instrumental_create_prefix = self._check_prefix(content, self.instrumental_create_prefixes)
            lyrics_create_prefix = self._check_prefix(content, self.lyrics_create_prefixes)
            if music_create_prefix:
                suno_prompt = content[len(music_create_prefix):].strip()
            elif instrumental_create_prefix:
                make_instrumental = True
                suno_prompt = content[len(instrumental_create_prefix):].strip()
            elif lyrics_create_prefix:
                make_lyrics = True
                suno_prompt = content[len(lyrics_create_prefix):].strip()
            else:
                logger.debug(f"[Nicesuno] content starts without any suno prefixes, ignored.")
                return
            # 判断是否存在创作的提示词
            if not suno_prompt:
                logger.info("[Nicesuno] content starts without any suno prompts, ignored.")
                return

            # 开始创作
            if make_lyrics:
                logger.info(f"[Nicesuno] start generating lyrics, suno_prompt={suno_prompt}.")
                self._create_lyrics(e_context, suno_prompt)
            else:
                logger.info(f"[Nicesuno] start generating {'instrumental' if make_instrumental else 'vocal'} music, suno_prompt={suno_prompt}.")
                self._create_music(e_context, suno_prompt, make_instrumental)
        except Exception as e:
            logger.warning(f"[Nicesuno] failed to generate music, error={e}")
            reply = Reply(ReplyType.TEXT, "抱歉！创作失败了，请稍后再试🥺")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

    # 创作音乐
    def _create_music(self, e_context, suno_prompt, make_instrumental=False):
        # 搜索可用的创作音乐的账号
        suno_api_base = self.search_account()
        if not suno_api_base:
            logger.warning(f"[Nicesuno] no available account to create music, ignored.")
            reply = Reply(ReplyType.TEXT, "抱歉！没有可用的Suno账号，请稍后再试🥺")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        else:
            logger.info(f"[Nicesuno] current suno_api_base={suno_api_base}")
            logger.debug(f"[Nicesuno] current accounts_info={self.accounts_info}")

        # 自定义模式
        if '标题' in suno_prompt and '风格' in suno_prompt and len(suno_prompt.split('\n')) > 2:
            regex_prompt = r' *标题[:：]?(?P<title>[\S ]*)\n+ *风格[:：]?(?P<tags>[\S ]*)(\n+(?P<lyrics>.*))?'
            r = re.fullmatch(regex_prompt, suno_prompt, re.DOTALL)
            title = r.group('title').strip() if r and r.group('title') else None
            tags = r.group('tags').strip() if r and r.group('tags') else None
            lyrics = r.group('lyrics').strip() if r and r.group('lyrics') else None
            if r and (tags or lyrics):
                logger.info(f"[Nicesuno] generating {'instrumental' if make_instrumental else 'vocal'} music in custom mode, title={title}, tags={tags}, lyrics={lyrics}")
                data = self._suno_generate_music_custom_mode(suno_api_base, title, tags, lyrics, make_instrumental)
            else:
                logger.warning(f"[Nicesuno] generating {'instrumental' if make_instrumental else 'vocal'} music in custom mode failed because of wrong format, suno_prompt={suno_prompt}")
                reply = Reply(ReplyType.TEXT, self.get_help_text(verbose=True))
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
        # 描述模式
        else:
            logger.info(f"[Nicesuno] generating {'instrumental' if make_instrumental else 'vocal'} music with description, description={suno_prompt}")
            data = self._suno_generate_music_with_description(suno_api_base, suno_prompt, make_instrumental)

        channel = e_context["channel"]
        context = e_context["context"]
        to_user_nickname = context["msg"].to_user_nickname
        if not data:
            logger.warning(f"response data of _suno_generate_music is empty.")
            reply = Reply(ReplyType.TEXT, f"因为神秘原因，音乐创作失败😂请稍后再重试...")
        # 音乐创作失败
        elif data.get('detail'):
            current_account = self.accounts_info[suno_api_base]
            current_account["last_time"] = datetime.now()
            detail = data.get('detail')
            current_account["last_status"] = detail
            logger.warning(f"[Nicesuno] error occurred in _suno_generate_music, response data={data}")
            if detail == 'Insufficient credits.':
                current_account["used_count"] = current_account["daily_limit"]
                reply = Reply(ReplyType.TEXT, f"因为当前账号超过限额，音乐创作失败😂请重试一次好不好😘")
            elif detail == 'Unauthorized':
                reply = Reply(ReplyType.TEXT, f"因为Suno-API登录失效，音乐创作失败😂请更新Suno-API的SessionID和Cookie...")
            elif detail == 'Topic too long.':
                reply = Reply(ReplyType.TEXT, f"因为废话太多，音乐创作失败😂请精简后再重试...")
            elif detail == 'Too many running jobs.':
                reply = Reply(ReplyType.TEXT, f"因为创作任务过多，音乐创作失败😂请稍等片刻再重试...")
            else:
                reply = Reply(ReplyType.TEXT, f"因为{detail}，音乐创作失败😂请稍后再重试...")
        # 音乐创作异常
        elif not data.get('clips'):
            logger.warning(f"[Nicesuno] no clips in response data of _suno_generate_music, response data={data}")
            reply = Reply(ReplyType.TEXT, f"因为神秘原因，音乐创作异常😂请稍后再重试...")
        # 音乐创作成功
        else:
            current_account = self.accounts_info[suno_api_base]
            current_account["last_time"] = datetime.now()
            current_account["last_status"] = "ok"
            current_account["used_count"] += 1
            # 获取和发送音乐
            aids = [clip['id'] for clip in data['clips']]
            logger.debug(f"[Nicesuno] start to handle music, aids={aids}, data={data}")
            threading.Thread(target=self._handle_music, args=(channel, context, suno_api_base, aids)).start()
            reply = Reply(ReplyType.TEXT, f"{to_user_nickname}正在为您创作音乐，请稍等☕")
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    # 创作歌词
    def _create_lyrics(self, e_context, suno_prompt):
        # 搜索可用的创作歌词账号
        suno_api_base = self.search_account(create_music=False)
        if not suno_api_base:
            logger.warning(f"[Nicesuno] no available account to create lyrics, ignored.")
            reply = Reply(ReplyType.TEXT, "抱歉！没有可用Suno账号，请稍后再试🥺")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
        else:
            logger.info(f"[Nicesuno] current suno_api_base={suno_api_base}")
            logger.debug(f"[Nicesuno] current accounts_info={self.accounts_info}")

        data = self._suno_generate_lyrics(suno_api_base, suno_prompt)
        channel = e_context["channel"]
        context = e_context["context"]
        reply = None
        if not data:
            logger.warning(f"response data of _suno_generate_lyrics is empty.")
            reply = Reply(ReplyType.TEXT, f"因为神秘原因，歌词创作失败😂请稍后再重试...")
        elif data.get('detail'):
            current_account = self.accounts_info[suno_api_base]
            current_account["last_time"] = datetime.now()
            detail = data.get('detail')
            current_account["last_status"] = detail
            logger.warning(f"[Nicesuno] error occurred in _suno_generate_lyrics, response data={data}")
            if detail == 'Unauthorized':
                reply = Reply(ReplyType.TEXT, f"因为Suno-API登录失效，歌词创作失败😂请更新Suno-API的SessionID和Cookie...")
            elif detail == 'Topic too long.':
                reply = Reply(ReplyType.TEXT, f"因为废话太多，歌词创作失败😂请精简后再重试...")
            elif detail == 'Too many running jobs.':
                reply = Reply(ReplyType.TEXT, f"因为创作任务过多，歌词创作失败😂请稍等片刻再重试...")
            else:
                reply = Reply(ReplyType.TEXT, f"因为{detail}，歌词创作失败😂请稍后再重试...")
        else:
            # 获取和发送歌词
            lid = data['id']
            logger.debug(f"[Nicesuno] start to handle lyrics, lid={lid}, data={data}")
            threading.Thread(target=self._handle_lyric, args=(channel, context, suno_api_base, lid, suno_prompt)).start()
        if reply:
            e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    # 下载和发送音乐
    def _handle_music(self, channel, context, suno_api_base, aids: List):
        # 用户信息
        actual_user_nickname = context["msg"].actual_user_nickname or context["msg"].other_user_nickname
        to_user_nickname = context["msg"].to_user_nickname
        # 获取歌词和音乐
        initial_delay_seconds = 15
        last_lyrics = ""
        for aid in aids:
            # 获取音乐信息
            start_time = time.time()
            while True:
                if initial_delay_seconds:
                    time.sleep(initial_delay_seconds)
                    initial_delay_seconds = 0
                data = self._suno_get_music(suno_api_base, aid)
                if not data:
                    raise Exception("[Nicesuno] 获取音乐信息失败！")
                elif data["audio_url"]:
                    break
                elif time.time() - start_time > 180:
                    raise TimeoutError("[Nicesuno] 获取音乐信息超时！")
                time.sleep(5)
            # 解析音乐信息
            title, metadata, audio_url = data["title"], data["metadata"], data["audio_url"]
            lyrics, tags, description_prompt = metadata["prompt"], metadata["tags"], metadata['gpt_description_prompt']
            description_prompt = description_prompt if description_prompt else "自定义模式不展示"
            # 发送歌词
            if not self.is_send_lyrics:
                logger.debug(f"[Nicesuno] 发送歌词开关关闭，不发送歌词！")
            elif lyrics == last_lyrics:
                logger.debug("[Nicesuno] 歌词和上次相同，不再重复发送歌词！")
            else:
                reply_text = f"🎻{title}🎻\n\n{lyrics}\n\n🎹风格: {tags}\n👶发起人：{actual_user_nickname}\n🍀制作人：Suno\n🎤提示词: {description_prompt}"
                logger.debug(f"[Nicesuno] 发送歌词，reply_text={reply_text}")
                last_lyrics = lyrics
                reply = Reply(ReplyType.TEXT, reply_text)
                channel.send(reply, context)
            # 下载音乐
            filename = f"{int(time.time())}-{sanitize_filename(title).replace(' ', '')[:20]}"
            audio_path = os.path.join(self.music_output_dir, f"{filename}.mp3")
            logger.debug(f"[Nicesuno] 下载音乐，audio_url={audio_url}")
            self._download_file(audio_url, audio_path)
            # 发送音乐
            logger.debug(f"[Nicesuno] 发送音乐，audio_path={audio_path}")
            reply = Reply(ReplyType.FILE, audio_path)
            channel.send(reply, context)
            # 发送封面
            if not self.is_send_covers:
                logger.debug(f"[Nicesuno] 发送封面开关关闭，不发送封面！")
            else:
                # 获取封面信息
                start_time = time.time()
                while True:
                    data = self._suno_get_music(suno_api_base, aid)
                    if not data:
                        #raise Exception("[Nicesuno] 获取封面信息失败！")
                        logger.warning("[Nicesuno] 获取封面信息失败！")
                        break
                    elif data["image_url"]:
                        break
                    elif time.time() - start_time > 60:
                        #raise TimeoutError("[Nicesuno] 获取封面信息超时！")
                        logger.warning("[Nicesuno] 获取封面信息超时！")
                        break
                    time.sleep(5)
                if data and data["image_url"]:
                    image_url = data["image_url"]
                    logger.debug(f"[Nicesuno] 发送封面，image_url={image_url}")
                    reply = Reply(ReplyType.IMAGE_URL, image_url)
                    channel.send(reply, context)
                else:
                    logger.warning(f"[Nicesuno] 获取封面信息失败，放弃发送封面！")
        # 获取视频地址
        video_urls = []
        for aid in aids:
            # 获取视频地址
            start_time = time.time()
            while True:
                data = self._suno_get_music(suno_api_base, aid)
                if not data:
                    #raise Exception("[Nicesuno] 获取视频地址失败！")
                    logger.warning("[Nicesuno] 获取视频地址失败！")
                    video_urls.append("获取失败！")
                    break
                elif data["video_url"]:
                    video_urls.append(data["video_url"])
                    break
                elif time.time() - start_time > 180:
                    #raise TimeoutError("[Nicesuno] 获取视频地址超时！")
                    logger.warning("[Nicesuno] 获取视频地址超时！")
                    video_urls.append("获取超时！")
                time.sleep(10)
        # 查收提醒
        video_text = '\n'.join(f'视频{idx+1}: {url}' for idx, url in zip(range(len(video_urls)), video_urls))
        reply_text = f"{to_user_nickname}已经为您创作了音乐，请查收！以下是音乐视频：\n{video_text}"
        if context.get("isgroup", False):
            reply_text = f"@{actual_user_nickname}\n" + reply_text
        logger.debug(f"[Nicesuno] 发送查收提醒，reply_text={reply_text}")
        reply = Reply(ReplyType.TEXT, reply_text)
        channel.send(reply, context)

    # 获取和发送歌词
    def _handle_lyric(self, channel, context, suno_api_base, lid, description_prompt=""):
        # 用户信息
        actual_user_nickname = context["msg"].actual_user_nickname or context["msg"].other_user_nickname
        # 获取歌词信息
        start_time = time.time()
        while True:
            data = self._suno_get_lyrics(suno_api_base, lid)
            if not data:
                raise Exception("[Nicesuno] 获取歌词信息失败！")
            elif data["status"] == 'complete':
                break
            elif time.time() - start_time > 120:
                raise TimeoutError("[Nicesuno] 获取歌词信息超时！")
            time.sleep(5)
        # 发送歌词
        title, lyrics = data["title"], data["text"]
        reply_text = f"🎻{title}🎻\n\n{lyrics}\n\n👶发起人：{actual_user_nickname}\n🍀制作人：Suno\n🎤提示词: {description_prompt}"
        logger.debug(f"[Nicesuno] 发送歌词，reply_text={reply_text}")
        reply = Reply(ReplyType.TEXT, reply_text)
        channel.send(reply, context)

    # 创作音乐-描述模式
    def _suno_generate_music_with_description(self, suno_api_base, description, make_instrumental=False):
        payload = {
            "gpt_description_prompt": description,
            "make_instrumental": make_instrumental,
            "mv": "chirp-v3-0",
        }
        try:
            response = requests.post(f"{suno_api_base}/generate/description-mode", data=json.dumps(payload), timeout=(5, 30))
            if response.status_code != 200:
                raise Exception(f"status_code is not ok, status_code={response.status_code}")
            logger.debug(f"[Nicesuno] _suno_generate_music_with_description, response={response.text}")
            return response.json()
        except Exception as e:
            logger.error(f"[Nicesuno] _suno_generate_music_with_description failed, description={description}, error={e}")

    # 创作音乐-自定义模式
    def _suno_generate_music_custom_mode(self, suno_api_base, title=None, tags=None, lyrics=None, make_instrumental=False):
        payload = {
            "title": title,
            "tags": tags,
            "prompt": lyrics,
            "make_instrumental": make_instrumental,
            "mv": "chirp-v3-0",
            "continue_clip_id": None,
            "continue_at": None,
        }
        try:
            response = requests.post(f"{suno_api_base}/generate", data=json.dumps(payload), timeout=(5, 30))
            if response.status_code != 200:
                raise Exception(f"status_code is not ok, status_code={response.status_code}")
            logger.debug(f"[Nicesuno] _suno_generate_music_custom_mode, response={response.text}")
            return response.json()
        except Exception as e:
            logger.error(f"[Nicesuno] _suno_generate_music_custom_mode failed, title={title}, tags={tags}, lyrics={lyrics}, error={e}")

    # 获取音乐信息
    def _suno_get_music(self, suno_api_base, aid, retry_count=3):
        while retry_count >= 0:
            try:
                response = requests.get(f"{suno_api_base}/feed/{aid}", timeout=(5, 30))
                if response.status_code != 200:
                    raise Exception(f"status_code is not ok, status_code={response.status_code}")
                logger.debug(f"[Nicesuno] _suno_get_music, response={response.text}")
                return response.json()[0]
            except Exception as e:
                logger.error(f"[Nicesuno] _suno_get_music failed, aid={aid}, error={e}")
                retry_count -= 1
                time.sleep(5)

    # 创作歌词
    def _suno_generate_lyrics(self, suno_api_base, suno_lyric_prompt, retry_count=3):
        payload = {
            "prompt": suno_lyric_prompt
        }
        while retry_count >= 0:
            try:
                response = requests.post(f"{suno_api_base}/generate/lyrics/", data=json.dumps(payload), timeout=(5, 30))
                if response.status_code != 200:
                    raise Exception(f"status_code is not ok, status_code={response.status_code}")
                logger.debug(f"[Nicesuno] _suno_generate_lyrics, response={response.text}")
                return response.json()
            except Exception as e:
                logger.error(f"[Nicesuno] _suno_generate_lyrics failed, suno_lyric_prompt={suno_lyric_prompt}, error={e}")
                retry_count -= 1
                time.sleep(5)

    # 获取歌词信息
    def _suno_get_lyrics(self, suno_api_base, lid, retry_count=3):
        while retry_count >= 0:
            try:
                response = requests.get(f"{suno_api_base}/lyrics/{lid}", timeout=(5, 30))
                if response.status_code != 200:
                    raise Exception(f"status_code is not ok, status_code={response.status_code}")
                logger.debug(f"[Nicesuno] _suno_get_lyrics, response={response.text}")
                return response.json()
            except Exception as e:
                logger.error(f"[Nicesuno] _suno_get_lyrics failed, lid={lid}, error={e}")
                retry_count -= 1
                time.sleep(5)

    # 下载文件
    def _download_file(self, file_url, file_path, retry_count=3):
        while retry_count >= 0:
            try:
                response = requests.get(file_url, allow_redirects=True, stream=True)
                if response.status_code != 200:
                    raise Exception(f"[Nicesuno] 文件下载失败，file_url={file_url}, status_code={response.status_code}")
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
            except Exception as e:
                logger.error(f"[Nicesuno] 文件下载失败，file_url={file_url}, error={e}")
                retry_count -= 1
                time.sleep(5)
            else:
                break

    # 检查是否包含创作音乐的前缀
    def _check_prefix(self, content, prefix_list):
        if not prefix_list:
            return None
        for prefix in prefix_list:
            if content.startswith(prefix):
                return prefix
        return None

    # 查找可用的Suno账户
    def search_account(self, create_music=True):
        self.reset_account_info()
        available_account = ""
        # 查找是否有余额充足+上次正常的账号，使用最先找到的正常帐号
        for account, account_info in self.accounts_info.items():
            if create_music and account_info["used_count"] < account_info["daily_limit"] and account_info["last_status"] in ["ok", ""] \
                    or not create_music and account_info["last_status"] in ["ok", "Insufficient credits.", ""]:
                available_account = account
                break
        if available_account:
            logger.debug(f"[Nicesuno] 账号[{available_account}]余额充足且上次正常，停止查找！账号信息={self.accounts_info[available_account]}")
            return available_account
        # 查找是否有余额充足+上次异常的账号，使用最久未使用的异常帐号
        oldest_last_time = None
        for account, account_info in self.accounts_info.items():
            if create_music and account_info["used_count"] < account_info["daily_limit"] or not create_music:
                if not oldest_last_time or account_info["last_time"] < oldest_last_time:
                    oldest_last_time = account_info["last_time"]
                    available_account = account
        if available_account:
            logger.debug(f"[Nicesuno] 账号[{available_account}]余额充足但上次异常，停止查找！账号信息={self.accounts_info[available_account]}")
            return available_account
        # 没有找到可用账号
        logger.warning(f"[Nicesuno] 没有找到可用账号，accounts_info={self.accounts_info}")
        return available_account

    # 查看Suno账户信息
    def view_account_info(self):
        self.reset_account_info()
        account_info_str = ""
        try:
            for account, account_info in self.accounts_info.items():
                account_tidy = account.split(':')[2]
                used_count = account_info["used_count"]
                daily_limit = account_info["daily_limit"]
                last_time_tidy = account_info['last_time'].strftime('%Y/%m/%d %H:%M')
                last_status = account_info["last_status"]
                account_info_str +=f"{account_tidy}\t{used_count}/{daily_limit}\t{last_time_tidy}\t{last_status}\n"
        except Exception as e:
            logger.info(f"[Nicesuno] 查询Suno账户信息失败，error={e}")
            account_info_str = "查询Suno账户信息失败！"
        return account_info_str.strip()

    # 恢复创作音乐的额度信息
    def reset_account_info(self):
        recover_time = datetime.now().replace(hour=11, minute=0, second=5, microsecond=0)
        for _, account_info in self.accounts_info.items():
            if account_info["last_time"] < recover_time:
                account_info["used_count"] = 0
                if account_info["last_status"] == "Insufficient credits.":
                    account_info["last_status"] = "ok"

    # 帮助文档
    def get_help_text(self, verbose=False, **kwargs):
        help_text = "使用Suno创作音乐。"
        if not verbose:
            return help_text
        return help_text + "\n1.创作声乐\n用法：唱/演唱<提示词>\n示例：唱明天会更好。\n\n2.创作器乐\n用法：演奏<提示词>\n示例：演奏明天会更好。\n\n3.创作歌词\n用法：写歌/作词<提示词>\n示例：写歌明天会更好。\n\n4.自定义模式\n用法：\n唱/演唱/演奏\n标题: <标题>\n风格: <风格1> <风格2> ...\n<歌词>\n备注：前三行必须为创作前缀、标题、风格，<标题><风格><歌词>三个值可以为空，但<风格><歌词>不可同时为空！"
