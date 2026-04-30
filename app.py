# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, timedelta

# ── 定数 ──────────────────────────────────────────
SHEET_NAME = "LAS_Rehab_Log"
DIARY_SHEET = "LAS_Diary"
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
DIARY_COLUMNS = ["date", "schedule_line", "condition_line", "title", "body", "mood"]

WEEKLY_SCHEDULE = {
    "月": ["朝ウォーク", "ピアノ練習"],
    "火": ["朝ウォーク", "ボイトレ"],
    "水": ["水中歩行", "ゴルフ"],
    "木": ["朝ウォーク", "ピアノ練習"],
    "金": ["朝ウォーク", "ボイトレ"],
    "土": ["水中歩行", "ゴルフ"],
    "日": ["休養", "自由"],
}

# ── Google Sheets 接続 ─────────────────────────────
@st.cache_resource
def get_workbook():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def get_worksheet(client):
    spreadsheet = client.open(SHEET_NAME)
    ws = spreadsheet.sheet1
    if not ws.row_values(1):
        ws.append_row(COLUMNS)
    return ws

def get_diary_sheet(client):
    try:
        spreadsheet = client.open(SHEET_NAME)
        try:
            ws = spreadsheet.worksheet(DIARY_SHEET)
        except Exception:
            ws = spreadsheet.add_worksheet(title=DIARY_SHEET, rows=1000, cols=10)
            ws.append_row(DIARY_COLUMNS)
        return ws
    except Exception as e:
        st.error(f"日記シートの接続に失敗：{e}")
        return None

# ── データ操作 ─────────────────────────────────────
def load_data(worksheet) -> pd.DataFrame:
    records = worksheet.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=COLUMNS)

def load_diary(ws) -> pd.DataFrame:
    records = ws.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=DIARY_COLUMNS)

def save_row(worksheet, row: dict):
    date_str = row["date"]
    all_values = worksheet.get_all_values()
    for i, r in enumerate(all_values):
        if i == 0:
            continue
        if r[0] == date_str:
            worksheet.update(range_name=f"A{i+1}",
                             values=[[str(row[col]) for col in COLUMNS]])
            return
    worksheet.append_row([str(row[col]) for col in COLUMNS])

def save_diary_row(ws, row: dict):
    date_str = row["date"]
    all_values = ws.get_all_values()
    row_values = [str(row.get(col, "")) for col in DIARY_COLUMNS]
    for i, r in enumerate(all_values):
        if i == 0:
            continue
        if r[0] == date_str:
            ws.update(range_name=f"A{i+1}", values=[row_values])
            return
    ws.append_row(row_values)

def get_bpm_target(target_date: date) -> str:
    day = target_date.day
    if day <= 7:    return "第1週：60〜70 BPM"
    elif day <= 14: return "第2週：65〜75 BPM"
    elif day <= 21: return "第3週：70〜80 BPM"
    else:           return "第4週：80〜90 BPM"

def get_existing(df, date_str, col, default):
    """指定日のデータから値を取得。なければdefaultを返す。"""
    if df.empty or "date" not in df.columns:
        return default
    row = df[df["date"] == date_str]
    if row.empty:
        return default
    v = row.iloc[0].get(col, default)
    return v if pd.notna(v) and str(v) != "" else default

