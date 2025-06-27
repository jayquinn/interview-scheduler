"""
Phase 6: Precedence 제약 테스트
"""
from datetime import datetime, timedelta
from solver.types import (
    DateConfig, Activity, Room, ActivityType, PrecedenceRule
)
from solver.single_date_scheduler import SingleDateScheduler
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')


def test_batched_precedence():
    """Batched 활동의 precedence 테스트"""
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 8,  # 8명
        },
        activities=[
            # 발표준비 (Batched)
            Activity(
                name="발표준비",
                mode=ActivityType.BATCHED,
                duration_min=30,
                room_type="준비실",
                required_rooms=["준비실"],
                min_capacity=4,
                max_capacity=6
            ),
            # 발표면접 (Batched)
            Activity(
                name="발표면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="발표실",
                required_rooms=["발표실"],
                min_capacity=4,
                max_capacity=6
            ),
        ],
        rooms=[
            Room(name="준비실A", room_type="준비실", capacity=6),
            Room(name="발표실A", room_type="발표실", capacity=6),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=17)),
        precedence_rules=[
            PrecedenceRule(
                predecessor="발표준비",
                successor="발표면접",
                gap_min=10  # 10분 간격
            )
        ],
        job_activity_matrix={
            ("JOB01", "발표준비"): True,
            ("JOB01", "발표면접"): True,
        }
    )
    
    # 스케줄러 실행
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    # 결과 검증
    print("\n" + "="*60)
    print("Batched Precedence 테스트")
    print("="*60)
    
    print(f"\n상태: {result.status}")
    
    if result.status == "SUCCESS":
        print("\n✅ 스케줄링 성공!")
        
        # 그룹별 스케줄 확인
        if result.schedule:
            # 그룹별로 정리
            group_schedules = {}
            for item in result.schedule:
                if item.group_id:
                    if item.group_id not in group_schedules:
                        group_schedules[item.group_id] = []
                    group_schedules[item.group_id].append(item)
            
            print("\n[그룹별 스케줄]")
            for group_id in sorted(group_schedules.keys()):
                items = sorted(group_schedules[group_id], 
                             key=lambda x: x.time_slot.start)
                print(f"\n{group_id}:")
                
                for item in items:
                    if not item.applicant_id.startswith("DUMMY_"):
                        start_str = item.time_slot.start.strftime("%H:%M")
                        end_str = item.time_slot.end.strftime("%H:%M")
                        print(f"  - {item.activity_name}: {start_str} ~ {end_str}")
                        
                # Precedence 검증
                prep_item = next((i for i in items if i.activity_name == "발표준비"), None)
                pres_item = next((i for i in items if i.activity_name == "발표면접"), None)
                
                if prep_item and pres_item:
                    gap = (pres_item.time_slot.start - prep_item.time_slot.end).total_seconds() / 60
                    print(f"  → 간격: {int(gap)}분")
                    
                    if gap >= 10:
                        print("  ✅ Precedence 준수 (10분 이상)")
                    else:
                        print("  ❌ Precedence 위반!")
    
    else:
        print("\n❌ 스케줄링 실패!")
        print(f"에러: {result.error_message}")


