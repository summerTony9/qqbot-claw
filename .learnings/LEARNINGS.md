## [LRN-20260328-001] best_practice

**Logged**: 2026-03-27T16:10:00Z
**Priority**: medium
**Status**: pending
**Area**: backend

### Summary
在 NoneBot Matcher handler 里，不要把 `matcher.finish()` / `matcher.reject()` 放进会捕获 `Exception` 的宽泛 `try/except` 中。

### Details
NoneBot 通过内部异常（如 `FinishedException`）来结束 matcher。若外层直接 `except Exception`，会把正常结束流程误判为失败，产生假错误日志和错误回复。

### Suggested Action
给生成/IO 逻辑单独包 `try/except`，而把 `finish()` 放到 `try` 外面，或只捕获更窄的异常范围。

### Metadata
- Source: error
- Related Files: qq-bot-3371871293/plugins/news_digest.py
- Tags: nonebot, exception-handling, matcher

---

## [LRN-20260402-001] correction

**Logged**: 2026-04-02T01:11:31Z
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
排查 QQ 自动总结故障时，必须先区分是 OpenClaw 的 qqbot 插件链路，还是独立的 NapCat + NoneBot 项目；不要先入为主按 AppID 方向排查。

### Details
本次用户说的 `qqbot-claw` 实际是工作区里的 `qq-bot-3371871293/`，依赖 NapCat + OneBot v11 + NoneBot，而不是 OpenClaw 自带的 qqbot channel。错误地先按 OpenClaw qqbot 配置去看，导致结论偏题。后续继续排查时，还出现了三类体验问题：
1. 没有先确认公网/内网访问路径，就反复发不可达的 WebUI 地址；
2. 说“已发二维码图”但实际上当前通道没有把图片真正发送出去；
3. 没先确认用户真正需要的是 WebUI 地址还是扫码 URL，来回切换让用户更烦。

### Suggested Action
以后遇到类似故障，按这个顺序：
1. 先确认目标系统归属（OpenClaw channel / 独立 bot / 其他守护进程）；
2. 直接验证关键依赖端口（本案是 3001、6099、8080）和进程；
3. 对外提供地址前，先区分内网 IP 与公网 IP，并亲自测试；
4. 没有真正发出图片/文件前，不要声称“已经发了”；
5. 优先给用户最短可执行路径，不来回切方案。

### Metadata
- Source: user_feedback
- Related Files: qq-bot-3371871293/start.sh, /etc/systemd/system/napcat.service, /etc/systemd/system/qqbot337.service
- Tags: qqbot, napcat, nonebot, webui, correction, troubleshooting

---
