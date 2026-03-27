import os
import re

from loguru import logger
from nonebot import get_bots, on_command, require
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg

from .shared import env_bool, env_int, generate_group_summary_reply

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

summary_cmd = on_command("总结群聊", aliases={"群聊总结", "总结聊天", "总结"}, priority=5, block=True)
daily_summary_cmd = on_command("日报总结", aliases={"夜间总结", "夜报", "群日报"}, priority=5, block=True)


def _parse_id_list(raw: str) -> list[str]:
    parts = re.split(r"[,，\s]+", (raw or "").strip())
    return [p for p in (x.strip() for x in parts) if p]


def _default_summary_targets() -> tuple[list[str], list[str]]:
    group_ids = _parse_id_list(os.getenv("DAILY_SUMMARY_DEFAULT_GROUP_IDS", ""))
    user_ids = _parse_id_list(os.getenv("DAILY_SUMMARY_DEFAULT_USER_IDS", ""))
    return group_ids, user_ids


def _default_summary_source_group(group_ids: list[str] | None = None) -> str:
    gids = group_ids if group_ids is not None else _default_summary_targets()[0]
    return (os.getenv("DAILY_SUMMARY_SOURCE_GROUP_ID", "") or (gids[0] if gids else "")).strip()


def _default_summary_hours() -> int:
    return max(1, min(env_int("DAILY_SUMMARY_HOURS", 24), 72))


async def _send_summary_to_targets(bot: Bot, message: str) -> tuple[int, int]:
    group_ids, user_ids = _default_summary_targets()

    sent_groups = 0
    sent_users = 0

    for group_id in group_ids:
        try:
            await bot.send_group_msg(group_id=int(group_id), message=message)
            sent_groups += 1
        except Exception as e:
            logger.warning(f"[daily-summary] send group failed: {group_id} -> {e}")

    for user_id in user_ids:
        try:
            await bot.send_private_msg(user_id=int(user_id), message=message)
            sent_users += 1
        except Exception as e:
            logger.warning(f"[daily-summary] send private failed: {user_id} -> {e}")

    return sent_groups, sent_users


@summary_cmd.handle()
async def _summary(event: Event, args: Message = CommandArg()):
    group_id = getattr(event, "group_id", None)
    if group_id is None:
        await summary_cmd.finish("这个命令要在群里用，不然我总结个空气。")

    raw = args.extract_plain_text().strip()
    hours = 6.0
    if raw:
        m = re.search(r"(\d+(?:\.\d+)?)", raw)
        if m:
            try:
                hours = float(m.group(1))
            except ValueError:
                hours = 6.0
    hours = max(0.5, min(hours, 72.0))
    await summary_cmd.send(f"行，我给你盘一下最近 {hours:g} 小时群聊。")
    reply = await generate_group_summary_reply(str(group_id), hours)
    await summary_cmd.finish(reply)


@daily_summary_cmd.handle()
async def _daily_summary(args: Message = CommandArg()):
    raw = args.extract_plain_text().strip()
    hours = _default_summary_hours()
    if raw:
        m = re.search(r"(\d+(?:\.\d+)?)", raw)
        if m:
            try:
                hours = max(0.5, min(float(m.group(1)), 72.0))
            except ValueError:
                hours = float(_default_summary_hours())

    group_ids, _ = _default_summary_targets()
    source_group = _default_summary_source_group(group_ids)
    if not source_group:
        await daily_summary_cmd.finish("默认总结群还没配好，你先别催，我这边没地方可盘。")

    await daily_summary_cmd.send(f"行，我去盘默认群最近 {hours:g} 小时。")
    reply = await generate_group_summary_reply(source_group, float(hours))
    title = f"默认群日报（最近 {hours:g} 小时）"
    await daily_summary_cmd.finish(f"{title}\n\n{reply}")


@scheduler.scheduled_job(
    "cron",
    hour=max(0, min(env_int("DAILY_SUMMARY_HOUR", 0), 23)),
    minute=max(0, min(env_int("DAILY_SUMMARY_MINUTE", 30), 59)),
    timezone=os.getenv("DAILY_SUMMARY_TIMEZONE", "Asia/Shanghai"),
    id="daily_group_summary_push",
)
async def _scheduled_group_summary_push():
    if not env_bool("DAILY_SUMMARY_ENABLED", True):
        return

    group_ids, user_ids = _default_summary_targets()
    if not group_ids and not user_ids:
        logger.info("[daily-summary] no default targets configured, skip scheduled push")
        return

    summary_hours = _default_summary_hours()
    summary_source_group = _default_summary_source_group(group_ids)
    if not summary_source_group:
        logger.warning("[daily-summary] no source group configured, skip scheduled push")
        return

    bots = list(get_bots().values())
    if not bots:
        logger.warning("[daily-summary] no active bot found for scheduled push")
        return
    bot = bots[0]

    try:
        reply = await generate_group_summary_reply(summary_source_group, float(summary_hours))
        title = f"昨日日报（最近 {summary_hours} 小时群聊总结）"
        message = f"{title}\n\n{reply}"
        sent_groups, sent_users = await _send_summary_to_targets(bot, message)
        logger.info(
            f"[daily-summary] scheduled push finished: source_group={summary_source_group} "
            f"groups={sent_groups} users={sent_users}"
        )
    except Exception as e:
        logger.warning(f"[daily-summary] scheduled push failed: {e}")
