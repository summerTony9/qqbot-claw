import json
import os
import random
import re
from collections import deque
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
GROUP_CONTEXTS: dict[str, deque] = {}
GROUP_TRIGGER_COUNTER: dict[str, int] = {}
GROUP_NEXT_TRIGGER: dict[str, int] = {}
SEEN_BILIBILI_URLS: deque = deque(maxlen=200)


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


def _extract_bilibili_url(text: str) -> str:
    m = re.search(r"https?://(?:www\.)?(?:bilibili\.com/video/[A-Za-z0-9]+|b23\.tv/[A-Za-z0-9]+)\S*", text or "")
    if not m:
        return ""
    url = m.group(0).strip()
    url = re.sub(r'["\\,，。！？；：\)\]\}>]+$', '', url)
    return url


def _extract_bilibili_url_from_event(event: Event) -> str:
    plain = event.get_plaintext().strip() if hasattr(event, "get_plaintext") else ""
    url = _extract_bilibili_url(plain)
    if url:
        logger.info(f"[bili-roaster] found url in plain text: {url}")
        return url

    for seg in event.get_message():
        if seg.type == "json":
            raw = seg.data.get("data", "") if hasattr(seg, "data") else ""
            logger.info(f"[bili-roaster] json card snippet: {str(raw)[:600]}")
            url = _extract_bilibili_url(raw)
            if url:
                logger.info(f"[bili-roaster] found url in json raw: {url}")
                return url
            try:
                obj = json.loads(raw)
                blob = json.dumps(obj, ensure_ascii=False)
                url = _extract_bilibili_url(blob)
                if url:
                    logger.info(f"[bili-roaster] found url in parsed json: {url}")
                    return url
            except Exception as e:
                logger.warning(f"[bili-roaster] json parse failed: {e}")
    logger.info("[bili-roaster] no bilibili url found in event")
    return ""


def _extract_bilibili_card_meta(event: Event) -> dict:
    meta = {"title": "", "desc": "", "jump_url": "", "raw": ""}
    for seg in event.get_message():
        if seg.type != "json":
            continue
        raw = seg.data.get("data", "") if hasattr(seg, "data") else ""
        meta["raw"] = str(raw)[:1000]
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        blob = json.dumps(obj, ensure_ascii=False)
        meta["jump_url"] = _extract_bilibili_url(blob) or meta["jump_url"]

        candidates = []
        for key in ["prompt", "desc", "description", "title", "headline", "news"]:
            val = obj.get(key)
            if isinstance(val, str):
                candidates.append(val)

        detail = ((obj.get("meta") or {}).get("detail_1") or {})
        for key in ["desc", "descText", "title", "qqdocurl", "jumpUrl", "url"]:
            val = detail.get(key)
            if isinstance(val, str):
                candidates.append(val)

        news = detail.get("news") or {}
        if isinstance(news, dict):
            for key in ["title", "desc", "summary", "tag"]:
                val = news.get(key)
                if isinstance(val, str):
                    candidates.append(val)

        cleaned = [c.strip() for c in candidates if isinstance(c, str) and c.strip()]
        if cleaned:
            meta["title"] = cleaned[0]
            if len(cleaned) > 1:
                meta["desc"] = cleaned[1]
        break
    logger.info(f"[bili-roaster] card meta: {meta}")
    return meta


def _format_message_brief(event: Event) -> str:
    user_id = getattr(event, "user_id", "unknown")
    text = event.get_plaintext().strip() if hasattr(event, "get_plaintext") else ""
    if not text:
        text = str(event.get_message())[:120]
    return f"[{user_id}] {text}"


def _ensure_group_state(group_id: str):
    context_size = max(8, min(int(os.getenv("GROUP_ROASTER_CONTEXT_SIZE", "15") or "15"), 30))
    if group_id not in GROUP_CONTEXTS:
        GROUP_CONTEXTS[group_id] = deque(maxlen=context_size)
    if group_id not in GROUP_TRIGGER_COUNTER:
        GROUP_TRIGGER_COUNTER[group_id] = 0
    if group_id not in GROUP_NEXT_TRIGGER:
        min_trigger = max(3, int(os.getenv("GROUP_ROASTER_MIN_TRIGGER", "5") or "5"))
        max_trigger = max(min_trigger, int(os.getenv("GROUP_ROASTER_MAX_TRIGGER", "10") or "10"))
        GROUP_NEXT_TRIGGER[group_id] = random.randint(min_trigger, max_trigger)


