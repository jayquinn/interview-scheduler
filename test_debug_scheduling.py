"""
디버그 테스트: 스케줄링 실패 원인 진단
"""
from datetime import datetime, timedelta
from solver.types import (
    DateConfig, Activity, Room, ActivityType, PrecedenceRule
)
from solver.single_date_scheduler import SingleDateScheduler
import logging

# 로깅 설정 - 더 자세한 로그 출력
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def test_simple_scenario():
    """간단한 시나리오로 문제 진단"""
    
    print("\n" + "="*60)
    print("간단한 시나리오 테스트")
    print("="*60)
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 6,  # 6명
            "JOB02": 6,  # 6명
        },
        activities=[
            # 1. 토론면접 (Batched)
            Activity(
                name="토론면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="토론실",
                required_rooms=["토론실"],
                min_capacity=3,
                max_capacity=6
            ),
            # 2. 발표준비 (Individual)
            Activity(
                name="발표준비",
                mode=ActivityType.INDIVIDUAL,
                duration_min=30,
                room_type="준비실",
                required_rooms=["준비실"]
            ),
            # 3. 발표면접 (Individual) 
            Activity(
                name="발표면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=20,
                room_type="발표실",
                required_rooms=["발표실"]
            ),
        ],
        rooms=[
            # 토론실 2개
            Room(name="토론실A", room_type="토론실", capacity=6),
            Room(name="토론실B", room_type="토론실", capacity=6),
            # 준비실 3개
            Room(name="준비실1", room_type="준비실", capacity=1),
            Room(name="준비실2", room_type="준비실", capacity=1),
            Room(name="준비실3", room_type="준비실", capacity=1),
            # 발표실 3개
            Room(name="발표실1", room_type="발표실", capacity=1),
            Room(name="발표실2", room_type="발표실", capacity=1),
            Room(name="발표실3", room_type="발표실", capacity=1),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=18)),  # 9시간
        precedence_rules=[
            # 토론면접 → 발표준비
            PrecedenceRule(
                predecessor="토론면접",
                successor="발표준비",
                gap_min=10  # 10분 휴식
            ),
            # 발표준비 → 발표면접
            PrecedenceRule(
                predecessor="발표준비",
                successor="발표면접",
                gap_min=5  # 5분 이동
            ),
        ],
        job_activity_matrix={
            # 모든 직무가 모든 활동 수행
            ("JOB01", "토론면접"): True,
            ("JOB01", "발표준비"): True,
            ("JOB01", "발표면접"): True,
            ("JOB02", "토론면접"): True,
            ("JOB02", "발표준비"): True,
            ("JOB02", "발표면접"): True,
        }
    )
    
    # 스케줄러 실행
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    print(f"\n상태: {result.status}")
    
    if result.status == "SUCCESS":
        print("✅ 스케줄링 성공!")
        
        # 스케줄 상세 분석
        print("\n[스케줄 상세]")
        for item in sorted(result.schedule, key=lambda x: (x.time_slot.start_time, x.applicant_id)):
            if not item.applicant_id.startswith("DUMMY_"):
                print(f"{item.time_slot.start_time.total_seconds()//3600:02.0f}:{(item.time_slot.start_time.total_seconds()%3600)//60:02.0f} - "
                      f"{item.time_slot.end_time.total_seconds()//3600:02.0f}:{(item.time_slot.end_time.total_seconds()%3600)//60:02.0f} | "
                      f"{item.applicant_id} | {item.activity_name} | {item.room_name}")
                      
        # Level별 결과
        if result.level1_result:
            print(f"\n[Level 1 결과]")
            print(f"총 그룹 수: {result.level1_result.group_count}")
            print(f"더미 지원자: {result.level1_result.dummy_count}명")
            
            # 그룹 구성 출력
            for activity_name, groups in result.level1_result.groups.items():
                print(f"\n{activity_name}:")
                for group in groups:
                    real_members = [m for m in group.members if not m.startswith("DUMMY_")]
                    dummy_members = [m for m in group.members if m.startswith("DUMMY_")]
                    print(f"  {group.id}: {len(real_members)}명 실제 + {len(dummy_members)}명 더미")
                    
    else:
        print("❌ 스케줄링 실패!")
        print(f"에러: {result.error_message}")
        
        # 각 레벨별 결과 확인
        if result.level1_result:
            print("\n✅ Level 1 (그룹 구성) 성공")
            print(f"   그룹 수: {result.level1_result.group_count}")
            
        if result.level2_result:
            print("✅ Level 2 (Batched 스케줄링) 성공")
            print(f"   스케줄된 항목: {len(result.level2_result.schedule)}개")
        elif result.level1_result:
            print("❌ Level 2 (Batched 스케줄링) 실패")
            
        if result.level3_result:
            if result.level3_result.success:
                print("✅ Level 3 (Individual 스케줄링) 성공")
            else:
                print("❌ Level 3 (Individual 스케줄링) 실패")
                if result.level3_result.unscheduled:
                    print(f"   미배정: {result.level3_result.unscheduled}")
        elif result.level2_result:
            print("❌ Level 3 (Individual 스케줄링) 실패")


