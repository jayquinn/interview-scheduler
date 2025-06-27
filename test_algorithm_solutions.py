import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def create_base_config():
    """기본 디폴트 설정"""
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
    
    return {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }

def analyze_success_rate(result, test_name):
    """성공률 분석"""
    if not isinstance(result, tuple) or len(result) < 2:
        return 0, f"{test_name}: 결과 형식 오류"
    
    status, schedule, logs, limit = result
    
    if status not in ["SUCCESS", "PARTIAL"] or schedule is None or schedule.empty:
        return 0, f"{test_name}: 스케줄링 실패"
    
    applicants = schedule['applicant_id'].unique()
    success_count = 0
    
    for applicant in applicants:
        app_schedule = schedule[schedule['applicant_id'] == applicant]
        prep_data = app_schedule[app_schedule['activity_name'] == '발표준비']
        interview_data = app_schedule[app_schedule['activity_name'] == '발표면접']
        
        if prep_data.empty or interview_data.empty:
            continue
        
        prep_end = prep_data.iloc[0]['end_time']
        interview_start = interview_data.iloc[0]['start_time']
        
        # 시간 차이 계산
        if hasattr(prep_end, 'hour'):
            prep_end_min = prep_end.hour * 60 + prep_end.minute
        else:
            prep_end_min = prep_end.total_seconds() / 60
            
        if hasattr(interview_start, 'hour'):
            interview_start_min = interview_start.hour * 60 + interview_start.minute
        else:
            interview_start_min = interview_start.total_seconds() / 60
        
        gap = interview_start_min - prep_end_min
        
        if abs(gap) < 0.1:  # 0분 간격 (연속배치)
            success_count += 1
    
    success_rate = (success_count / len(applicants)) * 100 if len(applicants) > 0 else 0
    return success_rate, f"{test_name}: {success_rate:.1f}% ({success_count}/{len(applicants)}명)"

def test_solution_1_individual_mode():
    """해결안 1: 발표준비를 individual 모드로 변경"""
    print("\n=== 💡 해결안 1: 발표준비 → individual 모드 ===")
    print("아이디어: parallel → individual로 변경하여 1명씩 처리")
    
    cfg = create_base_config()
    cfg['activities'].loc[1, 'mode'] = 'individual'  # 발표준비를 individual로
    
    try:
        result = solve_for_days_v2(cfg)
        return analyze_success_rate(result, "해결안 1")
    except Exception as e:
        return 0, f"해결안 1: 오류 - {e}"

def test_solution_2_batched_mode():
    """해결안 2: 발표준비를 batched 모드로 변경"""
    print("\n=== 💡 해결안 2: 발표준비 → batched 모드 ===")
    print("아이디어: parallel → batched로 변경하여 그룹 단위 처리")
    
    cfg = create_base_config()
    cfg['activities'].loc[1, 'mode'] = 'batched'  # 발표준비를 batched로
    cfg['activities'].loc[1, 'min_cap'] = 2  # 최소 2명
    cfg['activities'].loc[1, 'max_cap'] = 2  # 최대 2명 (발표면접실 수와 맞춤)
    
    try:
        result = solve_for_days_v2(cfg)
        return analyze_success_rate(result, "해결안 2")
    except Exception as e:
        return 0, f"해결안 2: 오류 - {e}"

def test_solution_3_room_capacity():
    """해결안 3: 발표준비실 용량을 1명으로 축소"""
    print("\n=== 💡 해결안 3: 발표준비실 용량 축소 ===")
    print("아이디어: 방 용량 2명 → 1명으로 축소하여 더 작은 그룹 생성")
    
    cfg = create_base_config()
    cfg['room_plan'].loc[0, '발표준비실_cap'] = 1  # 용량을 1명으로
    
    try:
        result = solve_for_days_v2(cfg)
        return analyze_success_rate(result, "해결안 3")
    except Exception as e:
        return 0, f"해결안 3: 오류 - {e}"

