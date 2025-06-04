# pages/5_Precedence.py  –  B-버전(처음/마지막 체크) + 활동 연동 & 클린업
import streamlit as st
import pandas as pd

st.header("⑤ Precedence Rules")

# ─────────────────────────────
# 1) 활동 목록 (① Activities 페이지와 연동)
# ─────────────────────────────
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:                     # 첫 진입-예외용
    acts_df = pd.DataFrame({"activity": ["발표준비", "발표면접", "심층면접", "커피챗"],
                            "use":       [True,       True,       True,       True]})

# ✔️ ‘use == True’ 로 체크된 활동만 드롭다운에 노출
act_opts = acts_df.query("use == True")["activity"].tolist()

# ─────────────────────────────
# 2) precedence DataFrame 준비
# ─────────────────────────────
st.session_state.setdefault(
    "precedence",
    pd.DataFrame(columns=["predecessor", "successor", "gap_min"])
)
df = st.session_state["precedence"]

# ⬇️ 현재 존재하지 않는 활동이 들어간 행은 자동 제거
valid_acts = set(act_opts) | {"__START__", "__END__"}
df = df[df["predecessor"].isin(valid_acts) & df["successor"].isin(valid_acts)]
st.session_state["precedence"] = df

# ─────────────────────────────
# 3-A) 처음/마지막 체크박스
# ─────────────────────────────
st.markdown("#### ↔ 처음/마지막 활동 지정")
c1, c2 = st.columns(2)
with c1:
    first_act = st.selectbox("가장 먼저 해야 할 활동",
                             ["(지정 안 함)"] + act_opts, index=0)
with c2:
    last_act  = st.selectbox("가장 마지막 활동",
                             ["(지정 안 함)"] + act_opts, index=0)

if st.button("✔️ 체크박스 반영"):
    # 기존 START/END 규칙 제거 후 새로 반영
    df = df[~df["predecessor"].isin(["__START__", "__END__"])]
    df = df[~df["successor"].isin(["__START__", "__END__"])]

    rows = []
    if first_act != "(지정 안 함)":
        rows.append({"predecessor": "__START__", "successor": first_act, "gap_min": 0})
    if last_act != "(지정 안 함)":
        rows.append({"predecessor": last_act, "successor": "__END__", "gap_min": 0})

    st.session_state["precedence"] = pd.concat([df, pd.DataFrame(rows)],
                                               ignore_index=True)
    st.success("반영 완료!")

# ─────────────────────────────
# 3-B) 일반 규칙 추가 폼
# ─────────────────────────────
st.markdown("#### 선행 → 후행 + 최소 간격 규칙 추가")
with st.form("add_rule"):
    cc = st.columns(3)
    pred = cc[0].selectbox("선행 활동", act_opts, key="pred")
    succ = cc[1].selectbox("후행 활동", act_opts, key="succ")
    gap  = cc[2].number_input("최소 간격(분)", 0, 60, 5, key="gap")
    if st.form_submit_button("➕ 규칙 추가"):
        df = st.session_state["precedence"]
        if pred == succ:
            st.warning("같은 활동끼리는 설정할 수 없습니다.")
        elif ((df["predecessor"] == pred) & (df["successor"] == succ)).any():
            st.warning("이미 존재하는 규칙입니다.")
        else:
            new = pd.DataFrame([{
                "predecessor": pred,
                "successor":   succ,
                "gap_min":     gap
            }])
            st.session_state["precedence"] = pd.concat([df, new], ignore_index=True)
            st.success("추가 완료!")

# ─────────────────────────────
# 4) 규칙 테이블 편집
# ─────────────────────────────
st.markdown("#### 현재 규칙")
edited = st.data_editor(
    st.session_state["precedence"],
    key="prec_editor",
    use_container_width=True,
    num_rows="dynamic",
    column_config={"gap_min": st.column_config.NumberColumn("간격(분)", min_value=0)},
)
st.session_state["precedence"] = edited

st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/6_Candidates.py")
