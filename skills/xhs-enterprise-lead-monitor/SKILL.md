---
name: xhs-enterprise-lead-monitor
description: Monitor Xiaohongshu/小红书 for enterprise outreach leads using a logged-in browser path, persistent state/dedupe files, structured findings logs, and optional email or chat alerts. Use when the user wants one-off or recurring scans for 对公开户、融资、企业结算、招聘扩张、经营增长 signals, especially Beijing tech-business lead hunting, or when converting a manual Xiaohongshu lead-scouting workflow into a reusable SOP/cron-driven skill.
---

# XHS Enterprise Lead Monitor

Run quiet, repeatable Xiaohongshu lead monitoring for business-outreach scenarios.

## Quick start

- For the current production flow, first read `references/beijing-tech-business-preset.md`.
- Prefer a logged-in local browser path when Xiaohongshu blocks data-center traffic.
- Keep scheduled runs quiet: if there is no new valid lead, return `NO_REPLY`.

## Workflow

### 1. Load the preset and working files

Use one preset per market/vertical. For the current workflow, use the Beijing tech-business preset.

Default runtime files for that preset:
- `monitoring/xhs-beijing-finance-state.json`
- `monitoring/xhs-beijing-finance-findings.md`
- `monitoring/reports/` for per-run Markdown reports

If the state or findings file does not exist, create it before the first run.

### 2. Verify browser availability before scanning

Before opening Xiaohongshu:
- verify the relay/browser health for the logged-in local path
- verify CDP/browser availability
- stop early if the page path is unavailable or rate-limited

For scheduled runs:
- update state if helpful
- only send a chat warning after a prolonged outage; default threshold is 12 hours
- otherwise stay quiet

### 3. Search lightly and inspect deeply

Use the preset’s search seeds, but do not hammer the site.

Always:
- randomize keyword order each run
- reuse one main tab
- add small random waits between actions
- deep-open only the strongest candidates first
- inspect title, body, and the first meaningful visible comments

Default deep-open budget: about 4-6 posts per run.

### 4. Qualify or reject candidates

Apply the preset rules strictly.

Important defaults:
- do not judge by title alone
- comments can independently create a lead
- reject intermediaries, brokers, service-provider bait, stale posts, and weak/non-target content
- record where the signal came from: `title`, `body`, `comment`, or `body+comment`

### 5. Deduplicate and persist

Use stable signatures for accepted and rejected items.

Persist:
- accepted signatures and summary metadata in the state file
- rejected signatures with a short reason
- append-only findings log entries for new accepted findings

Do not resend the same lead twice.

### 6. Deliver only high-signal results

If there are no new valid leads:
- return `NO_REPLY` for quiet monitoring runs

If there are new valid leads:
1. write a Markdown report
2. send it by email if SMTP is configured
3. fall back to chat only if email delivery fails

Do not expose SMTP secrets, raw shell output, cookies, or internal tool chatter.

## Output requirements

For each accepted lead, include:
- lead type
- source type
- title / author / date
- link
- why it qualifies
- signal source location
- suggested outreach angle

Keep alerts short, recent, and actionable.

## Delivery command

For the current workspace, use:

```bash
python3 /root/.openclaw/workspace/monitoring/send_email_alert.py \
  --subject "小红书监控提醒：北京科技企业线索" \
  --body "详见附件 Markdown 报告。" \
  --attach <report.md>
```

Only use chat as fallback when email fails.

## Scheduling pattern

When turning the workflow into a recurring task:
- keep the cron payload short
- instruct the run to use this skill, the chosen preset, and the canonical state/findings files
- make the run quiet on empty results
- keep delivery logic inside the run, not in the chat wrapper

## Adapting the skill

For another city, industry, or lead type:
- copy the preset
- change search seeds, qualification rules, exclusions, and delivery wording
- keep separate state/findings files per preset to avoid cross-contamination
