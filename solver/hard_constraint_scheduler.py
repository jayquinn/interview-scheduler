#!/usr/bin/env python3
"""
하드 제약 적용 2차 스케줄링 시스템
날짜별 하드 제약값을 적용하여 재스케줄링 수행
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging

from .hard_constraint_analyzer import HardConstraintAnalyzer

class HardConstraintScheduler:
    """하드 제약 스케줄러"""
    
    def __init__(self, percentile: float = 90.0):
        """
        초기화
        
        Args:
            percentile: 사용할 분위수 (기본값: 90.0)
        """
        self.analyzer = HardConstraintAnalyzer(percentile)
        self.logger = logging.getLogger(__name__)
        
    def run_two_phase_scheduling(self, 
                                cfg_ui: dict,
                                params: dict = None,
                                debug: bool = False,
                                progress_callback = None) -> Dict[str, Any]:
        """
        2단계 스케줄링 실행
        
        Args:
            cfg_ui: UI 설정
            params: 추가 파라미터
            debug: 디버그 모드
            progress_callback: 진행상황 콜백
            
        Returns:
            2단계 스케줄링 결과
        """
        self.logger.info("=== 2단계 스케줄링 시작 ===")
        
        # 1단계: 초기 스케줄링 (소프트 제약만 적용)
        self.logger.info("1단계: 초기 스케줄링 (소프트 제약)")
        
        # 소프트 제약으로 1차 스케줄링 (순환 import 방지를 위해 동적 import)
        from .api import solve_for_days_v2
        phase1_params = params.copy() if params else {}
        phase1_params['max_stay_hours'] = 12  # 충분히 큰 값으로 설정
        
        status1, df1, logs1, limit1 = solve_for_days_v2(
            cfg_ui, 
            phase1_params, 
            debug, 
            progress_callback
        )
        
        if status1 != "SUCCESS":
            return {
                'status': 'PHASE1_FAILED',
                'error': f"1단계 스케줄링 실패: {status1}",
                'logs': logs1,
                'phase1_result': None,
                'phase2_result': None,
                'constraint_analysis': None
            }
        
        self.logger.info(f"1단계 완료: {len(df1)}개 스케줄 생성")
        
        # 2단계: 체류시간 분석 및 하드 제약 산출
        self.logger.info("2단계: 체류시간 분석 및 하드 제약 산출")
        
        constraint_analysis = self.analyzer.analyze_stay_times_by_date(df1)
        
        if not constraint_analysis:
            return {
                'status': 'ANALYSIS_FAILED',
                'error': "체류시간 분석 실패",
                'logs': logs1,
                'phase1_result': df1,
                'phase2_result': None,
                'constraint_analysis': None
            }
        
        # 하드 제약값 추출
        hard_constraints = self.analyzer.get_hard_constraints(constraint_analysis)
        
        self.logger.info(f"하드 제약 산출 완료: {len(hard_constraints)}개 날짜")
        for date, constraint in hard_constraints.items():
            self.logger.info(f"  {date}: {constraint:.1f}시간")
        
        # 3단계: 하드 제약 적용 2차 스케줄링
        self.logger.info("3단계: 하드 제약 적용 2차 스케줄링")
        
        # 하드 제약을 적용한 2차 스케줄링
        phase2_result = self._apply_hard_constraints(
            cfg_ui, hard_constraints, params, debug, progress_callback
        )
        
        # 결과 정리
        result = {
            'status': 'SUCCESS',
            'phase1_result': df1,
            'phase2_result': phase2_result.get('schedule'),
            'constraint_analysis': constraint_analysis,
            'hard_constraints': hard_constraints,
            'phase2_status': phase2_result.get('status'),
            'phase2_logs': phase2_result.get('logs', ''),
            'exceed_analysis': phase2_result.get('exceed_analysis', {})
        }
        
        self.logger.info("=== 2단계 스케줄링 완료 ===")
        return result
    
    def _apply_hard_constraints(self, 
                               cfg_ui: dict,
                               hard_constraints: Dict[str, float],
                               params: dict = None,
                               debug: bool = False,
                               progress_callback = None) -> Dict[str, Any]:
        """
        하드 제약을 적용한 스케줄링
        
        Args:
            cfg_ui: UI 설정
            hard_constraints: 날짜별 하드 제약값
            params: 추가 파라미터
            debug: 디버그 모드
            progress_callback: 진행상황 콜백
            
        Returns:
            하드 제약 적용 결과
        """
        # 하드 제약을 적용한 파라미터 생성
        phase2_params = params.copy() if params else {}
        
        # 각 날짜별로 하드 제약 적용
        date_overrides = {}
        for date_str, constraint_hours in hard_constraints.items():
            date_overrides[date_str] = {
                'max_stay_hours': constraint_hours
            }
        
        # UI 설정에 날짜별 오버라이드 추가
        cfg_with_constraints = cfg_ui.copy()
        if 'multidate_plans' in cfg_with_constraints:
            for date_str, plan in cfg_with_constraints['multidate_plans'].items():
                if date_str in date_overrides:
                    if 'overrides' not in plan:
                        plan['overrides'] = {}
                    plan['overrides'].update(date_overrides[date_str])
        
        # 2차 스케줄링 실행 (순환 import 방지를 위해 동적 import)
        from .api import solve_for_days_v2
        status2, df2, logs2, limit2 = solve_for_days_v2(
            cfg_with_constraints,
            phase2_params,
            debug,
            progress_callback
        )
        
        if status2 != "SUCCESS":
            return {
                'status': 'PHASE2_FAILED',
                'error': f"2차 스케줄링 실패: {status2}",
                'logs': logs2,
                'schedule': None,
                'exceed_analysis': {}
            }
        
        # 🔧 하드 제약 강제 적용 후처리
        self.logger.info("🔧 하드 제약 강제 적용 후처리 시작")
        adjusted_df = self._force_apply_hard_constraints(df2, hard_constraints)
        
        # 초과자 분석
        exceed_analysis = self._analyze_constraint_violations(adjusted_df, hard_constraints)
        
        return {
            'status': 'SUCCESS',
            'schedule': adjusted_df,
            'logs': logs2,
            'exceed_analysis': exceed_analysis
        }
    
    def _force_apply_hard_constraints(self, 
                                     schedule_df: pd.DataFrame,
                                     hard_constraints: Dict[str, float]) -> pd.DataFrame:
        """
        하드 제약을 강제 적용하는 후처리
        
        Args:
            schedule_df: 원본 스케줄 DataFrame
            hard_constraints: 날짜별 하드 제약값
            
        Returns:
            조정된 스케줄 DataFrame
        """
        if schedule_df.empty:
            return schedule_df
        
        # 지원자별 체류시간 계산
        stay_times = self.analyzer._calculate_stay_times(schedule_df)
        
        if stay_times.empty:
            return schedule_df
        
        adjusted_df = schedule_df.copy()
        total_adjustments = 0
        
        for interview_date, group_data in stay_times.groupby('interview_date'):
            date_str = str(interview_date)
            constraint_hours = hard_constraints.get(date_str, float('inf'))
            
            # 제약 위반자 찾기
            violators = group_data[group_data['stay_hours'] > constraint_hours]
            
            if violators.empty:
                continue
            
            self.logger.info(f"🔧 {date_str}: {len(violators)}명 제약 위반자 조정 시작 (제약: {constraint_hours:.1f}시간)")
            
            # 각 위반자에 대해 조정 시도
            for _, violator in violators.iterrows():
                applicant_id = violator['applicant_id']
                current_stay_hours = violator['stay_hours']
                
                # 해당 지원자의 스케줄 찾기
                applicant_schedule = adjusted_df[
                    (adjusted_df['applicant_id'] == applicant_id) & 
                    (adjusted_df['interview_date'] == interview_date)
                ].copy()
                
                if applicant_schedule.empty:
                    continue
                
                # 체류시간 단축을 위한 조정 시도
                adjusted = self._adjust_applicant_schedule(
                    applicant_schedule, 
                    current_stay_hours, 
                    constraint_hours,
                    adjusted_df,
                    interview_date
                )
                
                if adjusted:
                    total_adjustments += 1
                    self.logger.debug(f"  ✅ {applicant_id}: {current_stay_hours:.1f}h → {constraint_hours:.1f}h 이하로 조정")
                else:
                    self.logger.warning(f"  ❌ {applicant_id}: 조정 실패 (현재: {current_stay_hours:.1f}h)")
        
        self.logger.info(f"🔧 하드 제약 강제 적용 완료: {total_adjustments}명 조정")
        return adjusted_df
    
    def _adjust_applicant_schedule(self,
                                  applicant_schedule: pd.DataFrame,
                                  current_stay_hours: float,
                                  target_hours: float,
                                  full_schedule: pd.DataFrame,
                                  interview_date) -> bool:
        """
        개별 지원자의 스케줄을 조정하여 체류시간 단축
        
        Args:
            applicant_schedule: 지원자의 스케줄
            current_stay_hours: 현재 체류시간
            target_hours: 목표 체류시간
            full_schedule: 전체 스케줄
            interview_date: 면접 날짜
            
        Returns:
            조정 성공 여부
        """
        if applicant_schedule.empty:
            return False
        
        # 활동을 시간 순으로 정렬
        applicant_schedule = applicant_schedule.sort_values('start_time')
        
        # 첫 번째와 마지막 활동 시간
        first_start = applicant_schedule['start_time'].min()
        last_end = applicant_schedule['end_time'].max()
        
        # 현재 체류시간
        current_duration = (last_end - first_start).total_seconds() / 3600
        
        if current_duration <= target_hours:
            return True  # 이미 제약을 만족
        
        # 단축해야 할 시간
        reduction_needed = current_duration - target_hours
        
        # 활동 간 간격 찾기
        gaps = []
        for i in range(len(applicant_schedule) - 1):
            current_end = applicant_schedule.iloc[i]['end_time']
            next_start = applicant_schedule.iloc[i + 1]['start_time']
            gap = (next_start - current_end).total_seconds() / 3600
            if gap > 0:
                gaps.append((i, gap, current_end, next_start))
        
        # 간격을 큰 순서로 정렬
        gaps.sort(key=lambda x: x[1], reverse=True)
        
        # 간격을 줄여서 체류시간 단축 시도
        total_reduced = 0
        for gap_idx, gap_hours, gap_start, gap_end in gaps:
            if total_reduced >= reduction_needed:
                break
            
            # 이 간격에서 줄일 수 있는 시간
            reducible = min(gap_hours, reduction_needed - total_reduced)
            
            if reducible <= 0:
                continue
            
            # 간격을 줄이기 위해 후속 활동들을 앞으로 당기기
            if self._try_shift_activities_forward(
                applicant_schedule, gap_idx + 1, reducible, full_schedule, interview_date
            ):
                total_reduced += reducible
                self.logger.debug(f"    간격 {gap_idx}에서 {reducible:.1f}시간 단축")
        
        # 조정된 스케줄로 전체 스케줄 업데이트
        if total_reduced > 0:
            # applicant_schedule의 변경사항을 full_schedule에 반영
            for _, row in applicant_schedule.iterrows():
                mask = (
                    (full_schedule['applicant_id'] == row['applicant_id']) &
                    (full_schedule['activity_name'] == row['activity_name']) &
                    (full_schedule['interview_date'] == interview_date)
                )
                full_schedule.loc[mask, 'start_time'] = row['start_time']
                full_schedule.loc[mask, 'end_time'] = row['end_time']
            
            return True
        
        return False
    
    def _try_shift_activities_forward(self,
                                     applicant_schedule: pd.DataFrame,
                                     start_idx: int,
                                     shift_hours: float,
                                     full_schedule: pd.DataFrame,
                                     interview_date) -> bool:
        """
        특정 인덱스부터의 활동들을 앞으로 당기기 시도
        
        Args:
            applicant_schedule: 지원자의 스케줄
            start_idx: 시작 인덱스
            shift_hours: 당길 시간 (시간)
            full_schedule: 전체 스케줄
            interview_date: 면접 날짜
            
        Returns:
            성공 여부
        """
        if start_idx >= len(applicant_schedule):
            return False
        
        shift_minutes = int(shift_hours * 60)
        
        # start_idx부터 끝까지의 활동들을 앞으로 당기기
        for i in range(start_idx, len(applicant_schedule)):
            activity_row = applicant_schedule.iloc[i]
            
            # 새로운 시작/종료 시간 계산
            new_start = activity_row['start_time'] - timedelta(minutes=shift_minutes)
            new_end = activity_row['end_time'] - timedelta(minutes=shift_minutes)
            
            # 시간 충돌 검사
            if self._check_time_conflict(
                activity_row['applicant_id'],
                activity_row['room_name'],
                new_start,
                new_end,
                full_schedule,
                interview_date,
                exclude_activity=activity_row['activity_name']
            ):
                return False  # 충돌 발생
            
            # 스케줄 업데이트
            applicant_schedule.iloc[i, applicant_schedule.columns.get_loc('start_time')] = new_start
            applicant_schedule.iloc[i, applicant_schedule.columns.get_loc('end_time')] = new_end
        
        return True
    
    def _check_time_conflict(self,
                            applicant_id: str,
                            room_name: str,
                            start_time: timedelta,
                            end_time: timedelta,
                            full_schedule: pd.DataFrame,
                            interview_date,
                            exclude_activity: str = None) -> bool:
        """
        시간 충돌 검사
        
        Args:
            applicant_id: 지원자 ID
            room_name: 방 이름
            start_time: 시작 시간
            end_time: 종료 시간
            full_schedule: 전체 스케줄
            interview_date: 면접 날짜
            exclude_activity: 제외할 활동명
            
        Returns:
            충돌 여부
        """
        # 같은 방의 다른 스케줄과 충돌 검사
        room_conflicts = full_schedule[
            (full_schedule['room_name'] == room_name) &
            (full_schedule['interview_date'] == interview_date) &
            (full_schedule['activity_name'] != exclude_activity) &
            (
                ((full_schedule['start_time'] < end_time) & (full_schedule['end_time'] > start_time))
            )
        ]
        
        if not room_conflicts.empty:
            return True
        
        # 같은 지원자의 다른 활동과 충돌 검사
        applicant_conflicts = full_schedule[
            (full_schedule['applicant_id'] == applicant_id) &
            (full_schedule['interview_date'] == interview_date) &
            (full_schedule['activity_name'] != exclude_activity) &
            (
                ((full_schedule['start_time'] < end_time) & (full_schedule['end_time'] > start_time))
            )
        ]
        
        return not applicant_conflicts.empty
    
    def _analyze_constraint_violations(self, 
                                     schedule_df: pd.DataFrame,
                                     hard_constraints: Dict[str, float]) -> Dict[str, Any]:
        """
        제약 위반 분석
        
        Args:
            schedule_df: 스케줄 DataFrame
            hard_constraints: 날짜별 하드 제약값
            
        Returns:
            제약 위반 분석 결과
        """
        if schedule_df.empty:
            return {}
        
        # 지원자별 체류시간 계산
        stay_times = self.analyzer._calculate_stay_times(schedule_df)
        
        if stay_times.empty:
            return {}
        
        violations = {}
        total_violations = 0
        
        for interview_date, group_data in stay_times.groupby('interview_date'):
            date_str = str(interview_date)
            constraint_hours = hard_constraints.get(date_str, float('inf'))
            
            # 제약 위반자 찾기
            violators = group_data[group_data['stay_hours'] > constraint_hours]
            
            violations[date_str] = {
                'constraint_hours': constraint_hours,
                'violator_count': len(violators),
                'total_count': len(group_data),
                'violation_rate': len(violators) / len(group_data) * 100 if len(group_data) > 0 else 0,
                'violators': violators[['applicant_id', 'stay_hours', 'job_code']].to_dict('records')
            }
            
            total_violations += len(violators)
        
        return {
            'date_violations': violations,
            'total_violations': total_violations,
            'total_applicants': len(stay_times),
            'overall_violation_rate': total_violations / len(stay_times) * 100 if len(stay_times) > 0 else 0
        }
    
    def generate_comprehensive_report(self, result: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        종합 리포트 생성
        
        Args:
            result: 2단계 스케줄링 결과
            
        Returns:
            종합 리포트 DataFrame들
        """
        reports = {}
        
        # 1. 제약 분석 리포트
        if result.get('constraint_analysis'):
            constraint_report = self.analyzer.generate_constraint_report(
                result['constraint_analysis']
            )
            reports['constraint_analysis'] = constraint_report
        
        # 2. 제약 위반 리포트
        if result.get('exceed_analysis'):
            exceed_report = self._generate_violation_report(result['exceed_analysis'])
            reports['constraint_violations'] = exceed_report
        
        # 3. 비교 리포트 (1단계 vs 2단계)
        if result.get('phase1_result') is not None and result.get('phase2_result') is not None:
            comparison_report = self._generate_comparison_report(
                result['phase1_result'], 
                result['phase2_result']
            )
            reports['phase_comparison'] = comparison_report
        
        return reports
    
    def _generate_violation_report(self, exceed_analysis: Dict[str, Any]) -> pd.DataFrame:
        """제약 위반 리포트 생성"""
        if not exceed_analysis.get('date_violations'):
            return pd.DataFrame()
        
        report_data = []
        
        for date_str, violation_info in exceed_analysis['date_violations'].items():
            report_data.append({
                'interview_date': date_str,
                'constraint_hours': violation_info['constraint_hours'],
                'total_applicants': violation_info['total_count'],
                'violator_count': violation_info['violator_count'],
                'violation_rate': round(violation_info['violation_rate'], 1),
                'status': '위반 있음' if violation_info['violator_count'] > 0 else '정상'
            })
        
        report_df = pd.DataFrame(report_data)
        
        # 날짜 순으로 정렬
        if not report_df.empty:
            report_df['interview_date'] = pd.to_datetime(report_df['interview_date'])
            report_df = report_df.sort_values('interview_date')
        
        return report_df
    
    def _generate_comparison_report(self, 
                                  phase1_df: pd.DataFrame,
                                  phase2_df: pd.DataFrame) -> pd.DataFrame:
        """1단계 vs 2단계 비교 리포트 생성"""
        # 1단계 체류시간 분석
        phase1_stay = self.analyzer._calculate_stay_times(phase1_df)
        phase2_stay = self.analyzer._calculate_stay_times(phase2_df)
        
        if phase1_stay.empty or phase2_stay.empty:
            return pd.DataFrame()
        
        comparison_data = []
        
        # 날짜별로 비교
        for date in phase1_stay['interview_date'].unique():
            phase1_date = phase1_stay[phase1_stay['interview_date'] == date]
            phase2_date = phase2_stay[phase2_stay['interview_date'] == date]
            
            if phase1_date.empty or phase2_date.empty:
                continue
            
            phase1_hours = phase1_date['stay_hours'].values
            phase2_hours = phase2_date['stay_hours'].values
            
            comparison_data.append({
                'interview_date': date,
                'phase1_mean': round(np.mean(phase1_hours), 2),
                'phase1_max': round(np.max(phase1_hours), 2),
                'phase2_mean': round(np.mean(phase2_hours), 2),
                'phase2_max': round(np.max(phase2_hours), 2),
                'mean_improvement': round(np.mean(phase1_hours) - np.mean(phase2_hours), 2),
                'max_improvement': round(np.max(phase1_hours) - np.max(phase2_hours), 2)
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        # 날짜 순으로 정렬
        if not comparison_df.empty:
            comparison_df['interview_date'] = pd.to_datetime(comparison_df['interview_date'])
            comparison_df = comparison_df.sort_values('interview_date')
        
        return comparison_df 