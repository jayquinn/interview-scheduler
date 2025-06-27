"""
실시간 모니터링 기능 테스트
"""
import pandas as pd
from datetime import time
import time as time_module
from solver.api import solve_for_days_v2
from solver.types import ProgressInfo


class ProgressMonitor:
    """진행 상황 모니터링 클래스"""
    
    def __init__(self):
        self.stages = []
        self.start_time = time_module.time()
        
    def callback(self, info: ProgressInfo):
        """진행 상황 콜백"""
        elapsed = time_module.time() - self.start_time
        
        print(f"[{elapsed:6.2f}s] 🎯 {info.stage}: {info.message}")
        
        if info.details:
            details = []
            for key, value in info.details.items():
                if key == "time":
                    details.append(f"소요시간: {value:.1f}초")
                elif key == "groups":
                    details.append(f"그룹: {value}개")
                elif key == "dummies":
                    details.append(f"더미: {value}명")
                elif key == "schedule_count":
                    details.append(f"스케줄: {value}개")
                elif key == "backtrack_count":
                    details.append(f"백트래킹: {value}회")
                else:
                    details.append(f"{key}: {value}")
            
            if details:
                print(f"          📊 {' | '.join(details)}")
        
        self.stages.append({
            "time": elapsed,
            "stage": info.stage,
            "progress": info.progress,
            "message": info.message,
            "details": info.details
        })
        
        # Progress bar 시뮬레이션
        bar_length = 30
        filled = int(bar_length * info.progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"          [{bar}] {info.progress*100:5.1f}%")
        print()


def create_test_config():
    """테스트용 설정 생성"""
    
    # 활동 설정 - 적절한 시간 배분
    activities = pd.DataFrame({
        "use": [True, True, True, True],
        "activity": ["토론면접", "인성면접", "발표준비", "발표면접"],
        "mode": ["batched", "individual", "individual", "individual"],
        "duration_min": [60, 25, 15, 20],  # 시간 단축
        "room_type": ["토론실", "면접실", "준비실", "발표실"],
        "min_cap": [4, 1, 1, 1],
        "max_cap": [6, 1, 1, 1],
    })
    
    # 방 계획 - 충분한 방 확보
    room_plan = pd.DataFrame({
        "토론실_count": [4],
        "토론실_cap": [6],
        "면접실_count": [6],
        "면접실_cap": [1],
        "준비실_count": [4],
        "준비실_cap": [1],
        "발표실_count": [4],
        "발표실_cap": [1],
    })
    
    # 직무별 활동 매핑 - 적절한 규모
    job_acts_map = pd.DataFrame({
        "code": ["개발직"],
        "count": [25],  # 25명으로 조정
        "토론면접": [True],
        "인성면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    # 운영 시간
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["18:00"]
    })
    
    # 선후행 제약
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
        "precedence": precedence
    }


def test_real_time_monitoring():
    """실시간 모니터링 테스트"""
    print("=" * 70)
    print("🚀 실시간 모니터링 테스트")
    print("=" * 70)
    print(f"시작 시간: {time_module.strftime('%H:%M:%S')}")
    print()
    
    # 모니터 생성
    monitor = ProgressMonitor()
    
    # 테스트 설정
    cfg_ui = create_test_config()
    params = {"max_stay_hours": 9}
    
    # 실시간 모니터링과 함께 스케줄링 실행
    status, final_df, logs, daily_limit = solve_for_days_v2(
        cfg_ui, 
        params, 
        debug=False,
        progress_callback=monitor.callback
    )
    
    print("=" * 70)
    print("📊 최종 결과")
    print("=" * 70)
    print(f"상태: {status}")
    print(f"일일 처리 한도: {daily_limit}명")
    print(f"스케줄 항목 수: {len(final_df) if final_df is not None else 0}")
    print(f"총 소요 시간: {time_module.time() - monitor.start_time:.2f}초")
    
    # 단계별 소요 시간 분석
    print("\n📈 단계별 분석:")
    current_stage = None
    stage_start = 0
    
    for stage_info in monitor.stages:
        if stage_info["stage"] != current_stage:
            if current_stage:
                duration = stage_info["time"] - stage_start
                print(f"  ✅ {current_stage}: {duration:.2f}초")
            current_stage = stage_info["stage"]
            stage_start = stage_info["time"]
    
    # 마지막 단계
    if current_stage:
        duration = monitor.stages[-1]["time"] - stage_start
        print(f"  ✅ {current_stage}: {duration:.2f}초")
    
    if final_df is not None and not final_df.empty:
        print(f"\n📅 스케줄 샘플 (상위 5개):")
        print(final_df.head(5)[['applicant_id', 'activity_name', 'start_time', 'room_name']].to_string(index=False))
        
        print(f"\n📊 활동별 분포:")
        activity_counts = final_df['activity_name'].value_counts()
        for activity, count in activity_counts.items():
            print(f"  - {activity}: {count}명")
    
    return status == "SUCCESS"


def test_backtracking_scenario():
    """백트래킹이 발생하는 시나리오 테스트"""
    print("\n" + "=" * 70)
    print("🔄 백트래킹 시나리오 테스트")
    print("=" * 70)
    
    # 백트래킹이 발생할 수 있는 까다로운 설정
    activities = pd.DataFrame({
        "use": [True, True],
        "activity": ["토론면접", "인성면접"],
        "mode": ["batched", "individual"],
        "duration_min": [120, 60],  # 긴 시간
        "room_type": ["토론실", "면접실"],
        "min_cap": [5, 1],
        "max_cap": [5, 1],  # 엄격한 제약
    })
    
    # 부족한 방 설정
    room_plan = pd.DataFrame({
        "토론실_count": [1],  # 방이 부족
        "토론실_cap": [5],
        "면접실_count": [1],  # 방이 부족
        "면접실_cap": [1],
    })
    
    # 많은 지원자
    job_acts_map = pd.DataFrame({
        "code": ["개발직"],
        "count": [30],  # 30명
        "토론면접": [True],
        "인성면접": [True]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["13:00"]  # 짧은 운영 시간
    })
    
    cfg_ui = {
        "activities": activities,
        "room_plan": room_plan,
        "job_acts_map": job_acts_map,
        "oper_window": oper_window,
        "precedence": pd.DataFrame()  # 빈 제약
    }
    
    monitor = ProgressMonitor()
    
    status, final_df, logs, daily_limit = solve_for_days_v2(
        cfg_ui, 
        {"max_stay_hours": 8}, 
        debug=False,
        progress_callback=monitor.callback
    )
    
    print(f"백트래킹 테스트 결과: {status}")
    if "Backtrack" in [s["stage"] for s in monitor.stages]:
        print("✅ 백트래킹이 성공적으로 감지되었습니다!")
    else:
        print("ℹ️ 이 시나리오에서는 백트래킹이 발생하지 않았습니다.")


def main():
    """메인 실행 함수"""
    print("🎯 실시간 모니터링 기능 테스트 시작")
    
    # 1. 정상 시나리오 테스트
    success = test_real_time_monitoring()
    
    # 2. 백트래킹 시나리오 테스트
    test_backtracking_scenario()
    
    # 3. 결과 요약
    print("\n" + "=" * 70)
    print("🏁 테스트 완료")
    print("=" * 70)
    
    if success:
        print("✅ 실시간 모니터링이 성공적으로 작동합니다!")
        print("🎯 UI 연동 준비 완료")
    else:
        print("❌ 테스트에 실패했습니다.")
        print("🔧 설정을 확인해주세요.")


if __name__ == "__main__":
    main() 