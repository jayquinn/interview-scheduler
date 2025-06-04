import streamlit as st
import pandas as pd
from pathlib import Path
import os

st.header("⑨ Advanced Scheduler")

# Ensure working directory is project root so relative paths work
ROOT_DIR = Path(__file__).resolve().parents[2]
os.chdir(ROOT_DIR)

out_csv = Path("schedule_wide_test_v4_HF.csv")

if st.button("Run Advanced Optimizer"):
    with st.spinner("Solving with CP-SAT…"):
        import interview_opt_test_v4 as opt
        opt.main()
        opt.export_schedule_view()
    if out_csv.exists():
        st.session_state["adv_result"] = pd.read_csv(out_csv, encoding="utf-8-sig")
        st.success("Optimization complete")
    else:
        st.session_state["adv_result"] = None
        st.error("Failed to produce schedule")

result = st.session_state.get("adv_result")
if isinstance(result, pd.DataFrame):
    st.dataframe(result, use_container_width=True)
    st.download_button(
        label="Download CSV",
        data=result.to_csv(index=False).encode("utf-8-sig"),
        file_name=out_csv.name,
        mime="text/csv",
        key="adv_csv",
    )
