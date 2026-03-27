import json
import os
import random
import re
import sqlite3
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import httpx
from loguru import logger
from nonebot.adapters.onebot.v11 import Event

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "chat_history.db"
TMP_AUDIO_DIR = BASE_DIR / "tmp_audio"
TMP_AUDIO_DIR.mkdir(exist_ok=True)

IMAGE_SEGMENT_CACHE: dict[str, str] = {}
PENDING_I2I: dict[str, dict[str, str]] = {}
GROUP_CONTEXTS: dict[str, deque] = {}
GROUP_MESSAGE_LOGS: dict[str, deque] = {}
GROUP_TRIGGER_COUNTER: dict[str, int] = {}
GROUP_NEXT_TRIGGER: dict[str, int] = {}
SEEN_BILIBILI_URLS: deque = deque(maxlen=200)
HYDRATED_GROUPS: set[str] = set()

USER_NAME_MAP = {
    "769163832": "yt",
    "1140637229": "润琦",
    "1048314482": "xh",
    "1393564897": "晧中",
    "2115639946": "e",
}


@dataclass
class GroupRoasterConfig:
    enabled: bool
    min_trigger: int
    max_trigger: int
    context_size: int


@dataclass
class GroupMessageRecord:
    ts: float
    user_id: str
    text: str


@dataclass
class BilibiliRoasterContext:
    title: str = ""
    description: str = ""
    uploader: str = ""
    tags: list[str] | None = None
    dynamic: str = ""
    argue_msg: str = ""
    subtitle_text: str = ""
    hot_comments: list[str] | None = None
    webpage_url: str = ""
    bvid: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.hot_comments is None:
            self.hot_comments = []


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_storage():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                ts REAL NOT NULL,
                user_id TEXT NOT NULL,
                text TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_group_messages_group_ts
            ON group_messages(group_id, ts)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS group_state (
                group_id TEXT PRIMARY KEY,
                trigger_counter INTEGER NOT NULL,
                next_trigger INTEGER NOT NULL
            )
            """
        )
        conn.commit()


init_storage()


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() == "true"


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or str(default))
    except ValueError:
        return default


def get_group_roaster_config() -> GroupRoasterConfig:
    context_size = max(8, min(env_int("GROUP_ROASTER_CONTEXT_SIZE", 15), 30))
    min_trigger = max(3, env_int("GROUP_ROASTER_MIN_TRIGGER", 5))
    max_trigger = max(min_trigger, env_int("GROUP_ROASTER_MAX_TRIGGER", 10))
    return GroupRoasterConfig(
        enabled=env_bool("GROUP_ROASTER_ENABLED", True),
        min_trigger=min_trigger,
        max_trigger=max_trigger,
        context_size=context_size,
    )


def get_group_summary_log_maxlen() -> int:
    return max(200, min(env_int("GROUP_SUMMARY_LOG_MAXLEN", 3000), 10000))


def load_group_state(group_id: str, config: GroupRoasterConfig) -> tuple[int, int]:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT trigger_counter, next_trigger FROM group_state WHERE group_id = ?",
            (group_id,),
        ).fetchone()
    if row is None:
        return 0, random.randint(config.min_trigger, config.max_trigger)
    return int(row["trigger_counter"]), int(row["next_trigger"])


def save_group_state(group_id: str):
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO group_state(group_id, trigger_counter, next_trigger)
            VALUES(?, ?, ?)
            ON CONFLICT(group_id) DO UPDATE SET
                trigger_counter=excluded.trigger_counter,
                next_trigger=excluded.next_trigger
            """,
            (group_id, GROUP_TRIGGER_COUNTER[group_id], GROUP_NEXT_TRIGGER[group_id]),
        )
        conn.commit()


def load_recent_group_messages(group_id: str, limit: int) -> list[GroupMessageRecord]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT ts, user_id, text FROM group_messages WHERE group_id = ? ORDER BY ts DESC LIMIT ?",
            (group_id, limit),
        ).fetchall()
    records = [
        GroupMessageRecord(ts=float(row["ts"]), user_id=str(row["user_id"]), text=str(row["text"]))
        for row in reversed(rows)
    ]
    return records


