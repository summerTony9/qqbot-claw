#!/usr/bin/env python3
import argparse
import json
import mimetypes
import smtplib
import sys
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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


def attach_file(msg: MIMEMultipart, file_path: str):
    path = Path(file_path)
    data = path.read_bytes()
    ctype, _ = mimetypes.guess_type(str(path))
    if ctype == 'text/markdown' or path.suffix.lower() == '.md':
        part = MIMEText(data.decode('utf-8'), 'markdown', 'utf-8')
    elif ctype and ctype.startswith('text/'):
        subtype = ctype.split('/', 1)[1]
        part = MIMEText(data.decode('utf-8', errors='ignore'), subtype, 'utf-8')
    else:
        part = MIMEApplication(data)
    part.add_header('Content-Disposition', 'attachment', filename=path.name)
    msg.attach(part)


def main():
    p = argparse.ArgumentParser(description='Send email alert for Xiaohongshu monitor')
    p.add_argument('--config', default=str(DEFAULT_CONFIG), help='SMTP config JSON path')
    p.add_argument('--to', dest='recipient', default=None, help='Override recipient')
    p.add_argument('--subject', required=True, help='Email subject')
    p.add_argument('--body', default=None, help='Email body text')
    p.add_argument('--body-file', default=None, help='Read email body from file')
    p.add_argument('--attach', action='append', default=[], help='Attach a file (repeatable)')
    args = p.parse_args()

    cfg = load_config(Path(args.config))
    sender = cfg['sender']
    username = cfg.get('username', sender)
    password = cfg['password']
    smtp_server = cfg['smtp_server']
    smtp_port = int(cfg.get('smtp_port', 465))
    recipient = args.recipient or cfg.get('recipient') or sender
    body = build_body(args)

    if args.attach:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        for file_path in args.attach:
            attach_file(msg, file_path)
    else:
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
