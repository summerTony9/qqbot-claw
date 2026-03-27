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
