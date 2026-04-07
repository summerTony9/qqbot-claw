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

## 2026-03-30 08:55:00 +0800
- Run mode: broadened Beijing business scan with fresh re-evaluation
- Deep-opened posts: 8
- New valid findings: 3
- Query: 北京 科技公司 招聘
- Source: post+comment
- Title: 我们招人啦 | AI初创公司-Apexmind
- Author: 初见未来科技有限公司
- Date: 03-21
- Urgency: 中
- Why: 官方公司账号直接发布招聘，明确为 AI 初创公司，Base 覆盖北京；同时开放产品、算法、销售、工程等多岗位，评论区显示简历集中涌入且作者持续回复，属于近期真实扩招信号。
- Snippet: 我们是ApexMind（初见智能），深耕AI时代全渠道零售生态；Base：北京/上海/成都；热招产品、算法、大客户销售、渠道销售、前后端、测试等岗位。
- Link: https://www.xiaohongshu.com/explore/69bdf642000000001b002377

- Query: 北京 新媒体 团队 招聘
- Source: post+comment
- Title: 🎈我们招人啦｜坐标北京，期待你的加入！
- Author: 艺术公园 ARTPARK
- Date: 5天前
- Urgency: 中
- Why: 官方账号披露 THEMiS 正在搭建跨领域内容团队，坐标北京，围绕移动出行内容平台持续孵化内容 IP；评论区对设计、活动、公关等岗位的追问获得作者确认，说明不是单点补人而是内容团队扩张。
- Snippet: THEMiS 是以“移动出行”为核心议题的内容与文化平台，持续孵化围绕移动出行展开的内容 IP；正在构建一个跨领域的内容团队，邀请汽车、设计、艺术、科技与媒体背景的人加入。
- Link: https://www.xiaohongshu.com/explore/69ba690f0000000021012071

- Query: 北京 创业公司 招聘
- Source: post+comment
- Title: AI陪伴赛道宝藏公司💻正在捞人
- Author: MM豆走天下
- Date: 2天前
- Urgency: 中
- Why: 帖子明确点名创业公司 Being Being，称其已获数百万天使轮融资，正在招聘内容负责人，工作地支持北京/上海；评论区持续有人询问投递与创始人背景，反映招聘仍在进行，属于近期融资后扩张信号。
- Snippet: Being Being 是一家专注 AI 陪伴产品的创业公司，已获数百万天使轮融资，团队核心成员来自一线互联网公司；本次招聘岗位为内容负责人，工作地点 Base 上海/北京。
- Link: https://www.xiaohongshu.com/explore/69c60d89000000002200f4e1


## 2026-04-03 16:30:42 +0800
- Scheduled run status: browser path unavailable (relay/CDP connection refused)
- Action: scan skipped to avoid data-center path; state updated
- Alert policy: outage exceeded 12h, sent one short warning

## 2026-04-04 16:30:42 +0800
- Scheduled run status: browser path unavailable (relay connection refused)
- Action: scan skipped to avoid data-center path; state updated
- Alert policy: outage >12h since unavailable_since, sent one short warning

## 2026-04-05 16:30:00 +0800
- Scheduled run status: browser path unavailable (relay/CDP connection refused)
- Action: scan skipped to avoid data-center path; state updated
- Alert policy: outage >12h, sent one short warning

## 2026-04-06 16:30:00 +0800
- Scheduled run status: browser path still unavailable (relay/CDP connection refused, Chrome instances running headless with --remote-debugging-port=0)
- Action: scan skipped; state updated; long-standing outage warning sent
