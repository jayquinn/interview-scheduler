#!/usr/bin/env python3
"""
스케줄 결과 데이터 구조 확인
"""

import pandas as pd

def main():
    try:
        df = pd.read_excel("complete_ui_defaults_test_result.xlsx")
        print(f"데이터 크기: {df.shape}")
        print(f"컬럼: {list(df.columns)}")
        
        print("\n첫 5행:")
        print(df.head())
        
        print("\n각 컬럼의 데이터 타입:")
        print(df.dtypes)
        
        print("\n시간 컬럼 샘플 데이터:")
        for col in ['start_time', 'end_time']:
            if col in df.columns:
                print(f"\n{col} 샘플:")
                sample_values = df[col].dropna().head(10)
                for i, val in enumerate(sample_values):
                    print(f"  {i+1}: {val} (타입: {type(val)})")
        
        print("\n지원자별 활동 수:")
        applicant_counts = df.groupby('applicant_id').size()
        print(f"평균 활동 수: {applicant_counts.mean():.1f}")
        print(f"최소 활동 수: {applicant_counts.min()}")
        print(f"최대 활동 수: {applicant_counts.max()}")
        
        print("\n지원자 샘플 (JOB01_001):")
        sample_applicant = df[df['applicant_id'] == 'JOB01_001']
        if not sample_applicant.empty:
            print(sample_applicant.to_string(index=False))
        
    except Exception as e:
        print(f"에러: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 