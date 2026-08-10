import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = Path(__file__).parent / "flights.db"

AIRPORT_COORDS = {
    "TPE": (25.0797, 121.2342),
    "KHH": (22.5771, 120.3500),
}

# 目的地對照表(座標 + 地區分類 合併成一張表,要新增/改名只需要改這裡一個地方):
# "目的地名稱": {"lat": 緯度, "lon": 經度, "region": 大洲/地區, "country": 國家}
DEST_INFO = {
    "上海/浦東": {"lat": 31.1443, "lon": 121.8083, "region": "亞洲", "country": "中國"},
    "北京": {"lat": 40.0799, "lon": 116.6031, "region": "亞洲", "country": "中國"},
    "南京": {"lat": 31.742, "lon": 118.8622, "region": "亞洲", "country": "中國"},
    "寧波": {"lat": 29.8267, "lon": 121.4619, "region": "亞洲", "country": "中國"},
    "廈門": {"lat": 24.544, "lon": 118.1275, "region": "亞洲", "country": "中國"},
    "廣州": {"lat": 23.3924, "lon": 113.2988, "region": "亞洲", "country": "中國"},
    "成都": {"lat": 30.5785, "lon": 103.9471, "region": "亞洲", "country": "中國"},
    "成都/雙流": {"lat": 30.5785, "lon": 103.9471, "region": "亞洲", "country": "中國"},
    "成都/天府": {"lat": 30.3184, "lon": 104.4417, "region": "亞洲", "country": "中國"},
    "杭州": {"lat": 30.2295, "lon": 120.4345, "region": "亞洲", "country": "中國"},
    "武漢": {"lat": 30.7838, "lon": 114.2081, "region": "亞洲", "country": "中國"},
    "深圳": {"lat": 22.6393, "lon": 113.8107, "region": "亞洲", "country": "中國"},
    "福州": {"lat": 25.935, "lon": 119.6633, "region": "亞洲", "country": "中國"},
    "虹橋": {"lat": 31.1979, "lon": 121.3363, "region": "亞洲", "country": "中國"},
    "鄭州": {"lat": 34.5197, "lon": 113.8408, "region": "亞洲", "country": "中國"},
    "重慶": {"lat": 29.7192, "lon": 106.6417, "region": "亞洲", "country": "中國"},
    "青島": {"lat": 36.2661, "lon": 120.3744, "region": "亞洲", "country": "中國"},
    "杜拜(DXB)": {"lat": 25.2532, "lon": 55.3657, "region": "亞洲", "country": "中東"},
    "阿布達比": {"lat": 24.433, "lon": 54.6511, "region": "亞洲", "country": "中東"},
    "七美": {"lat": 23.2075, "lon": 119.6272, "region": "亞洲", "country": "台灣"},
    "南竿": {"lat": 26.1533, "lon": 119.9575, "region": "亞洲", "country": "台灣"},
    "望安": {"lat": 23.2764, "lon": 119.5029, "region": "亞洲", "country": "台灣"},
    "東沙": {"lat": 20.7, "lon": 116.7167, "region": "亞洲", "country": "台灣"},
    "松山": {"lat": 25.0697, "lon": 121.5522, "region": "亞洲", "country": "台灣"},
    "澎湖": {"lat": 23.5686, "lon": 119.6289, "region": "亞洲", "country": "台灣"},
    "花蓮": {"lat": 23.9878, "lon": 121.618, "region": "亞洲", "country": "台灣"},
    "金門": {"lat": 24.4279, "lon": 118.3592, "region": "亞洲", "country": "台灣"},
    "高雄": {"lat": 22.5771, "lon": 120.35, "region": "亞洲", "country": "台灣"},
    "仙台": {"lat": 38.1397, "lon": 140.917, "region": "亞洲", "country": "日本"},
    "佐賀": {"lat": 33.1497, "lon": 130.3019, "region": "亞洲", "country": "日本"},
    "函館": {"lat": 41.77, "lon": 140.822, "region": "亞洲", "country": "日本"},
    "名古屋": {"lat": 34.8584, "lon": 136.8054, "region": "亞洲", "country": "日本"},
    "大分": {"lat": 33.4794, "lon": 131.7373, "region": "亞洲", "country": "日本"},
    "大阪/關西": {"lat": 34.4273, "lon": 135.244, "region": "亞洲", "country": "日本"},
    "宮古下地島": {"lat": 24.8267, "lon": 125.1447, "region": "亞洲", "country": "日本"},
    "宮崎": {"lat": 31.8772, "lon": 131.4489, "region": "亞洲", "country": "日本"},
    "小松": {"lat": 36.3941, "lon": 136.4061, "region": "亞洲", "country": "日本"},
    "岡山": {"lat": 34.7569, "lon": 133.8552, "region": "亞洲", "country": "日本"},
    "廣島": {"lat": 34.4361, "lon": 132.9194, "region": "亞洲", "country": "日本"},
    "新潟": {"lat": 37.9558, "lon": 139.1211, "region": "亞洲", "country": "日本"},
    "札幌": {"lat": 42.7752, "lon": 141.6923, "region": "亞洲", "country": "日本"},
    "東京": {"lat": 35.5494, "lon": 139.7798, "region": "亞洲", "country": "日本"},
    "東京/成田": {"lat": 35.7719, "lon": 140.3929, "region": "亞洲", "country": "日本"},
    "東京/羽田": {"lat": 35.5494, "lon": 139.7798, "region": "亞洲", "country": "日本"},
    "沖繩": {"lat": 26.1958, "lon": 127.6458, "region": "亞洲", "country": "日本"},
    "熊本": {"lat": 32.8372, "lon": 130.855, "region": "亞洲", "country": "日本"},
    "琉球．沖繩": {"lat": 26.1958, "lon": 127.6458, "region": "亞洲", "country": "日本"},
    "石垣島": {"lat": 24.3964, "lon": 124.165, "region": "亞洲", "country": "日本"},
    "神戶": {"lat": 34.6328, "lon": 135.2239, "region": "亞洲", "country": "日本"},
    "福岡": {"lat": 33.5859, "lon": 130.451, "region": "亞洲", "country": "日本"},
    "福島": {"lat": 37.2266, "lon": 140.4288, "region": "亞洲", "country": "日本"},
    "秋田": {"lat": 39.6156, "lon": 140.2186, "region": "亞洲", "country": "日本"},
    "米子": {"lat": 35.4922, "lon": 133.2362, "region": "亞洲", "country": "日本"},
    "羽田": {"lat": 35.5494, "lon": 139.7798, "region": "亞洲", "country": "日本"},
    "花卷": {"lat": 39.4286, "lon": 141.135, "region": "亞洲", "country": "日本"},
    "青森": {"lat": 40.7347, "lon": 140.6906, "region": "亞洲", "country": "日本"},
    "高松": {"lat": 34.2142, "lon": 134.0156, "region": "亞洲", "country": "日本"},
    "高知": {"lat": 33.5461, "lon": 133.6693, "region": "亞洲", "country": "日本"},
    "鹿兒島": {"lat": 31.8034, "lon": 130.7194, "region": "亞洲", "country": "日本"},
    "亞庇": {"lat": 5.9372, "lon": 116.0511, "region": "亞洲", "country": "東南亞"},
    "仰光": {"lat": 16.9073, "lon": 96.1332, "region": "亞洲", "country": "東南亞"},
    "克拉克": {"lat": 15.1859, "lon": 120.56, "region": "亞洲", "country": "東南亞"},
    "吉隆坡": {"lat": 2.7456, "lon": 101.7099, "region": "亞洲", "country": "東南亞"},
    "宿霧": {"lat": 10.3075, "lon": 123.9789, "region": "亞洲", "country": "東南亞"},
    "富國島": {"lat": 10.227, "lon": 103.9671, "region": "亞洲", "country": "東南亞"},
    "峇里島": {"lat": -8.7482, "lon": 115.1672, "region": "亞洲", "country": "東南亞"},
    "峴港": {"lat": 16.0439, "lon": 108.1996, "region": "亞洲", "country": "東南亞"},
    "帛琉": {"lat": 7.3673, "lon": 134.5442, "region": "亞洲", "country": "東南亞"},
    "德崇國際機場": {"lat": 11.3644, "lon": 104.8106, "region": "亞洲", "country": "東南亞"},
    "新加坡": {"lat": 1.3644, "lon": 103.9915, "region": "亞洲", "country": "東南亞"},
    "普吉": {"lat": 8.1132, "lon": 98.3169, "region": "亞洲", "country": "東南亞"},
    "曼谷": {"lat": 13.69, "lon": 100.7501, "region": "亞洲", "country": "東南亞"},
    "曼谷/廊曼": {"lat": 13.9126, "lon": 100.6067, "region": "亞洲", "country": "東南亞"},
    "曼谷/蘇凡納布": {"lat": 13.69, "lon": 100.7501, "region": "亞洲", "country": "東南亞"},
    "檳城": {"lat": 5.2971, "lon": 100.2769, "region": "亞洲", "country": "東南亞"},
    "汶萊": {"lat": 4.9442, "lon": 114.9283, "region": "亞洲", "country": "東南亞"},
    "河內": {"lat": 21.2212, "lon": 105.8072, "region": "亞洲", "country": "東南亞"},
    "清邁": {"lat": 18.7669, "lon": 98.9626, "region": "亞洲", "country": "東南亞"},
    "胡志明": {"lat": 10.8188, "lon": 106.652, "region": "亞洲", "country": "東南亞"},
    "胡志明市": {"lat": 10.8188, "lon": 106.652, "region": "亞洲", "country": "東南亞"},
    "芽莊": {"lat": 11.9982, "lon": 109.2196, "region": "亞洲", "country": "東南亞"},
    "金蘭": {"lat": 11.9982, "lon": 109.2196, "region": "亞洲", "country": "東南亞"},
    "關島": {"lat": 13.4834, "lon": 144.796, "region": "亞洲", "country": "東南亞"},
    "雅加達": {"lat": -6.1256, "lon": 106.6559, "region": "亞洲", "country": "東南亞"},
    "馬尼拉": {"lat": 14.5086, "lon": 121.0194, "region": "亞洲", "country": "東南亞"},
    "澳門": {"lat": 22.1496, "lon": 113.5915, "region": "亞洲", "country": "港澳"},
    "香港": {"lat": 22.308, "lon": 113.9185, "region": "亞洲", "country": "港澳"},
    "仁川": {"lat": 37.4602, "lon": 126.4407, "region": "亞洲", "country": "韓國"},
    "大邱": {"lat": 35.894, "lon": 128.6589, "region": "亞洲", "country": "韓國"},
    "清州": {"lat": 36.7166, "lon": 127.4992, "region": "亞洲", "country": "韓國"},
    "濟州": {"lat": 33.5113, "lon": 126.493, "region": "亞洲", "country": "韓國"},
    "金浦": {"lat": 37.5583, "lon": 126.7906, "region": "亞洲", "country": "韓國"},
    "釜山": {"lat": 35.1795, "lon": 129.0756, "region": "亞洲", "country": "韓國"},
    "多倫多": {"lat": 43.6777, "lon": -79.6248, "region": "北美洲", "country": "加拿大"},
    "溫哥華": {"lat": 49.1947, "lon": -123.1792, "region": "北美洲", "country": "加拿大"},
    "休士頓": {"lat": 29.9902, "lon": -95.3368, "region": "北美洲", "country": "美國"},
    "安大略": {"lat": 34.056, "lon": -117.6012, "region": "北美洲", "country": "美國"},
    "洛杉磯": {"lat": 33.9416, "lon": -118.4085, "region": "北美洲", "country": "美國"},
    "紐約": {"lat": 40.6413, "lon": -73.7781, "region": "北美洲", "country": "美國"},
    "舊金山": {"lat": 37.6213, "lon": -122.379, "region": "北美洲", "country": "美國"},
    "芝加哥": {"lat": 41.9742, "lon": -87.9073, "region": "北美洲", "country": "美國"},
    "華盛頓": {"lat": 38.9531, "lon": -77.4565, "region": "北美洲", "country": "美國"},
    "西雅圖": {"lat": 47.4502, "lon": -122.3088, "region": "北美洲", "country": "美國"},
    "達拉斯": {"lat": 32.8998, "lon": -97.0403, "region": "北美洲", "country": "美國"},
    "鳳凰城": {"lat": 33.4352, "lon": -112.0101, "region": "北美洲", "country": "美國"},
    "墨爾本": {"lat": -37.669, "lon": 144.841, "region": "大洋洲", "country": "澳洲"},
    "布里斯本": {"lat": -27.3842, "lon": 153.1175, "region": "大洋洲", "country": "澳洲"},
    "雪梨": {"lat": -33.9399, "lon": 151.1753, "region": "大洋洲", "country": "澳洲"},
    "奧克蘭": {"lat": -37.0082, "lon": 174.785, "region": "大洋洲", "country": "紐西蘭"},
    "伊斯坦堡": {"lat": 41.2753, "lon": 28.7519, "region": "歐洲", "country": "土耳其"},
    "維也納": {"lat": 48.1103, "lon": 16.5697, "region": "歐洲", "country": "奧地利"},
    "慕尼黑": {"lat": 48.3538, "lon": 11.7861, "region": "歐洲", "country": "德國"},
    "法蘭克福": {"lat": 50.0379, "lon": 8.5622, "region": "歐洲", "country": "德國"},
    "布拉格": {"lat": 50.1008, "lon": 14.26, "region": "歐洲", "country": "捷克"},
    "土魯斯": {"lat": 43.6293, "lon": 1.3638, "region": "歐洲", "country": "法國"},
    "巴黎": {"lat": 49.0097, "lon": 2.5479, "region": "歐洲", "country": "法國"},
    "米蘭": {"lat": 45.6306, "lon": 8.7231, "region": "歐洲", "country": "義大利"},
    "羅馬": {"lat": 41.8003, "lon": 12.2389, "region": "歐洲", "country": "義大利"},
    "倫敦": {"lat": 51.47, "lon": -0.4543, "region": "歐洲", "country": "英國"},
    "阿姆斯特丹": {"lat": 52.3105, "lon": 4.7683, "region": "歐洲", "country": "荷蘭"},
}

