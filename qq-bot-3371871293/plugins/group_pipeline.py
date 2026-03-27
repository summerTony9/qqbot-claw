from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, Event
from loguru import logger

from .image_to_image import run_i2i_from_image_url
from .shared import (
    GROUP_CONTEXTS,
    GROUP_NEXT_TRIGGER,
    GROUP_TRIGGER_COUNTER,
    PENDING_I2I,
    SEEN_BILIBILI_URLS,
    cache_image_message,
    env_bool,
    extract_bilibili_card_meta,
    extract_bilibili_url_from_event,
    format_message_brief,
    generate_bilibili_roast_reply,
    generate_group_roast_reply,
    get_group_roaster_config,
    is_regular_group_text,
    pick_image_url_from_segments,
    remember_group_message,
)

image_cache = on_message(priority=99, block=False)


async def handle_pending_i2i_if_needed(bot: Bot, event: Event, image_url: str) -> bool:
    session_key = f"{event.user_id}:{getattr(event, 'group_id', 'private')}"
    pending = PENDING_I2I.pop(session_key, None)
    if not pending:
        return False
    await bot.send(event, "收到图片，开始改图……")
    ok, result = await run_i2i_from_image_url(image_url, pending["prompt"])
    await bot.send(event, result)
    return True


async def handle_bilibili_if_needed(bot: Bot, event: Event, group_key: str) -> bool:
    if not env_bool("BILIBILI_ROASTER_ENABLED", True):
        return False
    bili_url = extract_bilibili_url_from_event(event)
    if not bili_url:
        return False

    logger.info(f"[bili-roaster] handling bilibili url: {bili_url}")
    if bili_url in SEEN_BILIBILI_URLS:
        return True

    SEEN_BILIBILI_URLS.append(bili_url)
    card_meta = extract_bilibili_card_meta(event)
    sender_ref = f"发这个链接的群友（QQ:{getattr(event, 'user_id', 'unknown')}）"
    reply = await generate_bilibili_roast_reply(bili_url, sender_ref, card_meta)
    if reply:
        await bot.send(event, reply)
    else:
        logger.warning(f"[bili-roaster] no reply generated for url={bili_url}")
    return True


async def handle_group_roaster_if_needed(bot: Bot, event: Event, group_key: str, plain: str) -> None:
    config = get_group_roaster_config()
    if not config.enabled or not is_regular_group_text(plain):
        return
    if GROUP_TRIGGER_COUNTER[group_key] < GROUP_NEXT_TRIGGER[group_key]:
        return

    logger.info(f"[group-roaster] triggered for group={group_key}")
    context_lines = list(GROUP_CONTEXTS[group_key])
    reply = await generate_group_roast_reply(format_message_brief(event), context_lines)
    GROUP_TRIGGER_COUNTER[group_key] = 0
    GROUP_NEXT_TRIGGER[group_key] = config.min_trigger + __import__('random').randint(0, config.max_trigger - config.min_trigger)
    logger.info(f"[group-roaster] next trigger reset to {GROUP_NEXT_TRIGGER[group_key]}")
    if reply:
        logger.info(f"[group-roaster] sending reply: {reply[:120]}")
        await bot.send(event, reply)
    else:
        logger.warning(f"[group-roaster] empty reply for group={group_key}")


@image_cache.handle()
async def _cache_image(bot: Bot, event: Event):
    try:
        message_id = getattr(event, "message_id", None)
        if message_id is None:
            return

        group_id = getattr(event, "group_id", None)
        group_key = str(group_id) if group_id is not None else None
        if group_key is not None:
            remember_group_message(event, group_key)

        image_url = pick_image_url_from_segments(event.get_message())
        if image_url:
            cache_image_message(message_id, image_url)
            if await handle_pending_i2i_if_needed(bot, event, image_url):
                return

        if group_key is None:
            return

        if await handle_bilibili_if_needed(bot, event, group_key):
            return

        plain = event.get_plaintext().strip() if hasattr(event, "get_plaintext") else ""
        await handle_group_roaster_if_needed(bot, event, group_key, plain)
    except Exception as e:
        logger.warning(f"[i2i/group] cache handler failed: {e}")
