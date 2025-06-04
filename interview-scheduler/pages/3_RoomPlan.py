# pages/3_RoomPlan.py  –  min/max cap 연동, 최상위 session_state
import streamlit as st, pandas as pd

st.header("③ Room Plan")

# ─────────────────────────────
# 0) 활동별 min/max cap 사전
# ─────────────────────────────
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:
    st.error("먼저 ① Activities & Template 페이지를 완료해 주세요.")
    st.stop()

min_cap = (acts_df.dropna(subset=["room_type"])
           .set_index("room_type")["min_cap"].to_dict())
max_cap = (acts_df.dropna(subset=["room_type"])
           .set_index("room_type")["max_cap"].to_dict())

# ─────────────────────────────
# 1) 날짜 범위 & 행 생성
# ─────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])
date_from = col1.date_input("시작 날짜")
date_to   = col2.date_input("종료 날짜")
if col3.button("날짜 행 생성"):
    if date_from > date_to:
        st.error("시작 날짜가 종료 날짜보다 늦습니다.")
        st.stop()
    days = pd.date_range(date_from, date_to, freq="D").date
    st.session_state["room_plan"] = pd.DataFrame({"date": days})

df = st.session_state.get("room_plan")
if df is None or df.empty:
    st.info("먼저 날짜 범위를 선택하고 **행 생성** 버튼을 눌러주세요.")
    st.stop()

# ─────────────────────────────
# 2) 날짜별 카드
# ─────────────────────────────
new_rows = []
for d in df["date"]:
    used = st.toggle(f"📅 {d} 사용", value=True, key=f"{d}_toggle")
    with st.expander(f"세부 설정 – {d}", expanded=used):
        if not used:
            new_rows.append({
                "date": d,
                "발표면접실_count": 0, "발표면접실_cap": 0,
                "심층면접실_count": 0, "심층면접실_cap": 0,
                "커피챗실_count":   0, "커피챗실_cap":   0,
                "면접준비실_count": 0, "면접준비실_cap": 0,
            })
            continue

        colA, colB = st.columns(2)

        # 개수 입력
        with colA:
            a_cnt = st.number_input("발표면접실 개수", 0, 50, 1, key=f"{d}_a_cnt")
            b_cnt = st.number_input("심층면접실 개수", 0, 50, 1, key=f"{d}_b_cnt")
            c_cnt = st.number_input("커피챗실 개수",   0, 50, 1, key=f"{d}_c_cnt")
            p_cnt = st.number_input("면접준비실 개수", 0, 50, 1, key=f"{d}_p_cnt")

        # 최대 동시 인원 입력 – min/max cap 활용
        with colB:
            a_cap = st.number_input(
                "발표면접실 최대동시인원",
                min_value=int(min_cap.get("발표면접실", 1)),
                max_value=int(max_cap.get("발표면접실", 50)),
                value=int(max_cap.get("발표면접실", 1)),
                key=f"{d}_a_cap")
            b_cap = st.number_input(
                "심층면접실 최대동시인원",
                min_value=int(min_cap.get("심층면접실", 1)),
                max_value=int(max_cap.get("심층면접실", 50)),
                value=int(max_cap.get("심층면접실", 1)),
                key=f"{d}_b_cap")
            c_cap = st.number_input(
                "커피챗실 최대동시인원",
                min_value=int(min_cap.get("커피챗실", 1)),
                max_value=int(max_cap.get("커피챗실", 50)),
                value=int(max_cap.get("커피챗실", 1)),
                key=f"{d}_c_cap")
            p_cap = st.number_input(
                "면접준비실 최대동시인원",
                min_value=int(min_cap.get("면접준비실", 1)),
                max_value=int(max_cap.get("면접준비실", 50)),
                value=int(max_cap.get("면접준비실", 1)),
                key=f"{d}_p_cap")

        new_rows.append({
            "date": d,
            "발표면접실_count": a_cnt, "발표면접실_cap": a_cap,
            "심층면접실_count": b_cnt, "심층면접실_cap": b_cap,
            "커피챗실_count":   c_cnt, "커피챗실_cap":   c_cap,
            "면접준비실_count": p_cnt, "면접준비실_cap": p_cap,
        })

# ─────────────────────────────
# 3) 첫째 날 값 복사
# ─────────────────────────────
if st.button("첫째 날 값을 뒤 날짜에 복사"):
    first = new_rows[0]
    for j in range(1, len(new_rows)):
        for k, v in first.items():
            if k != "date":
                new_rows[j][k] = v
    st.success("복사 완료! 값을 확인 후 다음 단계로 진행해 주세요.")

# 4) 결과 저장 & 미리보기
st.session_state["room_plan"] = pd.DataFrame(new_rows)
st.dataframe(st.session_state["room_plan"], use_container_width=True)

# 5) 다음 단계
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/4_OperatingWindow.py")
