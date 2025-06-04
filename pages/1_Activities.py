# pages/1_Activities.py  – AG-Grid, 안전 저장

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.header("① Activities & Template (AG-Grid)")

# ── 기본 템플릿 ──────────────────────────────────────────
def default_df() -> pd.DataFrame:
    return pd.DataFrame({
        "use"         : [True, True, True, True, False],
        "activity"    : ["발표준비", "발표면접", "심층면접", "커피챗", "인성검사"],
        "duration_min": [15, 15, 20, 5, 30],
        "room_type"   : ["면접준비실", "발표면접실", "심층면접실", "커피챗실", "인성검사실"],
        "min_cap"     : [1, 1, 1, 1, 1],
        "max_cap"     : [10, 5, 3, 8, 5],
    })

# 세션 기본값 주입
st.session_state.setdefault("activities", default_df())

df = st.session_state["activities"].copy()

# ── AG-Grid 옵션 ────────────────────────────────────────
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column(
    "use", header_name="사용",
    cellEditor="agCheckboxCellEditor", cellRenderer="agCheckboxCellRenderer",
    editable=True, singleClickEdit=True, width=80)
gb.configure_column("activity",  header_name="활동 이름", editable=True)
gb.configure_column("room_type", header_name="방 종류", editable=True, hide=True)
for col, hdr in [("duration_min","소요시간(분)"),
                 ("min_cap","최소 인원"), ("max_cap","최대 인원")]:
    gb.configure_column(col, header_name=hdr,
                        editable=True,
                        type=["numericColumn","numberColumnFilter"],
                        width=120)
grid_opts = gb.build()

# ── 그리드 표시 & 값 저장 ───────────────────────────────
st.markdown("#### 활동 정의")
grid_ret = AgGrid(
    df,
    gridOptions=grid_opts,
    data_return_mode=DataReturnMode.AS_INPUT,   # 행 손실 방지!
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    theme="balham",
    key="activities_grid",
)
st.session_state["activities"] = grid_ret["data"]

st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/2_JobActivities.py")
