from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from loguru import logger

from .shared import (
    GROUP_CONTEXTS,
    generate_group_roast_reply,
    format_message_brief,
    get_cached_message_content,
    get_user_display_name,
    is_regular_group_text,
    message_contains_image,
    pick_image_url_from_segments,
)

# 当有人艾特机器人时的处理器，优先级高于普通插嘴逻辑（priority 93 vs 99）
mention_handler = on_message(priority=93, block=False)


def get_reply_target_text(event: Event) -> str:
    """如果当前消息是回复别人（包括回复机器人本身），把那条消息的内容也捞出来"""
    # NoneBot v11 的 event.reply 字段表示这条消息在回复哪条
    reply = getattr(event, "reply", None)
    if reply is not None:
        reply_text = (reply.get("content") or "").strip()
        if reply_text:
            reply_user = get_user_display_name(getattr(reply, "user_id", "unknown"))
            return f"（回复对象：{reply_user} 说：{reply_text}）"
    # 回复机器人自己的消息，content 可能为空（只有 at 段），走缓存捞原消息内容
    msg_id = getattr(event, "message_id", None)
    if msg_id is not None:
        cached = get_cached_message_content(msg_id)
        if cached:
            return f"（回复内容：{cached}）"
    return ""


@mention_handler.handle()
async def _handle_mention(bot: Bot, event: Event):
    try:
        # 必须是群消息且 bot 被 @mentioned
        group_id = getattr(event, "group_id", None)
        if group_id is None:
            return
        if not event.is_tome():
            return

        group_key = str(group_id)

        # 取 @之后剩下的文字内容
        plain = event.get_plaintext().strip() if hasattr(event, "get_plaintext") else ""
        # 去掉开头的 @机器人 痕迹（常见的 @小Q 这种格式）
        import re
        plain = re.sub(r"^@\S+\s*", "", plain, count=1).strip()

        # 提取图片（如果有）
        image_url = pick_image_url_from_segments(event.get_message())

        # 拼上下文：从最近群聊里取
        context_lines = list(GROUP_CONTEXTS.get(group_key, []))

        # 把当前这条消息也加进上下文（让模型知道大家在聊什么）
        current_brief = format_message_brief(event)
        # 回复目标内容
        reply_target = get_reply_target_text(event)

        sender_name = get_user_display_name(getattr(event, "user_id", "unknown"))

        # 构建目标消息：去掉 @mention 之后的内容
        target_text = plain if plain else "(仅艾特，无文字)"
        if reply_target:
            target_text = f"{target_text} {reply_target}"

        logger.info(f"[mention-reply] triggered by {sender_name} in group={group_key}, target={target_text[:120]}")

        # 贴吧暴躁老哥风格，针对这条被 @ 的消息做锐评
        reply = await generate_group_roast_reply(target_text, context_lines)

        if not reply:
            logger.warning(f"[mention-reply] empty reply for group={group_key}")
            return

        # 作为被引用消息的回复发出
        message_id = getattr(event, "message_id", None)
        if message_id is not None:
            msg = Message()
            msg.append(MessageSegment.reply(message_id))
            msg.append(MessageSegment.text(reply))
            await bot.send(event, msg)
        else:
            await bot.send(event, reply)

        logger.info(f"[mention-reply] sent: {reply[:120]}")

    except Exception as e:
        logger.warning(f"[mention-reply] handler failed: {e}")
