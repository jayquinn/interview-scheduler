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


st.set_page_config(layout="wide")
st.header("③ 운영 공간 설정 (일일 템플릿)")
st.markdown("""
이 페이지에서는 면접을 운영할 경우, **하루에 동원 가능한 모든 공간의 종류와 수, 그리고 최대 수용 인원**을 설정합니다.
여기서 설정한 값은 '운영일정추정' 시뮬레이션의 기본 조건(일일 템플릿)으로 사용됩니다.
""")

# ─────────────────────────────────────────────
# 0. 활동 DF → room_types / min_cap / max_cap
# ─────────────────────────────────────────────
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:
    st.error("먼저 ① 면접활동정의 페이지를 완료해 주세요.")
    st.stop()

room_types = sorted(
    acts_df.query("use == True and room_type != '' and room_type.notna()")["room_type"].unique()
)
if not room_types:
    st.error("사용(use=True)하도록 설정된 활동 중, 'room_type'이 지정된 활동이 없습니다. '① 면접활동정의' 페이지를 확인해주세요.")
    st.stop()

min_cap_req = acts_df.set_index("room_type")["min_cap"].to_dict()
max_cap_req = acts_df.set_index("room_type")["max_cap"].to_dict()
# ▼▼▼  ⭐ NEW ⭐ : "활동이 요구하는 최소 cap" (req_cap) 계산
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
    tpl_dict.setdefault(rt, {"count": 1, "cap": max_cap_req.get(rt, 1)})
for rt in list(tpl_dict):
    if rt not in room_types:
        tpl_dict.pop(rt)

# ── UI : number_input 두 컬럼 ─────────────────────────
st.subheader("하루 기준 운영 공간 설정")
st.markdown("---")

col_cnt, col_cap = st.columns(2, gap="large")

with col_cnt:
    st.markdown("#### 방 개수")
    for rt in room_types:
        tpl_dict[rt]["count"] = st.number_input(
            f"{rt} 개수", 
            min_value=0, 
            max_value=50, 
            value=tpl_dict[rt].get("count", 1), 
            key=f"tpl_{rt}_cnt"
        )

with col_cap:
    st.markdown("#### 최대 동시 수용 인원")
    for rt in room_types:
        min_val = min_cap_req.get(rt, 1)
        max_val = max_cap_req.get(rt, 50)
        # 현재 값(value)이 min/max 범위 안에 있도록 보정
        current_val = tpl_dict[rt].get("cap", max_val)
        safe_val = max(min_val, min(current_val, max_val))

        tpl_dict[rt]["cap"] = st.number_input(
            f"{rt} Cap",
            min_value=min_val,
            max_value=max_val,
            value=safe_val,
            key=f"tpl_{rt}_cap",
        )

# 변경된 템플릿 정보를 session_state에 저장
st.session_state['room_template'] = tpl_dict

# 2. room_plan 생성 및 저장
# 이제 room_plan은 날짜 컬럼 없이, 템플릿 값만 반영하는 단일 행 DataFrame이 됨
room_plan_rows = []
for rt, values in tpl_dict.items():
    room_plan_rows.append({
        'room_type': rt,
        'count': values['count'],
        'cap': values['cap']
    })

room_plan_df = pd.DataFrame(room_plan_rows)
# 데이터가 있을 때만 저장
if not room_plan_df.empty:
    # count와 cap 컬럼을 모두 포함하는 형태로 재구성
    final_room_plan = pd.DataFrame([
        {
            f"{row.room_type}_count": row['count'],
            f"{row.room_type}_cap": row['cap']
        }
        for _, row in room_plan_df.iterrows()
    ]).T.reset_index().rename(columns={'index': 'type', 0: 'value'}).T
    # 위 방식은 복잡하니, 더 직관적인 dict 형태로 저장
    
    final_plan_dict = {}
    for rt, values in tpl_dict.items():
        final_plan_dict[f"{rt}_count"] = values['count']
        final_plan_dict[f"{rt}_cap"] = values['cap']
    
    # DataFrame으로 변환하여 저장 (한 행짜리)
    st.session_state['room_plan'] = pd.DataFrame([final_plan_dict])


with st.expander("🗂 저장된 `room_plan` 데이터 미리보기"):
    st.dataframe(st.session_state.get('room_plan', pd.DataFrame()), use_container_width=True)


st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/4_④ 운영시간설정.py")
