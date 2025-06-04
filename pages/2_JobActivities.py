# pages/2_JobActivities.py
import streamlit as st, pandas as pd, re
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.header("② Job ↔ Activities 매핑 (AG-Grid)")

# ── 활동 리스트 ───────────────────────────────
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:
    st.error("① Activities 페이지부터 완료하세요."); st.stop()

act_list = acts_df.query("use == True")["activity"].tolist()
if not act_list:
    st.error("활동을 최소 1개 ‘사용’으로 체크해야 합니다."); st.stop()

# ── 기존 매핑 불러오거나 새로 만들기 ───────────
if st.session_state.get("job_acts_map") is not None:
    job_df = st.session_state["job_acts_map"].copy()
else:
    cand_codes = (st.session_state.get("candidates") or
                  pd.DataFrame(columns=["code"]))["code"].unique().tolist()
    job_df = pd.DataFrame({"code": cand_codes or [""]})

for a in act_list:
    if a not in job_df.columns:
        job_df[a] = True

# --- count 열이 없으면 추가 (기본 0) ----------------
if "count" not in job_df.columns:
    job_df["count"] = 0

# --- 최종 열 순서: code, count, 활동들 --------------
job_df = job_df[["code", "count"] + act_list]


# ── AG-Grid 옵션 ──────────────────────────────
gb = GridOptionsBuilder.from_dataframe(job_df)
gb.configure_default_column(resizable=True, editable=True)
gb.configure_column("code",  header_name="직무 코드", width=120)
gb.configure_column("count", header_name="인원수",
                    type=["numericColumn"], width=90, editable=True)
for a in act_list:
    gb.configure_column(
        a, header_name=a,
        cellEditor="agCheckboxCellEditor",
        cellRenderer="agCheckboxCellRenderer",
        editable=True, singleClickEdit=True, width=110)

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

edited_df = pd.DataFrame(grid_ret["data"])

# ★★★ 항상 세션에 저장 + 공백 제거 ─────────────────
edited_df["code"] = edited_df["code"].astype(str).str.strip()
edited_df["count"] = pd.to_numeric(edited_df["count"], errors="coerce").fillna(0).astype(int)
edited_df = edited_df[edited_df["code"] != ""]

st.session_state["job_acts_map"] = edited_df
# -------------------------------------------------

# ── ➕ 직무 행 추가 (모든 활동 True) ──────────────
if st.button("➕ 직무 코드 행 추가"):
    prefixes, numbers = [], []
    pattern = re.compile(r"^([A-Za-z]+)(\d+)$")
    for c in edited_df["code"]:
        m = pattern.match(c)
        if m:
            prefixes.append(m.group(1))
            numbers.append(int(m.group(2)))
    if prefixes:
        pref = pd.Series(prefixes).mode()[0]
        max_num = max(n for p, n in zip(prefixes, numbers) if p == pref)
        next_num = max_num + 1
    else:
        pref, next_num = "M", 1
    new_code = f"{pref}{next_num:02d}"
    new_row  = {"code": new_code, "count": 0, **{a: True for a in act_list}}
    edited_df = pd.concat([edited_df, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state["job_acts_map"] = edited_df
    st.rerun()

st.write("DEBUG job_acts_map ▶", st.session_state["job_acts_map"])

st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/3_RoomPlan.py")
