import pandas as pd
from datetime import timedelta

print("=== JOB02_005 응시자 3단계 스케줄 분석 ===")

try:
    filename = "interview_schedule_20250716_145718.xlsx"
    
    # 3단계 스케줄링 결과 읽기
    df_schedule = pd.read_excel(filename, sheet_name='3단계_스케줄링_결과')
    df_schedule['interview_date'] = pd.to_datetime(df_schedule['interview_date'])
    
    # JOB02_005 응시자 스케줄 확인
    job02_005_schedule = df_schedule[df_schedule['applicant_id'] == 'JOB02_005']
    
    print(f"JOB02_005 응시자 스케줄:")
    print(f"총 스케줄 수: {len(job02_005_schedule)}개")
    
    for i, row in job02_005_schedule.iterrows():
        print(f"  {i+1}. {row['activity_name']}: {row['start_time']} ~ {row['end_time']} ({row['room_name']})")
    
    # 체류시간 계산
    start_time = job02_005_schedule['start_time'].min()
    end_time = job02_005_schedule['end_time'].max()
    stay_hours = (end_time - start_time).total_seconds() / 3600
    
    print(f"\n체류시간 분석:")
    print(f"  - 시작: {start_time}")
    print(f"  - 종료: {end_time}")
    print(f"  - 체류시간: {stay_hours:.2f}시간")
    
    # 발표면접 활동 찾기
    presentation_schedules = job02_005_schedule[
        job02_005_schedule['activity_name'].str.contains('발표면접', na=False)
    ]
    
    print(f"\n발표면접 활동:")
    if len(presentation_schedules) > 0:
        for i, row in presentation_schedules.iterrows():
            print(f"  - {row['start_time']} ~ {row['end_time']} ({row['room_name']})")
    else:
        print("  - 발표면접 활동 없음")
    
    # 토론면접 활동 찾기
    discussion_schedules = job02_005_schedule[
        job02_005_schedule['activity_name'].str.contains('토론면접', na=False)
    ]
    
    print(f"\n토론면접 활동:")
    if len(discussion_schedules) > 0:
        for i, row in discussion_schedules.iterrows():
            print(f"  - {row['start_time']} ~ {row['end_time']} ({row['room_name']})")
    else:
        print("  - 토론면접 활동 없음")
    
    # 개선 방안 제시
    print(f"\n=== 개선 방안 ===")
    
    if stay_hours > 3.5:  # 3단계 하드 제약
        excess_hours = stay_hours - 3.5
        print(f"현재 체류시간: {stay_hours:.2f}시간 (제약: 3.5시간)")
        print(f"초과 시간: {excess_hours:.2f}시간")
        
        if len(presentation_schedules) > 0:
            print(f"발표면접 시간을 {excess_hours:.2f}시간 앞당겨야 함")
            
            # 개선된 스케줄 계산
            for i, row in presentation_schedules.iterrows():
                current_start = row['start_time']
                current_end = row['end_time']
                duration = current_end - current_start
                
                new_start = current_start - timedelta(hours=excess_hours)
                new_end = new_start + duration
                
                print(f"  개선안: {current_start} → {new_start} (앞당김: {excess_hours:.2f}시간)")
        else:
            print("발표면접 활동이 없어 시간 조정이 어려움")
    
except Exception as e:
    print(f"오류: {e}")
    import traceback
    traceback.print_exc() 