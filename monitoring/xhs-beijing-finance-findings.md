# Xiaohongshu findings log — Beijing enterprise financing

Append new unique findings here with timestamp, source, snippet, relevance, and link.

## 2026-03-28 15:33:19 +0800
- Query: 北京 对公 贷款
- Source: post+comments
- Title: 北京有没有3个点左右的银行能贷？
- Author: 收拾音乐小助理
- Date: 2025-06-24
- Urgency: 高
- Why: 明确提到公司在北京、民生公户、想贷几万额度，并在评论区继续讨论企业/个人能否操作，属于较强的真实融资需求信号。
- Snippet: 公司在北京，民生的公户，一年流水一万左右；已经有一定的自媒体平台数据，现在打算用这个公司正常走账，想贷几万的额度出来。
- Link: https://www.xiaohongshu.com/explore/685a6cea0000000013012c11?xsec_token=ABAuFbYdI5BcCoQVJIRQx_P5dmkCMLf1rHDr95BgsMvnU=&xsec_source=

## 2026-03-28T15:41:48.080124+08:00
- Manual rerun with stricter filters
- Filters: no 发票贷, tech-related only, recency <= 30 days
- Result: 0 high-confidence valid leads
- Excluded buckets: stale old posts, marketing/product posts, policy/news posts, hiring/career posts, non-tech/non-business scenes

## 2026-03-28T15:48:09.430380+08:00
- Manual rerun with comment scanning + randomized pacing
- Deep-opened posts: 6
- New valid findings: 1
- [body+comment] 不看流水，新公司也能抵押贷我是怎么做到的 | 03-03 | https://www.xiaohongshu.com/explore/69a68382000000001b015520?xsec_token=ABm9Q85Tm9S4eCkvcs5oaVgvufvRk4yeAX2eCyKOdIGgM=&xsec_source=
  - body: 创作中心 业务合作 发现 直播 发布 通知 我 沪ICP备13030189号 | 营业执照 | 2024沪公网安备31010102002533号 | 增值电信业务经营许可证：沪B2-20150021 | 医疗器械网络交易服务第三方平台备案：(沪)网械平台备字[2019]第00006号 | 互联网药品信息服务资格证书：(沪)-经营性-2023-0144 | 违法不良信息举报电话：4006676810 | 上海市互联网举报中心 | 网上有害
  - comments: bord 这个怎么做呀 利息可以这么低吗 03-18北京 赞 1 Hi 品信保 作者 您好，根据个人资质和征信情况最终的利息是根据银行不同的产品来匹配的，您可以发下您的详细房产征信和负债情况给您做个详细的评估介绍。 03-18北京 赞 回复 Hi 品信保 作者 有很多人单独问我具体方案，但每个情况都不同。如果您也面临资金周转问题，可以发我【房本详细地址】，我帮你评估下。 03-03北京 赞 回复 - THE END - 说点什么... 

## 2026-03-28T15:55:44.115871+08:00
- Monitor logic updated per user feedback
- Delivery: send Markdown report attachments by email
- Scope widened: include Beijing tech-business outreach leads beyond pure loan/financing demand
- Comments can independently count as lead signals
- Exclude intermediaries / loan brokers / agents as lead targets
- Reclassified xhs:69a68382000000001b015520 as rejected (intermediary_or_broker_content)
