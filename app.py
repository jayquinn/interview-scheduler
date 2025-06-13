# pages/1_면접운영스케줄링.py
import streamlit as st
import pandas as pd
import re
from datetime import time, datetime
from st_aggrid import (
    AgGrid,
    GridOptionsBuilder,
    GridUpdateMode,
    DataReturnMode,
)
from io import BytesIO
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import PatternFill
import core
from solver.solver import solve_for_days, load_param_grid
import core_persist as cp

st.set_page_config(
    page_title="면접운영스케줄링",
    layout="wide"
)

# 이전 세션 내용 자동 복원
cp.autoload_state()

# 사이드바에서 app 페이지 숨기기
st.markdown("""
<style>
    /* 사이드바에서 첫 번째 항목(app) 숨기기 */
    .css-1d391kg .css-1rs6os .css-17eq0hr:first-child {
        display: none !important;
    }
    
    /* 다른 방법으로 app 항목 숨기기 */
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] ul li:first-child {
        display: none !important;
    }
    
    /* 또 다른 방법 */
    .css-1rs6os .css-17eq0hr:first-child {
        display: none !important;
    }
    
    /* 사이드바 네비게이션에서 첫 번째 링크 숨기기 */
    .css-1rs6os a[href="/"]:first-child {
        display: none !important;
    }
    
    /* 최신 Streamlit 버전용 */
    [data-testid="stSidebarNav"] > ul > li:first-child {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 페이지 상단 앵커 포인트
st.markdown('<div id="top"></div>', unsafe_allow_html=True)

st.title("🎯 면접운영스케줄링")
st.markdown("""
**올인원 면접 스케줄링 솔루션**  
이 페이지에서 면접 스케줄링에 필요한 모든 설정과 일정 생성을 한 번에 진행할 수 있습니다.
운영일정 추정을 먼저 확인한 후, 필요한 설정들을 순차적으로 진행해보세요.
""")

# 세션 상태 초기화
def init_session_states():
    # 기본 활동 템플릿
    default_activities = pd.DataFrame({
        "use": [True, True, True, True],
        "activity": ["면접1", "면접2", "인성검사", "커피챗"],
        "mode": ["individual"] * 4,
        "duration_min": [10] * 4,
        "room_type": ["면접1실", "면접2실", "인성검사실", "커피챗실"],
        "min_cap": [1] * 4,
        "max_cap": [1] * 4,
    })
    st.session_state.setdefault("activities", default_activities)
    
    # 스마트 직무 매핑 (모든 기본 활동 활성화 + 충분한 인원수)
    if "job_acts_map" not in st.session_state:
        act_list = default_activities.query("use == True")["activity"].tolist()
        job_data = {"code": ["JOB01"], "count": [20]}  # 기본 20명으로 설정
        for act in act_list:
            job_data[act] = True
        st.session_state["job_acts_map"] = pd.DataFrame(job_data)
    
    # 기본 선후행 제약 (인성검사 첫 번째, 커피챗 마지막)
    default_precedence = pd.DataFrame([
        {"predecessor": "__START__", "successor": "인성검사", "gap_min": 0, "adjacent": False},  # 인성검사가 가장 먼저
        {"predecessor": "커피챗", "successor": "__END__", "gap_min": 0, "adjacent": False}     # 커피챗이 가장 마지막
    ])
    st.session_state.setdefault("precedence", default_precedence)
    
    # 기본 운영 시간
    st.session_state.setdefault("oper_start_time", time(9, 0))
    st.session_state.setdefault("oper_end_time", time(18, 0))
    
    # 스마트 방 템플릿 (기본 활동에 맞춰 자동 생성)
    if "room_template" not in st.session_state:
        room_template = {}
        for _, row in default_activities.iterrows():
            if row["use"] and row["room_type"]:
                room_template[row["room_type"]] = {
                    "count": 3,  # 기본 3개 방으로 충분한 용량 확보
                    "cap": row["max_cap"]
                }
        st.session_state["room_template"] = room_template
    
    # 스마트 운영 공간 계획 (room_template 기반으로 자동 생성)
    if "room_plan" not in st.session_state:
        room_template = st.session_state.get("room_template", {})
        if room_template:
            final_plan_dict = {}
            for rt, values in room_template.items():
                final_plan_dict[f"{rt}_count"] = values['count']
                final_plan_dict[f"{rt}_cap"] = values['cap']
            st.session_state["room_plan"] = pd.DataFrame([final_plan_dict])
        else:
            st.session_state["room_plan"] = pd.DataFrame()
    
    # 스마트 운영 시간 (자동 생성)
    if "oper_window" not in st.session_state:
        t_start = st.session_state["oper_start_time"]
        t_end = st.session_state["oper_end_time"]
        oper_window_dict = {
            "start_time": t_start.strftime("%H:%M"),
            "end_time": t_end.strftime("%H:%M")
        }
        st.session_state["oper_window"] = pd.DataFrame([oper_window_dict])
    
    # 시뮬레이션 결과
    st.session_state.setdefault('final_schedule', None)
    st.session_state.setdefault('last_solve_logs', "")
    st.session_state.setdefault('solver_status', "미실행")
    st.session_state.setdefault('daily_limit', 0)

init_session_states()

# =============================================================================
# 섹션 0: 운영일정 추정 (메인 섹션)
# =============================================================================
st.header("🚀 운영일정 추정")
st.markdown("현재 설정을 바탕으로 최적의 운영일정을 추정합니다.")

# 첫 방문자를 위한 안내
if st.session_state.get('solver_status', '미실행') == '미실행':
    st.info("👋 **처음 방문하셨나요?** 바로 아래 '운영일정추정 시작' 버튼을 눌러보세요! 기본 설정으로 데모를 체험할 수 있습니다.")
    st.markdown("💡 **팁:** 추정 후 아래 섹션들에서 세부 설정을 조정하여 더 정확한 결과를 얻을 수 있습니다.")

# Excel 출력 함수
def df_to_excel(df: pd.DataFrame, stream=None) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = 'Schedule'
    df = df.copy()
    
    PALETTE = ['E3F2FD', 'FFF3E0', 'E8F5E9', 'FCE4EC', 'E1F5FE', 'F3E5F5', 'FFFDE7', 'E0F2F1', 'EFEBE9', 'ECEFF1']
    
    # 날짜별로 색상 지정
    unique_dates = df['interview_date'].dt.date.unique()
    date_color_map = {date: PALETTE[i % len(PALETTE)] for i, date in enumerate(unique_dates)}
    
    df = df.astype(object).where(pd.notna(df), None)
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)
    
    header_fill = PatternFill('solid', fgColor='D9D9D9')
    for cell in ws[1]:
        cell.fill = header_fill
    
    # 날짜 열 찾기
    date_col_idx = -1
    for j, col_name in enumerate(df.columns, 1):
        if col_name == 'interview_date':
            date_col_idx = j
            break
    
    for i, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), 2):
        if date_col_idx != -1:
            date_val = row[date_col_idx - 1].value
            if date_val and hasattr(date_val, 'date'):
                row_color = date_color_map.get(date_val.date())
                if row_color:
                    row_fill = PatternFill('solid', fgColor=row_color)
                    for cell in row:
                        cell.fill = row_fill
    
    # 시간 형식 지정
    for j, col_name in enumerate(df.columns, 1):
        if 'start' in col_name or 'end' in col_name:
            for i in range(2, ws.max_row + 1):
                ws.cell(i, j).number_format = 'hh:mm'
    
    wb.save(stream or "recommended_schedule.xlsx")

def reset_run_state():
    st.session_state['final_schedule'] = None
    st.session_state['last_solve_logs'] = ""
    st.session_state['solver_status'] = "미실행"
    st.session_state['daily_limit'] = 0

# 사이드바 파라미터
with st.sidebar:
    st.markdown("## 파라미터")
    debug_mode = st.checkbox("🐞 디버그 모드", value=False)
    param_grid = load_param_grid()
    
    if not param_grid.empty:
        scenario_options = param_grid['scenario_id'].tolist()
        selected_scenario_id = st.selectbox(
            "시나리오 선택",
            options=scenario_options,
            index=0,
            help="파라미터 시나리오를 선택합니다."
        )
        params = param_grid[param_grid['scenario_id'] == selected_scenario_id].iloc[0].to_dict()
    else:
        st.warning("파라미터 파일을 찾을 수 없습니다.")
        params = {}

# 데이터 검증
acts_df = st.session_state.get("activities", pd.DataFrame())
job_df = st.session_state.get("job_acts_map", pd.DataFrame())
room_plan = st.session_state.get("room_plan", pd.DataFrame())
oper_df = st.session_state.get("oper_window", pd.DataFrame())
prec_df = st.session_state.get("precedence", pd.DataFrame())

# 검증 결과 표시
validation_errors = []

if acts_df.empty or not (acts_df["use"] == True).any():
    validation_errors.append("활동을 하나 이상 정의하고 'use=True'로 설정해주세요.")

if job_df.empty or (job_df["count"].sum() == 0):
    validation_errors.append("직무 코드를 추가하고 인원수를 1명 이상 입력해주세요.")

if job_df["code"].duplicated().any():
    validation_errors.append("중복된 직무 코드가 있습니다.")

# room_plan 검증: room_template이 있으면 유효한 것으로 간주
room_template = st.session_state.get("room_template", {})
if room_plan.empty and not room_template:
    validation_errors.append("운영 공간을 설정해주세요.")

if validation_errors:
    st.error("다음 항목을 설정해주세요:")
    for error in validation_errors:
        st.error(f"• {error}")
    st.info("⬇️ 아래 섹션들에서 필요한 설정을 완료한 후 다시 추정해보세요.")
else:
    st.success("✅ 입력 데이터 검증 통과 – 운영일정추정을 시작할 수 있습니다!")

# 운영일정 추정 실행
if st.button("🚀 운영일정추정 시작", type="primary", use_container_width=True, on_click=reset_run_state):
    if not validation_errors:
        with st.spinner("최적의 운영 일정을 계산 중입니다..."):
            try:
                cfg = core.build_config(st.session_state)
                status, final_wide, logs, limit = solve_for_days(cfg, params, debug=debug_mode)
                
                st.session_state['last_solve_logs'] = logs
                st.session_state['solver_status'] = status
                st.session_state['daily_limit'] = limit
                
                if status == "OK" and final_wide is not None and not final_wide.empty:
                    st.session_state['final_schedule'] = final_wide
                    st.balloons()
                else:
                    st.session_state['final_schedule'] = None
            except Exception as e:
                st.error(f"계산 중 오류가 발생했습니다: {str(e)}")
                st.session_state['solver_status'] = "ERROR"

# 결과 표시
st.markdown("---")
status = st.session_state.get('solver_status', '미실행')
daily_limit = st.session_state.get('daily_limit', 0)

col1, col2 = st.columns(2)
with col1:
    st.info(f"Solver Status: `{status}`")
with col2:
    if daily_limit > 0:
        st.info(f"계산된 일일 최대 처리 인원: **{daily_limit}명**")

if "솔버 시간 초과" in st.session_state.get('last_solve_logs', ''):
    st.warning("⚠️ 연산 시간이 1분(60초)을 초과하여, 현재까지 찾은 최적의 스케줄을 반환했습니다. 결과는 최상이 아닐 수 있습니다.")

# 결과 출력
final_schedule = st.session_state.get('final_schedule')
if final_schedule is not None and not final_schedule.empty:
    st.success("🎉 운영일정 추정이 완료되었습니다!")
    
    # 요약 정보
    total_candidates = len(final_schedule)
    total_days = final_schedule['interview_date'].nunique()
    st.info(f"총 {total_candidates}명의 지원자를 {total_days}일에 걸쳐 면접 진행")
    
    # 결과 테이블
    st.subheader("📋 상세 일정표")
    st.dataframe(final_schedule, use_container_width=True)
    
    # Excel 다운로드
    excel_buffer = BytesIO()
    df_to_excel(final_schedule, excel_buffer)
    excel_data = excel_buffer.getvalue()
    
    st.download_button(
        label="📊 Excel 파일 다운로드",
        data=excel_data,
        file_name=f"interview_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

elif status == "MAX_DAYS_EXCEEDED":
    st.error("❌ 설정된 최대 날짜 내에서 모든 지원자를 배정할 수 없습니다. 조건을 조정해주세요.")
elif status == "INFEASIBLE":
    st.error("❌ 현재 설정으로는 일정을 생성할 수 없습니다. 제약 조건을 확인해주세요.")
elif status == "ERROR":
    st.error("❌ 계산 중 오류가 발생했습니다.")

# 로그 표시
if st.session_state.get('last_solve_logs'):
    with st.expander("🔍 상세 로그 보기"):
        st.text(st.session_state['last_solve_logs'])

st.divider()

# =============================================================================
# 섹션 1: 면접 활동 정의
# =============================================================================
col_header, col_refresh = st.columns([4, 1])
with col_header:
    st.header("1️⃣ 면접 활동 정의")
with col_refresh:
    if st.button("🔄", key="refresh_activities", help="이 섹션 새로고침"):
        st.rerun()

st.markdown("면접에서 진행할 활동들을 정의하고 각 활동의 속성을 설정합니다.")

# 기본 템플릿 함수
def default_df() -> pd.DataFrame:
    return pd.DataFrame({
        "use": [True, True, True, True],
        "activity": ["면접1", "면접2", "인성검사", "커피챗"],
        "mode": ["individual"] * 4,
        "duration_min": [10] * 4,
        "room_type": ["면접1실", "면접2실", "인성검사실", "커피챗실"],
        "min_cap": [1] * 4,
        "max_cap": [1] * 4,
    })

df = st.session_state["activities"].copy()

# 누락 컬럼 보강
for col, default_val in {
    "use": True,
    "mode": "individual",
    "duration_min": 10,
    "room_type": "",
    "min_cap": 1,
    "max_cap": 1,
}.items():
    if col not in df.columns:
        df[col] = default_val

# AG-Grid 설정
gb = GridOptionsBuilder.from_dataframe(df)

gb.configure_column(
    "use",
    header_name="사용",
    cellEditor="agCheckboxCellEditor",
    cellRenderer="agCheckboxCellRenderer",
    editable=True,
    singleClickEdit=True,
    width=80,
)

gb.configure_column("activity", header_name="활동 이름", editable=True)

mode_values = ["individual"]
gb.configure_column(
    "mode",
    header_name="모드",
    editable=True,
    cellEditor="agSelectCellEditor",
    cellEditorParams={"values": mode_values},
    width=110,
)

for col, hdr in [("duration_min", "소요시간(분)"), ("min_cap", "최소 인원"), ("max_cap", "최대 인원")]:
    gb.configure_column(
        col,
        header_name=hdr,
        editable=True,
        type=["numericColumn", "numberColumnFilter"],
        width=120,
    )

gb.configure_column("room_type", header_name="방 종류", editable=True)

grid_opts = gb.build()

st.markdown("#### 활동 정의")

grid_ret = AgGrid(
    df,
    gridOptions=grid_opts,
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    theme="balham",
    key="activities_grid",
)

st.session_state["activities"] = grid_ret["data"]

# 행 추가/삭제 기능
col_add, col_del = st.columns(2)

with col_add:
    if st.button("➕ 활동 행 추가", key="add_activity"):
        new_row = {
            "use": True,
            "activity": "NEW_ACT",
            "mode": "individual",
            "duration_min": 10,
            "room_type": "",
            "min_cap": 1,
            "max_cap": 1,
        }
        st.session_state["activities"] = pd.concat(
            [st.session_state["activities"], pd.DataFrame([new_row])],
            ignore_index=True,
        )
        st.rerun()

with col_del:
    act_df = st.session_state["activities"].copy()
    if not act_df.empty:
        # 인덱스와 활동명을 안전하게 결합
        delete_options = []
        valid_indices = []
        for idx, row in act_df.iterrows():
            activity_name = str(row.get('activity', 'Unknown'))
            if activity_name and activity_name != 'nan':
                delete_options.append(f"{idx}: {activity_name}")
                valid_indices.append(idx)
        
        to_delete = st.multiselect(
            "삭제할 활동 선택",
            options=delete_options,
            key="del_activity_select"
        )
        if st.button("❌ 선택된 활동 삭제", key="del_activity"):
            if to_delete:
                # 선택된 인덱스 추출
                selected_indices = [int(s.split(":")[0]) for s in to_delete]
                
                # 실제 DataFrame에 존재하는 인덱스만 필터링
                valid_to_drop = [idx for idx in selected_indices if idx in act_df.index]
                
                if valid_to_drop:
                    kept = st.session_state["activities"].drop(valid_to_drop).reset_index(drop=True)
                    st.session_state["activities"] = kept
                    st.success(f"선택된 {len(valid_to_drop)}개 활동이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.error("삭제할 유효한 활동이 없습니다.")
    else:
        st.info("삭제할 활동이 없습니다.")

st.divider()

# =============================================================================
# 섹션 2: 선후행 제약 설정 (면접 활동 정의 바로 다음으로 이동)
# =============================================================================
col_header, col_refresh = st.columns([4, 1])
with col_header:
    st.header("2️⃣ 선후행 제약 설정")
with col_refresh:
    if st.button("🔄", key="refresh_precedence", help="이 섹션 새로고침"):
        st.rerun()

st.markdown("면접 활동 간의 순서 제약과 시간 간격을 설정합니다.")

# 공통 데이터 로드
acts_df = st.session_state.get("activities", pd.DataFrame())
jobs_df = st.session_state.get("job_acts_map", pd.DataFrame())

if not acts_df.empty:
    ACT_OPTS = acts_df.query("use == True")["activity"].tolist()
    
    # precedence 규칙 초기화 (빈 문자열도 허용)
    prec_df = st.session_state["precedence"].copy()
    valid_acts = set(ACT_OPTS) | {"__START__", "__END__", ""}
    prec_df = prec_df[prec_df["predecessor"].isin(valid_acts) & prec_df["successor"].isin(valid_acts)]
    st.session_state["precedence"] = prec_df
    
    # 동선 미리보기 함수
    def generate_flow_preview():
        """현재 선후행 제약 규칙을 바탕으로 가능한 동선을 시각화"""
        prec_rules = st.session_state["precedence"].copy()
        if prec_rules.empty:
            return "📋 설정된 제약 규칙이 없습니다. 모든 활동이 자유롭게 배치 가능합니다."
        
        # START와 END 규칙 분리
        start_rules = prec_rules[prec_rules["predecessor"] == "__START__"]
        end_rules = prec_rules[prec_rules["successor"] == "__END__"]
        middle_rules = prec_rules[
            (~prec_rules["predecessor"].isin(["__START__", "__END__"])) &
            (~prec_rules["successor"].isin(["__START__", "__END__"]))
        ]
        
        flow_text = "🔄 **예상 면접 동선:**\n\n"
        
        # START 규칙이 있는 경우
        if not start_rules.empty:
            first_acts = start_rules["successor"].tolist()
            flow_text += f"**시작:** 🏁 → {' / '.join(first_acts)}\n\n"
        else:
            flow_text += "**시작:** 🏁 → (모든 활동 가능)\n\n"
        
        # 중간 규칙들
        if not middle_rules.empty:
            flow_text += "**중간 연결:**\n"
            for _, rule in middle_rules.iterrows():
                gap_info = f" ({rule['gap_min']}분 간격)" if rule['gap_min'] > 0 else ""
                adj_info = " [인접]" if rule['adjacent'] else ""
                flow_text += f"• {rule['predecessor']} → {rule['successor']}{gap_info}{adj_info}\n"
            flow_text += "\n"
        
        # END 규칙이 있는 경우
        if not end_rules.empty:
            last_acts = end_rules["predecessor"].tolist()
            flow_text += f"**종료:** {' / '.join(last_acts)} → 🏁"
        else:
            flow_text += "**종료:** (모든 활동 가능) → 🏁"
        
        return flow_text
    
    # 가능한 모든 활동 순서 계산 함수 (과거 코드 복원)
    def render_dynamic_flows(prec_df: pd.DataFrame, base_nodes: list[str]) -> list[str]:
        """
        prec_df: ['predecessor','successor','gap_min','adjacent']
        base_nodes: 순서에 포함될 활동 리스트
        """
        import itertools
        
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
                    # 붙이기(adjacent) 또는 gap>0 모두 "인접" 처리
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
    
    # 실시간 동선(활동 순서) 미리보기
    with st.expander("🔍 실시간 동선(활동 순서) 미리보기", expanded=True):
        prec_df_latest = st.session_state["precedence"]
        
        # 기본 규칙 표시
        st.markdown("**📋 현재 설정된 선후행 제약 규칙:**")
        if prec_df_latest.empty:
            st.info("설정된 제약 규칙이 없습니다. 모든 활동이 자유롭게 배치 가능합니다.")
        else:
            # 규칙을 사용자 친화적으로 표시
            for _, rule in prec_df_latest.iterrows():
                pred = rule['predecessor']
                succ = rule['successor']
                gap = rule['gap_min']
                adj = rule['adjacent']
                
                # 표시 형식 개선
                if pred == "__START__":
                    pred_display = "🏁 시작"
                elif pred == "":
                    pred_display = "🏁 시작"
                else:
                    pred_display = f"📝 {pred}"
                
                if succ == "__END__":
                    succ_display = "🏁 종료"
                elif succ == "":
                    succ_display = "🏁 종료"
                else:
                    succ_display = f"📝 {succ}"
                
                gap_info = f" ({gap}분 간격)" if gap > 0 else ""
                adj_info = " [인접 배치]" if adj else ""
                
                st.markdown(f"• {pred_display} → {succ_display}{gap_info}{adj_info}")
        
        st.markdown("---")
        
        # 가능한 활동 순서 계산 및 표시
        if ACT_OPTS:
            flows = render_dynamic_flows(prec_df_latest, ACT_OPTS)
            if not flows:
                st.warning("⚠️ 현재 제약을 만족하는 활동 순서가 없습니다. 제약 조건을 확인해주세요.")
            else:
                st.markdown("**🔄 가능한 모든 활동 순서:**")
                for i, f in enumerate(flows, 1):
                    st.markdown(f"{i}. {f}")
                
                if len(flows) == 1:
                    st.success("✅ 제약 조건에 따라 활동 순서가 고유하게 결정됩니다!")
                else:
                    st.info(f"💡 총 {len(flows)}가지 가능한 활동 순서가 있습니다.")
        else:
            st.warning("활성화된 활동이 없습니다. 먼저 활동을 정의해주세요.")
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════
    # 🎯 면접 순서 설정 (단계별 가이드)
    # ═══════════════════════════════════════════
    st.subheader("🎯 면접 순서 설정")
    st.markdown("면접 활동들의 순서를 설정합니다. 아래 단계를 따라 진행하세요.")
    
    # 현재 설정된 START/END 규칙 확인
    current_start = None
    current_end = None
    for _, rule in prec_df.iterrows():
        if rule['predecessor'] == "__START__":
            current_start = rule['successor']
        if rule['successor'] == "__END__":
            current_end = rule['predecessor']
    
    # ═══════════════════════════════════════════
    # 1단계: 시작/끝 활동 지정
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown("#### 1️⃣ 시작과 끝 활동 지정")
        st.markdown("💡 **면접의 첫 번째와 마지막 활동을 지정하세요.** (선택사항)")
        
        col1, col2 = st.columns(2)
        
        # 현재 값을 기본값으로 설정
        start_idx = 0
        end_idx = 0
        if current_start and current_start in ACT_OPTS:
            start_idx = ACT_OPTS.index(current_start) + 1
        if current_end and current_end in ACT_OPTS:
            end_idx = ACT_OPTS.index(current_end) + 1
        
        first = col1.selectbox(
            "🏁 가장 먼저 할 활동", 
            ["(지정 안 함)"] + ACT_OPTS, 
            index=start_idx, 
            key="first_act",
            help="면접 프로세스의 첫 번째 활동을 선택하세요"
        )
        last = col2.selectbox(
            "🏁 가장 마지막 활동", 
            ["(지정 안 함)"] + ACT_OPTS, 
            index=end_idx, 
            key="last_act",
            help="면접 프로세스의 마지막 활동을 선택하세요"
        )
        
        if st.button("✅ 시작/끝 활동 적용", key="btn_add_start_end", type="primary"):
            # 기존 __START__/__END__ 관련 행 제거
            tmp = prec_df[
                (~prec_df["predecessor"].isin(["__START__", "__END__"])) &
                (~prec_df["successor"].isin(["__START__", "__END__"]))
            ].copy()
            
            rows = []
            if first != "(지정 안 함)":
                rows.append({"predecessor": "__START__", "successor": first, "gap_min": 0, "adjacent": True})
            if last != "(지정 안 함)":
                rows.append({"predecessor": last, "successor": "__END__", "gap_min": 0, "adjacent": True})
            
            st.session_state["precedence"] = pd.concat([tmp, pd.DataFrame(rows)], ignore_index=True)
            st.success("✅ 시작/끝 활동이 설정되었습니다!")
            st.rerun()
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════
    # 2단계: 활동 순서 연결
    # ═══════════════════════════════════════════
    with st.container():
        st.markdown("#### 2️⃣ 활동 순서 연결")
        st.markdown("💡 **특정 활동 다음에 반드시 와야 하는 활동을 연결하세요.** (선택사항)")
        st.markdown("📝 **예시:** 면접1 → 면접2 (면접1 후에 반드시 면접2가 와야 함)")
        
        with st.form("form_add_rule"):
            st.markdown("##### 새 순서 규칙 추가")
            
            col_form1, col_form2 = st.columns(2)
            p = col_form1.selectbox("🔸 먼저 할 활동", ACT_OPTS, key="pred_select", help="선행 활동을 선택하세요")
            s = col_form2.selectbox("🔹 다음에 할 활동", ACT_OPTS, key="succ_select", help="후행 활동을 선택하세요")
            
            # 고급 옵션을 expander로 숨김
            with st.expander("⚙️ 고급 옵션 (기본값 사용 권장)", expanded=False):
                col_gap, col_adj = st.columns(2)
                g = col_gap.number_input("⏱️ 최소 간격 (분)", 0, 60, 5, key="gap_input", help="두 활동 사이의 최소 시간 간격")
                adj = col_adj.checkbox("📌 연속 배치 (붙여서 진행)", value=True, key="adj_checkbox", help="두 활동을 시간적으로 연속해서 배치")
            
            ok = st.form_submit_button("➕ 순서 규칙 추가", use_container_width=True, type="primary")
            
            if ok:
                df = st.session_state["precedence"]
                dup = ((df["predecessor"] == p) & (df["successor"] == s)).any()
                if p == s:
                    st.error("❌ 같은 활동끼리는 연결할 수 없습니다.")
                elif dup:
                    st.warning("⚠️ 이미 존재하는 규칙입니다.")
                else:
                    st.session_state["precedence"] = pd.concat(
                        [df, pd.DataFrame([{"predecessor": p, "successor": s, "gap_min": g, "adjacent": adj}])],
                        ignore_index=True
                    )
                    st.success(f"✅ 규칙 추가: {p} → {s}")
                    st.rerun()
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════
    # 규칙 삭제 - 직접 접근 가능
    # ═══════════════════════════════════════════
    st.subheader("🗑️ 설정된 규칙 삭제")
    
    prec_df = st.session_state["precedence"].copy()
    if not prec_df.empty:
        st.markdown("**현재 설정된 규칙들:**")
        
        # 규칙을 보기 좋게 표시
        prec_df["규칙표시용"] = prec_df.apply(
            lambda r: f"{r.predecessor} → {r.successor}" + 
                     (f" (간격: {r.gap_min}분)" if r.gap_min > 0 else "") +
                     (" [연속배치]" if r.adjacent else ""), axis=1
        )
        
        # START/END 규칙과 일반 규칙 분리해서 표시
        start_end_rules = prec_df[
            (prec_df["predecessor"] == "__START__") | (prec_df["successor"] == "__END__")
        ]
        normal_rules = prec_df[
            (~prec_df["predecessor"].isin(["__START__", "__END__"])) &
            (~prec_df["successor"].isin(["__START__", "__END__"]))
        ]
        
        if not start_end_rules.empty:
            st.markdown("**🏁 시작/끝 규칙:**")
            for rule in start_end_rules["규칙표시용"]:
                st.markdown(f"• {rule}")
        
        if not normal_rules.empty:
            st.markdown("**🔗 순서 연결 규칙:**")
            for rule in normal_rules["규칙표시용"]:
                st.markdown(f"• {rule}")
        
        # 삭제 기능
        delete_options = prec_df["규칙표시용"].tolist()
        
        to_delete = st.multiselect(
            "🗑️ 삭제할 규칙을 선택하세요",
            options=delete_options,
            key="del_prec_select",
            help="여러 규칙을 한 번에 선택하여 삭제할 수 있습니다"
        )
        
        col_del, col_clear = st.columns(2)
        
        with col_del:
            if st.button("❌ 선택된 규칙 삭제", key="del_prec", disabled=not to_delete):
                if to_delete:
                    new_prec = prec_df[~prec_df["규칙표시용"].isin(to_delete)].drop(
                        columns="규칙표시용"
                    ).reset_index(drop=True)
                    st.session_state["precedence"] = new_prec.copy()
                    st.success(f"✅ {len(to_delete)}개 규칙이 삭제되었습니다!")
                    st.rerun()
        
        with col_clear:
            if st.button("🗑️ 모든 규칙 삭제", key="clear_all_prec", type="secondary"):
                st.session_state["precedence"] = pd.DataFrame(columns=["predecessor", "successor", "gap_min", "adjacent"])
                st.success("✅ 모든 규칙이 삭제되었습니다!")
                st.rerun()
    else:
        st.info("📋 설정된 선후행 제약 규칙이 없습니다. 위에서 규칙을 추가해보세요.")

st.divider()

# =============================================================================
# 섹션 3: 직무별 면접활동 정의 (선후행 제약 설정 다음으로 이동)
# =============================================================================
col_header, col_refresh = st.columns([4, 1])
with col_header:
    st.header("3️⃣ 직무별 면접활동 정의")
with col_refresh:
    if st.button("🔄", key="refresh_job_activities", help="이 섹션 새로고침"):
        st.rerun()

st.markdown("각 직무 코드별로 어떤 면접활동을 진행할지 설정하고 인원수를 지정합니다.")

# 활동 목록 확보
acts_df = st.session_state.get("activities")
if acts_df is None or acts_df.empty:
    st.error("먼저 면접활동을 정의해주세요.")
else:
    act_list = acts_df.query("use == True")["activity"].tolist()
    
    if not act_list:
        st.error("활동을 최소 1개 '사용'으로 체크해야 합니다.")
    else:
        # 직무 매핑 데이터 로드
        if "job_acts_map" in st.session_state:
            job_df = st.session_state["job_acts_map"].copy()
        else:
            job_df = pd.DataFrame({"code": ["JOB01"], "count": [1]})
        
        # 컬럼 동기화
        for act in act_list:
            if act not in job_df.columns:
                job_df[act] = True
        
        if "count" not in job_df.columns:
            job_df["count"] = 1
        
        # 열 순서 정리
        cols = ["code", "count"] + act_list
        job_df = job_df.reindex(columns=cols, fill_value=True)
        
        st.session_state["job_acts_map"] = job_df
        
        # 행 추가/삭제 기능
        col_add2, col_del2 = st.columns(2)
        
        with col_add2:
            if st.button("➕ 직무 코드 행 추가", key="add_job"):
                current = st.session_state["job_acts_map"].copy()
                
                # 새 코드 자동 생성
                pattern = re.compile(r"^([A-Za-z]+)(\d+)$")
                prefixes, numbers = [], []
                for c in current["code"]:
                    m = pattern.match(str(c))
                    if m:
                        prefixes.append(m.group(1))
                        numbers.append(int(m.group(2)))
                
                if prefixes:
                    pref = pd.Series(prefixes).mode()[0]
                    max_num = max(n for p, n in zip(prefixes, numbers) if p == pref)
                    next_num = max_num + 1
                else:
                    pref, next_num = "JOB", 1
                
                new_code = f"{pref}{next_num:02d}"
                new_row = {"code": new_code, "count": 1, **{act: True for act in act_list}}
                
                current = pd.concat([current, pd.DataFrame([new_row])], ignore_index=True)
                st.session_state["job_acts_map"] = current
                st.success(f"'{new_code}' 행이 추가되었습니다.")
                st.rerun()
        
        with col_del2:
            codes = job_df["code"].tolist()
            to_delete2 = st.multiselect(
                "삭제할 코드 선택", 
                options=codes, 
                key="del_job_select"
            )
            
            if st.button("❌ 선택 코드 삭제", key="del_job"):
                if to_delete2:
                    kept = job_df[~job_df["code"].isin(to_delete2)].reset_index(drop=True)
                    st.session_state["job_acts_map"] = kept
                    st.success("삭제 완료!")
                    st.rerun()
        
        # 편집용 AG-Grid
        df_to_display = st.session_state["job_acts_map"].copy()
        
        gb2 = GridOptionsBuilder.from_dataframe(df_to_display)
        gb2.configure_selection(selection_mode="none")
        gb2.configure_default_column(resizable=True, editable=True)
        
        gb2.configure_column("code", header_name="직무 코드", width=120, editable=True)
        gb2.configure_column(
            "count", header_name="인원수", type=["numericColumn"], width=90, editable=True
        )
        
        for act in act_list:
            gb2.configure_column(
                act,
                header_name=act,
                cellRenderer="agCheckboxCellRenderer",
                cellEditor="agCheckboxCellEditor",
                editable=True,
                singleClickEdit=True,
                width=110,
            )
        
        grid_opts2 = gb2.build()
        
        grid_ret2 = AgGrid(
            df_to_display,
            gridOptions=grid_opts2,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            data_return_mode=DataReturnMode.AS_INPUT,
            fit_columns_on_grid_load=True,
            theme="balham",
            key="job_grid_display",
        )
        
        edited_df = pd.DataFrame(grid_ret2["data"])
        
        # 데이터 검증
        def validate_job_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
            msgs: list[str] = []
            df = df.copy()
            df["code"] = df["code"].astype(str).str.strip()
            df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
            
            # 빈 코드
            if (df["code"] == "").any():
                msgs.append("빈 코드가 있습니다.")
                df = df[df["code"] != ""].reset_index(drop=True)
            
            # 중복 코드
            dup_codes = df[df["code"].duplicated()]["code"].unique().tolist()
            if dup_codes:
                msgs.append(f"중복 코드: {', '.join(dup_codes)}")
            
            # count ≤ 0
            zero_cnt = df[df["count"] <= 0]["code"].tolist()
            if zero_cnt:
                msgs.append(f"0 이하 인원수: {', '.join(map(str, zero_cnt))}")
            
            # 활동이 하나도 선택되지 않은 행
            no_act = [
                row.code
                for row in df.itertuples()
                if not any(getattr(row, a) for a in act_list)
            ]
            if no_act:
                msgs.append(f"모든 활동이 False인 코드: {', '.join(no_act)}")
            
            return df, msgs
        
        clean_df, errors = validate_job_data(edited_df)
        
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            st.success("모든 입력이 유효합니다!")
        
        st.info(f"총 인원수: **{clean_df['count'].sum()}** 명")
        st.session_state["job_acts_map"] = clean_df

st.divider()

# =============================================================================
# 섹션 4: 운영 공간 설정
# =============================================================================
col_header, col_refresh = st.columns([4, 1])
with col_header:
    st.header("4️⃣ 운영 공간 설정")
with col_refresh:
    if st.button("🔄", key="refresh_room_settings", help="이 섹션 새로고침"):
        st.rerun()

st.markdown("면접을 운영할 경우, 하루에 동원 가능한 모든 공간의 종류와 수, 그리고 최대 수용 인원을 설정합니다.")

# 활동 DF에서 room_types 확보
acts_df = st.session_state.get("activities")
if acts_df is not None and not acts_df.empty:
    room_types = sorted(
        acts_df.query("use == True and room_type != '' and room_type.notna()")["room_type"].unique()
    )
    
    if room_types:
        min_cap_req = acts_df.set_index("room_type")["min_cap"].to_dict()
        max_cap_req = acts_df.set_index("room_type")["max_cap"].to_dict()
        
        # 공간 템플릿 설정
        tpl_dict = st.session_state.get("room_template", {})
        
        # room_types 동기화
        for rt in room_types:
            tpl_dict.setdefault(rt, {"count": 1, "cap": max_cap_req.get(rt, 1)})
        for rt in list(tpl_dict):
            if rt not in room_types:
                tpl_dict.pop(rt)
        
        st.subheader("하루 기준 운영 공간 설정")
        
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
                current_val = tpl_dict[rt].get("cap", max_val)
                safe_val = max(min_val, min(current_val, max_val))
                
                tpl_dict[rt]["cap"] = st.number_input(
                    f"{rt} 최대 동시 수용 인원",
                    min_value=min_val,
                    max_value=max_val,
                    value=safe_val,
                    key=f"tpl_{rt}_cap",
                )
        
        # 변경된 템플릿 정보를 세션에 저장
        st.session_state['room_template'] = tpl_dict
        
        # room_plan 생성 및 저장
        final_plan_dict = {}
        for rt, values in tpl_dict.items():
            final_plan_dict[f"{rt}_count"] = values['count']
            final_plan_dict[f"{rt}_cap"] = values['cap']
        
        st.session_state['room_plan'] = pd.DataFrame([final_plan_dict])
        
        with st.expander("🗂 저장된 room_plan 데이터 미리보기"):
            st.dataframe(st.session_state.get('room_plan', pd.DataFrame()), use_container_width=True)
    else:
        st.error("사용(use=True)하도록 설정된 활동 중, 'room_type'이 지정된 활동이 없습니다.")

st.divider()

# =============================================================================
# 섹션 5: 운영 시간 설정
# =============================================================================
col_header, col_refresh = st.columns([4, 1])
with col_header:
    st.header("5️⃣ 운영 시간 설정")
with col_refresh:
    if st.button("🔄", key="refresh_time_settings", help="이 섹션 새로고침"):
        st.rerun()

st.markdown("면접을 운영할 경우의 하루 기준 운영 시작 및 종료 시간을 설정합니다.")

# 기존 값 불러오기
init_start = st.session_state.get("oper_start_time", time(9, 0))
init_end = st.session_state.get("oper_end_time", time(18, 0))

st.subheader("하루 기준 공통 운영 시간")

col_start, col_end = st.columns(2)

with col_start:
    t_start = st.time_input("운영 시작 시간", value=init_start, key="oper_start")

with col_end:
    t_end = st.time_input("운영 종료 시간", value=init_end, key="oper_end")

if t_start >= t_end:
    st.error("오류: 운영 시작 시간은 종료 시간보다 빨라야 합니다.")
else:
    # 설정된 시간을 세션 상태에 저장
    st.session_state["oper_start_time"] = t_start
    st.session_state["oper_end_time"] = t_end
    
    # oper_window DataFrame 생성 및 저장
    oper_window_dict = {
        "start_time": t_start.strftime("%H:%M"),
        "end_time": t_end.strftime("%H:%M")
    }
    st.session_state['oper_window'] = pd.DataFrame([oper_window_dict])
    
    with st.expander("🗂 저장된 oper_window 데이터 미리보기"):
        st.dataframe(st.session_state.get('oper_window', pd.DataFrame()), use_container_width=True)
    
    st.success(f"운영 시간이 {t_start.strftime('%H:%M')}부터 {t_end.strftime('%H:%M')}까지로 설정되었습니다.")

st.divider()

# 위로 가기 기능
st.markdown("---")

# 중앙 링크 방식
st.markdown("""
<div style="text-align: center; margin: 20px 0;">
    <a href="#top" style="
        display: inline-block;
        background: linear-gradient(90deg, #ff6b6b, #4ecdc4);
        color: white;
        text-decoration: none;
        padding: 12px 24px;
        border-radius: 25px;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    ">
        ⬆️ 빠른 이동: 맨 위로
    </a>
</div>
""", unsafe_allow_html=True)

# 우하단 고정 버튼 (개선된 버전)
st.markdown("""
<style>
    .floating-top-button {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 999;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        font-size: 20px;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
    }
    
    .floating-top-button:hover {
        transform: translateY(-3px) scale(1.1);
        box-shadow: 0 6px 25px rgba(0,0,0,0.4);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    .floating-top-button:active {
        transform: translateY(-1px) scale(1.05);
    }
</style>

<a href="#top" class="floating-top-button" title="맨 위로 이동">
    ⬆️
</a>
""", unsafe_allow_html=True)

# 현재 세션 내용을 파일로 자동 저장
cp.autosave_state()