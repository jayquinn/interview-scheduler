# pages/5_Candidates.py
import streamlit as st
import pandas as pd

st.header("⑥ Candidates Upload")

uploaded = st.file_uploader("CSV 업로드 (id, code, interview_date)", type="csv")

if uploaded:
    # 0) 필수 열만 체크 ────────────────────────────────────────────
    df_raw = pd.read_csv(uploaded, encoding="utf-8-sig")
    df_raw["code"] = df_raw["code"].astype(str).str.strip()   # ← 공백 제거
    need = {"id", "code", "interview_date"}
    miss = need - set(df_raw.columns)
    if miss:
        st.error(f"CSV에 다음 열이 필요합니다: {', '.join(miss)}")
        st.stop()

    # 1) Job ↔ Activities 매핑표 가져오기 ─────────────────────────
    job_map = st.session_state.get("job_acts_map")
    if job_map is None or job_map.empty:
        st.error("먼저 ② Job ↔ Activities 페이지에서 직무·활동 매핑을 완성해 주세요.")
        st.stop()

    # ★★★ [추가] 체크박스 값을 'True/False' → 실제 bool 로 변환 ★★★
    act_cols = [c for c in job_map.columns if c not in ("code", "count")]
    for col in act_cols:
        job_map[col] = (
            job_map[col]                       # 여러 형식을 문자열로 통일
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False, "1": True, "0": False})
            .fillna(False)                     # 그 외 값은 False
        )

    # 2) 'True'인 활동 리스트를 코드별로 준비 ─────────────────────

    acts_by_code = (
        job_map
        .set_index("code")[act_cols]
        .apply(lambda row: [a for a, v in row.items() if v], axis=1)
    )

    # 3) 후보별 활동 붙이기 → explode ────────────────────────────
    df_raw["activity_list"] = df_raw["code"].map(acts_by_code)
    if df_raw["activity_list"].isna().any():
        bad = df_raw[df_raw["activity_list"].isna()]["code"].unique()
        st.error(f"매핑표에 없는 code 발견: {', '.join(bad)}")
        st.stop()

    df_exp = (
        df_raw
        .explode("activity_list")
        .rename(columns={"activity_list": "activity"})
        .assign(activity=lambda d: d["activity"].str.strip())
        .reset_index(drop=True)
    )


    # 4) 세션 저장 ─────────────────────────────
    df_raw = df_raw.reset_index(drop=True)        # 인덱스 리셋
    # df_exp 은 앞에서 이미 reset_index(drop=True) 적용됨

    st.session_state["candidates"]     = df_raw
    st.session_state["candidates_exp"] = df_exp


    st.success("업로드 및 활동 매핑 완료!")
    st.dataframe(df_exp, use_container_width=True)

if st.button("다음 단계로 ▶"):
    st.switch_page("pages/6_OperatingWindow.py")
