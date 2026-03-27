import re

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Event, Message
from nonebot.params import CommandArg

from .shared import generate_group_summary_reply

summary_cmd = on_command("总结群聊", aliases={"群聊总结", "总结聊天"}, priority=5, block=True)


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
