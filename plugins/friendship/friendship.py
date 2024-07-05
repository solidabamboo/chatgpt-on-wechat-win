# encoding:utf-8
from typing import Any

import json
import os

import plugins
from bridge.bridge import Bridge
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common import const
from common.log import logger
from config import conf
from plugins import *


class FriendshipChat:
    sessionid: Any

    def __init__(self, bot, sessionid, character_desc):
        self.bot = bot
        self.sessionid = sessionid
        self.character_desc = character_desc
        self.bot.sessions.build_session(self.sessionid, system_prompt=self.character_desc)

    def chat(self, content):
        session = self.bot.sessions.build_session(self.sessionid)
        if session.system_prompt != self.character_desc:  # 目前没有触发session过期事件，这里先简单判断，然后重置
            session.set_system_prompt(self.character_desc)
        new_content = content  # 暂时没有修改content
        return new_content


@plugins.register(
    name="Friendship",
    desire_priority=-10,
    namecn="友好关系",
    desc="我们的友谊天长地久。",
    version="1.1",
    author="空心菜",
)
class Friendship(Plugin):
    def __init__(self):
        super().__init__()
        try:
            # btype = Bridge().get_bot_type("chat")
            # if btype not in [const.OPEN_AI, const.CHATGPT, const.CHATGPTONAZURE, const.LINKAI]:
            #     return
            # 加载配置
            self.config = super().load_config()
            if not self.config:
                raise Exception("[Friendship] config.json not found")
            self.friendship = dict()
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
            logger.info("[Friendship] inited")
        except Exception as err:
            logger.warn("[Friendship] init failed, ignore.")
            raise err

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return

        logger.debug("[Friendship] on_handle_context.")
        sessionid = e_context["context"]["session_id"]
        if sessionid not in self.friendship.keys():
            nick_name, character_desc = self.get_character_desc(sessionid)
            if character_desc:
                logger.debug(f"[Friendship] Welcome {nick_name}, I love you!")
            else:
                logger.debug("[Friendship] Welcome stranger, you are ignored!")
                self.friendship[sessionid] = None
                return
            bot = Bridge().get_bot("chat")
            self.friendship[sessionid] = FriendshipChat(
                bot,
                sessionid,
                character_desc
            )
        elif not self.friendship[sessionid]:
            return
        content = e_context["context"].content
        new_content = self.friendship[sessionid].chat(content)
        e_context["context"].content = new_content
        e_context.action = EventAction.BREAK

    def get_character_desc(self, session_id):
        for record in self.config:
            if session_id in record["session_ids"]:
                nick_name = record["nick_name"]
                character_desc = record["character_desc"].format(nick_name=nick_name)
                return nick_name, character_desc
        return None, None

    def get_help_text(self, verbose=False, **kwargs):
        help_text = "我们的友谊天长地久。\n"
        return help_text
