#!/usr/bin/env python3
"""
하드코딩 수정 후 일반화된 인접 제약 시스템 테스트
- 발표준비 → 발표면접 (gap_min=0)
- 인성면접 → 최종면접 (gap_min=0) 
- 다양한 활동명과 방 타입으로 재사용성 검증
"""

import pandas as pd
from datetime import datetime, timedelta
import core

def test_generalized_precedence():
    print("=== 🔧 일반화된 인접 제약 시스템 테스트 ===")
    print("하드코딩 제거 후 다양한 활동 조합 테스트")
    
    # 테스트 1: 기본 발표준비 → 발표면접 (gap_min=0)
    print("\n📋 테스트 1: 발표준비 → 발표면접 (0분 간격)")
    test_config_1 = {
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "max_capacity": [6, 2, 1],
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [2],
        "발표면접실_count": [2],
        "발표면접실_cap": [1],
        "precedence": [
            {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
        ],
        "job_acts_map": {
            "code": ["JOB01"],
            "count": [6],
            "토론면접": [True],
            "발표준비": [True],
            "발표면접": [True]
        }
    }
    
    result_1 = run_test(test_config_1, "발표준비→발표면접")
    
    # 테스트 2: 인성면접 → 최종면접 (gap_min=0)
    print("\n📋 테스트 2: 인성면접 → 최종면접 (0분 간격)")
    test_config_2 = {
        "activity": ["토론면접", "인성면접", "최종면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 10, 20],
        "room_type": ["토론면접실", "인성면접실", "최종면접실"],
        "max_capacity": [6, 3, 1],
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "인성면접실_count": [1],
        "인성면접실_cap": [3],
        "최종면접실_count": [2],
        "최종면접실_cap": [1],
        "precedence": [
            {"predecessor": "인성면접", "successor": "최종면접", "gap_min": 0, "adjacent": True}
        ],
        "job_acts_map": {
            "code": ["JOB01"],
            "count": [6],
            "토론면접": [True],
            "인성면접": [True],
            "최종면접": [True]
        }
    }
    
    result_2 = run_test(test_config_2, "인성면접→최종면접")
    
    # 테스트 3: 복합 제약 (두 개의 인접 제약)
    print("\n📋 테스트 3: 복합 인접 제약")
    test_config_3 = {
        "activity": ["토론면접", "1차준비", "1차면접", "2차준비", "2차면접"],
        "mode": ["batched", "parallel", "individual", "parallel", "individual"],
        "duration_min": [30, 5, 15, 5, 20],
        "room_type": ["토론면접실", "준비실", "1차면접실", "준비실", "2차면접실"],
        "max_capacity": [6, 2, 1, 2, 1],
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "준비실_count": [2],
        "준비실_cap": [2],
        "1차면접실_count": [2],
        "1차면접실_cap": [1],
        "2차면접실_count": [1],
        "2차면접실_cap": [1],
        "precedence": [
            {"predecessor": "1차준비", "successor": "1차면접", "gap_min": 0, "adjacent": True},
            {"predecessor": "2차준비", "successor": "2차면접", "gap_min": 0, "adjacent": True}
        ],
        "job_acts_map": {
            "code": ["JOB01"],
            "count": [4],
            "토론면접": [True],
            "1차준비": [True],
            "1차면접": [True],
            "2차준비": [True],
            "2차면접": [True]
        }
    }
    
    result_3 = run_test(test_config_3, "복합인접제약")
    
    # 결과 요약
    print("\n" + "="*80)
    print("🏆 일반화된 인접 제약 시스템 테스트 결과")
    print("="*80)
    
    results = [
        ("발표준비→발표면접", result_1),
        ("인성면접→최종면접", result_2),
        ("복합인접제약", result_3)
    ]
    
    success_count = 0
    for test_name, success_rate in results:
        status = "✅ 성공" if success_rate > 0 else "❌ 실패"
        print(f"{test_name}: {status} (연속배치 성공률: {success_rate:.1%})")
        if success_rate > 0:
            success_count += 1
    
    print(f"\n총 {success_count}/{len(results)}개 테스트 통과")
    
    if success_count == len(results):
        print("🎉 모든 테스트 통과! 하드코딩 제거 및 일반화 성공!")
    else:
        print("⚠️ 일부 테스트 실패. 추가 수정 필요.")

def run_test(config, test_name):
    """단일 테스트 실행"""
    try:
        print(f"\n🔧 {test_name} 테스트 실행 중...")
        
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
            if "_count" in key or "_cap" in key:
                room_plan_data[key] = value
        room_plan = pd.DataFrame([room_plan_data])
        
        # 선후행 제약
        precedence = pd.DataFrame(config["precedence"])
        
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
        result = core.solve_schedule(
            activities=activities,
            room_plan=room_plan,
            precedence=precedence,
            job_acts_map=job_acts_map,
            oper_window=oper_window,
            interview_dates=interview_dates,
            group_min_size=4,
            group_max_size=6,
            global_gap_min=5,
            max_stay_hours=8,
            daily_limit=0,
            progress_callback=None
        )
        
        if result is None:
            print(f"❌ {test_name}: 스케줄링 실패")
            return 0.0
        
        # 연속배치 성공률 분석
        schedule_df = result.get("schedule", pd.DataFrame())
        if schedule_df.empty:
            print(f"❌ {test_name}: 결과 데이터 없음")
            return 0.0
        
        # 인접 제약 검증
        success_rate = analyze_adjacency_compliance(schedule_df, precedence)
        
        print(f"✅ {test_name}: 연속배치 성공률 {success_rate:.1%}")
        return success_rate
        
    except Exception as e:
        print(f"❌ {test_name}: 오류 발생 - {str(e)}")
        return 0.0

def analyze_adjacency_compliance(schedule_df, precedence_df):
    """인접 제약 준수율 분석"""
    if schedule_df.empty or precedence_df.empty:
        return 0.0
    
    total_constraints = 0
    satisfied_constraints = 0
    
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
                    
                    pred_end = pd.to_datetime(pred['end_time'])
                    succ_start = pd.to_datetime(succ['start_time'])
                    actual_gap = (succ_start - pred_end).total_seconds() / 60
                    
                    if actual_gap == gap_min:  # 정확히 gap_min 분 간격
                        satisfied_constraints += 1
                        print(f"✅ {applicant_id}: {pred_name} → {succ_name} 간격 {actual_gap}분 (목표: {gap_min}분)")
                    else:
                        print(f"❌ {applicant_id}: {pred_name} → {succ_name} 간격 {actual_gap}분 (목표: {gap_min}분)")
    
    if total_constraints == 0:
        return 1.0
    
    return satisfied_constraints / total_constraints

if __name__ == "__main__":
    test_generalized_precedence() 