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
import streamlit as st
import pandas as pd
import itertools
from collections import defaultdict, deque
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

st.header("⑤ 선후행 제약 설정")

# ───────────────────────────────────────────────
# 0) 공통 데이터 로드 & 간단 검증
# ───────────────────────────────────────────────
acts_df = st.session_state.get("activities", pd.DataFrame())
jobs_df = st.session_state.get("job_acts_map", pd.DataFrame())

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
    pd.DataFrame(columns=["predecessor", "successor",
                          "gap_min", "adjacent"])   # ← NEW
)
prec_df = st.session_state["precedence"].copy()
valid_acts = set(ACT_OPTS) | {"__START__", "__END__"}
prec_df = prec_df[prec_df["predecessor"].isin(valid_acts)
                  & prec_df["successor"].isin(valid_acts)]
st.session_state["precedence"] = prec_df

with st.expander("📐 공통 순서 규칙(Precedence)", expanded=True):
    ## START / END 선택
    col1, col2 = st.columns(2)
    first = col1.selectbox("가장 먼저 할 활동", ["(지정 안 함)"] + ACT_OPTS, index=0)
    last  = col2.selectbox("가장 마지막 활동", ["(지정 안 함)"] + ACT_OPTS, index=0)

    if st.button("➕ START/END 규칙 반영", key="btn_add_start_end"):
        # 기존 __START__/__END__ 와 관련된 행 제거
        tmp = prec_df[
            (~prec_df["predecessor"].isin(["__START__", "__END__"])) &
            (~prec_df["successor"].isin(["__START__", "__END__"]))
        ].copy()

        rows = []
        if first != "(지정 안 함)":
            rows.append({"predecessor": "__START__", "successor": first, "gap_min": 0})
        if last  != "(지정 안 함)":
            rows.append({"predecessor": last, "successor": "__END__", "gap_min": 0})

        st.session_state["precedence"] = pd.concat([tmp, pd.DataFrame(rows)], ignore_index=True)
        st.success("START/END 규칙 반영 완료")

    ## 자유 규칙 추가
    st.markdown("##### 자유 규칙 추가")
    with st.form("form_add_rule"):
        c = st.columns(3)
        p  = c[0].selectbox("선행", ACT_OPTS)
        s  = c[1].selectbox("후행", ACT_OPTS)
        g  = c[2].number_input("간격(분)", 0, 60, 5)
        adj = st.checkbox("A ↔ B 붙이기(인접)", value=False)
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
                    [df, pd.DataFrame([{"predecessor": p, "successor": s, "gap_min": g, "adjacent":adj}])],
                    ignore_index=True
                )
                st.success("추가 완료!")

    ## ========== 멀티셀렉트 + 삭제 버튼 추가 부분 시작 ==========
    # (1) “삭제표시용” 문자열 컬럼 생성 → 예: "발표준비 → 발표면접 (gap=5)"
    prec_df = st.session_state["precedence"].copy()
    prec_df["삭제표시용"] = prec_df.apply(
        lambda r: f"{r.predecessor} → {r.successor} (gap={r.gap_min})", axis=1
    )
    delete_options = prec_df["삭제표시용"].tolist()

    # (2) multiselect으로 삭제할 규칙 선택
    to_delete = st.multiselect(
        "삭제할 규칙을 선택하세요",
        options=delete_options,
        default=[],
        help="여러 개를 Ctrl/Cmd+클릭으로 선택할 수 있습니다."
    )

    # (3) “❌ 선택된 규칙 삭제” 버튼
    if st.button("❌ 선택된 규칙 삭제"):
        if not to_delete:
            st.warning("삭제하려면 먼저 목록에서 규칙을 하나 이상 선택하세요.")
        else:
            # “삭제표시용” 컬럼 값이 to_delete에 포함되지 않은 행만 남김
            new_prec = prec_df[~prec_df["삭제표시용"].isin(to_delete)].drop(
                columns="삭제표시용"
            ).reset_index(drop=True)
            st.session_state["precedence"] = new_prec.copy()
            st.success("선택된 규칙이 삭제되었습니다!")
    # (4) ——————————
    # (5) 이제 “간단히 st.data_editor로 편집만” 허용할 수도 있고, 
    #      혹은 AgGrid로 보여주기만 할 수도 있습니다.
    #      “체크박스 선택” 기능 없이, 단순히 셀을 수정만 하게 하고 싶다면
    #      아래 AgGrid 코드를 사용하세요.

    prec_df_for_grid = st.session_state["precedence"].copy()
    gb = GridOptionsBuilder.from_dataframe(prec_df_for_grid)
    gb.configure_default_column(resizable=True, editable=True)
    gb.configure_column(
        "predecessor",
        header_name="선행 활동",
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": ["__START__", "__END__"] + ACT_OPTS},
        width=140,
    )
    gb.configure_column(
        "successor",
        header_name="후행 활동",
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": ["__START__", "__END__"] + ACT_OPTS},
        width=140,
    )
    gb.configure_column(
        "gap_min",
        header_name="간격(분)",
        type=["numericColumn", "numberColumnFilter"],
        width=100,
    )
    gb.configure_column(          # gap_min 컬럼 바로 아래에 붙여두면 보기 좋음
        "adjacent",
        header_name="붙이기",          # 컬럼 헤더
        cellRenderer="agCheckboxCellRenderer",
        cellEditor="agCheckboxCellEditor",
        editable=True,
        width=90,
    )
    grid_opts = gb.build()

    response = AgGrid(
        prec_df_for_grid,
        gridOptions=grid_opts,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        theme="balham",
        key="prec_aggrid",
    )

    # (6) 셀 편집만 했을 때 세션에 반영하는 버튼
    edited_prec = pd.DataFrame(response["data"])
    if st.button("✅ 변경 적용"):
        df_edit = edited_prec.dropna(subset=["predecessor","successor"])
        df_edit = df_edit[
            (df_edit["predecessor"] != "") & (df_edit["successor"] != "")
        ].reset_index(drop=True)
        st.session_state["precedence"] = df_edit.copy()
    ## ========== 멀티셀렉트 + 삭제 버튼 추가 부분 끝 ==========



