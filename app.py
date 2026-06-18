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

# 🔄 [자동 새로고침 설정] 10,000밀리초(10초)마다 웹페이지가 알아서 새로고침 됩니다.
st_autorefresh(interval=10000, key="score_auto_refresh")

# ⏰ [시간 설정] 한국 시간 기준 마감일시 설정
DEADLINE = datetime(2026, 6, 19, 10, 0, 0)
now_kst = datetime.utcnow() + timedelta(hours=9)
is_open = now_kst < DEADLINE

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS bets 
             (name TEXT PRIMARY KEY, pin TEXT, korea INT, mexico INT, paid TEXT)''')
conn.commit()

# ------------------------------------------------
# 📡 football-data.org 실시간 스코어 연동 함수
# ------------------------------------------------
@st.cache_data(ttl=10) # 10초 동안은 임시 저장된 데이터를 써서 API 호출 낭비를 막음
def get_live_score():
    if API_KEY == "여기에_발급받은_토큰을_넣으세요" or not API_KEY:
        return 0, 0 # 키가 없으면 기본값 0:0 출력
        
    try:
        # 오늘 전세계 경기 목록을 가져오는 URL
        url = "https://api.football-data.org/v4/matches"
        headers = {'X-Auth-Token': API_KEY}
        response = requests.get(url, headers=headers).json()
        
        # 경기 목록 중에서 'Korea'가 들어간 경기를 자동으로 검색
        for match in response.get('matches', []):
            home_team = match['homeTeam']['name'].lower()
            away_team = match['awayTeam']['name'].lower()
            
            if 'korea' in home_team or 'korea' in away_team:
                home_score = match['score']['fullTime']['home']
                away_score = match['score']['fullTime']['away']
                
                # 경기가 시작 전이라 점수가 데이터가 없으면(None) 0으로 처리
                if home_score is None: home_score = 0
                if away_score is None: away_score = 0
                
                # 한국이 홈팀인지 원정팀인지 판별해서 (한국점수, 멕시코점수) 순서로 리턴
                if 'korea' in home_team:
                    return int(home_score), int(away_score)
                else:
                    return int(away_score), int(home_score)
                    
        return 0, 0 # 경기를 못 찾으면 0:0 리턴
    except:
        return 0, 0 # 에러 발생 시 안전하게 0:0 리턴

live_kr, live_mx = get_live_score()

# ------------------------------------------------
# 🎨 화면 UI 시작
# ------------------------------------------------
st.title("⚽ 한국 vs 멕시코 점수 맞추기 내기!")
st.info(f"💸 **참가비 입금 계좌:** {ACCOUNT_INFO}")

# 마감 상태 메시지 표시
if is_open:
    time_left = DEADLINE - now_kst
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    st.success(f"⏳ 투표 마감까지 **{time_left.days}일 {hours}시간 {minutes}분** 남았습니다! (오전 10시 마감)")
else:
    st.error("🚨 **투표가 마감되었습니다!** 이제 점수 수정 및 신규 투표가 불가능합니다.")

# 상단 실시간 스코어보드 (1분마다 자동으로 숫자가 바뀜)
col_score1, col_score2, col_score3 = st.columns([1, 1, 1])
with col_score1:
    st.metric("멕시코", live_kr)
with col_score2:
    st.markdown("<h2 style='text-align: center;'>VS</h2>", unsafe_allow_html=True)
with col_score3:
    st.metric("한국", live_mx)

st.markdown("---")

# ------------------------------------------------
# 📝 투표 및 수정 폼
# ------------------------------------------------
st.subheader("🎯 투표하기 (또는 수정하기)")
with st.form("betting_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("이름 (본명)", disabled=not is_open)
    with col2:
        pin = st.text_input("비밀번호 4자리 (수정용)", type="password", max_chars=4, disabled=not is_open)
        
    col3, col4 = st.columns(2)
    with col3:
        korea_score = st.number_input("멕시코 예상 점수", min_value=0, step=1, disabled=not is_open)
    with col4:
        mexico_score = st.number_input("한국 예상 점수", min_value=0, step=1, disabled=not is_open)
    
    submitted = st.form_submit_button("투표 / 수정하기", disabled=not is_open)
    
    if submitted and is_open:
        if not name or not pin:
            st.warning("이름과 비밀번호를 모두 입력해주세요.")
        else:
            c.execute("SELECT pin FROM bets WHERE name=?", (name,))
            row = c.fetchone()
            
            if row:
                if row[0] == pin:
                    c.execute("UPDATE bets SET korea=?, mexico=? WHERE name=?", (korea_score, mexico_score, name))
                    conn.commit()
                    st.success(f"✅ {name}님의 투표가 수정되었습니다!")
                else:
                    st.error("❌ 비밀번호가 틀립니다. 본인이 아니라면 수정할 수 없습니다.")
            else:
                c.execute("INSERT INTO bets VALUES (?, ?, ?, ?, ?)", (name, pin, korea_score, mexico_score, '❌ 미입금'))
                conn.commit()
                st.success(f"🎉 {name}님 투표 완료!")

st.markdown("---")

# ------------------------------------------------
# 📊 결과 확인 및 탈락 로직 처리
# ------------------------------------------------
st.subheader("📊 현재 생존 현황")
df = pd.read_sql("SELECT name, korea, mexico, paid FROM bets", conn)

if not df.empty:
    df['상태'] = df.apply(lambda x: '☠️ 탈락' if (x['korea'] < live_kr) or (x['mexico'] < live_mx) else '🏃 생존', axis=1)
    df.rename(columns={'name': '이름', 'korea': '한국(예상)', 'mexico': '멕시코(예상)', 'paid': '입금확인'}, inplace=True)
    df = df[['이름', '멕시코(예상)', '한국(예상)', '상태', '입금확인']]
    st.dataframe(df, use_container_width=True, hide_index=True)
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
