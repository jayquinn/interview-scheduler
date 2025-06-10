# pages/3_RoomPlan.py
# ─────────────────────────────────────────────
# 공통 방 템플릿(dict) + 날짜별 오버라이드 카드 UI
# ─────────────────────────────────────────────
import streamlit as st, pandas as pd, re

def build_act_space_map(act_df, space_df):
    # 컬럼이 없으면 바로 빈 DF 반환
    if "loc" not in space_df.columns:
        return pd.DataFrame(columns=["activity", "loc"])

    base2act = act_df.set_index("room_type")["activity"].to_dict()
    rows = []
    for loc in space_df["loc"].unique():
        base = re.sub(r"[A-Z]$", "", loc)
        if base in base2act:
            rows.append({"activity": base2act[base], "loc": loc})
    return pd.DataFrame(rows)


st.header("③ 운영 공간 설정")

# ─────────────────────────────────────────────
# 0. 활동 DF → room_types / min_cap / max_cap
# ─────────────────────────────────────────────
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:
    st.error("먼저 ① Activities & Template 페이지를 완료해 주세요."); st.stop()

room_types = sorted(
    acts_df.query("use == True and room_type != ''")["room_type"].unique()
)
if not room_types:
    st.error("room_type 이 지정된 활동이 없습니다."); st.stop()

min_cap = acts_df.set_index("room_type")["min_cap"].to_dict()
max_cap = acts_df.set_index("room_type")["max_cap"].to_dict()
# ▼▼▼  ⭐ NEW ⭐ : “활동이 요구하는 최소 cap” (req_cap) 계산
req_cap = (
    acts_df.query("use == True")           # 사용 중인 활동만
           .groupby("room_type")["max_cap"]
           .max()                          # room_type 별 최댓값
           .to_dict()
)
# ▲▲▲  (예: {'발표준비실': 30, '토론면접실': 5, ...})
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 1. 공통 방 템플릿(dict)  ★ NEW + 호환 변환 ★
# ─────────────────────────────────────────────
tpl_raw = st.session_state.get("room_template")

# ▸ 기존 DataFrame 저장분이 있으면 dict 로 변환
if isinstance(tpl_raw, pd.DataFrame):
    tpl_dict = (tpl_raw.set_index("room_type")[["count", "cap"]]
                        .astype(int)
                        .to_dict("index"))
else:
    tpl_dict = tpl_raw or {}

# room_types 동기화
for rt in room_types:
    tpl_dict.setdefault(rt, {"count": 1, "cap": min_cap.get(rt, 1)})
for rt in list(tpl_dict):
    if rt not in room_types:
        tpl_dict.pop(rt)

# ── UI : number_input 두 컬럼 ─────────────────────────
st.subheader("① 공통 방 템플릿")

col_cnt, col_cap = st.columns(2, gap="large")
with col_cnt:
    st.markdown("#### 방 개수")
    for rt in room_types:
        tpl_dict[rt]["count"] = st.number_input(
            f"{rt} 개수", 0, 50, tpl_dict[rt]["count"], key=f"tpl_{rt}_cnt"
        )

with col_cap:
    st.markdown("#### 최대 동시 인원(cap)")
    for rt in room_types:
        # 👇 value 가 항상 bounds 안에 들어오도록 ‘잘라내기’
        cap_min = min_cap.get(rt, 1)
        cap_max = max_cap.get(rt, 50)
        safe_val = max(cap_min, min(tpl_dict[rt]["cap"], cap_max))   # ← NEW

        tpl_dict[rt]["cap"] = st.number_input(
            f"{rt} cap",
            cap_min,               # min_value
            cap_max,               # max_value
            safe_val,              # value (clamped)
            key=f"tpl_{rt}_cap",
        )
# 템플릿 저장
st.session_state["room_template"] = tpl_dict
if st.button("🛠 cap 값을 활동 max_cap 에 맞추기"):
    for rt in room_types:
        need = req_cap.get(rt, 1)
        tpl_dict[rt]["cap"] = max(tpl_dict[rt]["cap"], need)
    st.session_state["room_template"] = tpl_dict
    st.success("공통 템플릿 cap 이 활동 max_cap 이상으로 보정되었습니다. ↻")
    st.rerun()
st.divider()  # ─────────────────────────────────────────
if st.button("🌀 템플릿 값을 모든 날짜에 적용", key="btn_apply_tpl"):
    room_df = st.session_state.get("room_plan")
    if room_df is None or room_df.empty:
        st.warning("먼저 날짜 범위를 생성하세요.")
    else:
        for rt in room_types:
            room_df[f"{rt}_count"] = tpl_dict[rt]["count"]
            room_df[f"{rt}_cap"]   = tpl_dict[rt]["cap"]
        st.session_state["room_plan"] = room_df.copy()
        st.success("공통 템플릿을 모든 날짜에 적용했습니다.")
