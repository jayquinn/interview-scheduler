import pandas as pd
from datetime import datetime, time, timedelta
from solver.api import solve_for_days_v2

def test_simple_scheduling():
    print("=== 간단한 스케줄링 테스트 ===")
    
    # 기본 활동 템플릿
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 직무 매핑
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [20],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    # 방 계획
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [2],
        "발표면접실_count": [2],
        "발표면접실_cap": [1]
    })
    
    # 운영 시간
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    # 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 5, "adjacent": True}
    ])
    
    # 단일 날짜 직무 설정
    tomorrow = datetime.now().date() + timedelta(days=1)
    single_date_jobs = [
        {"code": "JOB01", "count": 20}
    ]
    
    # cfg_ui 구성
    cfg_ui = {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'single_date_jobs': single_date_jobs,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }
    
    print("=== 데이터 확인 ===")
    for key, value in cfg_ui.items():
        if isinstance(value, pd.DataFrame):
            print(f"{key}: DataFrame ({len(value)} rows)")
            if not value.empty:
                print(f"  컬럼: {list(value.columns)}")
                print(value.to_string())
        elif isinstance(value, list):
            print(f"{key}: List ({len(value)} items) - {value}")
        else:
            print(f"{key}: {type(value)} - {value}")
        print()
    
    # 스케줄링 실행
    print("=== 스케줄링 실행 ===")
    try:
        status, result_df, logs, limit = solve_for_days_v2(cfg_ui, debug=True)
        
        print(f"결과 상태: {status}")
        print(f"일일 한계: {limit}")
        
        if result_df is not None and not result_df.empty:
            print(f"결과 DataFrame: {len(result_df)} rows")
            print("컬럼:", list(result_df.columns))
            print("\n결과 샘플:")
            print(result_df.head().to_string())
        else:
            print("결과 DataFrame 없음")
        
        if logs:
            print("\n=== 로그 ===")
            print(logs)
            
        return status == "SUCCESS"
            
    except Exception as e:
        print(f"스케줄링 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_scheduling()
    print(f"\n테스트 결과: {'성공' if success else '실패'}") 