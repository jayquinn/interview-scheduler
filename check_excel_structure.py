#!/usr/bin/env python3
"""
Excel 파일 구조 확인 스크립트
"""

import pandas as pd

def check_excel_structure(filename):
    """Excel 파일 구조 확인"""
    print(f"📊 Excel 파일 구조 확인: {filename}")
    print("=" * 50)
    
    try:
        # 모든 시트 이름 확인
        xl_file = pd.ExcelFile(filename)
        print(f"시트 목록: {xl_file.sheet_names}")
        
        # Schedule 시트 확인
        if 'Schedule' in xl_file.sheet_names:
            df = pd.read_excel(filename, sheet_name='Schedule')
            print(f"\n📋 Schedule 시트:")
            print(f"  - 행 수: {len(df)}")
            print(f"  - 칼럼: {list(df.columns)}")
            print(f"  - 샘플 데이터:")
            print(df.head())
        
        # 다른 시트들도 확인
        for sheet_name in xl_file.sheet_names:
            if sheet_name != 'Schedule':
                df_sheet = pd.read_excel(filename, sheet_name=sheet_name)
                print(f"\n📋 {sheet_name} 시트:")
                print(f"  - 행 수: {len(df_sheet)}")
                print(f"  - 칼럼: {list(df_sheet.columns)}")
                
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    check_excel_structure("ui_format_cpsat_result_20250714_123241.xlsx") 