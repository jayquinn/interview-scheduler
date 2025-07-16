#!/usr/bin/env python3
"""
min_gap_min 구조 적용 결과 분석
"""

import pandas as pd
from datetime import datetime, timedelta

def analyze_min_gap_result():
    """min_gap_min 구조 적용 결과 분석"""
    
    print("=== min_gap_min 구조 적용 결과 분석 ===")
    
    # Sheet1 시트 분석
    try:
        df = pd.read_excel('ui_defaults_test_result.xlsx', sheet_name='Sheet1')
        print(f"\n📊 Individual_StayTime 시트 분석:")
        print(f"총 {len(df)}개 행")
        
        # 종료시간 5분 단위 여부 확인
        df['end_time'] = pd.to_datetime(df['end_time'])
        df['end_minutes'] = df['end_time'].dt.minute
        non_5min = df[df['end_minutes'] % 5 != 0]
        
        print(f"\n🔍 종료시간 5분 단위 여부:")
        print(f"5분 단위가 아닌 종료시간: {len(non_5min)}개")
        
        if len(non_5min) > 0:
            print(f"\n⚠️ 5분 단위가 아닌 케이스들:")
            print(non_5min[['applicant_id', 'activity_name', 'end_time', 'end_minutes']].head(10))
            
            # duration 계산
            df['start_time'] = pd.to_datetime(df['start_time'])
            df['duration_minutes'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 60
            
            non_5min_with_duration = non_5min.merge(
                df[['applicant_id', 'activity_name', 'duration_minutes']], 
                on=['applicant_id', 'activity_name']
            )
            
            print(f"\n📏 5분 단위가 아닌 케이스의 duration 분포:")
            duration_counts = non_5min_with_duration['duration_minutes'].value_counts()
            print(duration_counts)
        else:
            print("✅ 모든 종료시간이 5분 단위로 정확히 조정됨!")
        
        # 시작시간 5분 단위 여부 확인
        df['start_minutes'] = df['start_time'].dt.minute
        non_5min_start = df[df['start_minutes'] % 5 != 0]
        
        print(f"\n🔍 시작시간 5분 단위 여부:")
        print(f"5분 단위가 아닌 시작시간: {len(non_5min_start)}개")
        
        if len(non_5min_start) > 0:
            print(f"\n⚠️ 5분 단위가 아닌 시작시간 케이스들:")
            print(non_5min_start[['applicant_id', 'activity_name', 'start_time', 'start_minutes']].head(10))
        else:
            print("✅ 모든 시작시간이 5분 단위로 정확히 조정됨!")
            
    except Exception as e:
        print(f"❌ Individual_StayTime 시트 분석 오류: {e}")
    
    # TS_날짜 시트 분석 (Sheet1에서 필터링)
    try:
        ts_df = df.copy()  # Sheet1 데이터 재사용
        print(f"\n📊 TS_2025-07-01 시트 분석:")
        print(f"총 {len(ts_df)}개 행")
        
        # 시간 컬럼 찾기
        time_cols = [col for col in ts_df.columns if 'start_' in col or 'end_' in col]
        print(f"시간 관련 컬럼: {time_cols}")
        
        # 각 시간 컬럼의 5분 단위 여부 확인
        for col in time_cols:
            if col in ts_df.columns and not ts_df[col].isna().all():
                ts_df[col] = pd.to_datetime(ts_df[col], errors='coerce')
                ts_df[f'{col}_minutes'] = ts_df[col].dt.minute
                non_5min_col = ts_df[ts_df[f'{col}_minutes'] % 5 != 0]
                
                print(f"\n🔍 {col} 컬럼 5분 단위 여부:")
                print(f"5분 단위가 아닌 값: {len(non_5min_col)}개")
                
                if len(non_5min_col) > 0:
                    print(f"⚠️ 5분 단위가 아닌 케이스들:")
                    print(non_5min_col[['id', col, f'{col}_minutes']].head(5))
                else:
                    print(f"✅ {col} 컬럼이 5분 단위로 정확히 조정됨!")
                    
    except Exception as e:
        print(f"❌ TS_2025-07-01 시트 분석 오류: {e}")

if __name__ == "__main__":
    analyze_min_gap_result() 