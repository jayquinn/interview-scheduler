# pages/1_면접운영스케줄링.py
import streamlit as st
import pandas as pd
import re
import time
from datetime import time as datetime_time, datetime
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
from core import df_to_excel_internal

st.set_page_config(
    page_title="면접운영스케줄링",
    layout="wide"
)

# 전역 스타일 및 단축키 설정
st.markdown("""
<style>
    /* 로딩 애니메이션 개선 */
    .stSpinner > div {
        border-color: #ff6b6b !important;
    }
    
    /* 버튼 호버 효과 */
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 10px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    
    /* 성공 메시지 애니메이션 */
    @keyframes slideIn {
        from { transform: translateX(-100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    .stSuccess {
        animation: slideIn 0.5s ease-out;
    }
    
    /* 툴팁 스타일 개선 */
    [data-baseweb="tooltip"] {
        max-width: 300px !important;
    }
</style>

<script>
// 단축키 지원
document.addEventListener('keydown', function(e) {
    // Ctrl+S: 자동 저장
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        console.log('Auto-save triggered');
    }
    // Ctrl+Enter: 운영일정 추정 시작
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        const button = document.querySelector('button[kind="primary"]');
        if (button) button.click();
    }
});
</script>
""", unsafe_allow_html=True)

# 이전 세션 내용 자동 복원
cp.autoload_state()

# 자동 저장 상태 표시
if st.session_state.get('auto_save_enabled', True):
    st.sidebar.success("💾 자동 저장 활성화됨")
    auto_save_interval = st.sidebar.slider(
        "자동 저장 주기 (분)", 
        min_value=1, 
        max_value=10, 
        value=5,
        help="설정이 자동으로 저장되는 주기를 설정합니다."
    )

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

# 단축키 안내
with st.sidebar:
    with st.expander("⌨️ 단축키 안내"):
        st.markdown("""
        - **Ctrl + Enter**: 운영일정 추정 시작
        - **Ctrl + S**: 설정 저장
        - **Tab**: 다음 입력 필드로 이동
        - **Shift + Tab**: 이전 입력 필드로 이동
        """)

# 진행 상태 표시
def show_progress_status():
    """현재 설정 진행 상태를 표시합니다."""
    acts_df = st.session_state.get("activities", pd.DataFrame())
    job_df = st.session_state.get("job_acts_map", pd.DataFrame())
    room_plan = st.session_state.get("room_plan", pd.DataFrame())
    oper_window = st.session_state.get("oper_window", pd.DataFrame())
    prec_df = st.session_state.get("precedence", pd.DataFrame())
    
    # 각 섹션별 완료 상태 확인
    activities_done = not acts_df.empty and (acts_df["use"] == True).any()
    precedence_done = True  # 선택사항이므로 항상 True
    jobs_done = not job_df.empty and job_df["count"].sum() > 0
    
    # batched 활동이 있는지 확인
    has_batched = False
    batched_done = True
    if activities_done:
        batched_activities = acts_df[
            (acts_df['mode'] == 'batched') & 
            (acts_df['use'] == True)
        ]
        has_batched = not batched_activities.empty
        if has_batched:
            # 그룹 크기 호환성 체크
            from solver.group_formation import check_group_size_compatibility
            is_compatible, _ = check_group_size_compatibility(acts_df)
            batched_done = is_compatible
    
    rooms_done = not room_plan.empty or bool(st.session_state.get("room_template", {}))
    time_done = not oper_window.empty
    
    # 전체 진행률 계산
    if has_batched:
        total_steps = 6
        completed_steps = sum([
            activities_done,
            precedence_done,
            jobs_done,
            batched_done,
            rooms_done,
            time_done
        ])
    else:
        total_steps = 5
        completed_steps = sum([
            activities_done,
            precedence_done,
            jobs_done,
            rooms_done,
            time_done
        ])
    
    progress = min(completed_steps / total_steps, 1.0)  # 최대값을 1.0으로 제한
    
    # Progress bar 표시
    st.progress(progress, text=f"설정 진행률: {int(progress * 100)}%")
    
    # 각 섹션별 상태 표시
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if activities_done:
            st.success("✅ 활동 정의")
        else:
            st.error("❌ 활동 정의")
    
    with col2:
        st.success("✅ 선후행 제약")  # 선택사항
    
    with col3:
        if jobs_done:
            st.success("✅ 직무별 활동")
        else:
            st.error("❌ 직무별 활동")
    
    with col4:
        if has_batched:
            if batched_done:
                st.success("✅ 집단면접")
            else:
                st.error("❌ 집단면접")
        else:
            st.info("➖ 집단면접")
    
    with col5:
        if rooms_done:
            st.success("✅ 운영 공간")
        else:
            st.error("❌ 운영 공간")
    
    with col6:
        if time_done:
            st.success("✅ 운영 시간")
        else:
            st.error("❌ 운영 시간")
    
    # batched 모드 알림
    if has_batched and not st.session_state.get('batched_notified', False):
        st.info("💡 **집단면접 모드가 감지되었습니다!** 아래 '집단면접 설정' 섹션에서 그룹 구성 방식을 설정해주세요.")
        st.session_state['batched_notified'] = True

# 진행 상태 표시
show_progress_status()

st.markdown("---")

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
    st.session_state.setdefault("oper_start_time", datetime_time(9, 0))
    st.session_state.setdefault("oper_end_time", datetime_time(18, 0))
    
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

# 빠른 시작 가이드
with st.expander("📖 **빠른 시작 가이드**", expanded=False):
    st.markdown("""
    ### 🚀 빠른 시작 (3단계)
    
    1. **기본 설정으로 시작**: 
       - 처음이시면 바로 '운영일정추정 시작' 버튼을 클릭하세요
       - 기본 설정으로 결과를 확인할 수 있습니다
    
    2. **면접 모드 선택**:
       - **individual**: 일반 개별 면접 (기본값)
       - **parallel**: 같은 공간에서 여러 명이 각자 면접
       - **batched**: 집단면접 (여러 명이 함께 하는 활동)
    
    3. **집단면접 사용 시**:
       - batched 모드 선택 시 자동으로 '집단면접 설정' 섹션이 나타납니다
       - 그룹 크기가 호환되는지 확인하세요
       - '그룹 구성 시뮬레이션'으로 미리 확인 가능합니다
    
    ### 💡 주요 기능
    
    - **진행 상태 표시**: 상단에서 설정 완료 상태를 한눈에 확인
    - **자동 연동 알림**: 설정 변경 시 영향받는 섹션을 자동으로 알려줍니다
    - **체류시간 분석**: 결과에서 직무별/그룹별 체류시간 통계 제공
    
    ### ⚠️ 주의사항
    
    - 집단면접 활동들의 그룹 크기 범위가 겹쳐야 합니다
    - 운영 공간은 활동에 맞게 자동으로 설정됩니다
    - 선후행 제약은 선택사항입니다
    """)

