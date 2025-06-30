#!/usr/bin/env python3
"""
시간/공간 충돌 검사 테스트
동일한 사람이 같은 시간에 여러 공간에 존재하는 문제를 분석합니다.
"""

import sys
import pandas as pd
from datetime import datetime, time
import streamlit as st

# Streamlit 환경 시뮬레이션
if 'st' not in sys.modules:
    import streamlit as st

# 앱 모듈 import
from app import default_df, init_session_states
from solver.api import create_schedule

def test_conflict_detection():
    """시간/공간 충돌 검사 테스트"""
    print("🔍 시간/공간 충돌 검사 테스트 시작")
    
    # 세션 상태 초기화
    init_session_states()
    
    # 디폴트 데이터 로드
    df = default_df()
    print(f"📊 테스트 데이터: {len(df)}명 지원자")
    
    # 스케줄링 실행
    print("🚀 스케줄링 실행 중...")
    schedule_result = create_schedule(
        applicants_df=df,
        selected_dates=['2025-07-01', '2025-07-02', '2025-07-03', '2025-07-04'],
        start_time=time(9, 0),
        end_time=time(18, 0)
    )
    
    if not schedule_result.success:
        print(f"❌ 스케줄링 실패: {schedule_result.error}")
        return
    
    print(f"✅ 스케줄링 성공: {len(schedule_result.schedule)} 항목")
    
    # DataFrame으로 변환
    schedule_df = schedule_result.schedule
    
    # 충돌 검사 수행
    conflicts = check_conflicts(schedule_df)
    
    if conflicts:
        print(f"🚨 충돌 발견: {len(conflicts)}개")
        for i, conflict in enumerate(conflicts[:10]):  # 최대 10개만 출력
            print(f"  {i+1}. {conflict}")
    else:
        print("✅ 충돌 없음")
    
    # 상세 분석
    analyze_schedule_details(schedule_df)
    
    # 통합 활동 분석
    analyze_integrated_activities(schedule_df)

def check_conflicts(df: pd.DataFrame) -> list:
    """시간/공간 충돌 검사"""
    conflicts = []
    
    # 각 날짜별로 검사
    for date in df['날짜'].unique():
        date_df = df[df['날짜'] == date].copy()
        
        # 시간 슬롯별로 그룹화
        time_groups = date_df.groupby(['시작시간', '종료시간'])
        
        for (start_time, end_time), group in time_groups:
            # 동일한 시간대에 있는 모든 사람들 확인
            people_in_timeslot = {}
            
            for _, row in group.iterrows():
                person = row['지원자명']
                room = row['장소']
                activity = row['활동명']
                
                if person not in people_in_timeslot:
                    people_in_timeslot[person] = []
                
                people_in_timeslot[person].append({
                    'room': room,
                    'activity': activity,
                    'time': f"{start_time}-{end_time}"
                })
            
            # 충돌 확인
            for person, locations in people_in_timeslot.items():
                if len(locations) > 1:
                    conflict_info = f"{date} {start_time}-{end_time}: {person}이(가) "
                    rooms = [loc['room'] for loc in locations]
                    activities = [loc['activity'] for loc in locations]
                    conflict_info += f"{', '.join(rooms)}에서 {', '.join(activities)} 동시 진행"
                    conflicts.append(conflict_info)
    
    return conflicts

def analyze_schedule_details(df: pd.DataFrame):
    """스케줄 상세 분석"""
    print("\n📈 스케줄 상세 분석")
    
    # 날짜별 통계
    print("\n📅 날짜별 통계:")
    for date in sorted(df['날짜'].unique()):
        date_df = df[df['날짜'] == date]
        unique_people = date_df['지원자명'].nunique()
        total_activities = len(date_df)
        print(f"  {date}: {unique_people}명, {total_activities}개 활동")
    
    # 활동별 통계
    print("\n🎯 활동별 통계:")
    activity_stats = df['활동명'].value_counts()
    for activity, count in activity_stats.items():
        print(f"  {activity}: {count}회")
    
    # 장소별 통계
    print("\n🏢 장소별 통계:")
    room_stats = df['장소'].value_counts()
    for room, count in room_stats.items():
        print(f"  {room}: {count}회")
    
    # 시간대별 활동량
    print("\n⏰ 시간대별 활동량:")
    time_stats = df['시작시간'].value_counts().sort_index()
    for start_time, count in time_stats.items():
        print(f"  {start_time}: {count}개 활동")

def analyze_integrated_activities(df: pd.DataFrame):
    """통합 활동 분석"""
    print("\n🔗 통합 활동 분석")
    
    # 통합 활동 찾기 (활동명에 '+'가 포함된 것들)
    integrated_activities = df[df['활동명'].str.contains(r'\+', na=False)]
    
    if len(integrated_activities) > 0:
        print(f"📋 통합 활동 발견: {len(integrated_activities)}개")
        
        # 통합 활동별 분석
        for activity_name in integrated_activities['활동명'].unique():
            activity_df = integrated_activities[integrated_activities['활동명'] == activity_name]
            print(f"\n  📌 {activity_name}:")
            print(f"    - 총 {len(activity_df)}회 진행")
            print(f"    - 참여자: {activity_df['지원자명'].nunique()}명")
            
            # 같은 사람이 여러 번 나타나는지 확인
            duplicate_people = activity_df['지원자명'].value_counts()
            duplicates = duplicate_people[duplicate_people > 1]
            if len(duplicates) > 0:
                print(f"    - ⚠️ 중복 참여자: {len(duplicates)}명")
                for person, count in duplicates.items():
                    print(f"      - {person}: {count}회")

if __name__ == "__main__":
    test_conflict_detection() 