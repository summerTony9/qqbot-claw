#!/usr/bin/env python3
"""
分批执行脚本 - 将长任务拆成小批次，每批只处理 N 家公司
每批完成后立即存档，防止单个批次失败导致大量重跑
"""
import os, re, sys

BATCH_SIZE = 10          # 每批数量（context 安全）
COMPANIES_FILE = '/root/.openclaw/workspace/corp-analysis/companies.txt'
PROGRESS_FILE = '/root/.openclaw/workspace/corp-analysis/progress.txt'
DONE_FILE     = '/root/.openclaw/workspace/corp-analysis/batch_done.txt'  # 记录已完成批次
OUTPUT_DIR    = '/root/.openclaw/workspace/corp-analysis/companies'

def get_all_companies():
    with open(COMPANIES_FILE) as f:
        return [l.strip() for l in f if l.strip()]

def get_done_batch_ids():
    if not os.path.exists(DONE_FILE):
        return set()
    with open(DONE_FILE) as f:
        return set(l.strip() for l in f if l.strip())

def mark_batch_done(batch_id):
    with open(DONE_FILE, 'a') as f:
        f.write(batch_id + '\n')

def get_batch_tasks(companies, done_batches):
    """返回 [(batch_id, [company, ...]), ...] 只返回未完成的批次"""
    tasks = []
    batch_id = 0
    for i in range(0, len(companies), BATCH_SIZE):
        bid = f'batch_{batch_id}'
        if bid not in done_batches:
            tasks.append((bid, companies[i:i+BATCH_SIZE]))
        batch_id += 1
    return tasks

def generate_batch_task_script(batch_id, companies):
    """生成单个批次的子 agent 任务描述"""
    return f"""
## 批次任务：{batch_id}

### 本批次公司（共 {len(companies)} 家）
{chr(10).join(f'- {c}' for c in companies)}

### 执行要求
- 读取 /root/.openclaw/workspace/skills/bank-corporate-customer-analysis/SKILL.md 了解 agent-browser 用法
- 读取 /root/.openclaw/workspace/skills/bank-corporate-customer-analysis/references/analysis-template.md
- 对上述每家公司：
  1. 检查 md 是否已存在于 {OUTPUT_DIR}/，存在则跳过
  2. 用 agent-browser 搜索分析（参考 SKILL.md）
  3. 按完整模板输出，写入 {OUTPUT_DIR}/{{公司名}}.md
  4. 每完成一家打印进度 [N/{len(companies)}]
- 完成后打印 "BATCH_DONE:{batch_id}" 报告给主 session
- 全程使用 minimax-m2.7 模型
"""

if __name__ == '__main__':
    companies = get_all_companies()
    done_batches = get_done_batch_ids()
    pending = get_batch_tasks(companies, done_batches)
    print(f'总任务：{len(companies)} 家，分 {len(pending)} 个批次待执行')
    for bid, cos in pending:
        print(f'  {bid}: {cos[0]} ... ({len(cos)}家)')
