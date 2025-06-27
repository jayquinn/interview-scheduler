import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2
from solver.individual_scheduler import IndividualScheduler
from solver.types import Activity, Room, Applicant, PrecedenceRule, ActivityType
import copy

def test_smart_grouping_fix():
    print("=== 🧠 스마트 그룹핑 수정 테스트 ===")
    print("핵심 아이디어: 발표준비 그룹을 발표면접실 수에 맞춰 조정")
    
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
    
    print("\n=== 📊 현재 방식 결과 ===")
    status, result_current, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
    
    if result_current is not None and not result_current.empty:
        violations_current = analyze_precedence_violations(result_current)
        success_rate_current = (6 - len(violations_current)) / 6 * 100
        print(f"현재 방식 성공률: {success_rate_current:.1f}% ({6-len(violations_current)}/6명)")
        
        print("\n현재 그룹핑 패턴:")
        analyze_grouping_pattern(result_current)
    
    print("\n=== 💡 스마트 그룹핑 아이디어 분석 ===")
    
    print("🔍 현재 문제점:")
    print("1. 발표준비실 1개(2명 용량) → 3개 그룹 (2명, 2명, 2명)")
    print("2. 발표면접실 2개(1명 용량) → 동시에 2명만 처리 가능")
    print("3. 그룹 1이 끝나고 5분 후 → 발표면접실 2개 모두 사용")
    print("4. 그룹 2가 끝나고 5분 후 → 발표면접실이 이미 점유됨!")
    
    print("\n🧠 해결 아이디어:")
    print("1. 발표준비 그룹 크기를 발표면접실 수(2개)에 맞춤")
    print("2. 즉, 2명씩 3그룹 → 2명씩 3그룹이지만 시간 간격 조정")
    print("3. 또는 그룹 크기를 동적으로 조정")
    
    # 아이디어 테스트: 발표준비실 용량을 1명으로 줄여서 더 작은 그룹 만들기
    print("\n🔧 테스트 1: 발표준비실 용량 1명 (더 작은 그룹)")
    room_plan_small = room_plan.copy()
    room_plan_small.loc[0, "발표준비실_cap"] = 1
    
    cfg_ui_small = copy.deepcopy(cfg_ui)
    cfg_ui_small['room_plan'] = room_plan_small
    
    status_small, result_small, logs_small, limit_small = solve_for_days_v2(cfg_ui_small, debug=False)
    
    if result_small is not None and not result_small.empty:
        violations_small = analyze_precedence_violations(result_small)
        success_rate_small = (6 - len(violations_small)) / 6 * 100
        print(f"작은 그룹 성공률: {success_rate_small:.1f}% ({6-len(violations_small)}/6명)")
        analyze_grouping_pattern(result_small)
    
    # 아이디어 테스트: 발표준비 시간을 더 길게 해서 시간 여유 확보
    print("\n🔧 테스트 2: 발표준비 시간 길게 (10분)")
    activities_long = activities.copy()
    activities_long.loc[1, "duration_min"] = 10
    
    cfg_ui_long = copy.deepcopy(cfg_ui)
    cfg_ui_long['activities'] = activities_long
    
    status_long, result_long, logs_long, limit_long = solve_for_days_v2(cfg_ui_long, debug=False)
    
    if result_long is not None and not result_long.empty:
        violations_long = analyze_precedence_violations(result_long)
        success_rate_long = (6 - len(violations_long)) / 6 * 100
        print(f"긴 발표준비 성공률: {success_rate_long:.1f}% ({6-len(violations_long)}/6명)")
        analyze_grouping_pattern(result_long)
    
    # 아이디어 테스트: gap_min을 0으로 해서 즉시 시작
    print("\n🔧 테스트 3: 발표준비 직후 즉시 발표면접 (gap=0)")
    precedence_zero = precedence.copy()
    precedence_zero.loc[0, "gap_min"] = 0
    
    cfg_ui_zero = copy.deepcopy(cfg_ui)
    cfg_ui_zero['precedence'] = precedence_zero
    
    status_zero, result_zero, logs_zero, limit_zero = solve_for_days_v2(cfg_ui_zero, debug=False)
    
    if result_zero is not None and not result_zero.empty:
        violations_zero = analyze_precedence_violations_zero(result_zero)
        success_rate_zero = (6 - len(violations_zero)) / 6 * 100
        print(f"즉시 시작 성공률: {success_rate_zero:.1f}% ({6-len(violations_zero)}/6명)")
        analyze_grouping_pattern(result_zero)
    
    print("\n=== 📈 결과 비교 ===")
    print(f"기본 설정 (2명 그룹, 5분 간격): {success_rate_current:.1f}%")
    if 'success_rate_small' in locals():
        print(f"작은 그룹 (1명 그룹, 5분 간격): {success_rate_small:.1f}%")
    if 'success_rate_long' in locals():
        print(f"긴 발표준비 (2명 그룹, 10분 발표준비): {success_rate_long:.1f}%")
    if 'success_rate_zero' in locals():
        print(f"즉시 시작 (2명 그룹, 0분 간격): {success_rate_zero:.1f}%")
    
    print("\n=== 🎯 핵심 인사이트 ===")
    print("문제의 근본 원인은 '시간 충돌'이 아니라 '방 부족'입니다.")
    print("발표준비 그룹이 순차 처리되면서 발표면접실이 부족해집니다.")
    print("해결책:")
    print("1. 발표면접실 증설 (66.7% → 100% 예상)")
    print("2. 스케줄링 알고리즘 개선 (백트래킹)")
    print("3. 그룹 크기 동적 조정")

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

def analyze_precedence_violations_zero(result):
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
            
            if abs(gap - 0) > 0.1:  # 0분 간격 기대
                violations.append({
                    'applicant': applicant_id,
                    'gap': gap,
                    'expected': 0
                })
    
    return violations

def analyze_grouping_pattern(result):
    prep_data = result[result['activity_name'] == '발표준비']
    interview_data = result[result['activity_name'] == '발표면접']
    
    if not prep_data.empty:
        prep_groups = prep_data.groupby('start_time')['applicant_id'].apply(list).to_dict()
        print(f"발표준비 그룹: {len(prep_groups)}개")
        for i, (start_time, applicants) in enumerate(prep_groups.items()):
            print(f"  그룹 {i+1}: {start_time} - {len(applicants)}명 {applicants}")
    
    if not interview_data.empty:
        interview_groups = interview_data.groupby('start_time')['applicant_id'].apply(list).to_dict()
        print(f"발표면접 그룹: {len(interview_groups)}개")
        for i, (start_time, applicants) in enumerate(interview_groups.items()):
            print(f"  그룹 {i+1}: {start_time} - {len(applicants)}명 {applicants}")

if __name__ == "__main__":
    test_smart_grouping_fix() 