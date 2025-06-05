# pages/7_RunScheduler.py
import streamlit as st
import core
from solver.solver import load_param_grid      # ▶︎ NEW – CSV 로더
import pandas as pd
import traceback, io, sys
import interview_opt_test_v4 as iv4
from interview_opt_test_v4 import prepare_schedule
st.header("⑦ Run Scheduler")
with st.expander("🛠️ 디버그 표 보기", expanded=False):
    if st.button("표 출력"):
        st.subheader("1) activity_space_map (상위 20행)")
        st.dataframe(st.session_state["activity_space_map"].head(20))

        st.subheader("2) space_avail – 2025-06-04")
        st.dataframe(
            st.session_state["space_avail"]
            .query("date=='2025-06-04'")
        )

        st.subheader("3) candidates_exp – 2025-06-04 (상위 30행)")
        st.dataframe(
            st.session_state["candidates_exp"]
            .query("interview_date=='2025-06-04'")
            .head(30)
        )
if st.button("🕵️ dup scan"):
    cfg = core.build_config(st.session_state)
    for name, df in cfg.items():
        if not isinstance(df, pd.DataFrame):
            continue
        dup_idx = df.index[df.index.duplicated()].unique().tolist()
        dup_col = df.columns[df.columns.duplicated()].unique().tolist()
        if dup_idx:
            st.write(f"❌ {name} – duplicated INDEX:", dup_idx[:5], "...")
        if dup_col:
            st.write(f"❌ {name} – duplicated COLUMNS:", dup_col)

if st.button("🔍 check index-duplicates"):
    cfg = core.build_config(st.session_state)
    for name, df in cfg.items():
        if isinstance(df, pd.DataFrame):
            if df.index.duplicated().any():
                st.write(f"❌ {name}  duplicated **index** rows")

if st.button("🔍 check col-duplicates"):
    cfg = core.build_config(st.session_state)
    for name, df in cfg.items():
        if isinstance(df, pd.DataFrame):
            dup_cols = df.columns[df.columns.duplicated()].tolist()
            if dup_cols:
                st.write(f"❌ {name}  duplicated columns:", dup_cols)

if st.button("🕵️‍♀️ check duplicates"):
    cfg = core.build_config(st.session_state)
    def dup(df, cols):
        return df.duplicated(subset=cols, keep=False).sum()
    st.write("oper dup :", dup(cfg["oper_window"],  ["code","date"]))
    st.write("room dup :", dup(cfg["room_plan"],    ["date"]))  # loc 은 melt 해야 함




if st.button("🔍 print debug df"):
    cfg = core.build_config(st.session_state)
    for k, v in cfg.items():
        if isinstance(v, pd.DataFrame):
            st.write(f"📄 {k}  shape={v.shape}")
            st.dataframe(v.head())           # 5행만 미리보기
# ─────────────────────────────
# 0) 간단 디버그
# ─────────────────────────────
act_df  = st.session_state.get("activities")
cand_df = st.session_state.get("candidates_exp")
st.write(
    "DEBUG rows:",
    0 if act_df  is None else len(act_df),
    0 if cand_df is None else len(cand_df),
)

# ─────────────────────────────
# A. 시나리오(파라미터) 선택 UI  ←★ 추가 블록
# ─────────────────────────────
grid_df = load_param_grid()                    # CSV → DataFrame
sid = st.selectbox(
    "Parameter scenario",
    grid_df["scenario_id"],
    format_func=lambda s: f"{s} "
                          f"(wave_len={grid_df.set_index('scenario_id').loc[s,'wave_len']})"
)

# 선택한 행을 딕셔너리로 추출
params = (grid_df[grid_df["scenario_id"] == sid]
          .iloc[0]
          .to_dict())

# 문자열로 저장된 숫자를 int 로 변환
params = {k: int(v) if str(v).lstrip("-").isdigit() else v
          for k, v in params.items()}

st.write("▶︎ Selected params:", params)        # (원한다면 제거)

# ─────────────────────────────
# 1) 이전 실행 결과
# ─────────────────────────────
status = st.session_state.get("run_status")
wide   = st.session_state.get("run_result")

# ─────────────────────────────
# 2) Run 버튼 → Solver
# ─────────────────────────────
# if st.button("Run", key="btn_run"):
#     cfg = core.build_config(st.session_state)

#     # ▷▹ Solver 진행·디버그 메시지를 한 상자에 모아보기
#     with st.status("🔍 Solver progress", expanded=True) as box:
#         try:
#             status, wide_or_msg = core.run_solver(
#                 cfg, params=params, debug=True        # 👈 debug=True 유지
#             )
#         except Exception:
#             buf = io.StringIO()
#             traceback.print_exc(file=buf)
#             st.error("‼️ Unexpected exception:")
#             st.code(buf.getvalue())
#             st.stop()

#         if status == "ERR":
#             st.error(wide_or_msg or "Solver returned ERR with no detail")
#             st.stop()

#     # ── 실행 결과를 세션에 저장
#     st.session_state["run_status"]  = status
#     st.session_state["run_result"]  = wide_or_msg if status == "OK" else None
if st.button("Run", key="btn_run"):
    cfg = core.build_config(st.session_state)

    with st.status("🔍 Solver progress", expanded=True):
        status, wide_or_msg = core.run_solver(cfg,
                                              params=params,
                                              debug=True)

    # ⬇️ 세션에도 넣고 **지역 변수도 즉시 갱신** ★★
    st.session_state["run_status"]  = status
    st.session_state["run_result"]  = wide_or_msg if status == "OK" else None
    wide = wide_or_msg              # ← 이 한 줄 추가

# ─────────────────────────────
# 3) 결과 표시 & 다운로드
# ─────────────────────────────
if status == "OK" and wide is not None:          # ✅ wide 존재 확인
    st.success("Success!")

    # (1) 열·행 정리
    df_view = prepare_schedule(wide)         # ✅ 이제 안전

    # (2) 화면 표시
    st.dataframe(df_view, use_container_width=True)

    # (3) Excel (wide 그대로)
    st.download_button(
        "Excel",
        core.to_excel(wide),
        "schedule.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_xlsx"
    )
    # (4) CSV (보기 편한 df_view)
    st.download_button(
        "CSV",
        df_view.to_csv(index=False).encode("utf-8-sig"),
        "schedule.csv",
        "text/csv",
        key="dl_csv"
    )

elif status is not None:          # FAIL / UNSAT / RULE_VIOL / ERR
    st.error(f"Solver status: {status}")
