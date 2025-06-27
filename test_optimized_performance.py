"""
최적화된 스케줄러 성능 테스트
"""
import pandas as pd
import time
import psutil
from datetime import date, timedelta
from solver.api import solve_for_days_v2, solve_for_days_optimized


def compare_performance():
    """기존 vs 최적화 성능 비교"""
    print("🚀 성능 비교 테스트")
    print("=" * 60)
    
    # 테스트 시나리오
    scenarios = [
        (50, "medium"),
        (100, "medium"),
        (200, "complex"),
        (300, "complex"),
    ]
    
    results = []
    
    for num_applicants, complexity in scenarios:
        print(f"\n🔥 테스트: {num_applicants}명, {complexity} 복잡도")
        print("-" * 50)
        
        # 설정 생성
        cfg = create_config(num_applicants, complexity)
        
        # 1. 기존 스케줄러 테스트
        print("📊 기존 스케줄러 테스트...")
        start_time = time.time()
        start_memory = get_memory_usage()
        
        try:
            status1, df1, logs1, limit1 = solve_for_days_v2(cfg, {"max_stay_hours": 12})
            time1 = time.time() - start_time
            memory1 = get_memory_usage() - start_memory
            
            result1 = {
                "scheduler": "기존",
                "applicants": num_applicants,
                "complexity": complexity,
                "status": status1,
                "time": time1,
                "items": len(df1) if df1 is not None else 0,
                "throughput": num_applicants / time1,
                "memory_mb": memory1
            }
            
            print(f"  ✅ {status1} | {time1:.3f}초 | {result1['throughput']:.1f}명/초 | {memory1:.1f}MB")
            
        except Exception as e:
            print(f"  ❌ 기존 스케줄러 실패: {e}")
            result1 = {
                "scheduler": "기존",
                "applicants": num_applicants,
                "complexity": complexity,
                "status": "ERROR",
                "error": str(e)
            }
        
        # 2. 최적화된 스케줄러 테스트
        print("🚀 최적화된 스케줄러 테스트...")
        start_time = time.time()
        start_memory = get_memory_usage()
        
        try:
            # 최적화 설정
            optimization_config = {
                "enable_parallel_processing": True,
                "enable_memory_optimization": True,
                "enable_caching": True,
                "chunk_size_threshold": 100,
                "memory_cleanup_interval": 50
            }
            
            status2, df2, logs2, limit2 = solve_for_days_optimized(
                cfg, 
                {"max_stay_hours": 12},
                optimization_config=optimization_config
            )
            time2 = time.time() - start_time
            memory2 = get_memory_usage() - start_memory
            
            result2 = {
                "scheduler": "최적화",
                "applicants": num_applicants,
                "complexity": complexity,
                "status": status2,
                "time": time2,
                "items": len(df2) if df2 is not None else 0,
                "throughput": num_applicants / time2,
                "memory_mb": memory2
            }
            
            print(f"  ✅ {status2} | {time2:.3f}초 | {result2['throughput']:.1f}명/초 | {memory2:.1f}MB")
            
            # 성능 향상 계산
            if 'time' in result1:
                speedup = result1['time'] / time2
                memory_reduction = result1['memory_mb'] - memory2
                print(f"  📈 성능 향상: {speedup:.2f}배 빠름, 메모리 {memory_reduction:.1f}MB 절약")
            
        except Exception as e:
            print(f"  ❌ 최적화 스케줄러 실패: {e}")
            result2 = {
                "scheduler": "최적화",
                "applicants": num_applicants,
                "complexity": complexity,
                "status": "ERROR",
                "error": str(e)
            }
        
        results.extend([result1, result2])
        time.sleep(1)  # 시스템 안정화
    
    # 결과 분석
    print("\n" + "=" * 60)
    print("📊 성능 비교 결과")
    print("=" * 60)
    
    successful_results = [r for r in results if r["status"] == "SUCCESS"]
    
    if successful_results:
        # 스케줄러별 평균 성능
        basic_results = [r for r in successful_results if r["scheduler"] == "기존"]
        optimized_results = [r for r in successful_results if r["scheduler"] == "최적화"]
        
        if basic_results:
            avg_time_basic = sum(r["time"] for r in basic_results) / len(basic_results)
            avg_throughput_basic = sum(r["throughput"] for r in basic_results) / len(basic_results)
            avg_memory_basic = sum(r["memory_mb"] for r in basic_results) / len(basic_results)
            print(f"🔧 기존 스케줄러 평균: {avg_time_basic:.3f}초, {avg_throughput_basic:.1f}명/초, {avg_memory_basic:.1f}MB")
        
        if optimized_results:
            avg_time_optimized = sum(r["time"] for r in optimized_results) / len(optimized_results)
            avg_throughput_optimized = sum(r["throughput"] for r in optimized_results) / len(optimized_results)
            avg_memory_optimized = sum(r["memory_mb"] for r in optimized_results) / len(optimized_results)
            print(f"🚀 최적화 스케줄러 평균: {avg_time_optimized:.3f}초, {avg_throughput_optimized:.1f}명/초, {avg_memory_optimized:.1f}MB")
            
            if basic_results:
                overall_speedup = avg_time_basic / avg_time_optimized
                memory_savings = avg_memory_basic - avg_memory_optimized
                print(f"📈 전체 성능 향상: {overall_speedup:.2f}배 빠름, 메모리 {memory_savings:.1f}MB 절약")
        
        # 대규모 처리 성능
        large_scale = [r for r in successful_results if r["applicants"] >= 200]
        if large_scale:
            print(f"\n🎯 대규모(200명+) 처리 성능:")
            for r in large_scale:
                print(f"  - {r['scheduler']} {r['applicants']}명: {r['time']:.3f}초, {r['throughput']:.1f}명/초")
        
        # 500명 목표 달성 여부
        target_500 = [r for r in successful_results if r["applicants"] >= 300]
        if target_500:
            print(f"\n🏆 500명 목표 달성 가능성:")
            for r in target_500:
                estimated_500_time = 500 / r["throughput"]
                achievable = "✅" if estimated_500_time <= 120 else "❌"
                print(f"  - {r['scheduler']}: 예상 {estimated_500_time:.1f}초 {achievable}")
        
    return results


