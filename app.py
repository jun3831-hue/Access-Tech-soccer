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

# Session State 초기화
if "target_name" not in st.session_state:
    st.session_state.target_name = None

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
# 🎨 화면 UI 시작 (모바일 전용 안전벨트 CSS)
# ------------------------------------------------
st.title("⚽ 한국 vs 멕시코 점수 예측")
st.info(f"💸 **참가비(1만원) 입금 계좌:** {ACCOUNT_INFO}")

st.markdown("""
    <style>
    /* 📱 오직 모바일(화면 600px 이하)에서만 작동하는 CSS */
    @media (max-width: 600px) {
        .stButton > button {
            padding: 0px 5px !important;
            font-size: 13px !important;
            min-height: 32px !important;
        }
        
        /* 🚨 [핵심] 현황판(마커 있는 곳)의 칸들이 모바일에서 밑으로 떨어지는 본능을 강제로 막음 */
        div[data-testid="stVerticalBlock"]:has(.status-board-marker) div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
        }
        div[data-testid="stVerticalBlock"]:has(.status-board-marker) div[data-testid="column"] {
            min-width: 0px !important;
            padding: 0px 2px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

if is_open:
    time_left = DEADLINE - now_kst
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    st.success(f"⏳ 마감까지 **{time_left.days}일 {hours}시간 {minutes}분** 남았습니다. (오전 10시 마감)")
elif not is_finished:
    st.warning("🏃 **투표가 마감되었습니다!** 경기가 진행 중입니다.")
else:
    st.error("🚨 **경기가 종료되었습니다!** 결과를 확인하세요.")

st.markdown(f"""
    <div style='text-align: center; padding: 15px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;'>
        <h2 style='margin: 0;'>멕시코 &nbsp;&nbsp; {live_mx} : {live_kr} &nbsp;&nbsp; 한국</h2>
    </div>
""", unsafe_allow_html=True)

# ------------------------------------------------
# 🎯 신규 투표하기 폼 (스트림릿 순정: 폰에서는 알아서 4줄 됨)
# ------------------------------------------------
st.subheader("🎯 신규 투표하기")
with st.form("new_betting_form"):
    name = st.text_input("이름 (본명)", disabled=not is_open)
    pin = st.text_input("비밀번호 4자리", type="password", max_chars=4, disabled=not is_open)
    
    col1, col2 = st.columns(2)
    with col1:
        mexico_score = st.selectbox("멕시코", options=list(range(15)), disabled=not is_open)
    with col2:
        korea_score = st.selectbox("한국", options=list(range(15)), disabled=not is_open)
    
    submitted = st.form_submit_button("투표 제출하기", disabled=not is_open, use_container_width=True)
    
    if submitted and is_open:
        if not name or not pin:
            st.warning("이름과 비밀번호를 모두 입력해주세요.")
        else:
            c.execute("SELECT name FROM bets WHERE name=?", (name,))
            if c.fetchone():
                st.error("❌ 이미 등록된 이름입니다. 기존 내역을 수정하려면 아래 현황판에서 [변경] 버튼을 눌러주세요.")
            else:
                c.execute("INSERT INTO bets (name, pin, mexico, korea, paid) VALUES (?, ?, ?, ?, ?)", 
                          (name, pin, mexico_score, korea_score, '❌ 미입금'))
                conn.commit()
                st.success(f"🎉 {name}님 투표 완료!")
                st.rerun()

st.markdown("---")

# ------------------------------------------------
# 🛠️ 투표 수정/삭제 액션 창
# ------------------------------------------------
if st.session_state.target_name and is_open:
    t_name = st.session_state.target_name
    
    st.warning(f"🛠️ **[{t_name}]님의 투표 관리**")
    st.write("##### 수정하시겠습니까? 삭제하시겠습니까?")
    
    action_type = st.radio("작업 선택", ["수정", "삭제"], horizontal=True, label_visibility="collapsed")
    
    with st.form("action_confirm_form"):
        st.write("본인의 비밀번호 4자리를 입력해주세요.")
        input_pin = st.text_input("비밀번호 확인", type="password", max_chars=4)
        
        new_mx, new_kr = 0, 0
        if action_type == "수정":
            st.info("새로운 예측 점수를 선택하세요.")
            c1, c2 = st.columns(2)
            with c1:
                new_mx = st.selectbox("멕시코", options=list(range(15)))
            with c2:
                new_kr = st.selectbox("한국", options=list(range(15)))
                
        c_submit, c_cancel = st.columns(2)
        with c_submit:
            confirm_btn = st.form_submit_button("✅ 실행하기", use_container_width=True)
        with c_cancel:
            cancel_btn = st.form_submit_button("❌ 취소하기", use_container_width=True)
            
        if cancel_btn:
            st.session_state.target_name = None
            st.rerun()
            
        if confirm_btn:
            c.execute("SELECT pin FROM bets WHERE name=?", (t_name,))
            orig_pin = c.fetchone()[0]
            
            if input_pin == orig_pin:
                if action_type == "수정":
                    c.execute("UPDATE bets SET mexico=?, korea=? WHERE name=?", (new_mx, new_kr, t_name))
                    st.success(f"✅ {t_name}님의 점수가 수정되었습니다.")
                elif action_type == "삭제":
                    c.execute("DELETE FROM bets WHERE name=?", (t_name,))
                    st.success(f"❌ {t_name}님의 투표가 삭제되었습니다.")
                conn.commit()
                st.session_state.target_name = None
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀립니다.")
                
    st.markdown("---")

# ------------------------------------------------
# 📊 현재 생존 현황 (PC: 순정 레이아웃 / 모바일: 한 줄 고정)
# ------------------------------------------------
st.subheader("📊 현재 투표 현황")

df = pd.read_sql("SELECT name, mexico, korea, paid FROM bets", conn)

if not df.empty:
    if is_finished:
        df['status_text'] = df.apply(lambda x: '당첨' if (x['mexico'] == live_mx) and (x['korea'] == live_kr) else '탈락', axis=1)
    else:
        df['status_text'] = df.apply(lambda x: '탈락' if (x['mexico'] < live_mx) or (x['korea'] < live_kr) else '생존', axis=1)
    
    df['paid_mark'] = df['paid'].apply(lambda x: '완료' if '완료' in x else '미입금')
    
    with st.container():
        # CSS가 이 구역만 콕 집어서 적용되도록 마커 달기
        st.markdown('<div class="status-board-marker"></div>', unsafe_allow_html=True)
        
        # 가장 안정적이었던 4:1 비율로 원복
        header_cols = st.columns([2, 1])
        header_cols[0].markdown("<div style='font-size: 15px;'><b>이 름 &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; 예측 &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; 상태/입금</b></div>", unsafe_allow_html=True)
        header_cols[1].markdown("<div style='font-size: 15px;'><b>관리</b></div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:2px 0px 10px 0px;'>", unsafe_allow_html=True)
        
        for index, row in df.iterrows():
            row_cols = st.columns([2, 1])
            
            info_string = f"<div style='font-size: 15px; padding-top: 5px; white-space: nowrap;'><b>{row['name']}</b> &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; <span style='color: #d32f2f; font-weight: bold;'>{row['mexico']} : {row['korea']}</span> &nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp; {row['status_text']}/{row['paid_mark']}</div>"
            row_cols[0].markdown(info_string, unsafe_allow_html=True)
            
            if row_cols[1].button("변경", key=f"btn_{row['name']}", disabled=not is_open):
                st.session_state.target_name = row['name']
                st.rerun()

    if is_finished:
        winners = df[df['status_text'] == '당첨']['name'].tolist()
        st.markdown("---")
        st.subheader("🏆 최종 당첨자 결과")
        if winners:
            winner_text = ", ".join([f"**{w}**님" for w in winners])
            st.balloons()
            st.success(f"🥳 **축하합니다!** {winner_text} 정확히 맞추셨습니다! 🎁")
        else:
            st.info("😭 아쉽게도 최종 스코어를 정확히 맞춘 사람이 없습니다.")
else:
    st.info("아직 투표한 사람이 없습니다.")

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
