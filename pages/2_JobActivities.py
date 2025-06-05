# pages/2_JobActivities.py
import streamlit as st
import pandas as pd
import re
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.header("② Job ↔ Activities 매핑 (AG-Grid + 멀티셀렉트 삭제/추가)")

# ── 0) “Activities” 페이지에서 넘어온 상태 불러오기 ─────────────────────────
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:
    st.error("① Activities 페이지부터 완료해 주세요.")
    st.stop()

act_list = acts_df.query("use == True")["activity"].tolist()
if not act_list:
    st.error("활동을 최소 1개 ‘사용’으로 체크해야 합니다.")
    st.stop()

# ── 1) 기존 “job_acts_map” 로드 또는 새로 초기화 ─────────────────────────
if "job_acts_map" in st.session_state and isinstance(st.session_state["job_acts_map"], pd.DataFrame):
    job_df = st.session_state["job_acts_map"].copy()
else:
    # “candidates”에서도 있을 수 있는 코드들을 기본으로
    cand_codes = (st.session_state.get("candidates") or pd.DataFrame(columns=["code"]))["code"].unique().tolist()
    job_df = pd.DataFrame({"code": cand_codes or [""]})

# ── 2) 없는 활동 컬럼은 True, “count” 컬럼이 없으면 0 채워넣기 ──────────────────
for act in act_list:
    if act not in job_df.columns:
        job_df[act] = True

if "count" not in job_df.columns:
    job_df["count"] = 0

# “code, count, <활동들>” 순서로 컬럼 정리
cols = ["code", "count"] + act_list
job_df = job_df.reindex(columns=cols)

# 매번 최신 상태를 세션에 저장
st.session_state["job_acts_map"] = job_df

# ── 3) 삭제할 코드를 멀티셀렉트로 선택 ───────────────────────────────────
st.markdown("#### 삭제할 **직무 코드**를 선택 후, 아래 버튼을 눌러주세요.")
codes = st.session_state["job_acts_map"]["code"].tolist()
to_delete = st.multiselect(
    "삭제할 코드 선택",
    options=codes,
    default=[],
    help="여러 개를 Ctrl/Cmd+클릭하여 선택 가능합니다."
)

# ── 4) “❌ 선택 코드 삭제” 버튼 ───────────────────────────────────────────
if st.button("❌ 선택 코드 삭제"):
    if not to_delete:
        st.warning("먼저 삭제할 코드를 하나 이상 선택해 주세요.")
    else:
        kept = job_df[~job_df["code"].isin(to_delete)].copy()
        kept["code"] = kept["code"].astype(str).str.strip()
        kept["count"] = (
            pd.to_numeric(kept["count"], errors="coerce")
              .fillna(0)
              .astype(int)
        )
        kept = kept[kept["code"] != ""].reset_index(drop=True)

        # 세션에 갱신된 DataFrame 덮어쓰기
        st.session_state["job_acts_map"] = kept
        st.success(f"삭제 완료: {', '.join(to_delete)}")
        # → 여기서 따로 st.stop()이나 st.experimental_rerun()을 쓰지 않습니다.
        #    아래 AG-Grid 코드는 이 갱신된 세션 값을 곧바로 다시 그려 줍니다.

# ── 5) “➕ 직무 코드 행 추가” 버튼 ─────────────────────────────────────────
if st.button("➕ 직무 코드 행 추가"):
    current = st.session_state["job_acts_map"].copy()
    prefixes, numbers = [], []
    pattern = re.compile(r"^([A-Za-z]+)(\d+)$")
    for c in current["code"]:
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
    new_row = {"code": new_code, "count": 0, **{act: True for act in act_list}}
    current = pd.concat([current, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state["job_acts_map"] = current.reset_index(drop=True)
    st.success(f"'{new_code}' 행이 추가되었습니다.")
    # → 여기서도 st.stop()이나 st.experimental_rerun() 없이, 
    #    아래 AG-Grid가 곧바로 갱신된 세션값으로 렌더링됩니다.

# ── 6) AG-Grid: “job_acts_map” 편집 가능한 테이블로 표시 ────────────────────
df_to_display = st.session_state["job_acts_map"].copy()

gb2 = GridOptionsBuilder.from_dataframe(df_to_display)
gb2.configure_selection(selection_mode="none")  # 행 선택 기능 없이 순수 편집용
gb2.configure_default_column(resizable=True, editable=True)

gb2.configure_column("code",  header_name="직무 코드", width=120, editable=True)
gb2.configure_column("count", header_name="인원수", type=["numericColumn"], width=90, editable=True)

for act in act_list:
    gb2.configure_column(
        act,
        header_name=act,
        cellRenderer="agCheckboxCellRenderer",
        cellEditor="agCheckboxCellEditor",
        editable=True,
        singleClickEdit=True,
        width=110,
    )

grid_opts2 = gb2.build()

grid_ret2 = AgGrid(
    df_to_display,
    gridOptions=grid_opts2,
    update_mode=GridUpdateMode.VALUE_CHANGED,    # 셀 편집 시 세션 반영
    data_return_mode=DataReturnMode.AS_INPUT,
    fit_columns_on_grid_load=True,
    theme="balham",
    key="job_grid_display",
)

# AG-Grid에서 편집된 내용을 다시 세션에 저장
edited_df2 = pd.DataFrame(grid_ret2["data"])
temp2 = edited_df2.copy()
temp2["code"] = temp2["code"].astype(str).str.strip()
temp2["count"] = pd.to_numeric(temp2["count"], errors="coerce").fillna(0).astype(int)
temp2 = temp2[temp2["code"] != ""].reset_index(drop=True)
st.session_state["job_acts_map"] = temp2

# ── 7) DEBUG: 항상 최신 “job_acts_map”을 확인용으로 출력 ───────────────────────
st.markdown("#### DEBUG job_acts_map ▶")
st.dataframe(st.session_state["job_acts_map"], use_container_width=True)

# ── 8) 네비게이션 버튼 ──────────────────────────────────────────────────
st.divider()
if st.button("다음 단계로 ▶", key="next_job_acts"):
    st.switch_page("pages/3_RoomPlan.py")
