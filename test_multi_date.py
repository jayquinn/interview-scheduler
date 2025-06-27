"""
Phase 8: 멀티 날짜 스케줄러 테스트
"""
from datetime import datetime, time
from solver.types import DatePlan, GlobalConfig, PrecedenceRule
from solver.multi_date_scheduler import MultiDateScheduler
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def test_multi_date_scheduling():
    """멀티 날짜 스케줄링 테스트"""
    
    print("\n" + "="*60)
    print("멀티 날짜 스케줄링 테스트")
    print("="*60)
    
    # 전역 설정
    global_config = GlobalConfig(
        operating_hours={
            "default": (time(9, 0), time(18, 0)),
            "friday": (time(9, 0), time(17, 0))  # 금요일은 일찍 종료
        },
        precedence_rules=[
            PrecedenceRule("토론면접", "발표준비", gap_min=15),
            PrecedenceRule("발표준비", "발표면접", gap_min=5),
        ],
        batched_group_sizes={
            "토론면접": (4, 6),
            "팀과제": (3, 5)
        },
        room_settings={},  # 활동별 방 설정 (현재 사용 안함)
        time_settings={},  # 활동별 소요시간 (현재 사용 안함)
        global_gap_min=5,  # 전역 최소 간격
        max_stay_hours=8   # 최대 체류시간
    )
    
    # 방 설정
    rooms = {
        "토론실": {"count": 3, "capacity": 6},
        "준비실": {"count": 2, "capacity": 1},
        "발표실": {"count": 2, "capacity": 1},
        "회의실": {"count": 2, "capacity": 5}
    }
    
    # 활동 설정
    activities = {
        "토론면접": {
            "mode": "batched",
            "duration_min": 60,
            "room_type": "토론실",
            "min_capacity": 4,
            "max_capacity": 6
        },
        "발표준비": {
            "mode": "individual",
            "duration_min": 30,
            "room_type": "준비실",
        },
        "발표면접": {
            "mode": "individual", 
            "duration_min": 20,
            "room_type": "발표실",
        },
        "팀과제": {
            "mode": "batched",
            "duration_min": 90,
            "room_type": "회의실",
            "min_capacity": 3,
            "max_capacity": 5
        }
    }
    
    # 날짜별 계획
    date_plans = {
        # 월요일: 개발직 위주
        datetime(2025, 1, 13): DatePlan(
            date=datetime(2025, 1, 13),
            jobs={
                "개발직": 15,
                "디자인직": 5,
            },
            selected_activities=["토론면접", "발표준비", "발표면접"]
        ),
        # 화요일: 기획직 추가
        datetime(2025, 1, 14): DatePlan(
            date=datetime(2025, 1, 14),
            jobs={
                "개발직": 10,
                "기획직": 12,
            },
            selected_activities=["토론면접", "팀과제"]  # 다른 활동 조합
        ),
        # 수요일: 직무별 다른 활동
        datetime(2025, 1, 15): DatePlan(
            date=datetime(2025, 1, 15),
            jobs={
                "개발직": 8,
                "디자인직": 8,
                "기획직": 8,
            },
            selected_activities=["토론면접", "발표준비", "발표면접"],
            overrides={
                "job_activities": {
                    "개발직": ["토론면접", "발표준비", "발표면접"],
                    "디자인직": ["토론면접", "발표면접"],  # 발표준비 제외
                    "기획직": ["토론면접"],  # 토론만
                }
            }
        ),
        # 금요일: 운영시간 오버라이드
        datetime(2025, 1, 17): DatePlan(
            date=datetime(2025, 1, 17),
            jobs={
                "개발직": 6,
                "디자인직": 6,
            },
            selected_activities=["토론면접", "발표준비", "발표면접"],
            overrides={
                "operating_hours": {
                    "start": "09:00",
                    "end": "16:00"  # 금요일은 16시 종료
                }
            }
        )
    }
    
    # 스케줄러 실행
    scheduler = MultiDateScheduler()
    result = scheduler.schedule(
        date_plans=date_plans,
        global_config=global_config,
        rooms=rooms,
        activities=activities
    )
    
    # 결과 분석
    print(f"\n전체 상태: {result.status}")
    print(f"총 지원자: {result.total_applicants}명")
    print(f"스케줄된 지원자: {result.scheduled_applicants}명")
    print(f"성공률: {result.scheduled_applicants/result.total_applicants*100:.1f}%")
    
    if result.failed_dates:
        print(f"\n실패한 날짜: {len(result.failed_dates)}개")
        for date in result.failed_dates:
            print(f"  - {date.date()}")
    
    # 날짜별 상세 결과
    print("\n[날짜별 결과]")
    for date in sorted(result.results.keys()):
        date_result = result.results[date]
        print(f"\n{date.date()} ({date.strftime('%A')})")
        print(f"  상태: {date_result.status}")
        
        if date_result.status == "SUCCESS":
            # 활동별 통계
            activity_stats = {}
            for item in date_result.schedule:
                if not item.applicant_id.startswith("DUMMY_"):
                    if item.activity_name not in activity_stats:
                        activity_stats[item.activity_name] = 0
                    activity_stats[item.activity_name] += 1
            
            print(f"  활동별 스케줄:")
            for activity, count in activity_stats.items():
                print(f"    - {activity}: {count}명")
                
            # 시간대별 분포
            hour_stats = {}
            for item in date_result.schedule:
                if not item.applicant_id.startswith("DUMMY_"):
                    hour = item.time_slot.start_time.total_seconds() // 3600
                    if hour not in hour_stats:
                        hour_stats[hour] = 0
                    hour_stats[hour] += 1
                    
            print(f"  시간대별 분포:")
            for hour in sorted(hour_stats.keys()):
                print(f"    - {int(hour)}시: {hour_stats[hour]}건")
        else:
            print(f"  에러: {date_result.error_message}")
            
        # 백트래킹 정보
        if date_result.backtrack_count > 0:
            print(f"  백트래킹: {date_result.backtrack_count}회")


def test_config_validation():
    """설정 검증 테스트"""
    
    print("\n" + "="*60)
    print("설정 검증 테스트")
    print("="*60)
    
    # 잘못된 설정 테스트
    invalid_config = GlobalConfig(
        operating_hours={
            "default": (time(17, 0), time(9, 0)),  # 시작이 종료보다 늦음
        },
        precedence_rules=[
            PrecedenceRule("A", "A", gap_min=10),  # 순환 참조
        ],
        batched_group_sizes={
            "토론": (6, 4),  # min > max
            "팀과제": (0, 5)  # min <= 0
        },
        room_settings={},
        time_settings={},
        global_gap_min=5,
        max_stay_hours=8
    )
    
    scheduler = MultiDateScheduler()
    errors = scheduler.validate_config({}, invalid_config)
    
    if errors:
        print("\n발견된 오류:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ 오류 없음")


if __name__ == "__main__":
    print("=== Phase 8: 멀티 날짜 스케줄러 테스트 ===")
    
    # 1. 멀티 날짜 스케줄링
    test_multi_date_scheduling()
    
    # 2. 설정 검증
    test_config_validation() 