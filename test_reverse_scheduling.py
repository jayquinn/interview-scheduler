import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2
from solver.individual_scheduler import IndividualScheduler
from solver.types import Activity, Room, PrecedenceRule
import copy

def test_reverse_scheduling():
    print("=== 🔄 역방향 스케줄링 테스트 ===")
    
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
    
    print("\n=== 🧠 역방향 스케줄링 아이디어 ===")
    print("1. 토론면접을 먼저 스케줄링 (batched)")
    print("2. 발표면접 시간을 최적 배치 (individual)")
    print("3. 발표준비 시간을 발표면접 시간에서 역산 (precedence 고려)")
    
    # 현재 방식 결과
    print("\n=== 📊 현재 방식 결과 ===")
    status, result_current, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
    
    if result_current is not None and not result_current.empty:
        violations_current = analyze_precedence_violations(result_current)
        success_rate_current = (6 - len(violations_current)) / 6 * 100
        print(f"현재 방식 성공률: {success_rate_current:.1f}% ({6-len(violations_current)}/6명)")
        
        for violation in violations_current:
            print(f"  위반: {violation['applicant']} - {violation['gap']:.1f}분 간격")
    
    print("\n=== 🔧 역방향 스케줄링 구현 시도 ===")
    print("아이디어: 스케줄링 순서를 변경해보겠습니다")
    
    # 방법 1: 활동 순서 변경
    activities_reversed = activities.copy()
    # individual -> parallel -> batched 순서로 변경
    activities_reversed = activities_reversed.iloc[[2, 1, 0]]  # 발표면접, 발표준비, 토론면접
    
    cfg_ui_reversed = copy.deepcopy(cfg_ui)
    cfg_ui_reversed['activities'] = activities_reversed
    
    print("\n=== 🔄 순서 변경 테스트 (발표면접 → 발표준비 → 토론면접) ===")
    status_rev, result_rev, logs_rev, limit_rev = solve_for_days_v2(cfg_ui_reversed, debug=False)
    
    if result_rev is not None and not result_rev.empty:
        violations_rev = analyze_precedence_violations(result_rev)
        success_rate_rev = (6 - len(violations_rev)) / 6 * 100
        print(f"순서 변경 성공률: {success_rate_rev:.1f}% ({6-len(violations_rev)}/6명)")
        
        for violation in violations_rev:
            print(f"  위반: {violation['applicant']} - {violation['gap']:.1f}분 간격")
    else:
        print("순서 변경 실패")
    
    print("\n=== 💡 추가 아이디어: 스마트 그룹핑 ===")
    print("발표준비 그룹을 발표면접 가용성에 맞춰 조정")

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
                    'prep_end': prep_end,
                    'interview_start': interview_start,
                    'gap': gap,
                    'expected': 5
                })
    
    return violations

if __name__ == "__main__":
    test_reverse_scheduling() 