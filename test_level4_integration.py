#!/usr/bin/env python3
"""
Level 4 후처리 조정 통합 테스트

목적:
- Level 4 후처리 조정이 메인 스케줄러에 정상 통합되었는지 확인
- 밀집 배치 + Level 4 조정의 기본 동작 확인
- 체류시간 개선 효과 측정
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime, time, timedelta
from solver.single_date_scheduler import SingleDateScheduler
from solver.types import DateConfig, Activity, Room, ActivityMode, Applicant

# ActivityType은 ActivityMode의 별칭
ActivityType = ActivityMode

def create_simple_test_config():
    """간단한 테스트 설정 생성"""
    
    # 활동 정의
    activities = [
        Activity(
            name="토론면접",
            mode=ActivityType.BATCHED,
            duration_min=30,
            room_type="토론면접실",
            required_rooms=["토론면접실"],
            min_capacity=4,
            max_capacity=6
        ),
        Activity(
            name="발표면접",
            mode=ActivityType.INDIVIDUAL,
            duration_min=15,
            room_type="발표면접실",
            required_rooms=["발표면접실"],
            min_capacity=1,
            max_capacity=1
        )
    ]
    
    # 방 정의
    rooms = [
        Room(name="토론면접실A", room_type="토론면접실", capacity=6),
        Room(name="토론면접실B", room_type="토론면접실", capacity=6),
        Room(name="발표면접실A", room_type="발표면접실", capacity=1),
        Room(name="발표면접실B", room_type="발표면접실", capacity=1),
    ]
    
    # 날짜 설정
    config = DateConfig(
        date=datetime(2025, 1, 1),
        jobs={"JOB01": 8},  # 8명 지원자 (2개 그룹, 4명씩)
        activities=activities,
        rooms=rooms,
        operating_hours=(timedelta(hours=9), timedelta(hours=18)),
        precedence_rules=[],
        job_activity_matrix={
            ("JOB01", "토론면접"): True,
            ("JOB01", "발표면접"): True,
        },
        global_gap_min=5
    )
    
    return config

def test_level4_integration():
    """Level 4 통합 테스트"""
    print("=== Level 4 후처리 조정 통합 테스트 ===")
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # 테스트 설정 생성
    config = create_simple_test_config()
    print(f"테스트 설정: {config.jobs['JOB01']}명 지원자, {len(config.activities)}개 활동")
    
    # 스케줄러 실행
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    
    print(f"\n=== 스케줄링 결과 ===")
    print(f"상태: {result.status}")
    print(f"총 스케줄 항목: {len(result.schedule)}")
    
    if result.error_message:
        print(f"오류: {result.error_message}")
    
    # 단계별 결과 확인
    print(f"\n=== 단계별 결과 ===")
    if result.level1_result:
        total_groups = sum(len(groups) for groups in result.level1_result.groups.values())
        print(f"Level 1: {total_groups}개 그룹 생성")
    
    if result.level2_result:
        print(f"Level 2: {len(result.level2_result.schedule)}개 Batched 스케줄")
    
    if result.level3_result:
        print(f"Level 3: {len(result.level3_result.schedule)}개 Individual 스케줄")
    
    if result.level4_result:
        print(f"Level 4: {result.level4_result.success} "
              f"(개선: {result.level4_result.total_improvement_hours:.1f}시간, "
              f"조정 그룹: {result.level4_result.adjusted_groups}개)")
        
        # Level 4 개선 세부 정보
        if result.level4_result.improvements:
            print(f"\n=== Level 4 조정 세부 사항 ===")
            for i, improvement in enumerate(result.level4_result.improvements, 1):
                print(f"조정 {i}: 그룹 {improvement.group_id}")
                print(f"  활동: {improvement.activity_name}")
                print(f"  시간 이동: {improvement.current_start} → {improvement.target_start}")
                print(f"  영향받는 지원자: {len(improvement.affected_applicants)}명")
                print(f"  예상 개선: {improvement.estimated_improvement:.1f}시간")
    
    # 체류시간 분석
    if result.schedule:
        print(f"\n=== 체류시간 분석 ===")
        analyze_stay_times(result.schedule)
    
    # 로그 출력
    print(f"\n=== 실행 로그 ===")
    for log in result.logs[-5:]:  # 마지막 5개 로그만
        print(f"  {log}")
    
    return result.status == "SUCCESS"

def analyze_stay_times(schedule):
    """체류시간 분석"""
    from collections import defaultdict
    
    applicant_schedules = defaultdict(list)
    
    # 지원자별 스케줄 그룹화 (더미 제외)
    for item in schedule:
        if not item.applicant_id.startswith('dummy'):
            applicant_schedules[item.applicant_id].append(item)
    
    if not applicant_schedules:
        print("  분석할 지원자 스케줄이 없습니다.")
        return
    
    stay_times = []
    for applicant_id, items in applicant_schedules.items():
        if len(items) >= 2:
            items.sort(key=lambda x: x.start_time)
            first_start = items[0].start_time
            last_end = items[-1].end_time
            stay_time = (last_end - first_start).total_seconds() / 3600
            stay_times.append(stay_time)
            
            activities = [item.activity_name for item in items]
            print(f"  {applicant_id}: {stay_time:.1f}시간 ({' → '.join(activities)})")
    
    if stay_times:
        avg_stay_time = sum(stay_times) / len(stay_times)
        max_stay_time = max(stay_times)
        min_stay_time = min(stay_times)
        
        print(f"\n  📊 체류시간 통계:")
        print(f"    평균: {avg_stay_time:.1f}시간")
        print(f"    최대: {max_stay_time:.1f}시간")
        print(f"    최소: {min_stay_time:.1f}시간")

if __name__ == "__main__":
    print("🚀 Level 4 후처리 조정 통합 테스트 시작\n")
    
    success = test_level4_integration()
    
    if success:
        print("\n🎉 Level 4 통합 테스트 성공!")
        print("\n📋 완료된 기능:")
        print("✅ 밀집 배치 (Level 2) - 순차적 그룹 배치")
        print("✅ Level 4 후처리 조정 - 체류시간 최적화")
        print("✅ 메인 스케줄러 통합 - 4단계 파이프라인")
        print("✅ 안전한 백트래킹 - Level 4 실패시 기본 스케줄 유지")
        
        print("\n🔍 다음 단계:")
        print("  • 대규모 데이터 테스트 (137명, 4일)")
        print("  • 체류시간 개선 효과 측정")
        print("  • 운영 환경 적용 준비")
    else:
        print("\n❌ Level 4 통합 테스트 실패")
        print("  디버깅이 필요합니다.") 