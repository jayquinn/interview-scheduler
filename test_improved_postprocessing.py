#!/usr/bin/env python3
"""
개선된 하드 제약 후처리 함수 테스트
"""

import pandas as pd
from datetime import timedelta

def test_improved_postprocessing():
    """개선된 후처리 함수 테스트"""
    
    print("=== 개선된 하드 제약 후처리 테스트 ===")
    
    try:
        # 기존 3단계 결과 읽기
        filename = "interview_schedule_20250716_145718.xlsx"
        df_original = pd.read_excel(filename, sheet_name='3단계_스케줄링_결과')
        df_original['interview_date'] = pd.to_datetime(df_original['interview_date'])
        
        print(f"원본 데이터: {len(df_original)}개 스케줄")
        
        # 원본 체류시간 분석
        print(f"\n=== 원본 체류시간 분석 ===")
        stay_times = []
        for applicant_id in df_original['applicant_id'].unique():
            applicant_df = df_original[df_original['applicant_id'] == applicant_id]
            start_time = applicant_df['start_time'].min()
            end_time = applicant_df['end_time'].max()
            stay_hours = (end_time - start_time).total_seconds() / 3600
            stay_times.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
        
        stay_times.sort(key=lambda x: x['stay_hours'], reverse=True)
        print(f"원본 최대 체류시간: {stay_times[0]['stay_hours']:.2f}시간 ({stay_times[0]['applicant_id']})")
        
        # 상위 5개 체류시간
        print("원본 상위 5개 체류시간:")
        for i, stay in enumerate(stay_times[:5]):
            print(f"  {i+1}. {stay['applicant_id']}: {stay['stay_hours']:.2f}시간")
        
        # 개선된 후처리 함수 적용
        print(f"\n=== 개선된 후처리 적용 ===")
        
        # test_internal_analysis에서 함수 import
        from test_internal_analysis import apply_hard_constraint_postprocessing
        
        # 3.5시간 제약으로 후처리 적용
        df_processed = apply_hard_constraint_postprocessing(df_original, 3.5)
        
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
            
            # 개선 효과 확인
            print(f"\n=== 개선 효과 ===")
            original_max = stay_times[0]['stay_hours']
            processed_max = stay_times_processed[0]['stay_hours']
            
            if processed_max <= 3.5:
                print(f"✅ 후처리 성공: {original_max:.2f}시간 → {processed_max:.2f}시간")
                print(f"   개선: {original_max - processed_max:.2f}시간 ({((original_max - processed_max) / original_max * 100):.1f}%)")
            else:
                print(f"❌ 후처리 실패: {original_max:.2f}시간 → {processed_max:.2f}시간")
                print(f"   여전히 제약 위반: {processed_max:.2f}시간 > 3.5시간")
            
            # JOB02_005 응시자 상세 분석
            print(f"\n=== JOB02_005 응시자 상세 분석 ===")
            job02_005_original = next((stay for stay in stay_times if stay['applicant_id'] == 'JOB02_005'), None)
            job02_005_processed = next((stay for stay in stay_times_processed if stay['applicant_id'] == 'JOB02_005'), None)
            
            if job02_005_original and job02_005_processed:
                print(f"JOB02_005 체류시간: {job02_005_original['stay_hours']:.2f}시간 → {job02_005_processed['stay_hours']:.2f}시간")
                
                if job02_005_processed['stay_hours'] <= 3.5:
                    print(f"✅ JOB02_005 제약 준수")
                else:
                    print(f"❌ JOB02_005 여전히 제약 위반")
            
            # 결과 저장
            output_filename = f"improved_postprocessing_test_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
                df_original.to_excel(writer, sheet_name='원본_3단계_결과', index=False)
                df_processed.to_excel(writer, sheet_name='후처리_3단계_결과', index=False)
                
                # 체류시간 비교
                comparison_data = []
                for i, stay in enumerate(stay_times[:10]):  # 상위 10개
                    processed_stay = next((s for s in stay_times_processed if s['applicant_id'] == stay['applicant_id']), None)
                    if processed_stay:
                        comparison_data.append({
                            '응시자ID': stay['applicant_id'],
                            '원본체류시간': stay['stay_hours'],
                            '후처리체류시간': processed_stay['stay_hours'],
                            '개선시간': stay['stay_hours'] - processed_stay['stay_hours']
                        })
                
                comparison_df = pd.DataFrame(comparison_data)
                comparison_df.to_excel(writer, sheet_name='체류시간_비교', index=False)
            
            print(f"\n결과 저장: {output_filename}")
            
        else:
            print("❌ 후처리 실패")
            
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_improved_postprocessing() 