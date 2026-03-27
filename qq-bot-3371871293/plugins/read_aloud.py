import os
from datetime import datetime

import httpx
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from .shared import TMP_AUDIO_DIR

read_cmd = on_command("朗读", aliases={"念", "语音复读", "read"}, priority=5, block=True)


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
