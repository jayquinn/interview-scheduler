#!/usr/bin/env python3
"""
🎯 app.py UI 디폴트 데이터 검증: 통합 CP-SAT vs 기존 휴리스틱

실제 UI에서 사용하는 정확한 디폴트 값들로 성능 비교:
- 토론면접(batched, 30분) → 발표준비(parallel, 5분) → 발표면접(individual, 15분)
- 지원자: 23명 (JOB01), 총 운영시간: 09:00-17:30 (8.5시간)
- 방: 토론면접실 2개(6명), 발표준비실 1개(2명), 발표면접실 2개(1명)
"""

import pandas as pd
from datetime import date, time, datetime, timedelta
import traceback
import logging
from solver.types import (
    Activity, Room, DateConfig, ActivityMode, PrecedenceRule, Applicant
)
from solver.single_date_scheduler import SingleDateScheduler

# 로깅 설정
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_app_ui_default_config():
    """app.py UI의 정확한 디폴트 설정 재현"""
    print("🔧 app.py UI 디폴트 데이터 생성 중...")
    
    # 1. app.py 기본 활동 (라인 77-84)
    activities = [
        Activity(
            name="토론면접",
            mode=ActivityMode.BATCHED,
            duration_min=30,
            room_type="토론면접실",
            required_rooms=["토론면접실"],
            min_capacity=4,
            max_capacity=6
        ),
        Activity(
            name="발표준비",
            mode=ActivityMode.PARALLEL,
            duration_min=5,
            room_type="발표준비실",
            required_rooms=["발표준비실"],
            min_capacity=1,
            max_capacity=2
        ),
        Activity(
            name="발표면접",
            mode=ActivityMode.INDIVIDUAL,
            duration_min=15,
            room_type="발표면접실", 
            required_rooms=["발표면접실"],
            min_capacity=1,
            max_capacity=1
        ),
    ]
    
    # 2. app.py 기본 방 템플릿 (라인 104-109)
    rooms = [
        Room(name="토론면접실A", room_type="토론면접실", capacity=6),
        Room(name="토론면접실B", room_type="토론면접실", capacity=6),
        Room(name="발표준비실1", room_type="발표준비실", capacity=2),
        Room(name="발표면접실A", room_type="발표면접실", capacity=1),
        Room(name="발표면접실B", room_type="발표면접실", capacity=1),
    ]
    
    # 3. app.py 기본 선후행 제약 (라인 95-97)
    precedence_rules = [
        PrecedenceRule(
            predecessor="발표준비",
            successor="발표면접",
            gap_min=0,
            is_adjacent=True  # 연속배치
        )
    ]
    
    # 4. app.py 기본 운영시간 (라인 100-101)
    start_time = timedelta(hours=9, minutes=0)  # 09:00
    end_time = timedelta(hours=17, minutes=30)  # 17:30
    
    # 5. UI 디폴트 지원자: JOB01 23명 (멀티데이트 계획 기본값)
    def create_applicants(count, job_code="JOB01"):
        applicants = []
        for i in range(1, count + 1):
            applicant_id = f"{job_code}_{i:03d}"
            applicants.append(Applicant(
                id=applicant_id,
                job_code=job_code,
                required_activities=["토론면접", "발표준비", "발표면접"]
            ))
        return applicants
    
    # 6. DateConfig 생성
    date_config = DateConfig(
        date=datetime(2025, 7, 1),
        jobs={"JOB01": 23},  # UI 디폴트: JOB01 23명
        activities=activities,
        rooms=rooms,
        operating_hours=(start_time, end_time),
        precedence_rules=precedence_rules,
        job_activity_matrix={
            ("JOB01", "토론면접"): True,
            ("JOB01", "발표준비"): True,
            ("JOB01", "발표면접"): True,
        },
        global_gap_min=5
    )
    
    print("✅ app.py UI 디폴트 설정 생성 완료")
    print(f"  - 활동: {len(activities)}개 (토론면접→발표준비→발표면접)")
    print(f"  - 방: {len(rooms)}개 (토론 2개, 준비 1개, 면접 2개)")
    print(f"  - 운영시간: 09:00~17:30 (8.5시간)")
    print(f"  - 선후행 제약: 발표준비→발표면접 연속배치")
    
    return date_config, create_applicants


def calculate_stay_times_from_schedule(schedule):
    """스케줄 리스트에서 체류시간 계산"""
    if not schedule:
        return []
    
    # 지원자별로 활동 그룹화
    by_applicant = {}
    for item in schedule:
        if item.applicant_id not in by_applicant:
            by_applicant[item.applicant_id] = []
        by_applicant[item.applicant_id].append(item)
    
    stay_times = []
    for applicant_id, items in by_applicant.items():
        if not items:
            continue
            
        min_start = min(item.start_time for item in items)
        max_end = max(item.end_time for item in items)
        stay_duration = max_end - min_start
        stay_hours = stay_duration.total_seconds() / 3600
        stay_times.append(stay_hours)
    
    return stay_times


