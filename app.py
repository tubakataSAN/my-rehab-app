# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, timedelta

# ── 定数 ──────────────────────────────────────────
SHEET_NAME   = "LAS_Rehab_Log"
DIARY_SHEET  = "LAS_Diary"
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
    "月": ["出社", "ピアノ"],
    "火": ["出社", "ゴルフスクール"],
    "水": ["ボイトレ", "パーソナル", "鍼"],
    "木": ["出社", "ピアノ練習", "ボイトレ練習",  "鍼"],
    "金": ["在宅", "月１ゴルフ"],
    "土": ["水中歩行", "自由"],
    "日": ["ボランティア", "自由"],
}

# ── スタイル ───────────────────────────────────────
def apply_style():
    st.markdown("""
    <style>
    div.stButton > button { height: 3rem; font-size: 1rem; }
    .stCheckbox { padding: 0.3rem 0; }
    .stNumberInput, .stSlider { margin-bottom: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

# ── ページ選択ボタン ───────────────────────────────
def page_selector():
    pages = ["📋 記録", "📊 グラフ", "📔 日記", "🗓️ 予定", "⚙️ 管理"]
    if "page" not in st.session_state:
        st.session_state.page = "📋 記録"
    cols = st.columns(len(pages))
    for i, p in enumerate(pages):
        if cols[i].button(p, use_container_width=True,
                          type="primary" if st.session_state.page == p else "secondary"):
            st.session_state.page = p
            st.rerun()
    st.divider()
    return st.session_state.page

# ── Google Sheets 接続 ─────────────────────────────
@st.cache_resource
def get_workbook():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_worksheet(client):
    sp = client.open(SHEET_NAME)
    ws = sp.sheet1
    if not ws.row_values(1):
        ws.append_row(COLUMNS)
    return ws

def get_diary_sheet(client):
    try:
        sp = client.open(SHEET_NAME)
        try:
            ws = sp.worksheet(DIARY_SHEET)
        except Exception:
            ws = sp.add_worksheet(title=DIARY_SHEET, rows=1000, cols=10)
            ws.append_row(DIARY_COLUMNS)
        return ws
    except Exception as e:
        st.error(f"日記シートの接続に失敗：{e}")
        return None

# ── データ操作 ─────────────────────────────────────
def load_data(ws) -> pd.DataFrame:
    records = ws.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=COLUMNS)

def load_diary(ws) -> pd.DataFrame:
    records = ws.get_all_records(expected_headers=DIARY_COLUMNS)
    return pd.DataFrame(records) if records else pd.DataFrame(columns=DIARY_COLUMNS)

def save_row(ws, row: dict):
    date_str = row["date"]
    all_v = ws.get_all_values()
    for i, r in enumerate(all_v):
        if i == 0: continue
        if r[0] == date_str:
            ws.update(range_name=f"A{i+1}",
                      values=[[str(row[c]) for c in COLUMNS]])
            return
    ws.append_row([str(row[c]) for c in COLUMNS])

def save_diary_row(ws, row: dict):
    date_str = row["date"]
    all_v = ws.get_all_values()
    vals = [str(row.get(c, "")) for c in DIARY_COLUMNS]
    for i, r in enumerate(all_v):
        if i == 0: continue
        if r[0] == date_str:
            ws.update(range_name=f"A{i+1}", values=[vals])
            return
    ws.append_row(vals)

def delete_row_by_date(ws, date_str: str) -> bool:
    all_v = ws.get_all_values()
    for i, r in enumerate(all_v):
        if i == 0: continue
        if r[0] == date_str:
            ws.delete_rows(i + 1)
            return True
    return False

def get_existing(df, date_str, col, default):
    if df.empty or "date" not in df.columns:
        return default
    row = df[df["date"] == date_str]
    if row.empty:
        return default
    v = row.iloc[0].get(col, default)
    return v if pd.notna(v) and str(v) != "" else default

def get_latest_weight(df, default=75.0) -> float:
    """直近の入力体重を返す。なければdefaultを返す。"""
    if df.empty or "weight_kg" not in df.columns:
        return default
    df_sorted = df[df["weight_kg"] != ""].copy()
    df_sorted["weight_kg"] = pd.to_numeric(df_sorted["weight_kg"], errors="coerce")
    df_sorted = df_sorted.dropna(subset=["weight_kg"])
    if df_sorted.empty:
        return default
    df_sorted = df_sorted.sort_values("date", ascending=False)
    return float(df_sorted.iloc[0]["weight_kg"])

def get_bpm_target(d: date) -> str:
    day = d.day
    if day <= 7:    return "第1週：65〜75 BPM"
    elif day <= 14: return "第2週：75〜85 BPM"
    elif day <= 21: return "第3週：85〜95 BPM"
    else:           return "第4週：95〜105 BPM"

# ── ページ：デイリー記録 ───────────────────────────
def page_daily(ws):
    st.title("🌟 LAS リハビリ")
    st.caption("毎日の積み重ねが、最大の力になる。")

    df = load_data(ws)
    today = date.today()
    input_date = st.date_input("📅 記録日", value=today)
    date_str = str(input_date)

    if input_date < today:
        st.info(f"📂 {input_date} の過去記録を表示しています。")

    def gv(col, default):
        return get_existing(df, date_str, col, default)

    st.info(f"🎵 今週のメトロノーム目標：{get_bpm_target(input_date)}")

    # 保存ボタン（上部）
    save_top = st.button("💾 記録を保存", use_container_width=True,
                         type="primary", key="save_top")

    # 体重スライダー（直近入力値を初期値に）
    latest_w = float(gv("weight_kg", get_latest_weight(df)))
    weight = st.slider(
        "⚖️ 体重 (kg)",
        min_value=67.0, max_value=97.0, step=0.1,
        value=latest_w
    )

    # 朝のルーティン（朝食を削除・リズムウォーク追加）
    with st.expander("☀️ 朝のルーティン", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            m_wakeup  = st.checkbox("6:00 起床",
                         value=(gv("morning_wakeup","False")=="True"))
            m_rhythm  = st.checkbox("🎵 リズムウォーク",
                         value=(gv("morning_metronome_walk","False")=="True"))
        with c2:
            m_weight  = st.checkbox("体重測定",
                         value=(gv("morning_weight_check","False")=="True"))
            m_stretch = st.checkbox("ストレッチ",
                         value=(gv("morning_stretch","False")=="True"))

    # 夜のルーティン（19:00夕食を削除・薬を追加）
    with st.expander("🌙 夜のルーティン", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            e_study   = st.checkbox("20:00 勉強",
                         value=(gv("evening_study_2000","False")=="True"))
            e_sleep   = st.checkbox("22:00 就寝",
                         value=(gv("evening_sleep_2200","False")=="True"))
        with c2:
            e_bath    = st.checkbox("21:00 入浴",
                         value=(gv("evening_bath_2100","False")=="True"))
            medicine  = st.checkbox("💊 薬を飲んだ",
                         value=(gv("medicine_taken","False")=="True"))

    # 食事ルール（朝食を取るを追加）
    with st.expander("🍽️ 食事ルール", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            f_half      = st.checkbox("主食を半分",
                           value=(gv("food_half_staple","False")=="True"))
            f_no2000    = st.checkbox("20時以降食べない",
                           value=(gv("food_no_eat_after_2000","False")=="True"))
        with c2:
            f_protein   = st.checkbox("たんぱく質",
                           value=(gv("food_protein","False")=="True"))
            m_breakfast = st.checkbox("朝食を取る",
                           value=(gv("morning_breakfast","False")=="True"))

    # 水分・BPM
    with st.expander("💧 水分・BPM", expanded=True):
        water = st.slider("水分補給量 (L)", min_value=0.0, max_value=3.0,
                          step=0.1, value=float(gv("water_intake_L", 1.5)))
        st.caption(f"目標：1.5〜2.0L　現在：{water:.1f}L")
        bpm = st.number_input("🎵 BPM", min_value=40, max_value=200, step=1,
                               value=int(gv("metronome_bpm", 65)))

    # 今日の活動
    with st.expander("🏃 今日の活動", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            walking = st.checkbox("🚶 ウォーキング",
                        value=(gv("walking_done","False")=="True"))
        with c2:
            rhythm  = st.checkbox("🎵 リズム練習",
                        value=(gv("rhythm_practice_done","False")=="True"))

    memo = st.text_area("📝 メモ", value=gv("memo", ""), height=80)

    # 保存ボタン（下部）
    save_bottom = st.button("💾 記録を保存", use_container_width=True,
                            type="primary", key="save_bottom")

    # 保存処理
    if save_top or save_bottom:
        row = {
            "date": date_str, "weight_kg": weight,
            "morning_wakeup": m_wakeup,
            "morning_weight_check": m_weight,
            "morning_metronome_walk": m_rhythm,
            "morning_stretch": m_stretch,
            "morning_breakfast": m_breakfast,
            "evening_dinner_1900": False,
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
            save_row(ws, row)
        st.success(f"✅ {input_date} の記録を保存しました！")
        st.balloons()

        df = load_data(ws)
        month_str = date_str[:7]
        monthly = df[df["date"].str.startswith(month_str)]
        st.subheader("📊 今月のサマリー")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("🚶 歩行日数",
                      f"{(monthly['walking_done']=='True').sum()}日")
        with c2:
            st.metric("🎵 リズム",
                      f"{(monthly['rhythm_practice_done']=='True').sum()}回")
        with c3:
            if len(monthly) >= 2:
                diff = round(float(monthly.iloc[-1]["weight_kg"])
                             - float(monthly.iloc[0]["weight_kg"]), 1)
                st.metric("⚖️ 体重変化", f"{diff:+.1f}kg")
            else:
                st.metric("⚖️ 体重変化", "記録中...")

    # 過去記録一覧
    if not df.empty:
        st.divider()
        with st.expander("📂 過去の記録を見る"):
            df_sorted = df.sort_values("date", ascending=False).head(30)
            for _, r in df_sorted.iterrows():
                walk = "🚶" if str(r.get("walking_done","")) == "True" else "－"
                rhy  = "🎵" if str(r.get("rhythm_practice_done","")) == "True" else "－"
                label = f"{r['date']}　{r.get('weight_kg','－')}kg　{walk}{rhy}"
                with st.expander(label):
                    st.write(f"BPM：{r.get('metronome_bpm','－')}　"
                             f"水分：{r.get('water_intake_L','－')}L")
                    st.write(f"メモ：{r.get('memo','')}")

# ── ページ：グラフ ─────────────────────────────────
def page_graph(ws):
    st.title("📊 進捗グラフ")

    import plotly.graph_objects as go

    df = load_data(ws)
    if df.empty or "date" not in df.columns:
        st.info("まだ記録がありません。")
        return

    df["date"] = pd.to_datetime(df["date"])
    df["weight_kg"] = pd.to_numeric(df["weight_kg"], errors="coerce")
    df = df.sort_values("date")

    period = st.selectbox("表示期間", ["今月", "過去30日", "全期間"])
    today  = pd.Timestamp(date.today())
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
        latest_date   = df_view["date"].max()
        x_end         = latest_date + pd.Timedelta(days=1)
        x_start       = x_end - pd.Timedelta(days=14)
        start_weight  = df_view["weight_kg"].iloc[0]
        target_weight = start_weight - 1.5

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_view["date"], y=df_view["weight_kg"],
            mode="lines+markers", name="体重",
            line=dict(color="#1f77b4", width=2), marker=dict(size=6)
        ))
        fig.add_trace(go.Scatter(
            x=[x_start, x_end], y=[target_weight, target_weight],
            mode="lines", name=f"目標 {target_weight:.1f}kg",
            line=dict(color="red", width=1, dash="dash")
        ))
        fig.update_layout(
            xaxis=dict(range=[x_start, x_end],
                       tickformat="%m/%d", dtick=86400000*2),
            yaxis=dict(range=[67, 97], title="kg"),
            legend=dict(orientation="h", y=-0.2),
            margin=dict(l=10, r=10, t=10, b=10), height=350
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"目標：{target_weight:.1f}kg（月-1.5kg）")

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

    df    = load_diary(ws)
    today = date.today()
    input_date = st.date_input("📅 日付", value=today)
    date_str   = str(input_date)

    if input_date < today:
        st.info(f"📂 {input_date} の過去の日記を表示しています。")

    def gv(col, default):
        return get_existing(df, date_str, col, default)

    with st.expander("🗒️ この日の予定・体調", expanded=True):
        schedule_line  = st.text_input("予定（習い事・通院など）",
                                        value=gv("schedule_line",""),
                                        placeholder="例：14:00 ボイトレ")
        condition_line = st.text_input("体調・天気",
                                        value=gv("condition_line",""),
                                        placeholder="例：晴れ、体調良好")

    with st.expander("✏️ 日記", expanded=True):
        mood  = st.select_slider("気分",
                                  options=["😞 つらい","😐 普通",
                                           "🙂 まあまあ","😊 良い","🌟 最高"],
                                  value=gv("mood","🙂 まあまあ"))
        title = st.text_input("タイトル", value=gv("title",""))
        body  = st.text_area("内容", value=gv("body",""), height=200)

    if st.button("💾 日記を保存", use_container_width=True, type="primary"):
        row = {
            "date": date_str, "schedule_line": schedule_line,
            "condition_line": condition_line, "title": title,
            "body": body, "mood": mood
        }
        with st.spinner("保存中..."):
            save_diary_row(ws, row)
        st.success(f"✅ {input_date} の日記を保存しました！")
        st.balloons()

    if not df.empty:
        st.divider()
        with st.expander("📚 過去の日記を見る"):
            for _, r in df.sort_values("date", ascending=False).iterrows():
                header = (f"{r.get('date','')}　"
                          f"{r.get('mood','')}　"
                          f"{r.get('title','')}")
                with st.expander(header):
                    if r.get("schedule_line",""):
                        st.caption(f"📌 予定：{r['schedule_line']}")
                    if r.get("condition_line",""):
                        st.caption(f"🌤️ 体調：{r['condition_line']}")
                    st.write(r.get("body",""))

# ── ページ：スケジュール ───────────────────────────
def page_schedule(client):
    st.title("🗓️ 週間スケジュール")

    ws       = get_diary_sheet(client)
    diary_df = (load_diary(ws) if ws is not None
                else pd.DataFrame(columns=DIARY_COLUMNS))

    today      = date.today()
    weekday_jp = ["月","火","水","木","金","土","日"]
    today_jp   = weekday_jp[today.weekday()]
    monday     = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    st.subheader("📅 今週の予定")
    for i, (day, activities) in enumerate(WEEKLY_SCHEDULE.items()):
        is_today    = (day == today_jp)
        target_date = week_dates[i]
        date_str    = str(target_date)
        diary_sched = get_existing(diary_df, date_str, "schedule_line", "")

        label = (f"{'👉 ' if is_today else ''}{day}曜日　"
                 f"{target_date.strftime('%m/%d')}"
                 f"{'（今日）' if is_today else ''}")
        with st.expander(label, expanded=is_today):
            st.caption("📌 固定スケジュール")
            for act in activities:
                st.write(f"・{act}")
            st.caption("🗒️ この日の予定（日記より）")
            st.write(diary_sched if diary_sched else "－ 未入力")

    st.divider()
    st.subheader("🎵 今月のメトロノーム目標")
    for week, bpm in {
        "第1週（1〜7日）":   "65〜75 BPM",
        "第2週（8〜14日）":  "75〜85 BPM",
        "第3週（15〜21日）": "85〜95 BPM",
        "第4週（22日〜）":   "95〜105 BPM",
    }.items():
        st.write(f"・{week}：{bpm}")

# ── ページ：管理 ───────────────────────────────────
def page_admin(client):
    st.title("⚙️ データ管理")

    ws       = get_worksheet(client)
    diary_ws = get_diary_sheet(client)
    df       = load_data(ws)
    diary_df = (load_diary(diary_ws) if diary_ws is not None
                else pd.DataFrame())

    # バックアップ
    st.header("📥 バックアップ")
    st.caption("現在のデータをCSVとしてダウンロードできます。")
    c1, c2 = st.columns(2)
    with c1:
        if not df.empty:
            st.download_button(
                label="⬇️ デイリー記録をCSV保存",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"rehab_backup_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
    with c2:
        if not diary_df.empty:
            st.download_button(
                label="⬇️ 日記をCSV保存",
                data=diary_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"diary_backup_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )

    st.divider()

    # データクリア
    st.header("🗑️ 特定日のデータをクリア")
    st.caption("誤入力を修正したいときは削除してから再入力してください。")
    st.warning("⚠️ 削除すると元に戻せません。先にバックアップを取ることをおすすめします。")

    clear_date = st.date_input("削除する日付", value=date.today())
    clear_str  = str(clear_date)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ デイリー記録を削除", use_container_width=True):
            if not df.empty and clear_str in df["date"].values:
                with st.spinner("削除中..."):
                    result = delete_row_by_date(ws, clear_str)
                if result:
                    st.success(f"✅ {clear_date} のデイリー記録を削除しました。")
                    st.info("デイリー記録ページで再入力してください。")
                else:
                    st.error("削除に失敗しました。")
            else:
                st.warning(f"{clear_date} のデイリー記録は見つかりませんでした。")
    with c2:
        if st.button("🗑️ 日記を削除", use_container_width=True):
            if (diary_ws and not diary_df.empty
                    and clear_str in diary_df["date"].values):
                with st.spinner("削除中..."):
                    result = delete_row_by_date(diary_ws, clear_str)
                if result:
                    st.success(f"✅ {clear_date} の日記を削除しました。")
                    st.info("日記ページで再入力してください。")
                else:
                    st.error("削除に失敗しました。")
            else:
                st.warning(f"{clear_date} の日記は見つかりませんでした。")

# ── メイン ─────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="LAS リハビリ管理",
        page_icon="🌟",
        layout="centered"
    )
    apply_style()
    page = page_selector()

    try:
        client    = get_workbook()
        worksheet = get_worksheet(client)
    except Exception as e:
        st.error(f"Google Sheetsへの接続に失敗しました：{e}")
        st.stop()

    if page == "📋 記録":
        page_daily(worksheet)
    elif page == "📊 グラフ":
        page_graph(worksheet)
    elif page == "📔 日記":
        page_diary(client)
    elif page == "🗓️ 予定":
        page_schedule(client)
    elif page == "⚙️ 管理":
        page_admin(client)

if __name__ == "__main__":
    main()