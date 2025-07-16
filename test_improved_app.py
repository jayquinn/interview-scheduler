#!/usr/bin/env python3
"""
개선된 app.py의 2단계 스케줄링 기능 테스트
계층적 스케줄러 v2가 자동으로 2단계 스케줄링을 포함하는지 확인
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

def test_improved_app_two_phase():
    """개선된 app.py의 2단계 스케줄링 기능 테스트"""
    
    print("[개선된 app.py 2단계 스케줄링 기능 테스트]")
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
        "duration_min": [30, 5, 15],  # 원래 UI 기본값
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],  # 원래 UI 기본값
    })
    
    # 지원자 데이터 (app.py와 동일한 기본값)
    job_codes = ["JOB01", "JOB02", "JOB03", "JOB04", "JOB05", 
                 "JOB06", "JOB07", "JOB08", "JOB09", "JOB10", "JOB11"]
    
    # 원래 UI의 정확한 지원자 수
    job_counts = [23, 23, 20, 20, 12, 15, 6, 6, 6, 3, 3]  # 총 137명
    
    # 날짜별 직무/인원 분포 (app.py 기본값)
    multidate_plans = {
        '2025-07-15': {'date': date(2025,7,15), 'enabled': True, 'jobs': [{'code': 'JOB01', 'count': 23}, {'code': 'JOB02', 'count': 23}]},
        '2025-07-16': {'date': date(2025,7,16), 'enabled': True, 'jobs': [{'code': 'JOB03', 'count': 20}, {'code': 'JOB04', 'count': 20}]},
        '2025-07-17': {'date': date(2025,7,17), 'enabled': True, 'jobs': [{'code': 'JOB05', 'count': 12}, {'code': 'JOB06', 'count': 15}, {'code': 'JOB07', 'count': 6}]},
        '2025-07-18': {'date': date(2025,7,18), 'enabled': True, 'jobs': [{'code': 'JOB08', 'count': 6}, {'code': 'JOB09', 'count': 6}, {'code': 'JOB10', 'count': 3}, {'code': 'JOB11', 'count': 3}]}
    }
    st.session_state["multidate_plans"] = multidate_plans

    # candidates_df 생성 (날짜별 직무 분포에 맞게)
    candidates_data = []
    for day in multidate_plans.values():
        for job in day['jobs']:
            for j in range(job['count']):
                candidates_data.append({
                    "id": f"{job['code']}_{j+1:03d}",
                    "job_code": job['code'],
                    "name": f"지원자_{job['code']}_{j+1:03d}"
                })
    candidates_df = pd.DataFrame(candidates_data)

    # job_acts_map 생성 (날짜별 직무 분포에 맞게)
    act_list = default_activities.query("use == True")['activity'].tolist()
    job_acts_map_data = []
    all_job_codes = set()
    for day in multidate_plans.values():
        for job in day['jobs']:
            all_job_codes.add(job['code'])
    for job_code in sorted(all_job_codes):
        count = len(candidates_df[candidates_df['job_code'] == job_code])
        row = {"code": job_code, "count": count}
        for act in act_list:
            row[act] = True
        job_acts_map_data.append(row)
    st.session_state["job_acts_map"] = pd.DataFrame(job_acts_map_data)

    # interview_dates도 multidate_plans에서 추출
    interview_dates = [v['date'] for v in multidate_plans.values()]
    st.session_state["interview_dates"] = interview_dates
    
    # 운영 시간 (원래 UI: 09:00 ~ 17:30)
    operating_hours = {
        "start_time": "09:00",
        "end_time": "17:30"  # 원래 UI 기본값
    }
    
    # 공간 정보 (원래 UI와 동일)
    rooms_data = [
        {"room_name": "토론면접실1", "room_type": "토론면접실", "capacity": 6},
        {"room_name": "토론면접실2", "room_type": "토론면접실", "capacity": 6},
        {"room_name": "발표준비실1", "room_type": "발표준비실", "capacity": 2},
        {"room_name": "발표면접실1", "room_type": "발표면접실", "capacity": 1},
        {"room_name": "발표면접실2", "room_type": "발표면접실", "capacity": 1},
    ]
    
    rooms_df = pd.DataFrame(rooms_data)
    
    # 우선순위 제약 (원래 UI와 동일)
    precedence_data = [
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ]
    
    precedence_df = pd.DataFrame(precedence_data)
    
    # 2. 설정을 session_state에 저장
    print("2. 설정을 session_state에 저장...")
    
    st.session_state["activities"] = default_activities
    st.session_state["candidates"] = candidates_df
    st.session_state["oper_start_time"] = datetime.strptime("09:00", "%H:%M").time()
    st.session_state["oper_end_time"] = datetime.strptime("17:30", "%H:%M").time()
    st.session_state["operating_hours"] = operating_hours
    st.session_state["precedence"] = precedence_df
    st.session_state["global_gap_min"] = 5
    st.session_state["max_stay_hours"] = 5

    # room_template 및 room_plan 생성 (원래 UI 기본값)
    room_types = default_activities['room_type'].unique()
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},  # 원래 UI 기본값
        "발표준비실": {"count": 1, "cap": 2},  # 원래 UI 기본값
        "발표면접실": {"count": 2, "cap": 1}   # 원래 UI 기본값
    }
    st.session_state["room_template"] = room_template
    final_plan_dict = {}
    for rt, values in room_template.items():
        final_plan_dict[f"{rt}_count"] = values['count']
        final_plan_dict[f"{rt}_cap"] = values['cap']
    st.session_state["room_plan"] = pd.DataFrame([final_plan_dict])

    # oper_window 생성 (원래 UI: 09:00 ~ 17:30)
    st.session_state["oper_window"] = pd.DataFrame([{"start_time": "09:00", "end_time": "17:30"}])

    # 3. 설정 구성
    print("3. 설정 구성...")
    
    cfg = core.build_config(st.session_state)
    
    # 스케줄링 파라미터 (UI와 동일하게)
    params = {
        "min_gap_min": st.session_state.get('global_gap_min', 5),
        "time_limit_sec": 120,
        "max_stay_hours": st.session_state.get('max_stay_hours', 5)
    }
    # batched 모드가 있으면 추가
    if any(default_activities["mode"] == "batched"):
        params["group_min_size"] = 4
        params["group_max_size"] = 4
    
    print(f"설정 완료:")
    print(f"- 지원자 수: {len(candidates_df)}명")
    print(f"- 면접 날짜: {len(interview_dates)}일")
    print(f"- 활동 수: {len(default_activities)}개")
    print(f"- 공간 수: {len(rooms_df)}개")
    
    # 4. 1차 스케줄링(v2) 실행
    print("\n4. 1차 스케줄링(v2) 실행...")
    from solver.api import solve_for_days_v2
    start_time = datetime.now()
    try:
        status1, final_schedule1, logs1, limit1 = solve_for_days_v2(
            cfg, params, debug=False
        )
    except Exception as e:
        print(f"❌ solve_for_days_v2 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    end_time = datetime.now()
    execution_time1 = (end_time - start_time).total_seconds()
    print(f"1차 실행 시간: {execution_time1:.2f}초")
    print(f"1차 스케줄링 상태: {status1}")
    if status1 == "SUCCESS" and final_schedule1 is not None and not final_schedule1.empty:
        print(f"✅ 1차 스케줄링 성공! 스케줄 항목: {len(final_schedule1)}개")
    else:
        print(f"❌ 1차 스케줄링 실패: {status1}")
        print(f"final_schedule1: {final_schedule1}")
        print(f"logs1: {logs1}")
        return False

    # 5. 2차 스케줄링(하드제약) 실행
    print("\n5. 2차 하드제약 스케줄링 실행...")
    start_time = datetime.now()
    try:
        status2, final_schedule2, logs2, limit2, reports2 = solve_for_days_two_phase(
            cfg, params, debug=False, percentile=90.0
        )
    except Exception as e:
        print(f"❌ solve_for_days_two_phase 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    end_time = datetime.now()
    execution_time2 = (end_time - start_time).total_seconds()
    print(f"2차 실행 시간: {execution_time2:.2f}초")
    print(f"2차 스케줄링 상태: {status2}")
    if status2 == "SUCCESS" and final_schedule2 is not None and not final_schedule2.empty:
        print(f"✅ 2차 스케줄링 성공! 스케줄 항목: {len(final_schedule2)}개")
    else:
        print(f"❌ 2차 스케줄링 실패: {status2}")
        print(f"final_schedule2: {final_schedule2}")
        print(f"logs2: {logs2}")
        print(f"reports2: {reports2}")
        return False
    return True

if __name__ == "__main__":
    success = test_improved_app_two_phase()
    
    if success:
        print("\n🎉 테스트 성공!")
    else:
        print("\n❌ 테스트 실패!")
        sys.exit(1) 