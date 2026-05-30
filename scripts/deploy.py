#!/usr/bin/env python3
"""
Sector Signal OS — 靜態網頁發布腳本 v4
台股報告用 <ol> 結構化每家公司欄位
"""

import re
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "output" / "reports"
SITE_DIR    = BASE_DIR / "output" / "site"
DOCS_DIR    = BASE_DIR / "docs"

TAIWAN_FIELDS = ['月營收', '訊號分類', '重要資訊', '與國際訊號的關聯', '噪音風險']


def convert_md_table(block: str) -> str:
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return block
    html = ['<div class="table-wrap"><table>']
    for i, line in enumerate(lines):
        if re.match(r'^\|[-| :]+\|$', line):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        tag = 'th' if i == 0 else 'td'
        html.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
    html.append('</table></div>')
    return '\n'.join(html)


def convert_taiwan_company_block(block: str) -> str:
    """把一家公司的 Markdown 區塊轉成 HTML ol 結構"""
    lines = block.strip().splitlines()
    if not lines:
        return block

    title_match = re.match(r'^####\s+(.+)$', lines[0].strip())
    if not title_match:
        return block

    company_title = title_match.group(1)
    html = f'<div class="company-block">\n<h4>{company_title}</h4>\n<ol class="company-fields">\n'

    current_field = None
    current_content = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        matched = False
        for field in TAIWAN_FIELDS:
            for sep in ['：**', ':**']:
                pattern = f'**{field}{sep}'
                if line.startswith(pattern):
                    if current_field:
                        content = ' '.join(current_content).strip()
                        html += f'  <li><strong>{current_field}：</strong><span>{content}</span></li>\n'
                    current_field = field
                    current_content = [line[len(pattern):].strip()]
                    matched = True
                    break
            if matched:
                break

        if not matched and current_field:
            current_content.append(line)

    if current_field:
        content = ' '.join(current_content).strip()
        html += f'  <li><strong>{current_field}：</strong><span>{content}</span></li>\n'

    html += '</ol>\n</div>'
    return html


def preprocess_taiwan(md: str) -> str:
    """把台股報告中每家公司的 #### 區塊轉成 ol 結構"""
    # 用 #### 分割公司區塊
    parts = re.split(r'\n(?=####)', md)
    result = []
    for part in parts:
        if part.strip().startswith('####'):
            result.append(convert_taiwan_company_block(part))
        else:
            result.append(part)
    return '\n\n'.join(result)


