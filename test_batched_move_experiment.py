#!/usr/bin/env python3
"""
토론면접 그룹 뒷시간 이동 실험
- 디폴트 데이터 결과에서 토론면접 그룹들을 뒷시간으로 이동
- 체류시간 변화 측정 및 효과 분석
"""

import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import copy

def load_schedule_data():
    """기존 스케줄 데이터 로드"""
    try:
        df = pd.read_excel('complete_ui_defaults_test_result.xlsx')
        print(f"✅ 스케줄 데이터 로드: {len(df)}개 항목")
        return df
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return None

def convert_time_to_minutes(time_value):
    """시간 값을 분 단위로 변환"""
    if isinstance(time_value, float):
        # 하루 비율 형태 (0.375 = 9:00)
        total_minutes = time_value * 24 * 60
        return int(total_minutes)
    elif hasattr(time_value, 'hour'):
        # time 객체
        return time_value.hour * 60 + time_value.minute
    else:
        # 문자열 시간 파싱 시도
        try:
            if isinstance(time_value, str):
                if ':' in time_value:
                    parts = time_value.split(':')
                    return int(parts[0]) * 60 + int(parts[1])
        except:
            pass
        return 0

def analyze_current_schedule(df):
    """현재 스케줄 분석"""
    print("\n🔍 현재 스케줄 분석")
    print("=" * 60)
    
    # 시간 컬럼 변환
    df['start_minutes'] = df['start_time'].apply(convert_time_to_minutes)
    df['end_minutes'] = df['end_time'].apply(convert_time_to_minutes)
    
    # 토론면접 그룹 식별
    discussion_groups = df[df['activity_name'].str.contains('토론', na=False)]
    
    print(f"📊 토론면접 그룹 분석:")
    print(f"  - 총 토론면접 항목: {len(discussion_groups)}개")
    
    # 날짜별, 그룹별 분석
    group_analysis = defaultdict(list)
    
    for _, row in discussion_groups.iterrows():
        date = row['interview_date']
        start_time = row['start_minutes']
        end_time = row['end_minutes']
        applicant_id = row['applicant_id']
        job_code = row['job_code']
        
        group_key = f"{date}_{job_code}_{start_time}"
        group_analysis[group_key].append({
            'applicant_id': applicant_id,
            'start_time': start_time,
            'end_time': end_time,
            'job_code': job_code,
            'date': date
        })
    
    print(f"  - 식별된 그룹 수: {len(group_analysis)}개")
    
    # 그룹별 상세 정보
    print(f"\n📋 그룹별 상세:")
    for group_key, members in group_analysis.items():
        date = members[0]['date']
        job_code = members[0]['job_code']
        start_minutes = members[0]['start_time']
        start_hour = start_minutes // 60
        start_min = start_minutes % 60
        
        print(f"  {group_key}: {len(members)}명, {start_hour:02d}:{start_min:02d} 시작")
    
    return group_analysis

def calculate_stay_times(df):
    """각 지원자의 체류시간 계산"""
    print("\n⏰ 체류시간 계산")
    print("=" * 60)
    
    stay_times = {}
    
    for applicant_id in df['applicant_id'].unique():
        applicant_data = df[df['applicant_id'] == applicant_id]
        
        if len(applicant_data) == 0:
            continue
            
        start_times = applicant_data['start_minutes'].tolist()
        end_times = applicant_data['end_minutes'].tolist()
        
        earliest_start = min(start_times)
        latest_end = max(end_times)
        
        stay_minutes = latest_end - earliest_start
        stay_hours = stay_minutes / 60
        
        stay_times[applicant_id] = {
            'stay_minutes': stay_minutes,
            'stay_hours': stay_hours,
            'earliest_start': earliest_start,
            'latest_end': latest_end,
            'activities': applicant_data['activity_name'].tolist(),
            'date': applicant_data['interview_date'].iloc[0]
        }
    
    # 통계 계산
    all_stay_hours = [info['stay_hours'] for info in stay_times.values()]
    
    print(f"📊 현재 체류시간 통계:")
    print(f"  - 지원자 수: {len(stay_times)}명")
    print(f"  - 평균 체류시간: {np.mean(all_stay_hours):.1f}시간")
    print(f"  - 최대 체류시간: {np.max(all_stay_hours):.1f}시간")
    print(f"  - 최소 체류시간: {np.min(all_stay_hours):.1f}시간")
    print(f"  - 표준편차: {np.std(all_stay_hours):.1f}시간")
    
    # 체류시간 분포
    long_stay_count = sum(1 for h in all_stay_hours if h >= 5.0)
    medium_stay_count = sum(1 for h in all_stay_hours if 3.0 <= h < 5.0)
    short_stay_count = sum(1 for h in all_stay_hours if h < 3.0)
    
    print(f"  - 5시간 이상: {long_stay_count}명 ({long_stay_count/len(stay_times)*100:.1f}%)")
    print(f"  - 3-5시간: {medium_stay_count}명 ({medium_stay_count/len(stay_times)*100:.1f}%)")
    print(f"  - 3시간 미만: {short_stay_count}명 ({short_stay_count/len(stay_times)*100:.1f}%)")
    
    return stay_times

