#!/usr/bin/env python3
"""
실제 UI 디폴트 데이터의 체류시간 분석 (Float 시간 형식 지원)
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
    """체류시간 분석 (Float 시간 형식 지원)"""
    stats_data = []
    
    # 컬럼명 확인
    id_col = 'applicant_id'
    job_col = 'job_code' 
    date_col = 'interview_date'
    
    print(f"✅ 분석 컬럼: ID={id_col}, JOB={job_col}, DATE={date_col}")
    
    # 지원자별 체류시간 계산
    for candidate_id, candidate_data in schedule_df.groupby(id_col):
        if len(candidate_data) == 0:
            continue
            
        # 해당 지원자의 모든 시간 정보 수집
        all_times = []
        
        for _, row in candidate_data.iterrows():
            # start_time과 end_time에서 시간 정보 추출
            start_time = row.get('start_time')
            end_time = row.get('end_time')
            
            if pd.notna(start_time):
                try:
                    # float 형태 시간 처리 (하루의 비율: 0.375 = 9:00)
                    if isinstance(start_time, (float, int)):
                        minutes = start_time * 24 * 60  # 하루 비율 → 분 단위
                        all_times.append(minutes)
                except:
                    continue
            
            if pd.notna(end_time):
                try:
                    # float 형태 시간 처리 (하루의 비율: 0.375 = 9:00)
                    if isinstance(end_time, (float, int)):
                        minutes = end_time * 24 * 60  # 하루 비율 → 분 단위
                        all_times.append(minutes)
                except:
                    continue
        
        if len(all_times) >= 2:  # 최소 시작/종료 시간이 있어야 함
            # 체류시간 = 최대 시간 - 최소 시간
            stay_duration_minutes = max(all_times) - min(all_times)
            
            # 메타 정보 추출
            job_code = candidate_data.iloc[0].get(job_col, 'Unknown')
            interview_date = candidate_data.iloc[0].get(date_col, 'Unknown')
            
            # 시간 변환 (분 → 시:분 형식)
            def minutes_to_time_str(minutes):
                hours = int(minutes // 60)
                mins = int(minutes % 60)
                return f"{hours:02d}:{mins:02d}"
            
            stats_data.append({
                'candidate_id': candidate_id,
                'job_code': job_code,
                'interview_date': interview_date,
                'stay_duration_minutes': stay_duration_minutes,
                'start_time_minutes': min(all_times),
                'end_time_minutes': max(all_times),
                'start_time_str': minutes_to_time_str(min(all_times)),
                'end_time_str': minutes_to_time_str(max(all_times)),
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
    
    display_cols = ['candidate_id', 'job_code', 'interview_date', 'stay_duration_hours', 'start_time_str', 'end_time_str']
    print(problematic[display_cols].head(10).to_string(index=False))
    
    return problematic

def identify_optimization_opportunities(individual_stats_df, job_stats_df):
    """최적화 기회 식별"""
    print("\n🔍 최적화 기회 분석")
    
    # 1. 직무별 체류시간 편차 분석
    print("\n📊 직무별 체류시간 편차:")
    high_variance_jobs = job_stats_df[job_stats_df['std_duration'] > 30].sort_values('std_duration', ascending=False)
    
    if len(high_variance_jobs) > 0:
        print("편차가 큰 직무들 (30분 이상):")
        for _, row in high_variance_jobs.iterrows():
            print(f"  {row['job_code']}: 평균 {row['avg_duration']:.1f}분, 편차 {row['std_duration']:.1f}분 ({row['min_duration']:.1f}~{row['max_duration']:.1f}분)")
    else:
        print("편차가 큰 직무가 없습니다 (모든 직무가 30분 미만 편차)")
    
    # 2. 시간대별 분포 분석
    print("\n⏰ 시간대별 시작/종료 분포:")
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
    elif avg_stay > 180:  # 3시간 이상
        print("  ⚡ 평균 체류시간이 3시간을 초과합니다. 최적화 고려 필요")
    else:
        print("  ✅ 평균 체류시간이 적당한 수준입니다")
    
    return {
        'high_variance_jobs': high_variance_jobs,
        'long_stay_ratio': long_stay_ratio,
        'avg_stay_minutes': avg_stay
    }

def analyze_time_gaps(individual_stats_df, schedule_df):
    """활동 간 시간 간격 분석"""
    print("\n⏳ 활동 간 시간 간격 분석")
    
    gap_data = []
    
    for candidate_id in individual_stats_df['candidate_id']:
        candidate_activities = schedule_df[schedule_df['applicant_id'] == candidate_id].copy()
        
        if len(candidate_activities) > 1:
            # 시작 시간으로 정렬
            candidate_activities['start_minutes'] = candidate_activities['start_time'] * 24 * 60
            candidate_activities['end_minutes'] = candidate_activities['end_time'] * 24 * 60
            candidate_activities = candidate_activities.sort_values('start_minutes')
            
            # 연속된 활동 간 간격 계산
            for i in range(len(candidate_activities) - 1):
                current_end = candidate_activities.iloc[i]['end_minutes']
                next_start = candidate_activities.iloc[i+1]['start_minutes']
                gap_minutes = next_start - current_end
                
                gap_data.append({
                    'candidate_id': candidate_id,
                    'gap_minutes': gap_minutes,
                    'activity_1': candidate_activities.iloc[i]['activity_name'],
                    'activity_2': candidate_activities.iloc[i+1]['activity_name']
                })
    
    if gap_data:
        gap_df = pd.DataFrame(gap_data)
        
        print(f"총 {len(gap_df)}개의 활동 간격 발견")
        print(f"평균 간격: {gap_df['gap_minutes'].mean():.1f}분")
        print(f"최소 간격: {gap_df['gap_minutes'].min():.1f}분")
        print(f"최대 간격: {gap_df['gap_minutes'].max():.1f}분")
        
        # 긴 간격이 있는 케이스
        long_gaps = gap_df[gap_df['gap_minutes'] > 60]
        if len(long_gaps) > 0:
            print(f"\n🚨 1시간 이상 간격이 있는 케이스: {len(long_gaps)}개")
            print(long_gaps.head().to_string(index=False))
        
        return gap_df
    else:
        print("활동 간격을 분석할 데이터가 없습니다.")
        return None

def main():
    """메인 분석 실행"""
    print("=" * 80)
    print("🔍 UI 디폴트 데이터 체류시간 분석 (Float 시간 형식)")
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
    display_job_stats = job_stats_df.copy()
    for col in ['min_duration', 'max_duration', 'avg_duration', 'median_duration', 'std_duration']:
        display_job_stats[col] = display_job_stats[col].round(1)
    print(display_job_stats.to_string(index=False))
    
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
    problematic = analyze_problematic_cases(individual_stats_df, threshold_hours=3)
    
    # 6. 최적화 기회 식별
    optimization_info = identify_optimization_opportunities(individual_stats_df, job_stats_df)
    
    # 7. 활동 간 간격 분석
    gap_df = analyze_time_gaps(individual_stats_df, schedule_df)
    
    # 8. 결과 저장
    try:
        job_stats_df.to_excel("stay_time_job_stats.xlsx", index=False)
        individual_stats_df.to_excel("stay_time_individual_stats.xlsx", index=False)
        if problematic is not None:
            problematic.to_excel("stay_time_problematic_cases.xlsx", index=False)
        if gap_df is not None:
            gap_df.to_excel("stay_time_gaps.xlsx", index=False)
        print(f"\n✅ 분석 결과 저장 완료")
    except Exception as e:
        print(f"⚠️ 결과 저장 실패: {e}")
    
    print("=" * 80)
    
    return job_stats_df, individual_stats_df, optimization_info

if __name__ == "__main__":
    main() 