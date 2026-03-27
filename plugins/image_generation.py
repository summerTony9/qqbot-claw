import os

import httpx
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

image_cmd = on_command("生图", aliases={"画图", "draw"}, priority=5, block=True)


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
