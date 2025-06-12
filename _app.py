# app.py
import streamlit as st
import core_persist as cp
import streamlit as st



# ① ───────────────────────────────
#   이전 세션 내용 자동 복원
cp.autoload_state()

# ② ───────────────────────────────
#   기본 레이아웃
st.set_page_config(page_title="Interview Scheduler",
                   page_icon="📅", layout="wide")
# 첫 화면을 면접운영스케줄링으로 리다이렉트
st.switch_page("pages/1_면접운영스케줄링.py")

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
