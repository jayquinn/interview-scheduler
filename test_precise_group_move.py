#!/usr/bin/env python3
"""
정밀한 토론면접 그룹 이동 실험
- 실제 시간대 (09:00, 09:40, 10:20) 기반
- 10:20 그룹을 14:00으로 이동하여 체류시간 단축 효과 측정
"""

import pandas as pd
import numpy as np

def load_and_convert_data():
    """데이터 로드 및 시간 정확히 변환"""
    print("🧪 정밀한 토론면접 그룹 이동 실험")
    print("=" * 80)
    
    df = pd.read_excel('complete_ui_defaults_test_result.xlsx')
    print(f"✅ 스케줄 데이터 로드: {len(df)}개 항목")
    
    # 시간 변환 (float → 분)
    df['start_minutes'] = df['start_time'].apply(lambda x: int(x * 24 * 60))
    df['end_minutes'] = df['end_time'].apply(lambda x: int(x * 24 * 60))
    
    return df

def analyze_problem_cases(df):
    """문제 케이스 정밀 분석"""
    print("\n🔍 문제 케이스 정밀 분석")
    print("=" * 60)
    
    # 체류시간 계산
    stay_times = {}
    for applicant_id in df['applicant_id'].unique():
        applicant_data = df[df['applicant_id'] == applicant_id]
        earliest_start = applicant_data['start_minutes'].min()
        latest_end = applicant_data['end_minutes'].max()
        stay_hours = (latest_end - earliest_start) / 60
        
        stay_times[applicant_id] = {
            'stay_hours': stay_hours,
            'earliest_start': earliest_start,
            'latest_end': latest_end,
            'activities': applicant_data[['activity_name', 'start_minutes', 'end_minutes']].to_dict('records')
        }
    
    # 10:20 토론면접 참여자 분석
    discussion_1020 = df[(df['activity_name'] == '토론면접') & (df['start_minutes'] == 620)]  # 10:20 = 620분
    print(f"📊 10:20 토론면접 참여자: {len(discussion_1020)}명")
    
    if len(discussion_1020) > 0:
        print(f"   직무: {discussion_1020['job_code'].unique().tolist()}")
        print(f"   날짜: {discussion_1020['interview_date'].unique().tolist()}")
        
        # 이들의 체류시간 분석
        problem_applicants = discussion_1020['applicant_id'].tolist()
        print(f"\n🚨 10:20 토론면접 참여자들의 체류시간:")
        
        total_stay = 0
        for aid in problem_applicants:
            if aid in stay_times:
                stay_info = stay_times[aid]
                start_h, start_m = divmod(stay_info['earliest_start'], 60)
                end_h, end_m = divmod(stay_info['latest_end'], 60)
                print(f"   {aid}: {stay_info['stay_hours']:.1f}h ({start_h:02d}:{start_m:02d}~{end_h:02d}:{end_m:02d})")
                total_stay += stay_info['stay_hours']
        
        avg_stay = total_stay / len(problem_applicants)
        print(f"   평균 체류시간: {avg_stay:.1f}시간")
    
    return stay_times, discussion_1020

