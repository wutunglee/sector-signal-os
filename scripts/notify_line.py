#!/usr/bin/env python3
"""
Sector Signal OS — Line 通知腳本
自動擷取月報摘要，發送到 Line 群組

使用方式：
  python3 notify_line.py                        # 發送所有本月報告摘要
  python3 notify_line.py --sector "AI 伺服器"   # 發送指定產業
  python3 notify_line.py --dry-run              # 只顯示訊息，不發送

設定方式：
  1. 到 https://developers.line.biz/ 建立 Messaging API Channel
  2. 取得 Channel Access Token
  3. 建立 .env 檔案（見下方說明）

.env 檔案內容：
  LINE_CHANNEL_TOKEN=你的 Channel Access Token
  LINE_GROUP_ID=群組的 Group ID（從 webhook 事件取得）
  SITE_BASE_URL=https://你的帳號.github.io/sector-signal-os
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "output" / "reports"
CONFIG_DIR  = BASE_DIR / "config"


# ── 環境變數載入 ──

def load_env():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

    token    = os.environ.get("LINE_CHANNEL_TOKEN", "")
    group_id = os.environ.get("LINE_GROUP_ID", "")
    site_url = os.environ.get("SITE_BASE_URL", "https://yourusername.github.io/sector-signal-os")
    return token, group_id, site_url


# ── 從月報 Markdown 擷取摘要 ──

def extract_summary(md_content: str, max_chars: int = 300) -> str:
    """擷取執行摘要段落"""
    # 找「一、Executive Summary」區塊
    match = re.search(
        r'### 一、Executive Summary[^\n]*\n+(.*?)(?=\n###|\Z)',
        md_content, re.DOTALL
    )
    if match:
        summary = match.group(1).strip()
        # 清除 Markdown 標記
        summary = re.sub(r'\*\*(.+?)\*\*', r'\1', summary)
        summary = re.sub(r'#+\s', '', summary)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."
        return summary
    return "（無法擷取摘要，請點連結查看完整報告）"


def extract_top_signals(md_content: str, max_signals: int = 3) -> list[str]:
    """擷取前幾個訊號標題"""
    signals = re.findall(r'\*\*(.+?)\*\*', md_content)
    # 過濾掉欄位標籤（通常是短字串如「訊號分類：」）
    signals = [s for s in signals if len(s) > 10 and "：" not in s]
    return signals[:max_signals]


# ── 組成 Line 訊息 ──

def build_line_message(
    sector: str,
    month: str,
    summary: str,
    signals: list[str],
    report_url: str
) -> str:

    signals_str = "\n".join(f"  • {s}" for s in signals) if signals else "  （請查看完整報告）"

    return f"""📊 兩津投資 Sector Signal Brief
━━━━━━━━━━━━━━━
{month} | {sector}
━━━━━━━━━━━━━━━

{summary}

本月重點訊號：
{signals_str}

▶ 完整報告：
{report_url}
━━━━━━━━━━━━━━━
不構成投資建議"""


# ── 發送 Line 訊息 ──

def send_line_message(token: str, group_id: str, text: str) -> bool:
    url     = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = json.dumps({
        "to": group_id,
        "messages": [{"type": "text", "text": text}]
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  ✗ Line API 錯誤：{e}")
        return False


# ── 主流程 ──

def main():
    parser = argparse.ArgumentParser(description="Sector Signal OS — Line 通知")
    parser.add_argument("--sector",  default=None, help="指定產業名稱")
    parser.add_argument("--dry-run", action="store_true", help="只顯示訊息內容，不發送")
    args = parser.parse_args()

    load_env()
    token, group_id, site_url = load_env()

    if not args.dry_run and (not token or not group_id):
        print("  ✗ 請設定 .env 檔案（LINE_CHANNEL_TOKEN 和 LINE_GROUP_ID）")
        print("  提示：python3 notify_line.py --dry-run 可預覽訊息內容")
        sys.exit(1)

    # 尋找本月報告
    today   = datetime.now()
    month   = today.strftime("%Y-%m")
    pattern = f"{month}_*_report.md"

    report_files = list(REPORTS_DIR.glob(pattern))
    if args.sector:
        safe = args.sector.replace(" ", "_").replace("/", "-")
        report_files = [f for f in report_files if safe in f.name]

    if not report_files:
        print(f"  ⚠ 找不到 {month} 的報告，請先執行 run_report.py")
        sys.exit(1)

    print(f"\n{'═'*50}")
    print("  Sector Signal OS — Line 通知")
    print(f"{'═'*50}\n")

    for report_file in sorted(report_files):
        parts        = report_file.stem.split("_", 1)
        report_month = parts[0] if len(parts) >= 1 else month
        sector_raw   = parts[1].replace("_report", "").replace("_", " ") if len(parts) >= 2 else "未知產業"

        with open(report_file, "r", encoding="utf-8") as f:
            md_content = f.read()

        summary  = extract_summary(md_content)
        signals  = extract_top_signals(md_content)
        safe_name = sector_raw.replace(" ", "_")
        report_url = f"{site_url}/reports/{report_file.stem.replace('.md', '')}.html"
        message  = build_line_message(sector_raw, report_month, summary, signals, report_url)

        print(f"  產業：{sector_raw}")
        print(f"{'─'*40}")
        print(message)
        print(f"{'─'*40}\n")

        if not args.dry_run:
            ok = send_line_message(token, group_id, message)
            if ok:
                print(f"  ✓ 已發送到 Line 群組\n")
            else:
                print(f"  ✗ 發送失敗\n")
        else:
            print(f"  [dry-run] 未實際發送\n")

    print(f"{'═'*50}\n")


if __name__ == "__main__":
    main()
