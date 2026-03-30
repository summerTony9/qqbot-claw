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

## 2026-03-28T16:05:19.943726+08:00
- Manual rerun after adding markdown-attachment email and broader outreach lead rules
- Candidate count: 14
- Deep-opened posts: 4
- New valid findings: 1
- [financing] [body] 北京这家企业，拿到2个亿贷款而且还是贷款 | 03-19 | https://www.xiaohongshu.com/explore/69bb4f460000000023023781?xsec_token=ABrVqUYJcktYqR2WmJT_kfEhx2BhkXEnCZ0sjeA3otVq8=&xsec_source=

## 2026-03-28T16:07:51.421520+08:00
- Manual correction after review
- Rejected xhs:69bb4f460000000023023781 as service_provider_or_case_study_marketing
- Corrected effective result for prior run: 0 valid high-confidence leads

## 2026-03-28T16:10:36.646353+08:00
Final clean run: 13 candidates, 5 inspected, 0 valid
- REJECTED [missing_beijing_or_tech] 北京朝阳｜新媒体｜初创公司招人啦～
- REJECTED [previously_rejected] 我们招人啦 | AI初创公司-Apexmind
- REJECTED [job_seeker] 宇树科技四月组里缺人！接受无经验 快来

## 2026-03-30 08:32:00 +0800
- Query: 北京 人工智能 公司 融资
- Source: post+comment
- Title: 北京机器人公司招融资及战略负责人
- Author: ovO✨
- Date: 03-08
- Urgency: 中
- Why: 明确提到 A轮具身机器人公司、base 北京海淀，并招聘融资及战略负责人，正文直接暴露股权融资/投融资流程/资源需求，符合北京科技企业近期融资拓展信号。
- Snippet: A轮具身机器人公司，汇报对象公司创始人，base北京海淀；有市场化机构股权融资经验，熟悉投融资流程和战略规划，熟悉AI、机器人等相关领域优先。
- Link: https://www.xiaohongshu.com/explore/69ad9334000000000d00b7ee

## 2026-03-30 08:53:00 +0800
- User correction applied
- Cleared all rejected_signatures for fresh re-evaluation
- Scope broadened: accept Beijing startup / new-media / hiring-growth signals in addition to account-opening and tech-enterprise loan clues
- Deep-open target increased to 8-10 posts per run with bounded runtime to avoid timeout
