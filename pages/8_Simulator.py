# pages/8_Simulator.py
# Days Estimator – 활동·직무·방 정보만으로 “며칠 필요?” 계산
import streamlit as st, pandas as pd, itertools, datetime, math, core
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.set_page_config(page_title="Days Estimator", layout="wide")
st.header("⑧ Days Estimator – 최소 며칠이면 되지?")

# ─────────────────────────────────────────────
# 0. 활동 목록 (없으면 기본 5종 주입)
# ─────────────────────────────────────────────
def default_activities() -> pd.DataFrame:
    return pd.DataFrame({
        "use":          [True]*5,
        "activity":     ["발표준비","발표면접","심층면접","커피챗","인성검사"],
        "duration_min": [15,15,20,5,30],
        "room_type":    ["발표준비실","발표면접실","심층면접실","커피챗실","인성검사실"],
    })

acts_df_orig = st.session_state.setdefault("activities", default_activities())
acts_df      = acts_df_orig.copy()

# ─────────────────────────────────────────────
# 1. 활동 표 (‘use’만 편집)
# ─────────────────────────────────────────────
st.subheader("① 활동(전형) 정의")
gb_acts = GridOptionsBuilder.from_dataframe(acts_df)
gb_acts.configure_default_column(resizable=True, editable=False)
gb_acts.configure_column(
    "use", header_name="사용",
    cellEditor="agCheckboxCellEditor", cellRenderer="agCheckboxCellRenderer",
    editable=True, singleClickEdit=True, width=80)

acts_ret = AgGrid(
    acts_df,
    gridOptions=gb_acts.build(),
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    theme="balham",
    key="acts_grid",
    height=200, fit_columns_on_grid_load=True,
)
acts_df  = acts_ret["data"]
act_list = acts_df.query("use == True")["activity"].tolist()
if not act_list:
    st.error("최소 한 개 이상의 활동을 ‘사용’으로 지정해야 합니다."); st.stop()

room_types = (acts_df.loc[acts_df["activity"].isin(act_list), "room_type"]
                     .unique().tolist())

# ─────────────────────────────────────────────
# 2. 직무 ↔ 활동 매핑 & 인원수
# ─────────────────────────────────────────────
st.subheader("② 직무 ↔ 활동 매핑 & 인원수")

if "est_jobs" not in st.session_state:
    st.session_state["est_jobs"] = pd.DataFrame(
        {"code":["DEV"], "count":[5], **{a:[True] for a in act_list}}
    )
job_df = st.session_state["est_jobs"].copy()

# 활동 열 동기화
for a in act_list:
    if a not in job_df.columns:
        job_df[a] = True
job_df = job_df[["code","count"] + act_list]

gb_job = GridOptionsBuilder.from_dataframe(job_df)
gb_job.configure_default_column(resizable=True, editable=True)
gb_job.configure_column("count", header_name="인원수", type=["numericColumn"])
for a in act_list:
    gb_job.configure_column(
        a, header_name=a,
        cellEditor="agCheckboxCellEditor",
        cellRenderer="agCheckboxCellRenderer",
        editable=True, singleClickEdit=True, width=90)

job_ret = AgGrid(
    job_df,
    gridOptions=gb_job.build(),
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    theme="balham",
    key="job_grid",
    reload_data=True,
)
st.session_state["est_jobs"] = job_ret["data"]

# ➕ 직무 행 추가 (모든 활동 True 로 기본 세팅)
if st.button("➕ 직무 행 추가", key="add_row"):
    df = st.session_state["est_jobs"]
    new_row = {"code": f"NEW{len(df)+1:02d}", "count": 0,
               **{a: True for a in act_list}}
    st.session_state["est_jobs"] = pd.concat(
        [df, pd.DataFrame([new_row])], ignore_index=True)
    st.rerun()

# ─────────────────────────────────────────────
# 3. 방 세트  (활동 변경 시 room_type 자동 동기화)
# ─────────────────────────────────────────────
st.subheader("③ 방 세트")

# ―― (1) room_type 동기화 — 누락 추가, 불필요 제거
base_rooms = st.session_state.get("est_rooms", pd.DataFrame())
if base_rooms.empty:
    base_rooms = pd.DataFrame({
        "room_type": room_types,
        "count": [1]*len(room_types),
        "cap":   [5]*len(room_types),
    })
else:
    base_rooms = base_rooms.copy()
    # 새 room_type 추가
    for rt in room_types:
        if rt not in base_rooms["room_type"].values:
            base_rooms = pd.concat(
                [base_rooms, pd.DataFrame([{"room_type": rt,
                                            "count": 1, "cap": 5}])],
                ignore_index=True)
    # 더 이상 쓰지 않는 room_type 삭제
    base_rooms = base_rooms[base_rooms["room_type"].isin(room_types)].reset_index(drop=True)

