"""
Phase 7: 전체 통합 테스트
"""
from datetime import datetime, timedelta
from solver.types import (
    DateConfig, Activity, Room, ActivityType, PrecedenceRule
)
from solver.single_date_scheduler import SingleDateScheduler
import logging
import time

# 로깅 설정
logging.basicConfig(level=logging.WARNING, format='%(message)s')


def test_realistic_scenario():
    """실제 면접 시나리오 테스트"""
    
    print("\n" + "="*60)
    print("1. 실제 면접 시나리오 테스트")
    print("="*60)
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            "개발직": 23,
            "디자인직": 15,
            "기획직": 18,
        },
        activities=[
            # 1차: 토론면접 (Batched)
            Activity(
                name="토론면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="토론실",
                required_rooms=["토론실"],
                min_capacity=4,
                max_capacity=6
            ),
            # 2차: 발표준비 (Individual)
            Activity(
                name="발표준비",
                mode=ActivityType.INDIVIDUAL,
                duration_min=30,
                room_type="준비실",
                required_rooms=["준비실"]
            ),
            # 3차: 발표면접 (Individual)
            Activity(
                name="발표면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=20,
                room_type="발표실",
                required_rooms=["발표실"]
            ),
            # 4차: AI역량검사 (Parallel)
            Activity(
                name="AI역량검사",
                mode=ActivityType.PARALLEL,
                duration_min=45,
                room_type="컴퓨터실",
                required_rooms=["컴퓨터실"],
                max_capacity=20
            ),
            # 5차: 임원면접 (Individual)
            Activity(
                name="임원면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=30,
                room_type="임원실",
                required_rooms=["임원실"]
            ),
        ],
        rooms=[
            # 토론실 3개
            Room(name="토론실A", room_type="토론실", capacity=6),
            Room(name="토론실B", room_type="토론실", capacity=6),
            Room(name="토론실C", room_type="토론실", capacity=6),
            # 준비실 2개
            Room(name="준비실1", room_type="준비실", capacity=1),
            Room(name="준비실2", room_type="준비실", capacity=1),
            # 발표실 3개
            Room(name="발표실1", room_type="발표실", capacity=1),
            Room(name="발표실2", room_type="발표실", capacity=1),
            Room(name="발표실3", room_type="발표실", capacity=1),
            # 컴퓨터실 2개
            Room(name="컴퓨터실1", room_type="컴퓨터실", capacity=20),
            Room(name="컴퓨터실2", room_type="컴퓨터실", capacity=15),
            # 임원실 2개
            Room(name="임원실1", room_type="임원실", capacity=1),
            Room(name="임원실2", room_type="임원실", capacity=1),
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=18)),  # 9시간 운영
        precedence_rules=[
            # 토론면접 → 발표준비
            PrecedenceRule(
                predecessor="토론면접",
                successor="발표준비",
                gap_min=15  # 15분 휴식
            ),
            # 발표준비 → 발표면접
            PrecedenceRule(
                predecessor="발표준비",
                successor="발표면접",
                gap_min=5  # 5분 이동
            ),
            # 발표면접 → AI역량검사
            PrecedenceRule(
                predecessor="발표면접",
                successor="AI역량검사",
                gap_min=10  # 10분 휴식
            ),
            # AI역량검사 → 임원면접
            PrecedenceRule(
                predecessor="AI역량검사",
                successor="임원면접",
                gap_min=20  # 20분 휴식
            ),
        ],
        job_activity_matrix={
            # 개발직: 모든 활동
            ("개발직", "토론면접"): True,
            ("개발직", "발표준비"): True,
            ("개발직", "발표면접"): True,
            ("개발직", "AI역량검사"): True,
            ("개발직", "임원면접"): True,
            # 디자인직: 토론, 발표, 임원만
            ("디자인직", "토론면접"): True,
            ("디자인직", "발표준비"): True,
            ("디자인직", "발표면접"): True,
            ("디자인직", "AI역량검사"): False,
            ("디자인직", "임원면접"): True,
            # 기획직: 토론, AI, 임원만
            ("기획직", "토론면접"): True,
            ("기획직", "발표준비"): False,
            ("기획직", "발표면접"): False,
            ("기획직", "AI역량검사"): True,
            ("기획직", "임원면접"): True,
        }
    )
    
    # 스케줄러 실행
    start_time = time.time()
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    elapsed = time.time() - start_time
    
    # 결과 분석
    print(f"\n상태: {result.status}")
    print(f"실행 시간: {elapsed:.2f}초")
    print(f"백트래킹 횟수: {result.backtrack_count}")
    
    if result.status == "SUCCESS":
        print("\n✅ 스케줄링 성공!")
        
        # 통계
        total_scheduled = len([i for i in result.schedule if not i.applicant_id.startswith("DUMMY_")])
        print(f"\n[통계]")
        print(f"총 지원자: 56명")
        print(f"스케줄된 항목: {total_scheduled}개")
        
        if result.level1_result:
            print(f"총 그룹 수: {result.level1_result.group_count}")
            print(f"더미 지원자: {result.level1_result.dummy_count}명")
            
        # 직무별 분석
        job_stats = {}
        for item in result.schedule:
            if not item.applicant_id.startswith("DUMMY_"):
                job = item.applicant_id.split("_")[0]
                if job not in job_stats:
                    job_stats[job] = set()
                job_stats[job].add(item.applicant_id)
                
        print(f"\n[직무별 스케줄]")
        for job, applicants in sorted(job_stats.items()):
            print(f"{job}: {len(applicants)}명")
            
        # 시간대별 분포
        hour_stats = {}
        for item in result.schedule:
            if not item.applicant_id.startswith("DUMMY_"):
                hour = item.time_slot.start.hour
                if hour not in hour_stats:
                    hour_stats[hour] = 0
                hour_stats[hour] += 1
                
        print(f"\n[시간대별 분포]")
        for hour in sorted(hour_stats.keys()):
            print(f"{hour}시: {hour_stats[hour]}건")
            
        # 방 활용도
        room_usage = {}
        for item in result.schedule:
            room = item.room_name
            if room not in room_usage:
                room_usage[room] = 0
            room_usage[room] += 1
            
        print(f"\n[방 활용도 TOP 5]")
        for room, count in sorted(room_usage.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"{room}: {count}회")
            
    else:
        print("\n❌ 스케줄링 실패!")
        print(f"에러: {result.error_message}")
        
        # 실패 원인 분석
        if result.level3_result and result.level3_result.unscheduled:
            print(f"\n미배정 지원자: {len(result.level3_result.unscheduled)}명")


