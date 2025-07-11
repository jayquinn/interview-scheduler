"""
⚡ 빠른 성능 비교: 기존 휴리스틱 vs 통합 CP-SAT
실제 app.py UI 데이터로 성능 개선 측정
"""

import pandas as pd
from datetime import datetime, timedelta
import traceback
import logging
from solver.types import (
    Activity, Room, DateConfig, ActivityMode, PrecedenceRule
)
from solver.single_date_scheduler import SingleDateScheduler

# 로깅 간소화
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_quick_test_scenarios():
    """빠른 테스트용 시나리오들"""
    scenarios = {}
    
    # 기본 활동 설정 (app.py 기반)
    base_activities = [
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
        )
    ]
    
    # 기본 방 설정 (app.py 기반)
    base_rooms = [
        Room(name="토론면접실A", room_type="토론면접실", capacity=6),
        Room(name="토론면접실B", room_type="토론면접실", capacity=6),
        Room(name="발표준비실1", room_type="발표준비실", capacity=2),
        Room(name="발표면접실A", room_type="발표면접실", capacity=1),
        Room(name="발표면접실B", room_type="발표면접실", capacity=1),
    ]
    
    # 선후행 제약
    precedence_rules = [
        PrecedenceRule(
            predecessor="발표준비",
            successor="발표면접",
            gap_min=0,
            is_adjacent=True
        )
    ]
    
    # 직무-활동 매트릭스
    job_activity_matrix = {
        ("JOB01", "토론면접"): True,
        ("JOB01", "발표준비"): True,
        ("JOB01", "발표면접"): True,
    }
    
    # 시나리오 1: 소규모 (6명)
    scenarios["small"] = DateConfig(
        date=datetime(2025, 7, 1),
        jobs={"JOB01": 6},
        activities=base_activities,
        rooms=base_rooms,
        operating_hours=(timedelta(hours=9), timedelta(hours=17, minutes=30)),
        job_activity_matrix=job_activity_matrix,
        precedence_rules=precedence_rules,
        global_gap_min=5
    )
    
    # 시나리오 2: 중규모 (12명)
    scenarios["medium"] = DateConfig(
        date=datetime(2025, 7, 1),
        jobs={"JOB01": 12},
        activities=base_activities,
        rooms=base_rooms,
        operating_hours=(timedelta(hours=9), timedelta(hours=17, minutes=30)),
        job_activity_matrix=job_activity_matrix,
        precedence_rules=precedence_rules,
        global_gap_min=5
    )
    
    return scenarios


def analyze_schedule_results(schedule_items, title):
    """스케줄 결과 분석"""
    if not schedule_items:
        return None
    
    # 지원자별 체류시간 계산
    applicant_times = {}
    for item in schedule_items:
        if item.applicant_id not in applicant_times:
            applicant_times[item.applicant_id] = []
        applicant_times[item.applicant_id].append((item.start_time, item.end_time))
    
    stay_times = []
    for applicant_id, times in applicant_times.items():
        if times:
            first_start = min(t[0] for t in times)
            last_end = max(t[1] for t in times)
            stay_hours = (last_end - first_start).total_seconds() / 3600
            stay_times.append(stay_hours)
    
    if stay_times:
        avg_stay = sum(stay_times) / len(stay_times)
        max_stay = max(stay_times)
        min_stay = min(stay_times)
        long_stay_count = len([t for t in stay_times if t >= 3.0])
        very_long_stay_count = len([t for t in stay_times if t >= 4.0])
        
        return {
            "title": title,
            "applicant_count": len(stay_times),
            "activity_count": len(schedule_items),
            "avg_stay": avg_stay,
            "max_stay": max_stay,
            "min_stay": min_stay,
            "long_stay_count": long_stay_count,
            "very_long_stay_count": very_long_stay_count,
            "stay_times": stay_times
        }
    
    return None


