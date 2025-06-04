# pages/7_RunScheduler.py  –  최상위 session_state + len(None) 패치
import streamlit as st
import core
import pandas as pd
import os
from pathlib import Path

st.header("⑦ Run Scheduler")

# ─────────────────────────────
# 0) 간단 디버그 (필요하면 주석 처리)
# ─────────────────────────────
st.write(
    "DEBUG rows:",
    len(st.session_state.get("activities")      or []),
    len(st.session_state.get("candidates_exp")  or []),
)

# ─────────────────────────────
# 1) 이전 실행 결과
# ─────────────────────────────
status = st.session_state.get("run_status")   # None if 처음
wide   = st.session_state.get("run_result")

# ─────────────────────────────
# 2) Run 버튼 → Solver
# ─────────────────────────────
if st.button("Run"):
    with st.spinner("Solving…"):
        cfg = core.build_config(st.session_state)   # 최상위 세션 전체 전달
        status, wide = core.run_solver(cfg)

    # 결과 저장 → 새로고침에도 유지
    st.session_state["run_status"] = status
    st.session_state["run_result"] = wide

# ─────────────────────────────
# 3) 결과 표시 & 다운로드
# ─────────────────────────────
if status == "OK":
    st.success("Success!")
    st.dataframe(wide, use_container_width=True)

    st.download_button(
        label="Excel",
        data=core.to_excel(wide),
        file_name="schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_xlsx",
    )

    st.download_button(
        label="CSV",
        data=wide.to_csv(index=False).encode("utf-8-sig"),
        file_name="schedule.csv",
        mime="text/csv",
        key="dl_csv",
    )

elif status is not None:   # 실행은 했지만 실패
    st.error(f"Solver status: {status}")

# ─────────────────────────────
# 4) Advanced Optimizer (CP-SAT)
# ─────────────────────────────
ROOT_DIR = Path(__file__).resolve().parents[2]
out_csv = ROOT_DIR / "schedule_wide_test_v4_HF.csv"

if st.button("Run Advanced Optimizer"):
    with st.spinner("Solving with CP-SAT…"):
        os.chdir(ROOT_DIR)
        import interview_opt_test_v4 as opt
        opt.main()
        opt.export_schedule_view()

    if out_csv.exists():
        st.session_state["adv_result"] = pd.read_csv(out_csv, encoding="utf-8-sig")
        st.success("Optimization complete")
    else:
        st.session_state["adv_result"] = None
        st.error("Failed to produce schedule")

adv_result = st.session_state.get("adv_result")
if isinstance(adv_result, pd.DataFrame):
    st.subheader("Advanced Optimizer Output")
    st.dataframe(adv_result, use_container_width=True)
    st.download_button(
        label="Download Advanced CSV",
        data=adv_result.to_csv(index=False).encode("utf-8-sig"),
        file_name=out_csv.name,
        mime="text/csv",
        key="adv_csv",
    )
