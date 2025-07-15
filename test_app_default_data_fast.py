#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py 디폴트 데이터 빠른 CP-SAT 테스트
- 날짜별 순차 처리로 속도 개선
- 제한시간 단축 (30초/날짜)
- 부분 결과 우선 저장
"""

import logging
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from typing import Tuple

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from app import create_session_state  # 이 import 제거
from solver.api import schedule_interviews
from solver.types import SchedulingContext

# 로깅 설정 (최소화)
def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"log/cpsat_fast_debug_{timestamp}.log"
    
    os.makedirs("log", exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # DEBUG → INFO로 변경
    
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def create_app_default_config():
    """app.py 디폴트 설정 생성"""
    today = datetime.now().date()
    selected_activities = ["토론면접", "발표준비", "발표면접"]
    
    # 날짜별 계획 (app.py 디폴트)
    date_plans = {
        today.strftime('%Y-%m-%d'): {
            "jobs": {"JOB01": 23, "JOB02": 23},
            "selected_activities": selected_activities
        },
        (today + timedelta(days=1)).strftime('%Y-%m-%d'): {
            "jobs": {"JOB03": 20, "JOB04": 20},
            "selected_activities": selected_activities
        },
        (today + timedelta(days=2)).strftime('%Y-%m-%d'): {
            "jobs": {"JOB05": 12, "JOB06": 15, "JOB07": 6},
            "selected_activities": selected_activities
        },
        (today + timedelta(days=3)).strftime('%Y-%m-%d'): {
            "jobs": {"JOB08": 6, "JOB09": 6, "JOB10": 3, "JOB11": 3},
            "selected_activities": selected_activities
        }
    }
    
    # 활동 정의 (app.py 디폴트)
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
    
    # 방 설정 (app.py 디폴트)
    rooms = {
        "토론면접실": {"count": 2, "capacity": 6},
        "발표준비실": {"count": 1, "capacity": 2},
        "발표면접실": {"count": 2, "capacity": 1}
    }
    
    # 전역 설정 (app.py 디폴트)
    global_config = {
        "precedence": [("발표준비", "발표면접", 0, True)],
        "operating_hours": {"start": "09:00", "end": "17:30"},
        "batched_group_sizes": {"토론면접": [4, 6]},
        "global_gap_min": 5,
        "max_stay_hours": 5
    }
    
    return date_plans, activities, rooms, global_config

def schedule_single_date_fast(date_str: str, date_plan: dict, global_config: dict, 
                            rooms: dict, activities: dict, logger: logging.Logger) -> Tuple[pd.DataFrame, bool]:
    """단일 날짜 빠른 스케줄링"""
    logger.info(f"📅 [{date_str}] 처리 시작 ({sum(date_plan['jobs'].values())}명)")
    
    # 빠른 스케줄링 시작
    logger.info(f"🚀 [{date_str}] 빠른 스케줄링 시작")
    
    try:
        # SchedulingContext 수정 - 올바른 파라미터 사용
        context = SchedulingContext(
            time_limit_sec=30.0,  # 30초 제한
            debug=True  # enable_progress_logging → debug로 변경
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
    try:
        # 성공한 결과만 수집
        successful_dfs = []
        for date_str, (df, success) in all_results.items():
            if success and df is not None:
                successful_dfs.append(df)
        
        if successful_dfs:
            # 모든 결과 합치기
            combined_df = pd.concat(successful_dfs, ignore_index=True)
            
            # 엑셀로 저장
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                combined_df.to_excel(writer, sheet_name='스케줄', index=False)
                
                # 요약 시트
                summary_data = {
                    '날짜': list(all_results.keys()),
                    '성공여부': [success for _, success in all_results.values()],
                    '지원자수': [len(df) if df is not None else 0 for df, _ in all_results.values()]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='요약', index=False)
            
            return True, len(combined_df)
        else:
            return False, 0
            
    except Exception as e:
        print(f"엑셀 저장 실패: {e}")
        return False, 0

def main():
    logger = setup_logging()
    
    try:
        logger.info("=== app.py 디폴트 데이터 빠른 CP-SAT 테스트 시작 ===")
        
        # 설정 생성
        date_plans, activities, rooms, global_config = create_app_default_config()
        
        # 설정 요약
        total_applicants = sum(sum(plan["jobs"].values()) for plan in date_plans.values())
        logger.info(f"총 지원자: {total_applicants}명, 날짜: {len(date_plans)}일")
        
        # 날짜별 순차 처리
        all_results = {}
        successful_dates = []
        failed_dates = []
        
        for date_str, date_plan in date_plans.items():
            logger.info(f"📅 [{date_str}] 처리 시작 ({sum(date_plan['jobs'].values())}명)")
            
            # 단일 날짜 스케줄링
            df, success = schedule_single_date_fast(
                date_str, date_plan, global_config, rooms, activities, logger
            )
            
            all_results[date_str] = (df, success)
            
            if success:
                successful_dates.append(date_str)
                logger.info(f"✅ [{date_str}] 완료 - {len(df)}개 스케줄")
            else:
                failed_dates.append(date_str)
                logger.warning(f"❌ [{date_str}] 실패")
            
            # 부분 결과 즉시 저장 (매 날짜마다)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            partial_filename = f"fast_partial_result_{timestamp}.xlsx"
            saved, count = save_partial_results(all_results, partial_filename)
            
            if saved:
                logger.info(f"💾 부분 결과 저장: {partial_filename} ({count}개 스케줄)")
        
        # 최종 결과 분석
        logger.info("=== 최종 결과 ===")
        logger.info(f"성공한 날짜: {len(successful_dates)}/{len(date_plans)}")
        logger.info(f"실패한 날짜: {len(failed_dates)}/{len(date_plans)}")
        
        if successful_dates:
            logger.info(f"✅ 성공한 날짜: {', '.join(successful_dates)}")
        
        if failed_dates:
            logger.warning(f"❌ 실패한 날짜: {', '.join(failed_dates)}")
        
        # 최종 엑셀 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"fast_final_result_{timestamp}.xlsx"
        saved, total_count = save_partial_results(all_results, final_filename)
        
        if saved:
            logger.info(f"🎉 최종 결과 저장: {final_filename} ({total_count}개 스케줄)")
            logger.info(f"성공률: {(len(successful_dates)/len(date_plans)*100):.1f}%")
        else:
            logger.error("💥 최종 결과 저장 실패")
        
    except Exception as e:
        logger.error(f"💥 전체 프로세스 실패: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 