def _json_from_httpx_response(resp: httpx.Response) -> dict:
    return json.loads(resp.content.decode("utf-8", errors="replace"))


async def _call_minimax_chat_with_reasoning(system_prompt: str, user_prompt: str) -> tuple[str, str]:
    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        return "", ""

    model = os.getenv("MINIMAX_CHAT_MODEL", "MiniMax-M2.7").strip() or "MiniMax-M2.7"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": 256,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.minimaxi.com/v1/text/chatcompletion_v2",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[minimax-chat] model={model} base_resp={data.get('base_resp')} choices_present={bool(data.get('choices'))}")

            choice = ((data or {}).get("choices") or [{}])[0]
            message = choice.get("message", {}) or {}
            reply = (message.get("content") or "").strip()
            reasoning = (message.get("reasoning_content") or "").strip()
            if not reply:
                reply = (((data or {}).get("reply") or {}).get("content") or "").strip()
            return reply.replace("\n", " ").strip()[:300], reasoning[:4000]
    except Exception as e:
        logger.warning(f"[minimax-chat] generate failed: {e}")
        return "", ""


async def _call_minimax_chat(system_prompt: str, user_prompt: str) -> str:
    reply, reasoning = await _call_minimax_chat_with_reasoning(system_prompt, user_prompt)
    if reply:
        return reply.replace("\n", " ").strip()[:300]
    if reasoning:
        logger.warning("[minimax-chat] empty content, retrying from reasoning")
        retry_reply, _ = await _call_minimax_chat_with_reasoning(
            "把给定分析压缩成1到3句最终回复。只输出最终回复，不要解释，不要思考过程，要像正常人在群里说话。",
            reasoning[-2200:],
        )
        return retry_reply.replace("\n", " ").strip()[:300] if retry_reply else ""
    return ""


async def _generate_group_roast_reply(target_text: str, context_lines: list[str]) -> str:
    system_prompt = (
        "你是QQ群里的暴躁贴吧老哥。你的任务是针对指定消息做一句具体回复。"
        "要求：1）必须结合最近群聊上下文和目标消息内容，不能泛泛而谈；"
        "2）语气暴躁、阴阳怪气、嘴硬、贴吧老哥味，但不要出现仇恨、歧视、暴力威胁、真实人身伤害鼓动；"
        "3）回复必须短，10-40字，像真实群友插话；"
        "4）不要解释自己，不要加引号，不要分点，不要写成AI腔；"
        "5）如果上下文不足，就抓住目标消息本身吐槽。"
    )
    user_prompt = (
        "最近群聊上下文：\n" + "\n".join(context_lines[-15:]) +
        "\n\n目标消息：\n" + target_text +
        "\n\n现在直接给出一句回复。"
    )
    return await _call_minimax_chat(system_prompt, user_prompt)


