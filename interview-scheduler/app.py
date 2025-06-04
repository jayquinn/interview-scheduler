# app.py  –  최상위 session_state + 자동 저장·복원
import streamlit as st
import core_persist as cp

# ① ───────────────────────────────
#   이전 세션 내용 자동 복원
cp.autoload_state()

# ② ───────────────────────────────
#   기본 레이아웃
st.set_page_config(page_title="Interview Scheduler",
                   page_icon="📅", layout="wide")

st.sidebar.title("Interview Scheduler")
st.sidebar.write("왼쪽 페이지 네비게이터로 이동하세요.")

st.header("Home")
st.markdown(
    """
    이 앱은 채용 일정 최적화를 위한 워크플로우 마법사입니다.  
    1. Activities → 2. Room Plan → … → 6. Run 까지 순서대로 진행하세요.
    """
)

# ③ ───────────────────────────────
#   필요한 키가 없으면 기본값 None 세팅
for key in [
    "activities", "room_plan", "oper_window",
    "precedence", "candidates", "candidates_exp",
    "job_acts_map", "run_status", "run_result"
]:
    st.session_state.setdefault(key, None)

# ④ ───────────────────────────────
#   현재 세션 내용을 파일로 자동 저장
cp.autosave_state()