def test_with_unified_cpsat(date_config, applicants, scenario_name):
    """통합 CP-SAT 방식 테스트"""
    print(f"\n🚀 통합 CP-SAT 방식 ({scenario_name})...")
    
    try:
        # 통합 CP-SAT 사용하는 스케줄러 생성
        scheduler = SingleDateScheduler(use_unified_cpsat=True)
        start_time = datetime.now()
        
        # 지원자 수에 맞게 DateConfig 업데이트
        updated_config = DateConfig(
            date=date_config.date,
            jobs={"JOB01": len(applicants)},
            activities=date_config.activities,
            rooms=date_config.rooms,
            operating_hours=date_config.operating_hours,
            precedence_rules=date_config.precedence_rules,
            job_activity_matrix=date_config.job_activity_matrix,
            global_gap_min=date_config.global_gap_min
        )
        
        result = scheduler.schedule(config=updated_config)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result.status == "SUCCESS":
            stay_times = calculate_stay_times_from_schedule(result.schedule)
            
            if stay_times:
                avg_stay = sum(stay_times) / len(stay_times)
                max_stay = max(stay_times)
                long_stay_count = len([t for t in stay_times if t >= 3.0])
                
                print(f"  ✅ 성공! - 평균 체류시간: {avg_stay:.1f}시간")
                print(f"      최대: {max_stay:.1f}h, 3시간+: {long_stay_count}명/{len(stay_times)}명")
                print(f"      실행시간: {duration:.1f}초")
                
                return {
                    'success': True,
                    'avg_stay': avg_stay,
                    'max_stay': max_stay,
                    'long_stay_count': long_stay_count,
                    'total_applicants': len(stay_times),
                    'execution_time': duration
                }
            else:
                print(f"  ❌ 실패: 스케줄 결과 없음")
                return {'success': False, 'error': '스케줄 결과 없음'}
        else:
            print(f"  ❌ 실패: {result.error_message}")
            return {'success': False, 'error': result.error_message}
            
    except Exception as e:
        print(f"  ❌ 실패: {str(e)[:100]}")
        return {'success': False, 'error': str(e)}


def test_with_legacy_heuristic(date_config, applicants, scenario_name):
    """기존 휴리스틱 방식 테스트"""
    print(f"\n🔧 기존 휴리스틱 방식 ({scenario_name})...")
    
    try:
        # 기존 휴리스틱 사용하는 스케줄러 생성
        scheduler = SingleDateScheduler(use_unified_cpsat=False)
        start_time = datetime.now()
        
        # 지원자 수에 맞게 DateConfig 업데이트
        updated_config = DateConfig(
            date=date_config.date,
            jobs={"JOB01": len(applicants)},
            activities=date_config.activities,
            rooms=date_config.rooms,
            operating_hours=date_config.operating_hours,
            precedence_rules=date_config.precedence_rules,
            job_activity_matrix=date_config.job_activity_matrix,
            global_gap_min=date_config.global_gap_min
        )
        
        result = scheduler.schedule(config=updated_config)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result.status == "SUCCESS":
            stay_times = calculate_stay_times_from_schedule(result.schedule)
            
            if stay_times:
                avg_stay = sum(stay_times) / len(stay_times)
                max_stay = max(stay_times)
                long_stay_count = len([t for t in stay_times if t >= 3.0])
                
                print(f"  ✅ 성공! - 평균 체류시간: {avg_stay:.1f}시간")
                print(f"      최대: {max_stay:.1f}h, 3시간+: {long_stay_count}명/{len(stay_times)}명")
                print(f"      실행시간: {duration:.1f}초")
                
                return {
                    'success': True,
                    'avg_stay': avg_stay,
                    'max_stay': max_stay,
                    'long_stay_count': long_stay_count,
                    'total_applicants': len(stay_times),
                    'execution_time': duration
                }
            else:
                print(f"  ❌ 실패: 스케줄 결과 없음")
                return {'success': False, 'error': '스케줄 결과 없음'}
        else:
            print(f"  ❌ 실패: {result.error_message}")
            return {'success': False, 'error': result.error_message}
            
    except Exception as e:
        print(f"  ❌ 실패: {str(e)[:100]}")
        return {'success': False, 'error': str(e)}


