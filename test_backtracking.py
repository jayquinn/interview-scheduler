"""
백트래킹 로직 테스트
"""
from datetime import datetime, timedelta
from solver.types import (
    DateConfig, Activity, Room, ActivityType, PrecedenceRule
)
from solver.single_date_scheduler import SingleDateScheduler
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')


def test_backtracking_scenario():
    """백트래킹이 필요한 시나리오 테스트"""
    
    # 어려운 시나리오 생성: 방이 부족하거나 시간이 촉박한 경우
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 15,  # 15명
            "JOB02": 15,  # 15명
        },
        activities=[
            # Batched 활동
            Activity(
                name="토론면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="토론면접실",
                required_rooms=["토론면접실"],
                min_capacity=5,
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
            # Parallel 활동
            Activity(
                name="AI면접",
                mode=ActivityType.PARALLEL,
                duration_min=45,
                room_type="컴퓨터실",
                required_rooms=["컴퓨터실"],
                max_capacity=10
            ),
        ],
        rooms=[
            # 토론면접실 2개만 (부족함)
            Room(name="토론면접실A", room_type="토론면접실", capacity=6),
            Room(name="토론면접실B", room_type="토론면접실", capacity=6),
            # 면접실 2개만
            Room(name="면접실1", room_type="면접실", capacity=1),
            Room(name="면접실2", room_type="면접실", capacity=1),
            # 컴퓨터실 1개
            Room(name="컴퓨터실1", room_type="컴퓨터실", capacity=10),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=13)),  # 4시간만 운영 (촉박)
        precedence_rules=[],
        job_activity_matrix={
            ("JOB01", "토론면접"): True,
            ("JOB01", "인성면접"): True,
            ("JOB01", "AI면접"): True,
            ("JOB02", "토론면접"): True,
            ("JOB02", "인성면접"): True,
            ("JOB02", "AI면접"): False,  # JOB02는 AI면접 없음
        }
    )
    
    # 스케줄러 실행
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    # 결과 출력
    print("\n" + "="*60)
    print("백트래킹 테스트 결과")
    print("="*60)
    
    print(f"\n상태: {result.status}")
    print(f"백트래킹 횟수: {result.backtrack_count}")
    
    if result.error_message:
        print(f"에러: {result.error_message}")
        
    print("\n[스케줄링 로그]")
    for log in result.logs:
        print(f"  {log}")
        
    if result.level1_result:
        print(f"\n[Level 1 결과]")
        print(f"  - 그룹 수: {result.level1_result.group_count}")
        print(f"  - 더미 수: {result.level1_result.dummy_count}")
        
    if result.level2_result:
        print(f"\n[Level 2 결과]")
        print(f"  - Batched 스케줄 수: {len(result.level2_result.schedule)}")
        
    if result.level3_result:
        print(f"\n[Level 3 결과]")
        print(f"  - Individual 스케줄 수: {len(result.level3_result.schedule)}")
        print(f"  - 미배정 지원자: {len(result.level3_result.unscheduled)}명")
        
    print("\n[시도한 설정들]")
    for i, config in enumerate(result.attempted_configs):
        print(f"  시도 {i+1}: {config}")
        
    print("\n" + "="*60)


def test_impossible_scenario():
    """불가능한 시나리오 테스트 (백트래킹 한계 도달)"""
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 50,  # 많은 인원
        },
        activities=[
            Activity(
                name="인성면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=60,  # 긴 시간
                room_type="면접실",
                required_rooms=["면접실"]
            ),
        ],
        rooms=[
            # 방 1개만
            Room(name="면접실1", room_type="면접실", capacity=1),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=11)),  # 2시간만
        precedence_rules=[],
        job_activity_matrix={
            ("JOB01", "인성면접"): True,
        }
    )
    
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    print("\n" + "="*60)
    print("불가능한 시나리오 테스트")
    print("="*60)
    
    print(f"\n상태: {result.status}")
    print(f"백트래킹 횟수: {result.backtrack_count}")
    
    if result.error_message:
        print(f"에러: {result.error_message}")
        
    # 마지막 몇 개 로그만 출력
    print("\n[마지막 로그들]")
    for log in result.logs[-10:]:
        print(f"  {log}")
        
    print("\n" + "="*60)


if __name__ == "__main__":
    print("=== 백트래킹 로직 테스트 ===\n")
    
    # 테스트 1: 백트래킹이 필요한 시나리오
    print("1. 백트래킹 시나리오 테스트")
    test_backtracking_scenario()
    
    # 테스트 2: 불가능한 시나리오
    print("\n2. 불가능한 시나리오 테스트")
    test_impossible_scenario() 