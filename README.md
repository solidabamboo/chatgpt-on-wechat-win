# 简介

> [chatgpt-on-wechat](https://github.com/zhayujie/chatgpt-on-wechat)（简称CoW）项目是基于大模型的智能对话机器人，支持微信公众号、企业微信应用、飞书、钉钉接入，可选择GPT3.5/GPT4.0/Claude/Gemini/LinkAI/ChatGLM/KIMI/文心一言/讯飞星火/通义千问/LinkAI，能处理文本、语音和图片，通过插件访问操作系统和互联网等外部资源，支持基于自有知识库定制企业AI应用。

> [chatgpt-on-wechat-win](https://github.com/Tishon1532/chatgpt-on-wechat-win)项目是chatgpt-on-wechat的PC windows端个人微信版，基于[WeChat-AIChatbot-WinOnly](https://github.com/chazzjimel/WeChat-AIChatbot-WinOnly)，由于跃迁大佬停更，所以备份一下，同时丰富一下原ntchat消息通道监听类型，方便开发对应类型插件。

> 本项目基于新版本的chatgpt-on-wechat项目，同时借鉴了chatgpt-on-wechat-win项目的ntchat消息通道，是一个可以使用Windows微信的AI聊天机器人。

最新版本支持的功能如下：

- [x] chatgpt-on-wechat的功能：基础对话、语音能力、图像能力、丰富插件等
- [x] 发送消息：文本/图片/视频/文件/群聊@/链接卡片/GIF/XML
- [x] 接收消息：几乎涵盖所有消息类型
- [x] 其他功能：同意加好友请求/创建群/添加好友入群/邀请好友入群/删除群成员/修改群名/修改群公告
- [ ] 不支持：无法发送语音条信息(只能发送音频文件)

备注：

1. Windows的个微消息通道，依赖[ntchat项目](https://github.com/billyplus/ntchat)，最高支持Python 3.10环境，以及WeChat3.6.0.18版本。
2. 2024年4月开始微信限制低版本登录，为提高本项目使用门槛，故不提供低版本登录解决方案，请自行解决！

## 声明

1. 本项目遵循 [MIT开源协议](/LICENSE)，仅用于技术研究和学习，使用本项目时需遵守所在地法律法规、相关政策以及企业章程，禁止用于任何违法或侵犯他人权益的行为
2. 境内使用该项目时，请使用国内厂商的大模型服务，并进行必要的内容安全审核及过滤
3. 本项目主要接入协同办公平台，推荐使用公众号、企微自建应用、钉钉、飞书等接入通道，其他通道为历史产物已不维护
4. 任何个人、团队和企业，无论以何种方式使用该项目、对何对象提供服务，所产生的一切后果，本项目均不承担任何责任

# 🏷 更新日志

>**2024.07.02：** 同步[1.6.7版本](https://github.com/zhayujie/chatgpt-on-wechat/releases/tag/1.6.7)chatgpt-on-wechat，同时添加ntchat消息通道。

# 🚀 快速开始

这里仅提供Windows + ntchat消息通道的配置说明，其他平台请参考[chatgpt-on-wechat项目搭建文档](https://docs.link-ai.tech/cow/quick-start)

## 一、准备

### 1.安装指定版本Windows微信

下载并安装指定版本微信：[WeChatSetup-3.6.0.18.exe](https://github.com/tom-snow/wechat-windows-versions/releases/download/v3.6.0.18/WeChatSetup-3.6.0.18.exe)

### 2.扫码登录Windows微信

备注：2024年4月开始微信限制低版本登录，为提高本项目使用门槛，故不提供低版本登录解决方案，请自行解决！

### 3.安装Python运行环境

ntchat项目最高支持Python 3.10环境，建议Python版本在3.7.1~3.10之间，可以使用后面的链接下载Python3.9.13：[python-3.9.13-amd64.exe](https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe)

### 4.克隆项目代码

```bash
git clone https://github.com/solidabamboo/chatgpt-on-wechat-win.git
cd chatgpt-on-wechat-win/
```

### 5.安装核心依赖 (必选)
```bash
pip3 install -r requirements.txt
```

### 6.拓展依赖 (可选，建议安装)

```bash
pip3 install -r requirements-optional.txt
```
> 如果某项依赖安装失败可注释掉对应的行再继续

## 二、配置

配置文件的模板在根目录的`config-template.json`中，需复制该模板创建最终生效的 `config.json` 文件：

```bash
cp config-template.json config.json
```

然后在`config.json`中填入配置，以下是对默认配置的说明，可根据需要进行自定义修改（注意实际使用时请去掉注释，保证JSON格式的完整）：

```bash
# config.json文件内容示例
{
  "model": "gpt-3.5-turbo",                                   # 模型名称, 支持 gpt-3.5-turbo, gpt-4, gpt-4-turbo, wenxin, xunfei, glm-4, claude-3-haiku, moonshot
  "open_ai_api_key": "YOUR API KEY",                          # 如果使用openAI模型则填入上面创建的 OpenAI API KEY
  "proxy": "",                                                # 代理客户端的ip和端口，国内环境开启代理的需要填写该项，如 "127.0.0.1:7890"
  "channel_type": "ntchat",                                   # 消息通道类型，默认ntchat
  "single_chat_prefix": ["bot", "@bot"],                      # 私聊时文本需要包含该前缀才能触发机器人回复
  "single_chat_reply_prefix": "[bot] ",                       # 私聊时自动回复的前缀，用于区分真人
  "group_chat_prefix": ["@bot"],                              # 群聊时包含该前缀则会触发机器人回复
  "group_name_white_list": ["ChatGPT测试群", "ChatGPT测试群2"], # 开启自动回复的群名称列表
  "group_chat_in_one_session": ["ChatGPT测试群"],              # 支持会话上下文共享的群名称  
  "image_create_prefix": ["画", "看", "找"],                   # 开启图片回复的前缀
  "conversation_max_tokens": 1000,                            # 支持上下文记忆的最多字符数
  "speech_recognition": false,                                # 是否开启语音识别
  "group_speech_recognition": false,                          # 是否开启群组语音识别
  "voice_reply_voice": false,                                 # 是否使用语音回复语音
  "character_desc": "你是基于大语言模型的AI智能助手，旨在回答并解决人们的任何问题，并且可以使用多种语言与人交流。",  # 人格描述
  # 订阅消息，公众号和企业微信channel中请填写，当被订阅时会自动回复，可使用特殊占位符。目前支持的占位符有{trigger_prefix}，在程序中它会自动替换成bot的触发词。
  "subscribe_msg": "感谢您的关注！\n这里是ChatGPT，可以自由对话。\n支持语音对话。\n支持图片输出，画字开头的消息将按要求创作图片。\n支持角色扮演和文字冒险等丰富插件。\n输入{trigger_prefix}#help 查看详细指令。",
  "use_linkai": false,                                        # 是否使用LinkAI接口，默认关闭，开启后可国内访问，使用知识库和MJ
  "linkai_api_key": "",                                       # LinkAI Api Key
  "linkai_app_code": ""                                       # LinkAI 应用或工作流code
}
```

**配置说明：**

**1.个人聊天**

+ 个人聊天中，需要以 "bot"或"@bot" 为开头的内容触发机器人，对应配置项 `single_chat_prefix` (如果不需要以前缀触发可以填写  `"single_chat_prefix": [""]`)
+ 机器人回复的内容会以 "[bot] " 作为前缀， 以区分真人，对应的配置项为 `single_chat_reply_prefix` (如果不需要前缀可以填写 `"single_chat_reply_prefix": ""`)

**2.群组聊天**

+ 群组聊天中，群名称需配置在 `group_name_white_list ` 中才能开启群聊自动回复。如果想对所有群聊生效，可以直接填写 `"group_name_white_list": ["ALL_GROUP"]`
+ 默认只要被人 @ 就会触发机器人自动回复；另外群聊天中只要检测到以 "@bot" 开头的内容，同样会自动回复（方便自己触发），这对应配置项 `group_chat_prefix`
+ 可选配置: `group_name_keyword_white_list`配置项支持模糊匹配群名称，`group_chat_keyword`配置项则支持模糊匹配群消息内容，用法与上述两个配置项相同。（Contributed by [evolay](https://github.com/evolay))
+ `group_chat_in_one_session`：使群聊共享一个会话上下文，配置 `["ALL_GROUP"]` 则作用于所有群聊

**3.语音识别**

+ 添加 `"speech_recognition": true` 将开启语音识别，默认使用openai的whisper模型识别为文字，同时以文字回复，该参数仅支持私聊 (注意由于语音消息无法匹配前缀，一旦开启将对所有语音自动回复，支持语音触发画图)；
+ 添加 `"group_speech_recognition": true` 将开启群组语音识别，默认使用openai的whisper模型识别为文字，同时以文字回复，参数仅支持群聊 (会匹配group_chat_prefix和group_chat_keyword, 支持语音触发画图)；
+ 添加 `"voice_reply_voice": true` 将开启语音回复语音（同时作用于私聊和群聊）

**4.其他配置**

+ `channel_type`: 消息通道类型，支持`wx`(itchat), `wxy`(wechaty，有bug), `ntchat`(基于ntchat项目), `terminal`(终端，测试使用), `wechatmp`, `wechatmp_service`, `wechatcom_app`, `wework`, `weworktop`, `feishu`, `dingtalk`，这里默认为`ntchat`
+ `model`: 模型名称，目前支持 `gpt-3.5-turbo`, `gpt-4o`, `gpt-4-turbo`, `gpt-4`, `wenxin` , `claude` , `gemini`, `glm-4`,  `xunfei`, `moonshot`等，全部模型名称参考[common/const.py](https://github.com/zhayujie/chatgpt-on-wechat/blob/master/common/const.py)文件
+ `temperature`,`frequency_penalty`,`presence_penalty`: Chat API接口参数，详情参考[OpenAI官方文档。](https://platform.openai.com/docs/api-reference/chat)
+ `proxy`：由于目前 `openai` 接口国内无法访问，需配置代理客户端的地址，详情参考  [#351](https://github.com/zhayujie/chatgpt-on-wechat/issues/351)
+ 对于图像生成，在满足个人或群组触发条件外，还需要额外的关键词前缀来触发，对应配置 `image_create_prefix `
+ 关于OpenAI对话及图片接口的参数配置（内容自由度、回复字数限制、图片大小等），可以参考 [对话接口](https://beta.openai.com/docs/api-reference/completions) 和 [图像接口](https://beta.openai.com/docs/api-reference/completions)  文档，在[`config.py`](https://github.com/zhayujie/chatgpt-on-wechat/blob/master/config.py)中检查哪些参数在本项目中是可配置的。
+ `conversation_max_tokens`：表示能够记忆的上下文最大字数（一问一答为一组对话，如果累积的对话字数超出限制，就会优先移除最早的一组对话）
+ `rate_limit_chatgpt`，`rate_limit_dalle`：每分钟最高问答速率、画图速率，超速后排队按序处理。
+ `clear_memory_commands`: 对话内指令，主动清空前文记忆，字符串数组可自定义指令别名。
+ `character_desc` 配置中保存着你对机器人说的一段话，他会记住这段话并作为他的设定，你可以为他定制任何人格      (关于会话上下文的更多内容参考该 [issue](https://github.com/zhayujie/chatgpt-on-wechat/issues/43))
+ `subscribe_msg`：订阅消息，公众号和企业微信channel中请填写，当被订阅时会自动回复， 可使用特殊占位符。目前支持的占位符有{trigger_prefix}，在程序中它会自动替换成bot的触发词。

**5.LinkAI配置 (可选)**

+ `use_linkai`: 是否使用LinkAI接口，开启后可国内访问，使用知识库和 `Midjourney` 绘画, 参考 [文档](https://link-ai.tech/platform/link-app/wechat)
+ `linkai_api_key`: LinkAI Api Key，可在 [控制台](https://link-ai.tech/console/interface) 创建
+ `linkai_app_code`: LinkAI 应用或工作流的code，选填

**本说明文档可能会未及时更新，当前所有可选的配置项均在该[`config.py`](https://github.com/solidabamboo/chatgpt-on-wechat-win/blob/master/config.py)中列出。**

## 三、运行

微信登录成功、依赖安装成功、配置修改完成之后，直接在项目根目录下执行：

```bash
chcp 65001
python app.py
```

# 🔎 常见问题

FAQs： <https://github.com/zhayujie/chatgpt-on-wechat/wiki/FAQs>