def _fetch_bilibili_metadata(url: str) -> dict:
    logger.info(f"[bili-roaster] fetching metadata via bilibili api: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/",
    }

    r = httpx.get(url, headers=headers, follow_redirects=True, timeout=20)
    final_url = str(r.url)
    logger.info(f"[bili-roaster] final url: {final_url}")
    m = re.search(r"/video/(BV[0-9A-Za-z]+)", final_url)
    if not m:
        raise ValueError(f"cannot extract bvid from url: {final_url}")
    bvid = m.group(1)

    api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    rr = httpx.get(api, headers=headers, timeout=20)
    rr.raise_for_status()
    data = _json_from_httpx_response(rr)
    if data.get("code") != 0:
        raise ValueError(f"bilibili api error: {data}")
    info = data.get("data") or {}
    owner = info.get("owner") or {}
    stat = info.get("stat") or {}
    cid = info.get("cid")

    subtitle_text = ""
    if cid:
        try:
            sub_api = f"https://api.bilibili.com/x/v2/dm/view?aid={info.get('aid')}&oid={cid}&type=1"
            sr = httpx.get(sub_api, headers=headers, timeout=20)
            sr.raise_for_status()
            sub_data = (_json_from_httpx_response(sr).get("data") or {})
            subtitles = ((sub_data.get("subtitle") or {}).get("subtitles")) or []
            zh_sub = None
            for item in subtitles:
                if item.get("lan") in ("ai-zh", "zh-CN", "zh-Hans", "zh"):
                    zh_sub = item
                    break
            if not zh_sub and subtitles:
                zh_sub = subtitles[0]
            if zh_sub and zh_sub.get("subtitle_url"):
                sub_url = zh_sub["subtitle_url"]
                if sub_url.startswith("//"):
                    sub_url = "https:" + sub_url
                elif sub_url.startswith("http://"):
                    sub_url = "https://" + sub_url[len("http://"):]
                tr = httpx.get(sub_url, headers=headers, timeout=20)
                tr.raise_for_status()
                body = _json_from_httpx_response(tr)
                pieces = []
                for item in body.get("body", [])[:80]:
                    content = (item.get("content") or "").strip()
                    if content:
                        pieces.append(content)
                subtitle_text = " ".join(pieces)[:4000]
        except Exception as e:
            logger.warning(f"[bili-roaster] subtitle fetch failed: {e}")

    hot_comments = []
    try:
        reply_candidates = [
            f"https://api.bilibili.com/x/v2/reply/main?oid={info.get('aid')}&type=1&mode=3&next=0&ps=5",
            f"https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid={info.get('aid')}&sort=2",
        ]
        for reply_api in reply_candidates:
            cr = httpx.get(reply_api, headers=headers, timeout=20)
            cr.raise_for_status()
            payload = _json_from_httpx_response(cr)
            if payload.get("code") != 0:
                logger.warning(f"[bili-roaster] comment api failed: {reply_api} -> {payload.get('code')}")
                continue
            cdata = ((payload.get("data") or {}).get("replies") or [])
            for item in cdata[:5]:
                message = (((item.get("content") or {}).get("message")) or "").strip()
                like = item.get("like", 0)
                if message:
                    hot_comments.append(f"{message}（赞{like}）")
            if hot_comments:
                break
    except Exception as e:
        logger.warning(f"[bili-roaster] hot comments fetch failed: {e}")

    logger.info(f"[bili-roaster] metadata title: {info.get('title', '')}")
    return {
        "title": info.get("title", ""),
        "description": info.get("desc", ""),
        "uploader": owner.get("name", ""),
        "tags": [],
        "duration": info.get("duration"),
        "view_count": stat.get("view"),
        "like_count": stat.get("like"),
        "dynamic": info.get("dynamic", ""),
        "argue_msg": ((info.get("argue_info") or {}).get("argue_msg")) or "",
        "subtitle_text": subtitle_text,
        "hot_comments": hot_comments,
        "webpage_url": final_url,
        "bvid": bvid,
    }


async def _generate_bilibili_roast_reply(url: str, context_lines: list[str], card_meta: dict | None = None) -> str:
    meta = {
        "title": (card_meta or {}).get("title", ""),
        "description": (card_meta or {}).get("desc", ""),
        "uploader": "",
        "tags": [],
        "dynamic": "",
        "argue_msg": "",
        "subtitle_text": "",
        "hot_comments": [],
        "webpage_url": (card_meta or {}).get("jump_url", "") or url,
    }
    try:
        fetched = await __import__('asyncio').to_thread(_fetch_bilibili_metadata, url)
        if fetched:
            meta.update({k: v for k, v in fetched.items() if v})
    except Exception as e:
        logger.warning(f"[bili-roaster] metadata fetch failed: {e}")

    summary_system = (
        "你是一个内容分析助手。请根据给定的B站视频信息，提炼出这个视频真正讲了什么、消费了什么梗、评论区主要在说什么。"
        "要求：只输出3条要点；每条一行；每条不超过28字；必须具体，不要空话；"
        "如果缺少字幕，就优先根据标题、简介、评论推断视频重点。"
    )
    summary_user = (
        f"标题：{meta.get('title', '')}\n"
        f"UP主：{meta.get('uploader', '')}\n"
        f"简介：{(meta.get('description', '') or '')[:400]}\n"
        f"动态：{(meta.get('dynamic', '') or '')[:160]}\n"
        f"字幕：{(meta.get('subtitle_text', '') or '')[:1200]}\n"
        f"热门评论：{' | '.join((meta.get('hot_comments') or [])[:5])}\n"
    )
    summary_reply, summary_reasoning = await _call_minimax_chat_with_reasoning(summary_system, summary_user)
    summary = summary_reply or summary_reasoning

    roast_system = (
        "你是QQ群里的暴躁贴吧老哥。根据给定视频要点，写1到3句具体回复。"
        "要求：必须点到具体内容点，不能空泛；要像真人在群里说话，句子完整，别写成半截残句；"
        "语气暴躁阴阳怪气但别越线；不要解释自己。"
    )
    roast_user = (
        f"视频标题：{meta.get('title', '')}\n"
        f"UP主：{meta.get('uploader', '')}\n"
        f"视频要点：\n{summary or '（摘要失败）'}\n"
        f"补充简介：{(meta.get('description', '') or '')[:220]}\n"
        f"补充评论：{' | '.join((meta.get('hot_comments') or [])[:3])}\n"
        "现在直接输出1到3句回复。"
    )
    reply = await _call_minimax_chat(roast_system, roast_user)
    if not reply and summary:
        reply = await _call_minimax_chat(
            "你是QQ群里的暴躁贴吧老哥。根据给定摘要，写1到3句具体回复。必须像人话，别写残句，别空泛。",
            summary[-2200:],
        )
    if not reply:
        logger.warning(f"[bili-roaster] empty reply; title={meta.get('title','')} summary={summary!r}")
    return reply


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


