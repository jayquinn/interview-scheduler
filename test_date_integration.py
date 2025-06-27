"""
날짜 설정 기능 통합 테스트
"""
import pandas as pd
from datetime import date, timedelta
from solver.api import solve_for_days_v2


def test_date_setting():
    """날짜 설정 기능 테스트"""
    print("🗓️ 날짜 설정 기능 테스트")
    print("=" * 50)
    
    # 테스트용 설정
    activities = pd.DataFrame({
        "use": [True, True],
        "activity": ["면접1", "면접2"],
        "mode": ["individual", "individual"],
        "duration_min": [30, 25],
        "room_type": ["면접실", "면접실"],
        "min_cap": [1, 1],
        "max_cap": [1, 1],
    })
    
    room_plan = pd.DataFrame({
        "면접실_count": [3],
        "면접실_cap": [1],
    })
    
    job_acts_map = pd.DataFrame({
        "code": ["개발직"],
        "count": [10],
        "면접1": [True],
        "면접2": [True]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:00"]
    })
    
    # 1. 날짜 없이 테스트 (기본값 사용)
    print("\n1️⃣ 날짜 미설정 테스트 (기본값: 내일)")
    cfg_no_date = {
        "activities": activities,
        "room_plan": room_plan,
        "job_acts_map": job_acts_map,
        "oper_window": oper_window,
        "precedence": pd.DataFrame()
    }
    
    status, df, logs, limit = solve_for_days_v2(cfg_no_date)
    print(f"상태: {status}")
    if not df.empty:
        unique_dates = df['interview_date'].dt.date.unique()
        print(f"스케줄된 날짜: {unique_dates}")
        print(f"스케줄 항목 수: {len(df)}")
    
    # 2. 특정 날짜 설정 테스트
    print("\n2️⃣ 특정 날짜 설정 테스트")
    target_date = date.today() + timedelta(days=7)  # 일주일 후
    
    cfg_with_date = cfg_no_date.copy()
    cfg_with_date["interview_date"] = target_date
    
    status, df, logs, limit = solve_for_days_v2(cfg_with_date)
    print(f"설정한 날짜: {target_date}")
    print(f"상태: {status}")
    if not df.empty:
        unique_dates = df['interview_date'].dt.date.unique()
        print(f"스케줄된 날짜: {unique_dates}")
        print(f"날짜 일치 여부: {target_date in unique_dates}")
        
        # 샘플 데이터 표시
        print(f"\n📅 스케줄 샘플:")
        sample = df.head(3)[['applicant_id', 'interview_date', 'activity_name', 'start_time']]
        print(sample.to_string(index=False))
    
    # 3. 문자열 날짜 테스트
    print("\n3️⃣ 문자열 날짜 테스트")
    target_date_str = "2025-07-15"
    
    cfg_with_str_date = cfg_no_date.copy()
    cfg_with_str_date["interview_date"] = target_date_str
    
    status, df, logs, limit = solve_for_days_v2(cfg_with_str_date)
    print(f"설정한 날짜 (문자열): {target_date_str}")
    print(f"상태: {status}")
    if not df.empty:
        unique_dates = df['interview_date'].dt.date.unique()
        print(f"스케줄된 날짜: {unique_dates}")
        expected_date = date(2025, 7, 15)
        print(f"날짜 일치 여부: {expected_date in unique_dates}")
    
    print("\n" + "=" * 50)
    print("✅ 날짜 설정 기능 테스트 완료")


if __name__ == "__main__":
    test_date_setting() 