# Sector Signal OS
## 兩津投資公司 — 產業訊號月報系統

---

## 系統架構

```
sector-signal-os/
├── config/
│   └── research_config.yaml   ← 每月月會後修改這個
├── scripts/
│   ├── run_report.py          ← 主執行腳本（產生報告）
│   ├── deploy.py              ← 發布到 GitHub Pages
│   └── notify_line.py         ← 發送 Line 通知
├── output/
│   ├── reports/               ← 月報 Markdown 與 Prompt 檔案
│   └── site/                  ← 靜態網站（推送到 GitHub Pages）
│       ├── index.html         ← 首頁（含搜尋功能）
│       └── reports/           ← 各月報 HTML 頁面
└── .env                       ← Line API 設定（不要 commit）
```

---

## 一次性設定（只需做一次）

### 1. 安裝環境

```bash
# 確認 Python 3.9+
python3 --version

# 安裝必要套件
pip3 install pyyaml

# 安裝 Claude Code（如尚未安裝）
curl -fsSL https://claude.ai/install.sh | bash

# 安裝 last30days skill
claude /plugin marketplace add mvanhorn/last30days-skill
```

### 2. 建立 GitHub Repo

```bash
# 在 GitHub 建立新 repo：sector-signal-os
# 然後在本機：
git init
git remote add origin https://github.com/[你的帳號]/sector-signal-os.git

# GitHub Pages 設定：
# repo Settings → Pages → Source: Deploy from branch
# Branch: main / Folder: output/site
```

### 3. 設定 Line Bot（長期方案）

```bash
# 建立 .env 檔案
cat > .env << 'EOF'
LINE_CHANNEL_TOKEN=你的 Channel Access Token
LINE_GROUP_ID=群組的 Group ID
SITE_BASE_URL=https://[你的帳號].github.io/sector-signal-os
EOF
```

Line Bot 申請步驟：
1. 到 https://developers.line.biz/ 登入
2. 建立 Provider → 建立 Messaging API Channel
3. 在 Basic settings 取得 Channel Access Token
4. 把 Bot 加入兩津 Line 群組
5. 從 webhook 收到的第一個群組訊息取得 Group ID

---

## 每月操作流程

### 月會後（約 10 分鐘）

```bash
# 1. 更新研究設定
nano config/research_config.yaml
#    → 修改月份、調整產業方向、更新關鍵字、調整觀察名單

# 2. 確認設定（預覽 Prompt）
python3 scripts/run_report.py --preview
```

### 執行月報（約 20–30 分鐘）

```bash
# 執行所有進行中的產業
python3 scripts/run_report.py

# 或只執行指定產業
python3 scripts/run_report.py --sector "AI 伺服器供應鏈"

# 同時產生台灣在地訊號補充 Prompt（月營收公布後）
python3 scripts/run_report.py --taiwan
```

### 發布與通知

```bash
# 發布到 GitHub Pages
python3 scripts/deploy.py

# 發送 Line 通知（預覽）
python3 scripts/notify_line.py --dry-run

# 實際發送 Line 通知
python3 scripts/notify_line.py
```

---

## 如何調整研究方向

打開 `config/research_config.yaml`，可以做以下調整：

### 新增產業
```yaml
- 名稱: "車用半導體"
  狀態: "新增"
  優先級: "中"
  核心關鍵字:
    - "automotive MCU SiC"
    - "ADAS supply chain"
  台股觀察名單: []
  美股觀察名單:
    - ticker: "ON"
      名稱: "ON Semiconductor"
      層級: "A"
```

### 暫停一個產業
```yaml
狀態: "暫停"   # 改為暫停即不執行
```

### 本月特別關注
```yaml
額外聚焦:
  - "NVIDIA GB300 supply timeline"
  - "台達電 Q2 毛利率展望"
```

### 調整觀察公司
直接在 `台股觀察名單` 或 `美股觀察名單` 增減公司即可。

---

## 未來擴充方向（第二階段）

- [ ] HackMD API 自動發布（短期補充）
- [ ] 月報搜尋功能加強（全文搜尋）
- [ ] 靜態網站加入互動式 To-Do 勾選
- [ ] 自動偵測月營收公布日，觸發台灣補充報告
- [ ] 簡易 Web UI 讓成員直接修改 research_config.yaml

---

## 注意事項

- `.env` 檔案包含 API Token，不要 commit 到 GitHub（已加入 .gitignore）
- 月報為兩津投資公司內部研究用途，不構成投資建議
- last30days skill 每次執行約消耗 150k–300k tokens，請注意 API 用量
