import pandas as pd
from datetime import datetime, time, timedelta
from solver.api import solve_for_days_v2

def test_fixed_scheduling():
    print("=== 수정된 스케줄링 테스트 ===")
    
    # 기본 활동 템플릿 (방 용량 문제 해결)
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 10, 1],  # 발표준비실 용량을 10명으로 증가
    })
    
    # 직무 매핑
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [20],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    # 방 계획 (발표준비실 용량 증가)
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [2],  # 방 개수 증가
        "발표준비실_cap": [10],   # 용량 증가
        "발표면접실_count": [3],  # 방 개수 증가
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
    
    print("=== 수정된 데이터 확인 ===")
    print("활동 설정:")
    print(activities[['activity', 'mode', 'duration_min', 'min_cap', 'max_cap']].to_string())
    print("\n방 계획:")
    print(room_plan.to_string())
    
    # 스케줄링 실행
    print("\n=== 스케줄링 실행 ===")
    try:
        status, result_df, logs, limit = solve_for_days_v2(cfg_ui, debug=True)
        
        print(f"결과 상태: {status}")
        print(f"일일 한계: {limit}")
        
        if result_df is not None and not result_df.empty:
            print(f"결과 DataFrame: {len(result_df)} rows")
            print("컬럼:", list(result_df.columns))
            print("\n결과 샘플:")
            print(result_df.head(10).to_string())
            
            # 성공률 계산
            total_expected = 20 * 3  # 20명 * 3활동
            actual_scheduled = len(result_df)
            success_rate = (actual_scheduled / total_expected) * 100
            print(f"\n성공률: {success_rate:.1f}% ({actual_scheduled}/{total_expected})")
            
        else:
            print("결과 DataFrame 없음")
        
        if logs:
            print("\n=== 주요 로그 (마지막 20줄) ===")
            log_lines = logs.split('\n')
            for line in log_lines[-20:]:
                if line.strip():
                    print(line)
            
        return status == "SUCCESS"
            
    except Exception as e:
        print(f"스케줄링 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_minimal_scheduling():
    """최소한의 설정으로 테스트"""
    print("\n=== 최소 설정 테스트 ===")
    
    # 토론면접만 사용 (가장 간단한 batched 활동)
    activities = pd.DataFrame({
        "use": [True, False, False],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 직무 매핑 (토론면접만)
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [20],
        "토론면접": [True],
        "발표준비": [False],
        "발표면접": [False]
    })
    
    # 방 계획
    room_plan = pd.DataFrame({
        "토론면접실_count": [3],
        "토론면접실_cap": [6]
    })
    
    # 운영 시간
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    # 선후행 제약 없음
    precedence = pd.DataFrame()
    
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
    
    print("토론면접만 사용, 20명 처리")
    
    try:
        status, result_df, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
        
        print(f"결과 상태: {status}")
        print(f"일일 한계: {limit}")
        
        if result_df is not None and not result_df.empty:
            print(f"성공! {len(result_df)}개 스케줄 생성")
            return True
        else:
            print("실패: 결과 없음")
            return False
            
    except Exception as e:
        print(f"오류: {str(e)}")
        return False

if __name__ == "__main__":
    print("1. 전체 활동 테스트")
    success1 = test_fixed_scheduling()
    
    print("\n" + "="*50)
    print("2. 최소 설정 테스트")
    success2 = test_minimal_scheduling()
    
    print(f"\n최종 결과:")
    print(f"전체 활동 테스트: {'성공' if success1 else '실패'}")
    print(f"최소 설정 테스트: {'성공' if success2 else '실패'}") 