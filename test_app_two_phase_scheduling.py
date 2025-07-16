#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py UI 기본 데이터를 사용한 2단계 스케줄링 테스트
1차 스케줄링 → 체류시간 통계 분석 → 하드 제약 설정 → 2차 스케줄링
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, time, date, timedelta
import warnings
warnings.filterwarnings('ignore')

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solver.api import solve_for_days_two_phase, get_scheduler_comparison
from solver.types import ProgressInfo

def get_app_default_data():
    """app.py의 UI 기본 데이터를 cfg_ui 형태로 반환"""
    
    # 기본 활동 템플릿 (app.py와 동일)
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 스마트 직무 매핑 (app.py와 동일)
    act_list = activities.query("use == True")["activity"].tolist()
    job_data = {"code": ["JOB01"], "count": [20]}
    for act in act_list:
        job_data[act] = True
    job_acts_map = pd.DataFrame(job_data)
    
    # 기본 선후행 제약 (app.py와 동일)
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 기본 운영 시간 (app.py와 동일: 09:00 ~ 17:30)
    oper_start_time = time(9, 0)
    oper_end_time = time(17, 30)
    
    # 스마트 방 템플릿 (app.py와 동일)
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 스마트 운영 공간 계획 (room_template 기반으로 자동 생성)
    final_plan_dict = {}
    for rt, values in room_template.items():
        final_plan_dict[f"{rt}_count"] = values['count']
        final_plan_dict[f"{rt}_cap"] = values['cap']
    room_plan = pd.DataFrame([final_plan_dict])
    
    # 스마트 운영 시간 (자동 생성)
    oper_window_dict = {
        "start_time": oper_start_time.strftime("%H:%M"),
        "end_time": oper_end_time.strftime("%H:%M")
    }
    oper_window = pd.DataFrame([oper_window_dict])
    
    # 멀티 날짜 계획 (app.py와 동일)
    today = date.today()
    multidate_plans = {
        today.strftime('%Y-%m-%d'): {
            "date": today,
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 23},
                {"code": "JOB02", "count": 23}
            ]
        },
        (today + timedelta(days=1)).strftime('%Y-%m-%d'): {
            "date": today + timedelta(days=1),
            "enabled": True,
            "jobs": [
                {"code": "JOB03", "count": 20},
                {"code": "JOB04", "count": 20}
            ]
        },
        (today + timedelta(days=2)).strftime('%Y-%m-%d'): {
            "date": today + timedelta(days=2),
            "enabled": True,
            "jobs": [
                {"code": "JOB05", "count": 12},
                {"code": "JOB06", "count": 15},
                {"code": "JOB07", "count": 6}
            ]
        },
        (today + timedelta(days=3)).strftime('%Y-%m-%d'): {
            "date": today + timedelta(days=3),
            "enabled": True,
            "jobs": [
                {"code": "JOB08", "count": 6},
                {"code": "JOB09", "count": 6},
                {"code": "JOB10", "count": 3},
                {"code": "JOB11", "count": 3}
            ]
        }
    }
    
    # 집단면접 설정 (app.py와 동일)
    group_min_size = 4
    group_max_size = 6
    global_gap_min = 5
    max_stay_hours = 5
    
    # cfg_ui 형태로 반환
    cfg_ui = {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'precedence': precedence,
        'oper_start_time': oper_start_time,
        'oper_end_time': oper_end_time,
        'room_template': room_template,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'multidate_plans': multidate_plans,
        'group_min_size': group_min_size,
        'group_max_size': group_max_size,
        'global_gap_min': global_gap_min,
        'max_stay_hours': max_stay_hours
    }
    
    return cfg_ui

