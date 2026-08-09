# ✈️ 機場航班資訊儀表板

一個以 **每日自動爬取的機場官方 API 資料** 為基礎,用 Streamlit 打造的互動式航班分析儀表板。涵蓋台灣桃園國際機場(TPE)與高雄國際機場(KHH)的離境 / 到場航班資訊。

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![License](https://img.shields.io/badge/license-MIT-green)

**🔗 [線上 Demo]((https://tpekhhairline-jjhcwfvjjkqkrq3pwwkpfu.streamlit.app/))**

---

## 專案簡介

這個專案的資料並非取用現成的政府開放資料集,而是**自行開發爬蟲程式,每天定時從機場官方網站 API 抓取最新航班資訊**,經過清洗後存入 SQLite 資料庫,再透過 Streamlit + Plotly 打造成一個可互動篩選的視覺化儀表板。

專案目標:**資料擷取 → 清洗 → 儲存 → 視覺化**

## 主要功能

- **多層級篩選**
  - 機場(TPE / KHH,單選 + 全選)
  - 航班類型(離境 / 到場,單選 + 全選)
  - 日期範圍
  - 目的地:**地區 → 國家/地區 → 目的地** 三層連動篩選(例如:亞洲 → 日本 → 福岡)
  - 航空公司:連動所選機場與目的地,只顯示實際有該航線的航空公司
- **KPI 總覽卡片**:總航班數、航空公司數、目的地數、機型數
- **每日航班趨勢圖**:依機場分色的每日航班數線圖
- **熱門目的地 / 航空公司排行**:依航空公司分色的並排長條圖,方便比較不同航空公司在同一航線的班次
- **航班類型比例圖**、**機型分佈圖**
- **航線地圖**:以出發機場為起點畫出航線,依航空公司分色,滑鼠移過可查看航班數
- **航班明細資料表**:可依目前篩選條件即時查看原始資料

## 技術架構

```
GitHub Actions(每日排程,台灣時間 00:30 自動觸發)
    │
    ├─ Scraper_TPE.py  抓取桃園機場官方 API
    ├─ Scraper_KHH.py  抓取高雄機場開放資料 API
    │
    ▼ (抓取後直接清洗:欄位整理、機型轉 ICAO 代碼、目的地名稱統一)
SQLite (flights.db)
    │  KHH_Flight_cleared / TPE_Flight_cleared
    │  自動 commit + push 回 repo
    ▼
Streamlit + Pandas + Plotly (app.py)
    │
    ▼
互動式 Web 儀表板(Streamlit Community Cloud)
```

| 項目 | 技術 |
|---|---|
| 資料擷取 | Python(`requests`),呼叫機場官方 API |
| 排程自動化 | GitHub Actions(每日定時執行 + 自動 commit) |
| 資料儲存 | SQLite |
| 資料處理 | pandas |
| 視覺化 | Plotly Express / Plotly Graph Objects |
| 前端介面 | Streamlit |

## 專案結構

```
.
├── app.py                        # Streamlit 主程式(篩選邏輯、圖表、地圖)
├── Scraper_TPE.py                 # 桃園機場爬蟲(抓取 + 清洗,寫入 flights.db)
├── Scraper_KHH.py                 # 高雄機場爬蟲(抓取 + 清洗,寫入 flights.db)
├── flights.db                     # 航班資料(KHH / TPE 兩張表)
├── requirements.txt                # 套件相依清單
├── .github/workflows/scrape.yml    # 每日排程:自動抓取 + 清洗 + commit 回 repo
└── README.md
```

## 安裝與執行

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 確認 flights.db 與 app.py 放在同一個資料夾

# 3. 啟動 Dashboard
streamlit run app.py
```

啟動後瀏覽器會自動開啟 `http://localhost:8501`。

### 手動執行爬蟲(補資料 / 本機測試用)

```bash
python Scraper_TPE.py                # 抓「昨天」的資料(預設)
python Scraper_TPE.py 2026/07/20     # 抓指定日期(補資料)

python Scraper_KHH.py                # 抓「昨天」的資料(預設)
python Scraper_KHH.py 2026-07-20     # 抓指定日期(補資料,注意日期格式跟 TPE 版不同)
```

平常有 GitHub Actions 每日自動排程,不需要手動執行;只有補資料或本機測試時才需要。

## 每日自動化排程

`.github/workflows/scrape.yml` 設定了 GitHub Actions,每天台灣時間 00:30 自動執行:

1. 依序執行 `Scraper_TPE.py`、`Scraper_KHH.py`,抓取前一天完整的航班資料
2. 抓取後直接清洗(欄位整理、機型轉 ICAO 代碼、目的地名稱統一),寫入 `flights.db`
3. 若資料有變動,自動 commit + push 回 repo

因為 Streamlit Community Cloud 是接 GitHub repo 部署,repo 一更新,線上的 dashboard 也會自動套用最新資料,不需要手動介入。也可以在 GitHub 的 **Actions** 分頁手動點 **Run workflow** 觸發測試或補資料。

## 資料說明

資料庫包含兩張表,欄位皆相同:

| 欄位 | 說明 |
|---|---|
| 機場名稱 | TPE(桃園)/ KHH(高雄) |
| 航空公司 | 該航班的營運航空公司 |
| 目的地 | 航班的目的地(城市/機場) |
| 機型 | 執飛機型 |
| 日期 | 航班日期 |
| 類型 | 離境 / 到場 |

> 目的地的經緯度與地區/國家分類,是額外整理的對照表(`app.py` 中的 `DEST_INFO`),資料來源若新增未收錄的目的地名稱,儀表板會顯示提醒訊息而不會中斷執行。

## 未來優化方向

- [x] 爬蟲排程自動化(GitHub Actions)並持續累積歷史資料
- [ ] 跨月份 / 跨季節趨勢比較
- [ ] 尖峰時段分析、航空公司市占率變化
- [ ] 加入資料驗證與單元測試(例如爬蟲欄位格式、空值檢查)

