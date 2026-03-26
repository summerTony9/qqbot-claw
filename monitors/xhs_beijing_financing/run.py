#!/usr/bin/env python3
import json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = json.loads((BASE / 'config.json').read_text())
STATE_PATH = BASE / 'state.json'
RELAY = 'http://127.0.0.1:18792'
TOKEN_FILE = '/tmp/browser-relay-token'


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {'seen_ids': [], 'last_run': None, 'last_status': 'never'}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def read_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    return Path(TOKEN_FILE).read_text().strip()


def request_json(path, method='GET', data=None, token=None, timeout=20):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    else:
        body = None
    req = urllib.request.Request(RELAY + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def relay_ok(token):
    try:
        data = request_json('/health', token=token, timeout=5)
        return data.get('status') == 'ok'
    except Exception:
        return False


def navigate(url, token):
    return request_json('/navigate', method='POST', data={'url': url}, token=token)


def evaluate(expression, token):
    return request_json('/evaluate', method='POST', data={'expression': expression}, token=token)


def extract_cards(token):
    # 仅提取页面中已渲染的帖子卡片公开文本，不读取 cookie/token 等敏感信息。
    js = r'''(() => {
      const cards = Array.from(document.querySelectorAll('section, .note-item, [class*="note"]')).slice(0, 30);
      const out = [];
      for (const el of cards) {
        const text = (el.innerText || '').trim();
        if (!text || text.length < 12) continue;
        const a = el.querySelector('a[href*="/explore/"]') || el.querySelector('a');
        const href = a ? a.href : '';
        const idMatch = href.match(/\/explore\/([^\/?#]+)/);
        const id = idMatch ? idMatch[1] : '';
        out.push({ id, href, text: text.slice(0, 500) });
      }
      return JSON.stringify(out);
    })()'''
    data = evaluate(js, token)
    result = data.get('result')
    if isinstance(result, str):
        try:
            return json.loads(result)
        except Exception:
            return []
    return []


def infer_company(text):
    m = re.search(r'([\u4e00-\u9fa5A-Za-z0-9（）()·]{2,40}(?:公司|企业|集团|科技有限公司|有限责任公司))', text)
    return m.group(1) if m else None


def score_level(text, keyword):
    t = text.lower()
    score = 0
    for s in CONFIG['signal_keywords']:
        if s.lower() in t:
            score += 1
    if '北京' in text:
        score += 1
    if keyword in text:
        score += 1
    if score >= 6:
        return '高'
    if score >= 3:
        return '中'
    return '低'


def normalize_findings(cards, keyword, seen):
    findings = []
    for c in cards:
        cid = c.get('id') or c.get('href') or c.get('text','')[:80]
        if not cid or cid in seen:
            continue
        text = c.get('text', '')
        if keyword.split()[0] not in text and not any(k in text for k in CONFIG['signal_keywords']):
            continue
        findings.append({
            'id': cid,
            'company_name': infer_company(text),
            'user_id': None,
            'nickname': None,
            'content': text,
            'url': c.get('href') or None,
            'published_at': None,
            'matched_keyword': keyword,
            'lead_level': score_level(text, keyword)
        })
    return findings


def run():
    state = load_state()
    token = read_token()
    if not token or not relay_ok(token):
        state['last_run'] = int(time.time())
        state['last_status'] = 'relay_unavailable'
        save_state(state)
        print(json.dumps({'ok': False, 'reason': 'relay_unavailable', 'findings': [], 'summary': 'relay 不可用，未执行采集'}, ensure_ascii=False))
        return 2

    all_findings = []
    seen = set(state.get('seen_ids', []))
    for kw in CONFIG['keywords']:
        url = 'https://www.xiaohongshu.com/search_result?keyword=' + urllib.parse.quote(kw)
        try:
            navigate(url, token)
            time.sleep(3)
            cards = extract_cards(token)
            findings = normalize_findings(cards, kw, seen)
            all_findings.extend(findings[: CONFIG.get('search_limit_per_keyword', 12)])
        except Exception:
            continue

    for item in all_findings:
        seen.add(item['id'])

    state['seen_ids'] = list(seen)[-5000:]
    state['last_run'] = int(time.time())
    state['last_status'] = 'ok'
    save_state(state)

    summary = f'本次新增线索 {len(all_findings)} 条'
    print(json.dumps({'ok': True, 'findings': all_findings, 'summary': summary}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