# 色盤:依航空公司輪流配色(數量夠多,避免相鄰航線撞色)
ROUTE_COLORS = px.colors.qualitative.Dark24 + px.colors.qualitative.Light24

st.set_page_config(page_title="台灣機場航班資訊分析儀表板", layout="wide")



@st.cache_data
def load_data(db_mtime):
    conn = sqlite3.connect(DB_PATH)
    khh = pd.read_sql("SELECT * FROM KHH_Flight_cleared", conn)
    tpe = pd.read_sql("SELECT * FROM TPE_Flight_cleared", conn)
    conn.close()
    df = pd.concat([khh, tpe], ignore_index=True)
    df["日期"] = pd.to_datetime(df["日期"], format="%Y/%m/%d")
    return df
 
df = load_data(DB_PATH.stat().st_mtime)

# ---------- 側邊欄篩選 ----------
st.sidebar.header("篩選條件")

airport_choice = st.sidebar.selectbox(
    "機場", options=["全部"] + sorted(df["機場名稱"].unique().tolist())
)
airports = sorted(df["機場名稱"].unique()) if airport_choice == "全部" else [airport_choice]

type_choice = st.sidebar.selectbox(
    "類型", options=["全部"] + sorted(df["類型"].unique().tolist())
)
flight_types = sorted(df["類型"].unique()) if type_choice == "全部" else [type_choice]

