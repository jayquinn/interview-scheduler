# pages/5_OperatingWindow.py
import streamlit as st
import pandas as pd
from datetime import time

st.set_page_config(layout="wide")
st.header("④ 운영 시간 설정 (일일 템플릿)")
st.markdown("""
이 페이지에서는 면접을 운영할 경우의 **하루 기준 운영 시작 및 종료 시간**을 설정합니다.
여기서 설정한 시간은 '운영일정추정' 시뮬레이션에서 모든 직무(Code)에 공통으로 적용되는 기본 운영 시간(템플릿)이 됩니다.
""")

# 0. 세션 상태에서 기존 값 불러오기 (없으면 기본값 사용)
init_start = st.session_state.get("oper_start_time", time(9, 0))
init_end = st.session_state.get("oper_end_time", time(18, 0))

st.subheader("하루 기준 공통 운영 시간")
st.markdown("---")

col_start, col_end = st.columns(2)

with col_start:
    t_start = st.time_input("운영 시작 시간", value=init_start, key="oper_start")

with col_end:
    t_end = st.time_input("운영 종료 시간", value=init_end, key="oper_end")

if t_start >= t_end:
    st.error("오류: 운영 시작 시간은 종료 시간보다 빨라야 합니다.")
    st.stop()

# 1. 설정된 시간을 세션 상태에 저장
st.session_state["oper_start_time"] = t_start
st.session_state["oper_end_time"] = t_end

# 2. oper_window DataFrame 생성 및 저장
# 이제 oper_window는 날짜/코드 없이 시작/종료 시간만 가진 단일 행 DataFrame.
oper_window_dict = {
    "start_time": t_start.strftime("%H:%M"),
    "end_time": t_end.strftime("%H:%M")
}
st.session_state['oper_window'] = pd.DataFrame([oper_window_dict])


with st.expander("🗂 저장된 `oper_window` 데이터 미리보기"):
    st.dataframe(st.session_state.get('oper_window', pd.DataFrame()), use_container_width=True)

st.divider()

if st.button("다음 단계로 ▶"):
    st.switch_page("pages/5_⑤ 선후행제약설정.py")

st.success(f"운영 시간이 {t_start.strftime('%H:%M')}부터 {t_end.strftime('%H:%M')}까지로 설정되었습니다.")
