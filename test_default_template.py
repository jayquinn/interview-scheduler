import sys
import pandas as pd
from datetime import datetime, time, timedelta
import logging

# Mock streamlit session state
class MockSessionState:
    def __init__(self):
        self.data = {}
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __contains__(self, key):
        return key in self.data

# Mock streamlit
class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()

# Setup mock streamlit
sys.modules['streamlit'] = MockStreamlit()
import streamlit as st

# Import after mocking
from app import init_session_states
from solver.api import solve_for_days_v2

def test_default_template():
    print("=== 기본 템플릿 테스트 시작 ===")
    
    # 초기화 실행
    init_session_states()
    
    # 현재 기본 템플릿 확인
    print('\n=== 기본 활동 템플릿 ===')
    activities = st.session_state.get('activities')
    if activities is not None:
        print(activities.to_string())
        print(f"활동 수: {len(activities)}")
        print(f"사용 가능한 활동: {activities[activities['use'] == True]['activity'].tolist()}")
    else:
        print('활동 데이터 없음')
    
    print('\n=== 기본 직무 매핑 ===')
    job_acts_map = st.session_state.get('job_acts_map')
    if job_acts_map is not None:
        print(job_acts_map.to_string())
    else:
        print('직무 매핑 데이터 없음')
    
    print('\n=== 기본 방 계획 ===')
    room_plan = st.session_state.get('room_plan')
    if room_plan is not None:
        print(room_plan.to_string())
    else:
        print('방 계획 데이터 없음')
    
    print('\n=== 기본 운영 시간 ===')
    oper_window = st.session_state.get('oper_window')
    if oper_window is not None:
        print(oper_window.to_string())
    else:
        print('운영 시간 데이터 없음')
    
    # 새로운 UI 구조에 맞춰 기본 데이터 설정
    print('\n=== 새로운 UI 구조용 데이터 설정 ===')
    
    # 단일 날짜 모드로 기본 설정
    tomorrow = datetime.now().date() + timedelta(days=1)
    st.session_state["interview_dates"] = [tomorrow]
    st.session_state["interview_date"] = tomorrow
    
    # 단일 날짜 직무 설정
    st.session_state["single_date_jobs"] = [
        {"code": "JOB01", "count": 20}
    ]
    
    print(f"면접 날짜: {tomorrow}")
    print(f"직무 설정: {st.session_state['single_date_jobs']}")
    
    # 스케줄링 테스트
    print('\n=== 스케줄링 테스트 ===')
    
    try:
        # cfg_ui 구성
        cfg_ui = {
            'activities': st.session_state.get('activities'),
            'job_acts_map': st.session_state.get('job_acts_map'),
            'room_plan': st.session_state.get('room_plan'),
            'oper_window': st.session_state.get('oper_window'),
            'precedence': st.session_state.get('precedence', pd.DataFrame()),
            'single_date_jobs': st.session_state.get('single_date_jobs', []),
            'interview_dates': st.session_state.get('interview_dates', []),
            'interview_date': st.session_state.get('interview_date')
        }
        
        print("cfg_ui 키들:", list(cfg_ui.keys()))
        
        # 각 데이터 확인
        for key, value in cfg_ui.items():
            if isinstance(value, pd.DataFrame):
                print(f"{key}: DataFrame ({len(value)} rows)")
                if not value.empty:
                    print(f"  컬럼: {list(value.columns)}")
            elif isinstance(value, list):
                print(f"{key}: List ({len(value)} items)")
            else:
                print(f"{key}: {type(value)} - {value}")
        
        # 스케줄링 실행
        print("\n스케줄링 실행 중...")
        status, result_df, logs, limit = solve_for_days_v2(cfg_ui, debug=True)
        
        print(f"결과 상태: {status}")
        print(f"일일 한계: {limit}")
        print(f"로그 길이: {len(logs) if logs else 0}")
        
        if result_df is not None and not result_df.empty:
            print(f"결과 DataFrame: {len(result_df)} rows")
            print("컬럼:", list(result_df.columns))
            print(result_df.head().to_string())
        else:
            print("결과 DataFrame 없음")
        
        if logs:
            print("\n=== 로그 ===")
            print(logs)
            
    except Exception as e:
        print(f"스케줄링 오류: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_default_template() 