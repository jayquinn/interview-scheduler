# pages/5_Candidates.py  –  최상위 session_state 버전
import streamlit as st
import pandas as pd

st.header("⑤ Candidates Upload")

# ─────────────────────────────
# 1) CSV 업로드
# ─────────────────────────────
uploaded = st.file_uploader("CSV 업로드", type="csv")

if uploaded:
    # (1) 원본 읽기
    df_raw = pd.read_csv(uploaded, encoding="utf-8-sig")
    st.dataframe(df_raw.head())       # 미리보기

    # (2) 활동 셀을 콤마 분해 → long 형태
    df_exp = (df_raw
              .assign(activity=df_raw["activity"].str.split(","))
              .explode("activity")
              .assign(activity=lambda d: d["activity"].str.strip()))

    # (3) 세션에 저장
    st.session_state["candidates"]      = df_raw
    st.session_state["candidates_exp"]  = df_exp

    st.success("업로드 완료!")

# ─────────────────────────────
# 2) 다음 단계
# ─────────────────────────────
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/7_RunScheduler.py")
