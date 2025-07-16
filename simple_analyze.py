import pandas as pd

print("=== 엑셀 파일 분석 시작 ===")

try:
    # 파일 읽기
    filename = "interview_schedule_20250716_145718.xlsx"
    print(f"파일: {filename}")
    
    # 시트 목록 확인
    excel_file = pd.ExcelFile(filename)
    print(f"시트: {excel_file.sheet_names}")
    
    # 각 시트 분석
    for sheet_name in excel_file.sheet_names:
        print(f"\n--- {sheet_name} ---")
        df = pd.read_excel(filename, sheet_name=sheet_name)
        print(f"행: {len(df)}, 컬럼: {list(df.columns)}")
        
        if 'stay_hours' in df.columns:
            stay_hours = df['stay_hours'].dropna()
            if len(stay_hours) > 0:
                print(f"최대 체류시간: {stay_hours.max():.2f}시간")
                print(f"평균 체류시간: {stay_hours.mean():.2f}시간")
                
                # 상위 3개
                top_3 = stay_hours.nlargest(3)
                print("상위 3개 체류시간:")
                for i, (idx, value) in enumerate(top_3.items()):
                    applicant_id = df.loc[idx, 'applicant_id'] if 'applicant_id' in df.columns else f"응시자_{idx}"
                    print(f"  {i+1}. {applicant_id}: {value:.2f}시간")
    
    # 단계별 비교
    print(f"\n=== 단계별 비교 ===")
    comparison_df = pd.read_excel(filename, sheet_name='단계별_비교')
    print(comparison_df.to_string(index=False))
    
    # 3단계 문제 확인
    if len(comparison_df) >= 3:
        phase1_max = comparison_df[comparison_df['단계'] == 'phase1']['최대체류시간'].iloc[0]
        phase2_max = comparison_df[comparison_df['단계'] == 'phase2']['최대체류시간'].iloc[0]
        phase3_max = comparison_df[comparison_df['단계'] == 'phase3']['최대체류시간'].iloc[0]
        
        print(f"\n3단계 문제 분석:")
        print(f"  1단계: {phase1_max:.2f}시간")
        print(f"  2단계: {phase2_max:.2f}시간")
        print(f"  3단계: {phase3_max:.2f}시간")
        
        if phase3_max > 4.0:
            print(f"⚠️ 3단계에서 4.5시간 문제 발견!")
            if phase3_max == phase1_max:
                print("  - 3단계가 1단계와 동일 (fallback 발생)")
            if phase3_max > phase2_max:
                print("  - 3단계가 2단계보다 악화 (제약 미적용)")
        else:
            print("✅ 3단계 체류시간 개선됨")
            
except Exception as e:
    print(f"오류: {e}")
    import traceback
    traceback.print_exc() 