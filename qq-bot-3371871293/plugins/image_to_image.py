import os
import re

import httpx
from loguru import logger
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.params import CommandArg

from .shared import IMAGE_SEGMENT_CACHE, PENDING_I2I, pick_image_url_from_segments

i2i_cmd = on_command("图生图", aliases={"垫图", "改图"}, priority=5, block=True)


async def extract_image_url(bot: Bot, event: Event, args: Message) -> str:
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
            image_url = pick_image_url_from_segments(replied_message)
            if image_url:
                IMAGE_SEGMENT_CACHE[str(reply_id)] = image_url
                return image_url
    except Exception as e:
        logger.warning(f"[i2i-debug] get replied message failed: {e}")

    image_url = pick_image_url_from_segments(args)
    if image_url:
        return image_url

    plain_text = args.extract_plain_text().strip()
    m = re.search(r"https?://\S+", plain_text)
    return m.group(0) if m else ""


async def run_i2i_from_image_url(image_url: str, prompt: str):
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
        "prompt_optimizer": True,
    }

    logger.info(f"[i2i-debug] prompt={prompt!r} image_url={image_url[:120]}")

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


@i2i_cmd.handle()
async def _i2i(bot: Bot, event: Event, args: Message = CommandArg()):
    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        await i2i_cmd.finish("还没配置 MiniMax API Key。")

    image_url = await extract_image_url(bot, event, args)
    plain_text = args.extract_plain_text().strip()
    prompt = plain_text

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
    ok, result = await run_i2i_from_image_url(image_url, prompt)
    await i2i_cmd.finish(result)
