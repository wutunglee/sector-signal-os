#!/usr/bin/env python3
"""
Sector Signal OS — 主執行腳本 v3
兩津投資公司

使用方式：
  python3 run_report.py --sector "AI 伺服器供應鏈"   # 顯示執行提示
  python3 run_report.py --convert                    # 轉換主報告（零到九節）
  python3 run_report.py --convert --sector "AI 伺服器供應鏈"
  python3 run_report.py --taiwan                     # 產生台股補充報告（第十節）
  python3 run_report.py --taiwan --sector "AI 伺服器供應鏈"
  python3 run_report.py --preview                    # 顯示關鍵字
  python3 run_report.py --site                       # 只更新首頁
"""

import yaml
import argparse
import sys
import subprocess
import os
from datetime import datetime
from pathlib import Path

# ── .env 載入 API Key ──
def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

load_env()

# ── 路徑設定 ──
BASE_DIR     = Path(__file__).parent.parent
CONFIG_DIR   = BASE_DIR / "config"
PROMPTS_DIR  = CONFIG_DIR / "prompts"
OUTPUT_DIR   = BASE_DIR / "output"
REPORTS_DIR  = OUTPUT_DIR / "reports"
SITE_DIR     = OUTPUT_DIR / "site"

for d in [REPORTS_DIR, SITE_DIR, PROMPTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# Prompt 載入
# ══════════════════════════════════════════════════════════════

def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"找不到 Prompt 檔案：{path}")
    content = path.read_text(encoding="utf-8")
    # 移除 YAML front matter（# 開頭的說明行）
    lines = [l for l in content.splitlines() if not l.startswith("# ")]
    return "\n".join(lines).strip()


def render_prompt(template: str, variables: dict) -> str:
    result = template
    for key, value in variables.items():
        result = result.replace("{" + key + "}", str(value))
    return result


# ══════════════════════════════════════════════════════════════
# 設定檔載入
# ══════════════════════════════════════════════════════════════

def load_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ══════════════════════════════════════════════════════════════
# 網站首頁產生器
# ══════════════════════════════════════════════════════════════

def generate_index_html(reports: list[dict]) -> str:
    items = ""
    for r in sorted(reports, key=lambda x: (x["month"], x["sector"]), reverse=True):
        badge_class = "badge-台股" if "台股" in r["sector"] else f"badge-{r['priority']}"
        items += f"""
        <div class="report-item" data-search="{r['sector']} {r['month']}">
          <span class="report-month">{r['month']}</span>
          <a href="{r['filename']}" class="report-title">{r['sector']}</a>
          <span class="report-badge {badge_class}">{"台股補充" if "台股" in r["sector"] else r["priority"]}</span>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>兩津投資 — Sector Signal Brief</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Noto Sans TC", sans-serif; background: #f7f5ef; color: #1a1a18; max-width: 800px; margin: 0 auto; padding: 2rem 1.5rem; }}
  header {{ border-bottom: 2px solid #1a1a18; padding-bottom: 1rem; margin-bottom: 2rem; }}
  .site-title {{ font-size: 22px; font-weight: 700; }}
  .site-sub {{ font-size: 13px; color: #7a7a74; margin-top: 4px; }}
  .search-bar {{ width: 100%; padding: 10px 14px; border: 1px solid #c8c5ba; background: white; font-size: 14px; margin-bottom: 1.5rem; border-radius: 4px; }}
  .search-bar:focus {{ outline: none; border-color: #1a1a18; }}
  .report-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .report-item {{ display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: white; border: 1px solid #e2dfd4; border-radius: 4px; }}
  .report-item.hidden {{ display: none; }}
  .report-month {{ font-family: monospace; font-size: 12px; color: #7a7a74; min-width: 70px; }}
  .report-title {{ font-size: 14px; color: #1a1a18; text-decoration: none; flex: 1; }}
  .report-title:hover {{ text-decoration: underline; }}
  .report-badge {{ font-size: 10px; padding: 2px 8px; border-radius: 2px; font-family: monospace; white-space: nowrap; }}
  .badge-高 {{ background: #e8f3e8; color: #0f6e56; }}
  .badge-中 {{ background: #faf0d0; color: #7a5a00; }}
  .badge-低 {{ background: #f1efe8; color: #7a7a74; }}
  .badge-台股 {{ background: #e8edf8; color: #1a4a8a; }}
  .no-results {{ text-align: center; color: #7a7a74; padding: 2rem; display: none; }}
  footer {{ margin-top: 3rem; font-size: 12px; color: #b0afa8; text-align: center; }}
</style>
</head>
<body>
<header>
  <div class="site-title">兩津投資公司</div>
  <div class="site-sub">Sector Signal Brief — 產業訊號月報</div>
</header>
<input class="search-bar" type="text" placeholder="搜尋月份或產業名稱..." id="search" oninput="filterReports(this.value)">
<div class="report-list" id="report-list">{items}</div>
<div class="no-results" id="no-results">沒有符合的月報</div>
<footer>兩津投資公司 內部使用 — 不構成投資建議</footer>
<script>
function filterReports(q) {{
  const items = document.querySelectorAll('.report-item');
  const kw = q.toLowerCase();
  let visible = 0;
  items.forEach(item => {{
    const match = item.dataset.search.toLowerCase().includes(kw);
    item.classList.toggle('hidden', !match);
    if (match) visible++;
  }});
  document.getElementById('no-results').style.display = visible === 0 ? 'block' : 'none';
}}
</script>
</body>
</html>"""


