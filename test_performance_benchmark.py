"""
성능 벤치마크 테스트 - 현재 성능 측정 및 병목 분석
"""
import pandas as pd
import time
import psutil
import gc
from datetime import date, timedelta
from solver.api import solve_for_days_v2
from solver.types import ProgressInfo
import tracemalloc


class PerformanceBenchmark:
    """성능 벤치마크 클래스"""
    
    def __init__(self):
        self.results = []
        self.memory_snapshots = []
        
    def create_test_config(self, num_applicants: int, complexity: str = "medium"):
        """테스트 설정 생성"""
        
        if complexity == "simple":
            # 간단한 시나리오
            activities = pd.DataFrame({
                "use": [True, True],
                "activity": ["면접1", "면접2"],
                "mode": ["individual", "individual"],
                "duration_min": [30, 30],
                "room_type": ["면접실", "면접실"],
                "min_cap": [1, 1],
                "max_cap": [1, 1],
            })
            
            room_plan = pd.DataFrame({
                "면접실_count": [max(10, num_applicants // 5)],
                "면접실_cap": [1],
            })
            
        elif complexity == "medium":
            # 중간 복잡도 시나리오
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
                "토론실_count": [max(5, num_applicants // 20)],
                "토론실_cap": [6],
                "면접실_count": [max(8, num_applicants // 8)],
                "면접실_cap": [1],
                "준비실_count": [max(6, num_applicants // 10)],
                "준비실_cap": [1],
                "발표실_count": [max(6, num_applicants // 10)],
                "발표실_cap": [1],
            })
            
        else:  # complex
            # 복잡한 시나리오
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
                "토론실_count": [max(6, num_applicants // 20)],
                "토론실_cap": [6],
                "면접실_count": [max(10, num_applicants // 8)],
                "면접실_cap": [1],
                "준비실_count": [max(8, num_applicants // 10)],
                "준비실_cap": [1],
                "발표실_count": [max(8, num_applicants // 10)],
                "발표실_cap": [1],
                "코딩실_count": [max(6, num_applicants // 12)],
                "코딩실_cap": [1],
                "임원실_count": [max(4, num_applicants // 15)],
                "임원실_cap": [1],
            })
        
        # 직무별 활동 매핑
        job_acts_map = pd.DataFrame({
            "code": ["개발직"],
            "count": [num_applicants],
            **{activity: [True] for activity in activities["activity"]}
        })
        
        # 운영 시간
        oper_window = pd.DataFrame({
            "start_time": ["08:00"],
            "end_time": ["19:00"]
        })
        
        # 선후행 제약
        if complexity != "simple":
            precedence = pd.DataFrame({
                "predecessor": ["토론면접", "발표준비"],
                "successor": ["인성면접", "발표면접"],
                "gap_min": [30, 5],
                "adjacent": [False, False]
            })
        else:
            precedence = pd.DataFrame()
        
        return {
            "activities": activities,
            "room_plan": room_plan,
            "job_acts_map": job_acts_map,
            "oper_window": oper_window,
            "precedence": precedence,
            "interview_date": date.today() + timedelta(days=1)
        }
    
    def measure_memory_usage(self):
        """메모리 사용량 측정"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # 물리 메모리
            "vms_mb": memory_info.vms / 1024 / 1024,  # 가상 메모리
            "percent": process.memory_percent()
        }
    
    def progress_monitor(self, info: ProgressInfo):
        """진행 상황 모니터링"""
        memory = self.measure_memory_usage()
        self.memory_snapshots.append({
            "stage": info.stage,
            "progress": info.progress,
            "memory_mb": memory["rss_mb"],
            "timestamp": time.time()
        })
    
    def run_benchmark(self, num_applicants: int, complexity: str = "medium"):
        """단일 벤치마크 실행"""
        print(f"\n🔥 벤치마크 실행: {num_applicants}명, {complexity} 복잡도")
        print("-" * 60)
        
        # 메모리 추적 시작
        tracemalloc.start()
        gc.collect()  # 가비지 컬렉션
        
        start_memory = self.measure_memory_usage()
        self.memory_snapshots = []
        
        # 설정 생성
        cfg = self.create_test_config(num_applicants, complexity)
        
        # 실행 시간 측정
        start_time = time.time()
        
        try:
            status, df, logs, limit = solve_for_days_v2(
                cfg, 
                {"max_stay_hours": 12}, 
                debug=False,
                progress_callback=self.progress_monitor
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 메모리 사용량 측정
            end_memory = self.measure_memory_usage()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # 결과 저장
            result = {
                "num_applicants": num_applicants,
                "complexity": complexity,
                "status": status,
                "execution_time": execution_time,
                "schedule_items": len(df) if df is not None else 0,
                "success_rate": len(df) / (num_applicants * len(cfg["activities"])) if df is not None else 0,
                "start_memory_mb": start_memory["rss_mb"],
                "end_memory_mb": end_memory["rss_mb"],
                "peak_memory_mb": peak / 1024 / 1024,
                "memory_growth_mb": end_memory["rss_mb"] - start_memory["rss_mb"],
                "throughput_per_sec": num_applicants / execution_time if execution_time > 0 else 0
            }
            
            self.results.append(result)
            
            # 결과 출력
            print(f"✅ 상태: {status}")
            print(f"⏱️ 실행 시간: {execution_time:.3f}초")
            print(f"📊 스케줄 항목: {len(df) if df is not None else 0}개")
            print(f"🎯 처리량: {result['throughput_per_sec']:.1f}명/초")
            print(f"💾 메모리 사용: {start_memory['rss_mb']:.1f}MB → {end_memory['rss_mb']:.1f}MB")
            print(f"📈 메모리 증가: {result['memory_growth_mb']:.1f}MB")
            print(f"🔝 최대 메모리: {result['peak_memory_mb']:.1f}MB")
            
            # 단계별 메모리 사용량 분석
            if self.memory_snapshots:
                print(f"\n📊 단계별 메모리 사용량:")
                for snapshot in self.memory_snapshots:
                    if snapshot["progress"] == 1.0:  # 완료된 단계만
                        print(f"  - {snapshot['stage']}: {snapshot['memory_mb']:.1f}MB")
            
            return result
            
        except Exception as e:
            print(f"❌ 실행 실패: {str(e)}")
            tracemalloc.stop()
            return {
                "num_applicants": num_applicants,
                "complexity": complexity,
                "status": "ERROR",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def run_full_benchmark(self):
        """전체 벤치마크 실행"""
        print("🚀 성능 벤치마크 테스트 시작")
        print("=" * 70)
        
        # 테스트 시나리오
        scenarios = [
            # (인원수, 복잡도)
            (10, "simple"),
            (25, "simple"),
            (50, "simple"),
            (100, "simple"),
            (25, "medium"),
            (50, "medium"),
            (100, "medium"),
            (200, "medium"),
            (50, "complex"),
            (100, "complex"),
            (200, "complex"),
            (300, "complex"),
        ]
        
        for num_applicants, complexity in scenarios:
            try:
                self.run_benchmark(num_applicants, complexity)
                time.sleep(1)  # 시스템 안정화
            except KeyboardInterrupt:
                print("\n⏹️ 사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"❌ 벤치마크 실패: {e}")
                continue
        
        # 결과 분석
        self.analyze_results()
    
    def analyze_results(self):
        """결과 분석 및 보고서 생성"""
        if not self.results:
            print("❌ 분석할 결과가 없습니다.")
            return
        
        print("\n" + "=" * 70)
        print("📊 성능 분석 보고서")
        print("=" * 70)
        
        # 성공한 결과만 필터링
        successful_results = [r for r in self.results if r["status"] == "SUCCESS"]
        
        if not successful_results:
            print("❌ 성공한 테스트가 없습니다.")
            return
        
        # 최고 성능
        best_throughput = max(successful_results, key=lambda x: x["throughput_per_sec"])
        print(f"🏆 최고 처리량: {best_throughput['throughput_per_sec']:.1f}명/초")
        print(f"   조건: {best_throughput['num_applicants']}명, {best_throughput['complexity']} 복잡도")
        
        # 대규모 처리 성능
        large_scale = [r for r in successful_results if r["num_applicants"] >= 200]
        if large_scale:
            avg_throughput = sum(r["throughput_per_sec"] for r in large_scale) / len(large_scale)
            print(f"📈 대규모(200명+) 평균 처리량: {avg_throughput:.1f}명/초")
        
        # 메모리 효율성
        memory_efficient = min(successful_results, key=lambda x: x["peak_memory_mb"])
        print(f"💾 최소 메모리 사용: {memory_efficient['peak_memory_mb']:.1f}MB")
        print(f"   조건: {memory_efficient['num_applicants']}명, {memory_efficient['complexity']} 복잡도")
        
        # 복잡도별 성능
        print(f"\n📊 복잡도별 평균 성능:")
        for complexity in ["simple", "medium", "complex"]:
            comp_results = [r for r in successful_results if r["complexity"] == complexity]
            if comp_results:
                avg_time = sum(r["execution_time"] for r in comp_results) / len(comp_results)
                avg_throughput = sum(r["throughput_per_sec"] for r in comp_results) / len(comp_results)
                avg_memory = sum(r["peak_memory_mb"] for r in comp_results) / len(comp_results)
                print(f"  - {complexity}: {avg_time:.3f}초, {avg_throughput:.1f}명/초, {avg_memory:.1f}MB")
        
        # 병목 구간 분석
        print(f"\n🔍 병목 구간 분석:")
        slow_results = [r for r in successful_results if r["execution_time"] > 2.0]
        if slow_results:
            print(f"  - 2초 이상 소요: {len(slow_results)}개 케이스")
            slowest = max(slow_results, key=lambda x: x["execution_time"])
            print(f"  - 최대 소요시간: {slowest['execution_time']:.3f}초 ({slowest['num_applicants']}명)")
        
        # 목표 달성 여부
        print(f"\n🎯 목표 달성 여부:")
        target_500_2min = [r for r in successful_results 
                          if r["num_applicants"] >= 300 and r["execution_time"] <= 120]
        if target_500_2min:
            print(f"  ✅ 대규모 2분 내 처리 가능 (300명+ 기준)")
        else:
            print(f"  ❌ 대규모 2분 내 처리 목표 미달성")
            print(f"      개선 필요: 알고리즘 최적화, 병렬 처리 등")


def main():
    """메인 실행 함수"""
    benchmark = PerformanceBenchmark()
    
    try:
        benchmark.run_full_benchmark()
    except KeyboardInterrupt:
        print("\n⏹️ 벤치마크가 중단되었습니다.")
    
    print(f"\n🏁 벤치마크 완료")
    print(f"총 {len(benchmark.results)}개 테스트 실행")


if __name__ == "__main__":
    main() 