date_min, date_max = df["日期"].min(), df["日期"].max()
date_range = st.sidebar.date_input(
    "日期範圍", value=(date_min, date_max), min_value=date_min, max_value=date_max
)

# 目的地依「地區 > 國家/地區 > 目的地」三層連動篩選,選項只顯示所選機場實際有的資料
avail_dests = set(df.loc[df["機場名稱"].isin(airports), "目的地"].unique())

# 若目的地名稱是新出現、尚未收錄進 DEST_INFO(例如爬蟲資料更新、目的地改名),
# 不讓整個 App 直接報錯,先歸類為「未分類」,並提醒之後補上對照表
unmapped_dests = avail_dests - set(DEST_INFO.keys())
if unmapped_dests:
    st.sidebar.warning(f"有 {len(unmapped_dests)} 個目的地尚未分類:{', '.join(sorted(unmapped_dests))}")


def get_region(d):
    info = DEST_INFO.get(d)
    return (info["region"], info["country"]) if info else ("未分類", "未分類")


region_options = sorted({get_region(d)[0] for d in avail_dests})
region_choice = st.sidebar.selectbox("地區", options=["全部"] + region_options)
dests_after_region = (
    avail_dests if region_choice == "全部"
    else {d for d in avail_dests if get_region(d)[0] == region_choice}
)