def create_config(num_applicants: int, complexity: str):
    """테스트 설정 생성"""
    
    if complexity == "medium":
        activities = pd.DataFrame({
            "use": [True, True, True, True],
            "activity": ["토론면접", "인성면접", "발표준비", "발표면접"],
            "mode": ["batched", "individual", "individual", "individual"],
            "duration_min": [60, 25, 15, 20],
            "room_type": ["토론실", "면접실", "준비실", "발표실"],
            "min_cap": [4, 1, 1, 1],
            "max_cap": [6, 1, 1, 1],
        })
        
        room_plan = pd.DataFrame({
            "토론실_count": [max(6, num_applicants // 15)],
            "토론실_cap": [6],
            "면접실_count": [max(10, num_applicants // 6)],
            "면접실_cap": [1],
            "준비실_count": [max(8, num_applicants // 8)],
            "준비실_cap": [1],
            "발표실_count": [max(8, num_applicants // 8)],
            "발표실_cap": [1],
        })
        
    else:  # complex
        activities = pd.DataFrame({
            "use": [True, True, True, True, True, True],
            "activity": ["토론면접", "인성면접", "발표준비", "발표면접", "코딩테스트", "최종면접"],
            "mode": ["batched", "individual", "individual", "individual", "individual", "individual"],
            "duration_min": [90, 30, 20, 25, 45, 40],
            "room_type": ["토론실", "면접실", "준비실", "발표실", "코딩실", "임원실"],
            "min_cap": [4, 1, 1, 1, 1, 1],
            "max_cap": [6, 1, 1, 1, 1, 1],
        })
        
        room_plan = pd.DataFrame({
            "토론실_count": [max(8, num_applicants // 15)],
            "토론실_cap": [6],
            "면접실_count": [max(15, num_applicants // 5)],
            "면접실_cap": [1],
            "준비실_count": [max(12, num_applicants // 8)],
            "준비실_cap": [1],
            "발표실_count": [max(12, num_applicants // 8)],
            "발표실_cap": [1],
            "코딩실_count": [max(10, num_applicants // 10)],
            "코딩실_cap": [1],
            "임원실_count": [max(6, num_applicants // 15)],
            "임원실_cap": [1],
        })
    
    job_acts_map = pd.DataFrame({
        "code": ["개발직"],
        "count": [num_applicants],
        **{activity: [True] for activity in activities["activity"]}
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["08:00"],
        "end_time": ["19:00"]
    })
    
    precedence = pd.DataFrame({
        "predecessor": ["토론면접", "발표준비"],
        "successor": ["인성면접", "발표면접"],
        "gap_min": [30, 5],
        "adjacent": [False, False]
    })
    
    return {
        "activities": activities,
        "room_plan": room_plan,
        "job_acts_map": job_acts_map,
        "oper_window": oper_window,
        "precedence": precedence,
        "interview_date": date.today() + timedelta(days=1)
    }


def get_memory_usage():
    """메모리 사용량 측정 (MB)"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


if __name__ == "__main__":
    results = compare_performance()
    print(f"\n🏁 총 {len(results)}개 테스트 완료") 