#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py 디폴트 데이터 CP-SAT 멀티데이트 테스트
- 더 작은 규모로 테스트하여 CP-SAT 적용 가능성 확인
- 상세한 진단 로그로 문제점 파악
"""

import logging
import sys
import os
from datetime import datetime, timedelta
import pandas as pd

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_session_state
from solver.api import schedule_interviews
from solver.types import SchedulingContext

# 로깅 설정
def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"log/cpsat_small_scale_debug_{timestamp}.log"
    
    # 로그 디렉토리 생성
    os.makedirs("log", exist_ok=True)
    
    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # 파일 핸들러 (UTF-8 인코딩)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def main():
    logger = setup_logging()
    
    try:
        logger.info("=== app.py 디폴트 데이터 CP-SAT 소규모 테스트 시작 ===")
        
        # 1. app.py 디폴트 세션 상태 생성
        logger.info("=== app.py 디폴트 세션 상태 생성 시작 ===")
        session_state = create_session_state()
        
        # 진단: 기본 설정 확인
        logger.info(f"[진단] 기본 활동 템플릿: {len(session_state.activity_templates)}개 활동")
        logger.info(f"[진단] 스마트 직무 매핑: {len(session_state.smart_job_mapping)}개 직무")
        logger.info(f"[진단] 기본 선후행 제약: {len(session_state.precedence_constraints)}개 규칙")
        logger.info(f"[진단] 기본 운영 시간: {session_state.operating_hours['start_time']} ~ {session_state.operating_hours['end_time']}")
        logger.info(f"[진단] 스마트 방 템플릿: {len(session_state.smart_room_templates)}개 방 타입")
        logger.info(f"[진단] 방 계획: {len(session_state.room_plans)}개 행")
        logger.info(f"[진단] 운영 시간: {len(session_state.operating_hours_plans)}개 행")
        logger.info(f"[진단] 집단면접 설정: {session_state.group_interview_settings['min_size']}~{session_state.group_interview_settings['max_size']}명, 간격 {session_state.group_interview_settings['interval_minutes']}분, 최대 체류 {session_state.group_interview_settings['max_stay_hours']}시간")
        logger.info(f"[진단] 멀티 날짜 계획: {len(session_state.multi_date_plans)}일")
        
        # 2. 가상 지원자 생성 (소규모로 조정)
        logger.info("=== 소규모 가상 지원자 생성 시작 ===")
        
        # 지원자 수를 줄여서 테스트 (기존 23명 → 6명으로 축소)
        small_applicants = []
        job_codes = ['JOB01']  # 하나의 직무만 테스트
        
        for job_code in job_codes:
            for i in range(1, 7):  # 6명만 생성
                applicant_id = f"{job_code}_{i:03d}"
                small_applicants.append({
                    'id': applicant_id,
                    'code': job_code,
                    'activity': ['토론면접', '발표준비', '발표면접'],
                    'interview_date': session_state.multi_date_plans[0]['date']  # 첫 번째 날짜만 사용
                })
        
        # 진단: 생성된 지원자 확인
        logger.info(f"[진단] 소규모 가상 지원자 생성 완료: {len(small_applicants)}명")
        logger.info(f"[진단] 지원자 샘플:")
        df_sample = pd.DataFrame(small_applicants[:5])
        logger.info(f"\n{df_sample}")
        logger.info(f"[진단] 가상 지원자: {len(small_applicants)}명")
        logger.info(f"[진단] 면접 날짜: 1일 (첫 번째 날짜만)")
        
        logger.info("=== app.py 디폴트 세션 상태 생성 완료 ===")
        
        # 3. schedule_interviews API 형식으로 변환
        logger.info("=== schedule_interviews API 형식으로 변환 시작 ===")
        
        # 첫 번째 날짜만 사용
        first_date_plan = session_state.multi_date_plans[0]
        
        # API 입력 형식으로 변환
        api_input = {
            'dates': [{
                'date': first_date_plan['date'],
                'start_time': session_state.operating_hours['start_time'],
                'end_time': session_state.operating_hours['end_time']
            }],
            'activities': [
                {
                    'name': template['name'],
                    'mode': template['mode'],
                    'duration': template['duration'],
                    'min_capacity': template['min_capacity'],
                    'max_capacity': template['max_capacity'],
                    'required_rooms': template['required_rooms']
                }
                for template in session_state.activity_templates
            ],
            'rooms': [
                {
                    'name': room['name'],
                    'type': room['type'],
                    'capacity': room['capacity']
                }
                for room in session_state.room_plans
            ],
            'precedence_constraints': [
                {
                    'before_activity': constraint['before_activity'],
                    'after_activity': constraint['after_activity'],
                    'gap_minutes': constraint['gap_minutes'],
                    'is_adjacent': constraint['is_adjacent']
                }
                for constraint in session_state.precedence_constraints
            ],
            'applicants': small_applicants
        }
        
        # 진단: 변환 결과 확인
        logger.info(f"[변환] 날짜별 계획: {len(api_input['dates'])}일")
        logger.info(f"[변환] 활동 설정: {len(api_input['activities'])}개")
        logger.info(f"[변환] 방 설정: {len(api_input['rooms'])}개")
        logger.info(f"[변환] 전역 설정: {len(api_input['precedence_constraints'])}개 선후행 규칙")
        
        logger.info("=== schedule_interviews API 형식 변환 완료 ===")
        
        # 4. schedule_interviews API 실행
        logger.info("=== schedule_interviews API 실행 시작 ===")
        
        # CP-SAT 컨텍스트 설정 (더 긴 제한시간)
        context = SchedulingContext(
            time_limit_sec=300,  # 5분으로 증가
            debug=True,
            enable_progress_logging=True
        )
        
        # 스케줄링 실행
        result = schedule_interviews(
            dates=api_input['dates'],
            activities=api_input['activities'],
            rooms=api_input['rooms'],
            precedence_constraints=api_input['precedence_constraints'],
            applicants=api_input['applicants'],
            context=context
        )
        
        # 5. 결과 처리
        logger.info("=== 결과 처리 시작 ===")
        
        if result.success:
            logger.info("✅ 스케줄링 성공!")
            logger.info(f"[결과] 스케줄된 지원자: {len(result.schedules)}명")
            logger.info(f"[결과] 총 소요 시간: {result.total_duration:.2f}초")
            
            # Excel 파일 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_filename = f"small_scale_cpsat_result_{timestamp}.xlsx"
            
            try:
                # 결과를 DataFrame으로 변환
                schedule_data = []
                for schedule in result.schedules:
                    for activity in schedule.activities:
                        schedule_data.append({
                            '지원자ID': schedule.applicant_id,
                            '직무코드': schedule.applicant_id.split('_')[0],
                            '활동명': activity.name,
                            '시작시간': activity.start_time.strftime('%H:%M'),
                            '종료시간': activity.end_time.strftime('%H:%M'),
                            '방': activity.room,
                            '그룹ID': getattr(activity, 'group_id', ''),
                            '날짜': activity.start_time.date().strftime('%Y-%m-%d')
                        })
                
                df_result = pd.DataFrame(schedule_data)
                
                # Excel 파일로 저장
                with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                    df_result.to_excel(writer, sheet_name='스케줄', index=False)
                    
                    # 요약 시트 추가
                    summary_data = {
                        '항목': ['총 지원자 수', '총 활동 수', '스케줄링 성공 여부', '총 소요 시간(초)'],
                        '값': [len(result.schedules), len(schedule_data), '성공', result.total_duration]
                    }
                    df_summary = pd.DataFrame(summary_data)
                    df_summary.to_excel(writer, sheet_name='요약', index=False)
                
                logger.info(f"✅ Excel 파일 생성 완료: {excel_filename}")
                
            except Exception as e:
                logger.error(f"❌ Excel 파일 생성 실패: {e}")
                
        else:
            logger.error("❌ 스케줄링 실패!")
            logger.error(f"[오류] {result.error_message}")
            
            # 부분 결과가 있다면 저장
            if hasattr(result, 'partial_schedules') and result.partial_schedules:
                logger.info(f"[부분 결과] {len(result.partial_schedules)}명의 부분 스케줄 저장")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                excel_filename = f"small_scale_cpsat_partial_{timestamp}.xlsx"
                
                try:
                    # 부분 결과를 DataFrame으로 변환
                    schedule_data = []
                    for schedule in result.partial_schedules:
                        for activity in schedule.activities:
                            schedule_data.append({
                                '지원자ID': schedule.applicant_id,
                                '직무코드': schedule.applicant_id.split('_')[0],
                                '활동명': activity.name,
                                '시작시간': activity.start_time.strftime('%H:%M'),
                                '종료시간': activity.end_time.strftime('%H:%M'),
                                '방': activity.room,
                                '그룹ID': getattr(activity, 'group_id', ''),
                                '날짜': activity.start_time.date().strftime('%Y-%m-%d')
                            })
                    
                    df_result = pd.DataFrame(schedule_data)
                    
                    # Excel 파일로 저장
                    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                        df_result.to_excel(writer, sheet_name='부분스케줄', index=False)
                        
                        # 오류 요약 시트 추가
                        error_data = {
                            '항목': ['총 지원자 수', '성공한 지원자 수', '실패한 지원자 수', '오류 메시지'],
                            '값': [len(small_applicants), len(result.partial_schedules), len(small_applicants) - len(result.partial_schedules), result.error_message]
                        }
                        df_error = pd.DataFrame(error_data)
                        df_error.to_excel(writer, sheet_name='오류요약', index=False)
                    
                    logger.info(f"✅ 부분 결과 Excel 파일 생성 완료: {excel_filename}")
                    
                except Exception as e:
                    logger.error(f"❌ 부분 결과 Excel 파일 생성 실패: {e}")
        
        logger.info("=== 결과 처리 완료 ===")
        
    except Exception as e:
        logger.error(f"❌ 전체 프로세스 실패: {e}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 