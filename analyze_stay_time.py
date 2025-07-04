#!/usr/bin/env python3
"""
실제 UI 디폴트 데이터의 체류시간 분석
저장된 스케줄 결과를 읽어서 체류시간 패턴을 분석합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback

def load_schedule_result():
    """저장된 스케줄 결과 로드"""
    try:
        df = pd.read_excel("complete_ui_defaults_test_result.xlsx")
        print(f"✅ 스케줄 결과 로드: {len(df)}개 항목")
        print(f"컬럼: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"❌ 파일 로드 실패: {e}")
        return None

def calculate_stay_duration_analysis(schedule_df):
    """체류시간 분석 (app.py의 기능을 개선)"""
    stats_data = []
    
    # 컬럼명 확인
    id_col = None
    for col in ['applicant_id', 'id', 'candidate_id']:
        if col in schedule_df.columns:
            id_col = col
            break
    
    job_col = None
    for col in ['job_code', 'code']:
        if col in schedule_df.columns:
            job_col = col
            break
    
    date_col = None
    for col in ['interview_date', 'date']:
        if col in schedule_df.columns:
            date_col = col
            break
    
    if not id_col:
        print(f"❌ ID 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(schedule_df.columns)}")
        return None, None
    
    print(f"✅ 분석 컬럼: ID={id_col}, JOB={job_col}, DATE={date_col}")
    
    # 시간 컬럼 찾기
    time_cols = [col for col in schedule_df.columns if 'time' in col.lower()]
    print(f"시간 관련 컬럼: {time_cols}")
    
    # 지원자별 체류시간 계산
    for candidate_id, candidate_data in schedule_df.groupby(id_col):
        if len(candidate_data) == 0:
            continue
            
        # 해당 지원자의 모든 시간 정보 수집
        all_times = []
        
                 for _, row in candidate_data.iterrows():
             # 모든 시간 컬럼에서 시간 정보 추출
             for col in time_cols:
                                  time_val = row.get(col)
                 if pd.notna(time_val) and time_val != '':
                     try:
                         # float 형태 시간 처리 (하루의 비율로 표현)
                         if isinstance(time_val, (float, int)):
                             # 0.375 = 9:00, 0.5 = 12:00 등
                             minutes = time_val * 24 * 60  # 하루 비율 → 분 단위
                             all_times.append(minutes)
                         # timedelta 처리
                         elif isinstance(time_val, pd.Timedelta):
                             # timedelta를 시간으로 변환 (초 단위 → 분 단위)
                             minutes = time_val.total_seconds() / 60
                             all_times.append(minutes)
                         elif isinstance(time_val, str) and 'days' in time_val:
                             # "0 days 09:00:00" 형태 처리
                             time_part = time_val.split(' ')[-1]  # "09:00:00"
                             time_obj = pd.to_datetime(time_part, format='%H:%M:%S')
                             minutes = time_obj.hour * 60 + time_obj.minute
                             all_times.append(minutes)
                         elif isinstance(time_val, str) and ':' in time_val:
                             # "09:00:00" 형태 처리
                             time_obj = pd.to_datetime(time_val, format='%H:%M:%S')
                             minutes = time_obj.hour * 60 + time_obj.minute
                             all_times.append(minutes)
                     except Exception as e:
                         continue
        
        if len(all_times) >= 2:  # 최소 시작/종료 시간이 있어야 함
            # 체류시간 = 최대 시간 - 최소 시간
            stay_duration_minutes = max(all_times) - min(all_times)
            
            # 메타 정보 추출
            job_code = candidate_data.iloc[0].get(job_col, 'Unknown') if job_col else 'Unknown'
            interview_date = candidate_data.iloc[0].get(date_col, 'Unknown') if date_col else 'Unknown'
            
            stats_data.append({
                'candidate_id': candidate_id,
                'job_code': job_code,
                'interview_date': interview_date,
                'stay_duration_minutes': stay_duration_minutes,
                'start_time_minutes': min(all_times),
                'end_time_minutes': max(all_times),
                'num_activities': len(candidate_data)
            })
    
    if not stats_data:
        print("❌ 체류시간을 계산할 수 있는 데이터가 없습니다.")
        return None, None
    
    stats_df = pd.DataFrame(stats_data)
    
    # 직무별 통계 계산
    job_stats = []
    for job_code, job_data in stats_df.groupby('job_code'):
        durations = job_data['stay_duration_minutes']
        job_stats.append({
            'job_code': job_code,
            'count': len(job_data),
            'min_duration': durations.min(),
            'max_duration': durations.max(),
            'avg_duration': durations.mean(),
            'median_duration': durations.median(),
            'std_duration': durations.std()
        })
    
    job_stats_df = pd.DataFrame(job_stats)
    
    return job_stats_df, stats_df

def analyze_problematic_cases(individual_stats_df, threshold_hours=4):
    """문제가 되는 장시간 체류 케이스 분석"""
    threshold_minutes = threshold_hours * 60
    
    problematic = individual_stats_df[individual_stats_df['stay_duration_minutes'] > threshold_minutes].copy()
    
    if len(problematic) == 0:
        print(f"✅ {threshold_hours}시간 이상 체류하는 지원자가 없습니다.")
        return None
    
    problematic['stay_duration_hours'] = problematic['stay_duration_minutes'] / 60
    problematic = problematic.sort_values('stay_duration_minutes', ascending=False)
    
    print(f"\n🚨 {threshold_hours}시간 이상 체류하는 지원자: {len(problematic)}명")
    print("상위 10명:")
    
    display_cols = ['candidate_id', 'job_code', 'interview_date', 'stay_duration_hours', 'start_time_minutes', 'end_time_minutes']
    for col in display_cols:
        if col not in problematic.columns:
            display_cols.remove(col)
    
    print(problematic[display_cols].head(10).to_string(index=False))
    
    return problematic

def identify_optimization_opportunities(individual_stats_df, job_stats_df):
    """최적화 기회 식별"""
    print("\n🔍 최적화 기회 분석")
    
    # 1. 직무별 체류시간 편차 분석
    print("\n📊 직무별 체류시간 편차:")
    high_variance_jobs = job_stats_df[job_stats_df['std_duration'] > 60].sort_values('std_duration', ascending=False)
    
    if len(high_variance_jobs) > 0:
        print("편차가 큰 직무들 (60분 이상):")
        for _, row in high_variance_jobs.iterrows():
            print(f"  {row['job_code']}: 평균 {row['avg_duration']:.1f}분, 편차 {row['std_duration']:.1f}분 ({row['min_duration']:.1f}~{row['max_duration']:.1f}분)")
    
    # 2. 시간대별 분포 분석
    print("\n⏰ 시간대별 시작/종료 분포:")
    
    # 시작 시간 분포
    start_times = individual_stats_df['start_time_minutes']
    end_times = individual_stats_df['end_time_minutes']
    
    print(f"시작 시간: {start_times.min()/60:.1f}시 ~ {start_times.max()/60:.1f}시")
    print(f"종료 시간: {end_times.min()/60:.1f}시 ~ {end_times.max()/60:.1f}시")
    
    # 3. 날짜별 체류시간 분석
    if 'interview_date' in individual_stats_df.columns:
        print("\n📅 날짜별 체류시간 분석:")
        date_stats = individual_stats_df.groupby('interview_date')['stay_duration_minutes'].agg(['count', 'mean', 'max', 'std']).round(1)
        print(date_stats.to_string())
    
    # 4. 개선 제안
    print("\n💡 개선 제안:")
    
    # 장시간 체류자 비율
    long_stay_ratio = len(individual_stats_df[individual_stats_df['stay_duration_minutes'] > 300]) / len(individual_stats_df)
    print(f"  - 5시간 이상 체류자 비율: {long_stay_ratio:.1%}")
    
    # 평균 체류시간
    avg_stay = individual_stats_df['stay_duration_minutes'].mean()
    print(f"  - 전체 평균 체류시간: {avg_stay:.1f}분 ({avg_stay/60:.1f}시간)")
    
    if avg_stay > 240:  # 4시간 이상
        print("  ⚠️ 평균 체류시간이 4시간을 초과합니다. 최적화 필요!")
    
    return {
        'high_variance_jobs': high_variance_jobs,
        'long_stay_ratio': long_stay_ratio,
        'avg_stay_minutes': avg_stay
    }

def main():
    """메인 분석 실행"""
    print("=" * 80)
    print("🔍 UI 디폴트 데이터 체류시간 분석")
    print("=" * 80)
    
    # 1. 데이터 로드
    schedule_df = load_schedule_result()
    if schedule_df is None:
        return
    
    # 2. 체류시간 분석
    print("\n📊 체류시간 분석 중...")
    job_stats_df, individual_stats_df = calculate_stay_duration_analysis(schedule_df)
    
    if job_stats_df is None:
        return
    
    # 3. 기본 통계 출력
    print(f"\n✅ 분석 완료: {len(individual_stats_df)}명 지원자")
    print("\n📋 직무별 체류시간 통계:")
    print(job_stats_df.round(1).to_string(index=False))
    
    # 4. 전체 요약 통계
    print(f"\n🎯 전체 요약:")
    total_min = individual_stats_df['stay_duration_minutes'].min()
    total_max = individual_stats_df['stay_duration_minutes'].max()
    total_avg = individual_stats_df['stay_duration_minutes'].mean()
    total_median = individual_stats_df['stay_duration_minutes'].median()
    
    print(f"  최소 체류시간: {total_min:.1f}분 ({total_min/60:.1f}시간)")
    print(f"  최대 체류시간: {total_max:.1f}분 ({total_max/60:.1f}시간)")
    print(f"  평균 체류시간: {total_avg:.1f}분 ({total_avg/60:.1f}시간)")
    print(f"  중간 체류시간: {total_median:.1f}분 ({total_median/60:.1f}시간)")
    
    # 5. 문제 케이스 분석
    problematic = analyze_problematic_cases(individual_stats_df, threshold_hours=4)
    
    # 6. 최적화 기회 식별
    optimization_info = identify_optimization_opportunities(individual_stats_df, job_stats_df)
    
    # 7. 결과 저장
    try:
        job_stats_df.to_excel("stay_time_job_stats.xlsx", index=False)
        individual_stats_df.to_excel("stay_time_individual_stats.xlsx", index=False)
        if problematic is not None:
            problematic.to_excel("stay_time_problematic_cases.xlsx", index=False)
        print(f"\n✅ 분석 결과 저장 완료")
    except Exception as e:
        print(f"⚠️ 결과 저장 실패: {e}")
    
    print("=" * 80)
    
    return job_stats_df, individual_stats_df, optimization_info

if __name__ == "__main__":
    main() 