import streamlit as st
import sqlite3
import pandas as pd
import requests

# ------------------------------------------------
# ⚙️ 기본 설정 및 DB 연동
# ------------------------------------------------
DB_NAME = 'worldcup.db'
ADMIN_PW = 'jeon0915'
ACCOUNT_INFO = '카카오페이 또는 카카오뱅크 3333-10-3569994 전광용'

conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()
# 테이블 생성 (이름이 고유키(PRIMARY KEY) 역할을 하도록 설정)
c.execute('''CREATE TABLE IF NOT EXISTS bets 
             (name TEXT PRIMARY KEY, pin TEXT, korea INT, mexico INT, paid TEXT)''')
conn.commit()

# ------------------------------------------------
# 📡 실시간 스코어 API 함수 (60초 캐시 적용하여 트래픽 폭탄 방지)
# ------------------------------------------------
@st.cache_data(ttl=60)
def get_live_score():
    """
    무료 API(예: API-Football, API-Sports 등)를 호출하는 부분입니다.
    가입하신 API의 구조에 맞게 아래 URL과 Headers, 파싱 로직을 수정해야 합니다.
    """
    # TODO: 발급받은 무료 API KEY와 경기(Fixture) ID를 넣으세요.
    API_KEY = "발급받은_무료_API_키를_여기에_넣으세요" 
    
    # API 키를 아직 안 넣었거나 에러가 나면 기본값(0:0) 반환
    if API_KEY == "발급받은_무료_API_키를_여기에_넣으세요":
        return 0, 0 
        
    try:
        # 예시: API-Football 구조
        url = "https://v3.football.api-sports.io/fixtures?id=내일경기ID"
        headers = {'x-apisports-key': API_KEY}
        response = requests.get(url, headers=headers).json()
        
        # JSON 응답에서 점수 추출 (사용하는 API에 따라 변경 필요)
        home_score = response['response'][0]['goals']['home']
        away_score = response['response'][0]['goals']['away']
        
        return int(home_score or 0), int(away_score or 0)
    except:
        # API 통신 실패 시 프로그램이 뻗지 않도록 0,0 반환
        return 0, 0

# 현재 스코어 가져오기
live_kr, live_mx = get_live_score()

# ------------------------------------------------
# 🎨 화면 UI 시작
# ------------------------------------------------
st.title("⚽ 한국 vs 멕시코 점수 맞추기 내기!")
st.info(f"💸 **참가비 입금 계좌:** {ACCOUNT_INFO}")

# 상단 실시간 스코어보드
col_score1, col_score2, col_score3 = st.columns([1, 1, 1])
with col_score1:
    st.metric("🇰🇷 한국 (현재)", live_kr)
with col_score2:
    st.markdown("<h2 style='text-align: center;'>VS</h2>", unsafe_allow_html=True)
with col_score3:
    st.metric("🇲🇽 멕시코 (현재)", live_mx)

st.markdown("---")

# ------------------------------------------------
# 📝 투표 및 수정 폼
# ------------------------------------------------
st.subheader("🎯 투표하기 (또는 수정하기)")
with st.form("betting_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("이름 (본명)")
    with col2:
        pin = st.text_input("비밀번호 4자리 (수정용)", type="password", max_chars=4)
        
    col3, col4 = st.columns(2)
    with col3:
        korea_score = st.number_input("🇰🇷 한국 예상 점수", min_value=0, step=1)
    with col4:
        mexico_score = st.number_input("🇲🇽 멕시코 예상 점수", min_value=0, step=1)
    
    submitted = st.form_submit_button("투표 / 수정하기")
    
    if submitted:
        if not name or not pin:
            st.warning("이름과 비밀번호를 모두 입력해주세요.")
        else:
            # DB에서 이름 검색
            c.execute("SELECT pin FROM bets WHERE name=?", (name,))
            row = c.fetchone()
            
            if row: # 이미 투표한 이력이 있는 경우 (수정 모드)
                if row[0] == pin: # 비밀번호 일치
                    c.execute("UPDATE bets SET korea=?, mexico=? WHERE name=?", (korea_score, mexico_score, name))
                    conn.commit()
                    st.success(f"✅ {name}님의 투표가 수정되었습니다!")
                else: # 비밀번호 불일치
                    st.error("❌ 비밀번호가 틀립니다. 본인이 아니라면 수정할 수 없습니다.")
            else: # 새로운 투표인 경우 (신규 등록)
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
    # 실시간 점수와 비교하여 탈락 여부 계산
    # 예측한 점수보다 실제 점수가 이미 더 높아졌다면 무조건 탈락
    df['상태'] = df.apply(lambda x: '☠️ 탈락' if (x['korea'] < live_kr) or (x['mexico'] < live_mx) else '🏃 생존', axis=1)
    
    # 보기 좋게 컬럼명 정리 및 순서 변경
    df.rename(columns={'name': '이름', 'korea': '한국(예상)', 'mexico': '멕시코(예상)', 'paid': '입금확인'}, inplace=True)
    df = df[['이름', '한국(예상)', '멕시코(예상)', '상태', '입금확인']]
    
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.write("아직 투표한 사람이 없습니다.")

st.markdown("---")

# ------------------------------------------------
# 🛠️ 관리자 전용 패널 (입금 상태 변경)
# ------------------------------------------------
with st.expander("🔐 방장 전용 관리자 패널"):
    admin_input = st.text_input("관리자 비밀번호", type="password")
    
    if admin_input == ADMIN_PW:
        st.write("### 💰 입금 확인 관리")
        st.caption("입금이 완료된 사람을 체크하고 '저장'을 누르세요.")
        
        # 입금 상태 수정을 위한 데이터프레임 불러오기
        df_admin = pd.read_sql("SELECT name, paid FROM bets", conn)
        df_admin['입금완료 체크'] = df_admin['paid'] == '✅ 완료'
        
        # 편집 가능한 데이터프레임 UI 제공
        edited_df = st.data_editor(df_admin[['name', '입금완료 체크']], hide_index=True, use_container_width=True)
        
        if st.button("입금 상태 일괄 저장"):
            for index, row in edited_df.iterrows():
                new_status = '✅ 완료' if row['입금완료 체크'] else '❌ 미입금'
                c.execute("UPDATE bets SET paid=? WHERE name=?", (new_status, row['name']))
            conn.commit()
            st.success("입금 상태가 업데이트되었습니다!")
            st.rerun() # 화면 새로고침
    elif admin_input != "":
        st.error("관리자 비밀번호가 틀렸습니다.")
