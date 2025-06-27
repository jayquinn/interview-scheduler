"""
Phase 5 백트래킹 완료 테스트
"""
from datetime import datetime, timedelta
from solver.types import (
    DateConfig, Activity, Room, ActivityType, PrecedenceRule
)
from solver.single_date_scheduler import SingleDateScheduler
import logging

# 로깅 설정
logging.basicConfig(level=logging.WARNING, format='%(message)s')


def test_complete_scenario():
    """전체 시나리오 테스트"""
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 13,  # 13명 (더미 추가 필요)
            "JOB02": 10,  # 10명
        },
        activities=[
            # Batched 활동
            Activity(
                name="토론면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="토론면접실",
                required_rooms=["토론면접실"],
                min_capacity=4,
                max_capacity=6
            ),
            # Individual 활동
            Activity(
                name="인성면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=30,
                room_type="면접실",
                required_rooms=["면접실"]
            ),
        ],
        rooms=[
            Room(name="토론면접실A", room_type="토론면접실", capacity=6),
            Room(name="토론면접실B", room_type="토론면접실", capacity=6),
            Room(name="면접실1", room_type="면접실", capacity=1),
            Room(name="면접실2", room_type="면접실", capacity=1),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=17)),
        precedence_rules=[],
        job_activity_matrix={
            ("JOB01", "토론면접"): True,
            ("JOB01", "인성면접"): True,
            ("JOB02", "토론면접"): True,
            ("JOB02", "인성면접"): True,
        }
    )
    
    # 스케줄러 실행
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    # 결과 출력
    print("\n" + "="*60)
    print("Phase 5 완료 테스트")
    print("="*60)
    
    print(f"\n상태: {result.status}")
    print(f"백트래킹 횟수: {result.backtrack_count}")
    
    if result.status == "SUCCESS":
        print("\n✅ 스케줄링 성공!")
        
        # 전체 스케줄 수
        if result.schedule:
            print(f"\n총 스케줄 항목 수: {len(result.schedule)}")
            
            # 활동별 분류
            by_activity = {}
            for item in result.schedule:
                activity = item.activity_name
                if activity not in by_activity:
                    by_activity[activity] = []
                if not item.applicant_id.startswith("DUMMY_"):
                    by_activity[activity].append(item.applicant_id)
            
            print("\n[활동별 배정 현황]")
            for activity, applicants in by_activity.items():
                print(f"  {activity}: {len(applicants)}명")
                
            # 시간대별 분포
            print("\n[시간대별 스케줄]")
            sorted_schedule = sorted(result.schedule, key=lambda x: x.time_slot.start)
            
            current_time = None
            for item in sorted_schedule[:10]:  # 처음 10개만
                if not item.applicant_id.startswith("DUMMY_"):
                    time_str = item.time_slot.start.strftime("%H:%M")
                    if time_str != current_time:
                        print(f"\n{time_str}:")
                        current_time = time_str
                    print(f"  - {item.applicant_id}: {item.activity_name} @ {item.room_name}")
                    
            if len(sorted_schedule) > 10:
                print(f"\n  ... 그 외 {len(sorted_schedule) - 10}개 스케줄")
    else:
        print("\n❌ 스케줄링 실패!")
        print(f"에러: {result.error_message}")
        
    # 백트래킹 정보
    if result.attempted_configs:
        print("\n[백트래킹 시도]")
        for i, config in enumerate(result.attempted_configs):
            print(f"  시도 {i+1}: {config}")
            
    print("\n" + "="*60)


def test_backtracking_success():
    """백트래킹이 성공하는 케이스"""
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 7,  # 7명 → 더미 추가로 해결 가능
        },
        activities=[
            Activity(
                name="토론면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="토론면접실",
                required_rooms=["토론면접실"],
                min_capacity=4,
                max_capacity=6
            ),
        ],
        rooms=[
            Room(name="토론면접실A", room_type="토론면접실", capacity=6),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=12)),
        precedence_rules=[],
        job_activity_matrix={
            ("JOB01", "토론면접"): True,
        }
    )
    
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    print("\n백트래킹 성공 케이스 테스트")
    print(f"상태: {result.status}")
    
    if result.level1_result:
        print(f"그룹 수: {result.level1_result.group_count}")
        print(f"더미 수: {result.level1_result.dummy_count}")
        
        # 그룹 구성 확인
        for activity, groups in result.level1_result.groups.items():
            print(f"\n{activity}:")
            for group in groups:
                print(f"  {group.id}: {len(group.members)}명")


if __name__ == "__main__":
    print("=== Phase 5: 백트래킹 로직 완료 테스트 ===\n")
    
    # 테스트 1: 전체 시나리오
    print("1. 전체 시나리오 테스트")
    test_complete_scenario()
    
    # 테스트 2: 백트래킹 성공 케이스
    print("\n2. 백트래킹 성공 케이스")
    test_backtracking_success() 