import pandas as pd

print("=== 3단계 체류시간 상세 분석 ===")

try:
    filename = "interview_schedule_20250716_145718.xlsx"
    
    # 3단계 체류시간 분석 시트 읽기
    df_stay = pd.read_excel(filename, sheet_name='3단계_체류시간_분석')
    print(f"3단계 체류시간 분석: {len(df_stay)}명")
    
    # 체류시간 통계
    stay_hours = df_stay['체류시간(시간)']
    print(f"\n체류시간 통계:")
    print(f"  - 최대: {stay_hours.max():.2f}시간")
    print(f"  - 평균: {stay_hours.mean():.2f}시간")
    print(f"  - 최소: {stay_hours.min():.2f}시간")
    print(f"  - 표준편차: {stay_hours.std():.2f}시간")
    
    # 상위 10개 체류시간
    print(f"\n상위 10개 체류시간:")
    top_10 = df_stay.nlargest(10, '체류시간(시간)')
    for i, row in top_10.iterrows():
        print(f"  {i+1}. {row['응시자ID']}: {row['체류시간(시간)']:.2f}시간 ({row['날짜']})")
    
    # 4.5시간 이상 체류자 확인
    over_4_5 = df_stay[df_stay['체류시간(시간)'] >= 4.5]
    if len(over_4_5) > 0:
        print(f"\n⚠️ 4.5시간 이상 체류자: {len(over_4_5)}명")
        for i, row in over_4_5.iterrows():
            print(f"  - {row['응시자ID']}: {row['체류시간(시간)']:.2f}시간 ({row['날짜']})")
    else:
        print(f"\n✅ 4.5시간 이상 체류자 없음")
    
    # StayTime_Analysis 시트도 확인
    print(f"\n=== 전체 체류시간 통계 ===")
    df_stats = pd.read_excel(filename, sheet_name='StayTime_Analysis')
    print(df_stats.to_string(index=False))
    
    # 3단계 스케줄링 결과 시트 확인
    print(f"\n=== 3단계 스케줄링 결과 ===")
    df_schedule = pd.read_excel(filename, sheet_name='3단계_스케줄링_결과')
    print(f"스케줄 수: {len(df_schedule)}개")
    
    # 체류시간 계산
    df_schedule['interview_date'] = pd.to_datetime(df_schedule['interview_date'])
    stay_times = []
    
    for applicant_id in df_schedule['applicant_id'].unique():
        applicant_df = df_schedule[df_schedule['applicant_id'] == applicant_id]
        start_time = applicant_df['start_time'].min()
        end_time = applicant_df['end_time'].max()
        stay_hours = (end_time - start_time).total_seconds() / 3600
        stay_times.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
    
    if stay_times:
        stay_times.sort(key=lambda x: x['stay_hours'], reverse=True)
        print(f"\n3단계 스케줄링 결과에서 계산한 체류시간:")
        print(f"  - 최대: {stay_times[0]['stay_hours']:.2f}시간 ({stay_times[0]['applicant_id']})")
        print(f"  - 상위 5개:")
        for i, stay in enumerate(stay_times[:5]):
            print(f"    {i+1}. {stay['applicant_id']}: {stay['stay_hours']:.2f}시간")
    
except Exception as e:
    print(f"오류: {e}")
    import traceback
    traceback.print_exc() 