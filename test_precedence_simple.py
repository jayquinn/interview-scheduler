"""
간단한 Precedence 테스트
"""
from datetime import datetime, timedelta
from solver.types import (
    DateConfig, Activity, Room, ActivityType, PrecedenceRule
)
from solver.single_date_scheduler import SingleDateScheduler
import logging

# 로깅 설정
logging.basicConfig(level=logging.WARNING, format='%(message)s')


def test_simple_precedence():
    """가장 간단한 precedence 테스트"""
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "JOB01": 4,  # 4명
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
        operating_hours=(timedelta(hours=9), timedelta(hours=12)),
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
    
    # 결과 출력
    print("\n=== 간단한 Precedence 테스트 ===")
    print(f"상태: {result.status}")
    
    if result.status == "SUCCESS":
        print("\n✅ 스케줄링 성공!")
        
        # 시간순으로 정렬
        sorted_schedule = sorted(result.schedule, key=lambda x: x.time_slot.start)
        
        # 활동별 시간 확인
        prep_time = None
        pres_time = None
        
        print("\n[전체 스케줄]")
        for item in sorted_schedule:
            if not item.applicant_id.startswith("DUMMY_"):
                start_str = item.time_slot.start.strftime("%H:%M")
                end_str = item.time_slot.end.strftime("%H:%M")
                print(f"{start_str} ~ {end_str}: {item.applicant_id} - {item.activity_name}")
                
                if item.activity_name == "발표준비" and prep_time is None:
                    prep_time = item.time_slot
                elif item.activity_name == "발표면접" and pres_time is None:
                    pres_time = item.time_slot
        
        # Precedence 검증
        if prep_time and pres_time:
            gap = (pres_time.start - prep_time.end).total_seconds() / 60
            print(f"\n[Precedence 검증]")
            print(f"발표준비 종료: {prep_time.end.strftime('%H:%M')}")
            print(f"발표면접 시작: {pres_time.start.strftime('%H:%M')}")
            print(f"간격: {int(gap)}분")
            
            if gap >= 10:
                print("✅ Precedence 준수!")
            else:
                print("❌ Precedence 위반!")
    else:
        print("\n❌ 스케줄링 실패!")
        print(f"에러: {result.error_message}")
        
        # 로그 출력
        print("\n[로그]")
        for log in result.logs[-5:]:
            print(f"  {log}")


if __name__ == "__main__":
    test_simple_precedence() 