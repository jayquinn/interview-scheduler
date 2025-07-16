#!/usr/bin/env python3
"""
interview_schedule_20250716_151143.xlsx의 Individual_StayTime 시트 상세 분석
"""

import pandas as pd

filename = "interview_schedule_20250716_151143.xlsx"

print(f"=== {filename} - Individual_StayTime 시트 상세 분석 ===")

df = pd.read_excel(filename, sheet_name='Individual_StayTime')
print(f"행 수: {len(df)}")
print(f"컬럼: {list(df.columns)}")

# 시작/종료시간 5분 단위 여부 확인
print("\n[5분 단위 여부 확인]")
non_5min = 0
for i, row in df.iterrows():
    for col in ['시작시간', '종료시간']:
        t = row[col]
        try:
            if isinstance(t, str):
                t = pd.to_datetime(t).time()
            minutes = t.minute
            if minutes % 5 != 0:
                print(f"  ⚠️ {row['지원자ID']} {col}: {t} (분: {minutes}) - 5분 단위 아님")
                non_5min += 1
        except Exception as e:
            print(f"  ⚠️ {row['지원자ID']} {col}: {t} (파싱 오류: {e})")
            non_5min += 1
if non_5min == 0:
    print("  ✅ 모든 시간이 5분 단위로 맞춰짐")
else:
    print(f"  ❌ {non_5min}개 항목이 5분 단위가 아님")

# 시작-종료시간 역전/이상치 확인
print("\n[시작-종료시간 역전/이상치 확인]")
abnormal = 0
for i, row in df.iterrows():
    try:
        s = row['시작시간']
        e = row['종료시간']
        if isinstance(s, str):
            s = pd.to_datetime(s)
        if isinstance(e, str):
            e = pd.to_datetime(e)
        if e < s:
            print(f"  ❌ {row['지원자ID']}: 종료시간({e}) < 시작시간({s})")
            abnormal += 1
    except Exception as e:
        print(f"  ⚠️ {row['지원자ID']}: 시간 파싱 오류: {e}")
        abnormal += 1
if abnormal == 0:
    print("  ✅ 모든 시작-종료시간 정상")
else:
    print(f"  ❌ {abnormal}개 항목 이상/역전")

# 체류시간 직접 계산 및 비교
print("\n[체류시간 직접 계산 및 비교]")
wrong_stay = 0
for i, row in df.iterrows():
    try:
        s = row['시작시간']
        e = row['종료시간']
        if isinstance(s, str):
            s = pd.to_datetime(s)
        if isinstance(e, str):
            e = pd.to_datetime(e)
        calc_stay = round((e - s).total_seconds() / 3600, 2)
        sheet_stay = round(float(row['체류시간(시간)']), 2)
        if abs(calc_stay - sheet_stay) > 0.01:
            print(f"  ❌ {row['지원자ID']}: 계산={calc_stay}h, 시트={sheet_stay}h, 시작={s.time()}, 종료={e.time()}")
            wrong_stay += 1
    except Exception as e:
        print(f"  ⚠️ {row['지원자ID']}: 체류시간 계산 오류: {e}")
        wrong_stay += 1
if wrong_stay == 0:
    print("  ✅ 모든 체류시간 계산값과 시트값 일치")
else:
    print(f"  ❌ {wrong_stay}개 항목 체류시간 불일치") 