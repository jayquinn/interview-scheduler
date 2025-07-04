#!/usr/bin/env python3
"""
엑셀 파일 구조 확인
"""

import pandas as pd

def check_data_structure():
    """데이터 구조 확인"""
    try:
        df = pd.read_excel('complete_ui_defaults_test_result.xlsx')
        print(f"✅ 데이터 로드: {len(df)}개 항목")
        
        print(f"\n📋 컬럼 정보:")
        print(f"컬럼 수: {len(df.columns)}")
        print(f"컬럼명:")
        for i, col in enumerate(df.columns):
            print(f"  {i+1}. '{col}'")
        
        print(f"\n📊 데이터 샘플 (첫 5개 행):")
        print(df.head())
        
        print(f"\n🔍 토론면접 관련 데이터:")
        discussion_mask = df['activity_name'].str.contains('토론', na=False)
        discussion_data = df[discussion_mask]
        print(f"토론면접 항목 수: {len(discussion_data)}")
        
        if len(discussion_data) > 0:
            print(f"\n토론면접 샘플:")
            print(discussion_data.head())
        
    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    check_data_structure() 