# ── ページ：デイリー記録 ───────────────────────────
def page_daily(worksheet):
    st.title("🌟 LAS リハ＆リズムウェルネス")
    st.caption("毎日の積み重ねが、最大の力になる。")

    df = load_data(worksheet)
    today = date.today()

    # ── 日付選択（変えるとその日のデータが反映される）
    input_date = st.date_input("📅 記録日を選ぶ", value=today)
    date_str = str(input_date)

    def gv(col, default):
        return get_existing(df, date_str, col, default)

    # 過去日の場合に通知
    if input_date < today:
        st.info(f"📂 {input_date} の過去記録を表示しています。")
    elif input_date > today:
        st.warning("未来の日付が選択されています。")

    st.info(f"🎵 今週のメトロノーム目標：{get_bpm_target(input_date)}")

    # ── 基本情報
    weight = st.number_input("⚖️ 体重 (kg)", min_value=30.0, max_value=200.0, step=0.1,
                              value=float(gv("weight_kg", 70.0)))

    # ── 朝のルーティン
    st.header("☀️ 朝のルーティン")
    m_wakeup    = st.checkbox("✅ 6:00 起床",           value=(gv("morning_wakeup","False")=="True"))
    m_weight    = st.checkbox("✅ 体重測定",             value=(gv("morning_weight_check","False")=="True"))
    m_metro     = st.checkbox("✅ メトロノームウォーク", value=(gv("morning_metronome_walk","False")=="True"))
    m_stretch   = st.checkbox("✅ ストレッチ",           value=(gv("morning_stretch","False")=="True"))
    m_breakfast = st.checkbox("✅ 朝食",                 value=(gv("morning_breakfast","False")=="True"))

    # ── 夜のルーティン
    st.header("🌙 夜のルーティン")
    e_dinner = st.checkbox("✅ 19:00 夕食", value=(gv("evening_dinner_1900","False")=="True"))
    e_study  = st.checkbox("✅ 20:00 勉強", value=(gv("evening_study_2000","False")=="True"))
    e_bath   = st.checkbox("✅ 21:00 入浴", value=(gv("evening_bath_2100","False")=="True"))
    e_sleep  = st.checkbox("✅ 22:00 就寝", value=(gv("evening_sleep_2200","False")=="True"))

    # ── 食事ルール
    st.header("🍽️ 食事ルール（3つ）")
    f_half    = st.checkbox("✅ 主食を半分にした",       value=(gv("food_half_staple","False")=="True"))
    f_protein = st.checkbox("✅ たんぱく質を摂った",     value=(gv("food_protein","False")=="True"))
    f_no2000  = st.checkbox("✅ 20時以降は食べなかった", value=(gv("food_no_eat_after_2000","False")=="True"))

    # ── 水分・薬・BPM
    st.header("💊 水分・薬・BPM")
    col1, col2 = st.columns(2)
    with col1:
        water = st.slider("水分補給量 (L)", min_value=0.0, max_value=3.0, step=0.1,
                          value=float(gv("water_intake_L", 1.5)))
        st.caption(f"目標：1.5〜2.0L　現在：{water:.1f}L")
    with col2:
        medicine = st.checkbox("💊 薬を飲んだ", value=(gv("medicine_taken","False")=="True"))

    bpm = st.number_input("今日のメトロノームBPM", min_value=40, max_value=200, step=1,
                           value=int(gv("metronome_bpm", 65)))

    # ── 今日の活動
    st.header("🏃 今日の活動")
    walking = st.checkbox("🚶 ウォーキング／水中歩行をした",
                          value=(gv("walking_done","False")=="True"))
    rhythm  = st.checkbox("🎵 リズム練習をした（ボイトレ／ピアノ）",
                          value=(gv("rhythm_practice_done","False")=="True"))

    memo = st.text_area("📝 メモ・気づき", value=gv("memo", ""), height=80)

    # ── 保存
    st.divider()
    if st.button("💾 記録を保存", use_container_width=True, type="primary"):
        row = {
            "date": date_str, "weight_kg": weight,
            "morning_wakeup": m_wakeup, "morning_weight_check": m_weight,
            "morning_metronome_walk": m_metro, "morning_stretch": m_stretch,
            "morning_breakfast": m_breakfast, "evening_dinner_1900": e_dinner,
            "evening_study_2000": e_study, "evening_bath_2100": e_bath,
            "evening_sleep_2200": e_sleep, "food_half_staple": f_half,
            "food_protein": f_protein, "food_no_eat_after_2000": f_no2000,
            "water_intake_L": water, "medicine_taken": medicine,
            "metronome_bpm": bpm, "walking_done": walking,
            "rhythm_practice_done": rhythm, "memo": memo
        }
        with st.spinner("保存中..."):
            save_row(worksheet, row)
        st.success(f"✅ {input_date} の記録を保存しました！")
        st.balloons()

        # サマリー
        df = load_data(worksheet)
        month_str = date_str[:7]
        monthly = df[df["date"].str.startswith(month_str)]
        st.subheader("📊 今月の簡易サマリー")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("🚶 歩行日数", f"{(monthly['walking_done']=='True').sum()}日")
        with c2:
            st.metric("🎵 リズム練習", f"{(monthly['rhythm_practice_done']=='True').sum()}回")
        with c3:
            if len(monthly) >= 2:
                diff = round(float(monthly.iloc[-1]["weight_kg"])
                             - float(monthly.iloc[0]["weight_kg"]), 1)
                st.metric("⚖️ 体重変化", f"{diff:+.1f}kg")
            else:
                st.metric("⚖️ 体重変化", "記録中...")

    # ── 過去記録一覧
    if not df.empty:
        st.divider()
        st.subheader("📂 過去の記録")
        df_sorted = df.sort_values("date", ascending=False).head(30)
        for _, r in df_sorted.iterrows():
            walk = "🚶" if str(r.get("walking_done","")) == "True" else "－"
            rhy  = "🎵" if str(r.get("rhythm_practice_done","")) == "True" else "－"
            w    = r.get("weight_kg","－")
            label = f"{r['date']}　体重:{w}kg　歩行:{walk}　リズム:{rhy}"
            with st.expander(label):
                st.write(f"BPM：{r.get('metronome_bpm','－')}")
                st.write(f"水分：{r.get('water_intake_L','－')}L")
                st.write(f"メモ：{r.get('memo','')}")

