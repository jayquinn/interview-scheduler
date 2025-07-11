"""
🚀 통합 CP-SAT 스케줄러 테스트
Phase 2: Batched + Individual 통합 최적화 검증

기존 순차 배치 vs 통합 CP-SAT 체류시간 비교
"""
from datetime import datetime, timedelta
from solver.types import (
    Activity, Room, DateConfig, ActivityMode, PrecedenceRule
)
from solver.single_date_scheduler import SingleDateScheduler
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_test_config() -> DateConfig:
    """테스트용 설정 생성"""
    
    # 활동 정의
    activities = [
        # Batched 활동
        Activity(
            name="토론면접",
            mode=ActivityMode.BATCHED,
            duration_min=60,
            room_type="토론면접실",
            required_rooms=["토론면접실"],
            min_capacity=4,
            max_capacity=6
        ),
        # Individual 활동들
        Activity(
            name="인성면접",
            mode=ActivityMode.INDIVIDUAL,
            duration_min=30,
            room_type="면접실",
            required_rooms=["면접실"]
        ),
        Activity(
            name="AI면접",
            mode=ActivityMode.PARALLEL,
            duration_min=45,
            room_type="컴퓨터실",
            required_rooms=["컴퓨터실"],
            max_capacity=10
        )
    ]
    
    # 방 정의
    rooms = [
        Room(name="토론면접실A", room_type="토론면접실", capacity=6),
        Room(name="토론면접실B", room_type="토론면접실", capacity=6),
        Room(name="면접실A", room_type="면접실", capacity=1),
        Room(name="면접실B", room_type="면접실", capacity=1),
        Room(name="면접실C", room_type="면접실", capacity=1),
        Room(name="컴퓨터실1", room_type="컴퓨터실", capacity=10),
    ]
    
    # 직무-활동 매트릭스 (모든 지원자가 모든 활동 수행)
    job_activity_matrix = {
        ("JOB01", "토론면접"): True,
        ("JOB01", "인성면접"): True,
        ("JOB01", "AI면접"): True,
        ("JOB02", "토론면접"): True,
        ("JOB02", "인성면접"): True,
        ("JOB02", "AI면접"): True,
    }
    
    return DateConfig(
        date=datetime(2025, 1, 15),
        jobs={"JOB01": 8, "JOB02": 4},  # 총 12명 지원자
        activities=activities,
        rooms=rooms,
        operating_hours=(timedelta(hours=9), timedelta(hours=17)),  # 09:00 ~ 17:00
        job_activity_matrix=job_activity_matrix,
        global_gap_min=5
    )


def analyze_stay_times(schedule, title):
    """체류시간 분석"""
    print(f"\n=== {title} ===")
    
    # 지원자별 체류시간 계산
    applicant_times = {}
    for item in schedule:
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
            print(f"  {applicant_id}: {stay_hours:.1f}시간 ({first_start} ~ {last_end})")
    
    if stay_times:
        avg_stay = sum(stay_times) / len(stay_times)
        max_stay = max(stay_times)
        min_stay = min(stay_times)
        long_stay_count = len([t for t in stay_times if t >= 3.0])
        
        print(f"\n📊 체류시간 통계:")
        print(f"  평균: {avg_stay:.1f}시간")
        print(f"  최대: {max_stay:.1f}시간")
        print(f"  최소: {min_stay:.1f}시간")
        print(f"  3시간 이상: {long_stay_count}명 ({long_stay_count/len(stay_times)*100:.1f}%)")
        
        return avg_stay, max_stay, long_stay_count
    
    return 0, 0, 0


def test_unified_vs_legacy():
    """통합 CP-SAT vs 기존 방식 비교 테스트"""
    print("🚀 Phase 2 통합 CP-SAT vs 기존 방식 비교 테스트")
    print("=" * 60)
    
    config = create_test_config()
    
    # 1. 기존 방식 테스트
    print("\n🔧 기존 순차 배치 방식 테스트...")
    legacy_scheduler = SingleDateScheduler(logger=logger, use_unified_cpsat=False)
    legacy_result = legacy_scheduler.schedule(config)
    
    if legacy_result.status == "SUCCESS":
        legacy_avg, legacy_max, legacy_long = analyze_stay_times(legacy_result.schedule, "기존 순차 배치 결과")
    else:
        print(f"❌ 기존 방식 실패: {legacy_result.error_message}")
        legacy_avg, legacy_max, legacy_long = 0, 0, 0
    
    # 2. 통합 CP-SAT 방식 테스트
    print("\n🚀 통합 CP-SAT 방식 테스트...")
    unified_scheduler = SingleDateScheduler(logger=logger, use_unified_cpsat=True)
    unified_result = unified_scheduler.schedule(config)
    
    if unified_result.status == "SUCCESS":
        unified_avg, unified_max, unified_long = analyze_stay_times(unified_result.schedule, "통합 CP-SAT 최적화 결과")
    else:
        print(f"❌ 통합 방식 실패: {unified_result.error_message}")
        if unified_result.logs:
            for log in unified_result.logs[-5:]:  # 마지막 5줄만 출력
                print(f"  {log}")
        unified_avg, unified_max, unified_long = 0, 0, 0
    
    # 3. 성능 비교
    print("\n" + "=" * 60)
    print("📊 성능 비교 결과")
    print("=" * 60)
    
    if legacy_avg > 0 and unified_avg > 0:
        avg_improvement = (legacy_avg - unified_avg) / legacy_avg * 100
        max_improvement = (legacy_max - unified_max) / legacy_max * 100
        long_stay_reduction = legacy_long - unified_long
        
        print(f"평균 체류시간: {legacy_avg:.1f}h → {unified_avg:.1f}h ({avg_improvement:+.1f}%)")
        print(f"최대 체류시간: {legacy_max:.1f}h → {unified_max:.1f}h ({max_improvement:+.1f}%)")
        print(f"3시간+ 체류자: {legacy_long}명 → {unified_long}명 ({long_stay_reduction:+d}명)")
        
        if avg_improvement > 0:
            print(f"✅ 체류시간 개선 성공! 평균 {avg_improvement:.1f}% 단축")
        else:
            print(f"⚠️ 체류시간 개선 미달: {avg_improvement:.1f}%")
    else:
        print("❌ 비교 불가능 - 일부 방식 실패")
    
    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    test_unified_vs_legacy() 