import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# ------------------------------------------------
# ⚙️ 기본 설정 및 DB 연동
# ------------------------------------------------
DB_NAME = 'worldcup.db'
ADMIN_PW = 'jeon0915'
ACCOUNT_INFO = '카카오페이 또는 카카오뱅크 3333-10-3569994 전광용'

# 🔑 [필수 입력] football-data.org에서 발급받은 API 토큰을 여기에 넣으세요!
API_KEY = "7a57cc65db3f47e4adea9e1468b053e1"

# 🔄 [자동 새로고침] 10초(10000밀리초)마다 웹페이지 자동 갱신
st_autorefresh(interval=10000, key="score_auto_refresh")

# ⏰ [시간 설정] 한국 시간 기준 마감(10시) 및 경기 종료(12시) 일시 설정
DEADLINE = datetime(2026, 6, 19, 10, 0, 0)
MATCH_END = datetime(2026, 6, 19, 12, 0, 0)

now_kst = datetime.utcnow() + timedelta(hours=9)
is_open = now_kst < DEADLINE
is_finished = now_kst >= MATCH_END

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS bets 
             (name TEXT PRIMARY KEY, pin TEXT, mexico INT, korea INT, paid TEXT)''')
conn.commit()

# ------------------------------------------------
# 📡 실시간 스코어 연동 (반환값: 멕시코점수, 한국점수)
# ------------------------------------------------
@st.cache_data(ttl=10)
def get_live_score():
    if API_KEY == "여기에_발급받은_토큰을_넣으세요" or not API_KEY:
        return 0, 0
        
    try:
        url = "https://api.football-data.org/v4/matches"
        headers = {'X-Auth-Token': API_KEY}
        response = requests.get(url, headers=headers).json()
        
        for match in response.get('matches', []):
            home_team = match['homeTeam']['name'].lower()
            away_team = match['awayTeam']['name'].lower()
            
            if 'korea' in home_team or 'korea' in away_team:
                home_score = match['score']['fullTime']['home']
                away_score = match['score']['fullTime']['away']
                
                if home_score is None: home_score = 0
                if away_score is None: away_score = 0
                
                if 'korea' in away_team: 
                    return int(home_score), int(away_score)
                else:
                    return int(away_score), int(home_score)
                    
        return 0, 0
    except:
        return 0, 0

live_mx, live_kr = get_live_score()

# ------------------------------------------------
# 🎨 화면 UI 시작
# ------------------------------------------------
st.title("⚽ 한국 vs 멕시코 점수 맞추기 내기!")
st.info(f"💸 **참가비 입금 계좌:** {ACCOUNT_INFO}")

# 마감 상태 메시지
if is_open:
    time_left = DEADLINE - now_kst
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    st.success(f"⏳ 투표 마감까지 **{time_left.days}일 {hours}시간 {minutes}분** 남았습니다! (오전 10시 마감)")
elif not is_finished:
    st.warning("🏃 **투표가 마감되었습니다!** 현재 경기가 진행 중입니다.")
else:
    st.error("🚨 **경기가 완전히 종료되었습니다!** 최종 당첨 결과를 확인하세요.")

# 상단 스코어보드
col_score1, col_score2, col_score3 = st.columns([1, 1, 1])
with col_score1:
    st.metric("🇲🇽 멕시코", live_mx)
with col_score2:
    st.markdown("<h2 style='text-align: center;'>VS</h2>", unsafe_allow_html=True)
with col_score3:
    st.metric("🇰🇷 한국", live_kr)

st.markdown("---")

# ------------------------------------------------
# 📝 투표 및 수정 폼
# ------------------------------------------------
st.subheader("🎯 투표하기 / 수정하기")
with st.form("betting_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("이름 (본명)", disabled=not is_open)
    with col2:
        pin = st.text_input("비밀번호 4자리 (수정용)", type="password", max_chars=4, disabled=not is_open)
        
    col3, col4 = st.columns(2)
    with col3:
        mexico_score = st.number_input("🇲🇽 멕시코 예상 점수", min_value=0, step=1, disabled=not is_open)
    with col4:
        korea_score = st.number_input("🇰🇷 한국 예상 점수", min_value=0, step=1, disabled=not is_open)
    
    submitted = st.form_submit_button("제출하기", disabled=not is_open)
    
    if submitted and is_open:
        if not name or not pin:
            st.warning("이름 and 비밀번호를 모두 입력해주세요.")
        else:
            c.execute("SELECT pin FROM bets WHERE name=?", (name,))
            row = c.fetchone()
            
            if row:
                if row[0] == pin:
                    c.execute("UPDATE bets SET mexico=?, korea=? WHERE name=?", (mexico_score, korea_score, name))
                    conn.commit()
                    st.success(f"✅ {name}님의 투표가 수정되었습니다!")
                else:
                    st.error("❌ 비밀번호가 틀립니다.")
            else:
                c.execute("INSERT INTO bets (name, pin, mexico, korea, paid) VALUES (?, ?, ?, ?, ?)", 
                          (name, pin, mexico_score, korea_score, '❌ 미입금'))
                conn.commit()
                st.success(f"🎉 {name}님 투표 완료!")

st.markdown("---")

# ------------------------------------------------
# 📊 결과 확인 및 탈락/당첨 로직 처리
# ------------------------------------------------
st.subheader("📊 현재 생존 현황")
df = pd.read_sql("SELECT name, mexico, korea, paid FROM bets", conn)

if not df.empty:
    # ⏰ 19일 12시 이후에는 정확히 맞춘 사람만 '🎉 당첨!', 나머지는 '☠️ 탈락'
    if is_finished:
        df['상태'] = df.apply(lambda x: '🎉 당첨!' if (x['mexico'] == live_mx) and (x['korea'] == live_kr) else '☠️ 탈락', axis=1)
    else:
        df['상태'] = df.apply(lambda x: '☠️ 탈락' if (x['mexico'] < live_mx) or (x['korea'] < live_kr) else '🏃 생존', axis=1)
    
    df.rename(columns={'name': '이름', 'mexico': '멕시코', 'korea': '한국', 'paid': '입금확인'}, inplace=True)
    df = df[['이름', '멕시코', '한국', '상태', '입금확인']]
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 🏆 [추가 기능] 경기 종료 후 하단에 당첨자 축하 코너 특별 표출
    if is_finished:
        winners = df[df['상태'] == '🎉 당첨!']['이름'].tolist()
        st.markdown("---")
        st.subheader("🏆 최종 당첨자 결과")
        
        if winners:
            winner_text = ", ".join([f"**{w}**님" for w in winners])
            st.balloons() # 화면 전체에 축하 풍선이 날아다니는 시각 효과!
            st.success(f"🥳 **축하합니다 당첨!** {winner_text} 정말 축하합니다! 예측 성공! 🎁")
        else:
            st.info("😭 아쉽게도 최종 스코어를 정확히 맞춘 사람이 없습니다.")
else:
    st.write("아직 투표한 사람이 없습니다.")

st.markdown("---")

# ------------------------------------------------
# 🛠️ 관리자 전용 패널
# ------------------------------------------------
with st.expander("🔐 방장 전용 관리자 패널"):
    admin_input = st.text_input("관리자 비밀번호", type="password")
    
    if admin_input == ADMIN_PW:
        st.write("### 💰 입금 확인 관리")
        df_admin = pd.read_sql("SELECT name, paid FROM bets", conn)
        df_admin['입금완료 체크'] = df_admin['paid'] == '✅ 완료'
        
        edited_df = st.data_editor(df_admin[['name', '입금완료 체크']], hide_index=True, use_container_width=True)
        
        if st.button("입금 상태 일괄 저장"):
            for index, row in edited_df.iterrows():
                new_status = '✅ 완료' if row['입금완료 체크'] else '❌ 미입금'
                c.execute("UPDATE bets SET paid=? WHERE name=?", (new_status, row['name']))
            conn.commit()
            st.success("입금 상태가 업데이트되었습니다!")
            st.rerun()
    elif admin_input != "":
        st.error("관리자 비밀번호가 틀렸습니다.")
