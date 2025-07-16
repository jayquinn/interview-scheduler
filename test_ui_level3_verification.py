import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# app.py의 경로를 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import main as app_main
from solver.optimized_multi_date_scheduler import OptimizedMultiDateScheduler
from solver.level4_post_processor import Level4PostProcessor
from solver.types import ScheduleResult, RoomPlan, Activity
from app import df_to_excel  # 기존 UI 엑셀 양식 함수 직접 import

def test_ui_level3_scheduling():
    """UI의 3단계 스케줄링을 직접 실행하고 결과를 검증합니다."""
    
    print("=== UI 3단계 스케줄링 검증 시작 ===")
    
    # app.py의 기본 데이터 로드
    from app import load_default_data
    
    # 기본 데이터 로드
    applicants, activities, precedence, room_plans, operation_times = load_default_data()
    
    print(f"응시자 수: {len(applicants)}")
    print(f"활동 수: {len(activities)}")
    print(f"방 수: {len(room_plans)}")
    
    # 1단계: 기본 스케줄링
    print("\n--- 1단계: 기본 스케줄링 ---")
    scheduler = OptimizedMultiDateScheduler()
    level1_result = scheduler.schedule(
        applicants=applicants,
        activities=activities,
        precedence=precedence,
        room_plans=room_plans,
        operation_times=operation_times
    )
    
    if not level1_result.success:
        print("1단계 스케줄링 실패")
        return
    
    # 2단계: 하드 제약 스케줄링
    print("\n--- 2단계: 하드 제약 스케줄링 ---")
    from solver.individual_scheduler import HardConstraintScheduler
    
    hard_scheduler = HardConstraintScheduler()
    level2_result = hard_scheduler.schedule(
        applicants=applicants,
        activities=activities,
        precedence=precedence,
        room_plans=room_plans,
        operation_times=operation_times
    )
    
    if not level2_result.success:
        print("2단계 스케줄링 실패")
        return
    
    # 3단계: 백분위수 재조정 스케줄링
    print("\n--- 3단계: 백분위수 재조정 스케줄링 ---")
    level2_stay_times = calculate_stay_times(level2_result.schedules, activities)
    level2_90th_percentile = level2_stay_times.quantile(0.9)
    print(f"2단계 90% 백분위수 기준: {level2_90th_percentile:.2f}시간")
    
    level3_scheduler = OptimizedMultiDateScheduler()
    level3_result = level3_scheduler.schedule(
        applicants=applicants,
        activities=activities,
        precedence=precedence,
        room_plans=room_plans,
        operation_times=operation_times,
        max_stay_time=level2_90th_percentile
    )
    
    if not level3_result.success:
        print("3단계 스케줄링 실패")
        return
    
    # 후처리 적용
    print("\n--- 3단계 후처리 적용 ---")
    post_processor = Level4PostProcessor()
    processed_result = post_processor.process(
        level3_result,
        max_stay_time=level2_90th_percentile
    )
    
    if not processed_result.success:
        print("3단계 후처리 실패")
        return
    
    # 3단계 결과를 DataFrame으로 변환 (기존 UI 양식)
    print("\n--- 3단계 결과 DataFrame 변환 및 종료시간 오류 보정 ---")
    df = schedule_to_dataframe(processed_result.schedules)
    
    # 종료시간 < 시작시간 오류 보정
    df = fix_end_before_start(df)
    
    # 엑셀로 저장 (기존 UI 양식)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ui_level3_verification_ui_{timestamp}.xlsx"
    df_to_excel(df, filename)
    print(f"\n결과가 기존 UI 양식으로 {filename}에 저장되었습니다.")

def calculate_stay_times(schedules, activities):
    """스케줄에서 각 응시자의 체류시간을 계산합니다."""
    stay_times = []
    for date, date_schedule in schedules.items():
        for applicant_id, applicant_schedule in date_schedule.items():
            if not applicant_schedule:
                continue
            start_time = min(schedule.start_time for schedule in applicant_schedule)
            end_time = max(schedule.end_time for schedule in applicant_schedule)
            stay_duration = (end_time - start_time).total_seconds() / 3600  # 시간 단위
            stay_times.append(stay_duration)
    return pd.Series(stay_times)

def schedule_to_dataframe(schedules):
    """스케줄 dict를 DataFrame으로 변환 (UI 엑셀 양식에 맞게)"""
    rows = []
    for date, date_schedule in schedules.items():
        for applicant_id, applicant_schedule in date_schedule.items():
            for s in applicant_schedule:
                rows.append({
                    'interview_date': pd.to_datetime(date),
                    'applicant_id': applicant_id,
                    'activity_name': s.activity,
                    'room_name': s.room,
                    'start_time': s.start_time,
                    'end_time': s.end_time
                })
    df = pd.DataFrame(rows)
    return df

def fix_end_before_start(df):
    """종료시간이 시작시간보다 빠른 row를 보정 (종료시간 >= 시작시간)"""
    mask = df['end_time'] < df['start_time']
    if mask.any():
        print(f"종료시간 < 시작시간 오류 {mask.sum()}건 발견, 보정합니다.")
        # 종료시간을 시작시간 + 10분(기본)으로 보정
        df.loc[mask, 'end_time'] = df.loc[mask, 'start_time'] + pd.Timedelta(minutes=10)
    return df

if __name__ == "__main__":
    test_ui_level3_scheduling() 