country_options = sorted({get_region(d)[1] for d in dests_after_region})
country_choice = st.sidebar.selectbox("國家/地區", options=["全部"] + country_options)
dests_after_country = (
    dests_after_region if country_choice == "全部"
    else {d for d in dests_after_region if get_region(d)[1] == country_choice}
)


dest_options = sorted(dests_after_country)
dest_choice = st.sidebar.selectbox("目的地", options=["全部"] + dest_options)
destinations = dest_options if dest_choice == "全部" else [dest_choice]

# 航空公司選單連動所選機場 + 目的地,只顯示實際有飛該目的地的航空公司
airline_options = sorted(
    df.loc[
        df["機場名稱"].isin(airports) & df["目的地"].isin(destinations), "航空公司"
    ].unique()
)
airlines = st.sidebar.multiselect("航空公司(可選,預設全部)", options=airline_options)

# ---------- 套用篩選 ----------
mask = (
    df["機場名稱"].isin(airports)
    & df["類型"].isin(flight_types)
    & df["目的地"].isin(destinations)
    & (df["日期"] >= pd.to_datetime(date_range[0]))
    & (df["日期"] <= pd.to_datetime(date_range[-1]))
)
if airlines:
    mask &= df["航空公司"].isin(airlines)

fdf = df[mask]