def scan_existing_reports() -> list[dict]:
    reports = []
    for f in REPORTS_DIR.glob("*.md"):
        # 跳過 prompt 和 taiwan_prompt 檔案
        if "_prompt" in f.name:
            continue
        # 解析檔名：YYYY-MM_產業名稱[_台股].md
        stem = f.stem  # e.g. 2026-06_AI伺服器供應鏈 or 2026-06_AI伺服器供應鏈_台股
        parts = stem.split("_", 1)
        if len(parts) < 2:
            continue
        month = parts[0]
        sector_raw = parts[1].replace("_", " ")
        is_taiwan = sector_raw.endswith(" 台股")

        reports.append({
            "month":    month,
            "sector":   sector_raw,
            "filename": f"reports/{stem}.html",
            "priority": "台股" if is_taiwan else "中",
        })
    return reports


def update_site_index():
    html = generate_index_html(scan_existing_reports())
    index_path = SITE_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ 網站首頁已更新")


# ══════════════════════════════════════════════════════════════
# 原始檔尋找
# ══════════════════════════════════════════════════════════════

def find_last30days_raw(sector: dict) -> Path | None:
    d = Path.home() / "Documents" / "Last30Days"
    if not d.exists():
        return None
    keywords = sector.get("核心關鍵字", [])
    candidates = sorted(d.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    # 嘗試用關鍵字匹配
    for f in candidates:
        fname = f.name.lower()
        if any(k.split()[0].lower() in fname for k in keywords[:3]):
            return f
    # 找不到就回傳最新的
    return candidates[0] if candidates else None


# ══════════════════════════════════════════════════════════════
# 選題說明區塊
# ══════════════════════════════════════════════════════════════

def build_selection_block(selection_note: dict) -> str:
    if not selection_note:
        return ""
    reasons = selection_note.get("選題理由", [])
    if not any(r for r in reasons if r):
        return ""
    scan_date   = selection_note.get("掃描日期", "")
    all_sectors = "、".join(selection_note.get("本月選定產業", []))
    reasons_str = "\n".join(f"  - {r}" for r in reasons if r)
    excluded    = "、".join(selection_note.get("排除的熱門話題", [])) or "無"
    return f"""
===== 本月選題背景 =====
掃描日期：{scan_date}
本月選定產業：{all_sectors}
選題理由：
{reasons_str}
本月排除的熱門話題：{excluded}
========================
"""


# ══════════════════════════════════════════════════════════════
# API 呼叫（主報告 + 台股補充共用）
# ══════════════════════════════════════════════════════════════

def call_claude_api(prompt: str, use_web_search: bool = False, timeout: int = 600) -> str | None:
    """用 Anthropic API 呼叫 Claude，可選開啟 web search"""
    try:
        import anthropic
    except ImportError:
        print("    ✗ 請先安裝：pip3 install anthropic --break-system-packages")
        return None

    client = anthropic.Anthropic()

    kwargs = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
    }

    if use_web_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    try:
        response = client.messages.create(**kwargs)
        # 擷取所有 text 區塊
        result = ""
        for block in response.content:
            if block.type == "text":
                result += block.text
        return result.strip() if result else None
    except Exception as e:
        print(f"    ✗ API 錯誤：{e}")
        return None


# ══════════════════════════════════════════════════════════════
# 主報告轉換（零到九節，不含台股）
# ══════════════════════════════════════════════════════════════

def convert_main_report(
    raw_file: Path,
    sector: dict,
    global_cfg: dict,
    month: str,
    selection_note: dict = None
) -> str | None:

    name      = sector["名稱"]
    tw_stocks = sector.get("台股觀察名單", [])
    us_stocks = sector.get("美股觀察名單", [])
    max_sig   = global_cfg.get("每產業最多訊號數", 5)
    tw_list   = "、".join(f"{c['ticker']} {c['名稱']}" for c in tw_stocks)
    us_list   = "、".join(f"{c['ticker']} {c['名稱']}" for c in us_stocks)

    try:
        raw_content = raw_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"    ✗ 無法讀取原始檔：{e}")
        return None

    if len(raw_content) > 8000:
        raw_content = raw_content[:8000] + "\n\n[... 內容截斷 ...]"

    selection_block = build_selection_block(selection_note)

    try:
        template = load_prompt("convert_report")
    except FileNotFoundError as e:
        print(f"    ✗ {e}")
        return None

    prompt = render_prompt(template, {
        "selection_block": selection_block,
        "tw_list":         tw_list,
        "us_list":         us_list,
        "raw_content":     raw_content,
        "sector_name":     name,
        "month":           month,
        "max_sig":         max_sig,
    })

    print(f"    ⏳ 呼叫 Claude API 轉換主報告...")
    return call_claude_api(prompt, use_web_search=False)


