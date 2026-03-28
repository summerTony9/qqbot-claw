# Xiaohongshu monitor: Beijing enterprise financing leads

## Goal
Monitor Xiaohongshu hourly for **new** posts/comments that indicate a **Beijing-based business** may need:
- business loans
- enterprise financing
- working-capital funding
- bridge loans / invoice loans / tax loans / operating loans

## Delivery
- Preferred email target: `769163832@qq.com`
- **Current live delivery**: Telegram chat only
- Email is **not configured yet** on this host because no SMTP / mail transport is available.

## Runtime dependency
This monitor depends on the user's local browser path being online:
1. local Chrome/Chromium with remote debugging on `127.0.0.1:9222`
2. reverse SSH tunnel from local machine to this server
3. browser relay on this server (`127.0.0.1:18792`)

If the browser/tunnel is offline, the monitor cannot inspect Xiaohongshu.

## Search seeds
Use and rotate combinations of these keywords:
- 北京 企业 贷款
- 北京 企业 融资
- 北京 公司 贷款
- 北京 公司 融资
- 北京 资金周转
- 北京 对公 贷款
- 北京 税贷
- 北京 发票贷
- 北京 流贷
- 北京 过桥 资金
- 北京 中小企业 融资
- 北京 法人 贷款

## What counts as a valid lead
Strong signals:
- clearly mentions Beijing / 北京 / 北京公司 / 北京企业 / 北京老板 / 北京个体工商户 / 北京工厂 / 北京商贸 / 北京快科/科技公司 etc.
- clearly expresses financing intent, pain, or need
- examples: `需要贷款`, `求融资`, `资金周转`, `征信花了还能做吗`, `有没有渠道`, `企业贷`, `票贷`, `税贷`, `流水贷`, `过桥`, `对公`, `急需资金`
- comments asking for contact,额度,条件,渠道,方案 also count

## Exclusions
Ignore:
- personal consumer loan posts without business context
- broad financial marketing spam with no actual demand signal
- investment news with no customer intent
- duplicate posts/comments already reported
- obvious recruiters/agents scraping leads from others unless they reveal a real demand side

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