@image_cache.handle()
async def _cache_image(bot: Bot, event: Event):
    try:
        message_id = getattr(event, "message_id", None)
        if message_id is None:
            return

        group_id = getattr(event, "group_id", None)
        if group_id is not None:
            group_key = str(group_id)
            _ensure_group_state(group_key)
            brief = _format_message_brief(event)
            GROUP_CONTEXTS[group_key].append(brief)
            GROUP_TRIGGER_COUNTER[group_key] += 1
            logger.info(f"[group-roaster] group={group_key} counter={GROUP_TRIGGER_COUNTER[group_key]} next={GROUP_NEXT_TRIGGER[group_key]} brief={brief[:120]}")

        image_url = _pick_image_url_from_segments(event.get_message())
        if image_url:
            IMAGE_SEGMENT_CACHE[str(message_id)] = image_url
            if len(IMAGE_SEGMENT_CACHE) > 500:
                for key in list(IMAGE_SEGMENT_CACHE.keys())[:100]:
                    IMAGE_SEGMENT_CACHE.pop(key, None)

            session_key = f"{event.user_id}:{getattr(event, 'group_id', 'private')}"
            pending = PENDING_I2I.pop(session_key, None)
            if pending:
                await bot.send(event, "收到图片，开始改图……")
                ok, result = await _run_i2i_from_image_url(image_url, pending["prompt"])
                await bot.send(event, result)
                return

        # 群聊随机插话逻辑：只对有文本的群消息触发
        if group_id is not None:
            plain = event.get_plaintext().strip() if hasattr(event, "get_plaintext") else ""
            group_key = str(group_id)

            # B站链接定向回复：优先于随机插话
            bili_url = _extract_bilibili_url_from_event(event)
            if os.getenv("BILIBILI_ROASTER_ENABLED", "true").lower() == "true" and bili_url:
                logger.info(f"[bili-roaster] handling bilibili url: {bili_url}")
                if bili_url not in SEEN_BILIBILI_URLS:
                    SEEN_BILIBILI_URLS.append(bili_url)
                    context_lines = list(GROUP_CONTEXTS[group_key])
                    card_meta = _extract_bilibili_card_meta(event)
                    reply = await _generate_bilibili_roast_reply(bili_url, context_lines, card_meta)
                    if reply:
                        await bot.send(event, reply)
                    else:
                        logger.warning(f"[bili-roaster] no reply generated for url={bili_url}")
                return

            if os.getenv("GROUP_ROASTER_ENABLED", "true").lower() == "true":
                if plain and not plain.startswith(("帮助", "ping", "时间", "说 ", "echo ", "生图", "画图", "图生图", "改图", "垫图", "朗读", "念 ")):
                    if GROUP_TRIGGER_COUNTER[group_key] >= GROUP_NEXT_TRIGGER[group_key]:
                        logger.info(f"[group-roaster] triggered for group={group_key}")
                        context_lines = list(GROUP_CONTEXTS[group_key])
                        reply = await _generate_group_roast_reply(_format_message_brief(event), context_lines)
                        min_trigger = max(3, int(os.getenv("GROUP_ROASTER_MIN_TRIGGER", "5") or "5"))
                        max_trigger = max(min_trigger, int(os.getenv("GROUP_ROASTER_MAX_TRIGGER", "10") or "10"))
                        GROUP_TRIGGER_COUNTER[group_key] = 0
                        GROUP_NEXT_TRIGGER[group_key] = random.randint(min_trigger, max_trigger)
                        logger.info(f"[group-roaster] next trigger reset to {GROUP_NEXT_TRIGGER[group_key]}")
                        if reply:
                            logger.info(f"[group-roaster] sending reply: {reply[:120]}")
                            await bot.send(event, reply)
                        else:
                            logger.warning(f"[group-roaster] empty reply for group={group_key}")
    except Exception as e:
        logger.warning(f"[i2i/group] cache handler failed: {e}")


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