st.title("✈️ 台灣機場航班資訊分析儀表板")
st.caption("資料來源:各機場官方網站 — 高雄(KHH) / 桃園(TPE) 機場航班紀錄")

db_updated = datetime.fromtimestamp(DB_PATH.stat().st_mtime, tz=ZoneInfo("Asia/Taipei"))
data_max_date = df["日期"].max()
st.caption(
    f"資料庫最後同步時間:{db_updated.strftime('%Y-%m-%d %H:%M')}"
    f"　|　資料涵蓋至:{data_max_date.strftime('%Y-%m-%d')}"
)

# ---------- KPI ----------
col1, col2, col3, col4 = st.columns(4)
col1.metric("總航班數", f"{len(fdf):,}")
col2.metric("航空公司數", fdf["航空公司"].nunique())
col3.metric("目的地數", fdf["目的地"].nunique())
col4.metric("機型數", fdf["機型"].nunique())

st.divider()

# ---------- 每日航班趨勢 ----------
daily = fdf.groupby([fdf["日期"].dt.date, "機場名稱"]).size().reset_index(name="航班數")
fig_trend = px.line(
    daily, x="日期", y="航班數", color="機場名稱", markers=True, title="每日航班數趨勢"
)
st.plotly_chart(fig_trend, use_container_width=True)

c1, c2 = st.columns(2)

with c1:
    top_dest_names = fdf["目的地"].value_counts().head(10).index.tolist()
    dest_by_airline = (
        fdf[fdf["目的地"].isin(top_dest_names)]
        .groupby(["目的地", "航空公司"])
        .size()
        .reset_index(name="航班數")
    )
    fig_dest = px.bar(
        dest_by_airline,
        x="航班數",
        y="目的地",
        color="航空公司",
        orientation="h",
        barmode="group",
        title="熱門目的地 Top 10(依航空公司分色)",
    )
    fig_dest.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_dest, use_container_width=True)

