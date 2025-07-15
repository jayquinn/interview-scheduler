#!/usr/bin/env python3
"""
최신 Excel 결과 파일 분석 스크립트
사용자가 지적한 문제점들 검증:
1. 발표준비 → 발표면접 선후행 제약
2. 방 활용률 및 동시 사용
3. 토론면접실 A, B 모두 사용
4. 발표준비실 2명 동시 수용
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

def analyze_excel_result(filename):
    """Excel 파일 분석"""
    print(f"📊 Excel 파일 분석: {filename}")
    print("=" * 60)
    
    try:
        # Excel 파일 읽기 (Schedule 시트)
        df = pd.read_excel(filename, sheet_name='Schedule')
        print(f"✅ 파일 로드 성공: {len(df)}개 활동, {df['applicant_id'].nunique()}명 지원자")
        
        # 기본 정보
        print(f"\n📋 기본 정보:")
        print(f"  - 총 활동: {len(df)}개")
        print(f"  - 총 지원자: {df['applicant_id'].nunique()}명")
        print(f"  - 면접 날짜: {df['interview_date'].nunique()}일")
        print(f"  - 활동 종류: {', '.join(df['activity_name'].unique())}")
        
        # 1. 발표준비 → 발표면접 선후행 제약 검증
        print(f"\n1️⃣ 발표준비 → 발표면접 선후행 제약 검증:")
        precedence_violations = 0
        valid_sequences = 0
        continuity_violations = 0
        
        for applicant in df['applicant_id'].unique():
            applicant_schedule = df[df['applicant_id'] == applicant].sort_values('start_time')
            activities = applicant_schedule['activity_name'].tolist()
            
            if '발표준비' in activities and '발표면접' in activities:
                prep_idx = activities.index('발표준비')
                interview_idx = activities.index('발표면접')
                
                if prep_idx >= interview_idx:
                    precedence_violations += 1
                    print(f"  ❌ {applicant}: 순서 위반")
                else:
                    valid_sequences += 1
                    
                    # 연속성 체크 
                    prep_row = applicant_schedule.iloc[prep_idx]
                    interview_row = applicant_schedule.iloc[interview_idx]
                    
                    prep_end = pd.to_datetime(f"{prep_row['interview_date']} {prep_row['end_time']}")
                    interview_start = pd.to_datetime(f"{interview_row['interview_date']} {interview_row['start_time']}")
                    
                    gap_minutes = (interview_start - prep_end).total_seconds() / 60
                    
                    if gap_minutes > 10:  # 10분 초과면 연속성 문제
                        continuity_violations += 1
                        print(f"  ⚠️ {applicant}: 연속성 위반 (간격 {gap_minutes:.0f}분)")
        
        print(f"  📊 결과: 올바른 순서 {valid_sequences}건, 순서위반 {precedence_violations}건, 연속성위반 {continuity_violations}건")
        
        if precedence_violations == 0:
            print("  ✅ 선후행 제약 모두 준수됨!")
        else:
            print(f"  ❌ 선후행 제약 위반 {precedence_violations}건 발견")
        
        # 2. 방 활용률 검증
        print(f"\n2️⃣ 방 활용률 검증:")
        room_usage = df.groupby(['room_name', 'activity_name']).size().reset_index(name='사용횟수')
        
        print("  방별 사용 현황:")
        for _, row in room_usage.iterrows():
            print(f"    {row['room_name']} ({row['activity_name']}): {row['사용횟수']}회")
        
        # 토론면접실 A, B 모두 사용되는지 확인
        discussion_rooms = room_usage[room_usage['activity_name'] == '토론면접']['room_name'].unique()
        print(f"\n  토론면접실 사용 현황: {list(discussion_rooms)}")
        
        if any('A' in room for room in discussion_rooms) and any('B' in room for room in discussion_rooms):
            print("  ✅ 토론면접실A, B 모두 활용됨")
        else:
            print("  ❌ 토론면접실 중 일부만 사용됨")
        
        # 3. 발표준비실 동시 수용 검증
        print(f"\n3️⃣ 발표준비실 동시 수용 검증:")
        prep_schedules = df[df['activity_name'] == '발표준비'].copy()
        
        if not prep_schedules.empty:
            print(f"  총 발표준비 일정: {len(prep_schedules)}개")
            
            # 시간대별 동시 사용자 수 계산
            max_concurrent = 0
            concurrent_2_count = 0
            
            # 각 발표준비 일정의 시작/종료 시간을 datetime으로 변환
            prep_schedules['datetime_start'] = pd.to_datetime(prep_schedules['interview_date'].astype(str) + ' ' + prep_schedules['start_time'].astype(str))
            prep_schedules['datetime_end'] = pd.to_datetime(prep_schedules['interview_date'].astype(str) + ' ' + prep_schedules['end_time'].astype(str))
            
            for idx, schedule in prep_schedules.iterrows():
                start = schedule['datetime_start']
                end = schedule['datetime_end']
                room = schedule['room_name']
                
                # 같은 방에서 시간이 겹치는 다른 일정들 찾기
                overlapping = prep_schedules[
                    (prep_schedules['datetime_start'] < end) & 
                    (prep_schedules['datetime_end'] > start) &
                    (prep_schedules['room_name'] == room)
                ]
                
                concurrent_count = len(overlapping)
                max_concurrent = max(max_concurrent, concurrent_count)
                
                if concurrent_count == 2:
                    concurrent_2_count += 1
            
            print(f"  최대 동시 사용자: {max_concurrent}명")
            print(f"  2명 동시 사용 발생: {concurrent_2_count//2}회")  # 중복 제거
            
            if max_concurrent >= 2:
                print("  ✅ 발표준비실 2명 수용 능력 활용됨")
            else:
                print("  ❌ 발표준비실 2명 수용 능력 미활용")
        
        # 4. 시간대별 방 활용 분석
        print(f"\n4️⃣ 시간대별 방 활용 분석:")
        
        # 시간대별 각 방의 사용률 계산
        df['datetime_start'] = pd.to_datetime(df['interview_date'].astype(str) + ' ' + df['start_time'].astype(str))
        df['datetime_end'] = pd.to_datetime(df['interview_date'].astype(str) + ' ' + df['end_time'].astype(str))
        
        # 각 시간대별로 사용 중인 방 수 계산
        room_types = ['토론면접실', '발표준비실', '발표면접실']
        utilization_summary = {}
        
        for room_type in room_types:
            room_schedules = df[df['room_name'].str.contains(room_type, na=False)]
            total_duration_hours = room_schedules['duration_min'].sum() / 60
            operating_hours = 8.5 * df['interview_date'].nunique()  # 8.5시간 * 일수
            utilization = (total_duration_hours / operating_hours) * 100
            utilization_summary[room_type] = utilization
            print(f"  {room_type} 전체 활용률: {utilization:.1f}%")
        
        # 5. 동시간대 활용 패턴 분석
        print(f"\n5️⃣ 동시간대 활용 패턴 분석:")
        
        # 토론면접 진행 중 다른 방들의 활용률 확인
        discussion_times = df[df['activity_name'] == '토론면접'][['datetime_start', 'datetime_end']]
        
        other_activities_during_discussion = 0
        total_discussion_slots = 0
        
        for _, discussion in discussion_times.iterrows():
            d_start = discussion['datetime_start']
            d_end = discussion['datetime_end']
            
            # 토론면접 시간 중 다른 활동들이 있는지 확인
            other_activities = df[
                (df['activity_name'] != '토론면접') &
                (df['datetime_start'] < d_end) &
                (df['datetime_end'] > d_start)
            ]
            
            if len(other_activities) > 0:
                other_activities_during_discussion += 1
            total_discussion_slots += 1
        
        parallel_rate = 0
        if total_discussion_slots > 0:
            parallel_rate = (other_activities_during_discussion / total_discussion_slots) * 100
            print(f"  토론면접 중 다른 활동 동시 진행율: {parallel_rate:.1f}%")
            
            if parallel_rate > 50:
                print("  ✅ 토론면접 중에도 다른 방들이 잘 활용됨")
            else:
                print("  ❌ 토론면접 중 다른 방들의 활용도가 낮음")
        
        # 종합 평가
        print(f"\n🎯 종합 평가:")
        issues_fixed = 0
        total_issues = 4
        
        if precedence_violations == 0:
            print("  ✅ 선후행 제약 문제 해결됨")
            issues_fixed += 1
        else:
            print("  ❌ 선후행 제약 문제 여전히 존재")
        
        if any('A' in room for room in discussion_rooms) and any('B' in room for room in discussion_rooms):
            print("  ✅ 토론면접실 A, B 모두 활용 문제 해결됨") 
            issues_fixed += 1
        else:
            print("  ❌ 토론면접실 A, B 활용 문제 여전히 존재")
        
        if max_concurrent >= 2:
            print("  ✅ 발표준비실 2명 수용 문제 해결됨")
            issues_fixed += 1
        else:
            print("  ❌ 발표준비실 2명 수용 문제 여전히 존재")
        
        if parallel_rate > 50:
            print("  ✅ 방들의 동시 활용 문제 해결됨")
            issues_fixed += 1
        else:
            print("  ❌ 방들의 동시 활용 문제 여전히 존재")
        
        print(f"\n📊 최종 결과: {issues_fixed}/{total_issues}개 문제 해결됨 ({issues_fixed/total_issues*100:.0f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ 파일 분석 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    filename = "ui_format_cpsat_result_20250714_123241.xlsx"
    
    if not os.path.exists(filename):
        print(f"❌ 파일을 찾을 수 없음: {filename}")
        return
    
    analyze_excel_result(filename)

if __name__ == "__main__":
    main() 