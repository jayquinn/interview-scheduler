# pages/2_JobActivities.py
# 직무 × 활동 매핑 (AG-Grid) – 새 행에 모든 활동 기본 True
import streamlit as st, pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.header("② Job ↔ Activities 매핑 (AG-Grid)")

# ── 활동 리스트 ─────────────────────────────────────────
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:
    st.error("① Activities 페이지부터 완료하세요."); st.stop()

act_list = acts_df.query("use == True")["activity"].tolist()
if not act_list:
    st.error("활동을 최소 1개 ‘사용’으로 체크해야 합니다."); st.stop()

# ── 기존 매핑 불러오거나 새로 만들기 ───────────────────
if st.session_state.get("job_acts_map") is not None:
    job_df = st.session_state["job_acts_map"].copy()
else:
    cand_codes = (st.session_state.get("candidates") or
                  pd.DataFrame(columns=["code"]))["code"].unique().tolist()
    job_df = pd.DataFrame({"code": cand_codes or [""]})

# 필수 열 보강
if "count" not in job_df.columns:
    job_df["count"] = 0
for a in act_list:
    if a not in job_df.columns:
        job_df[a] = True          # 새 활동은 기본 True

job_df = job_df[["code","count"] + act_list]      # 열 순서 고정

# ── AG-Grid 옵션 ───────────────────────────────────────
gb = GridOptionsBuilder.from_dataframe(job_df)
gb.configure_default_column(resizable=True, editable=True)
gb.configure_column("code", header_name="직무 코드")
gb.configure_column("count", header_name="인원수",
                    type=["numericColumn"], width=90)

for a in act_list:
    gb.configure_column(
        a, header_name=a,
        cellEditor="agCheckboxCellEditor",
        cellRenderer="agCheckboxCellRenderer",
        editable=True, singleClickEdit=True, width=100)

grid_ret = AgGrid(
    job_df,
    gridOptions=gb.build(),
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    theme="balham",
    key="job_grid",
)

edited_df = grid_ret["data"]

# ── ➕ 직무 행 추가  (모든 활동 기본 True) ──────────────
if st.button("➕ 직무 코드 행 추가"):
    used = [int(c[3:]) for c in edited_df["code"]
            if isinstance(c, str) and c.startswith("NEW") and c[3:].isdigit()]
    new_code = f"NEW{max(used, default=0)+1:02d}"
    new_row = {"code": new_code, "count": 0,
               **{a: True for a in act_list}}   # 기본 True!
    edited_df = pd.concat([edited_df, pd.DataFrame([new_row])],
                          ignore_index=True)
    st.session_state["job_acts_map"] = edited_df
    st.rerun()

# ── 빈 코드 행 제거 & 세션 저장 ────────────────────────
st.session_state["job_acts_map"] = edited_df[edited_df["code"].str.strip() != ""]

st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/3_RoomPlan.py")
