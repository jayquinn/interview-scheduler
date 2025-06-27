import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2
import copy

def test_integrated_scheduling():
    print("=== 🧩 통합 스케줄링 테스트 ===")
    print("아이디어: 발표준비+발표면접을 하나의 블록으로 처리")
    
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
        print_schedule_summary(result_current)
    
    print("\n=== 💡 해결 아이디어들 ===")
    
    # 아이디어 1: 발표면접실 수 조정 테스트 (내부적으로만)
    print("\n🔧 아이디어 1: 발표면접실 늘리기 (내부 테스트)")
    room_plan_4rooms = room_plan.copy()
    room_plan_4rooms.loc[0, "발표면접실_count"] = 4
    
    cfg_ui_4rooms = copy.deepcopy(cfg_ui)
    cfg_ui_4rooms['room_plan'] = room_plan_4rooms
    
    status_4, result_4, logs_4, limit_4 = solve_for_days_v2(cfg_ui_4rooms, debug=False)
    
    if result_4 is not None and not result_4.empty:
        violations_4 = analyze_precedence_violations(result_4)
        success_rate_4 = (6 - len(violations_4)) / 6 * 100
        print(f"4개 방 성공률: {success_rate_4:.1f}% ({6-len(violations_4)}/6명)")
    
    # 아이디어 2: 발표준비실 수 늘리기 (내부 테스트)
    print("\n🔧 아이디어 2: 발표준비실 늘리기 (내부 테스트)")
    room_plan_2prep = room_plan.copy()
    room_plan_2prep.loc[0, "발표준비실_count"] = 2
    
    cfg_ui_2prep = copy.deepcopy(cfg_ui)
    cfg_ui_2prep['room_plan'] = room_plan_2prep
    
    status_2p, result_2p, logs_2p, limit_2p = solve_for_days_v2(cfg_ui_2prep, debug=False)
    
    if result_2p is not None and not result_2p.empty:
        violations_2p = analyze_precedence_violations(result_2p)
        success_rate_2p = (6 - len(violations_2p)) / 6 * 100
        print(f"발표준비실 2개 성공률: {success_rate_2p:.1f}% ({6-len(violations_2p)}/6명)")
    
    # 아이디어 3: 발표준비 용량 늘리기 (내부 테스트)
    print("\n🔧 아이디어 3: 발표준비실 용량 늘리기 (내부 테스트)")
    room_plan_big = room_plan.copy()
    room_plan_big.loc[0, "발표준비실_cap"] = 6  # 모든 사람이 한 번에
    
    cfg_ui_big = copy.deepcopy(cfg_ui)
    cfg_ui_big['room_plan'] = room_plan_big
    
    status_big, result_big, logs_big, limit_big = solve_for_days_v2(cfg_ui_big, debug=False)
    
    if result_big is not None and not result_big.empty:
        violations_big = analyze_precedence_violations(result_big)
        success_rate_big = (6 - len(violations_big)) / 6 * 100
        print(f"큰 발표준비실 성공률: {success_rate_big:.1f}% ({6-len(violations_big)}/6명)")
    
    # 아이디어 4: 발표준비 duration 늘리기 (내부 테스트)
    print("\n🔧 아이디어 4: 발표준비 시간 늘리기 (내부 테스트)")
    activities_long = activities.copy()
    activities_long.loc[1, "duration_min"] = 10  # 5분 → 10분
    
    cfg_ui_long = copy.deepcopy(cfg_ui)
    cfg_ui_long['activities'] = activities_long
    
    status_long, result_long, logs_long, limit_long = solve_for_days_v2(cfg_ui_long, debug=False)
    
    if result_long is not None and not result_long.empty:
        violations_long = analyze_precedence_violations(result_long)
        success_rate_long = (6 - len(violations_long)) / 6 * 100
        print(f"긴 발표준비 성공률: {success_rate_long:.1f}% ({6-len(violations_long)}/6명)")
    
    print("\n=== 📈 결과 요약 ===")
    print(f"기본 설정: {success_rate_current:.1f}%")
    if 'success_rate_4' in locals():
        print(f"발표면접실 4개: {success_rate_4:.1f}%")
    if 'success_rate_2p' in locals():
        print(f"발표준비실 2개: {success_rate_2p:.1f}%")
    if 'success_rate_big' in locals():
        print(f"큰 발표준비실: {success_rate_big:.1f}%")
    if 'success_rate_long' in locals():
        print(f"긴 발표준비: {success_rate_long:.1f}%")
    
    print("\n=== 🚀 최적 해결책 찾기 ===")
    best_rate = success_rate_current
    best_config = "기본 설정"
    
    if 'success_rate_4' in locals() and success_rate_4 > best_rate:
        best_rate = success_rate_4
        best_config = "발표면접실 4개"
    
    if 'success_rate_2p' in locals() and success_rate_2p > best_rate:
        best_rate = success_rate_2p
        best_config = "발표준비실 2개"
        
    if 'success_rate_big' in locals() and success_rate_big > best_rate:
        best_rate = success_rate_big
        best_config = "큰 발표준비실"
        
    if 'success_rate_long' in locals() and success_rate_long > best_rate:
        best_rate = success_rate_long
        best_config = "긴 발표준비"
    
    print(f"최적 해결책: {best_config} ({best_rate:.1f}%)")
    
    if best_rate < 100:
        print("\n💡 추가 아이디어:")
        print("- 스케줄링 알고리즘 개선 (백트래킹, 제약 만족)")
        print("- 그룹핑 전략 변경")
        print("- 시간 슬롯 최적화")

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

def print_schedule_summary(result):
    print("\n📅 스케줄 요약:")
    for activity in ["토론면접", "발표준비", "발표면접"]:
        activity_data = result[result['activity_name'] == activity]
        if not activity_data.empty:
            start_times = sorted(activity_data['start_time'].unique())
            print(f"{activity}: {len(start_times)}개 시간대")
            for i, start_time in enumerate(start_times):
                participants = activity_data[activity_data['start_time'] == start_time]['applicant_id'].tolist()
                print(f"  {i+1}차: {start_time} ({len(participants)}명)")

if __name__ == "__main__":
    test_integrated_scheduling() 