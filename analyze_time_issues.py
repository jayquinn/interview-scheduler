#!/usr/bin/env python3
"""
엑셀 파일 시간대 문제 분석
"""

import pandas as pd
import numpy as np

def analyze_time_issues():
    """시간대 문제 분석"""
    
    print("=== 엑셀 파일 시간대 문제 분석 ===")
    
    filename = "interview_schedule_20250716_145718.xlsx"
    
    # 1. Individual_StayTime 시트 분석
    print("\n=== 1. Individual_StayTime 시트 분석 ===")
    try:
        df_individual = pd.read_excel(filename, sheet_name='Individual_StayTime')
        print(f"행 수: {len(df_individual)}")
        print(f"컬럼: {list(df_individual.columns)}")
        
        # 시작시간, 종료시간 분석
        if '시작시간' in df_individual.columns and '종료시간' in df_individual.columns:
            print("\n시작시간 분석:")
            start_times = df_individual['시작시간'].dropna()
            print(f"  - 최소: {start_times.min()}")
            print(f"  - 최대: {start_times.max()}")
            
            # 5분 단위 확인
            print("\n5분 단위 확인:")
            for time in start_times.head(10):
                minutes = time.minute if hasattr(time, 'minute') else pd.to_datetime(time).minute
                if minutes % 5 != 0:
                    print(f"  ⚠️ 5분 단위 아님: {time} (분: {minutes})")
                else:
                    print(f"  ✅ 5분 단위: {time} (분: {minutes})")
            
            print("\n종료시간 분석:")
            end_times = df_individual['종료시간'].dropna()
            print(f"  - 최소: {end_times.min()}")
            print(f"  - 최대: {end_times.max()}")
            
            # 5분 단위 확인
            print("\n5분 단위 확인:")
            for time in end_times.head(10):
                minutes = time.minute if hasattr(time, 'minute') else pd.to_datetime(time).minute
                if minutes % 5 != 0:
                    print(f"  ⚠️ 5분 단위 아님: {time} (분: {minutes})")
                else:
                    print(f"  ✅ 5분 단위: {time} (분: {minutes})")
        
    except Exception as e:
        print(f"Individual_StayTime 분석 오류: {e}")
    
    # 2. TS_날짜 시트 분석
    print("\n=== 2. TS_날짜 시트 분석 ===")
    ts_sheets = ['TS_0716', 'TS_0717', 'TS_0718', 'TS_0719']
    
    for sheet_name in ts_sheets:
        try:
            df_ts = pd.read_excel(filename, sheet_name=sheet_name)
            print(f"\n{sheet_name}:")
            print(f"  - 행 수: {len(df_ts)}")
            print(f"  - 컬럼: {list(df_ts.columns)}")
            
            # Time 컬럼 분석
            if 'Time' in df_ts.columns:
                times = df_ts['Time'].dropna()
                print(f"  - 시간 범위: {times.min()} ~ {times.max()}")
                
                # 5분 단위 확인
                print(f"  - 5분 단위 확인:")
                for time in times.head(5):
                    minutes = time.minute if hasattr(time, 'minute') else pd.to_datetime(time).minute
                    if minutes % 5 != 0:
                        print(f"    ⚠️ 5분 단위 아님: {time} (분: {minutes})")
                    else:
                        print(f"    ✅ 5분 단위: {time} (분: {minutes})")
        
        except Exception as e:
            print(f"{sheet_name} 분석 오류: {e}")
    
    # 3. 3단계 스케줄링 결과와 비교
    print("\n=== 3. 3단계 스케줄링 결과와 비교 ===")
    try:
        df_schedule = pd.read_excel(filename, sheet_name='3단계_스케줄링_결과')
        df_schedule['interview_date'] = pd.to_datetime(df_schedule['interview_date'])
        
        print(f"3단계 스케줄링 결과:")
        print(f"  - 행 수: {len(df_schedule)}")
        print(f"  - 컬럼: {list(df_schedule.columns)}")
        
        # 시작시간, 종료시간 분석
        if 'start_time' in df_schedule.columns and 'end_time' in df_schedule.columns:
            start_times = df_schedule['start_time'].dropna()
            end_times = df_schedule['end_time'].dropna()
            
            print(f"\n시작시간 분석:")
            print(f"  - 최소: {start_times.min()}")
            print(f"  - 최대: {start_times.max()}")
            
            print(f"\n종료시간 분석:")
            print(f"  - 최소: {end_times.min()}")
            print(f"  - 최대: {end_times.max()}")
            
            # 5분 단위 확인
            print(f"\n5분 단위 확인 (시작시간):")
            for time in start_times.head(5):
                minutes = time.minute if hasattr(time, 'minute') else pd.to_datetime(time).minute
                if minutes % 5 != 0:
                    print(f"  ⚠️ 5분 단위 아님: {time} (분: {minutes})")
                else:
                    print(f"  ✅ 5분 단위: {time} (분: {minutes})")
            
            print(f"\n5분 단위 확인 (종료시간):")
            for time in end_times.head(5):
                minutes = time.minute if hasattr(time, 'minute') else pd.to_datetime(time).minute
                if minutes % 5 != 0:
                    print(f"  ⚠️ 5분 단위 아님: {time} (분: {minutes})")
                else:
                    print(f"  ✅ 5분 단위: {time} (분: {minutes})")
        
    except Exception as e:
        print(f"3단계 스케줄링 결과 분석 오류: {e}")
    
    # 4. 일치성 검증
    print("\n=== 4. 일치성 검증 ===")
    try:
        # JOB02_005 응시자로 테스트
        job02_005_schedule = df_schedule[df_schedule['applicant_id'] == 'JOB02_005']
        
        if not job02_005_schedule.empty:
            print(f"JOB02_005 스케줄:")
            for i, row in job02_005_schedule.iterrows():
                print(f"  - {row['activity_name']}: {row['start_time']} ~ {row['end_time']} ({row['room_name']})")
            
            # Individual_StayTime에서 JOB02_005 찾기
            if '지원자ID' in df_individual.columns:
                job02_005_individual = df_individual[df_individual['지원자ID'] == 'JOB02_005']
                
                if not job02_005_individual.empty:
                    print(f"\nJOB02_005 Individual_StayTime:")
                    for i, row in job02_005_individual.iterrows():
                        print(f"  - 시작: {row['시작시간']}, 종료: {row['종료시간']}, 체류: {row['체류시간(시간)']}시간")
                    
                    # 일치성 확인
                    schedule_start = job02_005_schedule['start_time'].min()
                    schedule_end = job02_005_schedule['end_time'].max()
                    individual_start = job02_005_individual['시작시간'].iloc[0]
                    individual_end = job02_005_individual['종료시간'].iloc[0]
                    
                    print(f"\n일치성 확인:")
                    print(f"  - 스케줄: {schedule_start} ~ {schedule_end}")
                    print(f"  - Individual: {individual_start} ~ {individual_end}")
                    
                    if schedule_start == individual_start and schedule_end == individual_end:
                        print(f"  ✅ 시간 일치")
                    else:
                        print(f"  ❌ 시간 불일치")
        
    except Exception as e:
        print(f"일치성 검증 오류: {e}")

if __name__ == "__main__":
    analyze_time_issues() 