with c2:
    top_airline = (
        fdf["航空公司"].value_counts().head(10).reset_index()
    )
    top_airline.columns = ["航空公司", "航班數"]
    fig_airline = px.bar(
        top_airline, x="航班數", y="航空公司", orientation="h", title="航班數 Top 10 航空公司"
    )
    fig_airline.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_airline, use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    type_count = fdf["類型"].value_counts().reset_index()
    type_count.columns = ["類型", "航班數"]
    fig_type = px.pie(type_count, names="類型", values="航班數", title="離境 / 到場 比例")
    st.plotly_chart(fig_type, use_container_width=True)

with c4:
    top_model_names = fdf["機型"].value_counts().head(10).index.tolist()
    model_by_airline = (
        fdf[fdf["機型"].isin(top_model_names)]
        .groupby(["機型", "航空公司"])
        .size()
        .reset_index(name="航班數")
    )
    fig_model = px.bar(
        model_by_airline,
        x="機型",
        y="航班數",
        color="航空公司",
        barmode="group",
        title="機型分佈 Top 10(依航空公司分色)",
    )
    fig_model.update_layout(xaxis={"categoryorder": "total descending"})
    st.plotly_chart(fig_model, use_container_width=True)

st.divider()

# ---------- 航線地圖 ----------
st.subheader("🗺️ 航線地圖")
st.caption("依目前篩選(機場 / 類型 / 目的地 / 航空公司)顯示航線,顏色依航空公司區分。未選航空公司時預設顯示全部,航線較多可能較密集。")

routes = (
    fdf.groupby(["機場名稱", "目的地", "航空公司"]).size().reset_index(name="航班數")
)
routes["目的地座標"] = routes["目的地"].map(
    lambda d: (DEST_INFO[d]["lat"], DEST_INFO[d]["lon"]) if d in DEST_INFO else None
)
routes = routes.dropna(subset=["目的地座標"])

if routes.empty:
    st.info("目前篩選條件下沒有可繪製的航線資料。")
else:
    airline_list = sorted(routes["航空公司"].unique())
    color_map = {a: ROUTE_COLORS[i % len(ROUTE_COLORS)] for i, a in enumerate(airline_list)}

    fig_map = go.Figure()
    shown_legend = set()
    for row in routes.itertuples():
        origin_lat, origin_lon = AIRPORT_COORDS[row.機場名稱]
        dest_lat, dest_lon = row.目的地座標
        airline = row.航空公司
        color = color_map[airline]
        show_legend = airline not in shown_legend
        shown_legend.add(airline)
        fig_map.add_trace(
            go.Scattergeo(
                lat=[origin_lat, dest_lat],
                lon=[origin_lon, dest_lon],
                mode="lines",
                line=dict(width=1.5, color=color),
                opacity=0.6,
                name=airline,
                legendgroup=airline,
                showlegend=show_legend,
                hoverinfo="text",
                text=f"{row.機場名稱} → {row.目的地}({airline},{row.航班數} 班)",
            )
        )

    # 標出機場與目的地點位
    all_points = routes[["目的地", "目的地座標"]].drop_duplicates()
    fig_map.add_trace(
        go.Scattergeo(
            lat=[p[0] for p in all_points["目的地座標"]],
            lon=[p[1] for p in all_points["目的地座標"]],
            mode="markers",
            marker=dict(size=5, color="black"),
            name="目的地",
            showlegend=False,
            hoverinfo="text",
            text=all_points["目的地"],
        )
    )
    origin_coords = [AIRPORT_COORDS[a] for a in routes["機場名稱"].unique()]
    fig_map.add_trace(
        go.Scattergeo(
            lat=[c[0] for c in origin_coords],
            lon=[c[1] for c in origin_coords],
            mode="markers",
            marker=dict(size=10, color="red", symbol="star"),
            name="出發機場",
            showlegend=False,
            hoverinfo="text",
            text=list(routes["機場名稱"].unique()),
        )
    )

    fig_map.update_layout(
        geo=dict(
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(235,235,235)",
            showocean=True,
            oceancolor="rgb(245,250,255)",
            showcountries=True,
        ),
        height=550,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(title="航空公司"),
    )
    st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# ---------- 明細資料表 ----------
st.subheader("航班明細資料")
st.dataframe(fdf.sort_values("日期"), use_container_width=True, hide_index=True)