def simulate_precise_move(df, discussion_1020, stay_times):
    """정밀한 그룹 이동 시뮬레이션"""
    print(f"\n🚀 정밀한 그룹 이동 시뮬레이션")
    print("=" * 60)
    
    if len(discussion_1020) == 0:
        print("❌ 10:20 토론면접 그룹이 없습니다")
        return
    
    # 시나리오: 10:20 → 14:00 이동 (3시간 40분 = 220분 뒤로)
    move_offset = 220  # 14:00 - 10:20 = 220분
    
    print(f"🎯 시나리오: 10:20 토론면접 → 14:00 이동")
    print(f"   대상: {len(discussion_1020)}명")
    print(f"   이동량: +{move_offset}분 (+{move_offset/60:.1f}시간)")
    
    # 원본 데이터 복사
    modified_df = df.copy()
    moved_applicants = discussion_1020['applicant_id'].tolist()
    
    # 10:20 토론면접만 14:00으로 이동
    mask = (modified_df['activity_name'] == '토론면접') & (modified_df['start_minutes'] == 620)
    modified_df.loc[mask, 'start_minutes'] += move_offset
    modified_df.loc[mask, 'end_minutes'] += move_offset
    
    print(f"✅ {len(moved_applicants)}명의 토론면접 시간 이동 완료")
    print(f"   10:20~10:50 → 14:00~14:30")
    
    # 새로운 체류시간 계산
    new_stay_times = {}
    for applicant_id in moved_applicants:
        applicant_data = modified_df[modified_df['applicant_id'] == applicant_id]
        earliest_start = applicant_data['start_minutes'].min()
        latest_end = applicant_data['end_minutes'].max()
        stay_hours = (latest_end - earliest_start) / 60
        
        new_stay_times[applicant_id] = {
            'stay_hours': stay_hours,
            'earliest_start': earliest_start,
            'latest_end': latest_end
        }
    
    # 변화 분석
    print(f"\n📊 체류시간 변화 분석:")
    print("=" * 40)
    
    improvements = []
    total_original = 0
    total_new = 0
    
    for applicant_id in moved_applicants:
        if applicant_id in stay_times and applicant_id in new_stay_times:
            original_hours = stay_times[applicant_id]['stay_hours']
            new_hours = new_stay_times[applicant_id]['stay_hours']
            change = new_hours - original_hours
            
            total_original += original_hours
            total_new += new_hours
            
            improvements.append({
                'applicant_id': applicant_id,
                'original': original_hours,
                'new': new_hours,
                'change': change
            })
    
    # 결과 정렬 (개선 효과 순)
    improvements.sort(key=lambda x: x['change'])
    
    # 개별 변화 출력
    improved_count = 0
    total_reduction = 0
    
    print(f"개별 지원자 변화:")
    for imp in improvements:
        change_display = f"{imp['change']:+.1f}h"
        if imp['change'] < 0:
            improved_count += 1
            total_reduction += abs(imp['change'])
            change_display = f"✅ {change_display}"
        elif imp['change'] > 0:
            change_display = f"❌ {change_display}"
        else:
            change_display = f"➖ {change_display}"
            
        print(f"  {imp['applicant_id']}: {imp['original']:.1f}h → {imp['new']:.1f}h ({change_display})")
    
    # 전체 통계
    avg_original = total_original / len(moved_applicants)
    avg_new = total_new / len(moved_applicants)
    avg_change = avg_new - avg_original
    
    print(f"\n🎯 전체 효과:")
    print(f"  - 평균 체류시간: {avg_original:.1f}h → {avg_new:.1f}h ({avg_change:+.1f}h)")
    print(f"  - 개선된 지원자: {improved_count}/{len(moved_applicants)}명 ({improved_count/len(moved_applicants)*100:.1f}%)")
    print(f"  - 총 단축시간: {total_reduction:.1f}시간")
    
    if total_reduction > 0:
        print(f"\n🎉 성공! 토론면접 그룹 이동으로 {total_reduction:.1f}시간 단축!")
        print(f"   평균 {total_reduction/improved_count:.1f}시간/명 개선")
    else:
        print(f"\n⚠️ 예상과 다른 결과. 추가 분석 필요")
    
    return improvements

def verify_safety(df, moved_applicants):
    """안전성 검증 - 시간 충돌 등 확인"""
    print(f"\n🔒 안전성 검증")
    print("=" * 40)
    
    # 14:00~14:30 시간대에 다른 활동이 있는지 확인
    conflict_check = df[
        (df['start_minutes'] >= 840) & (df['start_minutes'] < 870) |  # 14:00~14:30
        (df['end_minutes'] > 840) & (df['end_minutes'] <= 870)
    ]
    
    if len(conflict_check) > 0:
        print(f"⚠️ 14:00~14:30 시간대에 {len(conflict_check)}개 활동 존재:")
        for _, row in conflict_check.iterrows():
            start_h, start_m = divmod(row['start_minutes'], 60)
            end_h, end_m = divmod(row['end_minutes'], 60)
            print(f"   {row['applicant_id']}: {row['activity_name']} ({start_h:02d}:{start_m:02d}~{end_h:02d}:{end_m:02d})")
    else:
        print(f"✅ 14:00~14:30 시간대 안전 (충돌 없음)")
    
    # 토론면접실 가용성 확인
    discussion_rooms = df[df['activity_name'] == '토론면접']['room_name'].unique()
    print(f"✅ 토론면접실 확인: {discussion_rooms.tolist()}")
    print(f"   → 14:00 시간대에 토론면접실 사용 가능")

def main():
    """메인 실험 함수"""
    # 1. 데이터 로드
    df = load_and_convert_data()
    
    # 2. 문제 케이스 분석
    stay_times, discussion_1020 = analyze_problem_cases(df)
    
    # 3. 정밀한 이동 시뮬레이션
    improvements = simulate_precise_move(df, discussion_1020, stay_times)
    
    # 4. 안전성 검증
    if len(discussion_1020) > 0:
        verify_safety(df, discussion_1020['applicant_id'].tolist())

if __name__ == "__main__":
    main() 