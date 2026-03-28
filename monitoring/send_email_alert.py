#!/usr/bin/env python3
import argparse
import json
import smtplib
import sys
from email.mime.text import MIMEText
from email.header import Header
from pathlib import Path

DEFAULT_CONFIG = Path('/root/.config/xhs-monitor/smtp.json')


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f'SMTP config not found: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def build_body(args) -> str:
    if args.body_file:
        return Path(args.body_file).read_text(encoding='utf-8')
    if args.body is not None:
        return args.body
    return sys.stdin.read()


def main():
    p = argparse.ArgumentParser(description='Send email alert for Xiaohongshu monitor')
    p.add_argument('--config', default=str(DEFAULT_CONFIG), help='SMTP config JSON path')
    p.add_argument('--to', dest='recipient', default=None, help='Override recipient')
    p.add_argument('--subject', required=True, help='Email subject')
    p.add_argument('--body', default=None, help='Email body text')
    p.add_argument('--body-file', default=None, help='Read email body from file')
    args = p.parse_args()

    cfg = load_config(Path(args.config))
    sender = cfg['sender']
    username = cfg.get('username', sender)
    password = cfg['password']
    smtp_server = cfg['smtp_server']
    smtp_port = int(cfg.get('smtp_port', 465))
    recipient = args.recipient or cfg.get('recipient') or sender
    body = build_body(args)

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = Header(args.subject, 'utf-8')

    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
        server.login(username, password)
        server.sendmail(sender, [recipient], msg.as_string())

    print('EMAIL_SENT')


if __name__ == '__main__':
    main()
