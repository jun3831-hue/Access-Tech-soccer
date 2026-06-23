import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# ------------------------------------------------
# ⚙️ 기본 설정 및 DB 연동
# ------------------------------------------------
# 💡 기존 멕시코전 데이터와 섞이지 않도록 새 DB 파일 생성
DB_NAME = 'worldcup_sa.db'
ADMIN_PW = 'jeon0915'
ACCOUNT_INFO = '카카오페이 또는 카카오뱅크 3333-10-3569994 전광용'

API_KEY = "7a57cc65db3f47e4adea9e1468b053e1"
st_autorefresh(interval=10000, key="score_auto_refresh")

# 💡 6월 25일 오전 10시 마감 적용
DEADLINE = datetime(2026, 6, 25, 10, 0, 0)
MATCH_END = datetime(2026, 6, 25, 12, 0, 0)

now_kst = datetime.utcnow() + timedelta(hours=9)
is_open = now_kst < DEADLINE
is_finished = now_kst >= MATCH_END

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS bets 
             (name TEXT PRIMARY KEY, pin TEXT, safrica INT, korea INT, paid TEXT)''')
conn.commit()

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
                if 'korea' in away_team: return int(home_score), int(away_score)
                else: return int(away_score), int(home_score)
        return 0, 0
    except:
        return 0, 0

live_sa, live_kr = get_live_score()

# ------------------------------------------------
# 🎨 화면 UI 시작
# ------------------------------------------------
st.title("⚽ 남아공 vs 한국 점수 예측")
st.info(f"💸 **참가비(1만원) 입금 계좌:** {ACCOUNT_INFO}")

st.markdown("""
    <style>
    @media (max-width: 768px) {
        .stButton > button {
            padding: 0px 5px !important;
            font-size: 13px !important;
            min-height: 32px !important;
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
        <h2 style='margin: 0;'>남아공 &nbsp;&nbsp; {live_sa} : {live_kr} &nbsp;&nbsp; 한국</h2>
    </div>
""", unsafe_allow_html=True)

# ------------------------------------------------
# 🎯 신규 투표하기 폼
# ------------------------------------------------
st.subheader("🎯 신규 투표하기")
with st.form("new_betting_form"):
    name = st.text_input("이름 (본명)", disabled=not is_open)
    pin = st.text_input("비밀번호 4자리", type="password", max_chars=4, disabled=not is_open)
    
    col1, col2 = st.columns(2)
    with col1:
        safrica_score = st.selectbox("남아공", options=list(range(15)), disabled=not is_open)
    with col2:
        korea_score = st.selectbox("한국", options=list(range(15)), disabled=not is_open)
    
    submitted = st.form_submit_button("투표 제출하기", disabled=not is_open, use_container_width=True)
    
    if submitted and is_open:
        if not name or not pin:
            st.warning("이름과 비밀번호를 모두 입력해주세요.")
        else:
            c.execute("SELECT name FROM bets WHERE name=?", (name,))
            if c.fetchone():
                st.error("❌ 이미 등록된 이름입니다. 기존 내역을 수정하려면 아래 현황판에서 변경 체크박스를 눌러주세요.")
            else:
                c.execute("INSERT INTO bets (name, pin, safrica, korea, paid) VALUES (?, ?, ?, ?, ?)", 
                          (name, pin, safrica_score, korea_score, '❌ 미입금'))
                conn.commit()
                st.success(f"🎉 {name}님 투표 완료!")
                st.rerun()

st.markdown("---")

# ------------------------------------------------
# 🛠️ 투표 수정/삭제 액션 창 (표 위쪽에 고정)
# ------------------------------------------------
if st.session_state.target_name and is_open:
    t_name = st.session_state.target_name
    
    st.warning(f"🛠️ **[{t_name}]님의 투표 관리**")
    st.write("##### 수정하시겠습니까? 삭제하시겠습니까?")
    
    action_type = st.radio("작업 선택", ["수정", "삭제"], horizontal=True, label_visibility="collapsed")
    
    with st.form("action_confirm_form"):
        st.write("본인의 비밀번호 4자리를 입력해주세요.")
        input_pin = st.text_input("비밀번호 확인", type="password", max_chars=4)
        
        new_sa, new_kr = 0, 0
        if action_type == "수정":
            st.info("새로운 예측 점수를 선택하세요.")
            c1, c2 = st.columns(2)
            with c1:
                new_sa = st.selectbox("남아공", options=list(range(15)))
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
                    c.execute("UPDATE bets SET safrica=?, korea=? WHERE name=?", (new_sa, new_kr, t_name))
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
# 📊 현재 생존 현황
# ------------------------------------------------
st.subheader("📊 현재 투표 현황")

df = pd.read_sql("SELECT name, safrica, korea, paid FROM bets", conn)

if not df.empty:
    if is_finished:
        df['🚥 상태'] = df.apply(lambda x: '🎉 당첨' if (x['safrica'] == live_sa) and (x['korea'] == live_kr) else '🔴 탈락', axis=1)
    else:
        df['🚥 상태'] = df.apply(lambda x: '🔴 탈락' if (x['safrica'] < live_sa) or (x['korea'] < live_kr) else '🟢 생존', axis=1)
    
    sort_mapping = {'🎉 당첨': 1, '🟢 생존': 2, '🔴 탈락': 3}
    df['sort_key'] = df['🚥 상태'].map(sort_mapping)
    df = df.sort_values(by=['sort_key', 'name']).reset_index(drop=True)
    
    df['입금'] = df['paid'].apply(lambda x: '✅ 완료' if '완료' in x else '❌ 미입금')
    df['남아공:한국'] = df['safrica'].astype(str) + " : " + df['korea'].astype(str)
    
    df['이름'] = df['name']
    df['변경'] = False  
    
    display_df = df[['🚥 상태', '이름', '남아공:한국', '입금', '변경']]
    dynamic_height = (len(display_df) + 1) * 36 + 10
    
    edited_df = st.data_editor(
        display_df,
        key=f"data_editor_{st.session_state.target_name}",
        hide_index=True,
        use_container_width=True,
        height=dynamic_height,
        disabled=["🚥 상태", "이름", "남아공:한국", "입금"], 
        column_config={
            "변경": st.column_config.CheckboxColumn("변경", default=False)
        }
    )
    
    checked_rows = edited_df[edited_df['변경'] == True]
    if not checked_rows.empty:
        selected_name = checked_rows.iloc[0]['이름']
        if st.session_state.target_name != selected_name:
            st.session_state.target_name = selected_name
            st.rerun()

    if is_finished:
        winners = df[df['🚥 상태'] == '🎉 당첨']['name'].tolist()
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
        
        edited_admin = st.data_editor(df_admin[['name', '입금완료 체크']], hide_index=True, use_container_width=True)
        
        if st.button("입금 상태 일괄 저장"):
            for index, row in edited_admin.iterrows():
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
