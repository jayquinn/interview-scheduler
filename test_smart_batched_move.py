#!/usr/bin/env python3
"""
스마트 토론면접 그룹 이동 실험
- 토론면접 그룹만 이동시키고 개별 활동은 기존 시간대 유지
- 체류시간 단축 효과 측정
"""

import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import copy

def load_and_analyze_data():
    """데이터 로드 및 기본 분석"""
    print("🧪 스마트 토론면접 그룹 이동 실험")
    print("=" * 80)
    
    try:
        df = pd.read_excel('complete_ui_defaults_test_result.xlsx')
        print(f"✅ 스케줄 데이터 로드: {len(df)}개 항목")
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return None
    
    # 시간 변환
    df['start_minutes'] = df['start_time'].apply(lambda x: int(x * 24 * 60))
    df['end_minutes'] = df['end_time'].apply(lambda x: int(x * 24 * 60))
    
    return df

def analyze_current_situation(df):
    """현재 상황 상세 분석"""
    print("\n🔍 현재 상황 분석")
    print("=" * 60)
    
    # 활동별 분석
    activities = df['activity_name'].unique()
    print(f"📊 활동 종류: {list(activities)}")
    
    # 토론면접 그룹 분석
    discussion_df = df[df['activity_name'] == '토론면접']
    print(f"\n📋 토론면접 현황:")
    print(f"  - 총 토론면접 항목: {len(discussion_df)}명")
    
    # 날짜별, 시간대별 그룹 분석
    groups = discussion_df.groupby(['interview_date', 'start_minutes', 'room_name'])
    
    group_info = []
    for (date, start_time, room), group in groups:
        start_hour = start_time // 60
        start_min = start_time % 60
        group_info.append({
            'date': date,
            'start_time': start_time,
            'start_display': f"{start_hour:02d}:{start_min:02d}",
            'room': room,
            'size': len(group),
            'members': group['applicant_id'].tolist(),
            'job_codes': group['job_code'].unique().tolist()
        })
    
    group_info.sort(key=lambda x: (x['date'], x['start_time']))
    
    print(f"  - 식별된 토론면접 그룹: {len(group_info)}개")
    for i, info in enumerate(group_info):
        print(f"    {i+1}. {info['date']} {info['start_display']} {info['room']}: {info['size']}명 ({', '.join(info['job_codes'])})")
    
    return group_info

def calculate_detailed_stay_times(df):
    """상세한 체류시간 분석"""
    print("\n⏰ 현재 체류시간 분석")
    print("=" * 60)
    
    stay_analysis = {}
    
    for applicant_id in df['applicant_id'].unique():
        applicant_data = df[df['applicant_id'] == applicant_id]
        
        # 활동별 정보
        activities_info = []
        for _, row in applicant_data.iterrows():
            activities_info.append({
                'activity': row['activity_name'],
                'start': row['start_minutes'],
                'end': row['end_minutes'],
                'duration': row['end_minutes'] - row['start_minutes']
            })
        
        activities_info.sort(key=lambda x: x['start'])
        
        # 체류시간 계산
        earliest_start = min(act['start'] for act in activities_info)
        latest_end = max(act['end'] for act in activities_info)
        stay_minutes = latest_end - earliest_start
        
        # 간격 분석
        gaps = []
        for i in range(len(activities_info) - 1):
            gap = activities_info[i+1]['start'] - activities_info[i]['end']
            gaps.append(gap)
        
        stay_analysis[applicant_id] = {
            'stay_hours': stay_minutes / 60,
            'stay_minutes': stay_minutes,
            'earliest_start': earliest_start,
            'latest_end': latest_end,
            'activities': activities_info,
            'gaps': gaps,
            'date': applicant_data['interview_date'].iloc[0],
            'job_code': applicant_data['job_code'].iloc[0]
        }
    
    # 통계
    all_stay_hours = [info['stay_hours'] for info in stay_analysis.values()]
    
    print(f"📊 현재 체류시간 통계:")
    print(f"  - 지원자 수: {len(stay_analysis)}명")
    print(f"  - 평균: {np.mean(all_stay_hours):.1f}시간")
    print(f"  - 최대: {np.max(all_stay_hours):.1f}시간")
    print(f"  - 최소: {np.min(all_stay_hours):.1f}시간")
    print(f"  - 표준편차: {np.std(all_stay_hours):.1f}시간")
    
    # 문제 케이스 식별
    long_stay = [(aid, info) for aid, info in stay_analysis.items() if info['stay_hours'] >= 4.0]
    long_stay.sort(key=lambda x: x[1]['stay_hours'], reverse=True)
    
    print(f"\n🚨 장시간 체류자 (4시간 이상): {len(long_stay)}명")
    for aid, info in long_stay[:10]:  # 상위 10명만
        start_h, start_m = divmod(info['earliest_start'], 60)
        end_h, end_m = divmod(info['latest_end'], 60)
        activities = ' → '.join([act['activity'] for act in info['activities']])
        print(f"  {aid}: {info['stay_hours']:.1f}h ({start_h:02d}:{start_m:02d}~{end_h:02d}:{end_m:02d}) {activities}")
    
    return stay_analysis

