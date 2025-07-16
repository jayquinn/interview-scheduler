#!/usr/bin/env python3
"""
UI를 통해 3단계 스케줄링을 자동으로 실행하고 결과를 분석하는 스크립트
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os

def run_ui_three_phase_test():
    """UI를 통해 3단계 스케줄링 테스트 실행"""
    
    print("=== UI 3단계 스케줄링 자동 테스트 시작 ===")
    
    # 1. 기본 설정 로드
    from app import default_df, init_session_states
    
    # 2. 세션 상태 초기화
    init_session_states()
    
    # 3. 기본 데이터 로드
    default_data = default_df()
    print(f"기본 데이터 로드: {len(default_data)}개 항목")
    
    # 4. 3단계 스케줄링 실행
    print("\n=== 3단계 스케줄링 실행 ===")
    
    # test_internal_analysis의 함수 직접 호출
    from test_internal_analysis import run_multi_date_scheduling
    
    try:
        results = run_multi_date_scheduling()
        
        if results:
            print("✅ 3단계 스케줄링 성공!")
            
            # 5. 결과 분석
            analyze_three_phase_results(results)
            
            # 6. 엑셀 파일 생성
            create_excel_report(results)
            
        else:
            print("❌ 3단계 스케줄링 실패!")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_three_phase_results(results):
    """3단계 결과 상세 분석"""
    
    print("\n=== 3단계 결과 상세 분석 ===")
    
    # 각 단계별 결과 확인
    for phase_name, phase_data in results.items():
        print(f"\n--- {phase_name} ---")
        print(f"상태: {phase_data['status']}")
        
        if phase_data['df'] is not None and not phase_data['df'].empty:
            df = phase_data['df']
            print(f"스케줄 수: {len(df)}개")
            
            # 체류시간 분석
            stay_times = analyze_stay_times(df)
            if stay_times:
                print(f"최대 체류시간: {stay_times['max_stay']:.2f}시간")
                print(f"평균 체류시간: {stay_times['avg_stay']:.2f}시간")
                print(f"최소 체류시간: {stay_times['min_stay']:.2f}시간")
                
                # 상위 5개 체류시간
                print("상위 5개 체류시간:")
                for i, stay in enumerate(stay_times['top_5']):
                    print(f"  {i+1}. {stay['applicant_id']}: {stay['stay_hours']:.2f}시간")
        else:
            print("데이터 없음")

def analyze_stay_times(df):
    """DataFrame에서 체류시간 분석"""
    
    if df.empty:
        return None
    
    # 날짜별 체류시간 계산
    stay_times = []
    
    for applicant_id in df['applicant_id'].unique():
        applicant_df = df[df['applicant_id'] == applicant_id]
        start_time = applicant_df['start_time'].min()
        end_time = applicant_df['end_time'].max()
        stay_hours = (end_time - start_time).total_seconds() / 3600
        stay_times.append({
            'applicant_id': applicant_id,
            'stay_hours': stay_hours
        })
    
    if not stay_times:
        return None
    
    # 정렬
    stay_times.sort(key=lambda x: x['stay_hours'], reverse=True)
    
    return {
        'max_stay': stay_times[0]['stay_hours'],
        'avg_stay': sum(s['stay_hours'] for s in stay_times) / len(stay_times),
        'min_stay': stay_times[-1]['stay_hours'],
        'top_5': stay_times[:5],
        'all_times': stay_times
    }

def create_excel_report(results):
    """엑셀 보고서 생성"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ui_three_phase_analysis_{timestamp}.xlsx"
    
    print(f"\n=== 엑셀 보고서 생성: {filename} ===")
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        
        # 각 단계별 결과 저장
        for phase_name, phase_data in results.items():
            if phase_data['df'] is not None and not phase_data['df'].empty:
                df = phase_data['df']
                
                # 체류시간 계산 추가
                df_with_stay = df.copy()
                stay_times = []
                
                for applicant_id in df['applicant_id'].unique():
                    applicant_df = df[df['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    stay_times.append(stay_hours)
                
                # 체류시간 통계 추가
                if stay_times:
                    df_with_stay['stay_hours'] = df_with_stay['applicant_id'].map(
                        dict(zip(df['applicant_id'].unique(), stay_times))
                    )
                
                df_with_stay.to_excel(writer, sheet_name=f'{phase_name}_스케줄', index=False)
                print(f"  - {phase_name}: {len(df_with_stay)}개 스케줄 저장")
        
        # 비교 분석 시트 생성
        comparison_data = []
        for phase_name, phase_data in results.items():
            if phase_data['df'] is not None and not phase_data['df'].empty:
                stay_times = analyze_stay_times(phase_data['df'])
                if stay_times:
                    comparison_data.append({
                        '단계': phase_name,
                        '최대체류시간': stay_times['max_stay'],
                        '평균체류시간': stay_times['avg_stay'],
                        '최소체류시간': stay_times['min_stay'],
                        '스케줄수': len(phase_data['df'])
                    })
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            comparison_df.to_excel(writer, sheet_name='단계별_비교', index=False)
            print(f"  - 단계별 비교: {len(comparison_data)}개 단계")
    
    print(f"✅ 엑셀 보고서 생성 완료: {filename}")
    return filename

if __name__ == "__main__":
    run_ui_three_phase_test() 