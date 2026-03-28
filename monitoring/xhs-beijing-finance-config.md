# Xiaohongshu monitor: Beijing tech-business outreach leads

## Goal
Monitor Xiaohongshu hourly for **new** posts/comments that reveal a **Beijing-based tech-related business** worth contacting.

This is **not limited to loan / financing demand**. We also want lead-like signals for:
- business loans / enterprise financing / working-capital need
- corporate bank account / 对公开户 / 公户 / 收款 / 流水 / tax / invoice / payroll / compliance questions
- startup growth / team expansion / active hiring / office expansion / business ramp-up
- founders or operators asking for business solutions where贷款、开户、结算、财税、授信可能都能切入

## Time window
- Prefer **fresh** leads only
- Ignore leads that are clearly **older than 30 days**
- If the page date is ambiguous, only keep it when other evidence suggests it is recent
- If it is already several months old, do not alert

## Delivery
- Preferred email target: `769163832@qq.com`
- **Primary live delivery**: QQ SMTP email to `769163832@qq.com`
- Delivery format: **Markdown report as attachment** + short email summary in body
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
- 北京 对公 开户 科技
- 北京 公户 开户 科技公司
- 北京 创业公司 招聘
- 北京 科技公司 招聘
- 北京 初创 科技 团队 扩张
- 北京 SaaS 公司 招人
- 北京 科技公司 资金周转
- 北京 税贷 科技企业

## What counts as a valid lead
Strong signals:
- clearly mentions Beijing / 北京 / 北京公司 / 北京企业 / 北京老板 / 北京快科 / 科技公司 etc.
- clearly shows **technology-related business context**, such as: `科技`, `软件`, `AI`, `人工智能`, `互联网`, `SaaS`, `系统开发`, `电商`, `MCN`, `高新`, `专精特新`, `研发`, `平台`, `云服务`, `自媒体团队`
- reveals a business opportunity for outreach, including any of the following:
  - explicit financing / loan /授信 / 资金周转 demand
  - explicit 对公开户 / 公户 / 银行 / 结算 / tax / payroll / invoice / 收款 / compliance need
  - startup or scale-up signals like 招聘、扩团队、扩大经营、开始走公户、准备规范财税、业务起量
- **评论区优先级很高**：如果标题普通，但正文或评论区明确暴露出北京科技企业的经营需求，也算有效线索
- capture whether the key signal came from `title`, `body`, `comment`, or `body+comment`

## Exclusions
Ignore:
- personal consumer loan posts without business context
- broad financial marketing spam with no actual demand signal
- investment news with no customer intent
- duplicate posts/comments already reported
- `发票贷`-focused content as a primary topic
- stale leads older than 30 days
- non-tech businesses when the technology signal is weak or missing
- **中介 / 助贷 / 代理 / 渠道商 / 居间方** as the lead subject
- posts where the author is obviously selling loan products rather than expressing business need
- recruiter / service-provider content unless the underlying company itself is the real target and not just an agency shell

## Comment scanning rules
For each promising candidate post:
- do not judge by title alone
- read the note body and inspect visible comments
- prioritize the first 8-15 meaningful visible comments
- if a comment reveals stronger intent than the original post, record the **comment-derived** lead
- comments can independently count as leads when the commenter exposes loan / account-opening / business-banking / expansion need
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

## Alert/report format
When a new valid lead is found, send a Markdown report including:
- lead type: financing | account-opening | business-banking | hiring/expansion | mixed
- source type: post | comment | post+comment
- title / author / date
- link
- why it qualifies
- whether the signal comes from title/body/comments
- quick outreach angle: why this could be useful for loans / 开户 / 对公结算 / 财税切入

## Persistence
- Stateful dedupe file: `monitoring/xhs-beijing-finance-state.json`
- Appendable findings log: `monitoring/xhs-beijing-finance-findings.md`
