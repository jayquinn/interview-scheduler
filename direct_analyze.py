#!/usr/bin/env python3
"""
직접 엑셀 파일 분석
"""

import pandas as pd
import numpy as np

# 파일명
filename = "interview_schedule_20250716_145718.xlsx"

print(f"=== 엑셀 파일 분석: {filename} ===")

try:
    # 엑셀 파일의 모든 시트 읽기
    excel_file = pd.ExcelFile(filename)
    print(f"시트 목록: {excel_file.sheet_names}")
    
    # 각 시트 분석
    for sheet_name in excel_file.sheet_names:
        print(f"\n--- {sheet_name} ---")
        
        df = pd.read_excel(filename, sheet_name=sheet_name)
        print(f"행 수: {len(df)}")
        print(f"컬럼: {list(df.columns)}")
        
        if 'stay_hours' in df.columns:
            stay_hours = df['stay_hours'].dropna()
            if len(stay_hours) > 0:
                print(f"체류시간 통계:")
                print(f"  - 최대: {stay_hours.max():.2f}시간")
                print(f"  - 평균: {stay_hours.mean():.2f}시간")
                print(f"  - 최소: {stay_hours.min():.2f}시간")
                print(f"  - 표준편차: {stay_hours.std():.2f}시간")
                
                # 상위 5개 체류시간
                top_5 = stay_hours.nlargest(5)
                print(f"  - 상위 5개 체류시간:")
                for i, (idx, value) in enumerate(top_5.items()):
                    applicant_id = df.loc[idx, 'applicant_id'] if 'applicant_id' in df.columns else f"응시자_{idx}"
                    print(f"    {i+1}. {applicant_id}: {value:.2f}시간")
        
        # 처음 3행 출력
        print("처음 3행:")
        print(df.head(3))
        
    # 단계별 비교 분석
    print(f"\n=== 단계별 비교 분석 ===")
    
    try:
        comparison_df = pd.read_excel(filename, sheet_name='단계별_비교')
        
        print("\n단계별 체류시간 비교:")
        print(comparison_df.to_string(index=False))
        
        # 개선 효과 계산
        if len(comparison_df) >= 3:
            phase1_max = comparison_df[comparison_df['단계'] == 'phase1']['최대체류시간'].iloc[0]
            phase2_max = comparison_df[comparison_df['단계'] == 'phase2']['최대체류시간'].iloc[0]
            phase3_max = comparison_df[comparison_df['단계'] == 'phase3']['최대체류시간'].iloc[0]
            
            print(f"\n개선 효과:")
            print(f"  1단계 → 2단계: {phase1_max - phase2_max:.2f}시간 ({((phase1_max - phase2_max) / phase1_max * 100):.1f}%)")
            print(f"  1단계 → 3단계: {phase1_max - phase3_max:.2f}시간 ({((phase1_max - phase3_max) / phase1_max * 100):.1f}%)")
            print(f"  2단계 → 3단계: {phase2_max - phase3_max:.2f}시간 ({((phase2_max - phase3_max) / phase1_max * 100):.1f}%)")
            
            # 4.5시간 문제 확인
            if phase3_max > 4.0:
                print(f"\n⚠️ 3단계에서 여전히 높은 체류시간 발견: {phase3_max:.2f}시간")
                print(f"🔍 원인 분석:")
                if phase3_max == phase1_max:
                    print(f"  - 3단계가 1단계와 동일한 결과 (fallback 발생 가능성)")
                if phase3_max > phase2_max:
                    print(f"  - 3단계가 2단계보다 악화됨 (제약 미적용)")
                print(f"  - 하드 제약 후처리가 제대로 동작하지 않았을 가능성")
            else:
                print(f"\n✅ 3단계 체류시간 개선됨: {phase3_max:.2f}시간")
        
    except Exception as e:
        print(f"비교 분석 오류: {str(e)}")
        
except Exception as e:
    print(f"오류 발생: {str(e)}")
    import traceback
    traceback.print_exc() 