# ══════════════════════════════════════════════════════════════
# 台股補充報告（獨立一份，使用 web search）
# ══════════════════════════════════════════════════════════════

def generate_taiwan_report(
    sector: dict,
    month: str
) -> str | None:

    name      = sector["名稱"]
    tw_stocks = sector.get("台股觀察名單", [])
    if not tw_stocks:
        print(f"    ⚠ 此產業無台股觀察名單，跳過")
        return None

    tw_list = "、".join(f"{c['ticker']} {c['名稱']}" for c in tw_stocks)

    try:
        template = load_prompt("taiwan_supplement")
    except FileNotFoundError as e:
        print(f"    ✗ {e}")
        return None

    prompt = render_prompt(template, {
        "sector_name":   name,
        "month":         month,
        "tw_companies":  tw_list,
    })

    print(f"    ⏳ 呼叫 Claude API（含 web search）搜尋台股資料...")
    return call_claude_api(prompt, use_web_search=True, timeout=600)


# ══════════════════════════════════════════════════════════════
# 檔案儲存
# ══════════════════════════════════════════════════════════════

def save_report(sector_name: str, content: str, month: str, suffix: str = "") -> Path:
    """
    命名規則：
      主報告：2026-06_AI伺服器供應鏈.md
      台股：  2026-06_AI伺服器供應鏈_台股.md
    """
    safe_name = sector_name.replace(" ", "").replace("/", "-")
    filename  = f"{month}_{safe_name}"
    if suffix:
        filename += f"_{suffix}"
    path = REPORTS_DIR / f"{filename}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ══════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Sector Signal OS — 兩津投資公司")
    parser.add_argument("--config",  default=str(BASE_DIR / "config" / "research_config.yaml"))
    parser.add_argument("--sector",  default=None)
    parser.add_argument("--preview", action="store_true", help="顯示本月 last30days 關鍵字")
    parser.add_argument("--convert", action="store_true", help="轉換主報告（零到九節）")
    parser.add_argument("--taiwan",  action="store_true", help="產生台股補充報告（獨立一份）")
    parser.add_argument("--site",    action="store_true", help="只更新靜態網站首頁")
    args = parser.parse_args()

    config         = load_config(Path(args.config))
    month          = config.get("月份", datetime.now().strftime("%Y-%m"))
    global_cfg     = config.get("全域設定", {})
    sectors        = config.get("產業方向", [])
    selection_note = config.get("選題說明", {})

    print(f"\n{'═'*55}")
    print(f"  Sector Signal OS — 兩津投資公司")
    print(f"  月份：{month}")
    print(f"{'═'*55}\n")

    if args.site:
        update_site_index()
        return

    active_sectors = [
        s for s in sectors
        if s.get("狀態") in ("進行中", "新增")
        and (args.sector is None or s["名稱"] == args.sector)
    ]

    if not active_sectors:
        print("  ⚠ 沒有找到符合條件的產業方向")
        sys.exit(1)

    for sector in active_sectors:
        name = sector["名稱"]
        print(f"  ▶ {name}")

        if args.preview:
            kw = " ".join(sector.get("核心關鍵字", [])[:6])
            print(f"    請在 Claude Code 執行：")
            print(f"    /last30days {kw}\n")

        elif args.convert:
            raw_file = find_last30days_raw(sector)
            if not raw_file:
                kw = " ".join(sector.get("核心關鍵字", [])[:4])
                print(f"    ⚠ 找不到原始檔，請先執行：")
                print(f"      /last30days {kw}")
            else:
                print(f"    📄 原始檔：{raw_file.name}")
                content = convert_main_report(raw_file, sector, global_cfg, month, selection_note)
                if content:
                    path = save_report(name, content, month)
                    print(f"    ✓ 主報告已儲存：{path.name}")
                else:
                    print(f"    ✗ 轉換失敗")

        elif args.taiwan:
            content = generate_taiwan_report(sector, month)
            if content:
                path = save_report(name, content, month, suffix="台股")
                print(f"    ✓ 台股補充報告已儲存：{path.name}")
            else:
                print(f"    ✗ 台股報告產生失敗")

        else:
            kw = " ".join(sector.get("核心關鍵字", [])[:6])
            print(f"    請在 Claude Code 執行：")
            print(f"      /last30days {kw}")
            print(f"    完成後執行：python3 scripts/run_report.py --convert --sector \"{name}\"")
            print(f"    台股補充：  python3 scripts/run_report.py --taiwan --sector \"{name}\"")
        print()

    update_site_index()
    print(f"{'═'*55}")
    print(f"  完成！報告：{REPORTS_DIR}")
    print(f"  網站：{SITE_DIR / 'index.html'}")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()
