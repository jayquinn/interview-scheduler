#!/usr/bin/env python3
"""
TS_날짜 시트명 구조의 엑셀 결과 파일 생성
시간대별 타임슬롯 구조로 방 정보를 여러 칼럼으로 배치
"""

import pandas as pd
from datetime import datetime, time, timedelta
import os

def create_timeslot_excel():
    """TS_날짜 시트명 구조의 타임슬롯 엑셀 생성"""
    
    # 기본 스케줄 데이터
    schedule_data = [
        {'applicant_id': 'JOB01_001', 'activity': '발표준비', 'room': '발표준비실', 'start': '09:30', 'end': '09:35'},
        {'applicant_id': 'JOB01_002', 'activity': '발표준비', 'room': '발표준비실', 'start': '09:30', 'end': '09:35'},
        {'applicant_id': 'JOB01_003', 'activity': '발표준비', 'room': '발표준비실', 'start': '09:30', 'end': '09:35'},
        {'applicant_id': 'JOB01_004', 'activity': '발표준비', 'room': '발표준비실', 'start': '09:30', 'end': '09:35'},
        {'applicant_id': 'JOB01_005', 'activity': '발표준비', 'room': '발표준비실', 'start': '09:30', 'end': '09:35'},
        {'applicant_id': 'JOB01_006', 'activity': '발표준비', 'room': '발표준비실', 'start': '09:30', 'end': '09:35'},
        
        {'applicant_id': 'JOB01_001', 'activity': '발표면접', 'room': '발표면접실A', 'start': '09:40', 'end': '09:55'},
        {'applicant_id': 'JOB01_002', 'activity': '발표면접', 'room': '발표면접실B', 'start': '09:40', 'end': '09:55'},
        {'applicant_id': 'JOB01_003', 'activity': '발표면접', 'room': '발표면접실A', 'start': '09:55', 'end': '10:10'},
        {'applicant_id': 'JOB01_004', 'activity': '발표면접', 'room': '발표면접실B', 'start': '09:55', 'end': '10:10'},
        {'applicant_id': 'JOB01_005', 'activity': '발표면접', 'room': '발표면접실A', 'start': '10:10', 'end': '10:25'},
        {'applicant_id': 'JOB01_006', 'activity': '발표면접', 'room': '발표면접실B', 'start': '10:10', 'end': '10:25'},
        
        {'applicant_id': 'JOB01_001', 'activity': '토론면접', 'room': '토론면접실A', 'start': '09:00', 'end': '09:30'},
        {'applicant_id': 'JOB01_002', 'activity': '토론면접', 'room': '토론면접실A', 'start': '09:05', 'end': '09:35'},
        {'applicant_id': 'JOB01_003', 'activity': '토론면접', 'room': '토론면접실A', 'start': '09:10', 'end': '09:40'},
        {'applicant_id': 'JOB01_004', 'activity': '토론면접', 'room': '토론면접실A', 'start': '09:15', 'end': '09:45'},
        {'applicant_id': 'JOB01_005', 'activity': '토론면접', 'room': '토론면접실A', 'start': '09:20', 'end': '09:50'},
        {'applicant_id': 'JOB01_006', 'activity': '토론면접', 'room': '토론면접실A', 'start': '09:25', 'end': '09:55'},
    ]
    
    # 시간대 생성 (5분 단위, 09:00~10:30)
    time_slots = []
    start_time = datetime.strptime('09:00', '%H:%M')
    end_time = datetime.strptime('10:30', '%H:%M')
    
    current_time = start_time
    while current_time <= end_time:
        time_slots.append(current_time.strftime('%H:%M'))
        current_time += timedelta(minutes=5)
    
    # 방 목록
    rooms = ['발표면접실A', '발표면접실B', '발표준비실', '토론면접실A']
    
    # 날짜 (시트명용)
    date_str = '2024-01-15'
    sheet_name = f"TS_{date_str}"
    
    # 엑셀 파일 생성
    filename = "simple_test_result.xlsx"
    
    # 시간대별 데이터프레임 생성
    df = pd.DataFrame({'Time': time_slots})
    
    # 각 방별로 칼럼 추가
    for room in rooms:
        room_schedule = []
        for time_slot in time_slots:
            activity_found = False
            for schedule in schedule_data:
                if schedule['room'] == room:
                    start_time = datetime.strptime(schedule['start'], '%H:%M')
                    end_time = datetime.strptime(schedule['end'], '%H:%M')
                    current_time = datetime.strptime(time_slot, '%H:%M')
                    
                    if start_time <= current_time < end_time:
                        room_schedule.append(schedule['applicant_id'])
                        activity_found = True
                        break
            
            if not activity_found:
                room_schedule.append('')
        
        df[room] = room_schedule
    
    # 엑셀로 저장
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"✅ 시트 생성: {sheet_name}")
    print(f"✅ 엑셀 파일 생성 완료: {filename}")
    print(f"📁 저장 위치: {os.path.abspath(filename)}")
    print(f"📊 데이터 크기: {df.shape}")
    print(f"🏠 방 개수: {len(rooms)}개")
    
    # 데이터 미리보기
    print(f"\n📋 데이터 미리보기:")
    print(df.head())
    
    return filename

if __name__ == "__main__":
    create_timeslot_excel() 