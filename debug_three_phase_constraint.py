#!/usr/bin/env python3
"""
3단계 스케줄링 제약 디버그
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

def debug_three_phase_constraint():
    """3단계 스케줄링 제약 디버그"""
    
    print("=== 3단계 스케줄링 제약 디버그 ===")
    
    # UI 설정 구성
    cfg_ui = {
        "multidate_plans": {},
        "activities": pd.DataFrame({
            "use": [True, True, True],
            "activity": ["토론면접", "발표준비", "발표면접"],
            "mode": ["batched", "parallel", "individual"],
            "duration_min": [30, 5, 15],
            "room_type": ["토론면접실", "발표준비실", "발표면접실"],
            "min_cap": [4, 1, 1],
            "max_cap": [6, 2, 1]
        }),
        "room_template": {
            "토론면접실": {"count": 2, "cap": 6},
            "발표준비실": {"count": 1, "cap": 2},
            "발표면접실": {"count": 2, "cap": 1}
        },
        "room_plan": pd.DataFrame({
            "토론면접실_count": [2],
            "토론면접실_cap": [6],
            "발표준비실_count": [1],
            "발표준비실_cap": [2],
            "발표면접실_count": [2],
            "발표면접실_cap": [1]
        }),
        "precedence": pd.DataFrame([
            {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
        ]),
        "oper_start_time": "09:00",
        "oper_end_time": "17:30",
        "global_gap_min": 5,
        "max_stay_hours": 8,
        "group_min_size": 4,
        "group_max_size": 6
    }
    
    # 날짜별 계획 추가
    today = date.today()
    date_jobs = [
        (today, [{"code": "JOB01", "count": 23}, {"code": "JOB02", "count": 23}]),
    ]
    
    for d, jobs in date_jobs:
        cfg_ui["multidate_plans"][d.strftime("%Y-%m-%d")] = {
            "date": d.strftime("%Y-%m-%d"),
            "enabled": True,
            "jobs": jobs
        }
    
    # 1단계: 기본 스케줄링
    print("\n[1단계] 기본 스케줄링...")
    from solver.api import solve_for_days_v2
    
    status1, df1, logs1, limit1 = solve_for_days_v2(cfg_ui, params={}, debug=True)
    
    if status1 != "SUCCESS":
        print(f"  1단계 스케줄링 실패: {status1}")
        return
    
    print(f"  1단계 스케줄링 성공: {len(df1)}개 스케줄")
    
    # 1단계 체류시간 분석
    phase1_max_stay = analyze_max_stay_time(df1)
    print(f"  1단계 최대 체류시간: {phase1_max_stay:.2f}시간")
    
    # 2단계: 90% 백분위수 제약
    print("\n[2단계] 90% 백분위수 제약...")
    from solver.api import solve_for_days_two_phase
    
    status2, df2, logs2, limit2, reports2 = solve_for_days_two_phase(cfg_ui, params={}, debug=True)
    
    if status2 != "SUCCESS":
        print(f"  2단계 스케줄링 실패: {status2}")
        return
    
    print(f"  2단계 스케줄링 성공: {len(df2)}개 스케줄")
    
    # 2단계 체류시간 분석
    phase2_max_stay = analyze_max_stay_time(df2)
    print(f"  2단계 최대 체류시간: {phase2_max_stay:.2f}시간")
    
    # 2단계 결과에서 80% 백분위수 계산
    phase2_stay_times = calculate_stay_times(df2)
    phase2_80th_percentile = np.percentile(phase2_stay_times, 80)
    print(f"  2단계 80% 백분위수: {phase2_80th_percentile:.2f}시간")
    
    # 3단계: 80% 백분위수 제약 적용
    print(f"\n[3단계] 80% 백분위수 제약 적용 ({phase2_80th_percentile:.2f}시간)...")
    
    # 3단계용 설정
    cfg_ui_phase3 = cfg_ui.copy()
    cfg_ui_phase3['max_stay_hours'] = phase2_80th_percentile
    
    print(f"  3단계 설정:")
    print(f"    - cfg_ui['max_stay_hours']: {cfg_ui_phase3['max_stay_hours']}")
    print(f"    - params['max_stay_hours']: {phase2_80th_percentile}")
    
    # 3단계 스케줄링 실행
    status3, df3, logs3, limit3 = solve_for_days_v2(
        cfg_ui_phase3, 
        params={'max_stay_hours': phase2_80th_percentile}, 
        debug=True
    )
    
    print(f"  3단계 스케줄링 결과:")
    print(f"    - 상태: {status3}")
    print(f"    - 스케줄 수: {len(df3) if df3 is not None else 0}")
    
    if status3 == "SUCCESS":
        # 3단계 체류시간 분석
        phase3_max_stay = analyze_max_stay_time(df3)
        print(f"  3단계 최대 체류시간: {phase3_max_stay:.2f}시간")
        
        # 제약 준수 확인
        if phase3_max_stay <= phase2_80th_percentile:
            print(f"  ✅ 3단계 제약 준수: {phase3_max_stay:.2f}시간 <= {phase2_80th_percentile:.2f}시간")
        else:
            print(f"  ❌ 3단계 제약 위반: {phase3_max_stay:.2f}시간 > {phase2_80th_percentile:.2f}시간")
        
        # 1단계와 비교
        if phase3_max_stay == phase1_max_stay:
            print(f"  ⚠️ 3단계가 1단계와 동일한 결과!")
        else:
            print(f"  ✅ 3단계가 1단계와 다른 결과")
    else:
        print(f"  ❌ 3단계 스케줄링 실패: {logs3}")
    
    # 로그 분석
    print(f"\n=== 로그 분석 ===")
    print("3단계 로그:")
    print(logs3)

def analyze_max_stay_time(df):
    """DataFrame에서 최대 체류시간 계산"""
    if df.empty:
        return 0
    
    df_temp = df.copy()
    df_temp['interview_date'] = pd.to_datetime(df_temp['interview_date'])
    
    max_stay = 0
    for applicant_id in df_temp['applicant_id'].unique():
        applicant_df = df_temp[df_temp['applicant_id'] == applicant_id]
        start_time = applicant_df['start_time'].min()
        end_time = applicant_df['end_time'].max()
        stay_hours = (end_time - start_time).total_seconds() / 3600
        max_stay = max(max_stay, stay_hours)
    
    return max_stay

def calculate_stay_times(df):
    """DataFrame에서 모든 체류시간 계산"""
    if df.empty:
        return []
    
    df_temp = df.copy()
    df_temp['interview_date'] = pd.to_datetime(df_temp['interview_date'])
    
    stay_times = []
    for applicant_id in df_temp['applicant_id'].unique():
        applicant_df = df_temp[df_temp['applicant_id'] == applicant_id]
        start_time = applicant_df['start_time'].min()
        end_time = applicant_df['end_time'].max()
        stay_hours = (end_time - start_time).total_seconds() / 3600
        stay_times.append(stay_hours)
    
    return stay_times

if __name__ == "__main__":
    debug_three_phase_constraint() 