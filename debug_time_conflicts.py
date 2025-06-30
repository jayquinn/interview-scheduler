#!/usr/bin/env python3
"""
시간 충돌 문제 상세 분석 스크립트
"""

import pandas as pd
from test_app_default_data import create_app_default_data
from solver.api import solve_for_days_v2
import core
from app import _convert_integrated_to_dual_display

def analyze_time_conflicts():
    """시간 충돌 문제를 단계별로 분석"""
    
    print("🔍 시간 충돌 분석 시작...")
    
    # 1. 스케줄러 원본 결과 분석
    print("\n" + "="*60)
    print("1️⃣ 스케줄러 원본 결과 분석")
    print("="*60)
    
    session_state = create_app_default_data()
    cfg = core.build_config(session_state)
    
    params = {
        "min_gap_min": 5,
        "time_limit_sec": 30,
        "max_stay_hours": 5,
        "group_min_size": 4,
        "group_max_size": 6
    }
    
    status, result_df, logs, limit = solve_for_days_v2(cfg, params, debug=True)
    
    if status != "SUCCESS" or result_df is None or result_df.empty:
        print("❌ 스케줄링 실패")
        return
    
    print(f"✅ 원본 결과: {len(result_df)}개 항목")
    
    # 원본 시간 충돌 확인
    print("\n🔍 원본 시간 충돌 확인:")
    original_conflicts = check_time_conflicts(result_df, "원본")
    
    # 2. 이중 스케줄 변환 후 분석
    print("\n" + "="*60)  
    print("2️⃣ 이중 스케줄 변환 후 분석")
    print("="*60)
    
    converted_df = _convert_integrated_to_dual_display(result_df.copy())
    print(f"✅ 변환 결과: {len(converted_df)}개 항목")
    
    # 변환 후 시간 충돌 확인
    print("\n🔍 변환 후 시간 충돌 확인:")
    converted_conflicts = check_time_conflicts(converted_df, "변환 후")
    
    # 3. 상세 비교 분석
    print("\n" + "="*60)
    print("3️⃣ 상세 변환 과정 분석") 
    print("="*60)
    
    analyze_conversion_details(result_df, converted_df)
    
    return result_df, converted_df


def check_time_conflicts(df, stage_name):
    """데이터프레임의 시간 충돌 확인"""
    conflicts = []
    
    if 'applicant_id' not in df.columns or 'start_time' not in df.columns:
        print(f"❌ {stage_name}: 필요한 컬럼이 없습니다")
        return conflicts
    
    # 지원자별 시간 충돌 확인
    for applicant_id in df['applicant_id'].unique():
        applicant_df = df[df['applicant_id'] == applicant_id].copy()
        applicant_df = applicant_df.sort_values('start_time')
        
        for i in range(len(applicant_df)):
            for j in range(i+1, len(applicant_df)):
                row1 = applicant_df.iloc[i]
                row2 = applicant_df.iloc[j]
                
                start1, end1 = row1['start_time'], row1['end_time']
                start2, end2 = row2['start_time'], row2['end_time']
                
                # 시간 겹침 확인
                if not (end1 <= start2 or start1 >= end2):
                    conflict = {
                        'applicant_id': applicant_id,
                        'activity1': row1.get('activity_name', 'Unknown'),
                        'room1': row1.get('room_name', 'Unknown'),
                        'time1': f"{start1}~{end1}",
                        'activity2': row2.get('activity_name', 'Unknown'), 
                        'room2': row2.get('room_name', 'Unknown'),
                        'time2': f"{start2}~{end2}"
                    }
                    conflicts.append(conflict)
    
    if conflicts:
        print(f"❌ {stage_name}: {len(conflicts)}건의 시간 충돌 발견")
        for conflict in conflicts:
            print(f"  - {conflict['applicant_id']}: {conflict['activity1']}({conflict['room1']}) {conflict['time1']} ↔ {conflict['activity2']}({conflict['room2']}) {conflict['time2']}")
    else:
        print(f"✅ {stage_name}: 시간 충돌 없음")
    
    return conflicts


def analyze_conversion_details(original_df, converted_df):
    """변환 과정 상세 분석"""
    
    print("🔍 변환 전후 비교:")
    
    # 통합 활동이 있는 지원자만 분석
    integrated_rows = original_df[original_df['activity_name'].str.contains('+', na=False, regex=False)]
    
    if integrated_rows.empty:
        print("❌ 통합 활동을 찾을 수 없습니다")
        return
    
    for _, orig_row in integrated_rows.iterrows():
        applicant_id = orig_row['applicant_id']
        activity_name = orig_row['activity_name']
        
        print(f"\n👤 {applicant_id} - {activity_name}")
        print(f"  원본: {orig_row['start_time']}~{orig_row['end_time']} @ {orig_row.get('room_name', 'Unknown')}")
        
        # 변환 후 해당 지원자의 관련 활동들 찾기
        converted_rows = converted_df[
            (converted_df['applicant_id'] == applicant_id) & 
            (converted_df.get('original_integrated', '') == activity_name)
        ]
        
        for _, conv_row in converted_rows.iterrows():
            print(f"  변환: {conv_row['activity_name']} - {conv_row['start_time']}~{conv_row['end_time']} @ {conv_row.get('room_name', 'Unknown')}")


if __name__ == "__main__":
    try:
        original_df, converted_df = analyze_time_conflicts()
        print("\n✅ 분석 완료!")
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc() 