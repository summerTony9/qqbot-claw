from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Bot, GroupRecallNoticeEvent, Message, MessageSegment
from loguru import logger

from .shared import (
    env_bool,
    generate_recall_roast_reply,
    get_cached_message_content,
    get_user_display_name,
)

recall_notice = on_notice(priority=20, block=False)


@recall_notice.handle()
async def _handle_group_recall(bot: Bot, event):
    try:
        if not isinstance(event, GroupRecallNoticeEvent):
            return
        if not env_bool("GROUP_RECALL_ROASTER_ENABLED", True):
            return

        message_id = getattr(event, "message_id", None)
        user_id = getattr(event, "user_id", None)
        group_id = getattr(event, "group_id", None)
        if message_id is None or user_id is None or group_id is None:
            return

        recalled_text = get_cached_message_content(message_id)
        if not recalled_text:
            recalled_text = "[这孙子撤太快，原文没截住]"

        sender_name = get_user_display_name(user_id)
        sender_ref = f"撤回消息的群友（{sender_name}）"
        roast = await generate_recall_roast_reply(sender_ref, recalled_text)
        if not roast:
            return

        msg = Message()
        msg.append(MessageSegment.at(int(user_id)))
        msg.append(MessageSegment.text(f" 撤回失败，原文给你补档：{recalled_text}\n{roast}"))
        await bot.send_group_msg(group_id=int(group_id), message=msg)
        logger.info(f"[recall-roaster] group={group_id} user={user_id} recalled={recalled_text[:80]} roast={roast[:80]}")
    except Exception as e:
        logger.warning(f"[recall-roaster] failed: {e}")
