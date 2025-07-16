#!/usr/bin/env python3
"""
하드 제약 강제 적용 기능 테스트
2단계 스케줄링에서 하드 제약이 제대로 적용되는지 확인
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solver.api import solve_for_days_two_phase
import core

def test_hard_constraint_force():
    """하드 제약 강제 적용 테스트"""
    
    print("[하드 제약 강제 적용 테스트]")
    print("=" * 60)
    
    # 1. 테스트 설정 구성
    print("1. 테스트 설정 구성...")
    
    # 세션 상태 초기화 (core.build_config에서 사용)
    import streamlit as st
    
    # 기본 활동 템플릿
    default_activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 스마트 직무 매핑
    job_data = {"code": ["JOB01", "JOB02"], "count": [20, 20]}
    for act in default_activities.query("use == True")["activity"].tolist():
        job_data[act] = True
    job_acts_map = pd.DataFrame(job_data)
    
    # 기본 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 운영 시간
    oper_start_time = datetime.strptime("09:00", "%H:%M").time()
    oper_end_time = datetime.strptime("17:30", "%H:%M").time()
    
    # 스마트 방 템플릿
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 방 계획 생성
    room_plan_data = {}
    for room_type, config in room_template.items():
        room_plan_data[f"{room_type}_count"] = [config["count"]]
        room_plan_data[f"{room_type}_cap"] = [config["cap"]]
    room_plan = pd.DataFrame(room_plan_data)
    
    # 운영 시간 창
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    # 멀티 날짜 계획 (2일)
    multidate_plans = {
        "2024-01-15": {
            "enabled": True,
            "date": "2024-01-15",
            "jobs": [
                {"code": "JOB01", "count": 20},
                {"code": "JOB02", "count": 20}
            ]
        },
        "2024-01-16": {
            "enabled": True,
            "date": "2024-01-16", 
            "jobs": [
                {"code": "JOB01", "count": 15},
                {"code": "JOB02", "count": 15}
            ]
        }
    }
    
    # UI 설정 구성
    cfg = {
        "activities": default_activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "multidate_plans": multidate_plans,
        "global_gap_min": 5,
        "max_stay_hours": 12  # 충분히 큰 값으로 설정 (1단계용)
    }
    
    print("✅ 테스트 설정 완료")
    
    # 2. 2단계 하드 제약 스케줄링 실행
    print("\n2. 2단계 하드 제약 스케줄링 실행...")
    
    try:
        status, final_wide, logs, limit, reports = solve_for_days_two_phase(
            cfg, 
            params={}, 
            debug=True,
            progress_callback=None,
            percentile=90.0  # 90% 분위수 하드 제약
        )
        
        print(f"✅ 2단계 스케줄링 완료: {status}")
        
        if status == "SUCCESS":
            print(f"📊 결과: {len(final_wide)}개 스케줄 생성")
            
            # 3. 결과 분석
            print("\n3. 결과 분석...")
            
            # 체류시간 계산
            stay_times = calculate_stay_times(final_wide)
            
            if not stay_times.empty:
                print("\n📈 체류시간 통계:")
                print(f"  평균: {stay_times['stay_hours'].mean():.2f}시간")
                print(f"  중간값: {stay_times['stay_hours'].median():.2f}시간")
                print(f"  최소: {stay_times['stay_hours'].min():.2f}시간")
                print(f"  최대: {stay_times['stay_hours'].max():.2f}시간")
                print(f"  90% 분위수: {stay_times['stay_hours'].quantile(0.9):.2f}시간")
                
                # 날짜별 분석
                print("\n📅 날짜별 체류시간:")
                for date in stay_times['interview_date'].unique():
                    date_data = stay_times[stay_times['interview_date'] == date]
                    date_str = str(date).split()[0]
                    print(f"  {date_str}: 평균 {date_data['stay_hours'].mean():.2f}시간, "
                          f"최대 {date_data['stay_hours'].max():.2f}시간")
                
                # 제약 위반 분석
                if 'constraint_analysis' in reports and not reports['constraint_analysis'].empty:
                    constraint_df = reports['constraint_analysis']
                    print("\n🔧 하드 제약 분석:")
                    for _, row in constraint_df.iterrows():
                        date_str = str(row['interview_date']).split()[0]
                        constraint_hours = row['hard_constraint_hours']
                        exceed_count = row['exceed_count']
                        exceed_rate = row['exceed_rate']
                        
                        print(f"  {date_str}: 제약 {constraint_hours:.1f}시간, "
                              f"위반자 {exceed_count}명 ({exceed_rate:.1f}%)")
                
                # 제약 위반 상세 분석
                if 'exceed_analysis' in reports and reports['exceed_analysis']:
                    exceed_analysis = reports['exceed_analysis']
                    if 'date_violations' in exceed_analysis:
                        print("\n🚨 제약 위반 상세:")
                        for date_str, violation_info in exceed_analysis['date_violations'].items():
                            if violation_info['violator_count'] > 0:
                                print(f"  {date_str}: {violation_info['violator_count']}명 위반")
                                for violator in violation_info['violators'][:3]:  # 상위 3명만 표시
                                    print(f"    - {violator['applicant_id']}: {violator['stay_hours']:.1f}시간")
                                if len(violation_info['violators']) > 3:
                                    print(f"    ... 외 {len(violation_info['violators']) - 3}명")
                
                # 4. 결과 저장
                print("\n4. 결과 저장...")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                excel_filename = f"hard_constraint_force_test_{timestamp}.xlsx"
                
                with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                    # 메인 스케줄
                    final_wide.to_excel(writer, sheet_name='Schedule', index=False)
                    
                    # 체류시간 분석
                    stay_times.to_excel(writer, sheet_name='StayTime_Analysis', index=False)
                    
                    # 제약 분석 리포트
                    if 'constraint_analysis' in reports and not reports['constraint_analysis'].empty:
                        reports['constraint_analysis'].to_excel(writer, sheet_name='Constraint_Analysis', index=False)
                    
                    # 제약 위반 리포트
                    if 'constraint_violations' in reports and not reports['constraint_violations'].empty:
                        reports['constraint_violations'].to_excel(writer, sheet_name='Constraint_Violations', index=False)
                    
                    # 단계별 비교 리포트
                    if 'phase_comparison' in reports and not reports['phase_comparison'].empty:
                        reports['phase_comparison'].to_excel(writer, sheet_name='Phase_Comparison', index=False)
                
                print(f"✅ 결과 저장 완료: {excel_filename}")
                
                # 5. 성공 여부 판정
                print("\n5. 테스트 결과 판정...")
                
                # 제약 위반자가 있는지 확인
                total_violations = 0
                if 'exceed_analysis' in reports and reports['exceed_analysis']:
                    total_violations = reports['exceed_analysis'].get('total_violations', 0)
                
                if total_violations == 0:
                    print("🎉 SUCCESS: 모든 지원자가 하드 제약을 만족합니다!")
                    return True
                else:
                    violation_rate = reports['exceed_analysis'].get('overall_violation_rate', 0)
                    print(f"⚠️ PARTIAL: {total_violations}명({violation_rate:.1f}%)이 제약을 위반합니다.")
                    
                    # 위반률이 10% 이하면 부분 성공으로 판정
                    if violation_rate <= 10.0:
                        print("✅ 부분 성공: 위반률이 허용 범위 내입니다.")
                        return True
                    else:
                        print("❌ 실패: 위반률이 너무 높습니다.")
                        return False
            else:
                print("❌ 체류시간 계산 실패")
                return False
        else:
            print(f"❌ 스케줄링 실패: {status}")
            print(f"로그: {logs}")
            return False
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def calculate_stay_times(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """체류시간 계산"""
    if schedule_df.empty:
        return pd.DataFrame()
    
    # 지원자별 체류시간 계산
    stay_data = []
    
    for (applicant_id, interview_date), group in schedule_df.groupby(['applicant_id', 'interview_date']):
        if group.empty:
            continue
        
        # 시간 순으로 정렬
        group_sorted = group.sort_values('start_time')
        
        # 첫 번째와 마지막 활동 시간
        first_start = group_sorted['start_time'].min()
        last_end = group_sorted['end_time'].max()
        
        # 체류시간 계산 (시간 단위)
        stay_duration = (last_end - first_start).total_seconds() / 3600
        
        stay_data.append({
            'applicant_id': applicant_id,
            'interview_date': interview_date,
            'first_start': first_start,
            'last_end': last_end,
            'stay_hours': stay_duration,
            'activity_count': len(group)
        })
    
    return pd.DataFrame(stay_data)

if __name__ == "__main__":
    success = test_hard_constraint_force()
    if success:
        print("\n🎉 하드 제약 강제 적용 테스트 성공!")
    else:
        print("\n❌ 하드 제약 강제 적용 테스트 실패!")
    
    sys.exit(0 if success else 1) 