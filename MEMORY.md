# MEMORY.md - 长期记忆

## 用户偏好

- **模型优先级**：所有任务统一使用 `minimax-m2.7`（已确认用户 OpenAI Codex 额度耗尽，即日起全面切换到 MiniMax M2.7）
- **GitHub 推送身份**：使用 `summerTony9 <summerTony9@users.noreply.github.com>`，不要出现 `penggaolai`
- **company-info 仓库 remote**：`https://github.com/summerTony9/company-info.git`（注意不是 qqbot 那个）
- **同步原则**：只推送最终 markdown 交付物；不混入 .cache/、原始搜索截图、临时抓取文件
- **反风控节奏**：批量搜索时 5-20s 随机停顿，批次间长间隔；遇到验证码立即切换来源

## 批次记录

- **艺璇批次_123户**（2026-03-30 启动）：123 家公司，拆为 13 个小时批次（hour-01 ~ hour-13，每批约 10 家）
  - 产物目录：`/root/.openclaw/workspace/yixuan-rerun-2026-03-30/`
  - 独立 INDEX（总表+超链接）：`yixuan-rerun-2026-03-30/INDEX_总表.md`
  - 最终评级分布：A类12/B类40/C类51/D类19/未知1
  - 监督 cron：`30610c4d-ec3e-4bba-840e-00db47300a6c`
  - 注意：isolated 任务的 announce 投递到 Telegram 有时不稳定，任务状态是 ok 但 announce 可能丢

## 重要教训（已更新入 skill）

### 1. Cron 时间戳只写 UTC
- ❌ `"2026-03-31T10:40:00+08:00"` → OpenClaw 当 UTC 解析，提前 8 小时
- ✅ 写 UTC：`"2026-03-31T02:40:00Z"`

### 2. Git 工作目录 = workspace 根目录
- company-info 的 git repo 就是 workspace 根目录
- 不要 `git checkout --orphan`，会清空工作目录里的所有文件
- 正确做法：先 `cp -r` 到 `/tmp/`，清空 workspace，再重新初始化

### 3. Git 暂存前必清缓存
- `find . -name '*.sources.txt' -delete`
- `find . -name 'progress.txt' -delete`
- `find . -name 'README.md' -delete`（部分批次目录有）
- 严禁把 .png/.jpg/browser-shots/ 推进仓库

### 4. 评级解析要处理边缘格式
- `**综合评级：**` 同一行和下一行都要查
- "B/C之间" → 按上下文偏向归类
- ⭐星级 → 平均≥3.5→B类，≥2.5→C类
- 明确写"无法评级" → 归入未知，保留但标注

### 5. 独立 INDEX 每个批次单独生成
- 含评级统计 + 超链接（可点击评级列）
- 更新后立即 push 到仓库

### 6. announce 投递不可靠
- 不要依赖 announce 通知进度
- 每批完成后直接在主会话报告，最终完成做完整汇总

## 历史教训

- workspace `origin` 预配置为 `git@github.com-qqbot:summerTony9/qqbot-claw.git`，曾误推到错误仓库；后来改用 HTTPS + PAT 直推 `company-info`
- 艺璇批次第一轮曾被旧数据污染（company-info-backup 里混杂了非目标公司），后来通过备份 zip 恢复
- 用户明确要求：批量任务不做"粗筛+深挖"，每家都要查