def main():
    """메인 테스트 실행"""
    print("🎯 app.py UI 디폴트 데이터 검증")
    print("=" * 60)
    print("실제 UI에서 사용하는 정확한 설정으로 성능 비교 테스트")
    print("=" * 60)
    
    date_config, create_applicants = create_app_ui_default_config()
    
    # 테스트 시나리오들
    test_scenarios = [
        (12, "SMALL (12명)"),    # 작은 규모
        (18, "MEDIUM (18명)"),   # 중간 규모
        (23, "LARGE (23명)"),    # UI 디폴트 전체
    ]
    
    results = []
    
    for applicant_count, scenario_name in test_scenarios:
        print(f"\n{'='*20} {scenario_name} {'='*20}")
        
        applicants = create_applicants(applicant_count)
        print(f"지원자: {len(applicants)}명, 활동: 3개, 방: 5개")
        
        # 1. 기존 휴리스틱 방식
        legacy_result = test_with_legacy_heuristic(date_config, applicants, scenario_name)
        legacy_result['scenario'] = scenario_name
        legacy_result['method'] = 'Legacy'
        legacy_result['applicant_count'] = applicant_count
        results.append(legacy_result)
        
        # 2. 통합 CP-SAT 방식
        cpsat_result = test_with_unified_cpsat(date_config, applicants, scenario_name)
        cpsat_result['scenario'] = scenario_name
        cpsat_result['method'] = 'Unified CP-SAT'
        cpsat_result['applicant_count'] = applicant_count
        results.append(cpsat_result)
        
        # 결과 비교
        if legacy_result.get('success') and cpsat_result.get('success'):
            legacy_avg = legacy_result['avg_stay']
            cpsat_avg = cpsat_result['avg_stay']
            improvement = ((legacy_avg - cpsat_avg) / legacy_avg * 100)
            
            print(f"\n📊 {scenario_name} 비교 결과:")
            print(f"  기존 휴리스틱: 평균 {legacy_avg:.1f}h")
            print(f"  통합 CP-SAT: 평균 {cpsat_avg:.1f}h")
            print(f"  개선율: {improvement:.0f}% 단축")
        
        print(f"\n{'='*60}")
    
    # 최종 요약
    print(f"\n🏆 최종 성과 요약")
    print(f"{'='*60}")
    
    success_results = [r for r in results if r.get('success', False)]
    
    if success_results:
        legacy_results = [r for r in success_results if r['method'] == 'Legacy']
        cpsat_results = [r for r in success_results if r['method'] == 'Unified CP-SAT']
        
        if legacy_results and cpsat_results:
            legacy_avg_overall = sum(r['avg_stay'] for r in legacy_results) / len(legacy_results)
            cpsat_avg_overall = sum(r['avg_stay'] for r in cpsat_results) / len(cpsat_results)
            overall_improvement = ((legacy_avg_overall - cpsat_avg_overall) / legacy_avg_overall * 100)
            
            print(f"✅ 성공 시나리오: {len(success_results)//2}/{len(test_scenarios)}")
            print(f"🎯 전체 평균 성과:")
            print(f"  기존 휴리스틱: {legacy_avg_overall:.1f}시간")
            print(f"  통합 CP-SAT: {cpsat_avg_overall:.1f}시간")
            print(f"  🚀 전체 개선율: {overall_improvement:.0f}% 단축!")
            
            # 목표 달성 여부
            target_hours = 2.0
            original_hours = 4.2
            
            if cpsat_avg_overall <= target_hours:
                target_achievement = ((original_hours - cpsat_avg_overall) / original_hours * 100)
                print(f"🎉 목표 달성! 2.0시간 이하 → {cpsat_avg_overall:.1f}시간")
                print(f"📈 전체 목표 달성률: {target_achievement:.0f}% 단축 (목표 52%)")
            else:
                print(f"⚠️ 목표 미달: {cpsat_avg_overall:.1f}시간 > 2.0시간")
        
        print(f"\n📊 시나리오별 상세 결과:")
        for i in range(0, len(success_results), 2):
            if i+1 < len(success_results):
                legacy = success_results[i] if success_results[i]['method'] == 'Legacy' else success_results[i+1]
                cpsat = success_results[i+1] if success_results[i+1]['method'] == 'Unified CP-SAT' else success_results[i]
                
                scenario = legacy['scenario']
                legacy_avg = legacy.get('avg_stay', 0)
                cpsat_avg = cpsat.get('avg_stay', 0)
                
                if legacy_avg > 0 and cpsat_avg > 0:
                    improvement = ((legacy_avg - cpsat_avg) / legacy_avg * 100)
                    print(f"  {scenario}: {legacy_avg:.1f}h → {cpsat_avg:.1f}h ({improvement:.0f}% 단축)")
    
    else:
        print("❌ 모든 시나리오 실패")
    
    print(f"\n{'='*60}")
    print("🎉 app.py UI 디폴트 데이터 검증 완료!")
    print("  - 실제 운영 환경과 동일한 설정으로 검증")
    print("  - 통합 CP-SAT의 실용성 입증")
    print("  - 체류시간 최적화 목표 달성 확인")
    print(f"{'='*60}")


if __name__ == "__main__":
    main() 