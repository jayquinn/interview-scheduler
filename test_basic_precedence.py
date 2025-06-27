import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def test_basic_precedence():
    print("=== 🔍 기본 선후행 제약 테스트 ===")
    print("디폴트 설정 (gap_min=0, adjacent=True)")
    
    # 기본 디폴트 설정
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [2],
        "발표면접실_count": [2],
        "발표면접실_cap": [1]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    cfg_ui = {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }
    
    print("\n=== 설정 요약 ===")
    print(f"지원자: {job_acts_map['count'].sum()}명")
    print(f"토론면접실: {room_plan['토론면접실_count'].iloc[0]}개 (각 {room_plan['토론면접실_cap'].iloc[0]}명)")
    print(f"발표준비실: {room_plan['발표준비실_count'].iloc[0]}개 (각 {room_plan['발표준비실_cap'].iloc[0]}명)")
    print(f"발표면접실: {room_plan['발표면접실_count'].iloc[0]}개 (각 {room_plan['발표면접실_cap'].iloc[0]}명)")
    print(f"선후행 제약: 발표준비 → 발표면접 (gap_min={precedence['gap_min'].iloc[0]}, adjacent={precedence['adjacent'].iloc[0]})")
    
    try:
        print("\n=== 스케줄링 실행 ===")
        result = solve_for_days_v2(cfg_ui)
        
        if isinstance(result, tuple) and len(result) >= 2:
            status, schedule, logs, limit = result
            
            print(f"상태: {status}")
            if schedule is not None and not schedule.empty:
                print(f"결과: {len(schedule)}개 항목")
                print(f"컬럼: {list(schedule.columns)}")
                
                # 샘플 데이터 출력
                print("\n=== 샘플 결과 ===")
                if len(schedule) > 0:
                    sample = schedule.head(3)
                    for _, row in sample.iterrows():
                        print(f"  {row.get('applicant_id', 'N/A')} - {row.get('activity_name', 'N/A')} - {row.get('start_time', 'N/A')} ~ {row.get('end_time', 'N/A')}")
            else:
                print("❌ 결과 없음")
                
            if logs:
                print(f"\n=== 로그 ===")
                print(logs[:500] + "..." if len(logs) > 500 else logs)
        else:
            print("❌ 잘못된 결과 형식")
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_precedence() 