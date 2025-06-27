"""
간단한 성능 테스트
"""
import pandas as pd
import time
import psutil
from datetime import date, timedelta
from solver.api import solve_for_days_v2


def simple_performance_test():
    """간단한 성능 테스트"""
    print("🚀 간단한 성능 테스트")
    print("=" * 50)
    
    # 테스트 시나리오
    scenarios = [
        (25, "기본"),
        (50, "중간"),
        (100, "대규모"),
        (200, "초대규모"),
    ]
    
    results = []
    
    for num_applicants, label in scenarios:
        print(f"\n🔥 테스트: {num_applicants}명 ({label})")
        print("-" * 40)
        
        # 설정 생성
        cfg = create_simple_config(num_applicants)
        
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
                "label": label,
                "status": status,
                "time": execution_time,
                "items": len(df) if df is not None else 0,
                "throughput": num_applicants / execution_time,
                "memory_mb": end_memory - start_memory,
                "success_rate": (len(df) / (num_applicants * 4)) * 100 if df is not None else 0  # 4개 활동
            }
            
            results.append(result)
            
            print(f"✅ {status}")
            print(f"⏱️ 실행 시간: {execution_time:.3f}초")
            print(f"🎯 처리량: {result['throughput']:.1f}명/초")
            print(f"📊 스케줄 항목: {result['items']}개")
            print(f"🎯 성공률: {result['success_rate']:.1f}%")
            print(f"💾 메모리 사용: {result['memory_mb']:.1f}MB")
            
        except Exception as e:
            print(f"❌ 실패: {str(e)}")
            results.append({
                "applicants": num_applicants,
                "label": label,
                "status": "ERROR",
                "error": str(e)
            })
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 성능 요약")
    print("=" * 50)
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    
    if successful:
        print("✅ 성공한 테스트:")
        for r in successful:
            print(f"  - {r['applicants']}명: {r['time']:.3f}초, {r['throughput']:.1f}명/초")
        
        # 최고 성능
        best = max(successful, key=lambda x: x["throughput"])
        print(f"\n🏆 최고 처리량: {best['throughput']:.1f}명/초 ({best['applicants']}명)")
        
        # 대규모 처리
        large_scale = [r for r in successful if r["applicants"] >= 100]
        if large_scale:
            avg_throughput = sum(r["throughput"] for r in large_scale) / len(large_scale)
            print(f"📈 대규모(100명+) 평균: {avg_throughput:.1f}명/초")
        
        # 500명 목표 예측
        if successful:
            avg_throughput = sum(r["throughput"] for r in successful) / len(successful)
            estimated_500_time = 500 / avg_throughput
            achievable = "✅ 달성 가능" if estimated_500_time <= 120 else "❌ 최적화 필요"
            print(f"🎯 500명 처리 예상 시간: {estimated_500_time:.1f}초 {achievable}")
    
    return results


def create_simple_config(num_applicants: int):
    """간단한 테스트 설정 생성"""
    
    activities = pd.DataFrame({
        "use": [True, True, True, True],
        "activity": ["토론면접", "인성면접", "발표준비", "발표면접"],
        "mode": ["batched", "individual", "individual", "individual"],
        "duration_min": [60, 25, 15, 20],
        "room_type": ["토론실", "면접실", "준비실", "발표실"],
        "min_cap": [4, 1, 1, 1],
        "max_cap": [6, 1, 1, 1],
    })
    
    # 방 계획 - 충분한 방 제공
    room_plan = pd.DataFrame({
        "토론실_count": [max(5, num_applicants // 12)],  # 넉넉하게
        "토론실_cap": [6],
        "면접실_count": [max(8, num_applicants // 5)],
        "면접실_cap": [1],
        "준비실_count": [max(6, num_applicants // 8)],
        "준비실_cap": [1],
        "발표실_count": [max(6, num_applicants // 8)],
        "발표실_cap": [1],
    })
    
    job_acts_map = pd.DataFrame({
        "code": ["개발직"],
        "count": [num_applicants],
        "토론면접": [True],
        "인성면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["08:00"],
        "end_time": ["18:00"]  # 10시간 운영
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
    results = simple_performance_test()
    print(f"\n🏁 총 {len(results)}개 테스트 완료") 