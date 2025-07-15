#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solver.api import schedule_interviews
from datetime import datetime, date, time, timedelta
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_small_test_config():
    """작은 규모의 테스트 데이터 생성 (app.py 설정 기반)"""
    
    # 현재 날짜 기준으로 2일치 데이터 생성 (축소)
    today = date.today()
    
    # 활동 리스트 (app.py와 동일)
    selected_activities = ["토론면접", "발표준비", "발표면접"]
    
    # 날짜별 계획 (작은 규모로 축소)
    date_plans = {
        today.strftime('%Y-%m-%d'): {
            "jobs": {"JOB01": 6, "JOB02": 6},  # 23 -> 6으로 축소
            "selected_activities": selected_activities
        },
        (today + timedelta(days=1)).strftime('%Y-%m-%d'): {
            "jobs": {"JOB03": 4, "JOB04": 4},  # 20 -> 4로 축소
            "selected_activities": selected_activities
        }
    }
    
    # 활동 정의 (app.py와 동일)
    activities = {
        "토론면접": {
            "mode": "batched",
            "duration_min": 30,
            "room_type": "토론면접실",
            "min_capacity": 4,
            "max_capacity": 6
        },
        "발표준비": {
            "mode": "parallel", 
            "duration_min": 5,
            "room_type": "발표준비실",
            "min_capacity": 1,
            "max_capacity": 2
        },
        "발표면접": {
            "mode": "individual",
            "duration_min": 15,
            "room_type": "발표면접실",
            "min_capacity": 1,
            "max_capacity": 1
        }
    }
    
    # 방 설정 (app.py와 동일)
    rooms = {
        "토론면접실": {"count": 2, "capacity": 6},
        "발표준비실": {"count": 1, "capacity": 2},
        "발표면접실": {"count": 2, "capacity": 1}
    }
    
    # 전역 설정 (app.py와 동일)
    global_config = {
        "precedence": [("발표준비", "발표면접", 0, True)],  # 연속배치, 0분 간격
        "operating_hours": {"start": "09:00", "end": "17:30"},
        "batched_group_sizes": {"토론면접": [4, 6]},
        "global_gap_min": 5,
        "max_stay_hours": 5
    }
    
    return date_plans, activities, rooms, global_config

def print_config_summary(date_plans, activities, rooms, global_config):
    """설정 요약 출력"""
    print("*** app.py 기반 소규모 테스트 데이터 ***")
    print("=" * 60)
    
    # 날짜별 지원자 수
    total_applicants = 0
    for i, (date_key, plan) in enumerate(date_plans.items(), 1):
        day_total = sum(plan["jobs"].values())
        total_applicants += day_total
        jobs_info = ", ".join(f"{job}({count}명)" for job, count in plan["jobs"].items())
        print(f"Day {i} ({date_key}): {jobs_info} = {day_total}명")
    
    print(f"\n총 지원자 수: {total_applicants}명 (2일간)")
    
    # 활동 정보
    print(f"\n활동 설정:")
    for name, config in activities.items():
        print(f"  - {name}: {config['mode']}, {config['duration_min']}분, {config['min_capacity']}-{config['max_capacity']}명")
    
    # 방 정보
    print(f"\n방 설정:")
    for name, config in rooms.items():
        print(f"  - {name}: {config['count']}개, 최대 {config['capacity']}명")
    
    # 운영시간
    print(f"\n운영시간: {global_config['operating_hours']['start']} ~ {global_config['operating_hours']['end']}")
    print(f"선후행 제약: {global_config['precedence']}")
    print("=" * 60)

def analyze_result(result):
    """결과 분석"""
    print(f"\n📊 스케줄링 결과 분석:")
    print(f"  - 상태: {result.status}")
    print(f"  - 총 지원자: {result.total_applicants}명")
    print(f"  - 배정 완료: {result.scheduled_applicants}명")
    print(f"  - 성공률: {(result.scheduled_applicants/result.total_applicants*100):.1f}%")
    
    # 날짜별 상세 결과
    print(f"\n📅 날짜별 결과:")
    for date_key, date_result in result.results.items():
        if date_result.status == "SUCCESS":
            print(f"  - {date_key.strftime('%Y-%m-%d')}: {date_result.scheduled_applicants}명 성공")
        else:
            print(f"  - {date_key.strftime('%Y-%m-%d')}: 실패 ({date_result.error_message})")
    
    # 실패한 날짜가 있는 경우
    if hasattr(result, 'failed_dates') and result.failed_dates:
        print(f"\n❌ 실패한 날짜: {[d.strftime('%Y-%m-%d') for d in result.failed_dates]}")

def main():
    """메인 테스트"""
    print("*** app.py 기반 소규모 CP-SAT 테스트 ***")
    print("=" * 60)
    
    # 설정 생성
    date_plans, activities, rooms, global_config = create_small_test_config()
    
    # 설정 요약 출력
    print_config_summary(date_plans, activities, rooms, global_config)
    
    print("\n[CP-SAT] 2일치 소규모 스케줄링 시작...")
    
    try:
        # schedule_interviews API 호출
        result = schedule_interviews(
            date_plans=date_plans,
            global_config=global_config,
            rooms=rooms,
            activities=activities,
            logger=logger
        )
        
        if result.status == "SUCCESS":
            print(f"\n✅ 성공!")
            analyze_result(result)
            print(f"\n🎉 결론: CP-SAT이 app.py 기반 설정에서 성공적으로 작동!")
            
        elif result.status == "PARTIAL":
            print(f"\n⚠️ 부분 성공!")
            analyze_result(result)
            print(f"\n🔶 결론: 일부 날짜에서 성공, 개선 필요")
            
        else:
            print(f"\n❌ 실패: {result.status}")
            analyze_result(result)
            
    except Exception as e:
        print(f"\n💥 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 