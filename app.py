import streamlit as st
import pandas as pd
from datetime import datetime

# アプリのタイトル
st.title("LASリハビリ＆リズム管理")

# 1. 今日の日付
date_today = st.date_input("日付", datetime.now())

# 2. 体重測定（ソース：起床・排尿後に必須 [1]）
st.header("朝の記録")
weight = st.number_input("体重 (kg) - 目標: 月-1.5kg [3]", min_value=30.0, max_value=150.0, step=0.1)

# 3. 毎日チェックリスト（ソース：[1, 4]に基づく）
st.header("デイリーチェック")
col1, col2 = st.columns(2)

with col1:
    st.subheader("朝のルーティン")
    walk = st.checkbox("メトロノームウォーク (20分以上) [1, 4]")
    protein = st.checkbox("たんぱく質を含む朝食 [1, 4]")
    water = st.checkbox("水分補給 (目標1.5-2L) [1, 5]")

with col2:
    st.subheader("夜のルーティン")
    study = st.checkbox("PC・勉強 (21時終了) [1, 5]")
    bath = st.checkbox("入浴 (38〜40度 15〜20分) [1, 5]")
    medicine = st.checkbox("薬の服用 (夕食後) [1, 5]")
    sleep = st.checkbox("22時台の就寝 [3]")

# 4. 保存ボタン
if st.button("記録を保存"):
    # データをまとめる
    new_data = {
        "日付": [date_today],
        "体重": [weight],
        "ウォーク": [walk],
        "たんぱく質": [protein],
        "勉強": [study],
        "就寝": [sleep]
    }
    df = pd.DataFrame(new_data)
    
    # CSVファイルに保存（最小限のMVP実装 [6, 7]）
    try:
        existing_df = pd.read_csv("rehab_log.csv")
        df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        pass
    
    df.to_csv("rehab_log.csv", index=False)
    st.success("データを保存しました！「毎日少しずつ、積み重ねる」[3]")