def test_without_precedence():
    """Precedence 없이 테스트"""
    
    print("\n" + "="*60)
    print("Precedence 없이 테스트")
    print("="*60)
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 6,
        },
        activities=[
            Activity(
                name="발표준비",
                mode=ActivityType.INDIVIDUAL,
                duration_min=30,
                room_type="준비실",
                required_rooms=["준비실"]
            ),
        ],
        rooms=[
            Room(name="준비실1", room_type="준비실", capacity=1),
            Room(name="준비실2", room_type="준비실", capacity=1),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=12)),  # 3시간
        precedence_rules=[],
        job_activity_matrix={
            ("JOB01", "발표준비"): True,
        }
    )
    
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    print(f"\n상태: {result.status}")
    if result.status == "SUCCESS":
        print("✅ Individual 스케줄링 자체는 작동함")
    else:
        print("❌ Individual 스케줄링 자체가 실패")
        print(f"에러: {result.error_message}")


def test_complex_scenario():
    """통합 테스트와 유사한 복잡한 시나리오"""
    
    print("\n" + "="*60)
    print("복잡한 시나리오 테스트")
    print("="*60)
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "개발직": 10,
            "디자인직": 8,
        },
        activities=[
            # 1차: 토론면접 (Batched)
            Activity(
                name="토론면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="토론실",
                required_rooms=["토론실"],
                min_capacity=4,
                max_capacity=6
            ),
            # 2차: 발표준비 (Individual)
            Activity(
                name="발표준비",
                mode=ActivityType.INDIVIDUAL,
                duration_min=30,
                room_type="준비실",
                required_rooms=["준비실"]
            ),
            # 3차: 발표면접 (Individual)
            Activity(
                name="발표면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=20,
                room_type="발표실",
                required_rooms=["발표실"]
            ),
        ],
        rooms=[
            # 토론실 2개
            Room(name="토론실A", room_type="토론실", capacity=6),
            Room(name="토론실B", room_type="토론실", capacity=6),
            # 준비실 2개
            Room(name="준비실1", room_type="준비실", capacity=1),
            Room(name="준비실2", room_type="준비실", capacity=1),
            # 발표실 2개
            Room(name="발표실1", room_type="발표실", capacity=1),
            Room(name="발표실2", room_type="발표실", capacity=1),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=18)),  # 9시간
        precedence_rules=[
            # 토론면접 → 발표준비
            PrecedenceRule(
                predecessor="토론면접",
                successor="발표준비",
                gap_min=15  # 15분 휴식
            ),
            # 발표준비 → 발표면접
            PrecedenceRule(
                predecessor="발표준비",
                successor="발표면접",
                gap_min=5  # 5분 이동
            ),
        ],
        job_activity_matrix={
            # 모든 직무가 모든 활동 수행
            ("개발직", "토론면접"): True,
            ("개발직", "발표준비"): True,
            ("개발직", "발표면접"): True,
            ("디자인직", "토론면접"): True,
            ("디자인직", "발표준비"): True,
            ("디자인직", "발표면접"): True,
        }
    )
    
    # 스케줄러 실행
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    print(f"\n상태: {result.status}")
    print(f"백트래킹 횟수: {result.backtrack_count}")
    
    # 로그 출력
    print("\n[실행 로그]")
    for log in result.logs:
        print(f"  {log}")
    
    if result.status == "SUCCESS":
        print("\n✅ 복잡한 시나리오도 성공!")
    else:
        print("\n❌ 복잡한 시나리오 실패!")
        print(f"에러: {result.error_message}")


if __name__ == "__main__":
    # 1. 간단한 시나리오
    test_simple_scenario()
    
    # 2. Precedence 없이 테스트
    test_without_precedence()
    
    # 3. 복잡한 시나리오
    test_complex_scenario() 