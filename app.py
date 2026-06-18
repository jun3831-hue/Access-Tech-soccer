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

# 🔑 [필수 입력] API 토큰
API_KEY = "7a57cc65db3f47e4adea9e1468b053e1"

# 🔄 [자동 새로고침] 10초 주기
st_autorefresh(interval=10000, key="score_auto_refresh")

# ⏰ [시간 설정] 
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
# 📡 실시간 스코어 연동
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
st.title("⚽ 한국 vs 멕시코 점수 예측")
st.info(f"💸 **참가비(1만원) 입금 계좌:** {ACCOUNT_INFO}")

if is_open:
    time_left = DEADLINE - now_kst
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    st.success(f"⏳ 마감까지 **{time_left.days}일 {hours}시간 {minutes}분** 남았습니다. (오전 10시 마감)")
elif not is_finished:
    st.warning("🏃 **투표가 마감되었습니다!** 경기가 진행 중입니다.")
else:
    st.error("🚨 **경기가 종료되었습니다!** 결과를 확인하세요.")

# [변경 포인트 1] 스코어보드를 한 줄의 텍스트로 깔끔하게 통합 (여백 낭비 제로)
st.markdown(f"""
    <div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;'>
        <h2 style='margin: 0;'>멕시코 &nbsp;&nbsp; {live_mx} : {live_kr} &nbsp;&nbsp; 한국</h2>
    </div>
""", unsafe_allow_html=True)

# ------------------------------------------------
# 🎯 신규 투표하기 폼 (스트림릿 반응형 기본 레이아웃 적용)
# ------------------------------------------------
st.subheader("🎯 신규 투표하기")
with st.form("new_betting_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("이름 (본명)", disabled=not is_open)
    with col2:
        pin = st.text_input("비밀번호 4자리", type="password", max_chars=4, disabled=not is_open)
        
    col3, col4 = st.columns(2)
    with col3:
        mexico_score = st.number_input("멕시코 예상", min_value=0, step=1, disabled=not is_open)
    with col4:
        korea_score = st.number_input("한국 예상", min_value=0, step=1, disabled=not is_open)
    
    submitted = st.form_submit_button("투표 제출하기", disabled=not is_open)
    
    if submitted and is_open:
        if not name or not pin:
            st.warning("이름과 비밀번호를 모두 입력해주세요.")
        else:
            c.execute("SELECT name FROM bets WHERE name=?", (name,))
            if c.fetchone():
                st.error("❌ 이미 등록된 이름입니다. 수정은 아래 [수정/삭제] 메뉴를 이용하세요.")
            else:
                c.execute("INSERT INTO bets (name, pin, mexico, korea, paid) VALUES (?, ?, ?, ?, ?)", 
                          (name, pin, mexico_score, korea_score, '❌ 미입금'))
                conn.commit()
                st.success(f"🎉 {name}님 투표 완료!")
                st.rerun()

st.markdown("---")

# ------------------------------------------------
# 📊 현재 생존 현황 (4열 표)
# ------------------------------------------------
st.subheader("📊 현재 투표 현황")

df = pd.read_sql("SELECT name, mexico, korea, paid FROM bets", conn)

if not df.empty:
    # 상태값 계산
    if is_finished:
        df['status_text'] = df.apply(lambda x: '🎉당첨' if (x['mexico'] == live_mx) and (x['korea'] == live_kr) else '☠️탈락', axis=1)
    else:
        df['status_text'] = df.apply(lambda x: '☠️탈락' if (x['mexico'] < live_mx) or (x['korea'] < live_kr) else '🏃생존', axis=1)
    
    # 입금여부 텍스트 간소화
    df['paid_mark'] = df['paid'].apply(lambda x: '완료' if '완료' in x else '미입금')
    
    # [변경 포인트 2] 4개의 열로 통합하여 모바일 해상도 안착
    df['상태/입금'] = df['status_text'] + " / " + df['paid_mark']
    display_df = df[['name', 'mexico', 'korea', '상태/입금']].copy()
    display_df.rename(columns={'name': '이름', 'mexico': '멕시코', 'korea': '한국'}, inplace=True)
    
    # 기본 데이터프레임 기능 사용 (자동 스크롤 및 반응형 지원)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    if is_finished:
        winners = df[df['status_text'] == '🎉당첨']['name'].tolist()
        st.markdown("---")
        st.subheader("🏆 최종 당첨자 결과")
        if winners:
            winner_text = ", ".join([f"**{w}**님" for w in winners])
            st.balloons()
            st.success(f"🥳 **축하합니다 당첨!** {winner_text} 정확히 맞추셨습니다! 🎁")
        else:
            st.info("😭 아쉽게도 최종 스코어를 정확히 맞춘 사람이 없습니다.")
else:
    st.info("아직 투표한 사람이 없습니다.")

st.markdown("---")

# ------------------------------------------------
# 🛠️ 분리된 투표 수정 / 삭제 구역 (모바일 최적화 폼)
# ------------------------------------------------
st.subheader("🛠️ 투표 수정 / 삭제")

if not df.empty and is_open:
    action = st.radio("어떤 작업을 하시겠습니까?", ["투표 수정하기", "투표 삭제하기"], horizontal=True)
    
    target_name = st.selectbox("본인 이름 선택", df['name'].tolist())
    input_pin = st.text_input("비밀번호 4자리 확인", type="password", max_chars=4)
    
    if action == "투표 수정하기":
        st.write("*(수정할 새로운 점수를 입력하세요)*")
        edit_col1, edit_col2 = st.columns(2)
        with edit_col1:
            new_mx = st.number_input("멕시코 새 점수", min_value=0, step=1)
        with edit_col2:
            new_kr = st.number_input("한국 새 점수", min_value=0, step=1)
            
        if st.button("수정 실행"):
            c.execute("SELECT pin FROM bets WHERE name=?", (target_name,))
            orig_pin = c.fetchone()[0]
            if input_pin == orig_pin:
                c.execute("UPDATE bets SET mexico=?, korea=? WHERE name=?", (new_mx, new_kr, target_name))
                conn.commit()
                st.success(f"✅ {target_name}님의 점수가 수정되었습니다.")
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀립니다.")
                
    elif action == "투표 삭제하기":
        st.write("*(삭제 시 복구할 수 없습니다)*")
        if st.button("삭제 실행"):
            c.execute("SELECT pin FROM bets WHERE name=?", (target_name,))
            orig_pin = c.fetchone()[0]
            if input_pin == orig_pin:
                c.execute("DELETE FROM bets WHERE name=?", (target_name,))
                conn.commit()
                st.success(f"❌ {target_name}님의 투표가 삭제되었습니다.")
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀립니다.")
elif not is_open:
    st.write("🔒 마감되어 수정 및 삭제가 불가능합니다.")

st.markdown("---")

# ------------------------------------------------
# 🛠️ 관리자 전용 패널 및 CSV 백업 버튼
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
            
        st.markdown("---")
        st.write("### 💾 서버 데이터 백업")
        csv_data = df_admin[['name', 'paid']].to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 현재 투표 현황 다운로드 (CSV)",
            data=csv_data,
            file_name=f"worldcup_backup_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    elif admin_input != "":
        st.error("관리자 비밀번호가 틀렸습니다.")
