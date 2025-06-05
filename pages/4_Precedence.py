# pages/4_Precedence.py
# -*- coding: utf-8 -*-
"""
⑤ Precedence & Branch Settings
────────────────────────────────────────────────────────────
* ① Activities ② Job-Activities 입력을 선행 가정
* 1) 일반 precedence 규칙  (기존 기능·그대로)
* 2) Branch-Template       (offset 파라미터 표 + 새 ‘플로우’ 미리보기)
* 3) Code ↔ Branch 매핑    (직무코드 → 사용할 브랜치)
"""
import streamlit as st, pandas as pd, re

st.header("⑤ Precedence & Branch Settings")

# ───────────────────────────────────────────────
# 0) 공통 데이터 로드 & 간단 검증
# ───────────────────────────────────────────────
acts_df = st.session_state.get("activities",     pd.DataFrame())
jobs_df = st.session_state.get("job_acts_map",   pd.DataFrame())
# --- [NEW] 활동 → 아이콘 매핑 -----------------------------------
ICON = {
    "인성검사":    "🧑‍💻",
    "발표준비":    "📝",
    "발표면접":    "🎤",
    "토론면접":    "💬",
    "심층면접":    "🔎",
    "__START__":  "🚩",
    "__END__":    "🏁",
}
# --- [NEW] 브랜치별 기본 동선(순서) -------------------------------
BR_FLOW = {
    "A": ["인성검사", "발표준비", "발표면접", "토론면접"],
    "B": ["인성검사", "토론면접", "발표준비", "발표면접"],
}
if acts_df.empty:
    st.error("① Activities 페이지부터 완료해 주세요."); st.stop()
if jobs_df.empty:
    st.error("② Job ↔ Activities 매핑을 먼저 입력하세요."); st.stop()

ACT_OPTS  = acts_df.query("use == True")["activity"].tolist()
CODE_LIST = jobs_df["code"].unique()

# ───────────────────────────────────────────────
# 1) precedence 규칙(공통)  – 기존 기능 유지
# ───────────────────────────────────────────────
st.session_state.setdefault(
    "precedence",
    pd.DataFrame(columns=["predecessor", "successor", "gap_min"])
)
prec_df = st.session_state["precedence"].copy()
valid_acts = set(ACT_OPTS) | {"__START__", "__END__"}
prec_df = prec_df[prec_df["predecessor"].isin(valid_acts)
                  & prec_df["successor"].isin(valid_acts)]
st.session_state["precedence"] = prec_df

with st.expander("📐 공통 순서 규칙(Precedence)", expanded=True):
    ## START / END 선택
    col1, col2 = st.columns(2)
    first = col1.selectbox("가장 먼저 할 활동", ["(지정 안 함)"]+ACT_OPTS, index=0)
    last  = col2.selectbox("가장 마지막 활동", ["(지정 안 함)"]+ACT_OPTS, index=0)

    if st.button("➕ START/END 규칙 반영", key="btn_add_start_end"):
        prec_df = prec_df[~prec_df["predecessor"].isin(["__START__", "__END__"])]
        prec_df = prec_df[~prec_df["successor"   ].isin(["__START__", "__END__"])]

        rows = []
        if first != "(지정 안 함)":
            rows.append({"predecessor":"__START__", "successor":first, "gap_min":0})
        if last  != "(지정 안 함)":
            rows.append({"predecessor":last,        "successor":"__END__", "gap_min":0})
        st.session_state["precedence"] = pd.concat([prec_df, pd.DataFrame(rows)],
                                                   ignore_index=True)
        st.success("START/END 규칙 반영 완료")

    ## 자유 규칙 추가
    st.markdown("##### 자유 규칙 추가")
    with st.form("form_add_rule"):
        c = st.columns(3)
        p  = c[0].selectbox("선행", ACT_OPTS)
        s  = c[1].selectbox("후행", ACT_OPTS)
        g  = c[2].number_input("간격(분)", 0, 60, 5)
        ok = st.form_submit_button("➕ 추가")
        if ok:
            df = st.session_state["precedence"]
            dup = ((df["predecessor"] == p) & (df["successor"] == s)).any()
            if p == s:
                st.warning("같은 활동끼리는 지정할 수 없습니다.")
            elif dup:
                st.warning("이미 존재하는 규칙입니다.")
            else:
                st.session_state["precedence"] = pd.concat(
                    [df, pd.DataFrame([{"predecessor":p,"successor":s,"gap_min":g}])],
                    ignore_index=True)
                st.success("추가 완료!")

    ## 현재 표 편집
    st.data_editor(
        st.session_state["precedence"],
        key="prec_editor",
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "gap_min": st.column_config.NumberColumn("간격(분)", min_value=0)
        },
    )
# ────────────────────────────────
# 1-C) 브랜치 동선 미리보기  ⭐ NEW
# ────────────────────────────────
with st.expander("🔍 브랜치별 동선 미리보기", expanded=True):
    br_defined = set(st.session_state["branch_templates"]["branch"])
    if not br_defined:
        st.info("먼저 ⬇️ 브랜치-템플릿 표에 브랜치를 최소 1개 입력해 주세요.")
    for br in sorted(br_defined):
        flow = BR_FLOW.get(br)
        if not flow:
            st.warning(f"브랜치 **{br}** 에 대한 기본 동선 정의가 없습니다.")
            continue
        icons = " ➔ ".join(ICON.get(a, a) for a in flow)
        st.markdown(f"**{br}** : {icons}")
