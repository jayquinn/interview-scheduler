# pages/1_Activities.py  – AG‑Grid with mode dropdown & row‑add
import streamlit as st
import pandas as pd
from st_aggrid import (
    AgGrid,
    GridOptionsBuilder,
    GridUpdateMode,
    DataReturnMode,
)




st.header("① 면접 활동 정의")

# ───────────────────────────────────────────────
# 1. 기본 템플릿 (모드·cap 디폴트 포함)
# ───────────────────────────────────────────────

def default_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "use": [True, True, True, True, True, True],
            "activity": [
                "면접1",
                "면접2",
                "면접3",
                "면접4",
                "인성검사",
                "커피챗",
            ],
            "mode": [
                "individual", 
                "individual",
                "individual", 
                "individual",
                "individual",
                "individual",
            ],
            "duration_min": [10, 10, 10, 10, 10, 10],
            "room_type": [
                "면접1실",
                "면접2실",
                "면접3실",
                "면접4실",
                "인성검사실",
                "커피챗실",
            ],
            "min_cap": [1, 1, 1, 1, 1, 1],
            "max_cap": [1, 1, 1, 1, 1, 1],
        }
    )

# ───────────────────────────────────────────────
# 2. 세션 기본값 주입 & DF 준비
# ───────────────────────────────────────────────

st.session_state.setdefault("activities", default_df())

df = st.session_state["activities"].copy()

# 누락 컬럼(예: mode) 보강 – 과거 세션 호환
for col, default_val in {
    "use": True,
    "mode": "individual",
    "duration_min": 10,
    "room_type": "",
    "min_cap": 1,
    "max_cap": 1,
}.items():
    if col not in df.columns:
        df[col] = default_val

# ───────────────────────────────────────────────
# 3. AG‑Grid 옵션 설정
# ───────────────────────────────────────────────

gb = GridOptionsBuilder.from_dataframe(df)

# (1) use 체크박스
gb.configure_column(
    "use",
    header_name="사용",
    cellEditor="agCheckboxCellEditor",
    cellRenderer="agCheckboxCellRenderer",
    editable=True,
    singleClickEdit=True,
    width=80,
)

# (2) activity 이름
gb.configure_column("activity", header_name="활동 이름", editable=True)

# (3) mode – dropdown
mode_values = ["individual"] #, "parallel", "batched"

gb.configure_column(
    "mode",
    header_name="모드",
    editable=True,
    cellEditor="agSelectCellEditor",
    cellEditorParams={"values": mode_values},
    width=110,
)

# (4) 기타 숫자 컬럼
for col, hdr in [("duration_min", "소요시간(분)"), ("min_cap", "최소 인원"), ("max_cap", "최대 인원")]:
    gb.configure_column(
        col,
        header_name=hdr,
        editable=True,
        type=["numericColumn", "numberColumnFilter"],
        width=120,
    )

# 숨김: room_type(내부용)
gb.configure_column("room_type", header_name="방 종류", editable=True, hide=True)

grid_opts = gb.build()

# ───────────────────────────────────────────────
# 4. 그리드 표시
# ───────────────────────────────────────────────

st.markdown("#### 활동 정의")

grid_ret = AgGrid(
    df,
    gridOptions=grid_opts,
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    theme="balham",
    key="activities_grid",
)

st.session_state["activities"] = grid_ret["data"]

# ───────────────────────────────────────────────
# 5. ➕ 새 활동 행 추가 (기본 individual, min/max = 1)
# ───────────────────────────────────────────────

if st.button("➕ 활동 행 추가"):
    new_row = {
        "use": True,
        "activity": "NEW_ACT",
        "mode": "individual",
        "duration_min": 10,
        "room_type": "",
        "min_cap": 1,
        "max_cap": 1,
    }
    st.session_state["activities"] = pd.concat(
        [st.session_state["activities"], pd.DataFrame([new_row])],
        ignore_index=True,
    )
    st.rerun()

# ───────────────────────────────────────────────
# 6. 네비게이션
# ───────────────────────────────────────────────

st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/2_② 직무별 면접활동.py")