def test_individual_precedence():
    """Individual 활동의 precedence 테스트"""
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 3,  # 3명
        },
        activities=[
            # 서류검토 (Individual)
            Activity(
                name="서류검토",
                mode=ActivityType.INDIVIDUAL,
                duration_min=20,
                room_type="검토실",
                required_rooms=["검토실"]
            ),
            # 심층면접 (Individual)
            Activity(
                name="심층면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=40,
                room_type="면접실",
                required_rooms=["면접실"]
            ),
        ],
        rooms=[
            Room(name="검토실1", room_type="검토실", capacity=1),
            Room(name="면접실1", room_type="면접실", capacity=1),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=12)),
        precedence_rules=[
            PrecedenceRule(
                predecessor="서류검토",
                successor="심층면접",
                gap_min=15  # 15분 간격
            )
        ],
        job_activity_matrix={
            ("JOB01", "서류검토"): True,
            ("JOB01", "심층면접"): True,
        }
    )
    
    # 스케줄러 실행
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    # 결과 검증
    print("\n" + "="*60)
    print("Individual Precedence 테스트")
    print("="*60)
    
    print(f"\n상태: {result.status}")
    
    if result.status == "SUCCESS":
        print("\n✅ 스케줄링 성공!")
        
        # 지원자별 스케줄 확인
        if result.schedule:
            # 지원자별로 정리
            applicant_schedules = {}
            for item in result.schedule:
                if not item.applicant_id.startswith("DUMMY_"):
                    if item.applicant_id not in applicant_schedules:
                        applicant_schedules[item.applicant_id] = []
                    applicant_schedules[item.applicant_id].append(item)
            
            print("\n[지원자별 스케줄]")
            for applicant_id in sorted(applicant_schedules.keys()):
                items = sorted(applicant_schedules[applicant_id], 
                             key=lambda x: x.time_slot.start)
                print(f"\n{applicant_id}:")
                
                for item in items:
                    start_str = item.time_slot.start.strftime("%H:%M")
                    end_str = item.time_slot.end.strftime("%H:%M")
                    print(f"  - {item.activity_name}: {start_str} ~ {end_str} @ {item.room_name}")
                
                # Precedence 검증
                review_item = next((i for i in items if i.activity_name == "서류검토"), None)
                interview_item = next((i for i in items if i.activity_name == "심층면접"), None)
                
                if review_item and interview_item:
                    gap = (interview_item.time_slot.start - review_item.time_slot.end).total_seconds() / 60
                    print(f"  → 간격: {int(gap)}분")
                    
                    if gap >= 15:
                        print("  ✅ Precedence 준수 (15분 이상)")
                    else:
                        print("  ❌ Precedence 위반!")
    
    else:
        print("\n❌ 스케줄링 실패!")
        print(f"에러: {result.error_message}")


def test_mixed_precedence():
    """Batched와 Individual이 섞인 precedence 테스트"""
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 6,  # 6명
        },
        activities=[
            # 토론면접 (Batched)
            Activity(
                name="토론면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="토론실",
                required_rooms=["토론실"],
                min_capacity=3,
                max_capacity=6
            ),
            # 인성면접 (Individual) - 토론면접 후
            Activity(
                name="인성면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=30,
                room_type="면접실",
                required_rooms=["면접실"]
            ),
        ],
        rooms=[
            Room(name="토론실A", room_type="토론실", capacity=6),
            Room(name="면접실1", room_type="면접실", capacity=1),
            Room(name="면접실2", room_type="면접실", capacity=1),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=14)),
        precedence_rules=[
            PrecedenceRule(
                predecessor="토론면접",
                successor="인성면접",
                gap_min=20  # 20분 간격
            )
        ],
        job_activity_matrix={
            ("JOB01", "토론면접"): True,
            ("JOB01", "인성면접"): True,
        }
    )
    
    # 스케줄러 실행
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    # 결과 검증
    print("\n" + "="*60)
    print("Mixed Precedence 테스트 (Batched → Individual)")
    print("="*60)
    
    print(f"\n상태: {result.status}")
    
    if result.status == "SUCCESS":
        print("\n✅ 스케줄링 성공!")
        print("\n[시간 순서대로 정렬]")
        
        sorted_schedule = sorted(result.schedule, key=lambda x: x.time_slot.start)
        for item in sorted_schedule[:10]:
            if not item.applicant_id.startswith("DUMMY_"):
                start_str = item.time_slot.start.strftime("%H:%M")
                end_str = item.time_slot.end.strftime("%H:%M")
                print(f"{start_str} ~ {end_str}: {item.applicant_id} - {item.activity_name}")
        
        if len(sorted_schedule) > 10:
            print(f"... 그 외 {len(sorted_schedule) - 10}개")
            
    else:
        print("\n❌ 스케줄링 실패!")
        print(f"에러: {result.error_message}")


if __name__ == "__main__":
    print("=== Phase 6: Precedence 제약 테스트 ===\n")
    
    # 테스트 1: Batched precedence
    print("1. Batched Precedence 테스트")
    test_batched_precedence()
    
    # 테스트 2: Individual precedence
    print("\n2. Individual Precedence 테스트")
    test_individual_precedence()
    
    # 테스트 3: Mixed precedence
    print("\n3. Mixed Precedence 테스트")
    test_mixed_precedence() 