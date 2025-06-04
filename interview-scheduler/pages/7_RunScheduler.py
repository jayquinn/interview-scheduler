# pages/7_RunScheduler.py  –  최상위 session_state + len(None) 패치
import streamlit as st
import core

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
