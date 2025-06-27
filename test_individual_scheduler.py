"""
Individual Scheduler 테스트
"""
from datetime import datetime, timedelta
from solver.types import (
    Activity, Room, Applicant, Group, ActivityType,
    GroupScheduleResult, TimeSlot, GroupAssignment
)
from solver.individual_scheduler import IndividualScheduler


def test_individual_scheduler():
    """Individual 스케줄러 기본 테스트"""
    
    # 테스트 데이터 준비
    activities = [
        Activity(
            name="인성면접",
            mode=ActivityType.INDIVIDUAL,
            duration_min=30,
            room_type="면접실",
            required_rooms=["면접실"]
        ),
        Activity(
            name="AI면접",
            mode=ActivityType.PARALLEL,
            duration_min=45,
            room_type="컴퓨터실",
            required_rooms=["컴퓨터실"],
            max_capacity=10
        ),
        Activity(
            name="토론면접",  # Batched 활동 (건너뛰어야 함)
            mode=ActivityType.BATCHED,
            duration_min=60,
            room_type="토론면접실",
            required_rooms=["토론면접실"],
            min_capacity=4,
            max_capacity=6
        )
    ]
    
    rooms = [
        Room(name="면접실A", room_type="면접실", capacity=1),
        Room(name="면접실B", room_type="면접실", capacity=1),
        Room(name="컴퓨터실1", room_type="컴퓨터실", capacity=10),
    ]
    
    applicants = [
        Applicant(id="JOB01_001", job_code="JOB01", activities=["인성면접", "AI면접"]),
        Applicant(id="JOB01_002", job_code="JOB01", activities=["인성면접", "AI면접"]),
        Applicant(id="JOB02_001", job_code="JOB02", activities=["인성면접"]),
    ]
    
    # Batched 결과 (가상)
    batched_results = []
    
    # 스케줄러 실행
    scheduler = IndividualScheduler()
    result = scheduler.schedule_individuals(
        applicants=applicants,
        activities=activities,
        rooms=rooms,
        batched_results=batched_results,
        start_time=timedelta(hours=9),  # 09:00
        end_time=timedelta(hours=17),   # 17:00
        date_str="2025-01-15"
    )
    
    # 결과 검증
    print("\n=== Individual 스케줄링 결과 ===")
    
    if result and result.success:
        print("✅ 스케줄링 성공!")
        
        # 지원자별 스케줄
        print("\n[지원자별 스케줄]")
        for applicant_id, slots in result.schedule_by_applicant.items():
            print(f"\n{applicant_id}:")
            for slot in slots:
                start_str = str(slot.start_time).split('.')[0]
                end_str = str(slot.end_time).split('.')[0]
                print(f"  - {slot.activity_name}: {start_str} ~ {end_str} @ {slot.room_name}")
                
        # 방별 스케줄
        print("\n[방별 스케줄]")
        for room_name, slots in result.schedule_by_room.items():
            print(f"\n{room_name}:")
            for slot in slots:
                start_str = str(slot.start_time).split('.')[0]
                end_str = str(slot.end_time).split('.')[0]
                app_ids = ", ".join(slot.applicant_ids)
                print(f"  - {slot.activity_name}: {start_str} ~ {end_str} ({app_ids})")
                
    else:
        print("❌ 스케줄링 실패!")
        
    print("\n" + "="*50)


def test_with_batched_constraints():
    """Batched 제약이 있는 경우 테스트"""
    
    print("\n=== Batched 제약 테스트 ===")
    
    activities = [
        Activity(
            name="인성면접",
            mode=ActivityType.INDIVIDUAL,
            duration_min=30,
            room_type="면접실",
            required_rooms=["면접실"]
        )
    ]
    
    rooms = [
        Room(name="면접실A", room_type="면접실", capacity=1),
    ]
    
    applicants = [
        Applicant(id="JOB01_001", job_code="JOB01", activities=["토론면접", "인성면접"]),
    ]
    
    # Batched 결과 - 10:00~11:00에 토론면접이 있다고 가정
    batched_results = [
        GroupScheduleResult(
            assignments={
                "JOB01_001_토론면접": GroupAssignment(
                    group_id="G1",
                    activity_name="토론면접",
                    job_code="JOB01",
                    applicant_ids=["JOB01_001"],
                    start_time=timedelta(hours=10),
                    end_time=timedelta(hours=11),
                    room_name="토론면접실A"
                )
            },
            schedule_by_applicant={
                "JOB01_001": [
                    TimeSlot(
                        activity_name="토론면접",
                        start_time=timedelta(hours=10),
                        end_time=timedelta(hours=11),
                        room_name="토론면접실A",
                        applicant_ids=["JOB01_001"],
                        date="2025-01-15"
                    )
                ]
            },
            schedule_by_room={},
            room_assignments={},
            success=True
        )
    ]
    
    # 스케줄러 실행
    scheduler = IndividualScheduler()
    result = scheduler.schedule_individuals(
        applicants=applicants,
        activities=activities,
        rooms=rooms,
        batched_results=batched_results,
        start_time=timedelta(hours=9),
        end_time=timedelta(hours=17),
        date_str="2025-01-15"
    )
    
    if result and result.success:
        print("✅ Batched 제약 반영 성공!")
        for applicant_id, slots in result.schedule_by_applicant.items():
            print(f"\n{applicant_id}:")
            for slot in slots:
                start_str = str(slot.start_time).split('.')[0]
                end_str = str(slot.end_time).split('.')[0]
                print(f"  - {slot.activity_name}: {start_str} ~ {end_str}")
                
        # 10:00~11:00을 피했는지 확인
        for slot in result.schedule_by_applicant["JOB01_001"]:
            if slot.activity_name == "인성면접":
                if slot.start_time >= timedelta(hours=11) or slot.end_time <= timedelta(hours=10):
                    print("✅ 토론면접 시간(10:00~11:00)을 피해서 배치됨")
                else:
                    print("❌ 토론면접 시간과 충돌!")
    else:
        print("❌ 스케줄링 실패!")


if __name__ == "__main__":
    test_individual_scheduler()
    test_with_batched_constraints() 