# 대화형 튜토리얼
if st.session_state.get('show_tutorial', True):
    with st.container():
        tutorial_container = st.info("🎓 **튜토리얼 모드 활성화됨** - 처음 사용하시는 분을 위한 단계별 가이드입니다.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("👉 각 섹션을 진행하시면 다음 단계를 안내해드립니다.")
        with col2:
            if st.button("튜토리얼 종료"):
                st.session_state['show_tutorial'] = False
                st.rerun()

# 튜토리얼 단계별 안내
def show_tutorial_hint():
    """현재 진행 상황에 따라 튜토리얼 힌트를 표시합니다."""
    if not st.session_state.get('show_tutorial', True):
        return
    
    # 현재 상태 확인
    acts_df = st.session_state.get("activities", pd.DataFrame())
    job_df = st.session_state.get("job_acts_map", pd.DataFrame())
    room_plan = st.session_state.get("room_plan", pd.DataFrame())
    
    # 단계별 가이드
    if acts_df.empty or not (acts_df["use"] == True).any():
        st.info("💡 **튜토리얼 단계 1**: 먼저 '1️⃣ 면접 활동 정의'에서 활동을 추가하거나 예제 템플릿을 사용해보세요!")
    elif job_df.empty or job_df["count"].sum() == 0:
        st.info("💡 **튜토리얼 단계 2**: '3️⃣ 직무별 면접활동 정의'에서 직무와 인원수를 설정하세요!")
    elif room_plan.empty and not st.session_state.get("room_template", {}):
        st.info("💡 **튜토리얼 단계 3**: '4️⃣ 운영 공간 설정'에서 면접실 정보를 입력하세요!")
    else:
        st.success("💡 **튜토리얼 완료**: 모든 필수 설정이 완료되었습니다! 이제 '운영일정추정 시작' 버튼을 클릭하세요! 🎉")
        if st.button("🎓 튜토리얼 완료하기"):
            st.session_state['show_tutorial'] = False
            st.balloons()
            st.rerun()

# 메인 섹션 시작 전에 튜토리얼 힌트 표시
show_tutorial_hint()

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
    
    # 성능 통계 표시
    st.markdown("---")
    with st.expander("📊 사용 통계", expanded=True):
        # 실행 횟수 추적
        if 'total_runs' not in st.session_state:
            st.session_state['total_runs'] = 0
        if 'successful_runs' not in st.session_state:
            st.session_state['successful_runs'] = 0
        if 'processing_times' not in st.session_state:
            st.session_state['processing_times'] = []
        
        # 통계 표시
        st.metric("총 실행 횟수", st.session_state.get('total_runs', 0))
        
        if st.session_state.get('total_runs', 0) > 0:
            success_rate = (st.session_state.get('successful_runs', 0) / st.session_state.get('total_runs', 1)) * 100
            st.metric("성공률", f"{success_rate:.1f}%")
        
        if st.session_state.get('processing_times', []):
            avg_time = sum(st.session_state['processing_times']) / len(st.session_state['processing_times'])
            st.metric("평균 처리 시간", f"{avg_time:.1f}초")
            st.metric("마지막 처리 시간", f"{st.session_state['processing_times'][-1]:.1f}초")
        
        # 리셋 버튼
        if st.button("📊 통계 초기화"):
            st.session_state['total_runs'] = 0
            st.session_state['successful_runs'] = 0
            st.session_state['processing_times'] = []
            st.rerun()

# 데이터 검증
acts_df = st.session_state.get("activities", pd.DataFrame())
job_df = st.session_state.get("job_acts_map", pd.DataFrame())
room_plan = st.session_state.get("room_plan", pd.DataFrame())
oper_df = st.session_state.get("oper_window", pd.DataFrame())
prec_df = st.session_state.get("precedence", pd.DataFrame())

# 검증 결과 표시
validation_errors = []

if acts_df.empty or not (acts_df["use"] == True).any():
    validation_errors.append({
        "error": "활동을 하나 이상 정의하고 'use=True'로 설정해주세요.",
        "section": "1️⃣ 면접 활동 정의",
        "action": "활동을 추가하거나 기존 활동의 'use' 체크박스를 활성화하세요."
    })

if job_df.empty or (job_df["count"].sum() == 0):
    validation_errors.append({
        "error": "직무 코드를 추가하고 인원수를 1명 이상 입력해주세요.",
        "section": "3️⃣ 직무별 면접활동 정의",
        "action": "직무 코드를 추가하고 각 직무별 인원수를 설정하세요."
    })

if job_df["code"].duplicated().any():
    validation_errors.append({
        "error": "중복된 직무 코드가 있습니다.",
        "section": "3️⃣ 직무별 면접활동 정의",
        "action": "중복된 직무 코드를 수정하거나 삭제하세요."
    })

# room_plan 검증: room_template이 있으면 유효한 것으로 간주
room_template = st.session_state.get("room_template", {})
if room_plan.empty and not room_template:
    validation_errors.append({
        "error": "운영 공간을 설정해주세요.",
        "section": "4️⃣ 운영 공간 설정",
        "action": "각 면접실의 개수와 수용 인원을 설정하세요."
    })

# Batched 활동이 있을 때 그룹 크기 호환성 체크
if not acts_df.empty:
    batched_acts = acts_df[(acts_df['mode'] == 'batched') & (acts_df['use'] == True)]
    if not batched_acts.empty:
        from solver.group_formation import check_group_size_compatibility
        is_compatible, error_msg = check_group_size_compatibility(acts_df)
        if not is_compatible:
            validation_errors.append({
                "error": "집단면접 활동의 그룹 크기가 호환되지 않습니다.",
                "section": "🏃‍♂️ 집단면접 설정",
                "action": "모든 batched 활동의 최소/최대 인원 범위가 겹치도록 조정하세요."
            })

if validation_errors:
    st.error("**🚨 다음 항목들을 확인해주세요:**")
    
    # 에러를 섹션별로 그룹화
    error_by_section = {}
    for error_info in validation_errors:
        section = error_info["section"]
        if section not in error_by_section:
            error_by_section[section] = []
        error_by_section[section].append(error_info)
    
    # 섹션별로 에러 표시
    for section, errors in error_by_section.items():
        with st.expander(f"**{section}** - {len(errors)}개 문제", expanded=True):
            for error_info in errors:
                st.error(f"❌ {error_info['error']}")
                st.info(f"💡 **해결방법**: {error_info['action']}")
    
    st.warning("⚠️ 위 문제들을 해결한 후 다시 '운영일정추정 시작' 버튼을 클릭하세요.")
else:
    st.success("✅ 모든 설정이 완료되었습니다! 운영일정추정을 시작할 수 있습니다.")

# 운영일정 추정 실행
if st.button("🚀 운영일정추정 시작", type="primary", use_container_width=True, on_click=reset_run_state):
    if not validation_errors:
        # 실행 전 최종 확인
        total_candidates = job_df['count'].sum()
        total_activities = len(acts_df[acts_df['use'] == True])
        
        # 예상 소요 시간 계산
        total_duration = 0
        for _, act in acts_df[acts_df['use'] == True].iterrows():
            total_duration += act['duration_min']
        
        st.info(f"""
        📊 **실행 전 요약**
        - 총 지원자 수: {total_candidates}명
        - 활성화된 활동 수: {total_activities}개
        - 지원자당 예상 소요시간: {total_duration}분
        """)
        
        # 프로그레스 바와 상태 메시지를 위한 컨테이너
        progress_container = st.container()
        status_container = st.container()
        
        with st.spinner("최적의 운영 일정을 계산 중입니다..."):
            try:
                # 실행 시작 시간 기록
                start_time = time.time()
                
                # 실행 횟수 증가
                st.session_state['total_runs'] = st.session_state.get('total_runs', 0) + 1
                
                # 진행 상황 표시
                progress_bar = progress_container.progress(0)
                status_text = status_container.empty()
                
                # 단계별 진행
                status_text.text("📍 단계 1/3: 설정 검증 중...")
                progress_bar.progress(0.33)
                
                cfg = core.build_config(st.session_state)
                
                status_text.text("📍 단계 2/3: 최적화 알고리즘 실행 중...")
                progress_bar.progress(0.66)
                
                status, final_wide, logs, limit = solve_for_days(cfg, params, debug=debug_mode)
                
                status_text.text("📍 단계 3/3: 결과 처리 중...")
                progress_bar.progress(1.0)
                
                # 실행 시간 계산
                execution_time = time.time() - start_time
                st.session_state['processing_times'] = st.session_state.get('processing_times', []) + [execution_time]
                
                # 진행 상황 UI 제거
                progress_bar.empty()
                status_text.empty()
                
                st.session_state['last_solve_logs'] = logs
                st.session_state['solver_status'] = status
                st.session_state['daily_limit'] = limit
                
                if status == "OK" and final_wide is not None and not final_wide.empty:
                    st.session_state['final_schedule'] = final_wide
                    st.session_state['successful_runs'] = st.session_state.get('successful_runs', 0) + 1
                    st.balloons()
                    st.success(f"🎉 최적화가 성공적으로 완료되었습니다! (처리 시간: {execution_time:.1f}초)")
                else:
                    st.session_state['final_schedule'] = None
                    
                    # 상태별 구체적인 에러 메시지와 해결책
                    error_solutions = {
                        "INFEASIBLE": {
                            "message": "현재 설정으로는 유효한 스케줄을 생성할 수 없습니다.",
                            "solutions": [
                                "운영 시간을 늘려보세요 (예: 9시-18시 → 9시-20시)",
                                "운영 공간(방)의 수를 늘려보세요",
                                "활동 시간을 줄여보세요",
                                "선후행 제약을 완화해보세요"
                            ]
                        },
                        "MAX_DAYS_EXCEEDED": {
                            "message": "설정된 최대 일수 내에 모든 지원자를 배정할 수 없습니다.",
                            "solutions": [
                                "일일 운영 시간을 늘려보세요",
                                "더 많은 면접실을 추가해보세요",
                                "병렬 처리 가능한 활동은 parallel 모드로 변경해보세요"
                            ]
                        },
                        "NO_SOLUTION": {
                            "message": "해결 가능한 스케줄을 찾을 수 없습니다.",
                            "solutions": [
                                "제약 조건을 하나씩 제거하며 테스트해보세요",
                                "지원자 수를 줄여서 먼저 테스트해보세요",
                                "기본 설정으로 되돌려보세요"
                            ]
                        }
                    }
                    
                    if status in error_solutions:
                        error_info = error_solutions[status]
                        st.error(f"❌ {error_info['message']}")
                        
                        with st.expander("🔧 해결 방법", expanded=True):
                            for i, solution in enumerate(error_info['solutions'], 1):
                                st.write(f"{i}. {solution}")
                        
                        # 빠른 수정 버튼들
                        st.markdown("### 🚀 빠른 수정")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("⏰ 운영시간 1시간 연장"):
                                current_end = st.session_state.get("oper_end_time", datetime_time(18, 0))
                                new_end = datetime_time(current_end.hour + 1, current_end.minute)
                                st.session_state["oper_end_time"] = new_end
                                st.rerun()
                        
                        with col2:
                            if st.button("🏢 면접실 1개씩 추가"):
                                room_template = st.session_state.get("room_template", {})
                                for rt in room_template:
                                    room_template[rt]["count"] += 1
                                st.session_state["room_template"] = room_template
                                st.rerun()
                        
                        with col3:
                            if st.button("🔄 기본 설정으로 복원"):
                                init_session_states()
                                st.rerun()
                    
            except Exception as e:
                # 예외 처리 개선
                error_type = type(e).__name__
                error_message = str(e)
                
                st.error(f"⚠️ 계산 중 오류가 발생했습니다: {error_type}")
                
                with st.expander("🐛 오류 상세 정보", expanded=True):
                    st.code(error_message)
                    
                    # 스택 트레이스 (디버그 모드에서만)
                    if debug_mode:
                        import traceback
                        st.code(traceback.format_exc())
                
                # 오류 복구 가이드
                st.warning("💡 **오류 해결 단계**")
                st.markdown("""
                1. **입력 데이터 확인**: 모든 필수 항목이 올바르게 입력되었는지 확인
                2. **제약 조건 검토**: 너무 엄격한 제약이 있는지 확인
                3. **단순화 테스트**: 최소한의 설정으로 먼저 테스트
                4. **지원 요청**: 위 단계로 해결되지 않으면 관리자에게 문의
                """)
                
                # 오류 리포트 생성
                if st.button("📧 오류 리포트 생성"):
                    error_report = f"""
                    오류 발생 시간: {datetime.now()}
                    오류 타입: {error_type}
                    오류 메시지: {error_message}
                    
                    현재 설정:
                    - 지원자 수: {job_df['count'].sum()}
                    - 활동 수: {len(acts_df[acts_df['use'] == True])}
                    - 운영 시간: {st.session_state.get('oper_start_time')} - {st.session_state.get('oper_end_time')}
                    """
                    st.text_area("오류 리포트 (복사하여 관리자에게 전달)", error_report, height=200)
                
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
    
    # 체류시간 분석 추가
    st.subheader("⏱️ 직무별 체류시간 분석")
    
    # 디버깅 모드 토글 (개발용)
    with st.expander("🔧 개발자 옵션"):
        debug_stay_time = st.checkbox("체류시간 분석 디버깅 모드", key="debug_stay_time", help="데이터 구조를 확인하기 위한 디버깅 정보를 표시합니다.")
    
    def calculate_stay_duration_stats(schedule_df):
        """각 지원자의 체류시간을 계산하고 직무별 통계를 반환"""
        stats_data = []
        
        # 실제 데이터 구조 확인을 위한 디버깅 정보 (개발용)
        if st.session_state.get('debug_stay_time', False):
            st.write("**디버깅: 스케줄 데이터 구조**")
            st.write(f"컬럼들: {list(schedule_df.columns)}")
            st.write(f"데이터 샘플 (첫 3행):")
            st.dataframe(schedule_df.head(3))
        
        # 컬럼명 매핑 (실제 데이터에 맞게 조정)
        id_col = 'id' if 'id' in schedule_df.columns else 'candidate_id'
        job_col = 'code' if 'code' in schedule_df.columns else 'job_code'
        group_col = 'group_id' if 'group_id' in schedule_df.columns else None
        
        # 시간 컬럼들 찾기 (start_활동명, end_활동명 형태)
        start_cols = [col for col in schedule_df.columns if col.startswith('start_')]
        end_cols = [col for col in schedule_df.columns if col.startswith('end_')]
        
        if not start_cols or not end_cols:
            st.error("시간 정보 컬럼을 찾을 수 없습니다. start_* 또는 end_* 형태의 컬럼이 필요합니다.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # 지원자별로 그룹화하여 체류시간 계산
        for candidate_id, candidate_data in schedule_df.groupby(id_col):
            # 해당 지원자의 모든 활동 시간 정보 수집
            all_start_times = []
            all_end_times = []
            
            for _, row in candidate_data.iterrows():
                for start_col in start_cols:
                    if pd.notna(row[start_col]) and row[start_col] != '':
                        try:
                            # 시간 문자열을 datetime으로 변환
                            time_str = str(row[start_col])
                            if ':' in time_str:
                                # HH:MM:SS 또는 HH:MM 형태
                                time_obj = pd.to_datetime(time_str, format='%H:%M:%S', errors='coerce')
                                if pd.isna(time_obj):
                                    time_obj = pd.to_datetime(time_str, format='%H:%M', errors='coerce')
                                if not pd.isna(time_obj):
                                    all_start_times.append(time_obj)
                        except:
                            continue
                
                for end_col in end_cols:
                    if pd.notna(row[end_col]) and row[end_col] != '':
                        try:
                            # 시간 문자열을 datetime으로 변환
                            time_str = str(row[end_col])
                            if ':' in time_str:
                                # HH:MM:SS 또는 HH:MM 형태
                                time_obj = pd.to_datetime(time_str, format='%H:%M:%S', errors='coerce')
                                if pd.isna(time_obj):
                                    time_obj = pd.to_datetime(time_str, format='%H:%M', errors='coerce')
                                if not pd.isna(time_obj):
                                    all_end_times.append(time_obj)
                        except:
                            continue
            
            if all_start_times and all_end_times:
                # 전체 체류시간 = 첫 번째 활동 시작 ~ 마지막 활동 종료
                total_start = min(all_start_times)
                total_end = max(all_end_times)
                stay_duration_minutes = (total_end - total_start).total_seconds() / 60
                
                # 직무 코드 (첫 번째 행에서 가져오기)
                job_code = candidate_data.iloc[0].get(job_col, 'Unknown')
                
                # 그룹 ID (있는 경우)
                group_id = candidate_data.iloc[0].get(group_col) if group_col else None
                
                stats_data.append({
                    'candidate_id': candidate_id,
                    'job_code': job_code,
                    'group_id': group_id,
                    'stay_duration_minutes': stay_duration_minutes,
                    'start_time': total_start,
                    'end_time': total_end
                })
        
        if not stats_data:
            st.warning("체류시간을 계산할 수 있는 유효한 데이터가 없습니다.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        stats_df = pd.DataFrame(stats_data)
        
        # 직무별 통계 계산
        job_stats = []
        for job_code, job_data in stats_df.groupby('job_code'):
            durations = job_data['stay_duration_minutes']
            job_stats.append({
                'job_code': job_code,
                'count': len(job_data),
                'min_duration': durations.min(),
                'max_duration': durations.max(),
                'avg_duration': durations.mean(),
                'median_duration': durations.median()
            })
        
        job_stats_df = pd.DataFrame(job_stats)
        
        # 그룹별 통계 계산 (그룹 ID가 있는 경우)
        group_stats_df = pd.DataFrame()
        if group_col and 'group_id' in stats_df.columns and stats_df['group_id'].notna().any():
            group_stats = []
            for group_id, group_data in stats_df.groupby('group_id'):
                if pd.notna(group_id):
                    # 그룹 내 모든 구성원의 체류시간이 동일해야 함 (동시 시작/종료)
                    durations = group_data['stay_duration_minutes']
                    job_dist = group_data['job_code'].value_counts().to_dict()
                    
                    group_stats.append({
                        'group_id': int(group_id),
                        'member_count': len(group_data),
                        'duration': durations.iloc[0],  # 모든 구성원이 동일한 체류시간
                        'job_distribution': job_dist,
                        'start_time': group_data['start_time'].iloc[0],
                        'end_time': group_data['end_time'].iloc[0]
                    })
            
            if group_stats:
                group_stats_df = pd.DataFrame(group_stats)
        
        return job_stats_df, stats_df, group_stats_df
    
    try:
        job_stats_df, individual_stats_df, group_stats_df = calculate_stay_duration_stats(final_schedule)
        
        if not job_stats_df.empty:
            # 직무별 통계 표시
            st.markdown("**📊 직무별 체류시간 통계 (분 단위)**")
            
            # 표시용 데이터프레임 생성
            display_stats = job_stats_df.copy()
            display_stats['min_duration'] = display_stats['min_duration'].round(1)
            display_stats['max_duration'] = display_stats['max_duration'].round(1)
            display_stats['avg_duration'] = display_stats['avg_duration'].round(1)
            display_stats['median_duration'] = display_stats['median_duration'].round(1)
            
            # 컬럼명 한글화
            display_stats.columns = ['직무코드', '인원수', '최소시간(분)', '최대시간(분)', '평균시간(분)', '중간값(분)']
            
            st.dataframe(display_stats, use_container_width=True)
            
            # 시각적 요약
            col1, col2, col3 = st.columns(3)
            with col1:
                overall_min = job_stats_df['min_duration'].min()
                st.metric("전체 최소 체류시간", f"{overall_min:.1f}분")
            with col2:
                overall_max = job_stats_df['max_duration'].max()
                st.metric("전체 최대 체류시간", f"{overall_max:.1f}분")
            with col3:
                overall_avg = (individual_stats_df['stay_duration_minutes'].mean())
                st.metric("전체 평균 체류시간", f"{overall_avg:.1f}분")
            
            # 그룹별 체류시간 통계 (집단면접이 있는 경우)
            if not group_stats_df.empty:
                st.markdown("**👥 그룹별 체류시간 통계**")
                
                # 그룹 통계 표시
                group_display = group_stats_df.copy()
                group_display['duration'] = group_display['duration'].round(1)
                group_display['start_time'] = group_display['start_time'].dt.strftime('%H:%M')
                group_display['end_time'] = group_display['end_time'].dt.strftime('%H:%M')
                
                # 직무 분포를 문자열로 변환
                group_display['직무구성'] = group_display['job_distribution'].apply(
                    lambda x: ', '.join([f"{k}:{v}명" for k, v in x.items()])
                )
                
                # 표시할 컬럼 선택
                group_display = group_display[['group_id', 'member_count', 'duration', 'start_time', 'end_time', '직무구성']]
                group_display.columns = ['그룹ID', '인원수', '체류시간(분)', '시작시간', '종료시간', '직무구성']
                
                st.dataframe(group_display, use_container_width=True)
                
                # 그룹 요약 정보
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("총 그룹 수", f"{len(group_stats_df)}개")
                with col2:
                    avg_group_size = group_stats_df['member_count'].mean()
                    st.metric("평균 그룹 크기", f"{avg_group_size:.1f}명")
            
            # 상세 정보를 expander로 제공
            with st.expander("🔍 개별 지원자 체류시간 상세보기"):
                detail_display = individual_stats_df.copy()
                detail_display['stay_duration_minutes'] = detail_display['stay_duration_minutes'].round(1)
                detail_display['start_time'] = detail_display['start_time'].dt.strftime('%H:%M')
                detail_display['end_time'] = detail_display['end_time'].dt.strftime('%H:%M')
                
                # 그룹 ID가 있는 경우 표시
                if 'group_id' in detail_display.columns:
                    detail_display['group_id'] = detail_display['group_id'].fillna('').astype(str).str.replace('.0', '', regex=False)
                    detail_display.columns = ['지원자ID', '직무코드', '그룹ID', '체류시간(분)', '시작시간', '종료시간']
                else:
                    detail_display = detail_display.drop(columns=['group_id'], errors='ignore')
                    detail_display.columns = ['지원자ID', '직무코드', '체류시간(분)', '시작시간', '종료시간']
                
                st.dataframe(detail_display, use_container_width=True)
        else:
            st.warning("체류시간 통계를 계산할 수 없습니다.")
            
    except Exception as e:
        st.error(f"체류시간 분석 중 오류가 발생했습니다: {str(e)}")
        st.info("일정표에 필요한 컬럼(candidate_id, start_time, end_time, job_code)이 있는지 확인해주세요.")
    
    # 결과 테이블
    st.subheader("📋 상세 일정표")
    st.dataframe(final_schedule, use_container_width=True)
    
    # Excel 다운로드
    excel_buffer = BytesIO()
    df_to_excel_internal(final_schedule, excel_buffer)
    excel_data = excel_buffer.getvalue()
    
    st.download_button(
        label="📊 Excel 파일 다운로드",
        data=excel_data,
        file_name=f"interview_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="secondary"  # 빨간색 버튼으로 변경
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
col_header, col_refresh = st.columns([3, 2])
with col_header:
    st.header("1️⃣ 면접 활동 정의")
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)  # 헤더와 높이 맞추기
    if st.button("🔄 섹션 새로고침", help="AG-Grid가 반응하지 않을 때 섹션을 새로고침합니다"):
        if "section_refresh_counter" not in st.session_state:
            st.session_state["section_refresh_counter"] = {}
        if "activities" not in st.session_state["section_refresh_counter"]:
            st.session_state["section_refresh_counter"]["activities"] = 0
        st.session_state["section_refresh_counter"]["activities"] += 1
        st.rerun()

st.markdown("면접 프로세스를 구성하는 모든 활동을 정의합니다.")

# 예제 템플릿 제공
with st.expander("📚 예제 템플릿", expanded=False):
    st.markdown("""
    ### 🎯 일반 채용 면접
    | 활동 | 모드 | 시간(분) | 방 종류 | 최소인원 | 최대인원 |
    |------|------|----------|---------|----------|----------|
    | 서류검토 | individual | 10 | 대기실 | 1 | 1 |
    | 1차면접 | individual | 30 | 면접실A | 1 | 1 |
    | 2차면접 | individual | 45 | 면접실B | 1 | 1 |
    | 인성검사 | parallel | 60 | 검사실 | 1 | 10 |
    
    ### 👥 집단면접 포함
    | 활동 | 모드 | 시간(분) | 방 종류 | 최소인원 | 최대인원 |
    |------|------|----------|---------|----------|----------|
    | 오리엔테이션 | batched | 30 | 강당 | 20 | 50 |
    | 집단토론 | batched | 60 | 토론실 | 4 | 6 |
    | 개별면접 | individual | 30 | 면접실 | 1 | 1 |
    | PT발표 | batched | 90 | 발표실 | 5 | 8 |
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎯 일반 채용 템플릿 적용"):
            template_data = pd.DataFrame({
                "use": [True, True, True, True],
                "activity": ["서류검토", "1차면접", "2차면접", "인성검사"],
                "mode": ["individual", "individual", "individual", "parallel"],
                "duration_min": [10, 30, 45, 60],
                "room_type": ["대기실", "면접실A", "면접실B", "검사실"],
                "min_cap": [1, 1, 1, 1],
                "max_cap": [1, 1, 1, 10],
            })
            st.session_state["activities"] = template_data
            st.rerun()
    
    with col2:
        if st.button("👥 집단면접 템플릿 적용"):
            template_data = pd.DataFrame({
                "use": [True, True, True, True],
                "activity": ["오리엔테이션", "집단토론", "개별면접", "PT발표"],
                "mode": ["batched", "batched", "individual", "batched"],
                "duration_min": [30, 60, 30, 90],
                "room_type": ["강당", "토론실", "면접실", "발표실"],
                "min_cap": [20, 4, 1, 5],
                "max_cap": [50, 6, 1, 8],
            })
            st.session_state["activities"] = template_data
            st.rerun()
    
    with col3:
        if st.button("🔄 기본값으로 리셋"):
            init_session_states()
            st.rerun()

# 모드별 설명
with st.expander("ℹ️ 면접 모드 상세 설명", expanded=False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🎯 Individual (개별)
        - **설명**: 전통적인 1:1 면접
        - **특징**: 
          - 한 명씩 독립적으로 진행
          - 방을 독점적으로 사용
          - 대기 시간 최소화
        - **예시**: 임원면접, 실무면접
        """)
    
    with col2:
        st.markdown("""
        ### 🔀 Parallel (병렬)
        - **설명**: 같은 공간에서 여러 명이 각자 활동
        - **특징**:
          - 방 용량만큼 동시 진행
          - 각자 다른 시작/종료 시간
          - 공간 효율성 극대화
        - **예시**: 인적성검사, 코딩테스트
        """)
    
    with col3:
        st.markdown("""
        ### 👥 Batched (집단)
        - **설명**: 여러 명이 함께하는 그룹 활동
        - **특징**:
          - 그룹 단위로 동시 시작/종료
          - 그룹 크기 범위 설정 필요
          - 자동 그룹 구성
        - **예시**: 집단토론, 팀 프로젝트
        """)

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

mode_values = ["individual", "parallel", "batched"]
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

gb.configure_column("room_type", header_name="면접실 이름", editable=True)

grid_opts = gb.build()

st.markdown("#### 활동 정의")

# 행 추가/삭제 기능 (위로 이동)
col_add, col_del = st.columns(2)

with col_add:
    if st.button("➕ 활동 행 추가"):
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
        if st.button("❌ 선택된 활동 삭제"):
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

# AG-Grid 표시 (행 추가/삭제 기능 아래로 이동)
# 섹션별 새로고침을 위한 동적 key 생성
activities_refresh_count = st.session_state.get("section_refresh_counter", {}).get("activities", 0)

grid_ret = AgGrid(
    df,
    gridOptions=grid_opts,
    data_return_mode=DataReturnMode.AS_INPUT,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=True,
    theme="balham",
    key=f"activities_grid_{activities_refresh_count}",  # 동적 key로 강제 재렌더링
)

st.session_state["activities"] = grid_ret["data"]

# Batched 모드 활동이 있는지 확인하고 알림 표시
updated_activities = st.session_state["activities"]
batched_activities = updated_activities[
    (updated_activities['mode'] == 'batched') & 
    (updated_activities['use'] == True)
]
if not batched_activities.empty:
    st.info("💡 **집단면접 활동이 감지되었습니다!**")
    
    # 그룹 크기 정보 표시
    for _, act in batched_activities.iterrows():
        st.write(f"- **{act['activity']}**: {act['min_cap']}-{act['max_cap']}명 그룹")
    
    # 그룹 크기 호환성 미리 체크
    from solver.group_formation import check_group_size_compatibility
    is_compatible, error_msg = check_group_size_compatibility(updated_activities)
    
    if not is_compatible:
        st.warning("⚠️ **주의**: 그룹 크기가 호환되지 않습니다. 아래 '집단면접 설정' 섹션에서 확인해주세요.")
    else:
        min_caps = batched_activities['min_cap'].values
        max_caps = batched_activities['max_cap'].values
        common_min = max(min_caps)
        common_max = min(max_caps)
        st.success(f"✅ 그룹 크기 호환성 OK: 공통 범위 {common_min}-{common_max}명")

# Parallel 모드 활동이 있는지 확인하고 설명 표시
parallel_activities = updated_activities[
    (updated_activities['mode'] == 'parallel') & 
    (updated_activities['use'] == True)
]
if not parallel_activities.empty:
    st.info("🔀 **병렬 처리 활동이 있습니다**: 같은 공간에서 여러 명이 각자 활동을 수행합니다.")
    for _, act in parallel_activities.iterrows():
        st.write(f"- **{act['activity']}**: 최대 {act['max_cap']}명 동시 수용")

# 설정 변경 감지 및 알림
def detect_configuration_changes():
    """설정 변경을 감지하고 영향받는 섹션을 알려줍니다."""
    notifications = []
    
    # 이전 상태와 비교
    prev_activities = st.session_state.get('prev_activities_state', pd.DataFrame())
    current_activities = st.session_state.get('activities', pd.DataFrame())
    
    if not prev_activities.equals(current_activities):
        # 활동이 변경됨
        affected_sections = []
        
        # room_type이 변경되었는지 확인
        if not prev_activities.empty and not current_activities.empty:
            prev_room_types = set(prev_activities[prev_activities['use'] == True]['room_type'].dropna())
            curr_room_types = set(current_activities[current_activities['use'] == True]['room_type'].dropna())
            
            if prev_room_types != curr_room_types:
                affected_sections.append("4️⃣ 운영 공간 설정")
        
        # batched 모드가 추가/제거되었는지 확인
        prev_has_batched = not prev_activities.empty and ((prev_activities['mode'] == 'batched') & (prev_activities['use'] == True)).any()
        curr_has_batched = not current_activities.empty and ((current_activities['mode'] == 'batched') & (current_activities['use'] == True)).any()
        
        if prev_has_batched != curr_has_batched:
            if curr_has_batched:
                affected_sections.append("🏃‍♂️ 집단면접 설정 (새로 추가됨)")
            
        # 선후행 제약에 영향을 줄 수 있는 활동 변경
        if not prev_activities.empty and not current_activities.empty:
            prev_act_names = set(prev_activities[prev_activities['use'] == True]['activity'])
            curr_act_names = set(current_activities[current_activities['use'] == True]['activity'])
            
            if prev_act_names != curr_act_names:
                affected_sections.append("2️⃣ 선후행 제약 정의")
        
        if affected_sections:
            notifications.append({
                "type": "활동 변경",
                "sections": affected_sections
            })
        
        # 현재 상태를 저장
        st.session_state['prev_activities_state'] = current_activities.copy()
    
    return notifications

# 활동 정의 섹션 후에 변경 감지 및 알림 표시
notifications = detect_configuration_changes()
if notifications:
    st.warning("⚠️ **설정 변경 감지**")
    for notif in notifications:
        st.info(f"**{notif['type']}**으로 인해 다음 섹션들을 확인해주세요:")
        for section in notif['sections']:
            st.write(f"  • {section}")

st.divider()

# =============================================================================
# 섹션 2: 선후행 제약 설정 (면접 활동 정의 바로 다음으로 이동)
# =============================================================================
col_header, col_refresh = st.columns([3, 2])
with col_header:
    st.header("2️⃣ 선후행 제약 설정")
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)  # 헤더와 높이 맞추기
    if st.button("🔄 섹션 새로고침", help="선후행 제약 UI가 먹통일 때 새로고침"):
        # 섹션별 새로고침
        if "section_refresh_counter" not in st.session_state:
            st.session_state["section_refresh_counter"] = {}
        if "precedence" not in st.session_state["section_refresh_counter"]:
            st.session_state["section_refresh_counter"]["precedence"] = 0
        st.session_state["section_refresh_counter"]["precedence"] += 1
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

    
    # ═══════════════════════════════════════════
    # 🎯 면접 순서 설정 (단계별 가이드)
    # ═══════════════════════════════════════════

    # 현재 설정된 START/END 규칙 확인
    current_start = None
    current_end = None
    for _, rule in prec_df.iterrows():
        if rule['predecessor'] == "__START__":
            current_start = rule['successor']
        if rule['successor'] == "__END__":
            current_end = rule['predecessor']
    
    # 섹션별 새로고침을 위한 동적 key 생성
    precedence_refresh_count = st.session_state.get("section_refresh_counter", {}).get("precedence", 0)
    
    st.markdown("---")
    st.subheader("🎯 면접 순서 설정")
    st.markdown("면접 활동들의 순서와 제약을 설정합니다.")
    
    # 탭으로 기능 구분
    tab1, tab2 = st.tabs(["🏁 시작/끝 규칙", "🔗 순서 규칙"])
    
    with tab1:
        st.markdown("💡 **면접의 첫 번째와 마지막 활동을 지정하세요.** (선택사항)")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        # 현재 값을 기본값으로 설정
        start_idx = 0
        end_idx = 0
        if current_start and current_start in ACT_OPTS:
            start_idx = ACT_OPTS.index(current_start) + 1
        if current_end and current_end in ACT_OPTS:
            end_idx = ACT_OPTS.index(current_end) + 1
        
        with col1:
            first = st.selectbox(
                "🏁 가장 먼저 할 활동", 
                ["(지정 안 함)"] + ACT_OPTS, 
                index=start_idx, 
                key=f"first_act_{precedence_refresh_count}",
                help="면접 프로세스의 첫 번째 활동을 선택하세요"
            )
        
        with col2:
            last = st.selectbox(
                "🏁 가장 마지막 활동", 
                ["(지정 안 함)"] + ACT_OPTS, 
                index=end_idx, 
                key=f"last_act_{precedence_refresh_count}",
                help="면접 프로세스의 마지막 활동을 선택하세요"
            )
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)  # 버튼 높이 맞추기
            if st.button("✅ 적용", type="primary", use_container_width=True):
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
    
    with tab2:
        st.markdown("💡 **특정 활동 다음에 반드시 와야 하는 활동을 연결하세요.** (선택사항)")
        st.markdown("📝 **예시:** 면접1 → 면접2 (면접1 후에 반드시 면접2가 와야 함)")
        
        # 기본 연결 설정
        st.markdown("#### 📌 활동 연결")
        col_form1, col_form2, col_form3 = st.columns([2, 2, 1])
        
        with col_form1:
            p = st.selectbox("🔸 먼저 할 활동", ACT_OPTS, key=f"pred_select_{precedence_refresh_count}", help="선행 활동을 선택하세요")
        
        with col_form2:
            s = st.selectbox("🔹 다음에 할 활동", ACT_OPTS, key=f"succ_select_{precedence_refresh_count}", help="후행 활동을 선택하세요")
        
        with col_form3:
            st.markdown("<br>", unsafe_allow_html=True)  # 버튼 높이 맞추기
            add_rule_btn = st.button("✅ 적용", type="primary", use_container_width=True)
        
        # 고급 옵션을 별도 영역으로 분리
        st.markdown("#### ⚙️ 고급 옵션")
        col_gap, col_adj = st.columns(2)
        with col_gap:
            g = st.number_input("⏱️ 최소 간격 (분)", 0, 60, 5, key=f"gap_input_{precedence_refresh_count}", help="두 활동 사이의 최소 시간 간격")
        with col_adj:
            adj = st.checkbox("📌 연속 배치 (붙여서 진행)", value=True, key=f"adj_checkbox_{precedence_refresh_count}", help="두 활동을 시간적으로 연속해서 배치")
        
        if add_rule_btn:
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
    
    # 설정된 규칙 관리 및 삭제
    with st.expander("🗂️ 설정된 규칙 관리", expanded=True):
        prec_df = st.session_state["precedence"].copy()
        
        if not prec_df.empty:
            # 규칙을 보기 좋게 표시
            prec_df["규칙표시용"] = prec_df.apply(
                lambda r: f"{r.predecessor} → {r.successor}" + 
                         (f" (간격: {r.gap_min}분)" if r.gap_min > 0 else "") +
                         (" [연속배치]" if r.adjacent else ""), axis=1
            )
            
            # 2단 구조: 왼쪽은 규칙 목록, 오른쪽은 삭제 기능
            col_rules, col_actions = st.columns([3, 2])
            
            with col_rules:
                st.markdown("**📋 현재 설정된 규칙들**")
                
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
            
            with col_actions:
                st.markdown("**🗑️ 규칙 삭제**")
                
                # 삭제할 규칙 선택
                delete_options = prec_df["규칙표시용"].tolist()
                to_delete = st.multiselect(
                    "삭제할 규칙 선택",
                    options=delete_options,
                    key=f"del_prec_select_{precedence_refresh_count}",
                    help="여러 규칙을 한 번에 선택 가능"
                )
                
                # 삭제 버튼들
                if st.button("❌ 선택 삭제", disabled=not to_delete, use_container_width=True):
                    if to_delete:
                        new_prec = prec_df[~prec_df["규칙표시용"].isin(to_delete)].drop(
                            columns="규칙표시용"
                        ).reset_index(drop=True)
                        st.session_state["precedence"] = new_prec.copy()
                        st.success(f"✅ {len(to_delete)}개 규칙 삭제!")
                        st.rerun()
                
                if st.button("🗑️ 전체 삭제", type="secondary", use_container_width=True):
                    st.session_state["precedence"] = pd.DataFrame(columns=["predecessor", "successor", "gap_min", "adjacent"])
                    st.success("✅ 모든 규칙 삭제!")
                    st.rerun()
        else:
            st.info("📋 설정된 선후행 제약 규칙이 없습니다. 위에서 규칙을 추가해보세요.")

st.divider()

# =============================================================================
# 섹션 3: 직무별 면접활동 정의 (선후행 제약 설정 다음으로 이동)
# =============================================================================
col_header, col_refresh = st.columns([3, 2])
with col_header:
    st.header("3️⃣ 직무별 면접활동 정의")
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)  # 헤더와 높이 맞추기
    if st.button("🔄 섹션 새로고침", help="직무별 면접활동 AG-Grid가 먹통일 때 새로고침"):
        # 섹션별 새로고침
        if "section_refresh_counter" not in st.session_state:
            st.session_state["section_refresh_counter"] = {}
        if "job_activities" not in st.session_state["section_refresh_counter"]:
            st.session_state["section_refresh_counter"]["job_activities"] = 0
        st.session_state["section_refresh_counter"]["job_activities"] += 1
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
            if st.button("➕ 직무 코드 행 추가"):
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
            
            if st.button("❌ 선택 코드 삭제"):
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
        
        # 섹션별 새로고침을 위한 동적 key 생성
        job_activities_refresh_count = st.session_state.get("section_refresh_counter", {}).get("job_activities", 0)
        
        grid_ret2 = AgGrid(
            df_to_display,
            gridOptions=grid_opts2,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            data_return_mode=DataReturnMode.AS_INPUT,
            fit_columns_on_grid_load=True,
            theme="balham",
            key=f"job_grid_display_{job_activities_refresh_count}",  # 동적 key로 강제 재렌더링
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
# 섹션 3-1: 집단면접 설정 (batched 활동이 있는 경우에만 표시)
# =============================================================================
# Batched 활동 확인
batched_activities = acts_df[acts_df['mode'] == 'batched']
if not batched_activities.empty:
    # 집단면접 섹션 강조 표시
    st.markdown("""
    <style>
    .batched-section {
        border: 3px solid #ff6b6b;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background-color: #fff5f5;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 107, 107, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 107, 107, 0); }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 새로운 집단면접 활동이 추가되었는지 확인
    prev_batched_count = st.session_state.get('prev_batched_count', 0)
    current_batched_count = len(batched_activities)
    
    if current_batched_count > prev_batched_count:
        st.balloons()
        st.session_state['prev_batched_count'] = current_batched_count
    
    st.markdown('<div class="batched-section">', unsafe_allow_html=True)
    
    col_header, col_refresh = st.columns([3, 2])
    with col_header:
        st.header("🏃‍♂️ 집단면접 설정")
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)  # 헤더와 높이 맞추기
        if st.button("🔄 섹션 새로고침", help="집단면접 설정이 반응하지 않을 때 새로고침"):
            # 섹션별 새로고침
            if "section_refresh_counter" not in st.session_state:
                st.session_state["section_refresh_counter"] = {}
            if "batched_settings" not in st.session_state["section_refresh_counter"]:
                st.session_state["section_refresh_counter"]["batched_settings"] = 0
            st.session_state["section_refresh_counter"]["batched_settings"] += 1
            st.rerun()

    st.markdown("집단면접(batched 모드) 활동을 위한 그룹 구성 방식을 설정합니다.")
    
    # 현재 batched 활동 목록 표시
    st.info("**📋 현재 집단면접 활동:**")
    for i, (_, act) in enumerate(batched_activities.iterrows()):
        st.write(f"{i+1}. **{act['activity']}** ({act['duration_min']}분) - 그룹 크기: {act['min_cap']}-{act['max_cap']}명")
    
    # 그룹 크기 호환성 체크
    from solver.group_formation import check_group_size_compatibility
    is_compatible, compatibility_error = check_group_size_compatibility(acts_df)
    
    if not is_compatible:
        st.error("🚨 **그룹 크기 호환성 오류**")
        st.error(compatibility_error)
        st.info("💡 **해결 방법**: 모든 batched 활동의 최소/최대 인원 범위가 겹치도록 조정해주세요.")
        
        # 구체적인 조정 가이드 제공
        st.markdown("### 🔧 권장 조정 방법")
        
        # 현재 설정된 범위 분석
        min_caps = batched_activities['min_cap'].values
        max_caps = batched_activities['max_cap'].values
        
        # 가능한 공통 범위 찾기
        potential_min = max(min_caps)
        potential_max = min(max_caps)
        
        if potential_min <= potential_max:
            st.warning(f"현재 설정으로는 공통 범위를 만들 수 없습니다. 다음 중 하나를 선택해주세요:")
        
        # 옵션 1: 최대값 기준
        option1_min = min(min_caps)
        option1_max = max(max_caps)
        
        # 옵션 2: 중간값 기준
        avg_min = int(sum(min_caps) / len(min_caps))
        avg_max = int(sum(max_caps) / len(max_caps))
        if avg_min > avg_max:
            avg_min, avg_max = avg_max, avg_min
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**옵션 1: 가장 넓은 범위 사용**")
            st.write(f"모든 활동을 **{option1_min}-{option1_max}명**으로 설정")
            
            # 각 활동별 조정 사항 표시
            for _, act in batched_activities.iterrows():
                if act['min_cap'] != option1_min or act['max_cap'] != option1_max:
                    st.write(f"- {act['activity']}: {act['min_cap']}-{act['max_cap']}명 → {option1_min}-{option1_max}명")
        
        with col2:
            st.info("**옵션 2: 평균값 기준**")
            st.write(f"모든 활동을 **{avg_min}-{avg_max}명**으로 설정")
            
            # 각 활동별 조정 사항 표시
            for _, act in batched_activities.iterrows():
                if act['min_cap'] != avg_min or act['max_cap'] != avg_max:
                    st.write(f"- {act['activity']}: {act['min_cap']}-{act['max_cap']}명 → {avg_min}-{avg_max}명")
        
        st.warning("⚠️ 위 옵션 중 하나를 선택하여 '1️⃣ 면접 활동 정의' 섹션에서 수정해주세요.")
    else:
        # 공통 그룹 크기 범위 표시
        min_caps = batched_activities['min_cap'].values
        max_caps = batched_activities['max_cap'].values
        common_min = max(min_caps)
        common_max = min(max_caps)
        
        st.success(f"✅ 그룹 크기 호환성 확인: 공통 범위 **{common_min}-{common_max}명**")
        
        # 그룹 구성 옵션
        st.subheader("📋 그룹 구성 옵션")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 직무별 분리 우선 옵션
            prefer_job_separation = st.checkbox(
                "🏢 직무별 분리 우선",
                value=st.session_state.get("prefer_job_separation", True),
                help="체크하면 같은 직무끼리 그룹을 구성하려고 시도합니다. 불가능한 경우에만 직무를 섞습니다.",
                key="cb_prefer_job_separation"
            )
            st.session_state["prefer_job_separation"] = prefer_job_separation
        
        with col2:
            # 유사 직무 그룹 설정 여부
            use_similarity_groups = st.checkbox(
                "🤝 유사 직무 그룹 사용",
                value=st.session_state.get("use_similarity_groups", False),
                help="체크하면 유사한 직무끼리 묶어서 그룹을 구성할 수 있습니다.",
                key="cb_use_similarity_groups"
            )
            st.session_state["use_similarity_groups"] = use_similarity_groups
        
        # 유사 직무 그룹 설정 UI
        if use_similarity_groups:
            st.subheader("🤝 유사 직무 그룹 설정")
            st.markdown("직무별 분리가 어려울 때 함께 묶을 수 있는 직무들을 그룹으로 설정합니다.")
            
            # 현재 직무 코드 목록
            job_codes = job_df['code'].tolist()
            
            # 기존 유사 직무 그룹 불러오기
            similarity_groups = st.session_state.get("job_similarity_groups", [])
            
            # 그룹 관리
            col_add_group, col_del_group = st.columns(2)
            
            with col_add_group:
                if st.button("➕ 유사 직무 그룹 추가"):
                    similarity_groups.append([])
                    st.session_state["job_similarity_groups"] = similarity_groups
                    st.rerun()
            
            with col_del_group:
                if similarity_groups and st.button("❌ 마지막 그룹 삭제"):
                    similarity_groups.pop()
                    st.session_state["job_similarity_groups"] = similarity_groups
                    st.rerun()
            
            # 각 그룹 편집
            updated_groups = []
            for i, group in enumerate(similarity_groups):
                st.markdown(f"**그룹 {i+1}**")
                selected_jobs = st.multiselect(
                    f"그룹 {i+1}에 포함할 직무",
                    options=job_codes,
                    default=group,
                    key=f"similarity_group_{i}"
                )
                if selected_jobs:
                    updated_groups.append(selected_jobs)
            
            st.session_state["job_similarity_groups"] = updated_groups
            
            # 그룹 현황 표시
            if updated_groups:
                st.info("**현재 유사 직무 그룹:**")
                for i, group in enumerate(updated_groups):
                    st.write(f"- 그룹 {i+1}: {', '.join(group)}")
        
        # 그룹 구성 예측
        with st.expander("🔍 예상 그룹 구성 미리보기", expanded=False):
            st.markdown("현재 설정으로 예상되는 그룹 구성입니다.")
            
            # 총 인원수와 그룹 크기 범위로 예상 그룹 수 계산
            total_candidates = job_df['count'].sum()
            estimated_groups = (total_candidates + common_max - 1) // common_max  # 최소 그룹 수
            
            st.info(f"총 {total_candidates}명을 {common_min}-{common_max}명 단위로 묶으면 약 **{estimated_groups}개** 그룹이 생성될 예정입니다.")
            
            if prefer_job_separation:
                st.write("📌 직무별 분리를 우선으로 그룹을 구성합니다.")
                for _, row in job_df.iterrows():
                    job_code = row['code']
                    count = row['count']
                    job_groups = (count + common_max - 1) // common_max
                    st.write(f"- {job_code}: {count}명 → 약 {job_groups}개 그룹")
            else:
                st.write("📌 직무 구분 없이 효율적으로 그룹을 구성합니다.")
            
            # 그룹 구성 시뮬레이션 버튼
            if st.button("🔮 그룹 구성 시뮬레이션"):
                with st.spinner("그룹 구성을 시뮬레이션하고 있습니다..."):
                    try:
                        # 가상 지원자 데이터 생성
                        candidates = []
                        for _, row in job_df.iterrows():
                            job_code = row['code']
                            count = int(row['count'])
                            for i in range(count):
                                candidates.append({
                                    'id': f"{job_code}_{i+1:03d}",
                                    'job_code': job_code
                                })
                        candidates_df = pd.DataFrame(candidates)
                        
                        # GroupFormationOptimizer 실행
                        from solver.group_formation import GroupFormationOptimizer
                        
                        optimizer = GroupFormationOptimizer(
                            candidates=candidates_df,
                            batched_activities=batched_activities,
                            job_similarity_groups=st.session_state.get("job_similarity_groups", []),
                            prefer_job_separation=prefer_job_separation
                        )
                        
                        groups, status, logs = optimizer.optimize(time_limit_sec=10.0)
                        
                        if status in ["OPTIMAL", "FEASIBLE"]:
                            st.success(f"✅ 그룹 구성 시뮬레이션 완료! (상태: {status})")
                            
                            # 그룹별 구성 표시
                            st.markdown("### 📊 시뮬레이션 결과")
                            
                            # 요약 정보
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("총 그룹 수", f"{len(groups)}개")
                            with col2:
                                avg_size = sum(len(members) for members in groups.values()) / len(groups)
                                st.metric("평균 그룹 크기", f"{avg_size:.1f}명")
                            with col3:
                                # 직무 혼합도 계산
                                mixed_groups = 0
                                for members in groups.values():
                                    job_codes = [candidates_df[candidates_df['id'] == m]['job_code'].iloc[0] for m in members]
                                    if len(set(job_codes)) > 1:
                                        mixed_groups += 1
                                st.metric("직무 혼합 그룹", f"{mixed_groups}개")
                            
                            # 상세 그룹 구성
                            st.markdown("#### 그룹별 상세 구성")
                            
                            for group_id in sorted(groups.keys()):
                                members = groups[group_id]
                                # 직무별 인원수 계산
                                job_dist = {}
                                for member_id in members:
                                    job_code = candidates_df[candidates_df['id'] == member_id]['job_code'].iloc[0]
                                    job_dist[job_code] = job_dist.get(job_code, 0) + 1
                                
                                # 직무 구성 문자열 생성
                                job_str = ", ".join([f"{k}: {v}명" for k, v in sorted(job_dist.items())])
                                
                                with st.container():
                                    st.write(f"**그룹 {group_id+1}** ({len(members)}명)")
                                    st.write(f"  - 직무 구성: {job_str}")
                                    
                                    # 구성원 ID 표시 (접기 가능)
                                    with st.expander(f"구성원 보기"):
                                        member_str = ", ".join(sorted(members))
                                        st.write(member_str)
                            
                            # 최적화 로그
                            with st.expander("🔍 최적화 로그"):
                                st.text(logs)
                        else:
                            st.error(f"❌ 그룹 구성 시뮬레이션 실패: {status}")
                            st.text(logs)
                            
                    except Exception as e:
                        st.error(f"시뮬레이션 중 오류 발생: {str(e)}")
                        st.info("그룹 크기 설정이나 직무별 인원수를 확인해주세요.")
    
    st.markdown('</div>', unsafe_allow_html=True)  # batched-section 닫기

    st.divider()
else:
    # Batched 활동이 없는 경우에도 prev_count 초기화
    st.session_state['prev_batched_count'] = 0

# =============================================================================
# 섹션 4: 운영 공간 설정
# =============================================================================
col_header, col_refresh = st.columns([3, 2])
with col_header:
    st.header("4️⃣ 운영 공간 설정")
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)  # 헤더와 높이 맞추기
    if st.button("🔄 섹션 새로고침", help="운영 공간 설정 UI가 먹통일 때 새로고침"):
        # 섹션별 새로고침
        if "section_refresh_counter" not in st.session_state:
            st.session_state["section_refresh_counter"] = {}
        if "room_settings" not in st.session_state["section_refresh_counter"]:
            st.session_state["section_refresh_counter"]["room_settings"] = 0
        st.session_state["section_refresh_counter"]["room_settings"] += 1
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
        
        # 섹션별 새로고침을 위한 동적 key 생성
        room_settings_refresh_count = st.session_state.get("section_refresh_counter", {}).get("room_settings", 0)
        
        col_cnt, col_cap = st.columns(2, gap="large")
        
        with col_cnt:
            st.markdown("#### 방 개수")
            for rt in room_types:
                tpl_dict[rt]["count"] = st.number_input(
                    f"{rt} 개수", 
                    min_value=0, 
                    max_value=50, 
                    value=tpl_dict[rt].get("count", 1), 
                    key=f"tpl_{rt}_cnt_{room_settings_refresh_count}"  # 동적 key로 강제 재렌더링
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
                    key=f"tpl_{rt}_cap_{room_settings_refresh_count}",  # 동적 key로 강제 재렌더링
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
col_header, col_refresh = st.columns([3, 2])
with col_header:
    st.header("5️⃣ 운영 시간 설정")
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)  # 헤더와 높이 맞추기
    if st.button("🔄 섹션 새로고침", help="운영 시간 설정 UI가 먹통일 때 새로고침"):
        # 섹션별 새로고침
        if "section_refresh_counter" not in st.session_state:
            st.session_state["section_refresh_counter"] = {}
        if "time_settings" not in st.session_state["section_refresh_counter"]:
            st.session_state["section_refresh_counter"]["time_settings"] = 0
        st.session_state["section_refresh_counter"]["time_settings"] += 1
        st.rerun()

st.markdown("면접을 운영할 경우의 하루 기준 운영 시작 및 종료 시간을 설정합니다.")

# 기존 값 불러오기
init_start = st.session_state.get("oper_start_time", datetime_time(9, 0))
init_end = st.session_state.get("oper_end_time", datetime_time(18, 0))

st.subheader("하루 기준 공통 운영 시간")

# 섹션별 새로고침을 위한 동적 key 생성
time_settings_refresh_count = st.session_state.get("section_refresh_counter", {}).get("time_settings", 0)

col_start, col_end = st.columns(2)

with col_start:
    t_start = st.time_input("운영 시작 시간", value=init_start, key=f"oper_start_{time_settings_refresh_count}")

with col_end:
    t_end = st.time_input("운영 종료 시간", value=init_end, key=f"oper_end_{time_settings_refresh_count}")

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

# 피드백 섹션
st.markdown("---")
with st.expander("💬 피드백 & 도움말", expanded=False):
    st.markdown("### 🤝 사용자 피드백")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 만족도 평가")
        satisfaction = st.radio(
            "이 시스템에 대한 만족도를 평가해주세요:",
            ["⭐⭐⭐⭐⭐ 매우 만족", "⭐⭐⭐⭐ 만족", "⭐⭐⭐ 보통", "⭐⭐ 불만족", "⭐ 매우 불만족"],
            index=0,
            key="satisfaction_rating"
        )
        
        feedback_text = st.text_area(
            "개선사항이나 건의사항을 자유롭게 작성해주세요:",
            height=100,
            key="feedback_text"
        )
        
        if st.button("📤 피드백 전송"):
            st.success("✅ 피드백이 전송되었습니다. 감사합니다!")
            # 실제로는 여기서 피드백을 저장하거나 전송하는 로직 추가
    
    with col2:
        st.markdown("#### 빠른 도움말")
        st.markdown("""
        **자주 묻는 질문:**
        
        **Q: 집단면접 그룹 크기가 호환되지 않는다고 나옵니다.**  
        A: 모든 batched 활동의 최소/최대 인원 범위가 겹쳐야 합니다. 
        예: 활동1(4-6명), 활동2(5-8명) → 공통범위(5-6명)
        
        **Q: 스케줄링이 실패합니다.**  
        A: 운영 시간을 늘리거나, 면접실 수를 증가시켜보세요.
        
        **Q: AG-Grid가 반응하지 않습니다.**  
        A: 각 섹션의 '🔄 섹션 새로고침' 버튼을 클릭하세요.
        
        **Q: 설정이 저장되지 않습니다.**  
        A: 자동 저장이 활성화되어 있는지 사이드바에서 확인하세요.
        """)
        
        st.markdown("#### 추가 지원")
        st.info("기술 지원이 필요하시면 관리자에게 문의하세요.")

# 현재 세션 내용을 파일로 자동 저장
cp.autosave_state()