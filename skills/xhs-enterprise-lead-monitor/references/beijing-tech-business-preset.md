# Beijing tech-business preset

Use this preset for the current workflow: monitor Xiaohongshu for **new Beijing tech-business outreach leads**.

## Goal

Find recent posts or comments that reveal a real Beijing-based business worth contacting.

Target lead types:
- financing / working-capital need
- 对公开户 / 公户 / corporate banking setup
- business-banking / settlement / payroll / invoice / tax / compliance needs
- hiring / team expansion / office expansion / operations growth

## Canonical runtime files

- State: `monitoring/xhs-beijing-finance-state.json`
- Findings log: `monitoring/xhs-beijing-finance-findings.md`
- Optional report directory: `monitoring/reports/`
- Optional local config mirror: `monitoring/xhs-beijing-finance-config.md`

If the state file is missing, initialize it with at least:

```json
{
  "version": 1,
  "created_at": "<iso>",
  "last_run_at": null,
  "last_success_at": null,
  "last_unavailable_alert_at": null,
  "seen_signatures": [],
  "recent_findings": [],
  "rejected_signatures": {}
}
```

## Browser dependency

This workflow depends on a usable, logged-in browser path.

Check before scanning:
- relay health endpoint
- CDP/browser availability
- authentication/login status if the page looks abnormal

If the browser path is unavailable:
- update state if useful
- stay quiet unless the outage has lasted more than 12 hours

## Search seeds

Rotate and remix these queries:
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

## Qualification rules

Keep only leads that satisfy most of the following:
- clearly tied to Beijing
- clearly tied to a tech-related business context
- reveal an outreach-worthy business need
- recent enough to act on now

Strong business-context words include:
- 科技 / 软件 / AI / 人工智能 / 互联网 / SaaS
- 系统开发 / 电商 / MCN / 高新 / 专精特新
- 研发 / 平台 / 云服务 / 自媒体团队

Signal sources can be:
- `title`
- `body`
- `comment`
- `body+comment`

Comments matter. A weak title can still become a valid lead if the body or comments expose a real business need.

## Freshness rules

- prefer recent leads only
- default freshness window: 30 days
- reject obviously stale posts
- if the visible date is ambiguous, keep it only when other evidence suggests it is recent

## Exclusions

Reject these by default:
- personal consumer-loan content without business context
- generic marketing spam
- pure policy/news posts with no customer intent
- duplicates already accepted or rejected
- `发票贷` as the primary topic
- weak or missing Beijing/tech signal
- intermediaries / 助贷 / brokers / 渠道 / agencies
- service-provider or case-study marketing posts that are really selling to others
- recruiter or career posts where the author is a job seeker instead of the company

## Comment scanning rules

For each promising post:
- do not rely on title alone
- inspect the note body
- inspect the first 8-15 meaningful visible comments
- if a comment reveals stronger intent than the post, record the lead from the comment angle
- if comments are noise and the post itself is weak, reject it

## Anti-blocking rules

Reduce platform risk:
- randomize query order each run
- reuse one main tab
- wait about 2-5s between searches/navigation
- wait about 3-7s after opening a post before reading comments
- wait about 1-3s between small scrolls
- deep-open only about 4-6 posts per run
- stop early if the page looks abnormal, empty, or rate-limited

## Signature rules

Use stable signatures to dedupe.

Recommended format:
- post lead: `xhs:<note_id>`
- comment-derived lead: `xhs:<note_id>#comment:<short-hash>`

Store:
- accepted items in `seen_signatures`
- rejected items in `rejected_signatures` with a reason and timestamp

## Findings log entry

Append only new accepted findings. Include:
- query used
- source type
- title
- author
- date
- urgency if visible
- why it qualifies
- short snippet
- link

## Report format

For each accepted lead, include:
- lead type: financing | account-opening | business-banking | hiring-expansion | mixed
- source type: post | comment | post+comment
- title / author / date
- link
- why it qualifies
- signal source location
- suggested outreach angle

## Delivery

Preferred delivery for the current workflow:

```bash
python3 /root/.openclaw/workspace/monitoring/send_email_alert.py \
  --subject "小红书监控提醒：北京科技企业线索" \
  --body "详见附件 Markdown 报告。" \
  --attach <report.md>
```

If email fails, send the findings in chat as fallback.