# ―― (2) AG-Grid — 값 직접 편집
gb_room = GridOptionsBuilder.from_dataframe(base_rooms)
gb_room.configure_default_column(resizable=True, editable=True)
gb_room.configure_column("count", header_name="개수",   type=["numericColumn"])
gb_room.configure_column("cap",   header_name="방당 cap", type=["numericColumn"])

room_ret = AgGrid(
    base_rooms,
    gridOptions=gb_room.build(),
    data_return_mode=DataReturnMode.AS_INPUT,      # 편집 결과 그대로 받기
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    theme="balham",
    key="room_grid",
    reload_data=True,
)

# ―― (3) 최신 값을 세션·로컬 모두 저장
st.session_state["est_rooms"] = room_ret["data"]
rooms_df = room_ret["data"]              # ⬅️  Estimate 단계에서 그대로 사용

# ─────────────────────────────────────────────
# 4. Estimate !
# ─────────────────────────────────────────────
if st.button("Estimate ! (며칠 필요?)", use_container_width=True):

    job_df   = st.session_state["est_jobs"]
    rooms_df = st.session_state["est_rooms"]

    if job_df["count"].sum() == 0:
        st.warning("직무 인원수가 모두 0 입니다."); st.stop()
    if rooms_df["count"].sum() == 0:
        st.warning("방 개수가 모두 0 입니다."); st.stop()

    activities = acts_df.loc[acts_df["activity"].isin(act_list),
                             ["activity","duration_min","room_type"]].assign(use=True)

    # 방 세트 → room_plan 템플릿
    room_row = {f"{rt}_count": int(r["count"]) for _,r in rooms_df.iterrows()
                                               for rt in [r["room_type"]]}
    room_row |= {f"{rt}_cap":   int(r["cap"])   for _,r in rooms_df.iterrows()
                                               for rt in [r["room_type"]]}

    job_map = job_df[["code"] + act_list].copy()

    start_date  = datetime.date.today()
    max_days_try= 30
    feasible_days, final_wide = None, None

    for d in range(1, max_days_try+1):
        dates = [start_date + datetime.timedelta(days=i) for i in range(d)]
        room_plan = pd.DataFrame([{"date": dt} | room_row for dt in dates])

        # 후보 생성
        rows, cyc = [], itertools.cycle(dates)
        for _, row in job_df.iterrows():
            code, n = row["code"], int(row["count"])
            acts    = [a for a in act_list if row[a]]
            act_str = ",".join(acts)
            for i in range(n):
                rows.append({
                    "id": f"{code}_{i+1:03d}",
                    "code": code,
                    "interview_date": next(cyc),
                    "activity": act_str,
                })
        cand = pd.DataFrame(rows)
        cand_exp = (cand.assign(activity=lambda d: d["activity"].str.split(","))
                          .explode("activity")
                          .assign(activity=lambda d: d["activity"].str.strip()))

        cfg = {
            "activities":      activities,
            "room_plan":       room_plan,
            "oper_window":     pd.DataFrame(),
            "precedence":      pd.DataFrame(),
            "job_acts_map":    job_map,
            "candidates":      cand,
            "candidates_exp":  cand_exp,
        }

        status, wide = core.run_solver(cfg)
        if status == "OK":
            feasible_days, final_wide = d, wide
            break

    # ── 결과 ──
    if feasible_days is None or final_wide is None:
        st.error("30일까지 늘려도 배치 불가 – 방 수나 cap 을 늘려 보세요.")
    else:
        # 실제 스케줄이 며칠을 넘기는지 재계산
        dt_start = final_wide.filter(regex="start_").min(axis=None)
        dt_end   = final_wide.filter(regex="end_").max(axis=None)
        delta    = (dt_end - dt_start)                       # pandas.Timedelta
        total_days = math.ceil(delta / pd.Timedelta(days=1)) # ← 여기서 일수로 변환
        st.success(f"✅ 최소 필요 일수: **{total_days} 일**")

        if "interview_date" in final_wide.columns:
            final_wide["date"] = pd.to_datetime(final_wide["interview_date"]).dt.date
        else:
            final_wide["date"] = start_date          # 단일 날짜(스칼라) 그대로 사용
        makespan = (final_wide.groupby("date")
                      .apply(lambda g: (g.filter(regex="end_").max(axis=None) -
                                        g.filter(regex="start_").min(axis=None)))
                      .reset_index(name="makespan"))
        makespan["makespan"] = makespan["makespan"].astype(str)

        st.dataframe(makespan, use_container_width=True)
        st.download_button(
            "스케줄 CSV 다운로드",
            final_wide.to_csv(index=False).encode("utf-8-sig"),
            "schedule_estimated.csv",
            "text/csv",
        )
