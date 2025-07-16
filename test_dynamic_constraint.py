#!/usr/bin/env python3
"""
실제 3단계 동적 제약 테스트
"""

import pandas as pd
import numpy as np
from datetime import timedelta

def test_dynamic_constraint():
    """실제 3단계 동적 제약 테스트"""
    
    print("=== 실제 3단계 동적 제약 테스트 ===")
    
    try:
        # 2단계 결과 읽기 (실제 3단계에서 사용하는 데이터)
        filename = "interview_schedule_20250716_145718.xlsx"
        
        # 2단계 결과가 없으므로, 3단계 결과에서 역산
        df_phase3 = pd.read_excel(filename, sheet_name='3단계_스케줄링_결과')
        df_phase3['interview_date'] = pd.to_datetime(df_phase3['interview_date'])
        
        print(f"3단계 결과 데이터: {len(df_phase3)}개 스케줄")
        
        # 2단계 결과 시뮬레이션 (실제로는 2단계 결과를 사용해야 함)
        print(f"\n=== 2단계 결과 시뮬레이션 ===")
        
        # 2단계 체류시간 계산 (실제로는 2단계 결과에서 가져와야 함)
        phase2_stay_times = []
        for applicant_id in df_phase3['applicant_id'].unique():
            applicant_df = df_phase3[df_phase3['applicant_id'] == applicant_id]
            start_time = applicant_df['start_time'].min()
            end_time = applicant_df['end_time'].max()
            stay_hours = (end_time - start_time).total_seconds() / 3600
            phase2_stay_times.append(stay_hours)
        
        # 2단계 백분위수 계산
        phase2_90th_percentile = np.percentile(phase2_stay_times, 90)
        phase2_80th_percentile = np.percentile(phase2_stay_times, 80)
        
        print(f"2단계 체류시간 통계:")
        print(f"  - 최대: {max(phase2_stay_times):.2f}시간")
        print(f"  - 90% 백분위수: {phase2_90th_percentile:.2f}시간")
        print(f"  - 80% 백분위수: {phase2_80th_percentile:.2f}시간")
        
        # 실제 3단계에서 사용하는 동적 제약
        dynamic_constraint = phase2_80th_percentile
        print(f"\n실제 3단계 동적 제약: {dynamic_constraint:.2f}시간 (2단계 80% 백분위수)")
        
        # 3단계 결과에 동적 제약 후처리 적용
        print(f"\n=== 동적 제약 후처리 적용 ===")
        
        from test_internal_analysis import apply_hard_constraint_postprocessing
        
        # 실제 동적 제약으로 후처리 적용
        df_processed = apply_hard_constraint_postprocessing(df_phase3, dynamic_constraint)
        
        if df_processed is not None:
            print(f"후처리 완료: {len(df_processed)}개 스케줄")
            
            # 후처리 후 체류시간 분석
            print(f"\n=== 후처리 후 체류시간 분석 ===")
            stay_times_processed = []
            for applicant_id in df_processed['applicant_id'].unique():
                applicant_df = df_processed[df_processed['applicant_id'] == applicant_id]
                start_time = applicant_df['start_time'].min()
                end_time = applicant_df['end_time'].max()
                stay_hours = (end_time - start_time).total_seconds() / 3600
                stay_times_processed.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
            
            stay_times_processed.sort(key=lambda x: x['stay_hours'], reverse=True)
            print(f"후처리 최대 체류시간: {stay_times_processed[0]['stay_hours']:.2f}시간 ({stay_times_processed[0]['applicant_id']})")
            
            # 상위 5개 체류시간
            print("후처리 상위 5개 체류시간:")
            for i, stay in enumerate(stay_times_processed[:5]):
                print(f"  {i+1}. {stay['applicant_id']}: {stay['stay_hours']:.2f}시간")
            
            # 동적 제약 준수 여부 확인
            print(f"\n=== 동적 제약 준수 여부 ===")
            print(f"동적 제약: {dynamic_constraint:.2f}시간")
            print(f"실제 최대: {stay_times_processed[0]['stay_hours']:.2f}시간")
            
            if stay_times_processed[0]['stay_hours'] <= dynamic_constraint:
                print(f"✅ 동적 제약 준수: {stay_times_processed[0]['stay_hours']:.2f}시간 <= {dynamic_constraint:.2f}시간")
            else:
                print(f"❌ 동적 제약 위반: {stay_times_processed[0]['stay_hours']:.2f}시간 > {dynamic_constraint:.2f}시간")
            
            # JOB02_005 응시자 확인
            print(f"\n=== JOB02_005 응시자 확인 ===")
            job02_005_processed = next((stay for stay in stay_times_processed if stay['applicant_id'] == 'JOB02_005'), None)
            
            if job02_005_processed:
                print(f"JOB02_005 체류시간: {job02_005_processed['stay_hours']:.2f}시간")
                
                if job02_005_processed['stay_hours'] <= dynamic_constraint:
                    print(f"✅ JOB02_005 동적 제약 준수")
                else:
                    print(f"❌ JOB02_005 동적 제약 위반")
            
            # 결과 저장
            output_filename = f"dynamic_constraint_test_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
                df_phase3.to_excel(writer, sheet_name='원본_3단계_결과', index=False)
                df_processed.to_excel(writer, sheet_name='동적제약_후처리_결과', index=False)
                
                # 제약 정보
                constraint_info = pd.DataFrame([{
                    '구분': '동적 제약',
                    '값': f"{dynamic_constraint:.2f}시간",
                    '설명': '2단계 80% 백분위수'
                }])
                constraint_info.to_excel(writer, sheet_name='제약_정보', index=False)
            
            print(f"\n결과 저장: {output_filename}")
            
        else:
            print("❌ 후처리 실패")
            
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dynamic_constraint() 