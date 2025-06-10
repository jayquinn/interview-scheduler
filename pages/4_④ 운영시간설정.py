# pages/5_OperatingWindow.py
import streamlit as st, pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from datetime import time

st.header("④ 운영 시간 설정")

# 0️⃣  이전에 저장해 둔 ‘메모’ 키 → 초기 기본값으로 사용
init_start = st.session_state.get("def_start_mem", time(8, 55))
init_end   = st.session_state.get("def_end_mem",   time(17, 45))
colA, colB = st.columns([1, 1])

t_start = colA.time_input("기본 시작", value=init_start, key="def_start")
t_end   = colB.time_input("기본 종료", value=init_end,   key="def_end")

# 👉 버튼은 시간 입력 바로 밑에, 줄 바꿈해서 배치
apply_all_clicked = st.button("🌀 템플릿(공통시간) **모든 날짜/코드에 적용**", use_container_width=True)


    
# ───────── 1. (code, date) 자동 생성 / 보강 ─────────
# ① 현재 oper_window 불러오기 (없으면 빈 DF)
ow = st.session_state.get("oper_window")
if ow is None:
    ow = pd.DataFrame(columns=["code", "date", "start", "end"])
ow["date"] = pd.to_datetime(ow["date"], errors="coerce")
# ② Job ↔ Activities / Room Plan 에서 code·date 추출
job_codes = (
    st.session_state.get("job_acts_map", pd.DataFrame(columns=["code"]))
    ["code"].astype(str).str.strip().replace("", pd.NA).dropna().unique()
)
# room_plan(③ 페이지) 의 ‘date’ 열을 사용
room_plan = st.session_state.get("room_plan",
             pd.DataFrame(columns=["date"]))
dates = sorted(
    pd.to_datetime(room_plan["date"], errors="coerce")
      .dropna()
      .dt.normalize()
      .unique()
)
# ⬇︎⬇︎ 이 블록 추가
if len(dates) == 0:                      # 날짜가 전혀 없으면,
    import datetime                      # (맨 위에 import 할 필요 없으면 OK)
    today = pd.Timestamp.today().normalize()
    dates = [today]                      # ‘오늘’ 하나를 임시로 넣는다
# ③ (code,date) 집합 구축
codes = sorted(job_codes)                     # codes는 job_acts_map 만으로 충분

# cand_exp = st.session_state.get("candidates_exp",
#             pd.DataFrame(columns=["code", "interview_date"]))
# if cand_exp.empty:
#     st.warning("⑥ Candidates 페이지에서 지원자 CSV를 먼저 업로드하세요.")
#     st.stop()
# pairs = (
#     cand_exp[["code", "interview_date"]]
#     .dropna()
#     .rename(columns={"interview_date": "date"})
#     .astype({"code": str})
#     .drop_duplicates()
# )
# pairs["date"] = pd.to_datetime(pairs["date"], errors="coerce")
# pairs.dropna(subset=["date"], inplace=True)
# # ③ (code,date) 집합 구축
# codes = sorted(set(job_codes) | set(pairs["code"].unique()))
# dates = sorted(pairs["date"].dt.normalize().unique())

if not codes:
    st.info("② Job ↔ Activities 페이지에서 직무 코드를 먼저 입력하세요.")
    st.stop()
# if not dates:
#     st.warning("지원자 날짜가 없습니다. CSV 업로드 후 다시 열어 주세요.")
#     st.stop()
# # room_plan 이 비어 있으면 안내 후 종료
# if not dates:
#     st.warning("③ Room Plan 페이지에서 날짜를 먼저 생성하세요.")
#     st.stop()


base = pd.DataFrame([(c, d) for c in codes for d in dates],
                    columns=["code", "date"])