def test_large_scale():
    """대규모 데이터 테스트"""
    
    print("\n" + "="*60)
    print("2. 대규모 데이터 테스트")
    print("="*60)
    
    config = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={
            f"JOB{i:02d}": 20 for i in range(1, 11)  # 10개 직무, 각 20명 = 총 200명
        },
        activities=[
            # 토론면접만 진행
            Activity(
                name="토론면접",
                mode=ActivityType.BATCHED,
                duration_min=60,
                room_type="토론실",
                required_rooms=["토론실"],
                min_capacity=5,
                max_capacity=6
            ),
            # 인성면접
            Activity(
                name="인성면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=30,
                room_type="면접실",
                required_rooms=["면접실"]
            ),
        ],
        rooms=[
            # 토론실 10개
            *[Room(name=f"토론실{chr(65+i)}", room_type="토론실", capacity=6) for i in range(10)],
            # 면접실 20개
            *[Room(name=f"면접실{i+1}", room_type="면접실", capacity=1) for i in range(20)],
        ],
        operating_hours=(timedelta(hours=8), timedelta(hours=20)),  # 12시간 운영
        precedence_rules=[
            PrecedenceRule(
                predecessor="토론면접",
                successor="인성면접",
                gap_min=30  # 30분 휴식
            ),
        ],
        job_activity_matrix={
            (f"JOB{i:02d}", "토론면접"): True for i in range(1, 11)
        } | {
            (f"JOB{i:02d}", "인성면접"): True for i in range(1, 11)
        }
    )
    
    # 스케줄러 실행
    print("\n대규모 스케줄링 시작...")
    start_time = time.time()
    scheduler = SingleDateScheduler()
    result = scheduler.schedule(config)
    elapsed = time.time() - start_time
    
    # 결과 분석
    print(f"\n상태: {result.status}")
    print(f"실행 시간: {elapsed:.2f}초")
    
    if result.status == "SUCCESS":
        print("\n✅ 대규모 스케줄링 성공!")
        
        total_scheduled = len([i for i in result.schedule if not i.applicant_id.startswith("DUMMY_")])
        print(f"\n[통계]")
        print(f"총 지원자: 200명")
        print(f"스케줄된 항목: {total_scheduled}개")
        print(f"평균 처리 시간: {elapsed/200:.3f}초/명")
        
        if elapsed < 120:  # 2분 이내
            print("✅ 성능 목표 달성 (2분 이내)")
        else:
            print("⚠️ 성능 개선 필요")
            
    else:
        print("\n❌ 대규모 스케줄링 실패!")
        print(f"에러: {result.error_message}")


