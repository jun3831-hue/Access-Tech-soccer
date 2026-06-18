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

# Session State 초기화
if "action_type" not in st.session_state:
    st.session_state.action_type = None
    st.session_state.action_name = None

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
# 📱 1번 방식 핵심: 모바일 해상도 고정 및 표 영역 가로 스크롤 CSS
# ------------------------------------------------
st.markdown("""
    <style>
    /* 1. 메인 앱 화면 전체가 가로로 억지로 늘어나는 브라우저 버그 현상 차단 */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMainViewContainer"] {
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
    
    /* 2. 테두리가 있는 컨테이너(표 구역) 내부만 독점적으로 가로 스크롤 활성화 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        overflow-x: auto !important;
        max-width: 100% !important;
        -webkit-overflow-scrolling: touch; /* 모바일 부드러운 스크롤 */
    }
    
    /* 3. 표 안의 콘텐트 가로 너비를 750px로 강제 고정하여 컬럼 정렬 유지 */
    div[data-testid="stVerticalBlockBorderWrapper"] > div > div {
        min-width: 750px !important;
    }
    
    /* 4. 가로 고정 정렬 유지 및 가독성 확보 */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
    div[data-testid="column"] {
        min-width: 0px !important;
        padding: 0px 4px !important;
    }
    .stButton > button {
        width: 100% !important;
        padding: 4px !important;
        font-size: 13px !important;
    }
    p, div {
        font-size: 14px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# 🎨 화면 UI 시작
# ------------------------------------------------
st.title("⚽ 한국 vs 멕시코 점수 맞추기 내기!")
st.info(f"💸 **참가비(1만원) 입금 계좌:** {ACCOUNT_INFO}")

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
    st.metric("멕시코", live_mx)
with col_score2:
    st.markdown("<h2 style='text-align: center; margin:0;'>VS</h2>", unsafe_allow_html=True)
with col_score3:
    st.metric("한국", live_kr)

st.markdown("---")

# ------------------------------------------------
# 🎯 신규 투표하기 폼
# ------------------------------------------------
st.subheader("🎯 신규 투표하기")
with st.form("new_betting_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("이름 (본명)", disabled=not is_open)
    with col2:
        pin = st.text_input("비밀번호 4자리 (수정/삭제용)", type="password", max_chars=4, disabled=not is_open)
        
    col3, col4 = st.columns(2)
    with col3:
        mexico_score = st.number_input("멕시코 예상 점수", min_value=0, step=1, disabled=not is_open)
    with col4:
        korea_score = st.number_input("한국 예상 점수", min_value=0, step=1, disabled=not is_open)
    
    submitted = st.form_submit_button("투표 제출하기", disabled=not is_open)
    
    if submitted and is_open:
        if not name or not pin:
            st.warning("이름과 비밀번호를 모두 입력해주세요.")
        else:
            c.execute("SELECT name FROM bets WHERE name=?", (name,))
            if c.fetchone():
                st.error("❌ 이미 등록된 이름입니다. 수정은 아래 현황판에서 해당 이름 우측의 [수정] 버튼을 이용해 주세요.")
            else:
                c.execute("INSERT INTO bets (name, pin, mexico, korea, paid) VALUES (?, ?, ?, ?, ?)", 
                          (name, pin, mexico_score, korea_score, '❌ 미입금'))
                conn.commit()
                st.success(f"🎉 {name}님 투표 완료!")
                st.rerun()

st.markdown("---")

# ------------------------------------------------
# 🔑 비밀번호 인증 및 액션 실행 창
# ------------------------------------------------
if st.session_state.action_type and is_open:
    target_name = st.session_state.action_name
    action_title = "투표 수정" if st.session_state.action_type == "edit" else "투표 삭제"
    
    st.info(f"🔒 **[{target_name}]님의 {action_title} 절차**")
    with st.form("action_confirm_form"):
        input_pin = st.text_input("본인의 비밀번호 4자리를 입력하세요", type="password", max_chars=4)
        
        new_mx, new_kr = 0, 0
        if st.session_state.action_type == "edit":
            c2_1, c2_2 = st.columns(2)
            with c2_1:
                new_mx = st.number_input("멕시코 새로운 예상 점수", min_value=0, step=1)
            with c2_2:
                new_kr = st.number_input("한국 새로운 예상 점수", min_value=0, step=1)
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submit_action = st.form_submit_button("확인 및 실행")
        with btn_col2:
            cancel_action = st.form_submit_button("취소")
            
        if cancel_action:
            st.session_state.action_type = None
            st.session_state.action_name = None
            st.rerun()
            
        if submit_action:
            c.execute("SELECT pin FROM bets WHERE name=?", (target_name,))
            orig_pin = c.fetchone()[0]
            
            if input_pin == orig_pin:
                if st.session_state.action_type == "delete":
                    c.execute("DELETE FROM bets WHERE name=?", (target_name,))
                    st.success(f"❌ {target_name}님의 투표가 삭제되었습니다.")
                elif st.session_state.action_type == "edit":
                    c.execute("UPDATE bets SET mexico=?, korea=? WHERE name=?", (new_mx, new_kr, target_name))
                    st.success(f"✅ {target_name}님의 투표가 수정되었습니다.")
                conn.commit()
                st.session_state.action_type = None
                st.session_state.action_name = None
                st.rerun()
            else:
                st.error("❌ 비밀번호가 일치하지 않습니다.")

# ------------------------------------------------
# 📊 현재 생존 현황 (가로 스크롤 컨테이너 적용 구역)
# ------------------------------------------------
st.subheader("📊 현재 생존 현황 (수정/삭제 가능)")

df = pd.read_sql("SELECT name, mexico, korea, paid FROM bets", conn)

if not df.empty:
    if is_finished:
        df['status_text'] = df.apply(lambda x: '🎉당첨' if (x['mexico'] == live_mx) and (x['korea'] == live_kr) else '☠️탈락', axis=1)
    else:
        df['status_text'] = df.apply(lambda x: '☠️탈락' if (x['mexico'] < live_mx) or (x['korea'] < live_kr) else '🏃생존', axis=1)
        
    # border=True를 주어 CSS가 이 영역만 타겟팅하여 가로 스크롤바를 띄우도록 유도합니다.
    with st.container(border=True):
        grid_cols = st.columns([1.6, 1.1, 1.1, 1.1, 1.4, 0.9, 0.9])
        grid_cols[0].markdown("**이름**")
        grid_cols[1].markdown("**멕시코**")
        grid_cols[2].markdown("**한국**")
        grid_cols[3].markdown("**상태**")
        grid_cols[4].markdown("**입금확인**")
        grid_cols[5].markdown("**수정**")
        grid_cols[6].markdown("**삭제**")
        st.markdown("<hr style='margin:2px 0px 6px 0px;'>", unsafe_allow_html=True)
        
        for index, row in df.iterrows():
            r_cols = st.columns([1.6, 1.1, 1.1, 1.1, 1.4, 0.9, 0.9])
            r_cols[0].write(row['name'])
            r_cols[1].write(str(row['mexico']))
            r_cols[2].write(str(row['korea']))
            r_cols[3].write(row['status_text'])
            r_cols[4].write(row['paid'])
            
            if r_cols[5].button("수정", key=f"edit_{row['name']}", disabled=not is_open):
                st.session_state.action_type = "edit"
                st.session_state.action_name = row['name']
                st.rerun()
                
            if r_cols[6].button("삭제", key=f"del_{row['name']}", disabled=not is_open):
                st.session_state.action_type = "delete"
                st.session_state.action_name = row['name']
                st.rerun()
            
    if is_finished:
        winners = df[df['status_text'] == '🎉당첨']['name'].tolist()
        st.markdown("---")
        st.subheader("🏆 최종 당첨자 결과")
        if winners:
            winner_text = ", ".join([f"**{w}**님" for w in winners])
            st.balloons()
            st.success(f"🥳 **사내 건전 집단지성 프로젝트 성공!** {winner_text} 정확히 맞추셨습니다! 축하합니다! 🎁")
        else:
            st.info("😭 아쉽게도 최종 스코어를 정확히 맞춘 사람이 없습니다.")
else:
    st.write("아직 투표한 사람이 없습니다.")

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
            
        # 서버 다운 대비 백업용 기능
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
