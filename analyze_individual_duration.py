#!/usr/bin/env python3
"""
5분 단위가 아닌 종료시간의 duration 분포 분석
"""

import pandas as pd

filename = "interview_schedule_20250716_151143.xlsx"
df = pd.read_excel(filename, sheet_name='Individual_StayTime')

print("=== 5분 단위가 아닌 종료시간의 duration(분) 분포 분석 ===")
non_5min_rows = []
for i, row in df.iterrows():
    t = row['종료시간']
    try:
        if isinstance(t, str):
            t = pd.to_datetime(t).time()
        minutes = t.minute
        if minutes % 5 != 0:
            s = row['시작시간']
            e = row['종료시간']
            if isinstance(s, str):
                s = pd.to_datetime(s)
            if isinstance(e, str):
                e = pd.to_datetime(e)
            duration_min = int((e - s).total_seconds() / 60)
            non_5min_rows.append({
                '지원자ID': row['지원자ID'],
                '시작': s.time(),
                '종료': e.time(),
                'duration_min': duration_min
            })
    except Exception as e:
        continue

if non_5min_rows:
    df_non5 = pd.DataFrame(non_5min_rows)
    print(df_non5)
    print("\nDuration(분) 값 분포:")
    print(df_non5['duration_min'].value_counts().sort_index())
else:
    print("5분 단위가 아닌 종료시간 없음") 