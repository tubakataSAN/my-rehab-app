# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

SHEET_NAME = "LAS_Rehab_Log"
COLUMNS = [
    "date", "weight_kg",
    "morning_wakeup", "morning_weight_check", "morning_metronome_walk",
    "morning_stretch", "morning_breakfast",
    "evening_dinner_1900", "evening_study_2000",
    "evening_bath_2100", "evening_sleep_2200",
    "food_half_staple", "food_protein", "food_no_eat_after_2000",
    "water_intake_L", "medicine_taken",
    "metronome_bpm", "walking_done", "rhythm_practice_done",
    "memo"
]

@st.cache_resource
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open(SHEET_NAME)
    worksheet = spreadsheet.sheet1
    existing = worksheet.row_values(1)
    if not existing:
        worksheet.append_row(COLUMNS)
    return worksheet

def load_data(worksheet) -> pd.DataFrame:
    records = worksheet.get_all_records()
    if records:
        return pd.DataFrame(records)
    return pd.DataFrame(columns=COLUMNS)

def save_row(worksheet, row: dict, df: pd.DataFrame):
    today_str = row["date"]
    all_values = worksheet.get_all_values()
    for i, r in enumerate(all_values):
        if i == 0:
            continue
        if r[0] == today_str:
            row_values = [str(row[col]) for col in COLUMNS]
            worksheet.update(range_name=f"A{i+1}", values=[row_values])
            return
    row_values = [str(row[col]) for col in COLUMNS]
    worksheet.append_row(row_values)

def get_bpm_target(target_date: date) -> str:
    day = target_date.day
    if day <= 7:
        return "第1週：60〜70 BPM"
    elif day <= 14:
        return "第2週：65〜75 BPM"
    elif day <= 21:
        return "第3週：70〜80 BPM"
    else:
        return "第4週：80〜90 BPM"

