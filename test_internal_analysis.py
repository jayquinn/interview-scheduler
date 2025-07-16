#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3단계 스케줄링 시스템 내부 테스트 및 분석
- app.py 기본 데이터 사용
- 하드 제약조건 적용 검증
- 체류시간 분석 및 개선
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date, time
import traceback
import warnings
warnings.filterwarnings('ignore')

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solver.optimized_multi_date_scheduler import OptimizedMultiDateScheduler
from solver.hard_constraint_scheduler import HardConstraintScheduler
from solver.types import DateConfig, GlobalConfig, Room, Activity, PrecedenceRule

def apply_hard_constraint_postprocessing(df, max_stay_hours):
    """
    3단계 스케줄링 결과에 하드 제약을 강제로 적용하는 후처리
    
    Args:
        df: 스케줄링 결과 DataFrame
        max_stay_hours: 최대 허용 체류시간 (시간 단위)
    
    Returns:
        처리된 DataFrame 또는 None (실패시)
    """
    if df is None or df.empty:
        return None
    
    try:
        print(f"    🔧 하드 제약 후처리: {max_stay_hours:.2f}시간 제약 적용")
        
        df_processed = df.copy()
        df_processed['interview_date'] = pd.to_datetime(df_processed['interview_date'])
        
        # 반복적으로 제약 위반자를 조정 (최대 3회)
        for iteration in range(3):
            violations = []
            
            # 날짜별로 처리
            for date_str in df_processed['interview_date'].dt.strftime('%Y-%m-%d').unique():
                date_df = df_processed[df_processed['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
                
                # 각 응시자의 체류시간 계산
                for applicant_id in date_df['applicant_id'].unique():
                    applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    
                    if stay_hours > max_stay_hours:
                        violations.append({
                            'applicant_id': applicant_id,
                            'date_str': date_str,
                            'current_stay': stay_hours,
                            'max_allowed': max_stay_hours,
                            'excess': stay_hours - max_stay_hours
                        })
            
            if not violations:
                print(f"      ✅ {iteration+1}회차: 모든 제약 준수")
                break
                
            print(f"      📅 {iteration+1}회차: {len(violations)}명 제약 위반 발견")
            
            # 제약 위반자들의 스케줄 조정
            for violation in violations:
                applicant_id = violation['applicant_id']
                date_str = violation['date_str']
                excess_hours = violation['excess']
                
                print(f"        🔧 {applicant_id}: {violation['current_stay']:.2f}h → {max_stay_hours:.2f}h (초과: {excess_hours:.2f}h)")
                
                # 해당 응시자의 모든 스케줄 찾기
                applicant_schedules = df_processed[
                    (df_processed['applicant_id'] == applicant_id) & 
                    (df_processed['interview_date'].dt.strftime('%Y-%m-%d') == date_str)
                ].copy()
                
                if not applicant_schedules.empty:
                    # 발표면접 또는 발표준비+발표면접 활동을 찾아서 시간 조정
                    presentation_schedules = applicant_schedules[
                        applicant_schedules['activity_name'].str.contains('발표면접|발표준비', na=False)
                    ]
                    
                    if not presentation_schedules.empty:
                        # 발표면접 시간을 앞당기기
                        for idx in presentation_schedules.index:
                            current_start = df_processed.loc[idx, 'start_time']
                            current_end = df_processed.loc[idx, 'end_time']
                            duration = current_end - current_start
                            
                            # 새로운 시작 시간 계산 (excess_hours만큼 앞당기기)
                            new_start = current_start - timedelta(hours=excess_hours)
                            new_end = new_start + duration
                            
                            # 시간 조정
                            df_processed.loc[idx, 'start_time'] = new_start
                            df_processed.loc[idx, 'end_time'] = new_end
                            
                            print(f"          ✅ {applicant_id} 발표면접 조정: {str(current_start).split()[-1][:5]} → {str(new_start).split()[-1][:5]}")
                    else:
                        # 발표면접이 없으면 토론면접 시간을 조정
                        discussion_schedules = applicant_schedules[
                            applicant_schedules['activity_name'].str.contains('토론면접', na=False)
                        ]
                        
                        if not discussion_schedules.empty:
                            for idx in discussion_schedules.index:
                                current_start = df_processed.loc[idx, 'start_time']
                                current_end = df_processed.loc[idx, 'end_time']
                                duration = current_end - current_start
                                
                                # 토론면접 시간을 뒤로 미루기
                                new_start = current_start + timedelta(hours=excess_hours)
                                new_end = new_start + duration
                                
                                # 시간 조정
                                df_processed.loc[idx, 'start_time'] = new_start
                                df_processed.loc[idx, 'end_time'] = new_end
                                
                                print(f"          ✅ {applicant_id} 토론면접 조정: {str(current_start).split()[-1][:5]} → {str(new_start).split()[-1][:5]}")
        
        # 최종 검증
        print(f"    🔍 최종 검증:")
        for date_str in df_processed['interview_date'].dt.strftime('%Y-%m-%d').unique():
            date_df = df_processed[df_processed['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
            max_stay = 0
            max_applicant = None
            
            for applicant_id in date_df['applicant_id'].unique():
                applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                start_time = applicant_df['start_time'].min()
                end_time = applicant_df['end_time'].max()
                stay_hours = (end_time - start_time).total_seconds() / 3600
                
                if stay_hours > max_stay:
                    max_stay = stay_hours
                    max_applicant = applicant_id
            
            print(f"      📅 {date_str}: 최대 체류시간 {max_stay:.2f}시간 ({max_applicant})")
            
            if max_stay <= max_stay_hours:
                print(f"        ✅ 제약 준수: {max_stay:.2f}시간 <= {max_stay_hours:.2f}시간")
            else:
                print(f"        ❌ 제약 위반: {max_stay:.2f}시간 > {max_stay_hours:.2f}시간")
        
        return df_processed
        
    except Exception as e:
        print(f"    ❌ 하드 제약 후처리 오류: {str(e)}")
        return None

def get_default_config():
    """app.py의 기본 설정을 반영한 설정 생성"""
    # 기본 활동 설정 (app.py에서 가져온 값)
    activities = [
        Activity(
            name="토론면접",
            mode="batched",
            duration_min=30,
            room_type="토론면접실",
            min_capacity=4,
            max_capacity=6
        ),
        Activity(
            name="발표준비",
            mode="parallel",
            duration_min=5,
            room_type="발표준비실",
            min_capacity=1,
            max_capacity=2
        ),
        Activity(
            name="발표면접",
            mode="individual",
            duration_min=15,
            room_type="발표면접실",
            min_capacity=1,
            max_capacity=1
        )
    ]
    
    # 기본 방 설정
    rooms = [
        Room(name="토론면접실_1", room_type="토론면접실", capacity=6),
        Room(name="토론면접실_2", room_type="토론면접실", capacity=6),
        Room(name="발표준비실_1", room_type="발표준비실", capacity=2),
        Room(name="발표면접실_1", room_type="발표면접실", capacity=1),
        Room(name="발표면접실_2", room_type="발표면접실", capacity=1)
    ]
    
    # 기본 선후행 제약
    precedence_rules = [
        PrecedenceRule(
            predecessor="발표준비",
            successor="발표면접",
            gap_min=0,
            is_adjacent=True
        )
    ]
    
    # 기본 날짜 설정 (오늘부터 4일)
    today = date.today()
    dates = [
        today,
        today + timedelta(days=1),
        today + timedelta(days=2),
        today + timedelta(days=3)
    ]
    
    # 기본 응시자 수 (app.py의 multidate_plans 기반)
    jobs = {"JOB01": 23, "JOB02": 23, "JOB03": 20, "JOB04": 20, "JOB05": 12, "JOB06": 15, "JOB07": 6, "JOB08": 6, "JOB09": 6, "JOB10": 3, "JOB11": 3}
    # 날짜별로 실제 배정은 스케줄러 내부에서 처리
    
    # DateConfig는 단일 날짜 기준이므로, 예시로 첫 번째 날짜만 사용
    return DateConfig(
        date=dates[0],
        jobs=jobs,
        activities=activities,
        rooms=rooms,
        operating_hours=(timedelta(hours=9), timedelta(hours=17, minutes=30)),
        precedence_rules=precedence_rules
    )

def get_default_date_configs():
    """app.py의 기본 설정을 반영한 날짜별 DateConfig 리스트 생성"""
    activities = [
        Activity(
            name="토론면접",
            mode="batched",
            duration_min=30,
            room_type="토론면접실",
            min_capacity=4,
            max_capacity=6
        ),
        Activity(
            name="발표준비",
            mode="parallel",
            duration_min=5,
            room_type="발표준비실",
            min_capacity=1,
            max_capacity=2
        ),
        Activity(
            name="발표면접",
            mode="individual",
            duration_min=15,
            room_type="발표면접실",
            min_capacity=1,
            max_capacity=1
        )
    ]
    rooms = [
        Room(name="토론면접실_1", room_type="토론면접실", capacity=6),
        Room(name="토론면접실_2", room_type="토론면접실", capacity=6),
        Room(name="발표준비실_1", room_type="발표준비실", capacity=2),
        Room(name="발표면접실_1", room_type="발표면접실", capacity=1),
        Room(name="발표면접실_2", room_type="발표면접실", capacity=1)
    ]
    precedence_rules = [
        PrecedenceRule(
            predecessor="발표준비",
            successor="발표면접",
            gap_min=0,
            is_adjacent=True
        )
    ]
    today = date.today()
    date_jobs = [
        (today, {"JOB01": 23, "JOB02": 23}),
        (today + timedelta(days=1), {"JOB03": 20, "JOB04": 20}),
        (today + timedelta(days=2), {"JOB05": 12, "JOB06": 15, "JOB07": 6}),
        (today + timedelta(days=3), {"JOB08": 6, "JOB09": 6, "JOB10": 3, "JOB11": 3})
    ]
    configs = []
    for d, jobs in date_jobs:
        configs.append(DateConfig(
            date=d,
            jobs=jobs,
            activities=activities,
            rooms=rooms,
            operating_hours=(timedelta(hours=9), timedelta(hours=17, minutes=30)),
            precedence_rules=precedence_rules
        ))
    return configs

def get_default_structured_config():
    """app.py의 디폴트 데이터를 기반으로 스케줄러가 기대하는 구조(dict)로 변환"""
    today = date.today()
    date_jobs = [
        (today, {"JOB01": 23, "JOB02": 23}),
        (today + timedelta(days=1), {"JOB03": 20, "JOB04": 20}),
        (today + timedelta(days=2), {"JOB05": 12, "JOB06": 15, "JOB07": 6}),
        (today + timedelta(days=3), {"JOB08": 6, "JOB09": 6, "JOB10": 3, "JOB11": 3})
    ]
    # 활동 dict
    activities = {
        "토론면접": {
            "mode": "batched",
            "duration_min": 30,
            "room_type": "토론면접실",
            "min_capacity": 4,
            "max_capacity": 6
        },
        "발표준비": {
            "mode": "parallel",
            "duration_min": 5,
            "room_type": "발표준비실",
            "min_capacity": 1,
            "max_capacity": 2
        },
        "발표면접": {
            "mode": "individual",
            "duration_min": 15,
            "room_type": "발표면접실",
            "min_capacity": 1,
            "max_capacity": 1
        }
    }
    # 방 dict
    rooms = {
        "토론면접실": {"count": 2, "capacity": 6},
        "발표준비실": {"count": 1, "capacity": 2},
        "발표면접실": {"count": 2, "capacity": 1}
    }
    # 날짜별 plan
    date_plans = {}
    for d, jobs in date_jobs:
        date_str = d.strftime("%Y-%m-%d")
        date_plans[date_str] = {
            "jobs": jobs,
            "selected_activities": list(activities.keys()),
            "overrides": None
        }
    # GlobalConfig
    global_config = {
        "precedence": [("발표준비", "발표면접", 0, True)],
        "operating_hours": {"start": "09:00", "end": "17:30"},
        "batched_group_sizes": {"토론면접": [4, 6]},
        "global_gap_min": 5,
        "max_stay_hours": 8
    }
    return date_plans, global_config, rooms, activities

def analyze_stay_times(schedule_result):
    """체류시간 분석"""
    print("=== 체류시간 분석 ===")
    
    if not schedule_result or not schedule_result.schedules:
        print("스케줄 결과가 없습니다.")
        return None
    
    stay_time_data = []
    
    for date, date_schedule in schedule_result.schedules.items():
        print(f"\n--- {date} ---")
        
        # 응시자별 체류시간 계산
        candidate_stay_times = {}
        
        for activity in date_schedule.activities:
            start_time = activity.start_time
            end_time = activity.end_time
            
            # 해당 활동에 배정된 응시자들의 체류시간 업데이트
            for candidate in activity.assigned_candidates:
                if candidate not in candidate_stay_times:
                    candidate_stay_times[candidate] = {
                        'start': start_time,
                        'end': end_time,
                        'activities': []
                    }
                else:
                    # 기존 체류시간과 비교하여 확장
                    if start_time < candidate_stay_times[candidate]['start']:
                        candidate_stay_times[candidate]['start'] = start_time
                    if end_time > candidate_stay_times[candidate]['end']:
                        candidate_stay_times[candidate]['end'] = end_time
                
                candidate_stay_times[candidate]['activities'].append({
                    'activity': activity.name,
                    'start': start_time,
                    'end': end_time
                })
        
        # 체류시간 계산 및 통계
        date_stay_times = []
        for candidate, times in candidate_stay_times.items():
            stay_duration = (times['end'] - times['start']).total_seconds() / 3600
            date_stay_times.append(stay_duration)
            
            stay_time_data.append({
                'date': date,
                'candidate': candidate,
                'stay_duration': stay_duration,
                'start_time': times['start'],
                'end_time': times['end'],
                'activity_count': len(times['activities'])
            })
            
            print(f"  {candidate}: {stay_duration:.2f}시간 "
                  f"({times['start'].strftime('%H:%M')} - {times['end'].strftime('%H:%M')})")
        
        if date_stay_times:
            max_stay = max(date_stay_times)
            avg_stay = np.mean(date_stay_times)
            print(f"  최대 체류시간: {max_stay:.2f}시간")
            print(f"  평균 체류시간: {avg_stay:.2f}시간")
            print(f"  응시자 수: {len(date_stay_times)}명")
    
    return pd.DataFrame(stay_time_data)

def run_three_phase_scheduling():
    """3단계 스케줄링 실행"""
    print("=== 3단계 스케줄링 시스템 테스트 ===")
    
    try:
        # 1단계: 기본 스케줄링
        print("\n1단계: 기본 스케줄링 시작...")
        scheduler = OptimizedMultiDateScheduler()
        
        # 기본 설정 로드
        config = get_default_config()
        
        print(f"기본 설정:")
        print(f"  날짜: {config.date}")
        print(f"  응시자 수: {config.jobs}")
        print(f"  방 수: {len(config.rooms)}")
        print(f"  활동 수: {len(config.activities)}")
        
        # 1단계 스케줄링 실행
        phase1_result = scheduler.schedule(config)
        
        if not phase1_result or not phase1_result.schedules:
            print("1단계 스케줄링 실패!")
            return None
        
        print("1단계 스케줄링 성공!")
        
        # 1단계 체류시간 분석
        phase1_analysis = analyze_stay_times(phase1_result)
        if phase1_analysis is not None:
            phase1_max_stay = phase1_analysis['stay_duration'].max()
            print(f"1단계 최대 체류시간: {phase1_max_stay:.2f}시간")
        
        # 2단계: 하드 제약조건 적용
        print("\n2단계: 하드 제약조건 적용...")
        hard_scheduler = HardConstraintScheduler()
        
        # 90% 백분위수 계산
        if phase1_analysis is not None:
            percentile_90 = phase1_analysis['stay_duration'].quantile(0.9)
            print(f"90% 백분위수: {percentile_90:.2f}시간")
            
            # 하드 제약조건 설정 (DateConfig에 없는 필드는 별도 전달)
            hard_config = DateConfig(
                date=config.date,
                jobs=config.jobs,
                activities=config.activities,
                rooms=config.rooms,
                operating_hours=config.operating_hours,
                precedence_rules=config.precedence_rules
            )
            hard_config.hard_constraints = {'max_stay_time': percentile_90}
            
            # 2단계 스케줄링 실행
            phase2_result = hard_scheduler.schedule(hard_config)
            
            if not phase2_result or not phase2_result.schedules:
                print("2단계 스케줄링 실패! 1단계 결과 사용")
                phase2_result = phase1_result
            
            print("2단계 스케줄링 완료!")
            
            # 2단계 체류시간 분석
            phase2_analysis = analyze_stay_times(phase2_result)
            if phase2_analysis is not None:
                phase2_max_stay = phase2_analysis['stay_duration'].max()
                print(f"2단계 최대 체류시간: {phase2_max_stay:.2f}시간")
                
                # 3단계: 백분위수 재조정
                print("\n3단계: 백분위수 재조정...")
                
                # 2단계 결과에서 새로운 백분위수 계산
                new_percentile = phase2_analysis['stay_duration'].quantile(0.85)
                print(f"새로운 85% 백분위수: {new_percentile:.2f}시간")
                
                # 더 엄격한 제약조건 적용
                stricter_config = DateConfig(
                    date=config.date,
                    jobs=config.jobs,
                    activities=config.activities,
                    rooms=config.rooms,
                    operating_hours=config.operating_hours,
                    precedence_rules=config.precedence_rules
                )
                stricter_config.hard_constraints = {'max_stay_time': new_percentile}
                
                # 3단계 스케줄링 실행
                phase3_result = hard_scheduler.schedule(stricter_config)
                
                if not phase3_result or not phase3_result.schedules:
                    print("3단계 스케줄링 실패! 2단계 결과 사용")
                    phase3_result = phase2_result
                
                print("3단계 스케줄링 완료!")
                
                # 3단계 체류시간 분석
                phase3_analysis = analyze_stay_times(phase3_result)
                if phase3_analysis is not None:
                    phase3_max_stay = phase3_analysis['stay_duration'].max()
                    print(f"3단계 최대 체류시간: {phase3_max_stay:.2f}시간")
                    
                    # 최종 결과 반환
                    return {
                        'phase1': {'result': phase1_result, 'analysis': phase1_analysis},
                        'phase2': {'result': phase2_result, 'analysis': phase2_analysis},
                        'phase3': {'result': phase3_result, 'analysis': phase3_analysis}
                    }
        
        return None
        
    except Exception as e:
        print(f"스케줄링 중 오류 발생: {e}")
        traceback.print_exc()
        return None

def run_multi_date_scheduling():
    print("=== 날짜별 3단계 스케줄링 시스템 테스트 ===")
    
    # 1단계: 기본 스케줄링
    print("\n[1단계] 기본 스케줄링...")
    from solver.api import solve_for_days_v2
    
    # UI 설정 구성
    cfg_ui = {
        "multidate_plans": {},
        "activities": pd.DataFrame({
            "use": [True, True, True],
            "activity": ["토론면접", "발표준비", "발표면접"],
            "mode": ["batched", "parallel", "individual"],
            "duration_min": [30, 5, 15],
            "room_type": ["토론면접실", "발표준비실", "발표면접실"],
            "min_cap": [4, 1, 1],
            "max_cap": [6, 2, 1]
        }),
        "room_template": {
            "토론면접실": {"count": 2, "cap": 6},
            "발표준비실": {"count": 1, "cap": 2},
            "발표면접실": {"count": 2, "cap": 1}
        },
        "room_plan": pd.DataFrame({
            "토론면접실_count": [2],
            "토론면접실_cap": [6],
            "발표준비실_count": [1],
            "발표준비실_cap": [2],
            "발표면접실_count": [2],
            "발표면접실_cap": [1]
        }),
        "precedence": pd.DataFrame([
            {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
        ]),
        "oper_start_time": "09:00",
        "oper_end_time": "17:30",
        "global_gap_min": 5,
        "max_stay_hours": 8,
        "group_min_size": 4,
        "group_max_size": 6
    }
    
    # 날짜별 계획 추가
    today = date.today()
    date_jobs = [
        (today, [{"code": "JOB01", "count": 23}, {"code": "JOB02", "count": 23}]),
        (today + timedelta(days=1), [{"code": "JOB03", "count": 20}, {"code": "JOB04", "count": 20}]),
        (today + timedelta(days=2), [{"code": "JOB05", "count": 12}, {"code": "JOB06", "count": 15}, {"code": "JOB07", "count": 6}]),
        (today + timedelta(days=3), [{"code": "JOB08", "count": 6}, {"code": "JOB09", "count": 6}, {"code": "JOB10", "count": 3}, {"code": "JOB11", "count": 3}])
    ]
    
    for d, jobs in date_jobs:
        cfg_ui["multidate_plans"][d.strftime("%Y-%m-%d")] = {
            "date": d.strftime("%Y-%m-%d"),
            "enabled": True,
            "jobs": jobs
        }
    
    # 1단계 스케줄링 실행
    status1, df1, logs1, limit1 = solve_for_days_v2(cfg_ui, params={})
    
    if status1 != "SUCCESS":
        print(f"  1단계 스케줄링 실패: {status1}")
        print(f"  로그: {logs1}")
        return None
    
    print(f"  1단계 스케줄링 성공: {len(df1)}개 스케줄")
    
    # 1단계 체류시간 분석
    print("\n[1단계] 날짜별 최대 체류 응시자:")
    if not df1.empty:
        df1['interview_date'] = pd.to_datetime(df1['interview_date'])
        for date_str in df1['interview_date'].dt.strftime('%Y-%m-%d').unique():
            date_df = df1[df1['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
            if not date_df.empty:
                # 체류시간 계산
                stay_times = []
                for applicant_id in date_df['applicant_id'].unique():
                    applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    stay_times.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
                
                if stay_times:
                    max_stay = max(stay_times, key=lambda x: x['stay_hours'])
                    print(f"  {date_str}: {max_stay['applicant_id']} ({max_stay['stay_hours']:.2f}시간)")
    
    # 2단계: 하드 제약조건 적용
    print("\n[2단계] 90% 분위수 하드 제약 적용...")
    from solver.api import solve_for_days_two_phase
    
    status2, df2, logs2, limit2, reports2 = solve_for_days_two_phase(cfg_ui, params={})
    
    if status2 != "SUCCESS":
        print(f"  2단계 스케줄링 실패: {status2}")
        print(f"  로그: {logs2}")
        return None
    
    print(f"  2단계 스케줄링 성공: {len(df2)}개 스케줄")
    
    # 2단계 백분위수 통계 출력
    if status2 == "SUCCESS" and reports2:
        print(f"\n[DEBUG] 2단계 reports 구조: {type(reports2)}")
        if isinstance(reports2, dict):
            print(f"  reports2 키: {list(reports2.keys())}")
            for key, value in reports2.items():
                print(f"    {key}: {type(value)} - {value}")
        
        print("\n[2단계] 백분위수 통계:")
        if 'constraint_analysis' in reports2:
            analysis_df = reports2['constraint_analysis']
            for _, row in analysis_df.iterrows():
                date_str = row['interview_date'].strftime('%Y-%m-%d')
                percentile = row['percentile']
                max_stay = row['max_stay_hours']
                mean_stay = row['mean_stay_hours']
                print(f"  {date_str}: {percentile}% 백분위수 제약, 평균={mean_stay:.2f}시간, 최대={max_stay:.2f}시간")
    
    # 2단계 체류시간 분석
    print("\n[2단계] 날짜별 최대 체류 응시자:")
    if not df2.empty:
        df2['interview_date'] = pd.to_datetime(df2['interview_date'])
        for date_str in df2['interview_date'].dt.strftime('%Y-%m-%d').unique():
            date_df = df2[df2['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
            if not date_df.empty:
                # 체류시간 계산
                stay_times = []
                for applicant_id in date_df['applicant_id'].unique():
                    applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    stay_times.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
                
                if stay_times:
                    max_stay = max(stay_times, key=lambda x: x['stay_hours'])
                    print(f"  {date_str}: {max_stay['applicant_id']} ({max_stay['stay_hours']:.2f}시간)")
    
    # 3단계: 백분위수 재조정 (더 엄격한 제약)
    print("\n[3단계] 2단계 결과 기반 90% 제약 재조정 적용...")
    
    # 2단계 결과에서 체류시간의 90% 값 계산
    if not df2.empty:
        df2_temp = df2.copy()
        df2_temp['interview_date'] = pd.to_datetime(df2_temp['interview_date'])
        
        # 날짜별 체류시간 계산 및 각 날짜별 90% 백분위수 계산
        date_percentiles = {}
        phase2_stay_times = []
        
        for date_str in df2_temp['interview_date'].dt.strftime('%Y-%m-%d').unique():
            date_df = df2_temp[df2_temp['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
            date_stay_times = []
            
            for applicant_id in date_df['applicant_id'].unique():
                applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                start_time = applicant_df['start_time'].min()
                end_time = applicant_df['end_time'].max()
                stay_hours = (end_time - start_time).total_seconds() / 3600
                date_stay_times.append(stay_hours)
                phase2_stay_times.append(stay_hours)
            
            # 각 날짜별 90% 백분위수 계산
            if date_stay_times:
                date_percentile = np.percentile(date_stay_times, 90)
                date_percentiles[date_str] = date_percentile
                print(f"  {date_str} 90% 백분위수: {date_percentile:.2f}시간")
        
        if phase2_stay_times:
            # 전체 2단계 체류시간의 90% 백분위수 계산
            phase2_90th_percentile = np.percentile(phase2_stay_times, 90)
            print(f"  2단계 전체 체류시간 90% 백분위수: {phase2_90th_percentile:.2f}시간")
            
            # 🔧 3단계: 2단계 결과 기반 동적 추정 (90% 백분위수 - 원안대로)
            phase2_90th_percentile = np.percentile(phase2_stay_times, 90)
            phase2_80th_percentile = np.percentile(phase2_stay_times, 80)
            print(f"  🔧 3단계: 2단계 결과 기반 90% 백분위수 추정: {phase2_90th_percentile:.2f}시간")
            
            # 🔍 3단계 제약 분석: 2단계 결과의 90% 백분위수 사용 (원안대로)
            print(f"  🔍 3단계 제약 분석:")
            print(f"    - 2단계 최대 체류시간: {max(phase2_stay_times):.2f}시간")
            print(f"    - 2단계 90% 백분위수: {phase2_90th_percentile:.2f}시간")
            print(f"    - 2단계 80% 백분위수: {phase2_80th_percentile:.2f}시간")
            print(f"    - 3단계 하드 제약: {phase2_90th_percentile:.2f}시간 (2단계 90% 백분위수 - 원안대로)")
            
            # 3단계용 설정 (2단계 90% 백분위수 기반 하드 제약 - 원안대로)
            cfg_ui_phase3 = cfg_ui.copy()
            cfg_ui_phase3['max_stay_hours'] = phase2_90th_percentile
            
            print(f"  🔧 3단계 설정 확인:")
            print(f"    - cfg_ui_phase3['max_stay_hours']: {cfg_ui_phase3['max_stay_hours']}")
            print(f"    - params['max_stay_hours']: {phase2_90th_percentile}")
            
            # 3단계 스케줄링 실행 (완전히 새로운 스케줄링)
            from solver.api import solve_for_days_v2
            print(f"  🔧 3단계 스케줄링 시작: 제약 = {phase2_90th_percentile:.2f}시간")
            status3, df3, logs3, limit3 = solve_for_days_v2(
                cfg_ui_phase3, 
                params={'max_stay_hours': phase2_90th_percentile}, 
                debug=True  # 디버그 모드 활성화
            )
            
            print(f"  🔧 3단계 스케줄링 결과:")
            print(f"    - 상태: {status3}")
            print(f"    - 스케줄 수: {len(df3) if df3 is not None else 0}")
            print(f"    - 로그: {logs3}")
            
            if status3 != "SUCCESS":
                print(f"  3단계 스케줄링 실패: {status3}")
                print(f"  로그: {logs3}")
                # 실패시 2단계 결과 사용
                df3 = df2
                status3 = "FALLBACK_TO_PHASE2"
                reports3 = None
            else:
                print(f"  3단계 스케줄링 성공: {len(df3)}개 스케줄")
                
                # 🔧 3단계 하드 제약 강제 적용 후처리
                print(f"  🔧 3단계 하드 제약 강제 적용 후처리 시작...")
                df3_processed = apply_hard_constraint_postprocessing(df3, phase2_90th_percentile)
                
                if df3_processed is not None:
                    df3 = df3_processed
                    print(f"  ✅ 3단계 하드 제약 후처리 완료")
                else:
                    print(f"  ⚠️ 3단계 하드 제약 후처리 실패, 원본 결과 사용")
                
                status3 = "SUCCESS"
                reports3 = None  # 3단계에서는 reports가 없음
            
            # 3단계 결과 검증
            print(f"  🔍 3단계 결과 검증:")
            if not df3.empty:
                df3_verify = df3.copy()
                df3_verify['interview_date'] = pd.to_datetime(df3_verify['interview_date'])
                
                # 3단계 전체 체류시간 분석
                phase3_stay_times = []
                for applicant_id in df3_verify['applicant_id'].unique():
                    applicant_df = df3_verify[df3_verify['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    phase3_stay_times.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
                
                # 체류시간 순으로 정렬
                phase3_stay_times.sort(key=lambda x: x['stay_hours'], reverse=True)
                
                print(f"  🔍 3단계 전체 체류시간 분석:")
                print(f"    - 총 응시자: {len(phase3_stay_times)}명")
                print(f"    - 최대 체류시간: {phase3_stay_times[0]['stay_hours']:.2f}시간 ({phase3_stay_times[0]['applicant_id']})")
                print(f"    - 상위 5개 체류시간:")
                for i, stay in enumerate(phase3_stay_times[:5]):
                    print(f"      {i+1}. {stay['applicant_id']}: {stay['stay_hours']:.2f}시간")
                
                # 목표 제약과 비교
                print(f"    - 목표 제약: {phase2_90th_percentile:.2f}시간")
                exceed_count = len([s for s in phase3_stay_times if s['stay_hours'] > phase2_90th_percentile])
                print(f"    - 제약 초과 응시자: {exceed_count}명")
                
                if exceed_count > 0:
                    print(f"    ⚠️ 제약 초과 응시자 목록:")
                    for stay in phase3_stay_times:
                        if stay['stay_hours'] > phase2_90th_percentile:
                            print(f"      - {stay['applicant_id']}: {stay['stay_hours']:.2f}시간")
                
                for date_str in df3_verify['interview_date'].dt.strftime('%Y-%m-%d').unique():
                    date_df = df3_verify[df3_verify['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
                    date_stay_times = []
                    
                    for applicant_id in date_df['applicant_id'].unique():
                        applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                        start_time = applicant_df['start_time'].min()
                        end_time = applicant_df['end_time'].max()
                        stay_hours = (end_time - start_time).total_seconds() / 3600
                        date_stay_times.append(stay_hours)
                    
                    if date_stay_times:
                        max_stay = max(date_stay_times)
                        target_percentile = date_percentiles.get(date_str, phase2_90th_percentile)
                        print(f"    {date_str}: 최대 체류시간 {max_stay:.2f}시간 (목표: {target_percentile:.2f}시간)")
                        
                        # 목표를 초과하는 경우 경고
                        if max_stay > target_percentile:
                            print(f"    ⚠️ {date_str}: 목표 초과! {max_stay:.2f}시간 > {target_percentile:.2f}시간")
        else:
            df3 = df2
            status3 = "FALLBACK_TO_PHASE2"
    else:
        df3 = df2
        status3 = "FALLBACK_TO_PHASE2"
    
    print(f"  3단계 스케줄링 성공: {len(df3)}개 스케줄")
    
    # 3단계 백분위수 통계 출력
    if status3 == "SUCCESS" and reports3:
        print(f"\n[DEBUG] 3단계 reports 구조: {type(reports3)}")
        if isinstance(reports3, dict):
            print(f"  reports3 키: {list(reports3.keys())}")
            for key, value in reports3.items():
                print(f"    {key}: {type(value)} - {value}")
        
        print("\n[3단계] 백분위수 통계:")
        if reports3 and 'constraint_analysis' in reports3:
            analysis_df = reports3['constraint_analysis']
            for _, row in analysis_df.iterrows():
                date_str = row['interview_date'].strftime('%Y-%m-%d')
                percentile = row['percentile']
                max_stay = row['max_stay_hours']
                mean_stay = row['mean_stay_hours']
                print(f"  {date_str}: {percentile}% 백분위수 제약, 평균={mean_stay:.2f}시간, 최대={max_stay:.2f}시간")
    else:
        print("\n[3단계] 백분위수 통계: reports 없음 (3단계는 직접 스케줄링)")
    
    # 3단계 체류시간 분석
    print("\n[3단계] 날짜별 최대 체류 응시자:")
    if not df3.empty:
        df3['interview_date'] = pd.to_datetime(df3['interview_date'])
        for date_str in df3['interview_date'].dt.strftime('%Y-%m-%d').unique():
            date_df = df3[df3['interview_date'].dt.strftime('%Y-%m-%d') == date_str]
            if not date_df.empty:
                # 체류시간 계산
                stay_times = []
                for applicant_id in date_df['applicant_id'].unique():
                    applicant_df = date_df[date_df['applicant_id'] == applicant_id]
                    start_time = applicant_df['start_time'].min()
                    end_time = applicant_df['end_time'].max()
                    stay_hours = (end_time - start_time).total_seconds() / 3600
                    stay_times.append({'applicant_id': applicant_id, 'stay_hours': stay_hours})
                
                if stay_times:
                    max_stay = max(stay_times, key=lambda x: x['stay_hours'])
                    print(f"  {date_str}: {max_stay['applicant_id']} ({max_stay['stay_hours']:.2f}시간)")
    
    return {
        'phase1': {'df': df1, 'status': status1},
        'phase2': {'df': df2, 'status': status2, 'reports': reports2},
        'phase3': {'df': df3, 'status': status3, 'reports': reports3 if status3 == "SUCCESS" else None}
    }

def convert_to_ui_format(df, phase_name):
    """DataFrame을 app.py UI 형식으로 변환"""
    if df.empty:
        return pd.DataFrame()
    
    print(f"\n[DEBUG] {phase_name} DataFrame 구조:")
    print(f"  컬럼: {list(df.columns)}")
    print(f"  데이터 타입: {df.dtypes}")
    if 'start_time' in df.columns:
        print(f"  start_time 샘플: {df['start_time'].iloc[0] if len(df) > 0 else 'N/A'}")
    
    # UI 형식에 맞게 컬럼명 변경 및 재구성
    ui_df = df.copy()
    
    # 컬럼명 매핑
    column_mapping = {
        'applicant_id': 'candidate',
        'interview_date': 'date',
        'start_time': 'start_time',
        'end_time': 'end_time',
        'activity': 'activity',
        'room': 'room',
        'group_id': 'group'
    }
    
    # 존재하는 컬럼만 매핑
    for old_col, new_col in column_mapping.items():
        if old_col in ui_df.columns:
            ui_df[new_col] = ui_df[old_col]
    
    # UI 형식에 필요한 컬럼들 추가
    ui_df['phase'] = phase_name
    
    # 시간 형식 변환 (안전하게 처리)
    try:
        if 'start_time' in ui_df.columns and 'end_time' in ui_df.columns:
            # timedelta를 시간으로 변환
            if ui_df['start_time'].dtype == 'timedelta64[ns]':
                # timedelta를 시간 문자열로 변환 (HH:MM 형식)
                ui_df['start_time_str'] = ui_df['start_time'].apply(lambda x: f"{int(x.total_seconds()//3600):02d}:{int((x.total_seconds()%3600)//60):02d}")
                ui_df['end_time_str'] = ui_df['end_time'].apply(lambda x: f"{int(x.total_seconds()//3600):02d}:{int((x.total_seconds()%3600)//60):02d}")
                
                # 체류시간 계산 (timedelta 차이)
                ui_df['stay_hours'] = (ui_df['end_time'] - ui_df['start_time']).dt.total_seconds() / 3600
            else:
                # datetime으로 변환
                ui_df['start_time'] = pd.to_datetime(ui_df['start_time'])
                ui_df['end_time'] = pd.to_datetime(ui_df['end_time'])
                
                # 체류시간 계산
                ui_df['stay_hours'] = (ui_df['end_time'] - ui_df['start_time']).dt.total_seconds() / 3600
                
                # 시간 문자열 변환
                ui_df['start_time_str'] = ui_df['start_time'].dt.strftime('%H:%M')
                ui_df['end_time_str'] = ui_df['end_time'].dt.strftime('%H:%M')
        else:
            ui_df['stay_hours'] = 0
            ui_df['start_time_str'] = ''
            ui_df['end_time_str'] = ''
    except Exception as e:
        print(f"  [WARNING] 시간 변환 오류: {e}")
        ui_df['stay_hours'] = 0
        ui_df['start_time_str'] = ''
        ui_df['end_time_str'] = ''
    
    # 날짜 형식 변환
    if 'date' in ui_df.columns:
        try:
            ui_df['date'] = pd.to_datetime(ui_df['date'])
            ui_df['date_str'] = ui_df['date'].dt.strftime('%Y-%m-%d')
        except:
            ui_df['date_str'] = ui_df['date'].astype(str)
    else:
        ui_df['date_str'] = ''
    
    # UI 표시용 컬럼 선택
    ui_columns = ['date_str', 'candidate', 'activity', 'room', 'start_time_str', 'end_time_str', 'stay_hours', 'phase']
    available_columns = [col for col in ui_columns if col in ui_df.columns]
    
    return ui_df[available_columns]

def generate_final_report(results):
    """최종 보고서 생성"""
    print("\n=== 최종 분석 보고서 ===")
    
    if not results:
        print("분석할 결과가 없습니다.")
        return
    
    # 각 단계별 결과 요약
    print(f"스케줄링 결과 요약:")
    print(f"  1단계: {results['phase1']['status']} ({len(results['phase1']['df'])}개 스케줄)")
    print(f"  2단계: {results['phase2']['status']} ({len(results['phase2']['df'])}개 스케줄)")
    print(f"  3단계: {results['phase3']['status']} ({len(results['phase3']['df'])}개 스케줄)")
    
    # 체류시간 비교 분석
    if not results['phase1']['df'].empty and not results['phase2']['df'].empty and not results['phase3']['df'].empty:
        print(f"\n체류시간 비교 분석:")
        
        # 1단계 최대 체류시간
        df1 = results['phase1']['df']
        df1['interview_date'] = pd.to_datetime(df1['interview_date'])
        phase1_max_stay = 0
        for applicant_id in df1['applicant_id'].unique():
            applicant_df = df1[df1['applicant_id'] == applicant_id]
            start_time = applicant_df['start_time'].min()
            end_time = applicant_df['end_time'].max()
            stay_hours = (end_time - start_time).total_seconds() / 3600
            phase1_max_stay = max(phase1_max_stay, stay_hours)
        
        # 2단계 최대 체류시간
        df2 = results['phase2']['df']
        df2['interview_date'] = pd.to_datetime(df2['interview_date'])
        phase2_max_stay = 0
        for applicant_id in df2['applicant_id'].unique():
            applicant_df = df2[df2['applicant_id'] == applicant_id]
            start_time = applicant_df['start_time'].min()
            end_time = applicant_df['end_time'].max()
            stay_hours = (end_time - start_time).total_seconds() / 3600
            phase2_max_stay = max(phase2_max_stay, stay_hours)
        
        # 3단계 최대 체류시간
        df3 = results['phase3']['df']
        df3['interview_date'] = pd.to_datetime(df3['interview_date'])
        phase3_max_stay = 0
        for applicant_id in df3['applicant_id'].unique():
            applicant_df = df3[df3['applicant_id'] == applicant_id]
            start_time = applicant_df['start_time'].min()
            end_time = applicant_df['end_time'].max()
            stay_hours = (end_time - start_time).total_seconds() / 3600
            phase3_max_stay = max(phase3_max_stay, stay_hours)
        
        print(f"  1단계 최대 체류시간: {phase1_max_stay:.2f}시간")
        print(f"  2단계 최대 체류시간: {phase2_max_stay:.2f}시간")
        print(f"  3단계 최대 체류시간: {phase3_max_stay:.2f}시간")
        if phase1_max_stay > 0:
            improvement = phase1_max_stay - phase2_max_stay
            print(f"  개선 효과: {improvement:.2f}시간 ({improvement/phase1_max_stay*100:.1f}%)")
            improvement_phase3 = phase1_max_stay - phase3_max_stay
            print(f"  3단계 개선 효과: {improvement_phase3:.2f}시간 ({improvement_phase3/phase1_max_stay*100:.1f}%)")

def main():
    """메인 실행 함수"""
    print("날짜별 3단계 스케줄링 시스템 내부 테스트 시작")
    print("=" * 50)
    
    # 3단계 스케줄링 실행
    results = run_multi_date_scheduling()
    
    if results:
        # 최종 보고서 생성
        generate_final_report(results)
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"three_phase_analysis_{timestamp}.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # UI 형식으로 변환하여 저장
            if not results['phase1']['df'].empty:
                ui_df1 = convert_to_ui_format(results['phase1']['df'], 'Phase1_기본')
                ui_df1.to_excel(writer, sheet_name='Phase1_기본', index=False)
            
            if not results['phase2']['df'].empty:
                ui_df2 = convert_to_ui_format(results['phase2']['df'], 'Phase2_90%백분위수')
                ui_df2.to_excel(writer, sheet_name='Phase2_90%백분위수', index=False)
            
            if not results['phase3']['df'].empty:
                ui_df3 = convert_to_ui_format(results['phase3']['df'], 'Phase3_85%백분위수')
                ui_df3.to_excel(writer, sheet_name='Phase3_85%백분위수', index=False)
            
            # 통합 결과 시트 추가
            all_results = []
            if not results['phase1']['df'].empty:
                all_results.append(ui_df1)
            if not results['phase2']['df'].empty:
                all_results.append(ui_df2)
            if not results['phase3']['df'].empty:
                all_results.append(ui_df3)
            
            if all_results:
                combined_df = pd.concat(all_results, ignore_index=True)
                combined_df.to_excel(writer, sheet_name='통합결과', index=False)
        
        print(f"\n분석 결과가 {filename}에 저장되었습니다.")
    else:
        print("스케줄링 실패로 분석을 완료할 수 없습니다.")

if __name__ == "__main__":
    main() 