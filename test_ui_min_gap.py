#!/usr/bin/env python3
"""
UI 경로를 통한 min_gap_min 구조 테스트
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import os

def test_ui_min_gap():
    """UI 경로를 통한 min_gap_min 구조 테스트"""
    
    print("=== UI 경로를 통한 min_gap_min 구조 테스트 ===")
    
    # 1. 기본 설정 데이터 생성
    print("\n1. 기본 설정 데이터 생성...")
    
    # Activities 설정
    activities_data = {
        'activity': ['토론면접', '발표준비', '발표면접'],
        'duration_min': [30, 5, 15],
        'room_type': ['토론면접실', '발표준비실', '발표면접실'],
        'mode': ['batched', 'parallel', 'individual'],
        'min_cap': [4, 1, 1],
        'max_cap': [6, 2, 1],
        'use': [True, True, True]
    }
    activities_df = pd.DataFrame(activities_data)
    
    # Job-Activity 매핑
    job_acts_data = {
        'code': ['JOB01', 'JOB02'],
        'activity': ['토론면접', '토론면접'],
        'use': [True, True]
    }
    job_acts_df = pd.DataFrame(job_acts_data)
    
    # Room Plan
    room_plan_data = {
        'date': ['2025-07-01', '2025-07-01', '2025-07-01'],
        'loc': ['토론면접실A', '토론면접실B', '발표준비실A'],
        'room_type': ['토론면접실', '토론면접실', '발표준비실'],
        'capacity_max': [6, 6, 2]
    }
    room_plan_df = pd.DataFrame(room_plan_data)
    
    # Operating Window
    oper_window_data = {
        'date': ['2025-07-01'],
        'code': ['JOB01'],
        'start_time': ['09:00'],
        'end_time': ['17:30']
    }
    oper_window_df = pd.DataFrame(oper_window_data)
    
    # Precedence
    precedence_data = {
        'predecessor': ['발표준비'],
        'successor': ['발표면접'],
        'gap_min': [0],
        'adjacent': [True]
    }
    precedence_df = pd.DataFrame(precedence_data)
    
    # Candidates
    candidates_data = []
    for i in range(1, 24):  # JOB01: 23명
        candidates_data.append({
            'id': f'JOB01_{str(i).zfill(3)}',
            'interview_date': '2025-07-01',
            'code': 'JOB01'
        })
    for i in range(1, 24):  # JOB02: 23명
        candidates_data.append({
            'id': f'JOB02_{str(i).zfill(3)}',
            'interview_date': '2025-07-01',
            'code': 'JOB02'
        })
    candidates_df = pd.DataFrame(candidates_data)
    
    # Job counts (UI에서 필요한 형식)
    job_counts_data = {
        'code': ['JOB01', 'JOB02'],
        'count': [23, 23]
    }
    job_counts_df = pd.DataFrame(job_counts_data)
    
    print(f"✅ 기본 설정 데이터 생성 완료")
    print(f"  - Activities: {len(activities_df)}개")
    print(f"  - Job-Activity: {len(job_acts_df)}개")
    print(f"  - Room Plan: {len(room_plan_df)}개")
    print(f"  - Operating Window: {len(oper_window_df)}개")
    print(f"  - Precedence: {len(precedence_df)}개")
    print(f"  - Candidates: {len(candidates_df)}명")
    
    # 2. UI 설정 시뮬레이션
    print("\n2. UI 설정 시뮬레이션...")
    
    # session_state 설정 (UI에서 사용하는 설정들)
    st.session_state.activities = activities_df
    st.session_state.job_acts_map = job_acts_df
    st.session_state.room_plan = room_plan_df
    st.session_state.oper_window = oper_window_df
    st.session_state.precedence = precedence_df
    st.session_state.candidates_exp = candidates_df
    st.session_state.job_counts = job_counts_df
    st.session_state.global_gap_min = 5  # min_gap_min 설정
    
    print("✅ UI 설정 시뮬레이션 완료")
    
    # 3. 스케줄링 실행
    print("\n3. UI 경로를 통한 스케줄링 실행...")
    
    try:
        # app.py의 스케줄링 로직 직접 호출
        from solver.api import solve_for_days_v2
        
        # UI 설정을 solver 형식으로 변환
        cfg_ui = {
            'activities': activities_df,
            'job_acts_map': job_acts_df,
            'room_plan': room_plan_df,
            'oper_window': oper_window_df,
            'precedence': precedence_df,
            'candidates_exp': candidates_df,
            'job_counts': job_counts_df,
            'global_gap_min': 5
        }
        
        # 스케줄링 파라미터
        params = {
            'min_gap_min': 5,  # min_gap_min 구조 적용
            'max_stay_hours': 8,
            'time_limit_sec': 120.0
        }
        
        print("🚀 스케줄링 시작...")
        start_time = time.time()
        
        status, result_df, logs, daily_limit = solve_for_days_v2(
            cfg_ui, params, debug=True
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"✅ 스케줄링 완료 (소요시간: {execution_time:.1f}초)")
        print(f"  - Status: {status}")
        print(f"  - 결과 행 수: {len(result_df) if result_df is not None else 0}")
        print(f"  - Daily Limit: {daily_limit}")
        
        if status == "SUCCESS" and result_df is not None:
            # 4. 결과 분석
            print("\n4. min_gap_min 구조 적용 결과 분석...")
            
            # 결과를 엑셀로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_filename = f"ui_min_gap_test_{timestamp}.xlsx"
            
            with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                result_df.to_excel(writer, sheet_name='Schedule_Result', index=False)
            
            print(f"✅ 결과 저장: {excel_filename}")
            
            # 시간 컬럼 분석
            time_cols = [col for col in result_df.columns if 'start_' in col or 'end_' in col]
            print(f"시간 관련 컬럼: {time_cols}")
            
            # 각 시간 컬럼의 5분 단위 여부 확인
            for col in time_cols:
                if col in result_df.columns and not result_df[col].isna().all():
                    # 시간 문자열을 datetime으로 변환
                    result_df[col] = pd.to_datetime(result_df[col], errors='coerce')
                    result_df[f'{col}_minutes'] = result_df[col].dt.minute
                    non_5min_col = result_df[result_df[f'{col}_minutes'] % 5 != 0]
                    
                    print(f"\n🔍 {col} 컬럼 5분 단위 여부:")
                    print(f"5분 단위가 아닌 값: {len(non_5min_col)}개")
                    
                    if len(non_5min_col) > 0:
                        print(f"⚠️ 5분 단위가 아닌 케이스들:")
                        print(non_5min_col[['id', col, f'{col}_minutes']].head(5))
                    else:
                        print(f"✅ {col} 컬럼이 5분 단위로 정확히 조정됨!")
            
            # 체류시간 분석
            print(f"\n📊 체류시간 분석:")
            stay_times = []
            for _, row in result_df.iterrows():
                start_times = []
                end_times = []
                
                for col in time_cols:
                    if 'start_' in col and pd.notna(row[col]):
                        start_times.append(row[col])
                    elif 'end_' in col and pd.notna(row[col]):
                        end_times.append(row[col])
                
                if start_times and end_times:
                    min_start = min(start_times)
                    max_end = max(end_times)
                    stay_hours = (max_end - min_start).total_seconds() / 3600
                    stay_times.append(stay_hours)
            
            if stay_times:
                print(f"  - 평균 체류시간: {sum(stay_times)/len(stay_times):.1f}시간")
                print(f"  - 최대 체류시간: {max(stay_times):.1f}시간")
                print(f"  - 최소 체류시간: {min(stay_times):.1f}시간")
            
            print(f"\n🎉 UI 경로를 통한 min_gap_min 구조 테스트 성공!")
            
        else:
            print(f"❌ 스케줄링 실패: {status}")
            print(f"로그: {logs}")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ui_min_gap() 