# ───────────────────────────────────────────────
# 2) Branch-Template (offset 파라미터) + 플로우 미리보기
# ───────────────────────────────────────────────
st.session_state.setdefault(
    "branch_templates",
    pd.DataFrame([
        {"branch":"A", "offset_wave":  4, "offset_slide":0, "arr_off":0},
        {"branch":"B", "offset_wave": -3, "offset_slide":0, "arr_off":5},
    ])
)
BR_TBL = st.session_state["branch_templates"]

def render_flow(row: pd.Series) -> str:
    """offset 파라미터 한 줄을 ‘아이콘 플로우’ 문자열로 변환"""
    wave, slide, arr = int(row.offset_wave), int(row.offset_slide), int(row.arr_off)
    # A) 활동 아이콘 – 간단 이모지 매핑
    ico = {"인성검사":"🧩", "발표준비":"📝", "발표면접":"🎤", "토론면접":"💬"}
    a,b,c,d = ico["인성검사"], ico["발표준비"], ico["발표면접"], ico["토론면접"]

    # B) offset_wave 로 순서 결정
    #   (wave > 0  ⇒ 인성→…→토론  / wave < 0  ⇒ 토론→…→인성)
    if wave >= 0:
        order = [a,b,c,d]      # A-type 기본
    else:
        order = [a,d,b,c]      # B-type 기본

    arr_txt   = "" if arr==0 else " (+5′)"
    slide_txt = "" if slide==0 else f"  Δ{slide}′"
    return " → ".join(order) + slide_txt + arr_txt

# ── 편집 UI + 우측 ‘플로우’ 라이브 미리보기
with st.expander("🏷️ 브랜치-템플릿 편집", expanded=True):
    st.caption("• `branch`: 대문자 한 글자  • `offset_wave`: 토론–인성 Wave 간격(+/-)\n"
               "• `offset_slide`: 같은 Wave 안에서 δ-slide(0-60분)  • `arr_off`: 0 또는 5")
    edited = st.data_editor(
        BR_TBL,
        key="tmpl_editor",
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "branch": st.column_config.TextColumn(max_chars=1,
                                                  help="대문자 한 글자 (A-Z)"),
            "offset_wave":  st.column_config.NumberColumn(step=1,  min_value=-10, max_value=10),
            "offset_slide": st.column_config.NumberColumn(step=5,  min_value=0,   max_value=60),
            "arr_off":      st.column_config.NumberColumn(step=5,  min_value=0,   max_value=5),
        },
    )
    # 검증: branch key 형식
    bad = edited[~edited["branch"].str.fullmatch(r"[A-Z]")]["branch"]
    if not bad.empty:
        st.warning(f"잘못된 branch 키: {', '.join(bad.unique())}")

    st.session_state["branch_templates"] = edited

    # 👉  아이콘 플로우 즉시 렌더
    st.markdown("##### ▶ 브랜치별 실행 플로우")
    flow_tbl = edited.assign(flow=edited.apply(render_flow, axis=1))[["branch","flow"]]
    st.dataframe(flow_tbl, hide_index=True, use_container_width=True)

# ───────────────────────────────────────────────
# 3) Code ↔ Branch 매핑
# ───────────────────────────────────────────────
st.session_state.setdefault(
    "code_branch_map",
    pd.DataFrame({"code": CODE_LIST, "branch": ""})
)
cb_df = st.session_state["code_branch_map"].query("code.isin(@CODE_LIST)").copy()

with st.expander("🔗 코드 ↔ 브랜치 매핑", expanded=False):

    # 3-A) job_acts_map 에 없는 코드는 자동 제거
    cb_df = st.session_state.setdefault(
        "code_branch_map",
        pd.DataFrame({"code": code_list, "branches": ""}),
    )
    cb_df = cb_df[cb_df["code"].isin(code_list)].reset_index(drop=True)

    # 3-B) 한 행씩 multiselect UI
    branch_opts = sorted(st.session_state["branch_templates"]["branch"].unique())
    updated = []
    for i, row in cb_df.iterrows():
        sel = [] if row["branches"] == "" else row["branches"].split("|")
        new_sel = st.multiselect(
            label = f"코드 **{row['code']}** – 허용 브랜치",
            options = branch_opts,
            default = [b for b in sel if b in branch_opts],
            key = f"cb_{row['code']}"
        )
        updated.append({"code": row["code"], "branches": "|".join(new_sel)})

    st.session_state["code_branch_map"] = pd.DataFrame(updated)
# (필요하면) 필수 입력 누락 시 막기
if st.button("다음 단계로 ▶"):
    if st.session_state["code_branch_map"]["branches"].eq("").all():
        st.warning("적어도 하나의 직무 코드에 브랜치를 지정해야 합니다.")
        st.stop()
    st.switch_page("pages/5_Candidates.py")

# ───────────────────────────────────────────────
# 4) 네비게이션
# ───────────────────────────────────────────────
st.divider()
if st.button("다음 단계로 ▶"):
    st.switch_page("pages/5_Candidates.py")
SystemError     