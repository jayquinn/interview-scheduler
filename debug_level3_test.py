#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계 스케줄링 디버깅 테스트
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_internal_analysis import run_multi_date_scheduling

def debug_level3_scheduling():
    """3단계 스케줄링 디버깅"""
    print("=== 3단계 스케줄링 디버깅 시작 ===")
    
    # 3단계 스케줄링 실행
    results = run_multi_date_scheduling()
    
    if not results:
        print("❌ 3단계 스케줄링 실패")
        return
    
    print(f"✅ 3단계 스케줄링 성공")
    print(f"  1단계 상태: {results['phase1']['status']}")
    print(f"  2단계 상태: {results['phase2']['status']}")
    print(f"  3단계 상태: {results['phase3']['status']}")
    
    # 각 단계별 최대 체류시간 계산
    def calculate_max_stay_time(df):
        if df is None or df.empty:
            return 0
        df_temp = df.copy()
        df_temp['interview_date'] = pd.to_datetime(df_temp['interview_date'])
        max_stay = 0
        for date_str in df_temp['interview_date'].dt.strftime('%Y-%m-%d').unique():
            date_df = df_temp[df_temp['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
            for applicant_id in date_df['applicant_id'].unique():
                applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                start_time = applicant_df['start_time'].min()
                end_time = applicant_df['end_time'].max()
                stay_hours = (end_time - start_time).total_seconds() / 3600
                max_stay = max(max_stay, stay_hours)
        return max_stay
    
    # 각 단계별 결과 확인
    if results['phase1']['df'] is not None:
        phase1_max = calculate_max_stay_time(results['phase1']['df'])
        print(f"  1단계 최대 체류시간: {phase1_max:.2f}시간")
    
    if results['phase2']['df'] is not None:
        phase2_max = calculate_max_stay_time(results['phase2']['df'])
        print(f"  2단계 최대 체류시간: {phase2_max:.2f}시간")
    
    if results['phase3']['df'] is not None:
        phase3_max = calculate_max_stay_time(results['phase3']['df'])
        print(f"  3단계 최대 체류시간: {phase3_max:.2f}시간")
        
        # 3단계 결과에서 실제 체류시간 분포 확인
        print(f"\n=== 3단계 결과 상세 분석 ===")
        df3 = results['phase3']['df']
        df3['interview_date'] = pd.to_datetime(df3['interview_date'])
        
        for date_str in df3['interview_date'].dt.strftime('%Y-%m-%d').unique():
            date_df = df3[df3['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
            print(f"\n📅 {date_str}:")
            
            # 해당 날짜의 응시자별 체류시간 계산
            stay_times = []
            for applicant_id in date_df['applicant_id'].unique():
                applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                start_time = applicant_df['start_time'].min()
                end_time = applicant_df['end_time'].max()
                stay_hours = (end_time - start_time).total_seconds() / 3600
                stay_times.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
            
            if stay_times:
                # 상위 5개 체류시간 출력
                stay_times.sort(key=lambda x: x['stay_hours'], reverse=True)
                print(f"  상위 5개 체류시간:")
                for i, stay in enumerate(stay_times[:5]):
                    print(f"    {i+1}. {stay['applicant_id']}: {stay['stay_hours']:.2f}시간")
                
                max_stay = max(stay_times, key=lambda x: x['stay_hours'])
                print(f"  최대 체류시간: {max_stay['applicant_id']} ({max_stay['stay_hours']:.2f}시간)")
    
    return results

if __name__ == "__main__":
    debug_level3_scheduling() 