# ④ start/end 기본값 채우기
base["start"] = st.session_state["def_start"]   # time(8, 55) → 세션 값
base["end"]   = st.session_state["def_end"]     # time(17, 45) → 세션 값
# ⑤ 기존 ow 와 merge → 누락 행 추가 & NaT 메우기
merged = (
    base.merge(ow, how="left", on=["code", "date"], suffixes=("", "_old"))
)
for col in ("start", "end"):
    merged[col] = merged[col].combine_first(merged[f"{col}_old"])
merged = merged[["code", "date", "start", "end"]].sort_values(["code", "date"])

st.session_state["oper_window"] = merged.reset_index(drop=True)
# 🔹 0-B. ‘전체 적용’ 클릭 시 모든 start/end 값 덮어쓰기
if apply_all_clicked:
    merged[["start", "end"]] = [t_start, t_end]
    st.session_state["oper_window"] = merged

    # 기본값(메모)도 업데이트
    st.session_state["def_start_mem"] = t_start
    st.session_state["def_end_mem"]   = t_end

    st.toast("공통 운영시간이 모든 행에 적용되었습니다 ✅", icon="✅")



# ───────── 2. AG-Grid 표시 ─────────
# (1) 화면에 보여줄 때 date → date 객체로 변환
df_disp = st.session_state["oper_window"].copy()
df_disp["date"] = df_disp["date"].dt.strftime("%Y-%m-%d")

# (2) Grid 설정
gb = GridOptionsBuilder.from_dataframe(df_disp)
gb.configure_column("code",  header_name="전형 Code", editable=True, width=120)
gb.configure_column("date",  header_name="날짜",       editable=True, type=["dateColumn"])
gb.configure_column("start", header_name="시작 시각",  editable=True, type=["timeColumn"])
gb.configure_column("end",   header_name="종료 시각",  editable=True, type=["timeColumn"])

grid_opts = gb.build()
st.markdown("#### 전형·날짜별 운영 시간")

grid_ret = AgGrid(
    df_disp,
    gridOptions=grid_opts,
    data_return_mode="AS_INPUT",
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    theme="balham",
    key="oper_window_grid",
)

# (3) 사용자가 편집한 결과를 datetime64 로 돌려서 저장
edited = pd.DataFrame(grid_ret["data"])

# 날짜 → datetime64[ns]  (시간 00:00:00 으로 정규화)
edited["date"] = pd.to_datetime(edited["date"], errors="coerce").dt.normalize()
edited = edited.dropna(subset=["date"])

# ───────── ■ NEW ①: (code,date) 누락 보정  ─────────
need_idx = pd.MultiIndex.from_product(
    [codes, dates], names=["code", "date"]
)
edited = (
    edited.set_index(["code", "date"])
          .reindex(need_idx)                # ← 없는 행 자동 생성
          .reset_index()
)

# ───────── ■ NEW ②: start/end 결측 → 기본값 채우기 ─────────
def _to_time(v):
    if isinstance(v, str) and v:
        return pd.to_datetime(v).time()
    if hasattr(v, "hour"):
        return v
    return None

edited["start"] = edited["start"].apply(_to_time)
edited["end"]   = edited["end"].apply(_to_time)

edited["start"].fillna(st.session_state["def_start"], inplace=True)
edited["end"].fillna(  st.session_state["def_end"],   inplace=True)





# ───────── ❶  start_time / end_time 문자열 열 확정 ─────────
def _to_hhmm(v):
    if pd.isna(v):
        return ""
    if isinstance(v, str):
        return v[:5]                # "08:55:00" → "08:55"
    if hasattr(v, "strftime"):
        return v.strftime("%H:%M")  # datetime.time, Timestamp 등
    return str(v)

edited["start_time"] = edited["start"].apply(_to_hhmm)
edited["end_time"]   = edited["end"].apply(_to_hhmm)
# ─────────────────────────────────────────────────────────
edited = edited.drop_duplicates(subset=["code","date"], keep="first")
st.session_state["oper_window"] = edited



st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/5_⑤ 선후행제약설정.py")
