import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from loguru import logger
from nonebot import get_bots, on_command, require
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg

from .shared import DATA_DIR, env_bool, env_int

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

FEED_X_URL = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json"
SUBSCRIPTIONS_PATH = DATA_DIR / "news_subscriptions.json"
CACHE_PATH = DATA_DIR / "news_digest_cache.json"

news_cmd = on_command("新闻", aliases={"要闻", "AI新闻", "日报"}, priority=5, block=True)
subscribe_news_cmd = on_command("订阅新闻", aliases={"开启新闻推送", "新闻订阅"}, priority=5, block=True)
unsubscribe_news_cmd = on_command("取消订阅新闻", aliases={"关闭新闻推送", "取消新闻订阅"}, priority=5, block=True)


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[news] read json failed: {path} -> {e}")
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_subscriptions() -> dict[str, list[str]]:
    data = _read_json(SUBSCRIPTIONS_PATH, {"groups": [], "users": [], "updated_at": ""})
    return {
        "groups": [str(x) for x in data.get("groups", [])],
        "users": [str(x) for x in data.get("users", [])],
        "updated_at": str(data.get("updated_at", "")),
    }


def _save_subscriptions(data: dict[str, list[str]]) -> None:
    payload = {
        "groups": sorted({str(x) for x in data.get("groups", [])}),
        "users": sorted({str(x) for x in data.get("users", [])}),
        "updated_at": _now_str(),
    }
    _write_json(SUBSCRIPTIONS_PATH, payload)


def _resolve_target(event: Event) -> tuple[str, str]:
    group_id = getattr(event, "group_id", None)
    if group_id is not None:
        return "group", str(group_id)
    return "user", str(getattr(event, "user_id", "0"))


def _parse_iso_time(value: str) -> datetime:
    value = (value or "").strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _score_tweet(tweet: dict[str, Any]) -> float:
    likes = int(tweet.get("likes", 0) or 0)
    retweets = int(tweet.get("retweets", 0) or 0)
    replies = int(tweet.get("replies", 0) or 0)
    return likes + retweets * 1.6 + replies * 1.2