# ─────────────────────────────────────────────
# 2. 날짜 범위 입력 → room_plan 기본 생성
# ─────────────────────────────────────────────
with st.expander("② 날짜 범위 설정 (펼치면 세부 날짜 수정 - 초기 설정 단계에선 그냥 지나가세요.)", expanded=False):

    st.subheader("② 날짜 범위 설정")   # ← 기존 코드 그대로

    col1, col2, col3 = st.columns([2, 2, 1])
    date_from = col1.date_input("시작 날짜")
    date_to   = col2.date_input("종료 날짜")


    if col3.button("날짜 행 생성"):
        if date_from > date_to:
            st.error("시작 날짜가 종료 날짜보다 늦습니다."); st.stop()

        days = pd.date_range(date_from, date_to, freq="D").date

        def make_row(day):
            base = {"date": day, "사용여부": True}
            for rt in room_types:
                base[f"{rt}_count"] = tpl_dict[rt]["count"]
                base[f"{rt}_cap"]   = tpl_dict[rt]["cap"]
            return base

        new_df = pd.DataFrame(make_row(d) for d in days)

        base = st.session_state.get("room_plan",
                                    pd.DataFrame(columns=["date"]))
        st.session_state["room_plan"] = (
            pd.concat([base, new_df])
            .drop_duplicates(subset="date")
            .sort_values("date")
            .reset_index(drop=True)
        )

    # ─────────────────────────────────────────────
    # 3. 날짜별 카드 편집 (기존 로직 유지)
    # ─────────────────────────────────────────────
    df = st.session_state.get("room_plan")
    # ★ 변경 ★  – ‘날짜 행’이 하나도 없으면 → 오늘 날짜 한 줄 자동 생성
    if df is None or df.empty:
        today = pd.Timestamp.today().normalize().date()
        df = pd.DataFrame([{
            "date": today, "사용여부": True,
            **{f"{rt}_count": tpl_dict[rt]["count"] for rt in room_types},
            **{f"{rt}_cap":   tpl_dict[rt]["cap"]   for rt in room_types},
        }])

    base_cols = ["사용여부"] + [f"{rt}_{x}" for rt in room_types for x in ("count", "cap")]
    for col in base_cols:
        if col not in df.columns:
            default = True if col == "사용여부" else (
                min_cap.get(col[:-4], 1) if col.endswith("_cap") else 1
            )
            df[col] = default

    new_rows = df.copy()

    for idx, d in enumerate(new_rows["date"]):
        key = d.strftime("%Y-%m-%d")

        def val(col, fallback):
            raw = new_rows.loc[idx, col]
            v = int(raw) if pd.notna(raw) else fallback
            if col.endswith("_cap"):
                base_rt = col[:-4]
                v = max(v, req_cap.get(base_rt, 1))   # ★ min_cap → req_cap 으로
            return v

        used = st.toggle(f"📅 {d} 사용",
                        value=val("사용여부", True),
                        key=f"{key}_toggle")
        new_rows.loc[idx, "사용여부"] = used

        with st.container():
            if used:                      # 토글 on 일 때만 세부 입력 보여주기
                st.markdown(f"##### 세부 설정 – {d}")
            if not used:
                for rt in room_types:
                    new_rows.loc[idx, f"{rt}_count"] = 0
                    new_rows.loc[idx, f"{rt}_cap"]   = 0
                continue
            colA, colB = st.columns(2)
            with colA:
                for rt in room_types:
                    new_rows.loc[idx, f"{rt}_count"] = st.number_input(
                        f"{rt} 개수", 0, 50,
                        val(f"{rt}_count", tpl_dict[rt]["count"]),
                        key=f"{key}_{rt}_cnt"
                    )
            # with colB:
            #     for rt in room_types:
            #         new_rows.loc[idx, f"{rt}_cap"] = st.number_input(
            #             f"{rt} cap",
            #             min_cap.get(rt, 1), max_cap.get(rt, 50),
            #             val(f"{rt}_cap", tpl_dict[rt]["cap"]),
            #             key=f"{key}_{rt}_cap"
            #         )
            with colB:
                for rt in room_types:
                    cap_min = min_cap.get(rt, 1)
                    cap_max = max_cap.get(rt, 50)

                    # value 를 min-max 범위로 한번 ‘잘라내기’
                    raw_val  = val(f"{rt}_cap", tpl_dict[rt]["cap"])
                    safe_val = max(cap_min, min(raw_val, cap_max))

                    new_rows.loc[idx, f"{rt}_cap"] = st.number_input(
                        f"{rt} cap",
                        cap_min,          # min_value
                        cap_max,          # max_value
                        safe_val,         # ✔︎ 범위 안으로 clamp
                        key=f"{key}_{rt}_cap",
                    )

# ─────────────────────────────────────────────
# 4. 결과 저장 + Solver 테이블 변환
# ─────────────────────────────────────────────
st.session_state["room_plan"] = new_rows

def explode_room_plan(df_dates):
    rows = []
    for _, row in df_dates.iterrows():
        # if not row["사용여부"]:
        #     continue
        if not row.get("사용여부", True):
            continue
        if pd.isna(row["date"]):          # ★ 추가 – 날짜가 없으면 skip
            continue
        date = row["date"]
        for rt in room_types:
            for i in range(1, row[f"{rt}_count"] + 1):
                rows.append({
                    "loc": f"{rt}{chr(64+i)}",
                    "date": date,
                    "capacity_max": row[f"{rt}_cap"],
                })
    # 🔽 columns 명시 – 행이 없어도 컬럼은 유지
    return pd.DataFrame(rows, columns=["loc", "date", "capacity_max"])

space_avail = explode_room_plan(new_rows)
st.session_state["space_avail"] = space_avail

st.session_state["activity_space_map"] = build_act_space_map(acts_df, space_avail)

with st.expander("🗂 room_plan / space_avail 미리보기"):
    st.dataframe(new_rows, use_container_width=True)
    st.dataframe(space_avail, height=250)

st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/4_④ 운영시간설정.py")
