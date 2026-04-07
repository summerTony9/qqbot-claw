# 对公客户批量分析任务

## ⚠️ 重要：上下文 Token 限制

**OpenClaw 子 agent 的 context window 有上限（200k tokens）**，单个 agent 跑太久会撞到上限导致异常终止（context 100% → compaction → abort）。

**解决方案：分小批次跑，每批 10 家。**
- 批次小 → context 不会累积到上限 → 不会 abort
- 进度文件已经保证可续跑 → 不怕中途失败
- 分批脚本已写好：`/root/.openclaw/workspace/corp-analysis/batch_runner.py`

**子 agent 每次运行前要清理上一批次历史**，不要在 prompt 里注入大量上下文。prompt 要精简，必要文件在任务内读取，不要靠 system prompt 继承。

## 任务目标
分析 `/root/.openclaw/workspace/corp-analysis/companies.txt` 中的企业，每家生成独立 md 文件，最终汇总发邮件。

## 关键要求
- **必须用 M2.7 模型**（model=minimax-m2.7）进行所有分析和生成
- **每分析一家立即写盘**，防止中途失败丢失进度
- **跳过已完成的**：检查 output 目录里没有该公司 md 才分析，已有的跳过
- **单次 agent 运行以 10 家为一批**，不要一次性跑太多
- 分析完所有公司后，生成汇总 index.md，然后 zip 发送邮件

---

## 第一步：读取必要文件

1. 读取公司列表：`/root/.openclaw/workspace/corp-analysis/companies.txt`
2. 读取分析模板：`/root/.openclaw/workspace/skills/bank-corporate-customer-analysis/references/analysis-template.md`
3. 读取 skill 说明书：`/root/.openclaw/workspace/skills/bank-corporate-customer-analysis/SKILL.md`

---

## 第二步：了解 email 发送方式

读取 email 配置：
```
/root/.openclaw/workspace/corp-analysis/email_config.env
```

发送邮件用 Python smtplib，参考代码：

```python
import smtplib, ssl, zipfile, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_email_with_zip(zip_path, to_addr):
    with open('/root/.openclaw/workspace/corp-analysis/email_config.env') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                if k == 'SMTP_HOST': smtp_host = v
                elif k == 'SMTP_PORT': smtp_port = int(v)
                elif k == 'SMTP_USER': smtp_user = v
                elif k == 'SMTP_PASS': smtp_pass = v
                elif k == 'FROM_ADDR': from_addr = v

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg['Subject'] = '对公客户深挖分析报告（49户）'

    body = MIMEText('您好，附件为49户对公客户深挖分析报告，含总览索引和每户独立报告。请查收。', 'plain', 'utf-8')
    msg.attach(body)

    with open(zip_path, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename=企业分析报告_49户.zip')
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, [to_addr], msg.as_string())
    print(f'Email sent to {to_addr}')
```

---

## 第三步：逐户分析（循环）

输出目录：`/root/.openclaw/workspace/corp-analysis/companies/`

对于 company_name in 公司列表：
1. 检查 `/root/.openclaw/workspace/corp-analysis/companies/{company_name}.md` 是否存在 → 存在则跳过
2. 使用 `agent-browser` skill 进行搜索分析：
   - 先读取 skill 文件：`/root/.openclaw/workspace/skills/bank-corporate-customer-analysis/SKILL.md`
   - 按 skill 步骤：搜索基础信息、招投标、股东背景、对外投资、近期动态、官网
   - 按 analysis-template.md 模板格式输出分析报告
3. 将分析报告写入：`/root/.openclaw/workspace/corp-analysis/companies/{company_name}.md`
4. 打印进度：`[N/49] {company_name} 完成`

---

## 第四步：生成汇总 index.md（使用固定分类脚本）

**⚠️ 分类逻辑必须严格按以下规则，禁止自己写分类代码：**

使用以下经过验证的 Python 脚本（复制运行即可）：

```python
import os, re

companies_dir = '/root/.openclaw/workspace/corp-analysis/companies'
files = sorted([f for f in os.listdir(companies_dir) if f.endswith('.md')])
results = {'A': [], 'B': [], 'C': [], 'D': [], 'Other': []}

for fname in files:
    path = os.path.join(companies_dir, fname)
    content = open(path).read()
    company_name = fname.replace('.md', '')

    # 1. 优先找"← 选择X类"标记
    m = re.search(r'←\s*选择([A-D])类', content)
    if m:
        results[m.group(1)].append(company_name)
        continue

    # 2. 找 **综合评级：X类 格式
    m = re.search(r'\*\*综合评级：([A-D])类', content)
    if m:
        results[m.group(1)].append(company_name)
        continue

    # 3. 找 **X类：重点深挖 这种粗体标题，只取最后一个
    blocks = list(re.finditer(r'\*\*([A-D])类：', content))
    if blocks:
        results[blocks[-1].group(1)].append(company_name)
        continue

    # 4. 特殊类型不评级
    if '工会委员会' in company_name or '有限合伙' in company_name:
        results['Other'].append(company_name)
        continue
    if '已注销' in content:
        results['Other'].append(company_name)
        continue

    # 兜底归 C类
    results['C'].append(company_name)
```

生成 index.md 时，对每个评级的公司都要用 `sorted()` 排序，A/B/C/D 类全部列出，**不能遗漏任何一家**。

---

## 第五步：打包发送

```python
import zipfile, os

output_dir = '/root/.openclaw/workspace/corp-analysis'
zip_path = '/root/.openclaw/workspace/corp-analysis/企业分析报告_49户.zip'

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    # 写 index
    zf.write(f'{output_dir}/index.md', '总览index.md')
    # 写每家公司
    for fname in os.listdir(f'{output_dir}/companies/'):
        if fname.endswith('.md'):
            zf.write(f'{output_dir}/companies/{fname}', f'companies/{fname}')

print(f'Zip created: {zip_path}')

# 发送邮件
send_email_with_zip(zip_path, '769163832@qq.com')
```

---

## 进度记录

每完成一家就更新进度文件：`/root/.openclaw/workspace/corp-analysis/progress.txt`
格式：`[DONE] 东联北方科技（北京）有限公司`
已完成数量写第一行：`DONE_COUNT: N / 49`

---

## 如果中途失败/中断

重新启动时：
1. 读取 `progress.txt` 获得已完成的
2. 读取 `companies.txt` 获得完整列表
3. 跳过已完成的，继续分析剩余的
4. 最终汇总和发送邮件（即使部分公司失败，也发送已完成的）
