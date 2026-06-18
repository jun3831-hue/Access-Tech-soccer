import streamlit as st
import sqlite3
import pandas as pd

# DB 설정
conn = sqlite3.connect('bets.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS bets (name TEXT, korea INT, mexico INT)')
conn.commit()

st.title("⚽ 한국 vs 멕시코 점수 맞추기 내기!")

# 입력 폼
with st.form("betting_form"):
    name = st.text_input("이름")
    col1, col2 = st.columns(2)
    with col1:
        korea_score = st.number_input("한국 점수", min_value=0, step=1)
    with col2:
        mexico_score = st.number_input("멕시코 점수", min_value=0, step=1)
    
    submitted = st.form_submit_button("투표하기")
    if submitted and name:
        c.execute("INSERT INTO bets VALUES (?, ?, ?)", (name, korea_score, mexico_score))
        conn.commit()
        st.success(f"{name}님 투표 완료!")

# 결과 보기
st.subheader("📊 현재까지의 예측 현황")
df = pd.read_sql("SELECT name as '이름', korea as '한국', mexico as '멕시코' FROM bets", conn)
st.dataframe(df, use_container_width=True)