def append_group_message(group_id: str, record: GroupMessageRecord):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO group_messages(group_id, ts, user_id, text) VALUES(?, ?, ?, ?)",
            (group_id, record.ts, record.user_id, record.text),
        )
        conn.commit()


def load_group_state(group_id: str, config: GroupRoasterConfig) -> tuple[int, int]:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT trigger_counter, next_trigger FROM group_state WHERE group_id = ?",
            (group_id,),
        ).fetchone()
    if row is None:
        return 0, random.randint(config.min_trigger, config.max_trigger)
    return int(row["trigger_counter"]), int(row["next_trigger"])


def save_group_state(group_id: str):
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO group_state(group_id, trigger_counter, next_trigger)
            VALUES(?, ?, ?)
            ON CONFLICT(group_id) DO UPDATE SET
                trigger_counter=excluded.trigger_counter,
                next_trigger=excluded.next_trigger
            """,
            (group_id, GROUP_TRIGGER_COUNTER[group_id], GROUP_NEXT_TRIGGER[group_id]),
        )
        conn.commit()


def load_recent_group_messages(group_id: str, limit: int) -> list[GroupMessageRecord]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT ts, user_id, text FROM group_messages WHERE group_id = ? ORDER BY ts DESC LIMIT ?",
            (group_id, limit),
        ).fetchall()
    return [
        GroupMessageRecord(ts=float(row["ts"]), user_id=str(row["user_id"]), text=str(row["text"]))
        for row in reversed(rows)
    ]


def append_group_message(group_id: str, record: GroupMessageRecord):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO group_messages(group_id, ts, user_id, text) VALUES(?, ?, ?, ?)",
            (group_id, record.ts, record.user_id, record.text),
        )
        conn.commit()


def ensure_group_state(group_id: str):
    config = get_group_roaster_config()
    if group_id not in GROUP_CONTEXTS:
        GROUP_CONTEXTS[group_id] = deque(maxlen=config.context_size)
    if group_id not in GROUP_MESSAGE_LOGS:
        GROUP_MESSAGE_LOGS[group_id] = deque(maxlen=get_group_summary_log_maxlen())
    if group_id not in GROUP_TRIGGER_COUNTER:
        GROUP_TRIGGER_COUNTER[group_id] = 0
    if group_id not in GROUP_NEXT_TRIGGER:
        GROUP_NEXT_TRIGGER[group_id] = random.randint(config.min_trigger, config.max_trigger)

    if group_id in HYDRATED_GROUPS:
        return

    counter, next_trigger = load_group_state(group_id, config)
    GROUP_TRIGGER_COUNTER[group_id] = counter
    GROUP_NEXT_TRIGGER[group_id] = next_trigger

    preload_limit = max(config.context_size, min(get_group_summary_log_maxlen(), 300))
    records = load_recent_group_messages(group_id, preload_limit)
    for record in records:
        GROUP_MESSAGE_LOGS[group_id].append(record)
        GROUP_CONTEXTS[group_id].append(record.text)
    HYDRATED_GROUPS.add(group_id)

    if group_id in HYDRATED_GROUPS:
        return

    counter, next_trigger = load_group_state(group_id, config)
    GROUP_TRIGGER_COUNTER[group_id] = counter
    GROUP_NEXT_TRIGGER[group_id] = next_trigger

    preload_limit = max(config.context_size, min(get_group_summary_log_maxlen(), 300))
    records = load_recent_group_messages(group_id, preload_limit)
    for record in records:
        GROUP_MESSAGE_LOGS[group_id].append(record)
        GROUP_CONTEXTS[group_id].append(record.text)
    HYDRATED_GROUPS.add(group_id)


def pick_image_url_from_segments(segments) -> str:
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


def extract_bilibili_url(text: str) -> str:
    m = re.search(r"https?://(?:www\.)?(?:bilibili\.com/video/[A-Za-z0-9]+|b23\.tv/[A-Za-z0-9]+)\S*", text or "")
    if not m:
        return ""
    url = m.group(0).strip()
    url = re.sub(r'["\\,，。！？；：\)\]\}>]+$', '', url)
    return url


def extract_bilibili_url_from_event(event: Event) -> str:
    plain = event.get_plaintext().strip() if hasattr(event, "get_plaintext") else ""
    url = extract_bilibili_url(plain)
    if url:
        logger.info(f"[bili-roaster] found url in plain text: {url}")
        return url

    for seg in event.get_message():
        if seg.type == "json":
            raw = seg.data.get("data", "") if hasattr(seg, "data") else ""
            logger.info(f"[bili-roaster] json card snippet: {str(raw)[:600]}")
            url = extract_bilibili_url(raw)
            if url:
                logger.info(f"[bili-roaster] found url in json raw: {url}")
                return url
            try:
                obj = json.loads(raw)
                blob = json.dumps(obj, ensure_ascii=False)
                url = extract_bilibili_url(blob)
                if url:
                    logger.info(f"[bili-roaster] found url in parsed json: {url}")
                    return url
            except Exception as e:
                logger.warning(f"[bili-roaster] json parse failed: {e}")
    logger.info("[bili-roaster] no bilibili url found in event")
    return ""


def extract_bilibili_card_meta(event: Event) -> dict:
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
        meta["jump_url"] = extract_bilibili_url(blob) or meta["jump_url"]

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


def get_user_display_name(user_id: str | int) -> str:
    user_id = str(user_id)
    return USER_NAME_MAP.get(user_id, user_id)


def format_message_brief(event: Event) -> str:
    user_id = getattr(event, "user_id", "unknown")
    display_name = get_user_display_name(user_id)
    text = event.get_plaintext().strip() if hasattr(event, "get_plaintext") else ""
    if not text:
        text = str(event.get_message())[:120]
    return f"[{display_name}] {text}"


def json_from_httpx_response(resp: httpx.Response) -> dict:
    return json.loads(resp.content.decode("utf-8", errors="replace"))


def sanitize_generated_text(text: str) -> str:
    text = (text or "").replace("\n", " ").strip()
    text = re.sub(r"\[[^\[\]\s]{1,12}\]", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:300]


async def call_minimax_chat_with_reasoning(system_prompt: str, user_prompt: str) -> tuple[str, str]:
    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        return "", ""

    model = os.getenv("MINIMAX_CHAT_MODEL", "MiniMax-M2.7").strip() or "MiniMax-M2.7"
    try:
        max_tokens = int(os.getenv("MINIMAX_CHAT_MAX_TOKENS", "1536") or "1536")
    except ValueError:
        max_tokens = 1536

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 1.0,
        "top_p": 0.95,
        "max_tokens": max_tokens,
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
            return sanitize_generated_text(reply), reasoning[:4000]
    except Exception as e:
        logger.warning(f"[minimax-chat] generate failed: {e}")
        return "", ""


async def call_minimax_chat(system_prompt: str, user_prompt: str) -> str:
    reply, reasoning = await call_minimax_chat_with_reasoning(system_prompt, user_prompt)
    if reply:
        return sanitize_generated_text(reply)
    if reasoning:
        logger.warning("[minimax-chat] empty content, retrying from reasoning")
        retry_reply, _ = await call_minimax_chat_with_reasoning(
            "把给定分析压缩成1到3句最终回复。只输出最终回复，不要解释，不要思考过程，要像正常人在群里说话。不要输出[小嘴][doge][笑哭]这类平台表情名。",
            reasoning[-2200:],
        )
        return sanitize_generated_text(retry_reply) if retry_reply else ""
    return ""


def build_group_roast_prompt(target_text: str, context_lines: list[str]) -> tuple[str, str]:
    system_prompt = (
        "你是QQ群里的暴躁贴吧老哥。你的任务是针对指定消息做一句具体回复。"
        "要求：1）必须结合最近群聊上下文和目标消息内容，不能泛泛而谈；"
        "2）语气暴躁、阴阳怪气、嘴硬、贴吧老哥味，但不要出现仇恨、歧视、暴力威胁、真实人身伤害鼓动；"
        "3）回复必须短，10-40字，像真实群友插话；"
        "4）不要解释自己，不要加引号，不要分点，不要写成AI腔；"
        "5）不要输出[小嘴][doge][笑哭]这类平台表情名；"
        "6）如果上下文不足，就抓住目标消息本身吐槽。"
    )
    user_prompt = (
        "最近群聊上下文：\n" + "\n".join(context_lines[-15:]) +
        "\n\n目标消息：\n" + target_text +
        "\n\n现在直接给出一句回复。"
    )
    return system_prompt, user_prompt


async def generate_group_roast_reply(target_text: str, context_lines: list[str]) -> str:
    system_prompt, user_prompt = build_group_roast_prompt(target_text, context_lines)
    return await call_minimax_chat(system_prompt, user_prompt)


def fetch_bilibili_subtitle_text(headers: dict, aid: int | None, cid: int | None) -> str:
    if not cid or not aid:
        return ""
    try:
        sub_api = f"https://api.bilibili.com/x/v2/dm/view?aid={aid}&oid={cid}&type=1"
        sr = httpx.get(sub_api, headers=headers, timeout=20)
        sr.raise_for_status()
        sub_data = (json_from_httpx_response(sr).get("data") or {})
        subtitles = ((sub_data.get("subtitle") or {}).get("subtitles")) or []
        zh_sub = None
        for item in subtitles:
            if item.get("lan") in ("ai-zh", "zh-CN", "zh-Hans", "zh"):
                zh_sub = item
                break
        if not zh_sub and subtitles:
            zh_sub = subtitles[0]
        if not zh_sub or not zh_sub.get("subtitle_url"):
            return ""

        sub_url = zh_sub["subtitle_url"]
        if sub_url.startswith("//"):
            sub_url = "https:" + sub_url
        elif sub_url.startswith("http://"):
            sub_url = "https://" + sub_url[len("http://"):]
        tr = httpx.get(sub_url, headers=headers, timeout=20)
        tr.raise_for_status()
        body = json_from_httpx_response(tr)
        pieces = []
        for item in body.get("body", [])[:80]:
            content = (item.get("content") or "").strip()
            if content:
                pieces.append(content)
        return " ".join(pieces)[:4000]
    except Exception as e:
        logger.warning(f"[bili-roaster] subtitle fetch failed: {e}")
        return ""


def fetch_bilibili_hot_comments(headers: dict, aid: int | None) -> list[str]:
    if not aid:
        return []
    hot_comments: list[str] = []
    try:
        reply_candidates = [
            f"https://api.bilibili.com/x/v2/reply/main?oid={aid}&type=1&mode=3&next=0&ps=5",
            f"https://api.bilibili.com/x/v2/reply?pn=1&type=1&oid={aid}&sort=2",
        ]
        for reply_api in reply_candidates:
            cr = httpx.get(reply_api, headers=headers, timeout=20)
            cr.raise_for_status()
            payload = json_from_httpx_response(cr)
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
    return hot_comments


def fetch_bilibili_metadata(url: str) -> BilibiliRoasterContext:
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
    data = json_from_httpx_response(rr)
    if data.get("code") != 0:
        raise ValueError(f"bilibili api error: {data}")
    info = data.get("data") or {}
    owner = info.get("owner") or {}

    meta = BilibiliRoasterContext(
        title=info.get("title", ""),
        description=info.get("desc", ""),
        uploader=owner.get("name", ""),
        dynamic=info.get("dynamic", ""),
        argue_msg=((info.get("argue_info") or {}).get("argue_msg")) or "",
        subtitle_text=fetch_bilibili_subtitle_text(headers, info.get("aid"), info.get("cid")),
        hot_comments=fetch_bilibili_hot_comments(headers, info.get("aid")),
        webpage_url=final_url,
        bvid=bvid,
    )
    logger.info(f"[bili-roaster] metadata title: {meta.title}")
    return meta


def build_bilibili_context(url: str, card_meta: dict | None = None) -> BilibiliRoasterContext:
    meta = BilibiliRoasterContext(
        title=(card_meta or {}).get("title", ""),
        description=(card_meta or {}).get("desc", ""),
        webpage_url=(card_meta or {}).get("jump_url", "") or url,
    )
    try:
        fetched = fetch_bilibili_metadata(url)
        if fetched.title:
            meta.title = fetched.title
        if fetched.description:
            meta.description = fetched.description
        if fetched.uploader:
            meta.uploader = fetched.uploader
        if fetched.dynamic:
            meta.dynamic = fetched.dynamic
        if fetched.argue_msg:
            meta.argue_msg = fetched.argue_msg
        if fetched.subtitle_text:
            meta.subtitle_text = fetched.subtitle_text
        if fetched.hot_comments:
            meta.hot_comments = fetched.hot_comments
        if fetched.webpage_url:
            meta.webpage_url = fetched.webpage_url
        if fetched.bvid:
            meta.bvid = fetched.bvid
    except Exception as e:
        logger.warning(f"[bili-roaster] metadata fetch failed: {e}")
    return meta


def build_bilibili_summary_prompt(meta: BilibiliRoasterContext) -> tuple[str, str]:
    system_prompt = (
        "你是一个内容分析助手。请根据给定的B站视频信息，提炼出这个视频真正讲了什么、消费了什么梗、评论区主要在说什么。"
        "要求：只输出3条要点；每条一行；每条不超过28字；必须具体，不要空话；"
        "如果缺少字幕，就优先根据标题、简介、评论推断视频重点。"
    )
    user_prompt = (
        f"标题：{meta.title}\n"
        f"UP主：{meta.uploader}\n"
        f"简介：{(meta.description or '')[:400]}\n"
        f"动态：{(meta.dynamic or '')[:160]}\n"
        f"字幕：{(meta.subtitle_text or '')[:1200]}\n"
        f"热门评论：{' | '.join((meta.hot_comments or [])[:5])}\n"
    )
    return system_prompt, user_prompt


def build_bilibili_roast_prompt(meta: BilibiliRoasterContext, sender_ref: str, summary: str) -> tuple[str, str]:
    system_prompt = (
        "你是QQ群里的暴躁贴吧老哥。根据给定视频要点，写1到3句具体回复。"
        "要求：必须点到具体内容点，不能空泛；要像真人在群里说话，句子完整，别写成半截残句；"
        "回复对象是发这个链接的群友，所以要顺着视频内容去阴阳他、吐槽他发的东西，不要只点评视频本身；"
        "不要输出[小嘴][doge][笑哭]这类平台表情名；"
        "语气暴躁阴阳怪气但别越线；不要解释自己。"
    )
    user_prompt = (
        f"回复对象：{sender_ref}\n"
        f"视频标题：{meta.title}\n"
        f"UP主：{meta.uploader}\n"
        f"视频要点：\n{summary or '（摘要失败）'}\n"
        f"补充简介：{(meta.description or '')[:220]}\n"
        f"补充评论：{' | '.join((meta.hot_comments or [])[:3])}\n"
        "现在直接输出1到3句回复。"
    )
    return system_prompt, user_prompt


async def generate_bilibili_roast_reply(url: str, sender_ref: str = "发链接这哥们", card_meta: dict | None = None) -> str:
    meta = await __import__('asyncio').to_thread(build_bilibili_context, url, card_meta)
    summary_system, summary_user = build_bilibili_summary_prompt(meta)
    summary_reply, summary_reasoning = await call_minimax_chat_with_reasoning(summary_system, summary_user)
    summary = summary_reply or summary_reasoning

    roast_system, roast_user = build_bilibili_roast_prompt(meta, sender_ref, summary)
    reply = await call_minimax_chat(roast_system, roast_user)
    if not reply and summary:
        reply = await call_minimax_chat(
            f"你是QQ群里的暴躁贴吧老哥。根据给定摘要，冲着{sender_ref}写1到3句具体回复。必须像人话，别写残句，别空泛。",
            summary[-2200:],
        )
    if not reply:
        logger.warning(f"[bili-roaster] empty reply; title={meta.title} summary={summary!r}")
    return reply


def remember_group_message(event: Event, group_key: str):
    ensure_group_state(group_key)
    brief = format_message_brief(event)
    record = GroupMessageRecord(
        ts=time.time(),
        user_id=str(getattr(event, 'user_id', 'unknown')),
        text=brief,
    )
    GROUP_CONTEXTS[group_key].append(brief)
    GROUP_MESSAGE_LOGS[group_key].append(record)
    append_group_message(group_key, record)
    GROUP_TRIGGER_COUNTER[group_key] += 1
    save_group_state(group_key)
    logger.info(
        f"[group-roaster] group={group_key} counter={GROUP_TRIGGER_COUNTER[group_key]} "
        f"next={GROUP_NEXT_TRIGGER[group_key]} brief={brief[:120]}"
    )


def cache_image_message(message_id: int, image_url: str):
    IMAGE_SEGMENT_CACHE[str(message_id)] = image_url
    if len(IMAGE_SEGMENT_CACHE) > 500:
        for key in list(IMAGE_SEGMENT_CACHE.keys())[:100]:
            IMAGE_SEGMENT_CACHE.pop(key, None)


def is_regular_group_text(plain: str) -> bool:
    if not plain:
        return False
    command_prefixes = ("帮助", "ping", "时间", "说 ", "echo ", "生图", "画图", "图生图", "改图", "垫图", "朗读", "念 ", "总结群聊", "群聊总结", "总结聊天")
    return not plain.startswith(command_prefixes)


def get_recent_group_records(group_key: str, hours: float) -> list[GroupMessageRecord]:
    now_ts = time.time()
    cutoff = now_ts - max(hours, 0.1) * 3600
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT ts, user_id, text FROM group_messages WHERE group_id = ? AND ts >= ? ORDER BY ts ASC",
            (group_key, cutoff),
        ).fetchall()
    return [
        GroupMessageRecord(ts=float(row["ts"]), user_id=str(row["user_id"]), text=str(row["text"]))
        for row in rows
    ]


def build_group_summary_prompt(records: list[GroupMessageRecord], hours: float) -> tuple[str, str]:
    system_prompt = (
        "你是QQ群里的暴躁贴吧老哥。请总结最近一段时间的群聊。"
        "要求：1）总结要具体，点出群里主要在聊什么、谁在带节奏、哪几段最抽象；"
        "2）语气暴躁、阴阳怪气、贴吧老哥味，但不要出现仇恨、歧视、暴力威胁；"
        "3）输出2到5句人话，不要分点，不要写成报告；"
        "4）不要输出[小嘴][doge][笑哭]这类平台表情名。"
    )
    recent_lines = [r.text for r in records[-120:]]
    user_prompt = (
        f"时间范围：最近 {hours:g} 小时\n"
        f"消息条数：{len(records)}\n"
        "群聊记录：\n" + "\n".join(recent_lines)
    )
    return system_prompt, user_prompt


async def generate_group_summary_reply(group_key: str, hours: float) -> str:
    records = get_recent_group_records(group_key, hours)
    if not records:
        return "这几个小时群里基本没啥可总结的，冷得跟停服了一样。"
    system_prompt, user_prompt = build_group_summary_prompt(records, hours)
    reply = await call_minimax_chat(system_prompt, user_prompt)
    return reply or "这几个小时群聊有动静，但你这会儿让我总结，它偏偏给我装哑巴。"