# ── ページ：グラフ ─────────────────────────────────
def page_graph(worksheet):
    st.title("📊 進捗グラフ")

    df = load_data(worksheet)
    if df.empty or "date" not in df.columns:
        st.info("まだ記録がありません。デイリー記録から入力してください。")
        return

    df["date"] = pd.to_datetime(df["date"])
    df["weight_kg"] = pd.to_numeric(df["weight_kg"], errors="coerce")
    df = df.sort_values("date")

    period = st.selectbox("表示期間", ["今月", "過去30日", "全期間"])
    today = pd.Timestamp(date.today())
    if period == "今月":
        df_view = df[df["date"].dt.month == today.month]
    elif period == "過去30日":
        df_view = df[df["date"] >= today - pd.Timedelta(days=30)]
    else:
        df_view = df

    if df_view.empty:
        st.info("選択した期間のデータがありません。")
        return

    # 体重グラフ
    st.subheader("⚖️ 体重推移")
    if not df_view["weight_kg"].isna().all():
        start_weight = df_view["weight_kg"].iloc[0]
        chart_df = df_view[["date", "weight_kg"]].copy()
        chart_df["目標ライン"] = start_weight - 1.5
        st.line_chart(chart_df.set_index("date")[["weight_kg", "目標ライン"]])
        st.caption(f"目標：{start_weight - 1.5:.1f}kg（月-1.5kg）")

    # 歩行日数グラフ
    st.subheader("🚶 週別歩行日数")
    df_w = df_view.copy()
    df_w["week"] = df_w["date"].dt.strftime("%m/%d週")
    df_w["walked"] = (df_w["walking_done"] == "True").astype(int)
    wk = df_w.groupby("week")["walked"].sum().reset_index()
    wk.columns = ["週", "歩行日数"]
    wk["目標(5日)"] = 5
    st.bar_chart(wk.set_index("週"))

    # リズム練習グラフ
    st.subheader("🎵 週別リズム練習回数")
    df_r = df_view.copy()
    df_r["week"] = df_r["date"].dt.strftime("%m/%d週")
    df_r["practiced"] = (df_r["rhythm_practice_done"] == "True").astype(int)
    rk = df_r.groupby("week")["practiced"].sum().reset_index()
    rk.columns = ["週", "練習回数"]
    rk["目標(2回)"] = 2
    st.bar_chart(rk.set_index("週"))

    # BPM推移グラフ
    st.subheader("🎵 メトロノームBPM推移")
    df_b = df_view[["date", "metronome_bpm"]].copy()
    df_b["metronome_bpm"] = pd.to_numeric(df_b["metronome_bpm"], errors="coerce")
    st.line_chart(df_b.set_index("date"))