def test_edge_cases():
    """엣지 케이스 테스트"""
    
    print("\n" + "="*60)
    print("3. 엣지 케이스 테스트")
    print("="*60)
    
    # 테스트 1: 방이 부족한 경우
    print("\n[테스트 1: 방 부족]")
    config1 = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={"JOB01": 20},
        activities=[
            Activity(
                name="면접",
                mode=ActivityType.INDIVIDUAL,
                duration_min=60,
                room_type="면접실",
                required_rooms=["면접실"]
            ),
        ],
        rooms=[
            Room(name="면접실1", room_type="면접실", capacity=1),  # 방 1개만
        ],
        operating_hours=(timedelta(hours=9), timedelta(hours=11)),  # 2시간만
        precedence_rules=[],
        job_activity_matrix={("JOB01", "면접"): True}
    )
    
    scheduler = SingleDateScheduler()
    result1 = scheduler.schedule(config1)
    print(f"상태: {result1.status}")
    if result1.status == "FAILED":
        print("✅ 예상대로 실패 (방/시간 부족)")
    
    # 테스트 2: 순환 precedence
    print("\n[테스트 2: 순환 Precedence]")
    config2 = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={"JOB01": 5},
        activities=[
            Activity(name="A", mode=ActivityType.INDIVIDUAL, duration_min=30, 
                    room_type="방", required_rooms=["방"]),
            Activity(name="B", mode=ActivityType.INDIVIDUAL, duration_min=30,
                    room_type="방", required_rooms=["방"]),
            Activity(name="C", mode=ActivityType.INDIVIDUAL, duration_min=30,
                    room_type="방", required_rooms=["방"]),
        ],
        rooms=[Room(name="방1", room_type="방", capacity=1)],
        operating_hours=(timedelta(hours=9), timedelta(hours=17)),
        precedence_rules=[
            PrecedenceRule("A", "B", 10),
            PrecedenceRule("B", "C", 10),
            PrecedenceRule("C", "A", 10),  # 순환!
        ],
        job_activity_matrix={
            ("JOB01", "A"): True,
            ("JOB01", "B"): True,
            ("JOB01", "C"): True,
        }
    )
    
    scheduler = SingleDateScheduler()
    result2 = scheduler.schedule(config2)
    print(f"상태: {result2.status}")
    if result2.status == "SUCCESS":
        print("✅ 순환 precedence도 처리 가능")
    else:
        print("⚠️ 순환 precedence 처리 실패")
    
    # 테스트 3: 빈 데이터
    print("\n[테스트 3: 빈 데이터]")
    config3 = DateConfig(
        date=datetime(2025, 1, 15),
        jobs={},
        activities=[],
        rooms=[],
        operating_hours=(timedelta(hours=9), timedelta(hours=17)),
        precedence_rules=[],
        job_activity_matrix={}
    )
    
    scheduler = SingleDateScheduler()
    result3 = scheduler.schedule(config3)
    print(f"상태: {result3.status}")
    if result3.status == "SUCCESS":
        print("✅ 빈 데이터도 정상 처리")


def test_performance_benchmark():
    """성능 벤치마크"""
    
    print("\n" + "="*60)
    print("4. 성능 벤치마크")
    print("="*60)
    
    test_sizes = [10, 50, 100, 200]
    results = []
    
    for size in test_sizes:
        config = DateConfig(
            date=datetime(2025, 1, 15),
            jobs={"JOB01": size},
            activities=[
                Activity(
                    name="토론면접",
                    mode=ActivityType.BATCHED,
                    duration_min=60,
                    room_type="토론실",
                    required_rooms=["토론실"],
                    min_capacity=5,
                    max_capacity=6
                ),
            ],
            rooms=[
                Room(name=f"토론실{i+1}", room_type="토론실", capacity=6) 
                for i in range(max(2, size // 20))
            ],
            operating_hours=(timedelta(hours=9), timedelta(hours=18)),
            precedence_rules=[],
            job_activity_matrix={("JOB01", "토론면접"): True}
        )
        
        start_time = time.time()
        scheduler = SingleDateScheduler()
        result = scheduler.schedule(config)
        elapsed = time.time() - start_time
        
        results.append({
            'size': size,
            'status': result.status,
            'time': elapsed,
            'backtrack': result.backtrack_count
        })
        
        print(f"\n{size}명: {elapsed:.2f}초 (상태: {result.status}, 백트래킹: {result.backtrack_count})")
    
    # 성능 분석
    print("\n[성능 분석]")
    success_results = [r for r in results if r['status'] == 'SUCCESS']
    if success_results:
        avg_time_per_person = sum(r['time'] / r['size'] for r in success_results) / len(success_results)
        print(f"평균 처리 시간: {avg_time_per_person:.4f}초/명")
        
        # 선형성 체크
        if len(success_results) >= 2:
            time_ratio = success_results[-1]['time'] / success_results[0]['time']
            size_ratio = success_results[-1]['size'] / success_results[0]['size']
            
            if time_ratio <= size_ratio * 1.5:
                print("✅ 거의 선형적 성능 (Good)")
            else:
                print(f"⚠️ 비선형적 성능 증가 (시간 비율: {time_ratio:.1f}x, 크기 비율: {size_ratio:.1f}x)")


if __name__ == "__main__":
    print("=== Phase 7: 전체 통합 테스트 ===")
    
    # 1. 실제 시나리오 테스트
    test_realistic_scenario()
    
    # 2. 대규모 데이터 테스트
    test_large_scale()
    
    # 3. 엣지 케이스 테스트
    test_edge_cases()
    
    # 4. 성능 벤치마크
    test_performance_benchmark()
    
    print("\n" + "="*60)
    print("통합 테스트 완료!")
    print("="*60) 