def main():
    st.set_page_config(
        page_title="LAS リハビリ管理",
        page_icon="🌟",
        layout="centered"
    )

    st.title("🌟 LAS リハビリ＆リズムウェルネス")
    st.caption("毎日の積み重ねが、最大の力になる。")

    try:
        worksheet = get_worksheet()
        df = load_data(worksheet)
    except Exception as e:
        st.error(f"Google Sheetsへの接続に失敗しました：{e}")
        st.stop()

    today = date.today()
    today_str = str(today)
    existing = df[df["date"] == today_str] if "date" in df.columns else pd.DataFrame()

    def get_val(col, default):
        if not existing.empty and col in existing.columns:
            v = existing.iloc[0][col]
            return v if pd.notna(v) and v != "" else default
        return default

    st.header("📅 基本情報")
    col1, col2 = st.columns(2)
    with col1:
        input_date = st.date_input("記録日", value=today)
    with col2:
        weight = st.number_input(
            "体重 (kg)",
            min_value=30.0, max_value=200.0, step=0.1,
            value=float(get_val("weight_kg", 70.0))
        )

    st.info(f"🎵 今週のメトロノーム目標：{get_bpm_target(input_date)}")

    st.header("☀️ 朝のルーティン")
    m_wakeup    = st.checkbox("✅ 6:00 起床",           value=(get_val("morning_wakeup","False")=="True"))
    m_weight    = st.checkbox("✅ 体重測定",             value=(get_val("morning_weight_check","False")=="True"))
    m_metro     = st.checkbox("✅ メトロノームウォーク", value=(get_val("morning_metronome_walk","False")=="True"))
    m_stretch   = st.checkbox("✅ ストレッチ",           value=(get_val("morning_stretch","False")=="True"))
    m_breakfast = st.checkbox("✅ 朝食",                 value=(get_val("morning_breakfast","False")=="True"))

    st.header("🌙 夜のルーティン")
    e_dinner = st.checkbox("✅ 19:00 夕食", value=(get_val("evening_dinner_1900","False")=="True"))
    e_study  = st.checkbox("✅ 20:00 勉強", value=(get_val("evening_study_2000","False")=="True"))
    e_bath   = st.checkbox("✅ 21:00 入浴", value=(get_val("evening_bath_2100","False")=="True"))
    e_sleep  = st.checkbox("✅ 22:00 就寝", value=(get_val("evening_sleep_2200","False")=="True"))

    st.header("🍽️ 食事ルール（3つ）")
    f_half    = st.checkbox("✅ 主食を半分にした",       value=(get_val("food_half_staple","False")=="True"))
    f_protein = st.checkbox("✅ たんぱく質を摂った",     value=(get_val("food_protein","False")=="True"))
    f_no2000  = st.checkbox("✅ 20時以降は食べなかった", value=(get_val("food_no_eat_after_2000","False")=="True"))

    st.header("💊 水分・薬・BPM")
    col3, col4 = st.columns(2)
    with col3:
        water = st.slider(
            "水分補給量 (L)",
            min_value=0.0, max_value=3.0, step=0.1,
            value=float(get_val("water_intake_L", 1.5))
        )
        st.caption(f"目標：1.5〜2.0L　現在：{water:.1f}L")
    with col4:
        medicine = st.checkbox(
            "💊 薬を飲んだ",
            value=(get_val("medicine_taken","False")=="True")
        )

    bpm = st.number_input(
        "今日のメトロノームBPM",
        min_value=40, max_value=200, step=1,
        value=int(get_val("metronome_bpm", 65))
    )

    st.header("🏃 今日の活動")
    walking = st.checkbox(
        "🚶 ウォーキング／水中歩行をした",
        value=(get_val("walking_done","False")=="True")
    )
    rhythm = st.checkbox(
        "🎵 リズム練習をした（ボイトレ／ピアノ）",
        value=(get_val("rhythm_practice_done","False")=="True")
    )

    memo = st.text_area(
        "📝 今日のメモ・気づき",
        value=get_val("memo", ""),
        height=80
    )

    st.divider()
    if st.button("💾 今日の記録を保存", use_container_width=True, type="primary"):
        row = {
            "date": str(input_date),
            "weight_kg": weight,
            "morning_wakeup": m_wakeup,
            "morning_weight_check": m_weight,
            "morning_metronome_walk": m_metro,
            "morning_stretch": m_stretch,
            "morning_breakfast": m_breakfast,
            "evening_dinner_1900": e_dinner,
            "evening_study_2000": e_study,
            "evening_bath_2100": e_bath,
            "evening_sleep_2200": e_sleep,
            "food_half_staple": f_half,
            "food_protein": f_protein,
            "food_no_eat_after_2000": f_no2000,
            "water_intake_L": water,
            "medicine_taken": medicine,
            "metronome_bpm": bpm,
            "walking_done": walking,
            "rhythm_practice_done": rhythm,
            "memo": memo
        }

        with st.spinner("保存中..."):
            save_row(worksheet, row, df)

        st.success(f"✅ {input_date} の記録をGoogle Sheetsに保存しました！")
        st.balloons()

        df = load_data(worksheet)
        month_str = str(input_date)[:7]
        monthly = df[df["date"].str.startswith(month_str)]

        st.subheader("📊 今月の簡易サマリー")
        col5, col6, col7 = st.columns(3)
        with col5:
            walk_count = (monthly["walking_done"] == "True").sum()
            st.metric("🚶 歩行日数", f"{walk_count}日")
        with col6:
            rhythm_count = (monthly["rhythm_practice_done"] == "True").sum()
            st.metric("🎵 リズム練習", f"{rhythm_count}回")
        with col7:
            if len(monthly) >= 2:
                first_w = float(monthly.iloc[0]["weight_kg"])
                last_w  = float(monthly.iloc[-1]["weight_kg"])
                diff    = round(last_w - first_w, 1)
                st.metric("⚖️ 体重変化", f"{diff:+.1f}kg")
            else:
                st.metric("⚖️ 体重変化", "記録中...")

if __name__ == "__main__":
    main()