def simulate_smart_group_move(df, group_info, stay_analysis):
    """스마트 그룹 이동 시뮬레이션"""
    print(f"\n🚀 스마트 그룹 이동 시뮬레이션")
    print("=" * 60)
    
    # 시뮬레이션 시나리오들
    scenarios = [
        {
            'name': '7/1 앞시간 그룹 → 뒷시간 이동',
            'target_date': '2025-07-01',
            'move_from_time': 540,  # 9:00 (540분)
            'move_to_time': 780,    # 13:00 (780분)
            'description': '7/1일 9시 토론면접 그룹들을 13시로 이동'
        },
        {
            'name': '7/2 일부 그룹 분산',
            'target_date': '2025-07-02',
            'move_from_time': 540,  # 9:00
            'move_to_time': 720,    # 12:00
            'description': '7/2일 9시 그룹 중 일부를 12시로 이동'
        }
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n🎯 시나리오: {scenario['name']}")
        print(f"   {scenario['description']}")
        
        # 이동 대상 그룹 찾기
        target_groups = [
            g for g in group_info 
            if g['date'] == scenario['target_date'] and g['start_time'] == scenario['move_from_time']
        ]
        
        if not target_groups:
            print(f"   ❌ 대상 그룹 없음")
            continue
        
        print(f"   📋 대상 그룹: {len(target_groups)}개")
        for group in target_groups:
            print(f"      - {group['room']}: {group['size']}명 ({', '.join(group['job_codes'])})")
        
        # 시뮬레이션 실행
        result = simulate_scenario(df, target_groups, scenario, stay_analysis)
        results.append(result)
    
    return results

def simulate_scenario(df, target_groups, scenario, stay_analysis):
    """단일 시나리오 시뮬레이션"""
    
    # 원본 데이터 복사
    modified_df = df.copy()
    moved_applicants = set()
    
    # 각 그룹의 토론면접만 이동
    for group in target_groups:
        move_offset = scenario['move_to_time'] - scenario['move_from_time']
        
        for applicant_id in group['members']:
            moved_applicants.add(applicant_id)
            
            # 해당 지원자의 토론면접만 이동
            mask = (modified_df['applicant_id'] == applicant_id) & (modified_df['activity_name'] == '토론면접')
            modified_df.loc[mask, 'start_minutes'] += move_offset
            modified_df.loc[mask, 'end_minutes'] += move_offset
    
    # 새로운 체류시간 계산
    new_stay_analysis = {}
    for applicant_id in moved_applicants:
        applicant_data = modified_df[modified_df['applicant_id'] == applicant_id]
        
        start_times = applicant_data['start_minutes'].tolist()
        end_times = applicant_data['end_minutes'].tolist()
        
        earliest_start = min(start_times)
        latest_end = max(end_times)
        stay_minutes = latest_end - earliest_start
        
        new_stay_analysis[applicant_id] = {
            'stay_hours': stay_minutes / 60,
            'stay_minutes': stay_minutes,
            'earliest_start': earliest_start,
            'latest_end': latest_end
        }
    
    # 변화 분석
    improvements = []
    total_reduction = 0
    
    for applicant_id in moved_applicants:
        if applicant_id in stay_analysis and applicant_id in new_stay_analysis:
            original_hours = stay_analysis[applicant_id]['stay_hours']
            new_hours = new_stay_analysis[applicant_id]['stay_hours']
            change = new_hours - original_hours
            
            improvements.append({
                'applicant_id': applicant_id,
                'original_hours': original_hours,
                'new_hours': new_hours,
                'change_hours': change,
                'job_code': stay_analysis[applicant_id]['job_code']
            })
            
            if change < 0:
                total_reduction += abs(change)
    
    improvements.sort(key=lambda x: x['change_hours'])
    
    # 결과 출력
    print(f"   📊 변화 분석:")
    improved_count = sum(1 for imp in improvements if imp['change_hours'] < 0)
    worsened_count = sum(1 for imp in improvements if imp['change_hours'] > 0)
    unchanged_count = sum(1 for imp in improvements if imp['change_hours'] == 0)
    
    print(f"      개선: {improved_count}명, 악화: {worsened_count}명, 불변: {unchanged_count}명")
    print(f"      총 단축시간: {total_reduction:.1f}시간")
    
    # 상세 변화 (개선된 케이스만)
    print(f"   🎯 개선된 케이스:")
    for imp in improvements:
        if imp['change_hours'] < 0:
            print(f"      {imp['applicant_id']}: {imp['original_hours']:.1f}h → {imp['new_hours']:.1f}h ({imp['change_hours']:.1f}h)")
    
    return {
        'scenario': scenario,
        'moved_applicants': len(moved_applicants),
        'improvements': improvements,
        'total_reduction': total_reduction,
        'improved_count': improved_count
    }

def main():
    """메인 실험 함수"""
    # 1. 데이터 로드
    df = load_and_analyze_data()
    if df is None:
        return
    
    # 2. 현재 상황 분석
    group_info = analyze_current_situation(df)
    
    # 3. 체류시간 분석
    stay_analysis = calculate_detailed_stay_times(df)
    
    # 4. 스마트 이동 시뮬레이션
    results = simulate_smart_group_move(df, group_info, stay_analysis)
    
    # 5. 전체 요약
    print(f"\n🎉 실험 완료!")
    print("=" * 60)
    
    total_reduction = sum(r['total_reduction'] for r in results)
    total_improved = sum(r['improved_count'] for r in results)
    
    print(f"📊 전체 실험 결과:")
    print(f"  - 총 단축시간: {total_reduction:.1f}시간")
    print(f"  - 개선된 지원자: {total_improved}명")
    
    if total_reduction > 0:
        print(f"✅ 토론면접 그룹 이동이 체류시간 단축에 효과적임을 확인!")
    else:
        print(f"⚠️ 추가 분석이 필요함")

if __name__ == "__main__":
    main() 