def analyze_stay_time_differences(phase1_schedule, phase2_schedule):
    """1차와 2차 스케줄링 간 체류시간 차이 분석"""
    
    def calculate_stay_times(schedule_df):
        """스케줄에서 체류시간 계산"""
        if schedule_df is None or schedule_df.empty:
            return pd.DataFrame()
        
        stay_times = []
        
        for date in schedule_df['date'].unique():
            df_day = schedule_df[schedule_df['date'] == date]
            
            for applicant in df_day['applicant'].unique():
                applicant_schedule = df_day[df_day['applicant'] == applicant].sort_values('start_time')
                
                if len(applicant_schedule) > 0:
                    first_activity = applicant_schedule.iloc[0]
                    last_activity = applicant_schedule.iloc[-1]
                    
                    start_time = pd.to_datetime(f"{date} {first_activity['start_time']}")
                    end_time = pd.to_datetime(f"{date} {last_activity['end_time']}")
                    
                    stay_duration = (end_time - start_time).total_seconds() / 3600  # 시간 단위
                    
                    stay_times.append({
                        'date': date,
                        'applicant': applicant,
                        'job': first_activity.get('job', 'Unknown'),
                        'stay_hours': stay_duration,
                        'activity_count': len(applicant_schedule)
                    })
        
        return pd.DataFrame(stay_times)
    
    # 1차와 2차 스케줄링의 체류시간 계산
    phase1_stay_times = calculate_stay_times(phase1_schedule)
    phase2_stay_times = calculate_stay_times(phase2_schedule)
    
    if phase1_stay_times.empty or phase2_stay_times.empty:
        return pd.DataFrame()
    
    # 분석 결과 생성
    analysis_results = []
    
    # 날짜별 비교
    for date in phase1_stay_times['date'].unique():
        phase1_date = phase1_stay_times[phase1_stay_times['date'] == date]
        phase2_date = phase2_stay_times[phase2_stay_times['date'] == date]
        
        if len(phase1_date) > 0 and len(phase2_date) > 0:
            phase1_mean = phase1_date['stay_hours'].mean()
            phase2_mean = phase2_date['stay_hours'].mean()
            phase1_std = phase1_date['stay_hours'].std()
            phase2_std = phase2_date['stay_hours'].std()
            phase1_max = phase1_date['stay_hours'].max()
            phase2_max = phase2_date['stay_hours'].max()
            phase1_min = phase1_date['stay_hours'].min()
            phase2_min = phase2_date['stay_hours'].min()
            
            analysis_results.append({
                'date': date,
                'phase1_mean_hours': round(phase1_mean, 2),
                'phase2_mean_hours': round(phase2_mean, 2),
                'mean_difference': round(phase2_mean - phase1_mean, 2),
                'phase1_std_hours': round(phase1_std, 2),
                'phase2_std_hours': round(phase2_std, 2),
                'std_difference': round(phase2_std - phase1_std, 2),
                'phase1_max_hours': round(phase1_max, 2),
                'phase2_max_hours': round(phase2_max, 2),
                'max_difference': round(phase2_max - phase1_max, 2),
                'phase1_min_hours': round(phase1_min, 2),
                'phase2_min_hours': round(phase2_min, 2),
                'min_difference': round(phase2_min - phase1_min, 2),
                'applicant_count': len(phase1_date)
            })
    
    return pd.DataFrame(analysis_results)

def main():
    """메인 실행 함수"""
    print("🚀 app.py UI 기본 데이터로 2단계 스케줄링 시작")
    print("=" * 60)
    
    # app.py의 기본 데이터 가져오기
    data = get_app_default_data()
    
    print("📊 입력 데이터 확인:")
    print(f"- 활동 수: {len(data['activities'])}")
    print(f"- 직무 수: {len(data['job_acts_map'])}")
    print(f"- 날짜 수: {len(data['multidate_plans'])}")
    print(f"- 총 지원자 수: {sum(sum(job['count'] for job in day['jobs']) for day in data['multidate_plans'].values())}")
    
    # 2단계 스케줄링 실행
    print("\n🔄 2단계 스케줄링 실행 중...")
    try:
        result = solve_for_days_two_phase(
            cfg_ui=data,
            params=None,
            debug=False,
            progress_callback=None,
            percentile=90.0
        )
        status, schedule_df, logs, daily_limit, reports = result
        if status == "SUCCESS":
            print("✅ 2단계 스케줄링 성공!")
            # 주요 리포트 추출
            constraint_df = reports.get('constraint_analysis')
            comparison_df = reports.get('phase_comparison')
            individual_stay_df = None
            if schedule_df is not None and not schedule_df.empty:
                # 개별 체류시간 시트 생성
                from solver.hard_constraint_analyzer import HardConstraintAnalyzer
                analyzer = HardConstraintAnalyzer(percentile=90.0)
                individual_stay_df = analyzer._calculate_stay_times(schedule_df)
            # 엑셀 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"app_two_phase_scheduling_{timestamp}.xlsx"
            print(f"\n💾 결과를 {filename}에 저장 중...")
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                if schedule_df is not None and not schedule_df.empty:
                    schedule_df.to_excel(writer, sheet_name='최종_스케줄', index=False)
                if constraint_df is not None and not constraint_df.empty:
                    constraint_df.to_excel(writer, sheet_name='Hard_Constraint_Analysis', index=False)
                if comparison_df is not None and not comparison_df.empty:
                    comparison_df.to_excel(writer, sheet_name='Phase_Comparison', index=False)
                if individual_stay_df is not None and not individual_stay_df.empty:
                    individual_stay_df.to_excel(writer, sheet_name='Individual_StayTime', index=False)
            print(f"✅ 결과가 {filename}에 저장되었습니다!")
            # 주요 분석 결과 출력
            if constraint_df is not None and not constraint_df.empty:
                print("\n[Hard Constraint Analysis]")
                print(constraint_df.to_string(index=False))
            if comparison_df is not None and not comparison_df.empty:
                print("\n[1차 vs 2차 체류시간 비교]")
                print(comparison_df.to_string(index=False))
        else:
            print("❌ 2단계 스케줄링 실패!")
            print(f"상태: {status}")
            print(f"로그: {logs}")
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 