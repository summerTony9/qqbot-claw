import os
import re
from datetime import datetime
from pathlib import Path

import httpx
from loguru import logger
from nonebot import on_command, on_keyword, on_message, require
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

help_cmd = on_command("帮助", aliases={"help", "菜单"}, priority=5, block=True)
ping_cmd = on_command("ping", priority=5, block=True)
time_cmd = on_command("时间", aliases={"time"}, priority=5, block=True)
echo_cmd = on_command("说", aliases={"echo"}, priority=5, block=True)
image_cmd = on_command("生图", aliases={"画图", "draw"}, priority=5, block=True)
i2i_cmd = on_command("图生图", aliases={"垫图", "改图"}, priority=5, block=True)
read_cmd = on_command("朗读", aliases={"念", "语音复读", "read"}, priority=5, block=True)
hello = on_keyword({"你好", "在吗", "机器人"}, priority=20, block=False)
image_cache = on_message(priority=99, block=False)

BASE_DIR = Path(__file__).resolve().parent.parent
TMP_AUDIO_DIR = BASE_DIR / "tmp_audio"
TMP_AUDIO_DIR.mkdir(exist_ok=True)
IMAGE_SEGMENT_CACHE: dict[str, str] = {}
PENDING_I2I: dict[str, dict[str, str]] = {}


def _pick_image_url_from_segments(segments) -> str:
    for seg in segments or []:
        seg_type = getattr(seg, "type", None)
        seg_data = getattr(seg, "data", None)
        if seg_type is None and isinstance(seg, dict):
            seg_type = seg.get("type")
            seg_data = seg.get("data", {})
        seg_data = seg_data or {}
        if seg_type == "image":
            image_url = seg_data.get("url") or seg_data.get("file") or ""
            if image_url:
                return image_url
    return ""


async def _extract_image_url(bot: Bot, event: Event, args: Message) -> str:
    # 1) 先读引用消息里的图片（优先查本地缓存）
    try:
        reply_id = None
        for seg in event.get_message():
            if seg.type == "reply":
                reply_id = seg.data.get("id")
                if reply_id:
                    break

        if reply_id:
            cached = IMAGE_SEGMENT_CACHE.get(str(reply_id), "")
            if cached:
                logger.info(f"[i2i-debug] hit image cache for reply_id={reply_id}")
                return cached

            replied = await bot.get_msg(message_id=reply_id)
            logger.info(f"[i2i-debug] reply_id={reply_id} replied={replied}")
            replied_message = replied.get("message") or []
            image_url = _pick_image_url_from_segments(replied_message)
            if image_url:
                IMAGE_SEGMENT_CACHE[str(reply_id)] = image_url
                return image_url
    except Exception as e:
        logger.warning(f"[i2i-debug] get replied message failed: {e}")

    # 2) 再读当前命令消息里直接附带的图片
    image_url = _pick_image_url_from_segments(args)
    if image_url:
        return image_url

    # 3) 最后从文本里抠链接
    plain_text = args.extract_plain_text().strip()
    m = re.search(r"https?://\S+", plain_text)
    return m.group(0) if m else ""


async def _run_i2i_from_image_url(image_url: str, prompt: str):
    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        return False, "还没配置 MiniMax API Key。"

    model = os.getenv("MINIMAX_IMAGE_MODEL", "image-01").strip() or "image-01"
    aspect_ratio = os.getenv("MINIMAX_IMAGE_ASPECT_RATIO", "1:1").strip() or "1:1"
    reference_type = os.getenv("MINIMAX_I2I_REFERENCE_TYPE", "character").strip() or "character"
    try:
        image_count = int(os.getenv("MINIMAX_IMAGE_COUNT", "1").strip() or "1")
    except ValueError:
        image_count = 1
    image_count = max(1, min(image_count, 4))

    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "subject_reference": [
            {
                "type": reference_type,
                "image_file": image_url,
            }
        ],
        "response_format": "url",
        "n": image_count,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.minimaxi.com/v1/image_generation",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500] if e.response is not None else str(e)
        return False, f"图生图失败，接口返回错误：{detail}"
    except Exception as e:
        return False, f"图生图失败：{e}"

    status_code = (((data or {}).get("base_resp") or {}).get("status_code"))
    if status_code not in (0, None):
        status_msg = (((data or {}).get("base_resp") or {}).get("status_msg")) or "未知错误"
        return False, f"图生图失败：{status_msg}"

    image_urls = (((data or {}).get("data") or {}).get("image_urls")) or []
    if not image_urls:
        return False, f"图生图失败，未拿到图片地址。原始返回：{str(data)[:500]}"

    msg = Message()
    msg.append(MessageSegment.text(f"改图提示词：{prompt}\n"))
    for url in image_urls:
        msg.append(MessageSegment.image(url))
    return True, msg