def run_performance_comparison():
    """성능 비교 실행"""
    print("⚡ 빠른 성능 비교 테스트")
    print("=" * 60)
    
    scenarios = create_quick_test_scenarios()
    all_results = {}
    
    for scenario_name, config in scenarios.items():
        print(f"\n{'='*20} {scenario_name.upper()} 시나리오 {'='*20}")
        print(f"지원자 수: {config.jobs['JOB01']}명")
        print(f"활동 수: {len(config.activities)}개")
        print(f"방 수: {len(config.rooms)}개")
        
        scenario_results = {}
        
        # 1. 기존 휴리스틱 방식
        print(f"\n🔧 기존 휴리스틱 방식...")
        try:
            legacy_scheduler = SingleDateScheduler(logger=logger, use_unified_cpsat=False)
            legacy_result = legacy_scheduler.schedule(config)
            
            if legacy_result.status == "SUCCESS":
                legacy_analysis = analyze_schedule_results(legacy_result.schedule, "기존 휴리스틱")
                scenario_results["legacy"] = legacy_analysis
                if legacy_analysis:
                    print(f"  ✅ 성공 - 평균 체류시간: {legacy_analysis['avg_stay']:.1f}시간")
                    print(f"      최대: {legacy_analysis['max_stay']:.1f}h, 3시간+: {legacy_analysis['long_stay_count']}명")
            else:
                print(f"  ❌ 실패: {legacy_result.error_message}")
                scenario_results["legacy"] = None
        except Exception as e:
            print(f"  ❌ 예외: {str(e)}")
            scenario_results["legacy"] = None
        
        # 2. 통합 CP-SAT 방식 (시간 제한 짧게)
        print(f"\n🚀 통합 CP-SAT 방식... (30초 제한)")
        try:
            unified_scheduler = SingleDateScheduler(logger=logger, use_unified_cpsat=True)
            # 스케줄러 시간 제한을 30초로 설정
            unified_scheduler.time_limit_sec = 30.0
            unified_result = unified_scheduler.schedule(config)
            
            if unified_result.status == "SUCCESS":
                unified_analysis = analyze_schedule_results(unified_result.schedule, "통합 CP-SAT")
                scenario_results["unified"] = unified_analysis
                if unified_analysis:
                    print(f"  ✅ 성공 - 평균 체류시간: {unified_analysis['avg_stay']:.1f}시간")
                    print(f"      최대: {unified_analysis['max_stay']:.1f}h, 3시간+: {unified_analysis['long_stay_count']}명")
            else:
                print(f"  ❌ 실패: {unified_result.error_message}")
                # 폴백 결과 확인
                if hasattr(unified_result, 'fallback_used') and unified_result.fallback_used:
                    print(f"  🔄 폴백 사용됨")
                    fallback_analysis = analyze_schedule_results(unified_result.schedule, "폴백 결과")
                    scenario_results["unified"] = fallback_analysis
                else:
                    scenario_results["unified"] = None
        except Exception as e:
            print(f"  ❌ 예외: {str(e)}")
            scenario_results["unified"] = None
        
        # 3. 결과 비교
        if scenario_results["legacy"] and scenario_results["unified"]:
            legacy = scenario_results["legacy"]
            unified = scenario_results["unified"]
            
            avg_improvement = ((legacy["avg_stay"] - unified["avg_stay"]) / legacy["avg_stay"]) * 100
            max_improvement = ((legacy["max_stay"] - unified["max_stay"]) / legacy["max_stay"]) * 100
            long_reduction = legacy["long_stay_count"] - unified["long_stay_count"]
            
            print(f"\n📊 성능 비교 결과:")
            print(f"  평균 체류시간: {legacy['avg_stay']:.1f}h → {unified['avg_stay']:.1f}h ({avg_improvement:+.1f}%)")
            print(f"  최대 체류시간: {legacy['max_stay']:.1f}h → {unified['max_stay']:.1f}h ({max_improvement:+.1f}%)")
            print(f"  3시간+ 체류자: {legacy['long_stay_count']}명 → {unified['long_stay_count']}명 ({long_reduction:+d}명)")
            
            scenario_results["improvement"] = {
                "avg_improvement": avg_improvement,
                "max_improvement": max_improvement,
                "long_reduction": long_reduction
            }
            
            if avg_improvement > 0:
                print(f"  🎉 체류시간 {avg_improvement:.1f}% 단축 성공!")
            elif avg_improvement > -5:
                print(f"  ✅ 비슷한 성능 (차이: {abs(avg_improvement):.1f}%)")
            else:
                print(f"  ⚠️ 성능 저하: {abs(avg_improvement):.1f}%")
        else:
            print(f"  ❌ 비교 불가능 - 일부 방식 실패")
        
        all_results[scenario_name] = scenario_results
    
    # 전체 요약
    print(f"\n{'='*60}")
    print("🏆 전체 성능 비교 요약")
    print(f"{'='*60}")
    
    for scenario_name, results in all_results.items():
        print(f"\n📈 {scenario_name.upper()} 시나리오:")
        if "improvement" in results:
            imp = results["improvement"]
            print(f"  - 평균 체류시간 개선: {imp['avg_improvement']:+.1f}%")
            print(f"  - 최대 체류시간 개선: {imp['max_improvement']:+.1f}%")
            print(f"  - 3시간+ 체류자 감소: {imp['long_reduction']:+d}명")
            
            if imp["avg_improvement"] > 20:
                print(f"  🚀 매우 우수한 개선!")
            elif imp["avg_improvement"] > 10:
                print(f"  ✅ 좋은 개선!")
            elif imp["avg_improvement"] > 0:
                print(f"  👍 개선됨")
            else:
                print(f"  ⚠️ 개선 필요")
        else:
            print(f"  - 테스트 실패 또는 불완전")
    
    return all_results


if __name__ == "__main__":
    try:
        results = run_performance_comparison()
        print(f"\n✅ 성능 비교 테스트 완료!")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        traceback.print_exc() 