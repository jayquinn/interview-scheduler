# pages/4_OperatingWindow.py  –  최상위 session_state 버전
import streamlit as st, pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from datetime import time

st.header("④ Operating Window (선택)")

# ─────────────────────────────
# 1) 기본 행 자동 채우기
#    (code × date 조합 생성)
# ─────────────────────────────
if st.session_state.get("oper_window") is None:
    # 후보 CSV 에서 code·date 추출 (없으면 빈)
    cand_df = (st.session_state.get("candidates") or
               pd.DataFrame(columns=["code", "interview_date"]))
    base_rows = (cand_df[["code", "interview_date"]]
                 .drop_duplicates()
                 .rename(columns={"interview_date": "date"}))

    if base_rows.empty:
        st.info("⑤ Candidates 업로드 후 돌아와 입력해도 됩니다.")
        base_rows = pd.DataFrame({"code": [""], "date": [pd.NaT]})

    # 기본 시간 08:55 ~ 17:45
    base_rows["start"] = time(8, 55)
    base_rows["end"]   = time(17, 45)
    st.session_state["oper_window"] = base_rows.reset_index(drop=True)

df = st.session_state["oper_window"].copy()

# ─────────────────────────────
# 2) AG-Grid 옵션
# ─────────────────────────────
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("code",  header_name="전형 Code", editable=True)
gb.configure_column("date",  header_name="날짜",       editable=True,
                    type=["dateColumn"])
gb.configure_column("start", header_name="시작 시각",  editable=True,
                    type=["timeColumn"])
gb.configure_column("end",   header_name="종료 시각",  editable=True,
                    type=["timeColumn"])
grid_opts = gb.build()

st.markdown("#### 전형·날짜별 운영 시간")
grid_ret = AgGrid(
    df,
    gridOptions=grid_opts,
    data_return_mode="AS_INPUT",           # ★ 추가: 필터·정렬 상관없이 원본 전체 반환
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    theme="balham",
    key="activities_grid",
)

# 최신 값 저장
st.session_state["oper_window"] = grid_ret["data"]

st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/5_Precedence.py")