@image_cache.handle()
async def _cache_image(bot: Bot, event: Event):
    try:
        message_id = getattr(event, "message_id", None)
        if message_id is None:
            return
        image_url = _pick_image_url_from_segments(event.get_message())
        if image_url:
            IMAGE_SEGMENT_CACHE[str(message_id)] = image_url
            # 控制缓存大小，避免一直涨
            if len(IMAGE_SEGMENT_CACHE) > 500:
                for key in list(IMAGE_SEGMENT_CACHE.keys())[:100]:
                    IMAGE_SEGMENT_CACHE.pop(key, None)

            session_key = f"{event.user_id}:{getattr(event, 'group_id', 'private')}"
            pending = PENDING_I2I.pop(session_key, None)
            if pending:
                await bot.send(event, "收到图片，开始改图……")
                ok, result = await _run_i2i_from_image_url(image_url, pending["prompt"])
                await bot.send(event, result)
    except Exception as e:
        logger.warning(f"[i2i-debug] cache/pending handler failed: {e}")


@help_cmd.handle()
async def _help():
    await help_cmd.finish(
        "可用指令：\n"
        "1. 帮助 / help / 菜单\n"
        "2. ping\n"
        "3. 时间\n"
        "4. 说 <内容>\n"
        "5. 朗读 <内容>\n"
        "6. 生图 <提示词>\n"
        "7. 图生图 <提示词>（可先发命令，再单独发图）\n"
        "\n"
        "示例：\n"
        "说 今天天气不错\n"
        "朗读 你好\n"
        "生图 一只戴墨镜的橘猫\n"
        "图生图 改成宫崎骏风格\n"
        "然后下一条单独发图"
    )


@ping_cmd.handle()
async def _ping():
    await ping_cmd.finish("pong")


@time_cmd.handle()
async def _time():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await time_cmd.finish(f"现在时间：{now}")


@echo_cmd.handle()
async def _echo(args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    if not text:
        await echo_cmd.finish("你要我说什么？用法：说 你好")
    await echo_cmd.finish(text)


@image_cmd.handle()
async def _image(args: Message = CommandArg()):
    prompt = args.extract_plain_text().strip()
    if not prompt:
        await image_cmd.finish("用法：生图 一个戴墨镜的橘猫，电影感，写实风")

    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        await image_cmd.finish("还没配置 MiniMax API Key。")

    model = os.getenv("MINIMAX_IMAGE_MODEL", "image-01").strip() or "image-01"
    aspect_ratio = os.getenv("MINIMAX_IMAGE_ASPECT_RATIO", "1:1").strip() or "1:1"
    try:
        image_count = int(os.getenv("MINIMAX_IMAGE_COUNT", "1").strip() or "1")
    except ValueError:
        image_count = 1
    image_count = max(1, min(image_count, 4))

    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "response_format": "url",
        "n": image_count,
        "prompt_optimizer": True,
    }

    await image_cmd.send("收到，开始画……")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.minimaxi.com/v1/image_generation",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500] if e.response is not None else str(e)
        await image_cmd.finish(f"生图失败，接口返回错误：{detail}")
    except Exception as e:
        await image_cmd.finish(f"生图失败：{e}")

    status_code = (((data or {}).get("base_resp") or {}).get("status_code"))
    if status_code not in (0, None):
        status_msg = (((data or {}).get("base_resp") or {}).get("status_msg")) or "未知错误"
        await image_cmd.finish(f"生图失败：{status_msg}")

    image_urls = (((data or {}).get("data") or {}).get("image_urls")) or []
    if not image_urls:
        await image_cmd.finish(f"生图失败，未拿到图片地址。原始返回：{str(data)[:500]}")

    msg = Message()
    msg.append(MessageSegment.text(f"提示词：{prompt}\n"))
    for url in image_urls:
        msg.append(MessageSegment.image(url))
    await image_cmd.finish(msg)


