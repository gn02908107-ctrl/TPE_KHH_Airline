import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------- 設定區 ----------
DB_PATH = Path(__file__).parent / "flights.db"
TABLE_NAME = "KHH_Flight_cleared"

AIRLINE_MAP_URL = "https://www.kia.gov.tw/data/airline2.json"
AIRPORT_MAP_URL = "https://www.kia.gov.tw/data/airport2.json"
FLIGHT_URLS = {"離境": "https://www.kia.gov.tw/data/dep.json", "到場": "https://www.kia.gov.tw/data/arr.json"}

# 機型 -> ICAO 代碼對照
PLANE_ICAO_MAP = {
    "320": "A320", "321": "A321", "738": "B738", "32Q": "A21N",
    "77W": "B77W", "DHC6-400": "DHC6", "319": "A319",
}

# 目的地名稱統一對照
DEST_RENAME_MAP = {
    "沖繩": "琉球．沖繩",
    "胡志明": "胡志明市",
    "曼谷/素萬那普":"曼谷/蘇凡納布",
    "首爾/仁川":"仁川",
    "首爾/金浦":"金浦",
    "石垣":"石垣島",
}


def fetch_json_data(url: str, is_map: bool = False) -> pd.DataFrame:
    try:
        response = requests.get(url, verify=False, timeout=10)
        data = response.json()
        if is_map:
            return pd.DataFrame(data[2]["data"])
        return pd.DataFrame(data)
    except Exception as e:
        print(f"❌ 讀取 {url} 失敗: {e}")
        return pd.DataFrame()


def fetch_and_clean(target_date_dash: str) -> pd.DataFrame:
    """target_date_dash: 'YYYY-MM-DD'"""

    df_airline = fetch_json_data(AIRLINE_MAP_URL, is_map=True)
    df_airport = fetch_json_data(AIRPORT_MAP_URL, is_map=True)
    airline_map = dict(zip(df_airline["AirlineIATA"], df_airline["AirlineChineseAlias"]))
    airport_map = dict(zip(df_airport["IATA"], df_airport["BN"]))

    all_data = []
    for f_type, url in FLIGHT_URLS.items():
        df = fetch_json_data(url, is_map=False)
        if df.empty:
            continue

        df = df[df["FDATE"] == target_date_dash]
        if df.empty:
            continue

        df["AirlineName"] = df["airLineIATA"].map(airline_map).fillna(df["airLineIATA"])
        airport_col = "ArrivalAirportIATA" if "ArrivalAirportIATA" in df.columns else "DepartureAirportIATA"
        df["AirportName"] = df[airport_col].map(airport_map).fillna(df[airport_col])

        df_clean = pd.DataFrame({
            "航空公司": df["AirlineName"],
            "目的地": df["AirportName"],
            "機型": df.get("airPlaneType", "N/A"),
            "日期": df["FDATE"],
            "類型": f_type,
        })
        all_data.append(df_clean)

    if not all_data:
        return pd.DataFrame()

    datas = pd.concat(all_data, ignore_index=True)
    datas.insert(0, "機場名稱", "KHH")

    # 日期格式統一成 flights.db 使用的 YYYY/MM/DD
    datas["日期"] = pd.to_datetime(datas["日期"]).dt.strftime("%Y/%m/%d")

    datas["機型"] = datas["機型"].replace(PLANE_ICAO_MAP)
    datas["目的地"] = datas["目的地"].replace(DEST_RENAME_MAP)

    return datas


def save_to_db(df: pd.DataFrame, target_date_slash: str) -> None:
    """寫入 flights.db,若該日期已存在資料先刪除再寫入,避免排程重跑造成重複"""
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            機場名稱 TEXT, 航空公司 TEXT, 目的地 TEXT, 機型 TEXT, 日期 TEXT, 類型 TEXT
        )
    """)

    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE 機場名稱 = 'KHH' AND 日期 = ?", (target_date_slash,))
    conn.commit()

    df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    conn.close()


def main():
    if len(sys.argv) > 1:
        target_date_dash = sys.argv[1]  # 手動指定日期,格式 YYYY-MM-DD
    else:
        target_date_dash = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"正在抓取 {target_date_dash} 的航班資料...")

    df_clean = fetch_and_clean(target_date_dash)

    if df_clean.empty:
        print(f"⚠️ {target_date_dash} 沒有找到任何航班資料,不寫入資料庫")
        return

    target_date_slash = datetime.strptime(target_date_dash, "%Y-%m-%d").strftime("%Y/%m/%d")
    save_to_db(df_clean, target_date_slash)

    print(f"✅ 成功寫入 {len(df_clean)} 筆資料至 {DB_PATH}({TABLE_NAME})")


if __name__ == "__main__":
    main()