# ── ページ：日記 ───────────────────────────────────
def page_diary(client):
    st.title("📔 日記")

    ws = get_diary_sheet(client)
    if ws is None:
        return

    df = load_diary(ws)
    today = date.today()

    # ── 日付選択（変えるとその日の日記が反映される）
    input_date = st.date_input("📅 日付を選ぶ", value=today)
    date_str = str(input_date)

    if input_date < today:
        st.info(f"📂 {input_date} の過去の日記を表示しています。")

    def gv(col, default):
        return get_existing(df, date_str, col, default)

    # ── 1行予定欄（習い事・通院など）
    st.subheader("🗒️ この日の予定")
    schedule_line = st.text_input(
        "予定（習い事・通院など）",
        value=gv("schedule_line", ""),
        placeholder="例：14:00 ボイトレ、16:00 通院"
    )

    # ── 1行体調欄（天気・体調メモ）
    condition_line = st.text_input(
        "体調・天気",
        value=gv("condition_line", ""),
        placeholder="例：晴れ、体調良好、少し疲れ気味"
    )

    # ── 日記本文
    st.subheader("✏️ 日記")
    mood = st.select_slider(
        "今日の気分",
        options=["😞 つらい", "😐 普通", "🙂 まあまあ", "😊 良い", "🌟 最高"],
        value=gv("mood", "🙂 まあまあ")
    )
    title = st.text_input("タイトル", value=gv("title", ""))
    body  = st.text_area("内容", value=gv("body", ""), height=200)

    if st.button("💾 日記を保存", use_container_width=True, type="primary"):
        row = {
            "date": date_str,
            "schedule_line": schedule_line,
            "condition_line": condition_line,
            "title": title,
            "body": body,
            "mood": mood
        }
        with st.spinner("保存中..."):
            save_diary_row(ws, row)
        st.success(f"✅ {input_date} の日記を保存しました！")
        st.balloons()

    # ── 過去の日記一覧
    if not df.empty:
        st.divider()
        st.subheader("📚 過去の日記")
        df_sorted = df.sort_values("date", ascending=False)
        for _, r in df_sorted.iterrows():
            header = (f"{r.get('date','')}　"
                      f"{r.get('mood','')}　"
                      f"{r.get('title','')}")
            with st.expander(header):
                sched = r.get("schedule_line", "")
                cond  = r.get("condition_line", "")
                if sched:
                    st.caption(f"📌 予定：{sched}")
                if cond:
                    st.caption(f"🌤️ 体調・天気：{cond}")
                st.write(r.get("body", ""))

# ── ページ：スケジュール ───────────────────────────
def page_schedule(client):
    st.title("🗓️ 週間スケジュール")

    # 日記シートから予定を読み込む
    ws = get_diary_sheet(client)
    diary_df = load_diary(ws) if ws is not None else pd.DataFrame(columns=DIARY_COLUMNS)

    today = date.today()
    weekday_jp = ["月", "火", "水", "木", "金", "土", "日"]
    today_jp = weekday_jp[today.weekday()]

    # 今週の月曜日を起点に7日分の日付を計算
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    st.subheader("📅 今週の予定")
    for i, (day, activities) in enumerate(WEEKLY_SCHEDULE.items()):
        is_today = (day == today_jp)
        target_date = week_dates[i]
        date_str = str(target_date)

        # 日記シートからその日の予定を取得
        diary_schedule = get_existing(diary_df, date_str, "schedule_line", "")

        label = f"{'👉 ' if is_today else ''}{day}曜日　{target_date.strftime('%m/%d')}{'（今日）' if is_today else ''}"
        with st.expander(label, expanded=is_today):
            # 習い事などの固定スケジュール
            st.caption("📌 固定スケジュール")
            for act in activities:
                st.write(f"・{act}")
            # 日記から取得した予定
            if diary_schedule:
                st.caption("🗒️ この日の予定（日記より）")
                st.write(diary_schedule)
            else:
                st.caption("🗒️ この日の予定（日記より）")
                st.write("－ 未入力")

    st.divider()
    st.subheader("🎵 今月のメトロノーム目標")
    for week, bpm in {
        "第1週（1〜7日）":   "60〜70 BPM",
        "第2週（8〜14日）":  "65〜75 BPM",
        "第3週（15〜21日）": "70〜80 BPM",
        "第4週（22日〜）":   "80〜90 BPM",
    }.items():
        st.write(f"・{week}：{bpm}")

# ── メイン ─────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="LAS リハビリ管理",
        page_icon="🌟",
        layout="centered"
    )

    page = st.selectbox(
        "ページを選択",
        ["📋 デイリー記録", "📊 グラフ", "📔 日記", "🗓️ スケジュール"]
    )

    try:
        client = get_workbook()
        worksheet = get_worksheet(client)
    except Exception as e:
        st.error(f"Google Sheetsへの接続に失敗しました：{e}")
        st.stop()

    if page == "📋 デイリー記録":
        page_daily(worksheet)
    elif page == "📊 グラフ":
        page_graph(worksheet)
    elif page == "📔 日記":
        page_diary(client)
    elif page == "🗓️ スケジュール":
        page_schedule(client)   # ← clientを追加

if __name__ == "__main__":
    main()