def md_to_html(md: str, title: str, is_taiwan: bool = False) -> str:
    html_body = md

    # 台股報告：先把公司區塊轉成 ol 結構
    if is_taiwan:
        html_body = preprocess_taiwan(html_body)

    # 表格
    html_body = re.sub(r'((?:\|.+\|\n?)+)', lambda m: convert_md_table(m.group(0)), html_body)

    # 標題
    html_body = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^## (.+)$',  r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
    html_body = re.sub(r'^# (.+)$',   r'<h1>\1</h1>', html_body, flags=re.MULTILINE)

    # 主報告產業鏈段落拆分
    if not is_taiwan:
        html_body = re.sub(
            r'\*\*((?:上游|中游|下游|終端應用|\[警示)[^*]*)\*\*',
            r'\n\n<h4>\1</h4>',
            html_body
        )

    # 粗體
    html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)

    # 勾選框
    html_body = html_body.replace('- [ ]', '<li class="todo"><input type="checkbox" disabled>')
    html_body = html_body.replace('- [x]', '<li class="todo done"><input type="checkbox" checked disabled>')

    # 列表
    html_body = re.sub(r'^- (.+)$', r'<li>\1</li>', html_body, flags=re.MULTILINE)

    # ── 有序列表（1. 2. 3.）
    # 先把連續的數字列表行包成 <ol>
    def wrap_ordered_list(text):
        lines = text.splitlines()
        result = []
        in_ol = False
        for line in lines:
            if re.match(r'^\d+\.\s+', line):
                if not in_ol:
                    result.append('<ol>')
                    in_ol = True
                item = re.sub(r'^\d+\.\s+', '', line)
                result.append(f'<li>{item}</li>')
            else:
                if in_ol:
                    result.append('</ol>')
                    in_ol = False
                result.append(line)
        if in_ol:
            result.append('</ol>')
        return '\n'.join(result)
    html_body = wrap_ordered_list(html_body)

    # ── 分隔線
    html_body = re.sub(r'^---+$', '<hr>', html_body, flags=re.MULTILINE)

    # 引用
    html_body = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html_body, flags=re.MULTILINE)

    # 段落
    paragraphs = html_body.split('\n\n')
    html_body = '\n\n'.join(
        f'<p>{p.strip()}</p>' if not p.strip().startswith('<') else p
        for p in paragraphs if p.strip()
    )

    taiwan_badge = '<span class="taiwan-badge">台股補充</span>' if is_taiwan else ""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — 兩津投資</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, "Noto Sans TC", sans-serif;
    background: #f7f5ef; color: #1a1a18;
    max-width: 860px; margin: 0 auto;
    padding: 2rem 1.5rem; line-height: 1.8; font-size: 15px;
  }}
  h1 {{ font-size: 24px; font-weight: 700; margin: 2rem 0 0.4rem; border-bottom: 2px solid #1a1a18; padding-bottom: 0.5rem; }}
  h2 {{ font-size: 15px; font-weight: 400; color: #7a7a74; margin-bottom: 2rem; }}
  h3 {{ font-size: 17px; font-weight: 700; margin: 2.5rem 0 1rem; color: #8b2500; border-left: 3px solid #8b2500; padding-left: 0.75rem; }}
  h4 {{ font-size: 15px; font-weight: 700; margin: 1.75rem 0 0.5rem; color: #1a1a18; padding-bottom: 0.2rem; border-bottom: 1px dashed #c8c5ba; }}
  p {{ margin-bottom: 1rem; color: #3d3d39; }}
  strong {{ color: #1a1a18; font-weight: 600; }}
  blockquote {{ border-left: 3px solid #c8c5ba; padding: 0.5rem 1rem; margin: 1rem 0; background: #f0ede6; color: #5a5a54; font-size: 13px; }}
  li {{ margin: 0.35rem 0 0.35rem 1.5rem; font-size: 14px; color: #3d3d39; line-height: 1.7; }}
  li.todo {{ list-style: none; margin-left: 0; }}
  li.done {{ opacity: 0.5; text-decoration: line-through; }}
  hr {{ border: none; border-top: 1px solid #e2dfd4; margin: 2rem 0; }}
  .table-wrap {{ overflow-x: auto; margin: 1.25rem 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #e2dfd4; padding: 9px 14px; text-align: left; font-weight: 600; border: 1px solid #c8c5ba; }}
  td {{ padding: 9px 14px; border: 1px solid #c8c5ba; vertical-align: top; color: #3d3d39; line-height: 1.6; }}
  tr:nth-child(even) td {{ background: #f7f5ef; }}
  /* 台股公司區塊 */
  .company-block {{ margin: 2rem 0; padding: 1.25rem 1.5rem; background: white; border: 1px solid #e2dfd4; border-radius: 4px; }}
  .company-block h4 {{ margin-top: 0; font-size: 16px; color: #1a1a18; border-bottom: 2px solid #8b2500; padding-bottom: 0.4rem; margin-bottom: 1rem; }}
  ol.company-fields {{ list-style: none; padding: 0; margin: 0; }}
  ol.company-fields li {{ padding: 0.75rem 0; border-bottom: 1px solid #f0ede6; margin: 0; font-size: 14px; line-height: 1.7; }}
  ol.company-fields li:last-child {{ border-bottom: none; }}
  ol.company-fields li strong {{ display: block; color: #8b2500; font-size: 12px; letter-spacing: 0.05em; margin-bottom: 0.2rem; }}
  ol.company-fields li span {{ color: #3d3d39; }}
  /* 導覽 */
  .nav-bar {{ display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem; }}
  .back-link {{ font-size: 13px; color: #7a7a74; text-decoration: none; }}
  .back-link:hover {{ color: #1a1a18; }}
  .taiwan-badge {{ font-size: 11px; background: #e8edf8; color: #1a4a8a; padding: 2px 10px; border-radius: 2px; font-family: monospace; }}
  footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e2dfd4; font-size: 12px; color: #b0afa8; display: flex; justify-content: space-between; }}
</style>
</head>
<body>
<div class="nav-bar">
  <a class="back-link" href="../index.html">← 回到月報清單</a>
  {taiwan_badge}
</div>
{html_body}
<footer>
  <span>兩津投資公司 內部使用</span>
  <span>不構成投資建議</span>
</footer>
</body>
</html>"""


def convert_all_reports():
    converted = []
    report_html_dir = SITE_DIR / "reports"
    report_html_dir.mkdir(parents=True, exist_ok=True)

    for md_file in REPORTS_DIR.glob("*.md"):
        if "_prompt" in md_file.name:
            continue
        stem      = md_file.stem
        html_file = report_html_dir / f"{stem}.html"
        is_taiwan = stem.endswith("_台股")
        parts = stem.split("_", 1)
        title = f"{parts[0]} {parts[1]}".replace("_", " ") if len(parts) == 2 else stem

        md_content = md_file.read_text(encoding="utf-8")
        html_file.write_text(md_to_html(md_content, title, is_taiwan=is_taiwan), encoding="utf-8")
        converted.append(html_file)
        print(f"  ✓ {html_file.name}{' [台股]' if is_taiwan else ''}")

    return converted


def update_site_index():
    subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "run_report.py"), "--site"], cwd=BASE_DIR)


def sync_to_docs():
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    shutil.copytree(SITE_DIR, DOCS_DIR)
    print("  ✓ 已同步到 docs/")


def push_to_github(dry_run=False):
    result = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=BASE_DIR, capture_output=True)
    if result.returncode != 0:
        print("  ⚠ 尚未初始化 git repo")
        return
    if dry_run:
        print("  [dry-run] 跳過 git push")
        return
    for cmd in [["git", "add", "docs/"], ["git", "commit", "-m", f"月報更新 {datetime.now().strftime('%Y-%m-%d')}"], ["git", "push", "origin", "main"]]:
        r = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  ✓ {' '.join(cmd[:2])}")
        else:
            if "nothing to commit" in r.stdout + r.stderr:
                print("  ✓ 無新變更")
            else:
                print(f"  ✗ {r.stderr[:100]}")
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"\n{'═'*50}\n  Sector Signal OS — 發布腳本 v4\n{'═'*50}\n")
    print("  步驟一：轉換 Markdown → HTML")
    converted = convert_all_reports()
    print(f"  共轉換 {len(converted)} 份報告\n")
    print("  步驟二：更新網站首頁")
    update_site_index()
    print("\n  步驟三：同步到 docs/")
    sync_to_docs()
    print("\n  步驟四：推送到 GitHub")
    push_to_github(dry_run=args.dry_run)
    print(f"\n{'═'*50}\n  完成！https://wutunglee.github.io/sector-signal-os\n{'═'*50}\n")


if __name__ == "__main__":
    main()
