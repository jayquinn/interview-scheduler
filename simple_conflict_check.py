#!/usr/bin/env python3
"""간단한 시간 충돌 체크"""
import pandas as pd
from datetime import timedelta

# 예상 데이터로 직접 테스트
data = [
    # 토론면접 (6명이 모두 같은 시간)
    {'applicant_id': 'JOB01_001', 'activity_name': '토론면접', 'room_name': '토론면접실A', 'start_time': timedelta(hours=9), 'end_time': timedelta(hours=9, minutes=30)},
    {'applicant_id': 'JOB01_002', 'activity_name': '토론면접', 'room_name': '토론면접실A', 'start_time': timedelta(hours=9), 'end_time': timedelta(hours=9, minutes=30)},
    {'applicant_id': 'JOB01_003', 'activity_name': '토론면접', 'room_name': '토론면접실A', 'start_time': timedelta(hours=9), 'end_time': timedelta(hours=9, minutes=30)},
    {'applicant_id': 'JOB01_004', 'activity_name': '토론면접', 'room_name': '토론면접실A', 'start_time': timedelta(hours=9), 'end_time': timedelta(hours=9, minutes=30)},
    {'applicant_id': 'JOB01_005', 'activity_name': '토론면접', 'room_name': '토론면접실A', 'start_time': timedelta(hours=9), 'end_time': timedelta(hours=9, minutes=30)},
    {'applicant_id': 'JOB01_006', 'activity_name': '토론면접', 'room_name': '토론면접실A', 'start_time': timedelta(hours=9), 'end_time': timedelta(hours=9, minutes=30)},
    
    # 발표준비+발표면접 (Individual 스케줄링)
    {'applicant_id': 'JOB01_001', 'activity_name': '발표준비+발표면접', 'room_name': '발표면접실A', 'start_time': timedelta(hours=9), 'end_time': timedelta(hours=9, minutes=20)},
    {'applicant_id': 'JOB01_002', 'activity_name': '발표준비+발표면접', 'room_name': '발표면접실B', 'start_time': timedelta(hours=9), 'end_time': timedelta(hours=9, minutes=20)},
]

df = pd.DataFrame(data)

print("📊 테스트 데이터:")
print(df[['applicant_id', 'activity_name', 'room_name', 'start_time', 'end_time']])

print("\n🔍 시간 충돌 확인:")
conflicts = []

for applicant_id in df['applicant_id'].unique():
    applicant_df = df[df['applicant_id'] == applicant_id]
    
    for i in range(len(applicant_df)):
        for j in range(i+1, len(applicant_df)):
            row1 = applicant_df.iloc[i]
            row2 = applicant_df.iloc[j]
            
            start1, end1 = row1['start_time'], row1['end_time']
            start2, end2 = row2['start_time'], row2['end_time']
            
            # 시간 겹침 확인
            if not (end1 <= start2 or start1 >= end2):
                print(f"❌ {applicant_id}: {row1['activity_name']}({row1['room_name']}) {start1}~{end1} ↔ {row2['activity_name']}({row2['room_name']}) {start2}~{end2}")
                conflicts.append(applicant_id)

if not conflicts:
    print("✅ 시간 충돌 없음")

print(f"\n총 충돌 건수: {len(conflicts)}")

# 이제 app.py의 변환 함수를 시뮬레이션
print("\n" + "="*50)
print("🔧 이중 스케줄 변환 시뮬레이션")
print("="*50)

converted_data = []
for _, row in df.iterrows():
    if '+' in row['activity_name']:
        # 발표준비+발표면접 → 발표준비 + 발표면접
        parts = row['activity_name'].split('+')
        prep_name = parts[0].strip()
        interview_name = parts[1].strip()
        
        # 발표준비 (5분)
        prep_row = row.copy()
        prep_row['activity_name'] = prep_name
        prep_row['room_name'] = '발표준비실'
        prep_row['end_time'] = prep_row['start_time'] + timedelta(minutes=5)
        
        # 발표면접 (발표준비 직후 시작)
        interview_row = row.copy()
        interview_row['activity_name'] = interview_name
        interview_row['start_time'] = prep_row['end_time']
        # end_time은 원본 유지
        
        converted_data.extend([prep_row, interview_row])
        print(f"분리: {row['applicant_id']} - {row['activity_name']} → {prep_name} + {interview_name}")
    else:
        converted_data.append(row)

converted_df = pd.DataFrame(converted_data)

print("\n📊 변환 후 데이터:")
print(converted_df[['applicant_id', 'activity_name', 'room_name', 'start_time', 'end_time']])

print("\n🔍 변환 후 시간 충돌 확인:")
converted_conflicts = []

for applicant_id in converted_df['applicant_id'].unique():
    applicant_df = converted_df[converted_df['applicant_id'] == applicant_id]
    
    for i in range(len(applicant_df)):
        for j in range(i+1, len(applicant_df)):
            row1 = applicant_df.iloc[i]
            row2 = applicant_df.iloc[j]
            
            start1, end1 = row1['start_time'], row1['end_time']
            start2, end2 = row2['start_time'], row2['end_time']
            
            # 시간 겹침 확인
            if not (end1 <= start2 or start1 >= end2):
                print(f"❌ {applicant_id}: {row1['activity_name']}({row1['room_name']}) {start1}~{end1} ↔ {row2['activity_name']}({row2['room_name']}) {start2}~{end2}")
                converted_conflicts.append(applicant_id)

if not converted_conflicts:
    print("✅ 변환 후 시간 충돌 없음")

print(f"\n변환 후 총 충돌 건수: {len(converted_conflicts)}") 