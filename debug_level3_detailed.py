#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계 스케줄링 상세 디버깅
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_internal_analysis import run_multi_date_scheduling

def debug_level3_detailed():
    """3단계 스케줄링 상세 디버깅"""
    print("=== 3단계 스케줄링 상세 디버깅 시작 ===")
    
    # 3단계 스케줄링 실행
    results = run_multi_date_scheduling()
    
    if not results:
        print("❌ 3단계 스케줄링 실패")
        return
    
    print(f"✅ 3단계 스케줄링 성공")
    
    # 각 단계별 결과 상세 분석
    for phase in ['phase1', 'phase2', 'phase3']:
        print(f"\n=== {phase.upper()} 상세 분석 ===")
        phase_data = results[phase]
        
        if phase_data['df'] is not None and not phase_data['df'].empty:
            df = phase_data['df']
            df['interview_date'] = pd.to_datetime(df['interview_date'])
            
            # 날짜별 최대 체류시간 분석
            for date_str in df['interview_date'].dt.strftime('%Y-%m-%d').unique():
                date_df = df[df['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
                print(f"\n📅 {date_str}:")
                
                # 해당 날짜의 응시자별 체류시간 계산
                stay_times = []
                for applicant_id in date_df['applicant_id'].unique():
                    applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    stay_times.append({
                        'applicant_id': applicant_id,
                        'stay_hours': stay_hours,
                        'start_time': start_time,
                        'end_time': end_time
                    })
                
                if stay_times:
                    # 상위 10개 체류시간 출력
                    stay_times.sort(key=lambda x: x['stay_hours'], reverse=True)
                    print(f"  상위 10개 체류시간:")
                    for i, stay in enumerate(stay_times[:10]):
                        start_str = stay['start_time'].strftime('%H:%M') if hasattr(stay['start_time'], 'strftime') else str(stay['start_time'])
                        end_str = stay['end_time'].strftime('%H:%M') if hasattr(stay['end_time'], 'strftime') else str(stay['end_time'])
                        print(f"    {i+1}. {stay['applicant_id']}: {stay['stay_hours']:.2f}시간 ({start_str}~{end_str})")
                    
                    max_stay = max(stay_times, key=lambda x: x['stay_hours'])
                    print(f"  최대 체류시간: {max_stay['applicant_id']} ({max_stay['stay_hours']:.2f}시간)")
                    
                    # JOB02_005 특별 확인
                    job02_005_data = [s for s in stay_times if s['applicant_id'] == 'JOB02_005']
                    if job02_005_data:
                        job02_005 = job02_005_data[0]
                        start_str = job02_005['start_time'].strftime('%H:%M') if hasattr(job02_005['start_time'], 'strftime') else str(job02_005['start_time'])
                        end_str = job02_005['end_time'].strftime('%H:%M') if hasattr(job02_005['end_time'], 'strftime') else str(job02_005['end_time'])
                        print(f"  🔍 JOB02_005: {job02_005['stay_hours']:.2f}시간 ({start_str}~{end_str})")
        else:
            print(f"  {phase} 데이터가 없습니다.")
    
    # 3단계 결과에서 JOB02_005 특별 확인
    print(f"\n=== JOB02_005 특별 확인 ===")
    if results['phase3']['df'] is not None and not results['phase3']['df'].empty:
        df3 = results['phase3']['df']
        df3['interview_date'] = pd.to_datetime(df3['interview_date'])
        
        # 2025-07-16 날짜의 JOB02_005 찾기
        date_20250716 = df3[df3['interview_date'].dt.strftime('%Y-%m-%d') == '2025-07-16']
        job02_005_data = date_20250716[date_20250716['applicant_id'] == 'JOB02_005']
        
        if not job02_005_data.empty:
            print(f"JOB02_005 스케줄:")
            for _, row in job02_005_data.iterrows():
                start_time = row['start_time']
                end_time = row['end_time']
                stay_hours = (end_time - start_time).total_seconds() / 3600
                start_str = start_time.strftime('%H:%M') if hasattr(start_time, 'strftime') else str(start_time)
                end_str = end_time.strftime('%H:%M') if hasattr(end_time, 'strftime') else str(end_time)
                print(f"  {row['activity_name']}: {start_str}~{end_str} ({stay_hours:.2f}시간)")
            
            # 전체 체류시간 계산
            start_time = job02_005_data['start_time'].min()
            end_time = job02_005_data['end_time'].max()
            total_stay_hours = (end_time - start_time).total_seconds() / 3600
            start_str = start_time.strftime('%H:%M') if hasattr(start_time, 'strftime') else str(start_time)
            end_str = end_time.strftime('%H:%M') if hasattr(end_time, 'strftime') else str(end_time)
            print(f"  전체 체류시간: {start_str}~{end_str} ({total_stay_hours:.2f}시간)")
        else:
            print("JOB02_005를 찾을 수 없습니다.")
    else:
        print("3단계 데이터가 없습니다.")
    
    return results

if __name__ == "__main__":
    debug_level3_detailed() 