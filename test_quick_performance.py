"""
빠른 성능 테스트 - 핵심 시나리오만 측정
"""
import pandas as pd
import time
import psutil
from datetime import date, timedelta
from solver.api import solve_for_days_v2


def quick_benchmark():
    """빠른 성능 벤치마크"""
    print("🚀 빠른 성능 벤치마크")
    print("=" * 50)
    
    # 테스트 시나리오: 중요한 케이스만
    scenarios = [
        (50, "medium"),
        (100, "medium"), 
        (200, "medium"),
        (300, "complex"),
        (500, "complex"),
    ]
    
    results = []
    
    for num_applicants, complexity in scenarios:
        print(f"\n🔥 테스트: {num_applicants}명, {complexity} 복잡도")
        print("-" * 40)
        
        # 설정 생성
        cfg = create_config(num_applicants, complexity)
        
        # 메모리 측정
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024
        
        # 실행
        start_time = time.time()
        
        try:
            status, df, logs, limit = solve_for_days_v2(cfg, {"max_stay_hours": 12})
            execution_time = time.time() - start_time
            
            end_memory = process.memory_info().rss / 1024 / 1024
            
            result = {
                "applicants": num_applicants,
                "complexity": complexity,
                "status": status,
                "time": execution_time,
                "items": len(df) if df is not None else 0,
                "throughput": num_applicants / execution_time,
                "memory_mb": end_memory - start_memory
            }
            
            results.append(result)
            
            print(f"✅ {status} | {execution_time:.3f}초 | {result['throughput']:.1f}명/초")
            print(f"📊 {result['items']}개 스케줄 | {result['memory_mb']:.1f}MB 증가")
            
        except Exception as e:
            print(f"❌ 실패: {str(e)}")
            results.append({
                "applicants": num_applicants,
                "complexity": complexity,
                "status": "ERROR",
                "error": str(e)
            })
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 성능 요약")
    print("=" * 50)
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    
    if successful:
        # 최고 처리량
        best = max(successful, key=lambda x: x["throughput"])
        print(f"🏆 최고 처리량: {best['throughput']:.1f}명/초 ({best['applicants']}명)")
        
        # 대규모 처리
        large_scale = [r for r in successful if r["applicants"] >= 200]
        if large_scale:
            avg_throughput = sum(r["throughput"] for r in large_scale) / len(large_scale)
            avg_time = sum(r["time"] for r in large_scale) / len(large_scale)
            print(f"📈 대규모(200명+): {avg_throughput:.1f}명/초, {avg_time:.3f}초 평균")
        
        # 500명 목표 체크
        target_500 = [r for r in successful if r["applicants"] >= 500]
        if target_500:
            for r in target_500:
                print(f"🎯 500명 처리: {r['time']:.3f}초 ({'✅' if r['time'] <= 120 else '❌'} 2분 목표)")
        else:
            print("⚠️ 500명 테스트 없음 - 더 큰 규모 테스트 필요")
    
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


if __name__ == "__main__":
    results = quick_benchmark()
    print(f"\n🏁 총 {len(results)}개 테스트 완료") 