#!/usr/bin/env python3
"""
Level 4 후처리 조정 안전성 검증 테스트

토론면접실B 14:00에 10명 이상이 동시에 배정되는 버그가 
재발하지 않도록 안전성을 검증합니다.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime, time, timedelta
from solver.types import (
    DateConfig, Room, Activity, ActivityMode, 
    ScheduleItem, Level4Result
)
from solver.level4_post_processor import Level4PostProcessor
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_schedule() -> list:
    """테스트용 스케줄 생성 - 토론면접 그룹 포함"""
    schedule = []
    
    # 토론면접 그룹 1 (5명) - 오전 10시
    group1_time = timedelta(hours=10)
    for i in range(5):
        schedule.append(ScheduleItem(
            applicant_id=f"JOB02_00{i+1}",
            job_code="JOB02",
            activity_name="토론면접",
            room_name="토론면접실B",
            start_time=group1_time,
            end_time=group1_time + timedelta(minutes=60),
            group_id="GROUP_DISCUSSION_1"
        ))
    
    # 토론면접 그룹 2 (4명) - 오전 11시
    group2_time = timedelta(hours=11)
    for i in range(4):
        schedule.append(ScheduleItem(
            applicant_id=f"JOB02_00{i+6}",
            job_code="JOB02",
            activity_name="토론면접",
            room_name="토론면접실B",
            start_time=group2_time,
            end_time=group2_time + timedelta(minutes=60),
            group_id="GROUP_DISCUSSION_2"
        ))
    
    # 개별 활동들 (체류시간 증가용)
    for i in range(9):
        # 오후 늦은 시간 개별 활동
        individual_time = timedelta(hours=16)
        schedule.append(ScheduleItem(
            applicant_id=f"JOB02_00{i+1}",
            job_code="JOB02",
            activity_name="개별면접",
            room_name="개별면접실1",
            start_time=individual_time,
            end_time=individual_time + timedelta(minutes=20),
            group_id=None
        ))
    
    return schedule

def create_test_config() -> DateConfig:
    """테스트용 설정 생성"""
    rooms = [
        Room(name="토론면접실B", capacity=6, room_type="토론면접"),
        Room(name="개별면접실1", capacity=1, room_type="개별면접")
    ]
    
    activities = [
        Activity(
            name="토론면접",
            mode=ActivityMode.BATCHED,
            duration_min=60,
            room_type="토론면접",
            min_capacity=4,
            max_capacity=6,
            required_rooms=["토론면접"]
        ),
        Activity(
            name="개별면접", 
            mode=ActivityMode.INDIVIDUAL,
            duration_min=20,
            room_type="개별면접",
            min_capacity=1,
            max_capacity=1,
            required_rooms=["개별면접"]
        )
    ]
    
    return DateConfig(
        date=datetime(2025, 7, 7),
        jobs={"JOB02": 9},
        operating_hours=(timedelta(hours=9), timedelta(hours=17)),
        rooms=rooms,
        activities=activities,
        precedence_rules=[]
    )

def test_group_size_validation():
    """그룹 크기 검증 테스트"""
    logger.info("=== 그룹 크기 검증 테스트 ===")
    
    processor = Level4PostProcessor(logger)
    
    # 비정상적으로 큰 그룹 생성 (10명)
    large_group_schedule = []
    group_time = timedelta(hours=10)
    
    for i in range(10):  # 10명 그룹 (비정상)
        large_group_schedule.append(ScheduleItem(
            applicant_id=f"JOB02_0{i+1:02d}",
            job_code="JOB02",
            activity_name="토론면접",
            room_name="토론면접실B",
            start_time=group_time,
            end_time=group_time + timedelta(minutes=60),
            group_id="LARGE_GROUP_TEST"
        ))
    
    # 무결성 검사 실행
    issues = processor._validate_schedule_integrity(large_group_schedule)
    
    if issues:
        logger.info(f"✅ 그룹 크기 검증 성공: {issues}")
        return True
    else:
        logger.error("❌ 그룹 크기 검증 실패: 10명 그룹이 감지되지 않음")
        return False

def test_time_room_conflict_detection():
    """시간-방 중복 배정 검증 테스트"""
    logger.info("=== 시간-방 중복 배정 검증 테스트 ===")
    
    processor = Level4PostProcessor(logger)
    
    # 같은 시간, 같은 방에 여러 그룹 배정
    conflict_schedule = []
    same_time = timedelta(hours=14)
    
    # 그룹 1
    for i in range(4):
        conflict_schedule.append(ScheduleItem(
            applicant_id=f"JOB02_00{i+1}",
            job_code="JOB02",
            activity_name="토론면접",
            room_name="토론면접실B",
            start_time=same_time,
            end_time=same_time + timedelta(minutes=60),
            group_id="GROUP_1"
        ))
    
    # 그룹 2 (같은 시간, 같은 방)
    for i in range(4):
        conflict_schedule.append(ScheduleItem(
            applicant_id=f"JOB02_00{i+5}",
            job_code="JOB02",
            activity_name="토론면접",
            room_name="토론면접실B",
            start_time=same_time,
            end_time=same_time + timedelta(minutes=60),
            group_id="GROUP_2"
        ))
    
    # 무결성 검사 실행
    issues = processor._validate_schedule_integrity(conflict_schedule)
    
    if issues:
        logger.info(f"✅ 시간-방 중복 검증 성공: {issues}")
        return True
    else:
        logger.error("❌ 시간-방 중복 검증 실패: 중복 배정이 감지되지 않음")
        return False

def test_level4_safety():
    """Level 4 후처리 조정 안전성 테스트"""
    logger.info("=== Level 4 후처리 조정 안전성 테스트 ===")
    
    processor = Level4PostProcessor(logger)
    config = create_test_config()
    schedule = create_test_schedule()
    
    # Level 4 후처리 조정 실행
    result = processor.optimize_stay_times(schedule, config)
    
    if result.success:
        # 최종 스케줄 무결성 검사
        final_issues = processor._validate_schedule_integrity(result.optimized_schedule)
        
        if final_issues:
            logger.error(f"❌ Level 4 후처리 조정 안전성 실패: {final_issues}")
            return False
        else:
            logger.info("✅ Level 4 후처리 조정 안전성 검증 성공")
            
            # 결과 분석
            group_counts = {}
            for item in result.optimized_schedule:
                if item.group_id and not item.applicant_id.startswith('dummy'):
                    group_counts[item.group_id] = group_counts.get(item.group_id, 0) + 1
            
            logger.info(f"그룹별 크기: {group_counts}")
            
            # 시간대별 분포 확인
            time_distribution = {}
            for item in result.optimized_schedule:
                if "토론면접" in item.activity_name:
                    time_key = f"{item.start_time} {item.room_name}"
                    if time_key not in time_distribution:
                        time_distribution[time_key] = []
                    time_distribution[time_key].append(item.applicant_id)
            
            logger.info("시간대별 분포:")
            for time_room, applicants in time_distribution.items():
                logger.info(f"  {time_room}: {len(applicants)}명")
            
            return True
    else:
        logger.info("Level 4 후처리 조정이 안전하게 실행되지 않음 (정상)")
        return True

def main():
    """메인 테스트 실행"""
    logger.info("🔧 Level 4 후처리 조정 안전성 검증 시작")
    
    tests = [
        ("그룹 크기 검증", test_group_size_validation),
        ("시간-방 중복 검증", test_time_room_conflict_detection),
        ("Level 4 안전성", test_level4_safety)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            logger.info(f"{'✅' if result else '❌'} {test_name}: {'통과' if result else '실패'}")
        except Exception as e:
            logger.error(f"❌ {test_name}: 예외 발생 - {str(e)}")
            results.append((test_name, False))
    
    # 최종 결과
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    logger.info(f"\n🎯 최종 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        logger.info("✅ 모든 안전성 검증 통과! Level 4 후처리 조정이 안전합니다.")
        return True
    else:
        logger.error("❌ 일부 안전성 검증 실패. 추가 수정이 필요합니다.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 