# ────────────────────────────────────────────────────────
# 단계 1-C) 제약된 규칙을 기반으로 가능한 모든 활동 순서를 계산하여 보여주기 (gap_min + START/END 포함)
# ────────────────────────────────────────────────────────
import itertools
import pandas as pd

def render_dynamic_flows(prec_df: pd.DataFrame, base_nodes: list[str]) -> list[str]:
    """
    prec_df: ['predecessor','successor','gap_min','adjacent']
    base_nodes: 순서에 포함될 활동 리스트
    """
    # 1) 규칙(rules)에 adjacent까지 함께 읽어오기
    rules = [
        (row.predecessor, row.successor,
         int(row.gap_min),
         bool(getattr(row, "adjacent", False)))
        for row in prec_df.itertuples()
    ]
    n = len(base_nodes)
    valid_orders = []

    # 2) 인터뷰 느낌 이모지 풀(10개) + 동적 매핑
    emoji_pool = ["📝","🧑‍💼","🎤","💼","🗣️","🤝","🎯","🔎","📋","⏰"]
    icons = { act: emoji_pool[i % len(emoji_pool)]
              for i, act in enumerate(base_nodes) }

    # 3) 모든 순열 검사
    for perm in itertools.permutations(base_nodes, n):
        ok = True
        for p, s, gap, adj in rules:
            # START → S
            if p == "__START__":
                if perm[0] != s:
                    ok = False
                if not ok: break
                else: continue
            # P → END
            if s == "__END__":
                if perm[-1] != p:
                    ok = False
                if not ok: break
                else: continue
            # 일반 활동 간 제약
            if p in perm and s in perm:
                i_p, i_s = perm.index(p), perm.index(s)
                # 붙이기(adjacent) 또는 gap>0 모두 “인접” 처리
                if adj or gap > 0:
                    if i_s != i_p + 1:
                        ok = False
                        break
                else:
                    # gap==0: 순서만 보장
                    if i_p >= i_s:
                        ok = False
                        break
        if ok:
            valid_orders.append(perm)

    # 4) 문자열로 변환 (아이콘 + 활동명)
    flow_strs = []
    for order in valid_orders:
        labels = [f"{icons[act]} {act}" for act in order]
        flow_strs.append(" ➔ ".join(labels))
    return flow_strs
# ────────────────────────────────────────────────
# 1-C) 가능한 동선 미리보기 UI
# ────────────────────────────────────────────────
with st.expander("🔍 실시간 동선(활동 순서) 미리보기", expanded=True):
    prec_df_latest = st.session_state["precedence"]
    if prec_df_latest.empty:
        st.info("추가된 precedence 규칙이 없습니다. 자유 규칙을 먼저 추가해 주세요.")
    else:
        flows = render_dynamic_flows(prec_df_latest, ACT_OPTS)
        if not flows:
            st.warning("현재 제약을 만족하는 활동 순서가 없습니다.")
        else:
            st.markdown("**가능한 모든 활동 순서:**")
            for f in flows:
                st.markdown(f"- {f}")
