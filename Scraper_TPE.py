import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
 
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
 
# ---------- 設定區 ----------
DB_PATH = Path(__file__).parent / "flights.db"
TABLE_NAME = "TPE_Flight_cleared"
 
API_URL = "https://www.taoyuan-airport.com/api/api/flight/a_flight"
 
# 機型 -> ICAO 代碼對照
PLANE_ICAO_MAP = {
    "B777-300": "B773", "A330-300": "A333", "A321-200": "A321", "A321-271": "A21N",
    "A350-900": "A359", "B737-800": "B738", "B787-10": "B78X", "A320-200": "A320",
    "B787-9": "B789", "A320-232": "A320", "A330-900": "A339", "A321-252": "A321",
    "A320-271": "A20N", "B737-900": "B739", "B787-8": "B788", "B777-200": "B772",
    "A350-100": "A35K", "A320-251": "A20N", "A321-231": "A321", "A321-251": "A21N",
    "A320-214": "A320", "A330-343": "A333", "A330-323": "A333", "A380-861": "A388",
    "B767-300": "B763", "A321-211": "A321", "A320-216": "A320", "B777-222": "B772",
    "A330-243": "A332", "B777-224": "B772", "B737-MAX": "B37M", "A330-200": "A332",
    "A319-132": "A319", "A380-800": "A388", "B747-8I": "B748", "B737-8MA": "B38M",
}
 
# 目的地名稱統一對照(跟 dashboard 的 DEST_INFO key 要保持一致)
DEST_RENAME_MAP = {
    "東京": "東京/成田",
    "羽田": "東京/羽田",
    "曼谷": "曼谷/蘇凡納布",
}
 
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.taoyuan-airport.com/flight_depart",
    "Content-Type": "application/json",
})
 
# 自動重試設定:遇到連線逾時、讀取逾時、或伺服器錯誤(5xx)時,自動重試最多 4 次,
# 每次重試間隔遞增(1s, 2s, 4s, 8s...),避免官網一時不穩就讓整個排程失敗。
retry_strategy = Retry(
    total=4,
    connect=4,
    read=4,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)
 
 
def fetch_flights(date_str: str, state: str):
    """
    date_str: 'YYYY/MM/DD'
    state: 'D'(離境) 或 'A'(到場)
 
    回傳:
      - pd.DataFrame:成功取得資料(可能是空的,代表當天真的沒有這類航班)
      - None:重試多次後仍然失敗(網路問題、API 錯誤等),不代表當天沒有航班
    """
    payload = {"ODate": date_str, "AState": state, "language": "ch", "keyword": ""}
    try:
        # timeout=(連線逾時秒數, 讀取逾時秒數):讀取給寬鬆一點,避免官網回應慢就被判定逾時
        response = session.post(API_URL, json=payload, timeout=(10, 30))
    except requests.exceptions.RequestException as e:
        print(f"❌ 抓取失敗(已重試但仍不成功):{state} {date_str} — {e}")
        return None
 
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            df["FlightType"] = "離境" if state == "D" else "到場"
            return df
        return pd.DataFrame()  # API 正常回應,但當天真的沒有這類航班
 
    print(f"⚠️ API 回應非 200:{response.status_code}({state} {date_str})")
    return None
 
 
def clean_flights(df_raw: pd.DataFrame) -> pd.DataFrame:
    """把 API 原始欄位轉成 flights.db 的格式(對應原 TPE_Flight_Datas_Select.py 的清洗邏輯)"""
    if df_raw.empty:
        return df_raw
 
    df = df_raw[["AName", "CityName", "PlaneNo", "ODate", "FlightType"]].rename(
        columns={
            "AName": "航空公司",
            "CityName": "目的地",
            "PlaneNo": "機型",
            "ODate": "日期",
            "FlightType": "類型",
        }
    )
    df.insert(0, "機場名稱", "TPE")
 
    df["機型"] = df["機型"].replace(PLANE_ICAO_MAP)
    df["目的地"] = df["目的地"].replace(DEST_RENAME_MAP)
 
    return df
 
 
def save_to_db(df: pd.DataFrame, target_date: str) -> None:
    """寫入 flights.db。target_date 這天視為「完整資料」,先清除該日期舊資料再整批寫入
    (避免排程重跑造成重複)。df 若夾帶其他日期的跨日資料(例如跨午夜航班),因為那些
    資料只是「零星片段」不是完整的一天,不會整批清除該日期原有資料,而是逐筆比對後
    只新增「還不存在」的紀錄,避免蓋掉那個日期原本已經完整寫入的資料。"""
    import sqlite3
 
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
 
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            機場名稱 TEXT, 航空公司 TEXT, 目的地 TEXT, 機型 TEXT, 日期 TEXT, 類型 TEXT
        )
    """)
 
    target_rows = df[df["日期"] == target_date]
    stray_rows = df[df["日期"] != target_date]
 
    # 目標日期:視為完整資料,先清除舊資料再整批寫入
    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE 機場名稱 = 'TPE' AND 日期 = ?", (target_date,))
    conn.commit()
    target_rows.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
 
    # 跨日資料:逐筆比對,只新增資料庫裡還沒有的紀錄,不動該日期原有的其他資料
    for _, row in stray_rows.iterrows():
        cur.execute(
            f"""SELECT 1 FROM {TABLE_NAME}
                WHERE 機場名稱=? AND 航空公司=? AND 目的地=? AND 機型=? AND 日期=? AND 類型=?
                LIMIT 1""",
            (row["機場名稱"], row["航空公司"], row["目的地"], row["機型"], row["日期"], row["類型"]),
        )
        if cur.fetchone() is None:
            cur.execute(
                f"""INSERT INTO {TABLE_NAME} (機場名稱, 航空公司, 目的地, 機型, 日期, 類型)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                (row["機場名稱"], row["航空公司"], row["目的地"], row["機型"], row["日期"], row["類型"]),
            )
    conn.commit()
    conn.close()
 
 
def main():
    if len(sys.argv) > 1:
        target_date = sys.argv[1]  # 手動指定日期,格式 YYYY/MM/DD
    else:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")
 
    print(f"正在抓取 {target_date} 的航班資料...")
 
    df_d = fetch_flights(target_date, "D")
    df_a = fetch_flights(target_date, "A")
 
    if df_d is None or df_a is None:
        print(f"❌ {target_date} 資料抓取失敗(已自動重試多次),不寫入資料庫,結束並回報失敗")
        sys.exit(1)
 
    df_raw = pd.concat([df_d, df_a], ignore_index=True)
 
    if df_raw.empty:
        print(f"  - {target_date} 當日確實沒有航班紀錄,不寫入資料庫")
        return
 
    df_clean = clean_flights(df_raw)
 
    # API 偶爾會夾帶幾筆隔天的航班(例如跨午夜離境),這些是真實航班、不是錯誤資料,
    # 會依它們「自己真正的日期」個別歸類寫入,不會混進 target_date 這批裡,也不會遺漏。
    stray = df_clean[df_clean["日期"] != target_date]
    if not stray.empty:
        print(f"ℹ️ 有 {len(stray)} 筆跨日資料(可能是跨午夜航班),將依各自日期歸類寫入:{sorted(stray['日期'].unique())}")
 
    save_to_db(df_clean, target_date)
 
    print(f"✅ 成功寫入 {len(df_clean)} 筆資料至 {DB_PATH}({TABLE_NAME})")
 
 
if __name__ == "__main__":
    main()
 