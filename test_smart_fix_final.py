import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def test_smart_fix():
    print("=== 🚀 스마트 그룹핑 수정 후 테스트 ===")
    
    # 기본 설정
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
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 5, "adjacent": True}
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
    
    print("\n=== 📊 수정 후 결과 ===")
    status, result, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
    
    if result is not None and not result.empty:
        violations = analyze_precedence_violations(result)
        success_rate = (6 - len(violations)) / 6 * 100
        print(f"수정 후 성공률: {success_rate:.1f}% ({6-len(violations)}/6명)")
        
        print("\n📅 스케줄 상세:")
        analyze_detailed_schedule(result)
        
        print("\n🚨 위반 사항:")
        for violation in violations:
            print(f"  {violation['applicant']}: {violation['gap']:.1f}분 간격 (예상: 5분)")
    
    else:
        print("❌ 스케줄링 실패")

def analyze_precedence_violations(result):
    violations = []
    
    for applicant_id in sorted(result['applicant_id'].unique()):
        applicant_data = result[result['applicant_id'] == applicant_id]
        
        prep_data = applicant_data[applicant_data['activity_name'] == '발표준비']
        interview_data = applicant_data[applicant_data['activity_name'] == '발표면접']
        
        if not prep_data.empty and not interview_data.empty:
            prep_end = prep_data.iloc[0]['end_time']
            interview_start = interview_data.iloc[0]['start_time']
            
            # 시간 차이 계산
            if hasattr(prep_end, 'total_seconds'):
                prep_end_min = prep_end.total_seconds() / 60
            else:
                prep_end_min = prep_end.hour * 60 + prep_end.minute
            
            if hasattr(interview_start, 'total_seconds'):
                interview_start_min = interview_start.total_seconds() / 60
            else:
                interview_start_min = interview_start.hour * 60 + interview_start.minute
            
            gap = interview_start_min - prep_end_min
            
            if abs(gap - 5) > 0.1:
                violations.append({
                    'applicant': applicant_id,
                    'gap': gap,
                    'expected': 5
                })
    
    return violations

def analyze_detailed_schedule(result):
    for applicant_id in sorted(result['applicant_id'].unique()):
        applicant_data = result[result['applicant_id'] == applicant_id]
        print(f"\n{applicant_id}:")
        
        for _, row in applicant_data.iterrows():
            print(f"  {row['activity_name']}: {row['start_time']} ~ {row['end_time']} ({row['room_name']})")
    
    print("\n📊 방별 사용 현황:")
    for room_name in sorted(result['room_name'].unique()):
        room_data = result[result['room_name'] == room_name]
        print(f"\n{room_name}:")
        
        for _, row in room_data.iterrows():
            print(f"  {row['start_time']} ~ {row['end_time']}: {row['applicant_id']} ({row['activity_name']})")

if __name__ == "__main__":
    test_smart_fix() 