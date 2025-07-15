#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solver.types import (
    DateConfig, Activity, Room, Applicant, 
    PrecedenceRule, ActivityMode
)
from solver.api import SingleDateScheduler
from datetime import datetime, timedelta, time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_config():
    """테스트용 설정 생성"""
    # 시간 설정
    date_str = "2024-01-15"
    start_time = timedelta(hours=9, minutes=0)
    end_time = timedelta(hours=18, minutes=0)
    
    # 활동 정의
    activities = [
        Activity(
            name="토론면접",
            mode=ActivityMode.BATCHED,
            duration_min=30,
            room_type="discussion",
            required_rooms=["discussion"],
            min_capacity=4,
            max_capacity=6
        ),
        Activity(
            name="발표준비",
            mode=ActivityMode.PARALLEL,
            duration_min=5,
            room_type="preparation",
            required_rooms=["preparation"],
            min_capacity=1,
            max_capacity=2
        ),
        Activity(
            name="발표면접",
            mode=ActivityMode.INDIVIDUAL,
            duration_min=15,
            room_type="presentation",
            required_rooms=["presentation"],
            min_capacity=1,
            max_capacity=1
        )
    ]
    
    # 방 정의
    rooms = [
        Room(name="토론면접실1", room_type="discussion", capacity=6),
        Room(name="토론면접실2", room_type="discussion", capacity=6),
        Room(name="발표준비실", room_type="preparation", capacity=2),
        Room(name="발표면접실1", room_type="presentation", capacity=1),
        Room(name="발표면접실2", room_type="presentation", capacity=1)
    ]
    
    # 지원자 정의 (6명)
    applicants = [
        Applicant(id=f"JOB01_{i:03d}", job_code="JOB01", required_activities=["토론면접", "발표준비", "발표면접"])
        for i in range(1, 7)
    ]
    
    # 선후행 규칙
    precedence_rules = [
        PrecedenceRule(
            predecessor="발표준비",
            successor="발표면접",
            gap_min=5
        )
    ]
    
    # 직무별 인원수
    jobs = {"JOB01": 6}
    
    config = DateConfig(
        date=datetime.strptime(date_str, "%Y-%m-%d"),
        jobs=jobs,
        activities=activities,
        rooms=rooms,
        operating_hours=(start_time, end_time),
        precedence_rules=precedence_rules,
        job_activity_matrix={("JOB01", "토론면접"): True, ("JOB01", "발표준비"): True, ("JOB01", "발표면접"): True}
    )
    
    return config

def calculate_stay_time(result):
    """체류시간 계산"""
    if not result or not result.level2_result or not result.level3_result or not result.level4_result:
        return None
    
    batched_items = result.level2_result.schedule or []
    individual_items = result.level3_result.schedule or []
    
    # Level4Result의 올바른 속성 사용
    level4_items = result.level4_result.optimized_schedule or []
    
    all_items = batched_items + individual_items + level4_items
    
    # 지원자별 체류시간 계산
    applicant_times = {}
    for item in all_items:
        if hasattr(item, 'applicant_id') and item.applicant_id:
            if item.applicant_id not in applicant_times:
                applicant_times[item.applicant_id] = {'start': item.start_time, 'end': item.end_time}
            else:
                applicant_times[item.applicant_id]['start'] = min(applicant_times[item.applicant_id]['start'], item.start_time)
                applicant_times[item.applicant_id]['end'] = max(applicant_times[item.applicant_id]['end'], item.end_time)
    
    stay_times = []
    for applicant_id, times in applicant_times.items():
        stay_time = (times['end'] - times['start']).total_seconds() / 3600
        if stay_time > 0:
            stay_times.append(stay_time)
    
    if stay_times:
        return {
            'avg': sum(stay_times) / len(stay_times),
            'max': max(stay_times),
            'count': len(stay_times)
        }
    return None

def main():
    print("*** 간단한 CP-SAT vs 휴리스틱 비교 테스트 ***")
    print("=" * 60)
    
    config = create_test_config()
    
    # 1. 휴리스틱 방식 테스트
    print("\n[1] 휴리스틱 방식 테스트...")
    try:
        heuristic_scheduler = SingleDateScheduler(use_unified_cpsat=False)
        heuristic_result = heuristic_scheduler.schedule(config)
        
        if heuristic_result.error_message:
            print(f"  실패: {heuristic_result.error_message}")
            heuristic_stats = None
        else:
            heuristic_stats = calculate_stay_time(heuristic_result)
            if heuristic_stats:
                print(f"  성공: 평균 {heuristic_stats['avg']:.1f}h, 최대 {heuristic_stats['max']:.1f}h")
            else:
                print("  실패: 체류시간 계산 불가")
                heuristic_stats = None
    except Exception as e:
        print(f"  예외: {str(e)}")
        heuristic_stats = None
    
    # 2. CP-SAT 방식 테스트
    print("\n[2] CP-SAT 방식 테스트...")
    try:
        cpsat_scheduler = SingleDateScheduler(use_unified_cpsat=True)
        cpsat_result = cpsat_scheduler.schedule(config)
        
        if cpsat_result.error_message:
            print(f"  실패: {cpsat_result.error_message}")
            cpsat_stats = None
        else:
            cpsat_stats = calculate_stay_time(cpsat_result)
            if cpsat_stats:
                print(f"  성공: 평균 {cpsat_stats['avg']:.1f}h, 최대 {cpsat_stats['max']:.1f}h")
            else:
                print("  실패: 체류시간 계산 불가")
                cpsat_stats = None
    except Exception as e:
        print(f"  예외: {str(e)}")
        cpsat_stats = None
    
    # 3. 결과 비교
    print("\n" + "=" * 60)
    print("*** 비교 결과 ***")
    print("=" * 60)
    
    if heuristic_stats and cpsat_stats:
        print(f"휴리스틱: 평균 {heuristic_stats['avg']:.1f}h, 최대 {heuristic_stats['max']:.1f}h")
        print(f"CP-SAT:   평균 {cpsat_stats['avg']:.1f}h, 최대 {cpsat_stats['max']:.1f}h")
        
        improvement = ((heuristic_stats['avg'] - cpsat_stats['avg']) / heuristic_stats['avg']) * 100
        print(f"개선율: {improvement:.1f}%")
        
        if cpsat_stats['avg'] < heuristic_stats['avg']:
            print("결론: CP-SAT가 더 우수한 성과를 보임!")
        else:
            print("결론: 휴리스틱이 더 우수한 성과를 보임!")
    elif cpsat_stats:
        print(f"CP-SAT만 성공: 평균 {cpsat_stats['avg']:.1f}h, 최대 {cpsat_stats['max']:.1f}h")
        print("결론: CP-SAT가 안정적으로 작동함!")
    elif heuristic_stats:
        print(f"휴리스틱만 성공: 평균 {heuristic_stats['avg']:.1f}h, 최대 {heuristic_stats['max']:.1f}h")
        print("결론: 휴리스틱이 더 안정적임!")
    else:
        print("둘 다 실패!")

if __name__ == "__main__":
    main() 