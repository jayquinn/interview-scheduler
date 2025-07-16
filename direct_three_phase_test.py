#!/usr/bin/env python3
"""
직접 3단계 스케줄링 실행 및 분석
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_three_phase_direct():
    """직접 3단계 스케줄링 테스트"""
    
    print("=== 직접 3단계 스케줄링 테스트 ===")
    
    try:
        # test_internal_analysis에서 3단계 스케줄링 실행
        from test_internal_analysis import run_multi_date_scheduling
        
        print("3단계 스케줄링 실행 중...")
        results = run_multi_date_scheduling()
        
        if results:
            print("✅ 3단계 스케줄링 성공!")
            
            # 결과 분석
            analyze_results_direct(results)
            
            # 엑셀 저장
            save_results_to_excel(results)
            
        else:
            print("❌ 3단계 스케줄링 실패!")
            
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_results_direct(results):
    """결과 직접 분석"""
    
    print("\n=== 결과 분석 ===")
    
    for phase_name, phase_data in results.items():
        print(f"\n--- {phase_name} ---")
        print(f"상태: {phase_data['status']}")
        
        if phase_data['df'] is not None and not phase_data['df'].empty:
            df = phase_data['df']
            print(f"스케줄 수: {len(df)}개")
            
            # 체류시간 계산
            stay_times = []
            for applicant_id in df['applicant_id'].unique():
                applicant_df = df[df['applicant_id'] == applicant_id]
                start_time = applicant_df['start_time'].min()
                end_time = applicant_df['end_time'].max()
                stay_hours = (end_time - start_time).total_seconds() / 3600
                stay_times.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
            
            if stay_times:
                stay_times.sort(key=lambda x: x['stay_hours'], reverse=True)
                max_stay = stay_times[0]['stay_hours']
                avg_stay = sum(s['stay_hours'] for s in stay_times) / len(stay_times)
                
                print(f"최대 체류시간: {max_stay:.2f}시간 ({stay_times[0]['applicant_id']})")
                print(f"평균 체류시간: {avg_stay:.2f}시간")
                
                print("상위 5개 체류시간:")
                for i, stay in enumerate(stay_times[:5]):
                    print(f"  {i+1}. {stay['applicant_id']}: {stay['stay_hours']:.2f}시간")
        else:
            print("데이터 없음")

def save_results_to_excel(results):
    """결과를 엑셀로 저장"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"direct_three_phase_test_{timestamp}.xlsx"
    
    print(f"\n=== 엑셀 저장: {filename} ===")
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        
        # 각 단계별 결과 저장
        for phase_name, phase_data in results.items():
            if phase_data['df'] is not None and not phase_data['df'].empty:
                df = phase_data['df']
                
                # 체류시간 계산 추가
                stay_times = {}
                for applicant_id in df['applicant_id'].unique():
                    applicant_df = df[df['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    stay_times[applicant_id] = stay_hours
                
                df_with_stay = df.copy()
                df_with_stay['stay_hours'] = df_with_stay['applicant_id'].map(stay_times)
                
                sheet_name = f'{phase_name}_스케줄'
                df_with_stay.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  - {sheet_name}: {len(df_with_stay)}개 스케줄")
        
        # 비교 분석
        comparison_data = []
        for phase_name, phase_data in results.items():
            if phase_data['df'] is not None and not phase_data['df'].empty:
                df = phase_data['df']
                stay_times = []
                
                for applicant_id in df['applicant_id'].unique():
                    applicant_df = df[df['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    stay_times.append(stay_hours)
                
                if stay_times:
                    comparison_data.append({
                        '단계': phase_name,
                        '최대체류시간': max(stay_times),
                        '평균체류시간': sum(stay_times) / len(stay_times),
                        '최소체류시간': min(stay_times),
                        '스케줄수': len(df)
                    })
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            comparison_df.to_excel(writer, sheet_name='단계별_비교', index=False)
            print(f"  - 단계별_비교: {len(comparison_data)}개 단계")
    
    print(f"✅ 엑셀 저장 완료: {filename}")
    return filename

if __name__ == "__main__":
    test_three_phase_direct() 