# ───────────────────────────────────────────────
# 2) Branch-Template (offset 파라미터) + 플로우 미리보기  (기존 코드 유지)
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
    ico = {"인성검사":"🧩", "발표준비":"📝", "발표면접":"🎤", "토론면접":"💬"}
    a,b,c,d = ico["인성검사"], ico["발표준비"], ico["발표면접"], ico["토론면접"]

    if wave >= 0:
        order = [a,b,c,d]
    else:
        order = [a,d,b,c]

    arr_txt   = "" if arr == 0 else " (+5′)"
    slide_txt = "" if slide == 0 else f"  Δ{slide}′"
    return " → ".join(order) + slide_txt + arr_txt

# with st.expander("🏷️ 브랜치-템플릿 편집", expanded=True):
#     st.caption(
#         "• `branch`: 대문자 한 글자  • `offset_wave`: 토론–인성 Wave 간격(+/-)\n"
#         "• `offset_slide`: 같은 Wave 안에서 δ-slide(0-60분)  • `arr_off`: 0 또는 5"
#     )
#     edited = st.data_editor(
#         BR_TBL,
#         key="tmpl_editor",
#         use_container_width=True,
#         num_rows="dynamic",
#         column_config={
#             "branch": st.column_config.TextColumn(max_chars=1,
#                                                   help="대문자 한 글자 (A-Z)"),
#             "offset_wave":  st.column_config.NumberColumn(step=1, min_value=-10, max_value=10),
#             "offset_slide": st.column_config.NumberColumn(step=5, min_value=0, max_value=60),
#             "arr_off":      st.column_config.NumberColumn(step=5, min_value=0, max_value=5),
#         },
#     )
#     bad = edited[~edited["branch"].str.fullmatch(r"[A-Z]")]["branch"]
#     if not bad.empty:
#         st.warning(f"잘못된 branch 키: {', '.join(bad.unique())}")

#     st.session_state["branch_templates"] = edited

#     st.markdown("##### ▶ 브랜치별 실행 플로우 (템플릿 기준)")
#     flow_tbl = edited.assign(flow=edited.apply(render_flow, axis=1))[["branch","flow"]]
#     st.dataframe(flow_tbl, hide_index=True, use_container_width=True)

# # ───────────────────────────────────────────────
# # 3) Code ↔ Branch 매핑 (AG-Grid 체크박스 버전)
# # ───────────────────────────────────────────────
# branch_opts = sorted(st.session_state["branch_templates"]["branch"].unique())

# st.session_state.setdefault(
#     "code_branch_map",
#     pd.DataFrame({"code": CODE_LIST, "branches": ""})
# )
# cb_df = st.session_state["code_branch_map"].copy()

# if "branches" not in cb_df.columns:
#     cb_df["branches"] = ""

# cb_df = cb_df[cb_df["code"].isin(CODE_LIST)].reset_index(drop=True)

# rows = []
# for _, row in cb_df.iterrows():
#     code = row["code"]
#     allowed = row["branches"].split("|") if row["branches"].strip() != "" else branch_opts[:]
#     r = {"code": code}
#     for br in branch_opts:
#         r[br] = (br in allowed)
#     rows.append(r)

# df_check = pd.DataFrame(rows)
# gb2 = GridOptionsBuilder.from_dataframe(df_check)
# gb2.configure_column("code", header_name="코드", editable=False, width=120)
# for br in branch_opts:
#     gb2.configure_column(
#         br,
#         header_name=f"브랜치 {br}",
#         cellRenderer="agCheckboxCellRenderer",
#         cellEditor="agCheckboxCellEditor",
#         editable=True,
#         width=100,
#     )

# grid_opts2 = gb2.build()
# grid_response2 = AgGrid(
#     df_check,
#     gridOptions=grid_opts2,
#     update_mode=GridUpdateMode.VALUE_CHANGED,
#     data_return_mode=DataReturnMode.AS_INPUT,
#     fit_columns_on_grid_load=True,
#     theme="balham",
#     key="code_branch_aggrid",
# )

# edited2 = pd.DataFrame(grid_response2["data"])
# new_rows = []
# for _, row in edited2.iterrows():
#     code = row["code"]
#     allowed = [br for br in branch_opts if row.get(br, False)]
#     new_rows.append({"code": code, "branches": "|".join(allowed)})

# st.session_state["code_branch_map"] = pd.DataFrame(new_rows)

st.divider()
if st.button("다음 단계로 ▶", key="next_code_branch_aggrid"):
    st.switch_page("pages/6_⑥ 운영일정추정.py")
