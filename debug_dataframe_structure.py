#!/usr/bin/env python3
"""
DataFrame 구조 확인 및 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, date
import pandas as pd
from solver.api import solve_for_days_v2
from test_app_default_data import create_app_default_data
import core

def debug_dataframe_structure():
    """DataFrame 구조 확인"""
    print("🔍 DataFrame 구조 확인 및 테스트")
    print("="*50)
    
    # 기본 데이터 생성
    session_state = create_app_default_data()
    
    # 현재 날짜 기준으로 1일 계획
    today = datetime.now().date()
    dates = [today]
    
    # 멀티데이트 플랜 생성
    multidate_plans = {}
    date_str = today.strftime("%Y-%m-%d")
    multidate_plans[date_str] = {
        "date": today,
        "enabled": True,
        "jobs": [
            {"code": "JOB01", "count": 12},
            {"code": "JOB02", "count": 8},
        ]
    }
    
    session_state['multidate_plans'] = multidate_plans
    session_state['interview_dates'] = dates
    
    # Config 빌드
    cfg = core.build_config(session_state)
    
    # 테스트 실행
    params = {'enable_level4': True}
    status, result_df, logs, limit = solve_for_days_v2(cfg, params, debug=True)
    
    print(f"\n✅ 스케줄링 결과:")
    print(f"Status: {status}")
    print(f"DataFrame 타입: {type(result_df)}")
    print(f"DataFrame 크기: {result_df.shape if result_df is not None else 'None'}")
    
    if result_df is not None and not result_df.empty:
        print(f"\n📊 DataFrame 구조:")
        print(f"컬럼 목록: {list(result_df.columns)}")
        print(f"첫 5행:\n{result_df.head()}")
        
        # 체류시간 분석 시도
        print(f"\n🔍 체류시간 분석 시도:")
        try:
            stay_times = analyze_stay_times_corrected(result_df)
            print(f"분석 결과: {stay_times}")
        except Exception as e:
            print(f"분석 오류: {e}")
    
    return result_df

def analyze_stay_times_corrected(schedule_df):
    """수정된 체류시간 분석"""
    if schedule_df.empty:
        return {'average': 0, 'max': 0, 'min': 0, 'count': 0}
    
    print(f"컬럼 목록: {list(schedule_df.columns)}")
    
    # 'id' 컬럼이 없다면 다른 식별자 컬럼을 찾아보자
    possible_id_cols = [col for col in schedule_df.columns if 'id' in col.lower()]
    print(f"가능한 ID 컬럼: {possible_id_cols}")
    
    # 샘플 데이터 출력
    print(f"첫 번째 행:\n{schedule_df.iloc[0] if len(schedule_df) > 0 else 'No data'}")
    
    # 실제 컬럼에 따라 분석
    if 'applicant_id' in schedule_df.columns:
        id_col = 'applicant_id'
    elif 'ID' in schedule_df.columns:
        id_col = 'ID'
    elif len(schedule_df.columns) > 0:
        id_col = schedule_df.columns[0]  # 첫 번째 컬럼을 ID로 가정
    else:
        return {'average': 0, 'max': 0, 'min': 0, 'count': 0}
    
    print(f"사용할 ID 컬럼: {id_col}")
    
    stay_times = []
    
    for applicant_id in schedule_df[id_col].unique():
        applicant_data = schedule_df[schedule_df[id_col] == applicant_id]
        
        if not applicant_data.empty:
            # 시간 관련 컬럼 찾기
            time_cols = [col for col in schedule_df.columns if 'time' in col.lower() or 'start' in col.lower() or 'end' in col.lower()]
            print(f"시간 컬럼: {time_cols}")
            
            all_times = []
            for _, row in applicant_data.iterrows():
                for col in time_cols:
                    if pd.notna(row[col]):
                        try:
                            all_times.append(pd.to_datetime(row[col]))
                        except:
                            pass
            
            if all_times:
                min_time = min(all_times)
                max_time = max(all_times)
                stay_hours = (max_time - min_time).total_seconds() / 3600
                stay_times.append(stay_hours)
                print(f"{applicant_id}: {stay_hours:.1f}h")
    
    if stay_times:
        return {
            'average': sum(stay_times) / len(stay_times),
            'max': max(stay_times),
            'min': min(stay_times),
            'count': len(stay_times)
        }
    else:
        return {'average': 0, 'max': 0, 'min': 0, 'count': 0}

if __name__ == "__main__":
    try:
        result_df = debug_dataframe_structure()
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc() 