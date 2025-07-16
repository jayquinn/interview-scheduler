#!/usr/bin/env python3
"""
app.py의 2단계 스케줄링 기능 테스트
실제 UI 플로우를 시뮬레이션하여 2단계 스케줄링이 제대로 작동하는지 확인
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solver.api import solve_for_days_two_phase
import core

def test_app_two_phase_scheduling():
    """app.py의 2단계 스케줄링 기능 테스트"""
    
    print("[app.py 2단계 스케줄링 기능 테스트]")
    print("=" * 60)
    
    # 1. app.py와 동일한 설정 구성
    print("1. app.py와 동일한 설정 구성...")
    
    # 세션 상태 초기화 (core.build_config에서 사용)
    import streamlit as st
    
    # 기본 활동 템플릿 (app.py와 동일)
    default_activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 스마트 직무 매핑 (app.py와 동일)
    job_data = {"code": ["JOB01", "JOB02", "JOB03", "JOB04", "JOB05", "JOB06", "JOB07", "JOB08", "JOB09", "JOB10", "JOB11"], 
                "count": [23, 23, 20, 20, 12, 15, 6, 6, 6, 3, 3]}
    for act in default_activities.query("use == True")["activity"].tolist():
        job_data[act] = True
    job_acts_map = pd.DataFrame(job_data)
    
    # 기본 선후행 제약 (app.py와 동일)
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 운영 시간 (app.py와 동일)
    oper_start_time = datetime.strptime("09:00", "%H:%M").time()
    oper_end_time = datetime.strptime("17:30", "%H:%M").time()
    
    # 스마트 방 템플릿 (app.py와 동일)
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 스마트 운영 공간 계획
    final_plan_dict = {}
    for rt, values in room_template.items():
        final_plan_dict[f"{rt}_count"] = values['count']
        final_plan_dict[f"{rt}_cap"] = values['cap']
    room_plan = pd.DataFrame([final_plan_dict])
    
    # 스마트 운영 시간
    oper_window_dict = {
        "start_time": oper_start_time.strftime("%H:%M"),
        "end_time": oper_end_time.strftime("%H:%M")
    }
    oper_window = pd.DataFrame([oper_window_dict])
    
    # 멀티 날짜 계획 (app.py의 4일치 데이터와 동일)
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
    
    # 세션 상태 설정 (app.py와 동일)
    st.session_state.update({
        "activities": default_activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "oper_start_time": oper_start_time,
        "oper_end_time": oper_end_time,
        "room_template": room_template,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "multidate_plans": multidate_plans,
        "group_min_size": 4,
        "group_max_size": 6,
        "global_gap_min": 5,
        "max_stay_hours": 8,
        "use_new_scheduler": True  # app.py에서 사용하는 설정
    })
    
    # 2. 설정 구성
    print("2. 설정 구성...")
    cfg = core.build_config(st.session_state)
    
    # 기본 파라미터 (app.py와 동일)
    params = {
        "min_gap_min": 5,
        "time_limit_sec": 120,
        "max_stay_hours": 12  # 1단계에서는 충분히 큰 값
    }
    
    # 3. 2단계 스케줄링 실행 (app.py와 동일한 방식)
    print("3. 2단계 스케줄링 실행...")
    print("   - app.py의 2단계 하드 제약 스케줄링 모드 시뮬레이션")
    print("   - 1단계: 초기 스케줄링 (소프트 제약)")
    print("   - 2단계: 체류시간 분석 및 하드 제약 산출")
    print("   - 3단계: 하드 제약 적용 2차 스케줄링")
    
    # 총 지원자 수 계산
    total_applicants = 0
    for date_key, plan in multidate_plans.items():
        if plan.get("enabled", True):
            for job in plan.get("jobs", []):
                total_applicants += job.get("count", 0)
    
    print(f"   - 총 지원자: {total_applicants}명")
    print(f"   - 총 날짜: {len(multidate_plans)}일")
    
    # app.py에서 사용하는 것과 동일한 방식으로 2단계 스케줄링 실행
    status, final_df, logs, limit, reports = solve_for_days_two_phase(
        cfg, params, debug=True, percentile=90.0
    )
    
    # 4. 결과 분석
    print("\n4. 결과 분석")
    print("=" * 60)
    
    print(f"스케줄링 상태: {status}")
    print(f"일일 처리 한계: {limit}명")
    print(f"최종 스케줄 항목: {len(final_df) if final_df is not None else 0}개")
    
    if status == "SUCCESS":
        print("app.py 2단계 스케줄링 성공!")
        
        # 제약 분석 리포트
        if 'constraint_analysis' in reports and not reports['constraint_analysis'].empty:
            print("\n날짜별 하드 제약 분석:")
            constraint_df = reports['constraint_analysis']
            print(constraint_df.to_string(index=False))
        
        # 제약 위반 리포트
        if 'constraint_violations' in reports and not reports['constraint_violations'].empty:
            print("\n제약 위반 분석:")
            violations_df = reports['constraint_violations']
            print(violations_df.to_string(index=False))
        
        # 단계별 비교 리포트
        if 'phase_comparison' in reports and not reports['phase_comparison'].empty:
            print("\n1단계 vs 2단계 비교:")
            comparison_df = reports['phase_comparison']
            print(comparison_df.to_string(index=False))
        
        # 결과 저장
        if final_df is not None and not final_df.empty:
            output_file = f"app_two_phase_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                final_df.to_excel(writer, sheet_name='Schedule', index=False)
                
                if 'constraint_analysis' in reports:
                    reports['constraint_analysis'].to_excel(writer, sheet_name='Hard_Constraint_Analysis', index=False)
                
                if 'constraint_violations' in reports:
                    reports['constraint_violations'].to_excel(writer, sheet_name='Constraint_Violations', index=False)
                
                if 'phase_comparison' in reports:
                    reports['phase_comparison'].to_excel(writer, sheet_name='Phase_Comparison', index=False)
            
            print(f"\n결과가 {output_file}에 저장되었습니다.")
    
    else:
        print("app.py 2단계 스케줄링 실패")
        print(f"오류: {logs}")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")

if __name__ == "__main__":
    test_app_two_phase_scheduling() 