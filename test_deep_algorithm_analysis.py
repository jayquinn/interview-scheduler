#!/usr/bin/env python3
"""
스케줄러 내부 로직 심층 분석
- 왜 인접 제약이 무시되는가?
- 방 배정 순서와 우선순위 문제
- 알고리즘의 근본적 한계 파악
"""

import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def deep_algorithm_analysis():
    print("=== 🔬 스케줄러 내부 로직 심층 분석 ===")
    print("인접 제약이 무시되는 근본 원인 파악")
    
    # 간단한 2명 테스트부터 시작
    print(f"\n🧪 실험 1: 최소 단위 (2명) 테스트")
    test_minimal_case()
    
    print(f"\n🧪 실험 2: 중간 단위 (4명) 테스트") 
    test_medium_case()
    
    print(f"\n🧪 실험 3: 역순 스케줄링 테스트")
    test_reverse_scheduling()
    
    print(f"\n🧪 실험 4: 강제 연속 배치 테스트")
    test_forced_adjacency()

def test_minimal_case():
    """2명으로 최소 단위 테스트"""
    print(f"  📋 2명, 발표준비실 1개(2명), 발표면접실 2개(1명)")
    print(f"  💡 이론: 발표준비 1그룹(2명) → 발표면접 2그룹(1명씩)")
    
    config = create_base_config(applicant_count=2)
    result = run_detailed_test(config, "2명_최소단위")
    
    if result == 1.0:
        print(f"  ✅ 성공! 2명은 완벽하게 처리됨")
    else:
        print(f"  ❌ 실패! 2명도 안 됨 - 근본적 문제 확인")

def test_medium_case():
    """4명으로 중간 단위 테스트"""
    print(f"  📋 4명, 발표준비실 1개(2명), 발표면접실 2개(1명)")
    print(f"  💡 이론: 발표준비 2그룹(2명씩) → 발표면접 4그룹(1명씩)")
    
    config = create_base_config(applicant_count=4)
    result = run_detailed_test(config, "4명_중간단위")
    
    if result == 1.0:
        print(f"  ✅ 성공! 4명은 처리 가능")
    else:
        print(f"  ❌ 실패! 4명부터 문제 시작")

def test_reverse_scheduling():
    """역순 스케줄링 - 발표면접을 먼저 배치"""
    print(f"  📋 활동 순서를 바꿔서 발표면접을 먼저 처리")
    print(f"  💡 아이디어: 후행 제약부터 시간을 확정하고 선행 제약을 맞춤")
    
    config = create_base_config(applicant_count=6)
    # 활동 순서 변경: 토론면접 → 발표면접 → 발표준비
    config["activity"] = ["토론면접", "발표면접", "발표준비"]
    config["mode"] = ["batched", "individual", "parallel"]
    config["duration_min"] = [30, 15, 5]
    config["room_type"] = ["토론면접실", "발표면접실", "발표준비실"]
    config["max_capacity"] = [6, 1, 2]
    
    # 선후행 제약도 역순으로
    config["precedence"] = [
        {"predecessor": "발표면접", "successor": "발표준비", "gap_min": -15, "adjacent": True}
    ]
    
    result = run_detailed_test(config, "역순_스케줄링")

def test_forced_adjacency():
    """강제 연속 배치 - 발표준비+발표면접을 하나로 묶기"""
    print(f"  📋 발표준비와 발표면접을 하나의 20분 활동으로 통합")
    print(f"  💡 아이디어: 물리적으로 분리할 수 없게 만들어서 강제 연속성 확보")
    
    config = create_base_config(applicant_count=6)
    # 발표준비 제거하고 발표면접을 20분으로 확장
    config["activity"] = ["토론면접", "발표세션"]
    config["mode"] = ["batched", "individual"]
    config["duration_min"] = [30, 20]  # 5분 + 15분 = 20분
    config["room_type"] = ["토론면접실", "발표면접실"]
    config["max_capacity"] = [6, 1]
    config["precedence"] = []  # 선후행 제약 불필요
    
    # 방 설정에서 발표준비실 제거
    del config["발표준비실_count"]
    del config["발표준비실_cap"]
    
    # 지원자 활동 매핑 수정
    config["job_acts_map"] = {
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표세션": [True]
    }
    
    result = run_detailed_test(config, "강제_연속배치")
    
    if result == 1.0:
        print(f"  🎉 대성공! 통합 방식이 완벽한 해결책!")
    else:
        print(f"  ❌ 통합 방식도 실패")

