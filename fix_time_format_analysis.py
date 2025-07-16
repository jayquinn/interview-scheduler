#!/usr/bin/env python3
"""
시간 형식 통일 분석
"""

import pandas as pd
import numpy as np

def fix_time_format_analysis():
    """시간 형식 통일 분석"""
    
    print("=== 시간 형식 통일 분석 ===")
    
    filename = "interview_schedule_20250716_145718.xlsx"
    
    # 3단계 스케줄링 결과 읽기
    df_schedule = pd.read_excel(filename, sheet_name='3단계_스케줄링_결과')
    df_schedule['interview_date'] = pd.to_datetime(df_schedule['interview_date'])
    
    print(f"3단계 스케줄링 결과: {len(df_schedule)}개")
    
    # 시간 형식 변환
    print("\n=== 시간 형식 변환 ===")
    
    # Timedelta를 시간 형식으로 변환
    df_schedule['start_time_str'] = df_schedule['start_time'].apply(
        lambda x: str(x).split()[-1][:5] if pd.notna(x) else None
    )
    df_schedule['end_time_str'] = df_schedule['end_time'].apply(
        lambda x: str(x).split()[-1][:5] if pd.notna(x) else None
    )
    
    print("변환된 시간 형식:")
    print(df_schedule[['applicant_id', 'activity_name', 'start_time_str', 'end_time_str']].head(10))
    
    # JOB02_005 응시자 상세 분석
    print("\n=== JOB02_005 응시자 상세 분석 ===")
    job02_005_schedule = df_schedule[df_schedule['applicant_id'] == 'JOB02_005']
    
    if not job02_005_schedule.empty:
        print("JOB02_005 스케줄 (변환된 형식):")
        for i, row in job02_005_schedule.iterrows():
            print(f"  - {row['activity_name']}: {row['start_time_str']} ~ {row['end_time_str']} ({row['room_name']})")
        
        # 체류시간 계산
        start_times = job02_005_schedule['start_time_str'].tolist()
        end_times = job02_005_schedule['end_time_str'].tolist()
        
        overall_start = min(start_times)
        overall_end = max(end_times)
        
        print(f"\n전체 체류시간: {overall_start} ~ {overall_end}")
        
        # 시간 차이 계산
        start_dt = pd.to_datetime(f"2000-01-01 {overall_start}")
        end_dt = pd.to_datetime(f"2000-01-01 {overall_end}")
        stay_hours = (end_dt - start_dt).total_seconds() / 3600
        
        print(f"계산된 체류시간: {stay_hours:.2f}시간")
    
    # Individual_StayTime과 비교
    print("\n=== Individual_StayTime과 비교 ===")
    try:
        df_individual = pd.read_excel(filename, sheet_name='Individual_StayTime')
        
        # JOB02_005 찾기
        job02_005_individual = df_individual[df_individual['지원자ID'] == 'JOB02_005']
        
        if not job02_005_individual.empty:
            print("JOB02_005 Individual_StayTime:")
            for i, row in job02_005_individual.iterrows():
                print(f"  - 시작: {row['시작시간']}, 종료: {row['종료시간']}, 체류: {row['체류시간(시간)']}시간")
            
            # 일치성 확인 (변환된 형식으로)
            individual_start = str(job02_005_individual['시작시간'].iloc[0])
            individual_end = str(job02_005_individual['종료시간'].iloc[0])
            
            print(f"\n일치성 확인 (변환된 형식):")
            print(f"  - 스케줄: {overall_start} ~ {overall_end}")
            print(f"  - Individual: {individual_start} ~ {individual_end}")
            
            if overall_start == individual_start and overall_end == individual_end:
                print(f"  ✅ 시간 일치")
            else:
                print(f"  ❌ 시간 불일치")
                
                # 차이점 분석
                print(f"\n차이점 분석:")
                print(f"  - 시작시간: 스케줄={overall_start}, Individual={individual_start}")
                print(f"  - 종료시간: 스케줄={overall_end}, Individual={individual_end}")
        
    except Exception as e:
        print(f"Individual_StayTime 비교 오류: {e}")
    
    # 전체 응시자 체류시간 분석
    print("\n=== 전체 응시자 체류시간 분석 ===")
    
    stay_times = []
    for applicant_id in df_schedule['applicant_id'].unique():
        applicant_df = df_schedule[df_schedule['applicant_id'] == applicant_id]
        start_times = applicant_df['start_time_str'].tolist()
        end_times = applicant_df['end_time_str'].tolist()
        
        overall_start = min(start_times)
        overall_end = max(end_times)
        
        start_dt = pd.to_datetime(f"2000-01-01 {overall_start}")
        end_dt = pd.to_datetime(f"2000-01-01 {overall_end}")
        stay_hours = (end_dt - start_dt).total_seconds() / 3600
        
        stay_times.append({
            'applicant_id': applicant_id,
            'start_time': overall_start,
            'end_time': overall_end,
            'stay_hours': stay_hours
        })
    
    # 체류시간 순으로 정렬
    stay_times.sort(key=lambda x: x['stay_hours'], reverse=True)
    
    print("상위 10개 체류시간:")
    for i, stay in enumerate(stay_times[:10]):
        print(f"  {i+1}. {stay['applicant_id']}: {stay['start_time']} ~ {stay['end_time']} ({stay['stay_hours']:.2f}시간)")
    
    # 5분 단위 확인
    print("\n=== 5분 단위 확인 ===")
    non_5min_count = 0
    for stay in stay_times[:20]:  # 상위 20개만 확인
        start_minutes = int(stay['start_time'].split(':')[1])
        end_minutes = int(stay['end_time'].split(':')[1])
        
        if start_minutes % 5 != 0 or end_minutes % 5 != 0:
            non_5min_count += 1
            print(f"  ⚠️ {stay['applicant_id']}: {stay['start_time']} ~ {stay['end_time']} (5분 단위 아님)")
    
    if non_5min_count == 0:
        print("  ✅ 모든 시간이 5분 단위로 정확히 맞춰짐")
    else:
        print(f"  ❌ {non_5min_count}개 응시자가 5분 단위가 아님")

if __name__ == "__main__":
    fix_time_format_analysis() 