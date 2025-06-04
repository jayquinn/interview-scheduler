# pages/3_RoomPlan.py  –  key 안정화(대안 1, 오류 수정본)
import streamlit as st, pandas as pd
st.header("③ Room Plan")
def explode_room_plan(df_dates: pd.DataFrame) -> pd.DataFrame:
    """
    (date, <room>_count, <room>_cap …) DF  ➜
    loc,date,capacity_max DataFrame 으로 변환
    예) 발표면접실_count = 2  → loc = 발표면접실A / 발표면접실B
    """
    rows = []
    for _, row in df_dates.iterrows():
        the_date = row["date"]
        for base in ("발표면접실","심층면접실","커피챗실","면접준비실"):
            n   = int(row[f"{base}_count"])
            cap = int(row[f"{base}_cap"])
            for i in range(1, n+1):
                loc = f"{base}{chr(64+i)}"   # 1→A, 2→B …
                rows.append({"loc":loc, "date":the_date,
                             "capacity_max": cap})
    return pd.DataFrame(rows)
# 0) 활동별 min/max cap
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:
    st.error("먼저 ① Activities & Template 페이지를 완료해 주세요."); st.stop()

min_cap = (acts_df.dropna(subset=["room_type"])
           .set_index("room_type")["min_cap"].to_dict())
max_cap = (acts_df.dropna(subset=["room_type"])
           .set_index("room_type")["max_cap"].to_dict())
# ─────────────────────────────
# 1) 날짜 범위 입력 → 행 생성
# ─────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])
date_from = col1.date_input("시작 날짜")
date_to   = col2.date_input("종료 날짜")


if col3.button("날짜 행 생성"):
    if date_from > date_to:
        st.error("시작 날짜가 종료 날짜보다 늦습니다."); st.stop()

    days = pd.date_range(date_from, date_to, freq="D").date
    new_df = pd.DataFrame({"date": days})

    # (a) 이미 입력돼 있던 room_plan (없으면 빈 DF)
    base = st.session_state.get("room_plan",
                                pd.DataFrame(columns=["date"]))

    # (b) 기존 + 새 날짜 합치고, 중복 제거 후 정렬
    st.session_state["room_plan"] = (
        pd.concat([base, new_df])
          .drop_duplicates(subset="date")
          .sort_values("date")
          .reset_index(drop=True)
    )

df = st.session_state.get("room_plan")
if df is None or df.empty:
    st.info("먼저 날짜 범위를 선택하고 **행 생성** 버튼을 눌러주세요."); st.stop()
base_cols = (
    ["사용여부"] +
    [f"{room}_{suffix}"
     for room in ("발표면접실","심층면접실","커피챗실","면접준비실")
     for suffix in ("count","cap")]
)

for col in base_cols:
    if col not in df.columns:
        default = True if col == "사용여부" else 1
        df[col] = default

# 세션에 다시 저장해 두어야 이후 new_rows.copy()에 열이 존재합니다.
st.session_state["room_plan"] = df
# ─────────────────────────────
# 2) 날짜별 카드
# ─────────────────────────────
new_rows = df.copy()                # ① 기존 DF 복사

