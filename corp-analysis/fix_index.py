#!/usr/bin/env python3
"""
固定分类脚本 - 根据 md 文件内容中的评级标注，自动分类生成 index.md
使用方法: python3 fix_index.py
"""
import os, re, zipfile, smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

OUTPUT_DIR = '/root/.openclaw/workspace/corp-analysis'
COMPANIES_DIR = f'{OUTPUT_DIR}/companies'

def classify_companies():
    files = sorted([f for f in os.listdir(COMPANIES_DIR) if f.endswith('.md')])
    results = {'A': [], 'B': [], 'C': [], 'D': [], 'Other': []}
    for fname in files:
        content = open(os.path.join(COMPANIES_DIR, fname)).read()
        company_name = fname.replace('.md', '')
        m = re.search(r'←\s*选择([A-D])类', content)
        if m:
            results[m.group(1)].append(company_name); continue
        m = re.search(r'\*\*综合评级：([A-D])类', content)
        if m:
            results[m.group(1)].append(company_name); continue
        blocks = list(re.finditer(r'\*\*([A-D])类：', content))
        if blocks:
            results[blocks[-1].group(1)].append(company_name); continue
        if '工会委员会' in company_name or '有限合伙' in company_name:
            results['Other'].append(company_name); continue
        if '已注销' in content:
            results['Other'].append(company_name); continue
        results['C'].append(company_name)
    return results

def get_highlight(fname):
    path = os.path.join(COMPANIES_DIR, fname)
    content = open(path).read()
    for kw in ['为什么值得关注', '核心亮点', '主要机会', '主要风险']:
        idx = content.find(kw)
        if idx >= 0:
            snippet = re.sub(r'[#*>\[\]`\n]| {2,}', '', content[idx:idx+300]).strip()
            return ' '.join(snippet.split())[:100]
    return '详见报告'

def make_table_row(company_md, company_name, rating_cls, idx=None):
    hl = get_highlight(company_md)
    link = f"[查看](companies/{company_md})"
    return f"| {idx or '-'} | {company_name} | {rating_cls} | {hl} | {link} |"

def build_index(results):
    lines = []
    lines.append("# 企业分析报告索引 - 交通银行对公客户深挖\n")
    lines.append("> 生成日期：2026-03-28  |  分析公司总数：49户\n")
    lines.append("---\n")

    for cls_name, cls_key in [('A类客户（重点深挖，优先拜访）', 'A'),
                               ('B类客户（持续跟踪，择机切入）', 'B'),
                               ('C类客户（维护观察，以结算为主）', 'C'),
                               ('D类客户（暂不重点投入）', 'D')]:
        companies = sorted(results[cls_key])
        lines.append(f"## {cls_name}\n")
        lines.append("| 序号 | 公司名称 | 综合评级 | 核心亮点 | 分析报告 |")
        lines.append("|------|---------|---------|---------|---------|")
        for i, c in enumerate(companies, 1):
            lines.append(make_table_row(c + '.md', c, cls_key.replace('A','A类').replace('B','B类').replace('C','C类').replace('D','D类'), i))
        lines.append("\n")

    # Other
    if results['Other']:
        lines.append("## 特殊类型（不参与评级）\n")
        lines.append("| 序号 | 公司名称 | 类型 | 说明 | 分析报告 |")
        lines.append("|------|---------|------|---------|---------|")
        for i, c in enumerate(sorted(results['Other']), 1):
            kind = '工会组织' if '工会' in c else ('有限合伙' if '有限合伙' in c else '已注销')
            link = f"[查看](companies/{c}.md)"
            lines.append(f"| {i} | {c} | {kind} | 非独立商业主体 | {link} |")
        lines.append("\n")

    # 汇总
    a,b,c_d,d,o = len(results['A']),len(results['B']),len(results['C']),len(results['D']),len(results['Other'])
    normal = a+b+c_d+d
    lines.append("---\n## 分类汇总\n\n")
    lines.append("| 分类 | 数量 | 占比 |\n|------|------|------|\n")
    for cls, cnt in [('A类（重点深挖）',a),('B类（持续跟踪）',b),('C类（维护观察）',c_d),('D类（暂不投入）',d),('特殊类型',o)]:
        lines.append(f"| {cls} | {cnt}户 | {cnt*100//normal if normal else 0}% |\n")
    lines.append(f"| **合计** | **{a+b+c_d+d+o}户** | **100%** |\n")
    lines.append("\n---\n*本索引由自动分类脚本生成 · 2026-03-28*\n")
    return '\n'.join(lines)

def rebuild_zip():
    zip_path = f'{OUTPUT_DIR}/企业分析报告_49户.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(f'{OUTPUT_DIR}/index.md', '总览index.md')
        for fname in sorted(os.listdir(COMPANIES_DIR)):
            if fname.endswith('.md'):
                zf.write(os.path.join(COMPANIES_DIR, fname), f'companies/{fname}')
    return zip_path

def send_email(zip_path):
    env = {}
    with open(f'{OUTPUT_DIR}/email_config.env') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                env[k] = v
    msg = MIMEMultipart()
    msg['From'] = env['FROM_ADDR']
    msg['To'] = '769163832@qq.com'
    msg['Subject'] = '【修订版】对公客户深挖分析报告（49户）- zip格式'
    body = MIMEText('您好，附件为【修订版】49户对公客户深挖分析报告（zip格式），已修正分类逻辑。请查收。', 'plain', 'utf-8')
    msg.attach(body)
    with open(zip_path, 'rb') as f:
        part = MIMEBase('application', 'zip')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="企业分析报告_49户.zip"')
        msg.attach(part)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(env['SMTP_HOST'], int(env['SMTP_PORT']), context=context) as server:
        server.login(env['SMTP_USER'], env['SMTP_PASS'])
        server.sendmail(env['FROM_ADDR'], ['769163832@qq.com'], msg.as_string())
    print(f'邮件已发送至 769163832@qq.com')

if __name__ == '__main__':
    results = classify_companies()
    print(f"分类完成: A={len(results['A'])} B={len(results['B'])} C={len(results['C'])} D={len(results['D'])} Other={len(results['Other'])}")
    index_content = build_index(results)
    with open(f'{OUTPUT_DIR}/index.md', 'w') as f:
        f.write(index_content)
    print("index.md 已生成")
    zip_path = rebuild_zip()
    print(f"zip 已打包: {zip_path}")
    send_email(zip_path)