@i2i_cmd.handle()
async def _i2i(bot: Bot, event: Event, args: Message = CommandArg()):
    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        await i2i_cmd.finish("还没配置 MiniMax API Key。")

    image_url = await _extract_image_url(bot, event, args)
    plain_text = args.extract_plain_text().strip()
    prompt = plain_text

    # 支持：图生图 图片链接 | 提示词
    if "|" in plain_text:
        left, right = plain_text.split("|", 1)
        left = left.strip()
        right = right.strip()
        if re.match(r"^https?://", left):
            image_url = left
        prompt = right
    elif image_url:
        prompt = re.sub(r"https?://\S+", "", plain_text).strip()

    if not prompt:
        await i2i_cmd.finish("缺少提示词。用法：图生图 改成赛博朋克夜景海报")

    if not image_url:
        session_key = f"{event.user_id}:{getattr(event, 'group_id', 'private')}"
        PENDING_I2I[session_key] = {"prompt": prompt}
        await i2i_cmd.finish("好，你下一条单独发图片给我，我用这张图来改。")

    await i2i_cmd.send("收到，开始改图……")
    ok, result = await _run_i2i_from_image_url(image_url, prompt)
    await i2i_cmd.finish(result)


@read_cmd.handle()
async def _read(args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    if not text:
        await read_cmd.finish("用法：朗读 你好，今天过得怎么样")

    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        await read_cmd.finish("还没配置 MiniMax API Key。")

    model = os.getenv("MINIMAX_TTS_MODEL", "speech-2.8-hd").strip() or "speech-2.8-hd"
    voice_id = os.getenv("MINIMAX_TTS_VOICE_ID", "male-qn-qingse").strip() or "male-qn-qingse"
    emotion = os.getenv("MINIMAX_TTS_EMOTION", "happy").strip() or "happy"

    payload = {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": emotion,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
        },
    }

    await read_cmd.send("收到，我念一下……")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.minimaxi.com/v1/t2a_v2",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500] if e.response is not None else str(e)
        await read_cmd.finish(f"朗读失败，接口返回错误：{detail}")
    except Exception as e:
        await read_cmd.finish(f"朗读失败：{e}")

    status_code = (((data or {}).get("base_resp") or {}).get("status_code"))
    if status_code not in (0, None):
        status_msg = (((data or {}).get("base_resp") or {}).get("status_msg")) or "未知错误"
        await read_cmd.finish(f"朗读失败：{status_msg}")

    audio_hex = (((data or {}).get("data") or {}).get("audio")) or ""
    if not audio_hex:
        await read_cmd.finish(f"朗读失败，未拿到音频数据。原始返回：{str(data)[:500]}")

    try:
        audio_bytes = bytes.fromhex(audio_hex)
        filename = TMP_AUDIO_DIR / f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.mp3"
        filename.write_bytes(audio_bytes)
    except Exception as e:
        await read_cmd.finish(f"朗读失败，音频写入异常：{e}")

    msg = Message()
    msg.append(MessageSegment.record(f"file://{filename}"))
    msg.append(MessageSegment.text(f"\n{text}"))
    await read_cmd.finish(msg)


@hello.handle()
async def _hello(bot: Bot, event: Event):
    # 轻量关键词响应，避免打断聊天
    if "你好" in event.get_plaintext():
        await hello.finish("你好，我在。发“帮助”看命令。")


# 定时任务能力已接入；如需启用，请按你的发送对象再补具体任务。