for idx, d in enumerate(new_rows["date"]):
    key = d.strftime("%Y-%m-%d")    # 고정 접두어

    # ── helper : DF 값 ↔ 기본값 ─────────────────────────
    def val(col, default):
        return int(new_rows.loc[idx, col]) if pd.notna(new_rows.loc[idx, col]) else default

    used = st.toggle(f"📅 {d} 사용",
                     value=val("사용여부", True),
                     key=f"{key}_toggle")

    new_rows.loc[idx, "사용여부"] = used        # DF에 즉시 반영

    with st.expander(f"세부 설정 – {d}", expanded=used):
        if not used:
            for room in ("발표면접실","심층면접실","커피챗실","면접준비실"):
                new_rows.loc[idx, f"{room}_count"] = 0
                new_rows.loc[idx, f"{room}_cap"]   = 0
            continue

        colA, colB = st.columns(2)

        # ── 개수 입력 ───────────────────────────────────
        with colA:
            new_rows.loc[idx, "발표면접실_count"] = st.number_input(
                "발표면접실 개수", 0, 50, val("발표면접실_count", 1),
                key=f"{key}_a_cnt")
            new_rows.loc[idx, "심층면접실_count"] = st.number_input(
                "심층면접실 개수", 0, 50, val("심층면접실_count", 1),
                key=f"{key}_b_cnt")
            new_rows.loc[idx, "커피챗실_count"] = st.number_input(
                "커피챗실 개수", 0, 50, val("커피챗실_count", 1),
                key=f"{key}_c_cnt")
            new_rows.loc[idx, "면접준비실_count"] = st.number_input(
                "면접준비실 개수", 0, 50, val("면접준비실_count", 1),
                key=f"{key}_p_cnt")

        # ── 최대 동시 인원 입력 ──────────────────────────
        with colB:
            new_rows.loc[idx, "발표면접실_cap"] = st.number_input(
                "발표면접실 최대동시인원",
                int(min_cap.get("발표면접실",1)),
                int(max_cap.get("발표면접실",50)),
                val("발표면접실_cap", int(max_cap.get("발표면접실",1))),
                key=f"{key}_a_cap")
            new_rows.loc[idx, "심층면접실_cap"] = st.number_input(
                "심층면접실 최대동시인원",
                int(min_cap.get("심층면접실",1)),
                int(max_cap.get("심층면접실",50)),
                val("심층면접실_cap", int(max_cap.get("심층면접실",1))),
                key=f"{key}_b_cap")
            new_rows.loc[idx, "커피챗실_cap"] = st.number_input(
                "커피챗실 최대동시인원",
                int(min_cap.get("커피챗실",1)),
                int(max_cap.get("커피챗실",50)),
                val("커피챗실_cap", int(max_cap.get("커피챗실",1))),
                key=f"{key}_c_cap")
            new_rows.loc[idx, "면접준비실_cap"] = st.number_input(
                "면접준비실 최대동시인원",
                int(min_cap.get("면접준비실",1)),
                int(max_cap.get("면접준비실",50)),
                val("면접준비실_cap", int(max_cap.get("면접준비실",1))),
                key=f"{key}_p_cap")
# 3) 첫째 날 값 복사

if st.button("첫째 날 값을 뒤 날짜에 복사"):
    first_row = new_rows.iloc[0]          # ← 열이 아니라 ‘행’ 선택
    for idx in range(1, len(new_rows)):
        for col in new_rows.columns:
            if col != "date":
                new_rows.loc[idx, col] = first_row[col]
    st.success("복사 완료! 값을 확인 후 다음 단계로 진행해 주세요.")
# 4) 결과 저장 & 내부 테이블 생성  ⭐ <<<< 여기부터 교체
st.session_state["room_plan"] = new_rows

# (1) 방별-날짜-수용인원 테이블  ➜  Solver: cfg_avail
space_avail = explode_room_plan(new_rows)
st.session_state["space_avail"] = space_avail

# (2) 활동-공간 매핑 테이블      ➜  Solver: cfg_map
def build_act_space_map(act_df: pd.DataFrame, space_avail: pd.DataFrame) -> pd.DataFrame:
    """'발표면접실A'→'발표면접실'→'발표면접' 식으로 activity 매핑."""
    base2act = act_df.set_index("room_type")["activity"].to_dict()
    rows = []
    for loc in space_avail["loc"].unique():
        base = ''.join(filter(str.isalpha, loc))          # '발표면접실A'→'발표면접실'
        if base in base2act:
            rows.append({"activity": base2act[base], "loc": loc})
    return pd.DataFrame(rows)

st.session_state["activity_space_map"] = build_act_space_map(acts_df, space_avail)

# (3) 화면 미리보기 (선택: 지워도 무방)
st.dataframe(new_rows, use_container_width=True)
st.dataframe(space_avail, height=250)

# 5) 다음 단계
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/4_Precedence.py")