def simulate_group_move(df, group_analysis, target_date, target_job, move_hours=2):
    """특정 토론면접 그룹을 뒷시간으로 이동 시뮬레이션"""
    print(f"\n🚀 그룹 이동 시뮬레이션: {target_date} {target_job} (+{move_hours}시간)")
    print("=" * 60)
    
    # 원본 데이터 복사
    modified_df = df.copy()
    
    # 이동할 그룹 찾기
    target_groups = []
    for group_key, members in group_analysis.items():
        if target_date in group_key and target_job in group_key:
            target_groups.append((group_key, members))
    
    if not target_groups:
        print(f"❌ {target_date} {target_job} 그룹을 찾을 수 없습니다")
        return None, None
    
    moved_applicants = set()
    
    for group_key, members in target_groups:
        original_start = members[0]['start_time']
        new_start = original_start + (move_hours * 60)  # 분 단위
        move_offset = move_hours * 60
        
        print(f"🔄 그룹 이동: {group_key}")
        print(f"  - 기존 시작: {original_start//60:02d}:{original_start%60:02d}")
        print(f"  - 새 시작: {new_start//60:02d}:{new_start%60:02d}")
        print(f"  - 그룹 크기: {len(members)}명")
        
        # 해당 그룹 멤버들의 모든 활동 시간 이동
        for member in members:
            applicant_id = member['applicant_id']
            moved_applicants.add(applicant_id)
            
            # 해당 지원자의 모든 활동 시간 이동
            applicant_mask = modified_df['applicant_id'] == applicant_id
            modified_df.loc[applicant_mask, 'start_minutes'] += move_offset
            modified_df.loc[applicant_mask, 'end_minutes'] += move_offset
    
    print(f"✅ 총 {len(moved_applicants)}명의 일정 이동 완료")
    
    return modified_df, moved_applicants

def compare_stay_times(original_stay_times, modified_df, moved_applicants):
    """이동 전후 체류시간 비교"""
    print(f"\n📊 체류시간 변화 분석")
    print("=" * 60)
    
    # 수정된 스케줄에서 체류시간 재계산
    new_stay_times = {}
    
    for applicant_id in modified_df['applicant_id'].unique():
        applicant_data = modified_df[modified_df['applicant_id'] == applicant_id]
        
        if len(applicant_data) == 0:
            continue
            
        start_times = applicant_data['start_minutes'].tolist()
        end_times = applicant_data['end_minutes'].tolist()
        
        earliest_start = min(start_times)
        latest_end = max(end_times)
        
        stay_minutes = latest_end - earliest_start
        stay_hours = stay_minutes / 60
        
        new_stay_times[applicant_id] = {
            'stay_minutes': stay_minutes,
            'stay_hours': stay_hours,
            'earliest_start': earliest_start,
            'latest_end': latest_end
        }
    
    # 변화 분석
    print(f"🔍 개별 지원자 변화 (이동 그룹):")
    total_reduction = 0
    improved_count = 0
    
    for applicant_id in moved_applicants:
        if applicant_id in original_stay_times and applicant_id in new_stay_times:
            original_hours = original_stay_times[applicant_id]['stay_hours']
            new_hours = new_stay_times[applicant_id]['stay_hours']
            change = new_hours - original_hours
            
            if change < 0:
                improved_count += 1
                total_reduction += abs(change)
                
            print(f"  {applicant_id}: {original_hours:.1f}h → {new_hours:.1f}h ({change:+.1f}h)")
    
    # 전체 통계 비교
    original_all_hours = [info['stay_hours'] for info in original_stay_times.values()]
    new_all_hours = [info['stay_hours'] for info in new_stay_times.values()]
    
    print(f"\n📈 전체 통계 변화:")
    print(f"  평균 체류시간: {np.mean(original_all_hours):.1f}h → {np.mean(new_all_hours):.1f}h ({np.mean(new_all_hours) - np.mean(original_all_hours):+.1f}h)")
    print(f"  최대 체류시간: {np.max(original_all_hours):.1f}h → {np.max(new_all_hours):.1f}h ({np.max(new_all_hours) - np.max(original_all_hours):+.1f}h)")
    print(f"  표준편차: {np.std(original_all_hours):.1f}h → {np.std(new_all_hours):.1f}h ({np.std(new_all_hours) - np.std(original_all_hours):+.1f}h)")
    
    print(f"\n🎯 개선 효과:")
    print(f"  - 개선된 지원자: {improved_count}/{len(moved_applicants)}명")
    print(f"  - 총 단축시간: {total_reduction:.1f}시간")
    
    return new_stay_times

def main():
    """메인 실험 함수"""
    print("🧪 토론면접 그룹 뒷시간 이동 실험")
    print("=" * 80)
    
    # 1. 데이터 로드
    df = load_schedule_data()
    if df is None:
        return
    
    # 2. 현재 스케줄 분석
    group_analysis = analyze_current_schedule(df)
    
    # 3. 현재 체류시간 계산
    original_stay_times = calculate_stay_times(df)
    
    # 4. 실험 시나리오별 시뮬레이션
    experiments = [
        ("2025-07-01", "JOB01", 2),  # 7/1 JOB01 그룹을 2시간 뒤로
        ("2025-07-01", "JOB02", 2),  # 7/1 JOB02 그룹을 2시간 뒤로
        ("2025-07-02", "JOB03", 1),  # 7/2 JOB03 그룹을 1시간 뒤로
    ]
    
    for target_date, target_job, move_hours in experiments:
        print(f"\n{'='*80}")
        print(f"🧪 실험: {target_date} {target_job} 그룹 +{move_hours}시간 이동")
        print(f"{'='*80}")
        
        # 시뮬레이션 실행
        modified_df, moved_applicants = simulate_group_move(
            df, group_analysis, target_date, target_job, move_hours
        )
        
        if modified_df is not None:
            # 변화 분석
            new_stay_times = compare_stay_times(
                original_stay_times, modified_df, moved_applicants
            )

if __name__ == "__main__":
    main() 