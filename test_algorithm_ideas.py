#!/usr/bin/env python3
"""
인접 제약 개선을 위한 다양한 알고리즘 아이디어 테스트
- 아이디어 1: 후행 제약 우선 스케줄링
- 아이디어 2: 역방향 스케줄링  
- 아이디어 3: 동시 예약 시스템
- 아이디어 4: 그룹 크기 적응형 조정
"""

import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def test_algorithm_ideas():
    print("=== 🧠 인접 제약 개선 알고리즘 아이디어 테스트 ===")
    print("방 효율성보다 인접 제약을 우선하는 다양한 접근법 실험")
    
    # 기본 설정 (6명, 발표준비실 1개/2명, 발표면접실 2개/1명)
    base_config = {
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
            "count": [6],
            "토론면접": [True],
            "발표준비": [True],
            "발표면접": [True]
        }
    }
    
    print(f"\n📊 기본 상황 분석:")
    print(f"- 지원자: 6명")
    print(f"- 발표준비실: 1개 (2명 용량) → 이론적으로 3개 그룹 가능")
    print(f"- 발표면접실: 2개 (1명 용량) → 동시에 2명만 처리 가능")
    print(f"- 문제: 3번째 그룹이 발표면접실 대기로 인한 간격 발생")
    
    # 현재 상태 확인
    print(f"\n🔍 현재 알고리즘 결과:")
    current_result = run_test(base_config, "현재_알고리즘")
    
    ideas = []
    
    # 아이디어 1: 후행 제약 우선 - 그룹 수 제한
    print(f"\n💡 아이디어 1: 후행 제약 우선 스케줄링")
    print(f"발표면접실 2개에 맞춰 최대 2개 그룹만 생성 (발표준비실 여유 무시)")
    
    idea1_config = base_config.copy()
    idea1_config["max_capacity"] = [6, 2, 1]  # 발표준비 max_capacity를 2로 제한하여 그룹 수 조정
    
    # 더 직접적인 방법: 발표준비실을 2개로 늘려서 각각 1명씩 처리
    idea1_alt_config = base_config.copy()
    idea1_alt_config["발표준비실_count"] = 2
    idea1_alt_config["발표준비실_cap"] = 1  # 1명씩 개별 처리
    
    idea1_result = run_test(idea1_alt_config, "아이디어1_개별처리")
    ideas.append(("아이디어1: 후행제약우선", idea1_result))
    
    # 아이디어 2: 발표준비를 individual로 변경
    print(f"\n💡 아이디어 2: 발표준비를 Individual 모드로 변경")
    print(f"parallel 대신 individual로 처리하여 더 정밀한 시간 제어")
    
    idea2_config = base_config.copy()
    idea2_config["mode"] = ["batched", "individual", "individual"]  # 발표준비를 individual로
    
    idea2_result = run_test(idea2_config, "아이디어2_Individual모드")
    ideas.append(("아이디어2: Individual모드", idea2_result))
    
    # 아이디어 3: 발표준비 시간 단축
    print(f"\n💡 아이디어 3: 발표준비 시간 조정")
    print(f"발표준비 시간을 단축하여 더 빠른 회전율 확보")
    
    idea3_config = base_config.copy()
    idea3_config["duration_min"] = [30, 3, 15]  # 발표준비 5분 → 3분
    
    idea3_result = run_test(idea3_config, "아이디어3_시간단축")
    ideas.append(("아이디어3: 시간단축", idea3_result))
    
    # 아이디어 4: 소그룹 처리
    print(f"\n💡 아이디어 4: 소그룹 단위 처리")
    print(f"4명만 처리하여 발표면접실 2개로 완벽하게 처리")
    
    idea4_config = base_config.copy()
    idea4_config["job_acts_map"]["count"] = [4]  # 6명 → 4명
    
    idea4_result = run_test(idea4_config, "아이디어4_소그룹")
    ideas.append(("아이디어4: 소그룹처리", idea4_result))
    
    # 아이디어 5: 발표준비실 용량 조정
    print(f"\n💡 아이디어 5: 발표준비실 용량 1명으로 조정")
    print(f"용량을 1명으로 줄여서 개별 처리 유도")
    
    idea5_config = base_config.copy()
    idea5_config["발표준비실_cap"] = 1  # 2명 → 1명
    
    idea5_result = run_test(idea5_config, "아이디어5_용량조정")
    ideas.append(("아이디어5: 용량조정", idea5_result))
    
    # 결과 요약
    print(f"\n" + "="*80)
    print(f"🏆 알고리즘 아이디어 테스트 결과")
    print(f"="*80)
    
    print(f"현재 알고리즘: 연속배치 성공률 {current_result:.1%}")
    print(f"")
    
    best_idea = None
    best_rate = 0
    
    for idea_name, success_rate in ideas:
        status = "✅ 성공" if success_rate > 0 else "❌ 실패"
        improvement = "🚀 개선!" if success_rate > current_result else ""
        print(f"{idea_name}: {status} (성공률: {success_rate:.1%}) {improvement}")
        
        if success_rate > best_rate:
            best_rate = success_rate
            best_idea = idea_name
    
    print(f"\n🎯 최고 성과: {best_idea} ({best_rate:.1%})")
    
    if best_rate > current_result:
        print(f"🎉 개선 성공! {current_result:.1%} → {best_rate:.1%}")
    else:
        print(f"⚠️ 추가 연구 필요. 모든 아이디어가 현재 수준 이하")
    
    return ideas

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
        room_plan_data = {
            "토론면접실_count": config["토론면접실_count"],
            "토론면접실_cap": config["토론면접실_cap"],
            "발표준비실_count": config["발표준비실_count"],
            "발표준비실_cap": config["발표준비실_cap"],
            "발표면접실_count": config["발표면접실_count"],
            "발표면접실_cap": config["발표면접실_cap"]
        }
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
            print(f"❌ {test_name}: 스케줄링 실패 (status: {status})")
            return 0.0
        
        # 인접 제약 검증
        success_rate = analyze_adjacency_compliance(schedule_df, precedence)
        
        print(f"✅ {test_name}: 연속배치 성공률 {success_rate:.1%}")
        
        # 상세 분석
        analyze_detailed_schedule(schedule_df, test_name)
        
        return success_rate
        
    except Exception as e:
        print(f"❌ {test_name}: 오류 발생 - {str(e)}")
        import traceback
        traceback.print_exc()
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
    
    if total_constraints == 0:
        return 1.0
    
    return satisfied_constraints / total_constraints

def analyze_detailed_schedule(schedule_df, test_name):
    """상세 스케줄 분석"""
    print(f"  📋 {test_name} 상세 분석:")
    
    for activity in ["발표준비", "발표면접"]:
        activity_data = schedule_df[schedule_df['activity_name'] == activity]
        if not activity_data.empty:
            print(f"    🔹 {activity}:")
            
            # 시간대별 그룹핑
            time_groups = activity_data.groupby(['start_time', 'room_name'])
            for (start_time, room_name), group in time_groups:
                participants = sorted(group['applicant_id'].tolist())
                if hasattr(start_time, 'total_seconds'):
                    start_min = int(start_time.total_seconds() / 60)
                    start_time_str = f"{9 + start_min//60:02d}:{start_min%60:02d}"
                else:
                    start_time_str = str(start_time)
                print(f"      {start_time_str} @ {room_name}: {participants} ({len(participants)}명)")

if __name__ == "__main__":
    test_algorithm_ideas() 