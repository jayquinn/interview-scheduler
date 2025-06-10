# pages/6_Simulator.py
# “며칠이 필요?” — 기존 입력값을 그대로 이용해 최소 소요 날짜 추정
import streamlit as st
import re
import pandas as pd, itertools, datetime, math, core
from io import BytesIO
from interview_opt_test_v4 import prepare_schedule, df_to_excel   # ← 이미 준 유틸 재활용

st.set_page_config(page_title="Days Estimator", layout="wide")
st.header("⑥ 운영 일정 추정")

# ─────────────────────────────────────────────
# 0. 세션 값 로드 & 기본 검증
# ─────────────────────────────────────────────
acts_df   = st.session_state.get("activities",           pd.DataFrame())
job_df    = st.session_state.get("job_acts_map",         pd.DataFrame())
room_plan = st.session_state.get("room_plan",            pd.DataFrame())
oper_df   = st.session_state.get("oper_window",          pd.DataFrame())
prec_df   = st.session_state.get("precedence",           pd.DataFrame())

# ① 활동
if acts_df.empty or not (acts_df["use"] == True).any():
    st.error("① Activities 페이지에서 ‘use=True’ 활동을 하나 이상 지정하세요.")
    st.stop()
acts_df = acts_df.query("use == True").reset_index(drop=True)
act_list = acts_df["activity"].tolist()

# ② 직무 + 인원수
if job_df.empty or (job_df["count"].sum() == 0):
    st.error("② Job ↔ Activities 페이지에서 인원수를 1 명 이상 입력하세요.")
    st.stop()
if job_df["code"].duplicated().any():
    st.error("Job code 중복이 있습니다. 수정 후 다시 실행해 주세요.")
    st.stop()
# ── NEW: job_df <-> act_list 열 동기화 ────────────────────────
# (A) act_list 에 있지만 job_df 에 없는 열 → False 로 추가
for a in act_list:
    if a not in job_df.columns:
        job_df[a] = False

# (B) act_list 에서 빠진(=더 이상 use=True 가 아닌) 열은 제거
keep_cols = ["code", "count"] + act_list
job_df = job_df[[c for c in job_df.columns if c in keep_cols]]
# ────────────────────────────────────────────────────────────

# ③ Room Plan – “첫째 날” 값을 템플릿으로 사용
if room_plan.empty:
    st.error("③ Room Plan 페이지에서 방 정보를 먼저 입력하세요.")
    st.stop()
room_tpl = room_plan.iloc[0]   # 첫 행(날짜)에 입력된 방 세트
room_types = [
    re.sub(r"_count$", "", col)           # 뒤의 '_count' 만 제거
    for col in room_tpl.index
    if col.endswith("_count")
]

# ④ 운영시간 – “기본 시작/종료(템플릿)” 우선, 없으면 08:55~17:45
if not oper_df.empty and {"start_time","end_time"} <= set(oper_df.columns):
    common_start = str(oper_df.iloc[0]["start_time"])[:5]   # HH:MM
    common_end   = str(oper_df.iloc[0]["end_time"])[:5]
else:
    # ⑤ Operating Window 페이지에서 저장해 둔 ‘메모’(def_*_mem) 사용
    t_s = st.session_state.get("def_start_mem", datetime.time(8,55))
    t_e = st.session_state.get("def_end_mem",   datetime.time(17,45))
    common_start = t_s.strftime("%H:%M")
    common_end   = t_e.strftime("%H:%M")








st.success("✅ 입력 데이터 검증 통과 – Estimate 버튼을 누르세요!")

