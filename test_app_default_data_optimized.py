#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py 디폴트 데이터 최적화된 CP-SAT 테스트
- 병목 분석 결과 반영
- 로깅 최소화
- 빠른 스케줄링
"""

import logging
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from typing import Tuple

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solver.api import schedule_interviews
from solver.types import SchedulingContext

# 로깅 설정 (최소화)
def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"log/cpsat_optimized_{timestamp}.log"
    
    os.makedirs("log", exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)  # INFO → WARNING으로 변경하여 로그 최소화
    
    # 파일 핸들러 (UTF-8 인코딩)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.WARNING)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_app_default_data():
    """app.py의 디폴트 데이터 반환"""
    # 날짜별 계획
    date_plans = {
        "2025-07-15": {
            "jobs": {"JOB01": 23, "JOB02": 23},
            "selected_activities": ["토론면접", "발표준비", "발표면접"]
        },
        "2025-07-16": {
            "jobs": {"JOB03": 23, "JOB04": 23},
            "selected_activities": ["토론면접", "발표준비", "발표면접"]
        },
        "2025-07-17": {
            "jobs": {"JOB05": 23, "JOB06": 23},
            "selected_activities": ["토론면접", "발표준비", "발표면접"]
        },
        "2025-07-18": {
            "jobs": {"JOB07": 23},
            "selected_activities": ["토론면접", "발표준비", "발표면접"]
        }
    }
    
    # 활동 정의
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
    
    # 방 정의
    rooms = {
        "토론면접실A": {"type": "토론면접실", "capacity": 6},
        "토론면접실B": {"type": "토론면접실", "capacity": 6},
        "발표준비실": {"type": "발표준비실", "capacity": 2},
        "발표면접실A": {"type": "발표면접실", "capacity": 1},
        "발표면접실B": {"type": "발표면접실", "capacity": 1}
    }
    
    # 전역 설정
    global_config = {
        "operating_hours": {
            "2025-07-15": ("09:00", "17:30"),
            "2025-07-16": ("09:00", "17:30"),
            "2025-07-17": ("09:00", "17:30"),
            "2025-07-18": ("09:00", "17:30")
        },
        "precedence_rules": [
            {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "is_adjacent": True}
        ],
        "batched_group_sizes": {
            "토론면접": (4, 6)
        },
        "global_gap_min": 5,
        "max_stay_hours": 8
    }
    
    return date_plans, activities, rooms, global_config

def schedule_single_date_optimized(date_str: str, date_plan: dict, global_config: dict, 
                                 rooms: dict, activities: dict, logger: logging.Logger) -> Tuple[pd.DataFrame, bool]:
    """단일 날짜 최적화된 스케줄링"""
    logger.info(f"📅 [{date_str}] 처리 시작 ({sum(date_plan['jobs'].values())}명)")
    
    try:
        # 최적화된 컨텍스트 (15초 제한, 로깅 최소화)
        context = SchedulingContext(
            time_limit_sec=15.0,  # 30초 → 15초로 단축
            debug=False  # 디버그 로깅 비활성화
        )
        
        # 시간 측정 시작
        start_time = datetime.now()
        logger.info(f"⏱️ [{date_str}] CP-SAT 시작: {start_time}")
        
        # schedule_interviews 호출
        result = schedule_interviews(
            date_plans={date_str: date_plan},
            global_config=global_config,
            rooms=rooms,
            activities=activities,
            logger=logger,
            context=context
        )
        
        # 시간 측정 종료
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        logger.info(f"⏱️ [{date_str}] CP-SAT 완료: {end_time} (소요시간: {elapsed:.2f}초)")
        
        # result가 dict인 경우 처리
        if isinstance(result, dict):
            status = result.get('status', 'UNKNOWN')
            if status == "SUCCESS":
                df = result.get('schedule', pd.DataFrame())
                scheduled_applicants = result.get('summary', {}).get('scheduled_applicants', 0)
                total_applicants = result.get('summary', {}).get('total_applicants', 0)
                logger.info(f"✅ [{date_str}] 성공! {scheduled_applicants}/{total_applicants}명 스케줄링")
                return df, True
            elif status in ["PARTIAL", "FAILED"]:
                # 부분 결과가 있으면 반환
                partial_df = result.get('partial_schedule')
                if partial_df is not None and not partial_df.empty:
                    scheduled_applicants = result.get('scheduled_applicants', 0)
                    total_applicants = result.get('total_applicants', 0)
                    logger.info(f"⚠️ [{date_str}] 부분 성공! {scheduled_applicants}/{total_applicants}명 스케줄링")
                    return partial_df, True
                else:
                    logger.error(f"❌ [{date_str}] 실패: {status}")
                    return pd.DataFrame(), False
            else:
                logger.error(f"❌ [{date_str}] 알 수 없는 상태: {status}")
                return pd.DataFrame(), False
        else:
            # MultiDateResult 객체인 경우 (기존 로직)
            if result.status == "SUCCESS":
                logger.info(f"✅ [{date_str}] 성공! {result.scheduled_applicants}/{result.total_applicants}명 스케줄링")
                df = result.to_dataframe()
                return df, True
            elif result.status == "PARTIAL":
                logger.info(f"⚠️ [{date_str}] 부분 성공! {result.scheduled_applicants}/{result.total_applicants}명 스케줄링")
                df = result.to_dataframe()
                return df, True
            else:
                logger.error(f"❌ [{date_str}] 실패: {result.status}")
                # 실패해도 부분 결과가 있으면 반환
                if hasattr(result, 'to_dataframe'):
                    df = result.to_dataframe()
                    if not df.empty:
                        logger.info(f"📊 [{date_str}] 부분 결과 반환: {len(df)}개 항목")
                        return df, False
                return pd.DataFrame(), False
            
    except Exception as e:
        logger.error(f"💥 [{date_str}] 예외 발생: {str(e)}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return pd.DataFrame(), False

def save_partial_results(all_results, filename):
    """부분 결과를 엑셀로 저장"""
    if not all_results:
        print("❌ 저장할 결과가 없습니다.")
        return
    
    # 모든 결과를 하나의 DataFrame으로 통합
    all_dfs = []
    for date_str, (df, success) in all_results.items():
        if not df.empty:
            all_dfs.append(df)
    
    if not all_dfs:
        print("❌ 저장할 데이터가 없습니다.")
        return
    
    final_df = pd.concat(all_dfs, ignore_index=True)
    
    # 엑셀로 저장
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 전체 스케줄
            final_df.to_excel(writer, sheet_name='전체스케줄', index=False)
            
            # 날짜별 스케줄
            for date_str, (df, success) in all_results.items():
                if not df.empty:
                    sheet_name = f"{date_str.replace('-', '')}"
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 요약 정보
            summary_data = []
            for date_str, (df, success) in all_results.items():
                summary_data.append({
                    '날짜': date_str,
                    '성공여부': '성공' if success else '부분성공',
                    '스케줄수': len(df) if not df.empty else 0
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='요약', index=False)
        
        print(f"✅ 엑셀 파일 저장 완료: {filename}")
        print(f"📊 총 {len(final_df)}개 스케줄 저장")
        
    except Exception as e:
        print(f"❌ 엑셀 저장 실패: {str(e)}")

def main():
    """메인 함수"""
    logger = setup_logging()
    
    print("=== app.py 디폴트 데이터 최적화된 CP-SAT 테스트 시작 ===")
    
    # app.py 디폴트 데이터 가져오기
    date_plans, activities, rooms, global_config = get_app_default_data()
    
    total_applicants = sum(sum(plan['jobs'].values()) for plan in date_plans.values())
    print(f"총 지원자: {total_applicants}명, 날짜: {len(date_plans)}일")
    
    # 날짜별 순차 처리 (병목 분석 결과 반영)
    all_results = {}
    
    for date_str, date_plan in date_plans.items():
        print(f"\n📅 {date_str} 처리 중...")
        
        # 단일 날짜 스케줄링
        df, success = schedule_single_date_optimized(
            date_str, date_plan, global_config, rooms, activities, logger
        )
        
        all_results[date_str] = (df, success)
        
        # 부분 결과 즉시 저장
        if not df.empty:
            partial_filename = f"partial_result_{date_str.replace('-', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            save_partial_results({date_str: (df, success)}, partial_filename)
    
    # 최종 결과 저장
    final_filename = f"optimized_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    save_partial_results(all_results, final_filename)
    
    # 결과 요약
    success_count = sum(1 for _, success in all_results.values() if success)
    total_count = len(all_results)
    
    print(f"\n=== 최종 결과 ===")
    print(f"성공: {success_count}/{total_count}일")
    print(f"총 스케줄: {sum(len(df) for df, _ in all_results.values() if not df.empty)}개")
    
    if success_count == total_count:
        print("🎉 모든 날짜에서 성공!")
    elif success_count > 0:
        print("🔶 일부 날짜에서 성공")
    else:
        print("❌ 모든 날짜에서 실패")

if __name__ == "__main__":
    main() 