def test_solution_4_activity_order():
    """해결안 4: 활동 순서 변경 (individual 먼저)"""
    print("\n=== 💡 해결안 4: 활동 순서 변경 ===")
    print("아이디어: 발표면접 → 발표준비 순서로 변경")
    
    cfg = create_base_config()
    # 활동 순서 바꾸기
    activities_reordered = cfg['activities'].copy()
    activities_reordered.loc[1, 'activity'] = '발표면접'
    activities_reordered.loc[1, 'mode'] = 'individual'
    activities_reordered.loc[1, 'duration_min'] = 15
    activities_reordered.loc[1, 'room_type'] = '발표면접실'
    activities_reordered.loc[1, 'max_cap'] = 1
    
    activities_reordered.loc[2, 'activity'] = '발표준비'
    activities_reordered.loc[2, 'mode'] = 'parallel'
    activities_reordered.loc[2, 'duration_min'] = 5
    activities_reordered.loc[2, 'room_type'] = '발표준비실'
    activities_reordered.loc[2, 'max_cap'] = 2
    
    cfg['activities'] = activities_reordered
    
    # 선후행 제약도 변경
    cfg['precedence'].loc[0, 'predecessor'] = '발표면접'
    cfg['precedence'].loc[0, 'successor'] = '발표준비'
    
    try:
        result = solve_for_days_v2(cfg)
        return analyze_success_rate(result, "해결안 4")
    except Exception as e:
        return 0, f"해결안 4: 오류 - {e}"

def test_solution_5_combined_activity():
    """해결안 5: 발표준비+발표면접을 하나의 활동으로 통합"""
    print("\n=== 💡 해결안 5: 활동 통합 ===")
    print("아이디어: 발표준비+발표면접을 '발표세션' 하나로 통합")
    
    cfg = create_base_config()
    
    # 새로운 활동 구성
    new_activities = pd.DataFrame({
        "use": [True, True],
        "activity": ["토론면접", "발표세션"],
        "mode": ["batched", "individual"],
        "duration_min": [30, 20],  # 발표준비 5분 + 발표면접 15분
        "room_type": ["토론면접실", "발표면접실"],
        "min_cap": [4, 1],
        "max_cap": [6, 1],
    })
    
    cfg['activities'] = new_activities
    
    # 직무별 활동 매핑 업데이트
    cfg['job_acts_map'] = pd.DataFrame({
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표세션": [True]
    })
    
    # 선후행 제약 제거
    cfg['precedence'] = pd.DataFrame()
    
    try:
        result = solve_for_days_v2(cfg)
        return analyze_success_rate(result, "해결안 5")
    except Exception as e:
        return 0, f"해결안 5: 오류 - {e}"

def main():
    print("=== 🧠 알고리즘적 해결 방안 테스트 ===")
    print("디폴트 설정으로 여러 해결책 비교")
    
    # 현재 상태 (기준선)
    print("\n=== 📊 현재 상태 (기준선) ===")
    cfg_baseline = create_base_config()
    try:
        result_baseline = solve_for_days_v2(cfg_baseline)
        baseline_rate, baseline_msg = analyze_success_rate(result_baseline, "현재 상태")
        print(baseline_msg)
    except Exception as e:
        baseline_rate = 0
        print(f"현재 상태: 오류 - {e}")
    
    # 해결안들 테스트
    solutions = [
        test_solution_1_individual_mode,
        test_solution_2_batched_mode, 
        test_solution_3_room_capacity,
        test_solution_4_activity_order,
        test_solution_5_combined_activity
    ]
    
    results = []
    
    for solution_func in solutions:
        try:
            rate, msg = solution_func()
            results.append((rate, msg))
            print(msg)
        except Exception as e:
            results.append((0, f"{solution_func.__name__}: 예외 - {e}"))
            print(f"{solution_func.__name__}: 예외 - {e}")
    
    # 결과 요약
    print(f"\n=== 📊 결과 요약 ===")
    print(f"기준선 (현재): {baseline_rate:.1f}%")
    
    best_rate = 0
    best_solution = "없음"
    
    for i, (rate, msg) in enumerate(results, 1):
        print(f"해결안 {i}: {rate:.1f}%")
        if rate > best_rate:
            best_rate = rate
            best_solution = f"해결안 {i}"
    
    print(f"\n🏆 **최고 성능**: {best_solution} ({best_rate:.1f}%)")
    
    if best_rate > baseline_rate:
        improvement = best_rate - baseline_rate
        print(f"✅ **개선도**: +{improvement:.1f}%p")
    else:
        print("❌ 개선된 해결안 없음")
    
    print(f"\n💡 **권장사항**:")
    if best_rate >= 80:
        print("- 충분한 성능 달성! 해당 해결안 적용 권장")
    elif best_rate >= 50:
        print("- 부분적 개선. 추가 최적화 필요")
    else:
        print("- 근본적인 알고리즘 재설계 필요")
        print("- 인접 제약 묶음 처리 등 고급 기법 검토")

if __name__ == "__main__":
    main() 