def _trim_text(text: str, max_len: int = 420) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _flatten_feed(feed: dict[str, Any], max_builders: int, max_tweets: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for builder in feed.get("x", []):
        tweets = builder.get("tweets", []) or []
        ranked = sorted(tweets, key=_score_tweet, reverse=True)[:2]
        for tweet in ranked:
            try:
                created_at = _parse_iso_time(str(tweet.get("createdAt", "")))
            except Exception:
                created_at = datetime.min
            items.append(
                {
                    "name": builder.get("name", ""),
                    "handle": builder.get("handle", ""),
                    "bio": builder.get("bio", ""),
                    "text": _trim_text(str(tweet.get("text", ""))),
                    "url": tweet.get("url", ""),
                    "likes": int(tweet.get("likes", 0) or 0),
                    "retweets": int(tweet.get("retweets", 0) or 0),
                    "replies": int(tweet.get("replies", 0) or 0),
                    "createdAt": str(tweet.get("createdAt", "")),
                    "createdAtObj": created_at,
                    "score": _score_tweet(tweet),
                }
            )

    items.sort(key=lambda x: (x["createdAtObj"], x["score"]), reverse=True)

    selected: list[dict[str, Any]] = []
    seen_builders: set[str] = set()
    for item in items:
        builder_key = item.get("handle") or item.get("name")
        if builder_key in seen_builders and len(selected) >= max_tweets:
            continue
        selected.append(item)
        seen_builders.add(builder_key)
        if len(seen_builders) >= max_builders and len(selected) >= max_tweets:
            break

    if len(selected) < max_tweets:
        selected = items[:max_tweets]
    return selected[:max_tweets]


def _sanitize_multiline_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    cleaned_lines: list[str] = []
    blank_pending = False
    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if cleaned_lines:
                blank_pending = True
            continue
        if blank_pending and cleaned_lines:
            cleaned_lines.append("")
        blank_pending = False
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


async def _call_minimax_multiline(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if not api_key:
        return ""

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
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": max(1200, min(max_tokens, 2400)),
    }

    try:
        async with httpx.AsyncClient(timeout=90) as client:
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
            choice = ((data or {}).get("choices") or [{}])[0]
            message = choice.get("message", {}) or {}
            content = (message.get("content") or "").strip()
            if not content:
                content = (((data or {}).get("reply") or {}).get("content") or "").strip()
            return _sanitize_multiline_text(content)
    except Exception as e:
        logger.warning(f"[news] minimax digest failed: {e}")
        return ""


async def _fetch_feed_x() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(FEED_X_URL, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.json()


def _build_digest_prompt(feed: dict[str, Any], items: list[dict[str, Any]]) -> tuple[str, str]:
    generated_at = str(feed.get("generatedAt", ""))
    stats = feed.get("stats", {}) or {}
    source_lines = []
    for idx, item in enumerate(items, start=1):
        source_lines.append(
            f"[{idx}] {item['name']} (@{item['handle']})\n"
            f"时间: {item['createdAt']}\n"
            f"互动: 赞{item['likes']} / 转{item['retweets']} / 评{item['replies']}\n"
            f"内容: {item['text']}\n"
            f"链接: {item['url']}"
        )

    system_prompt = (
        "你是一个给QQ群发晨报的 AI 行业编辑。"
        "请根据给定的 X/Twitter builders 动态，写一份中文《今日 AI Builder X 要闻》。"
        "要求："
        "1）只基于给定内容，不要编造；"
        "2）先给一个标题；"
        "3）输出 5 到 8 条要闻，每条 1 到 2 句，必须具体，点出人名、动作、观点或产品方向；"
        "4）别写官话，像真人整理的晨报；"
        "5）如果几条动态在说同一主题，要合并提炼；"
        "6）最后加一个“原帖链接”区，列出 3 到 5 条最值得点开的链接；"
        "7）总长度控制在 500 到 1200 字；"
        "8）输出纯文本，不要 markdown 表格。"
    )
    user_prompt = (
        f"feed 更新时间: {generated_at}\n"
        f"builders 数量: {stats.get('buildersCount', 0)}\n"
        f"tweets 数量: {stats.get('tweetsCount', 0)}\n\n"
        "候选动态：\n"
        + "\n\n".join(source_lines)
    )
    return system_prompt, user_prompt


def _build_fallback_digest(feed: dict[str, Any], items: list[dict[str, Any]]) -> str:
    generated_at = str(feed.get("generatedAt", ""))
    title_date = generated_at[:10] if generated_at else datetime.now().strftime("%Y-%m-%d")
    lines = [f"今日 AI Builder X 要闻（{title_date}）"]
    for idx, item in enumerate(items[:6], start=1):
        lines.append(
            f"{idx}. {item['name']}：{item['text']}\n"
            f"链接：{item['url']}"
        )
    return "\n\n".join(lines).strip()


async def _generate_news_digest(force_refresh: bool = False) -> str:
    max_builders = max(4, min(env_int("NEWS_DIGEST_MAX_BUILDERS", 8), 20))
    max_tweets = max(5, min(env_int("NEWS_DIGEST_MAX_TWEETS", 10), 20))

    feed = await _fetch_feed_x()
    items = _flatten_feed(feed, max_builders=max_builders, max_tweets=max_tweets)
    if not items:
        return "今天这份 X feed 空得离谱，暂时没扒到能发的内容。"

    cache_key = f"{feed.get('generatedAt', '')}|{max_builders}|{max_tweets}|v1"
    cache = _read_json(CACHE_PATH, {})
    if not force_refresh and cache.get("key") == cache_key and cache.get("digest"):
        return str(cache.get("digest"))

    system_prompt, user_prompt = _build_digest_prompt(feed, items)
    digest = await _call_minimax_multiline(system_prompt, user_prompt)
    if not digest:
        digest = _build_fallback_digest(feed, items)

    _write_json(
        CACHE_PATH,
        {
            "key": cache_key,
            "generated_at": _now_str(),
            "feed_generated_at": feed.get("generatedAt", ""),
            "digest": digest,
        },
    )
    return digest


async def _broadcast_news_digest(bot: Bot, digest: str) -> tuple[int, int]:
    subs = _load_subscriptions()
    sent_groups = 0
    sent_users = 0

    for group_id in subs.get("groups", []):
        try:
            await bot.send_group_msg(group_id=int(group_id), message=digest)
            sent_groups += 1
        except Exception as e:
            logger.warning(f"[news] send group failed: {group_id} -> {e}")

    for user_id in subs.get("users", []):
        try:
            await bot.send_private_msg(user_id=int(user_id), message=digest)
            sent_users += 1
        except Exception as e:
            logger.warning(f"[news] send private failed: {user_id} -> {e}")

    return sent_groups, sent_users


@news_cmd.handle()
async def _news(args: Message = CommandArg()):
    raw = args.extract_plain_text().strip()
    force_refresh = raw in {"刷新", "重刷", "重新生成", "update", "refresh"}
    await news_cmd.send("等会儿，我去扒今天 X 上那帮 AI builder 又在说什么。")
    try:
        digest = await _generate_news_digest(force_refresh=force_refresh)
        await news_cmd.finish(digest)
    except Exception as e:
        logger.warning(f"[news] manual generate failed: {e}")
        await news_cmd.finish("新闻这会儿拉取失败了，八成是 feed 或模型在抽风，你等下再来一脚。")


@subscribe_news_cmd.handle()
async def _subscribe_news(event: Event):
    target_type, target_id = _resolve_target(event)
    data = _load_subscriptions()
    key = "groups" if target_type == "group" else "users"
    if target_id not in data[key]:
        data[key].append(target_id)
        _save_subscriptions(data)
    where = f"群 {target_id}" if target_type == "group" else f"QQ {target_id}"
    await subscribe_news_cmd.finish(f"行，已经给 {where} 开了新闻推送。每天早上 8 点我会自动发，手动也能直接敲“新闻”。")


@unsubscribe_news_cmd.handle()
async def _unsubscribe_news(event: Event):
    target_type, target_id = _resolve_target(event)
    data = _load_subscriptions()
    key = "groups" if target_type == "group" else "users"
    if target_id in data[key]:
        data[key] = [x for x in data[key] if x != target_id]
        _save_subscriptions(data)
    where = f"群 {target_id}" if target_type == "group" else f"QQ {target_id}"
    await unsubscribe_news_cmd.finish(f"行，{where} 的新闻推送给你关了。")


@scheduler.scheduled_job(
    "cron",
    hour=max(0, min(env_int("NEWS_DIGEST_HOUR", 8), 23)),
    minute=max(0, min(env_int("NEWS_DIGEST_MINUTE", 0), 59)),
    timezone=os.getenv("NEWS_DIGEST_TIMEZONE", "Asia/Shanghai"),
    id="daily_news_digest_push",
)
async def _scheduled_news_push():
    if not env_bool("NEWS_DIGEST_ENABLED", True):
        return

    subs = _load_subscriptions()
    if not subs.get("groups") and not subs.get("users"):
        logger.info("[news] no subscriptions, skip scheduled push")
        return

    bots = list(get_bots().values())
    if not bots:
        logger.warning("[news] no active bot found for scheduled push")
        return
    bot = bots[0]

    try:
        digest = await _generate_news_digest(force_refresh=False)
        sent_groups, sent_users = await _broadcast_news_digest(bot, digest)
        logger.info(f"[news] scheduled push finished: groups={sent_groups} users={sent_users}")
    except Exception as e:
        logger.warning(f"[news] scheduled push failed: {e}")
