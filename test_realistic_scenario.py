"""
🚀 실제 시나리오 테스트: app.py UI 데이터로 통합 CP-SAT 성능 검증

1. app.py 기본 데이터 사용
2. 기존 휴리스틱 vs 통합 CP-SAT 비교  
3. INFEASIBLE 문제 해결 과정
4. 성능 개선 측정
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
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_realistic_scenario_config() -> DateConfig:
    """app.py UI 데이터를 기반으로 한 현실적 시나리오 구성"""
    print("🔧 실제 UI 시나리오 데이터 생성 중...")
    
    # 1. app.py 기본 활동 (라인 77-84)
    activities = [
        Activity(
            name="토론면접",
            mode=ActivityMode.BATCHED,
            duration_min=30,  # app.py 기본값
            room_type="토론면접실",
            required_rooms=["토론면접실"],
            min_capacity=4,
            max_capacity=6
        ),
        Activity(
            name="발표준비",
            mode=ActivityMode.PARALLEL,
            duration_min=5,  # app.py 기본값
            room_type="발표준비실",
            required_rooms=["발표준비실"],
            min_capacity=1,
            max_capacity=2
        ),
        Activity(
            name="발표면접",
            mode=ActivityMode.INDIVIDUAL,
            duration_min=15,  # app.py 기본값
            room_type="발표면접실",
            required_rooms=["발표면접실"],
            min_capacity=1,
            max_capacity=1
        )
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
            is_adjacent=True
        )
    ]
    
    # 4. 직무-활동 매트릭스 (모든 지원자가 모든 활동 수행)
    job_activity_matrix = {
        ("JOB01", "토론면접"): True,
        ("JOB01", "발표준비"): True,
        ("JOB01", "발표면접"): True,
    }
    
    # 5. 시나리오별 지원자 수 조정
    scenarios = {
        "small": 6,   # 작은 규모 - 디버깅용
        "medium": 12, # 중간 규모 - 현실적
        "large": 24   # 큰 규모 - 스트레스 테스트
    }
    
    return {
        "activities": activities,
        "rooms": rooms,
        "precedence_rules": precedence_rules,
        "job_activity_matrix": job_activity_matrix,
        "scenarios": scenarios,
        "operating_hours": (timedelta(hours=9), timedelta(hours=17, minutes=30)),  # 09:00 ~ 17:30
        "global_gap_min": 5
    }


def create_test_config(scenario_size: str) -> DateConfig:
    """시나리오별 DateConfig 생성"""
    base_config = create_realistic_scenario_config()
    applicant_count = base_config["scenarios"][scenario_size]
    
    return DateConfig(
        date=datetime(2025, 7, 1),
        jobs={"JOB01": applicant_count},
        activities=base_config["activities"],
        rooms=base_config["rooms"],
        operating_hours=base_config["operating_hours"],
        job_activity_matrix=base_config["job_activity_matrix"],
        precedence_rules=base_config["precedence_rules"],
        global_gap_min=base_config["global_gap_min"]
    )


def analyze_schedule_performance(schedule, title, scenario_size):
    """스케줄 성능 분석"""
    print(f"\n=== {title} ({scenario_size} 시나리오) ===")
    
    if not schedule:
        print("❌ 스케줄 없음")
        return None, None, None
    
    # 지원자별 체류시간 계산
    applicant_times = {}
    for item in schedule:
        if item.applicant_id not in applicant_times:
            applicant_times[item.applicant_id] = []
        applicant_times[item.applicant_id].append((item.start_time, item.end_time))
    
    stay_times = []
    activity_counts = {}
    
    for applicant_id, times in applicant_times.items():
        if times:
            first_start = min(t[0] for t in times)
            last_end = max(t[1] for t in times)
            stay_hours = (last_end - first_start).total_seconds() / 3600
            stay_times.append(stay_hours)
            activity_counts[applicant_id] = len(times)
            
            print(f"  {applicant_id}: {stay_hours:.1f}시간 ({len(times)}개 활동)")
    
    if stay_times:
        avg_stay = sum(stay_times) / len(stay_times)
        max_stay = max(stay_times)
        min_stay = min(stay_times)
        long_stay_count = len([t for t in stay_times if t >= 3.0])
        very_long_stay_count = len([t for t in stay_times if t >= 4.0])
        
        print(f"\n📊 체류시간 통계:")
        print(f"  평균: {avg_stay:.1f}시간")
        print(f"  최대: {max_stay:.1f}시간")
        print(f"  최소: {min_stay:.1f}시간")
        print(f"  3시간 이상: {long_stay_count}명 ({long_stay_count/len(stay_times)*100:.1f}%)")
        print(f"  4시간 이상: {very_long_stay_count}명 ({very_long_stay_count/len(stay_times)*100:.1f}%)")
        
        # 활동별 분포
        total_activities = sum(activity_counts.values())
        expected_activities = len(stay_times) * 3  # 3개 활동 기대
        print(f"  총 스케줄된 활동: {total_activities}/{expected_activities} ({total_activities/expected_activities*100:.1f}%)")
        
        return avg_stay, max_stay, long_stay_count
    
    return 0, 0, 0


def test_scenario_progression():
    """시나리오 크기별 점진적 테스트"""
    print("🚀 실제 시나리오 점진적 테스트")
    print("=" * 70)
    
    results = {}
    
    for scenario in ["small", "medium"]:  # large는 나중에
        print(f"\n{'='*20} {scenario.upper()} 시나리오 {'='*20}")
        
        config = create_test_config(scenario)
        applicant_count = config.jobs["JOB01"]
        
        print(f"📋 시나리오 정보:")
        print(f"  - 지원자 수: {applicant_count}명")
        print(f"  - 활동 수: {len(config.activities)}개")
        print(f"  - 방 수: {len(config.rooms)}개")
        print(f"  - 운영시간: {config.operating_hours[0]} ~ {config.operating_hours[1]}")
        
        scenario_results = {}
        
        # 1. 기존 방식 테스트
        print(f"\n🔧 기존 휴리스틱 방식 테스트...")
        try:
            legacy_scheduler = SingleDateScheduler(logger=logger, use_unified_cpsat=False)
            legacy_result = legacy_scheduler.schedule(config)
            
            if legacy_result.status == "SUCCESS":
                avg, max_stay, long_count = analyze_schedule_performance(
                    legacy_result.schedule, "기존 휴리스틱 결과", scenario
                )
                scenario_results["legacy"] = {
                    "success": True,
                    "avg_stay": avg,
                    "max_stay": max_stay,
                    "long_count": long_count,
                    "schedule_count": len(legacy_result.schedule)
                }
                print("✅ 기존 방식 성공")
            else:
                print(f"❌ 기존 방식 실패: {legacy_result.error_message}")
                scenario_results["legacy"] = {"success": False}
        except Exception as e:
            print(f"❌ 기존 방식 예외: {str(e)}")
            scenario_results["legacy"] = {"success": False, "error": str(e)}
        
        # 2. 통합 CP-SAT 방식 테스트
        print(f"\n🚀 통합 CP-SAT 방식 테스트...")
        try:
            unified_scheduler = SingleDateScheduler(logger=logger, use_unified_cpsat=True)
            unified_result = unified_scheduler.schedule(config)
            
            if unified_result.status == "SUCCESS":
                avg, max_stay, long_count = analyze_schedule_performance(
                    unified_result.schedule, "통합 CP-SAT 결과", scenario
                )
                scenario_results["unified"] = {
                    "success": True,
                    "avg_stay": avg,
                    "max_stay": max_stay,
                    "long_count": long_count,
                    "schedule_count": len(unified_result.schedule)
                }
                print("✅ 통합 CP-SAT 성공")
            else:
                print(f"❌ 통합 CP-SAT 실패: {unified_result.error_message}")
                if unified_result.logs:
                    for log in unified_result.logs[-3:]:
                        print(f"  {log}")
                scenario_results["unified"] = {"success": False, "error": unified_result.error_message}
        except Exception as e:
            print(f"❌ 통합 CP-SAT 예외: {str(e)}")
            traceback.print_exc()
            scenario_results["unified"] = {"success": False, "error": str(e)}
        
        # 3. 시나리오별 결과 비교
        print(f"\n📊 {scenario.upper()} 시나리오 결과 비교:")
        if scenario_results["legacy"]["success"] and scenario_results["unified"]["success"]:
            legacy = scenario_results["legacy"]
            unified = scenario_results["unified"]
            
            avg_improvement = (legacy["avg_stay"] - unified["avg_stay"]) / legacy["avg_stay"] * 100
            max_improvement = (legacy["max_stay"] - unified["max_stay"]) / legacy["max_stay"] * 100
            long_reduction = legacy["long_count"] - unified["long_count"]
            
            print(f"  평균 체류시간: {legacy['avg_stay']:.1f}h → {unified['avg_stay']:.1f}h ({avg_improvement:+.1f}%)")
            print(f"  최대 체류시간: {legacy['max_stay']:.1f}h → {unified['max_stay']:.1f}h ({max_improvement:+.1f}%)")
            print(f"  3시간+ 체류자: {legacy['long_count']}명 → {unified['long_count']}명 ({long_reduction:+d}명)")
            
            scenario_results["improvement"] = {
                "avg_improvement": avg_improvement,
                "max_improvement": max_improvement,
                "long_reduction": long_reduction
            }
            
            if avg_improvement > 0:
                print(f"  ✅ 개선 성공! 평균 {avg_improvement:.1f}% 단축")
            else:
                print(f"  ⚠️ 개선 없음: {avg_improvement:.1f}%")
        else:
            print("  ❌ 비교 불가능 - 일부 방식 실패")
        
        results[scenario] = scenario_results
    
    # 전체 결과 요약
    print(f"\n{'='*70}")
    print("🏆 전체 테스트 결과 요약")
    print(f"{'='*70}")
    
    for scenario, result in results.items():
        print(f"\n📈 {scenario.upper()} 시나리오:")
        if "improvement" in result:
            imp = result["improvement"]
            print(f"  - 평균 체류시간 개선: {imp['avg_improvement']:+.1f}%")
            print(f"  - 최대 체류시간 개선: {imp['max_improvement']:+.1f}%")
            print(f"  - 3시간+ 체류자 감소: {imp['long_reduction']:+d}명")
        else:
            print(f"  - 테스트 실패 또는 불완전")
    
    return results


def debug_infeasible_issue():
    """INFEASIBLE 문제 디버깅 및 해결"""
    print("\n🐛 INFEASIBLE 문제 디버깅 시작")
    print("=" * 50)
    
    # 최소한의 시나리오로 디버깅
    print("1. 최소 시나리오 생성 (지원자 4명)...")
    
    activities = [
        Activity(
            name="토론면접",
            mode=ActivityMode.BATCHED,
            duration_min=30,
            room_type="토론면접실",
            required_rooms=["토론면접실"],
            min_capacity=4,
            max_capacity=6
        )
    ]
    
    rooms = [
        Room(name="토론면접실A", room_type="토론면접실", capacity=6),
    ]
    
    config = DateConfig(
        date=datetime(2025, 7, 1),
        jobs={"JOB01": 4},  # 최소 4명
        activities=activities,
        rooms=rooms,
        operating_hours=(timedelta(hours=9), timedelta(hours=17)),
        job_activity_matrix={("JOB01", "토론면접"): True},
        global_gap_min=5
    )
    
    print("2. 최소 시나리오 통합 CP-SAT 테스트...")
    try:
        unified_scheduler = SingleDateScheduler(logger=logger, use_unified_cpsat=True)
        result = unified_scheduler.schedule(config)
        
        if result.status == "SUCCESS":
            print("✅ 최소 시나리오 성공! INFEASIBLE 문제 해결됨")
            analyze_schedule_performance(result.schedule, "최소 시나리오 결과", "debug")
            return True
        else:
            print(f"❌ 최소 시나리오도 실패: {result.error_message}")
            return False
    except Exception as e:
        print(f"❌ 최소 시나리오 예외: {str(e)}")
        return False


if __name__ == "__main__":
    # 1. INFEASIBLE 문제 디버깅
    if debug_infeasible_issue():
        # 2. 점진적 시나리오 테스트
        test_scenario_progression()
    else:
        print("❌ INFEASIBLE 문제 해결 필요 - 시나리오 테스트 중단") 