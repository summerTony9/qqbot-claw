from datetime import datetime

from nonebot import on_command, on_keyword, require
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.params import CommandArg

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

help_cmd = on_command("帮助", aliases={"help", "菜单"}, priority=5, block=True)
ping_cmd = on_command("ping", priority=5, block=True)
time_cmd = on_command("时间", aliases={"time"}, priority=5, block=True)
echo_cmd = on_command("说", aliases={"echo"}, priority=5, block=True)
hello = on_keyword({"你好", "在吗", "机器人"}, priority=20, block=False)


@help_cmd.handle()
async def _help():
    await help_cmd.finish(
        "可用指令：\n"
        "1. 帮助 / help / 菜单\n"
        "2. ping\n"
        "3. 时间\n"
        "4. 说 <内容>\n"
        "\n"
        "示例：\n"
        "说 今天天气不错"
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


@hello.handle()
async def _hello(bot: Bot, event: Event):
    # 轻量关键词响应，避免打断聊天
    if "你好" in event.get_plaintext():
        await hello.finish("你好，我在。发“帮助”看命令。")


@scheduler.scheduled_job("cron", hour="9", minute="0", id="daily-greeting", replace_existing=True)
async def _daily_greeting():
    # 这里只示例定时任务注册；实际发送对象需要你按群号/QQ号补充。
    return None