# ─────────────────────────────────────────────
# 1. Estimate!
# ─────────────────────────────────────────────
if st.button("Estimate !  (며칠 필요?)", use_container_width=True):
    # ── (1) 파라미터 템플릿 (단순화 모드)
    params_simple = dict(
        wave_len   = 30,   # 의미 없지만 0 불가 → 30
        max_wave   = 1,    # 단일 wave
        br_offset_A= 0,
        br_offset_B= 0,
        min_gap_min= 0,
        tl_sec     = 5,
    )

    # ── (2) 루프 : 1 일 → 30 일
    start_date     = datetime.date.today()
    max_days_try   = 30
    feasible_days  = None
    final_schedule = None

    for d in range(1, max_days_try + 1):
        dates = [start_date + datetime.timedelta(days=i) for i in range(d)]

        # (a) 날짜별 room_plan 행 생성
        rp_rows = []
        for dt in dates:
            row = {"date": dt, "사용여부": True}
            for rt in room_types:
                row[f"{rt}_count"] = int(room_tpl[f"{rt}_count"])
                row[f"{rt}_cap"]   = int(room_tpl[f"{rt}_cap"])
            rp_rows.append(row)
        rp_df = pd.DataFrame(rp_rows)

        # (b) 후보 CSV(가상의 id) 생성
        cand_rows, cyc = [], itertools.cycle(dates)
        for _, r in job_df.iterrows():
            code, n = r["code"], int(r["count"])
            acts    = [a for a in act_list if bool(r.get(a, False))]
            act_str = ",".join(acts)
            for i in range(n):
                cand_rows.append({
                    "id": f"{code}_{i+1:03d}",
                    "code": code,
                    "interview_date": next(cyc),
                    "activity": act_str,
                })
        cand_df = pd.DataFrame(cand_rows)
        cand_exp = (cand_df.assign(activity=lambda d: d["activity"].str.split(","))
                              .explode("activity")
                              .assign(activity=lambda d: d["activity"].str.strip()))

        # # (c) 임시 cfg 사전 구성
        # cfg_tmp = {
        #     "activities":      acts_df,
        #     "room_plan":       rp_df,
        #     "oper_window":     oper_df,         # 공통 시간이면 그대로 전달
        #     "precedence":      prec_df,
        #     "job_acts_map":    job_df,
        #     "candidates":      cand_df,
        #     "candidates_exp":  cand_exp,
        # }


        # # (c) 공통 운영시간 DF(코드×날짜) 생성  ← NEW
        # oper_rows = [
        #     {"code": c, "date": dt,
        #      "start_time": common_start, "end_time": common_end}
        #     for c in job_df["code"].unique()  # 모든 code
        #     for dt in dates                   # 모든 가상-날짜
        # ]
        # oper_window_df = pd.DataFrame(oper_rows)

        # (c) 공통 운영시간 DF(코드×날짜) 생성
        oper_rows = [
            {
                "code": c,
                "date": pd.to_datetime(dt),   # datetime64 로 변환
                "start_time": common_start,   # "08:55" 같은 문자열
                "end_time":   common_end,
            }
            for c in job_df["code"].unique()   # 모든 직무 코드
            for dt in dates                    # 이번 루프의 모든 날짜
        ]
        oper_window_df = pd.DataFrame(oper_rows)




        # (d) 임시 cfg 사전 구성


        cfg_tmp = {
            "activities":      acts_df,
            "room_plan":       rp_df,
            "oper_window":     oper_window_df,  # ← 방금 만든 DF 를 넘김
            "precedence":      prec_df,
            "job_acts_map":    job_df,
            "candidates":      cand_df,
            "candidates_exp":  cand_exp,
        }




        status, wide = core.run_solver(cfg_tmp, params=params_simple)
        if status == "OK":
            feasible_days, final_schedule = d, wide
            break

    # ── (3) 결과 표시
    if feasible_days is None:
        st.error("30 일까지 늘려도 배치 불가 – 방 수나 cap을 늘려 보세요.")
    else:
        st.success(f"✅ 최소 필요 일수: **{feasible_days} 일**")

        # ---------- ✨ 새 코드 시작 ✨ ----------
        # 1) 보기용 DataFrame (열 정렬·변종 이동 포함)
        df_view = prepare_schedule(final_schedule)
        # 👇 이 4줄을 df_view 바로 아래에 추가
        time_cols = [c for c in df_view.columns         # start_ / end_ 전부
                    if re.match(r'^(start|end)_', c)]
        df_view[time_cols] = (df_view[time_cols]        # '' → NaT → datetime64
                            .apply(pd.to_datetime, errors='coerce'))
        # 2) 날짜별 makespan 표 (df_view 기반)
        makespan = (
            df_view.assign(date=lambda d:
                           pd.to_datetime(d['interview_date']).dt.date)
                   .groupby('date')
                   .apply(lambda g: (g.filter(regex='end_').max(axis=None) -
                                     g.filter(regex='start_').min(axis=None)))
                   .reset_index(name='makespan')
        )
        st.markdown("##### ▸ 날짜별 makespan")
        st.dataframe(makespan, use_container_width=True)

        # 3) Excel 다운로드 – 색상 입힌 워크북
        buf = BytesIO()
        df_to_excel(df_view, by_wave=('wave' in df_view), stream=buf)
        st.download_button(
            "Excel 다운로드",
            data=buf.getvalue(),
            file_name="schedule_estimated.xlsx",
            mime=("application/vnd.openxmlformats-officedocument."
                  "spreadsheetml.sheet"),
        )
        # ---------- ✨ 새 코드 끝 ✨ ----------

