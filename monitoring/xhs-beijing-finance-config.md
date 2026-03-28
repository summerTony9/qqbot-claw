# Xiaohongshu monitor: Beijing enterprise financing leads

## Goal
Monitor Xiaohongshu hourly for **new** posts/comments that indicate a **Beijing-based tech-related business** may need:
- business loans
- enterprise financing
- working-capital funding
- bridge loans / tax loans / operating loans

## Time window
- Prefer **fresh** leads only
- Ignore leads that are clearly **older than 30 days**
- If the page date is ambiguous, only keep it when other evidence suggests it is recent
- If it is already several months old, do not alert

## Delivery
- Preferred email target: `769163832@qq.com`
- **Primary live delivery**: QQ SMTP email to `769163832@qq.com`
- **Secondary live delivery**: Telegram chat can be used as fallback / duplicate alert if needed
- SMTP runtime config is stored root-only at `/root/.config/xhs-monitor/smtp.json`
- Email helper script: `/root/.openclaw/workspace/monitoring/send_email_alert.py`

## Runtime dependency
This monitor depends on the user's local browser path being online:
1. local Chrome/Chromium with remote debugging on `127.0.0.1:9222`
2. reverse SSH tunnel from local machine to this server
3. browser relay on this server (`127.0.0.1:18792`)

If the browser/tunnel is offline, the monitor cannot inspect Xiaohongshu.

## Search seeds
Use and rotate combinations of these keywords:
- 北京 科技企业 贷款
- 北京 科技企业 融资
- 北京 软件公司 贷款
- 北京 软件公司 融资
- 北京 AI公司 融资
- 北京 人工智能 公司 融资
- 北京 互联网公司 贷款
- 北京 电商 公司 贷款
- 北京 MCN 公司 贷款
- 北京 高新企业 贷款
- 北京 对公 贷款 科技
- 北京 税贷 科技企业

## What counts as a valid lead
Strong signals:
- clearly mentions Beijing / 北京 / 北京公司 / 北京企业 / 北京老板 / 北京个体工商户 / 北京工厂 / 北京商贸 / 北京快科 / 科技公司 etc.
- clearly shows **technology-related business context**, such as: `科技`, `软件`, `AI`, `人工智能`, `互联网`, `SaaS`, `系统开发`, `电商`, `MCN`, `高新`, `专精特新`, `研发`, `平台`, `云服务`
- clearly expresses financing intent, pain, or need
- examples: `需要贷款`, `求融资`, `资金周转`, `征信花了还能做吗`, `有没有渠道`, `企业贷`, `税贷`, `流水贷`, `过桥`, `对公`, `急需资金`
- comments asking for contact,额度,条件,渠道,方案 also count
- **评论区优先级很高**：如果标题普通，但正文或评论区明确暴露出北京科技企业的融资需求，也算有效线索

## Exclusions
Ignore:
- personal consumer loan posts without business context
- broad financial marketing spam with no actual demand signal
- investment news with no customer intent
- duplicate posts/comments already reported
- obvious recruiters/agents scraping leads from others unless they reveal a real demand side
- `发票贷`-focused content as a primary topic
- stale leads older than 30 days
- non-tech businesses when the technology signal is weak or missing

## Comment scanning rules
For each promising candidate post:
- do not judge by title alone
- read the note body and inspect visible comments
- prioritize the first 8-15 meaningful visible comments
- if a comment reveals stronger intent than the original post, record the **comment-derived** lead
- capture whether the key signal came from `title`, `body`, `comment`, or `body+comment`
- if comments are generic noise and the post itself is weak, discard it

## Anti-blocking / pacing rules
To reduce platform risk:
- randomize query order each run instead of using a fixed sequence
- keep one main tab and reuse it; avoid tab bursts
- wait a random delay between actions:
  - 2-5 seconds between searches/navigation
  - 3-7 seconds after opening a post before reading comments
  - 1-3 seconds between small scrolls
- deep-open only the most promising results first; cap deep post opens to about 4-6 per run
- do not rapidly click many links from the same result page
- if the page looks abnormal / empty / heavily rate-limited, stop early and avoid hammering retries

## Alert format
When a new valid lead is found, send a short alert with:
- source type: post/comment
- title or post headline
- snippet
- link if available
- why it qualifies
- urgency: high / medium / low

## Persistence
- Stateful dedupe file: `monitoring/xhs-beijing-finance-state.json`
- Appendable findings log: `monitoring/xhs-beijing-finance-findings.md`
