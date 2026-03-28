## [ERR-20260328-001] qqbot-news-finishedexception

**Logged**: 2026-03-27T16:10:00Z
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
QQ bot 的 `新闻` 命令实际上已成功生成摘要，但因 `news_cmd.finish()` 位于 `try/except` 内部，NoneBot 抛出的 `FinishedException` 被误当成失败，导致用户收到错误提示。

### Error
```
[news] manual generate failed: FinishedException()
```

### Context
- Command/operation attempted: QQ bot 私聊触发 `新闻`
- Environment details: NoneBot2 + OneBot v11 + custom `plugins/news_digest.py`
- Root cause: `Matcher.finish()` 本身通过抛出 `FinishedException` 结束流程，不应被宽泛的 `except Exception` 捕获

### Suggested Fix
将摘要生成放在 `try` 内，仅捕获真实生成异常；把 `news_cmd.finish(digest)` 移到 `try/except` 外。

### Metadata
- Reproducible: yes
- Related Files: qq-bot-3371871293/plugins/news_digest.py

### Resolution
- **Resolved**: 2026-03-27T16:10:00Z
- **Notes**: 已调整异常边界，避免把正常结束误判为失败。

---
## [ERR-20260328-002] exec-path-missing-sbin

**Logged**: 2026-03-28T15:11:00+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
Admin commands like `useradd` may fail in exec because `/usr/sbin` is not always present in PATH.

### Error
```
/usr/bin/bash: line 5: useradd: command not found
```

### Context
- Operation attempted: create restricted SSH tunnel user `relay`
- Environment: OpenClaw exec shell on Ubuntu host
- Resolution: prepend `/usr/sbin:/sbin` to PATH or use full command path like `/usr/sbin/useradd`

### Suggested Fix
For system administration commands, prefer explicit paths or export `PATH=/usr/sbin:/sbin:$PATH` first.

### Metadata
- Reproducible: yes
- Related Files: /root/.openclaw/workspace/.learnings/ERRORS.md, /root/.openclaw/workspace/TOOLS.md

---
## [ERR-20260328-003] xhs-lead-qualification-too-narrow-and-intermediary-false-positive

**Logged**: 2026-03-28T16:10:00+08:00
**Priority**: high
**Status**: pending
**Area**: monitoring

### Summary
The Xiaohongshu lead monitor was initially too narrow (focused mostly on loans/financing) and also misclassified intermediary/broker content as a valid lead.

### Error
- Email delivery format used plain body text instead of a markdown attachment, which made long reports feel truncated.
- The monitor did not sufficiently distinguish true business targets from loan brokers/intermediaries.
- The monitor underweighted comments as independent sources of lead intent.

### Correction
- Send markdown reports as email attachments.
- Treat comments as first-class lead sources.
- Broaden target types to tech-business outreach leads (hiring/expansion/account-opening/business-banking signals), not only explicit financing requests.
- Explicitly exclude intermediaries / brokers / agencies as lead targets.

---
