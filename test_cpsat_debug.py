#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CP-SAT 모델 실패 원인 분석을 위한 디버깅 테스트
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta, date
import sys
import os
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import core
from solver.api import solve_for_days_v2
from solver.types import ProgressInfo

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_debug_session_state():
    """app.py UI와 동일한 구조의 세션 상태 생성"""
    # 활동
    activities = pd.DataFrame({
        "activity": ["토론면접", "발표준비", "발표면접"],
        "use": [True, True, True],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    # 직무-활동 매핑
    job_acts_map = pd.DataFrame({
        "code": ["SW"],
        "count": [10],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True],
    })
    # 방 계획
    room_plan = pd.DataFrame({
        "date": ["2024-01-15"],  # date 컬럼 추가
        "토론면접실_count": [2], "토론면접실_cap": [6],
        "발표준비실_count": [1], "발표준비실_cap": [2],
        "발표면접실_count": [2], "발표면접실_cap": [1],
    })
    # 운영시간
    oper_window = pd.DataFrame({
        "date": ["2024-01-15"],  # date 컬럼 추가
        "code": ["SW"],
        "start_time": ["09:00"],
        "end_time": ["18:00"],
    })
    # 선후행
    precedence = pd.DataFrame({
        "predecessor": ["토론면접", "발표준비"],
        "successor": ["발표준비", "발표면접"],
        "gap_min": [0, 0],
        "adjacent": [False, True],
    })
    # 지원자
    candidates = pd.DataFrame({
        "id": [f"지원자{i:02d}" for i in range(1, 11)],
        "code": ["SW"] * 10,
        "name": [f"지원자{i:02d}" for i in range(1, 11)],
        "interview_date": ["2024-01-15"] * 10,
        "activity": ["토론면접,발표준비,발표면접"] * 10,  # 리스트 → 문자열로 변환
    })
    # candidates_exp(확장)
    candidates_exp = candidates.copy()
    # 날짜
    interview_dates = ["2024-01-15"]
    # session_state dict
    return {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "precedence": precedence,
        "candidates": candidates,
        "candidates_exp": candidates_exp,
        "interview_dates": interview_dates,
        "interview_date": "2024-01-15",
        "group_min_size": 4,
        "group_max_size": 6,
        "global_gap_min": 5,
        "max_stay_hours": 8,
    }

def test_cpsat_debug():
    """CP-SAT 디버깅 테스트"""
    logger.info("🔍 CP-SAT 디버깅 테스트 시작")
    
    # 디버깅용 세션 상태 생성
    session_state = create_debug_session_state()
    
    # 설정 빌드
    logger.info("🔧 설정 빌드 중...")
    config = core.build_config(session_state)
    
    if not config:
        logger.error("❌ 설정 빌드 실패")
        return
    
    logger.info(f"✅ 설정 빌드 완료: {len(config['interview_dates'])}개 날짜, {len(config['candidates'])}명 지원자, {len(config['room_plan'])}개 방, {len(config['activities'])}개 활동, {len(config['precedence'])}개 선후행")
    
    # 데이터 매핑 검증 로그 추가
    logger.info("🔍 데이터 매핑 검증:")
    logger.info(f"  - room_plan 컬럼: {list(config['room_plan'].columns)}")
    logger.info(f"  - oper_window 컬럼: {list(config['oper_window'].columns)}")
    logger.info(f"  - candidates 컬럼: {list(config['candidates'].columns)}")
    logger.info(f"  - activities 컬럼: {list(config['activities'].columns)}")
    
    # 날짜 매칭 검증
    room_dates = set(config['room_plan']['date'].astype(str)) if 'date' in config['room_plan'].columns else set()
    candidate_dates = set(config['candidates']['interview_date'].astype(str)) if 'interview_date' in config['candidates'].columns else set()
    logger.info(f"  - room_plan 날짜: {room_dates}")
    logger.info(f"  - candidates 날짜: {candidate_dates}")
    logger.info(f"  - 날짜 매칭: {bool(room_dates & candidate_dates)}")
    
    # 방 타입 매칭 검증
    activity_room_types = set(config['activities']['room_type'].dropna())
    room_plan_columns = set(config['room_plan'].columns)
    room_types_in_plan = {col.replace('_count', '').replace('_cap', '') for col in room_plan_columns if '_count' in col or '_cap' in col}
    logger.info(f"  - 활동별 방 타입: {activity_room_types}")
    logger.info(f"  - room_plan 방 타입: {room_types_in_plan}")
    logger.info(f"  - 방 타입 매칭: {bool(activity_room_types & room_types_in_plan)}")
    
    # 필수 컬럼 검증
    required_columns = {
        'room_plan': ['date'],
        'oper_window': ['date', 'code', 'start_time', 'end_time'],
        'candidates': ['id', 'code', 'interview_date'],
        'activities': ['activity', 'use', 'mode', 'duration_min', 'room_type'],
        'precedence': ['predecessor', 'successor']
    }
    
    logger.info("🔍 필수 컬럼 검증:")
    for df_name, required_cols in required_columns.items():
        if df_name in config:
            df = config[df_name]
            missing_cols = [col for col in required_cols if col not in df.columns]
            logger.info(f"  - {df_name}: {'✅' if not missing_cols else f'❌ ({missing_cols})'}")
        else:
            logger.info(f"  - {df_name}: ❌ (DataFrame 없음)")
    
    # CP-SAT 모델 빌드 전 데이터 유효성 검증
    logger.info("🔍 CP-SAT 모델 빌드 전 데이터 유효성 검증:")
    
    # 1. 지원자별 활동 매핑 검증
    if 'candidates' in config and 'activity' in config['candidates'].columns:
        candidate_activities = config['candidates']['activity'].tolist()
        logger.info(f"  - 지원자별 활동 수: {len(candidate_activities)}")
        logger.info(f"  - 첫 번째 지원자 활동: {candidate_activities[0] if candidate_activities else 'None'}")
    
    # 2. 활동 정의 검증
    if 'activities' in config:
        activities_df = config['activities']
        active_activities = activities_df[activities_df['use'] == True]['activity'].tolist()
        logger.info(f"  - 활성화된 활동: {active_activities}")
        logger.info(f"  - 활동별 모드: {dict(zip(activities_df['activity'], activities_df['mode']))}")
    
    # 3. 방 용량 검증
    if 'room_plan' in config:
        room_plan_df = config['room_plan']
        room_capacities = {}
        for col in room_plan_df.columns:
            if '_cap' in col:
                room_type = col.replace('_cap', '')
                capacity = room_plan_df[col].iloc[0]
                room_capacities[room_type] = capacity
        logger.info(f"  - 방별 용량: {room_capacities}")
    
    # 4. 운영시간 검증
    if 'oper_window' in config:
        oper_df = config['oper_window']
        logger.info(f"  - 운영시간: {oper_df['start_time'].iloc[0]} ~ {oper_df['end_time'].iloc[0]}")
    
    # 5. 선후행 규칙 검증
    if 'precedence' in config and not config['precedence'].empty:
        precedence_rules = []
        for _, row in config['precedence'].iterrows():
            rule = f"{row['predecessor']} → {row['successor']}"
            if 'gap_min' in row and row['gap_min'] > 0:
                rule += f" (간격: {row['gap_min']}분)"
            precedence_rules.append(rule)
        logger.info(f"  - 선후행 규칙: {precedence_rules}")
    
    # 6. 데이터 타입 검증
    logger.info("🔍 데이터 타입 검증:")
    if 'candidates' in config and 'activity' in config['candidates'].columns:
        sample_activity = config['candidates']['activity'].iloc[0]
        logger.info(f"  - 첫 번째 지원자 활동 타입: {type(sample_activity)}")
        logger.info(f"  - 첫 번째 지원자 활동 값: {sample_activity}")
        if isinstance(sample_activity, list):
            logger.info(f"  - 활동 리스트 길이: {len(sample_activity)}")
            logger.info(f"  - 활동 리스트 내용: {sample_activity}")
    
    # 7. ACT_SPACE 구조 검증 (예상)
    if 'activities' in config:
        activities_df = config['activities']
        expected_act_space = {}
        for _, row in activities_df.iterrows():
            if row['use']:
                expected_act_space[row['activity']] = {
                    'duration': int(row['duration_min']),
                    'required_rooms': [row['room_type']]
                }
        logger.info(f"  - 예상 ACT_SPACE 키: {list(expected_act_space.keys())}")
        logger.info(f"  - 예상 ACT_SPACE 구조: {expected_act_space}")
    
    # 8. 데이터 변환 과정 로그
    logger.info("🔍 데이터 변환 과정:")
    if 'candidates' in config and 'activity' in config['candidates'].columns:
        sample_activity = config['candidates']['activity'].iloc[0]
        logger.info(f"  - 변환 후 활동 타입: {type(sample_activity)}")
        logger.info(f"  - 변환 후 활동 값: {sample_activity}")
        if isinstance(sample_activity, str):
            activity_list = sample_activity.split(',')
            logger.info(f"  - 파싱된 활동 리스트: {activity_list}")
            logger.info(f"  - 파싱된 활동 수: {len(activity_list)}")
    
    # 9. CP-SAT 결과 처리 예상 로그
    logger.info("🔍 CP-SAT 결과 처리 예상:")
    logger.info("  - CP-SAT 실행 후 결과 DataFrame 생성 예상")
    logger.info("  - DataFrame 컬럼명 변환 과정 예상")
    logger.info("  - 최종 엑셀 출력 형식 변환 예상")
    
    # 10. 디버깅 모드 설정
    logger.info("🔍 디버깅 모드 설정:")
    logger.info(f"  - debug=True로 설정됨")
    logger.info(f"  - 상세 로그 출력 활성화")
    logger.info(f"  - CP-SAT 내부 통계 출력 활성화")
    
    # 스케줄링 실행
    logger.info("🚀 스케줄링 실행 중...")
    params = {
        "min_gap_min": 5,
        "time_limit_sec": 60,
        "max_stay_hours": 8,
        "group_min_size": 4,
        "group_max_size": 6,
    }
    def progress_callback(info: ProgressInfo):
        logger.info(f"📊 진행상황: {info.current_step}/{info.total_steps} - {info.message}")
    try:
        status, result_df, logs = core.run_solver(config, params, debug=True)
        if status in ["SUCCESS", "OPTIMAL", "FEASIBLE"]:
            logger.info("✅ 스케줄링 성공!")
            logger.info(f"결과 DataFrame shape: {result_df.shape if result_df is not None else 'None'}")
        else:
            logger.error(f"❌ 스케줄링 실패: {status}")
            logger.error(f"로그: {logs}")
    except Exception as e:
        logger.error(f"❌ 스케줄링 중 예외 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_cpsat_debug() 