def create_base_config(applicant_count=6):
    """기본 설정 생성"""
    return {
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "max_capacity": [6, 2, 1],
        "토론면접실_count": 2,
        "토론면접실_cap": 6,
        "발표준비실_count": 1,
        "발표준비실_cap": 2,
        "발표면접실_count": 2,
        "발표면접실_cap": 1,
        "precedence": [
            {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
        ],
        "job_acts_map": {
            "code": ["JOB01"],
            "count": [applicant_count],
            "토론면접": [True],
            "발표준비": [True],
            "발표면접": [True]
        }
    }

def run_detailed_test(config, test_name):
    """상세 테스트 실행"""
    try:
        print(f"  🔧 {test_name} 실행 중...")
        
        # 설정 데이터 준비
        activities = pd.DataFrame({
            "activity": config["activity"],
            "mode": config["mode"],
            "duration_min": config["duration_min"],
            "room_type": config["room_type"],
            "max_capacity": config["max_capacity"],
            "use": [True] * len(config["activity"])
        })
        
        # 방 계획
        room_plan_data = {}
        for key, value in config.items():
            if key.endswith("_count") or key.endswith("_cap"):
                room_plan_data[key] = value
        room_plan = pd.DataFrame([room_plan_data])
        
        # 선후행 제약
        precedence = pd.DataFrame(config["precedence"]) if config["precedence"] else pd.DataFrame()
        
        # 지원자 활동 매핑
        job_acts_map = pd.DataFrame(config["job_acts_map"])
        
        # 운영 시간
        oper_window = pd.DataFrame([{
            "start_time": "09:00",
            "end_time": "17:00"
        }])
        
        # 면접 날짜
        interview_dates = [datetime.now().date()]
        
        # 스케줄링 실행
        cfg_ui = {
            'activities': activities,
            'job_acts_map': job_acts_map,
            'room_plan': room_plan,
            'oper_window': oper_window,
            'precedence': precedence,
            'interview_dates': interview_dates,
            'interview_date': interview_dates[0]
        }
        
        status, schedule_df, logs, limit = solve_for_days_v2(cfg_ui)
        
        if status != "SUCCESS" or schedule_df is None or schedule_df.empty:
            print(f"  ❌ {test_name}: 스케줄링 실패 (status: {status})")
            return 0.0
        
        # 상세 분석
        analyze_schedule_pattern(schedule_df, test_name)
        
        # 인접 제약 검증
        if not precedence.empty:
            success_rate = analyze_adjacency_compliance(schedule_df, precedence)
            print(f"  📊 연속배치 성공률: {success_rate:.1%}")
            return success_rate
        else:
            print(f"  📊 선후행 제약 없음 - 통합 방식")
            return 1.0  # 통합 방식은 항상 성공
        
    except Exception as e:
        print(f"  ❌ {test_name}: 오류 발생 - {str(e)}")
        import traceback
        traceback.print_exc()
        return 0.0

def analyze_schedule_pattern(schedule_df, test_name):
    """스케줄 패턴 분석"""
    print(f"  📋 {test_name} 스케줄 패턴:")
    
    # 활동별로 분석
    for activity in schedule_df['activity_name'].unique():
        activity_data = schedule_df[schedule_df['activity_name'] == activity]
        print(f"    🔹 {activity}:")
        
        # 시간순 정렬
        activity_data = activity_data.sort_values(['start_time', 'room_name'])
        
        for _, row in activity_data.iterrows():
            applicant = row['applicant_id']
            room = row['room_name']
            
            # 시간 처리
            start_time = row['start_time']
            if hasattr(start_time, 'total_seconds'):
                start_min = int(start_time.total_seconds() / 60)
                start_time_str = f"{9 + start_min//60:02d}:{start_min%60:02d}"
            else:
                start_time_str = str(start_time)
            
            print(f"      {start_time_str} @ {room}: {applicant}")

def analyze_adjacency_compliance(schedule_df, precedence_df):
    """인접 제약 준수율 분석"""
    if schedule_df.empty or precedence_df.empty:
        return 0.0
    
    total_constraints = 0
    satisfied_constraints = 0
    violation_details = []
    
    # 지원자별로 분석
    for applicant_id in schedule_df['applicant_id'].unique():
        applicant_schedule = schedule_df[schedule_df['applicant_id'] == applicant_id].copy()
        applicant_schedule = applicant_schedule.sort_values('start_time')
        
        # 각 인접 제약 확인
        for _, rule in precedence_df.iterrows():
            if not rule.get('adjacent', False):
                continue
                
            pred_name = rule['predecessor']
            succ_name = rule['successor']
            gap_min = rule.get('gap_min', 0)
            
            # 선행 및 후행 활동 찾기
            pred_activities = applicant_schedule[applicant_schedule['activity_name'] == pred_name]
            succ_activities = applicant_schedule[applicant_schedule['activity_name'] == succ_name]
            
            if pred_activities.empty or succ_activities.empty:
                continue
            
            # 시간 간격 확인
            for _, pred in pred_activities.iterrows():
                for _, succ in succ_activities.iterrows():
                    total_constraints += 1
                    
                    # 시간 데이터 처리
                    pred_end = pred['end_time']
                    succ_start = succ['start_time']
                    
                    # Timedelta 타입인 경우 분으로 변환
                    if hasattr(pred_end, 'total_seconds'):
                        pred_end_min = pred_end.total_seconds() / 60
                    elif hasattr(pred_end, 'hour'):
                        pred_end_min = pred_end.hour * 60 + pred_end.minute
                    else:
                        pred_end_min = float(pred_end)
                    
                    if hasattr(succ_start, 'total_seconds'):
                        succ_start_min = succ_start.total_seconds() / 60
                    elif hasattr(succ_start, 'hour'):
                        succ_start_min = succ_start.hour * 60 + succ_start.minute
                    else:
                        succ_start_min = float(succ_start)
                    
                    actual_gap = succ_start_min - pred_end_min
                    
                    if abs(actual_gap - gap_min) < 0.1:  # 허용 오차 0.1분
                        satisfied_constraints += 1
                    else:
                        violation_details.append({
                            'applicant': applicant_id,
                            'expected_gap': gap_min,
                            'actual_gap': actual_gap,
                            'violation': actual_gap - gap_min
                        })
    
    # 위반 상세 정보 출력
    if violation_details:
        print(f"  ⚠️ 인접 제약 위반 상세:")
        for violation in violation_details[:3]:  # 처음 3개만 출력
            print(f"    {violation['applicant']}: 예상 {violation['expected_gap']}분, 실제 {violation['actual_gap']:.1f}분 (차이: {violation['violation']:.1f}분)")
    
    if total_constraints == 0:
        return 1.0
    
    return satisfied_constraints / total_constraints

if __name__ == "__main__":
    deep_algorithm_analysis() 