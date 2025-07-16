"""
Level 4: 후처리 조정 모듈

전체 스케줄링(Level 1-3) 완료 후 체류시간 최적화를 위한 후처리 조정
주요 기능:
- 체류시간 분석 및 문제 케이스 식별
- Batched 그룹 시간 이동 시뮬레이션
- 제약 조건 검증 및 최적 조정 실행
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import time # Added for timing

from .types import (
    DateConfig, ScheduleItem, Room, Activity, ActivityMode,
    PrecedenceRule, GroupAssignment, StayTimeAnalysis,
    GroupMoveCandidate, Level4Result
)


class Level4PostProcessor:
    """Level 4 후처리 조정 프로세서"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
    def _get_activity_max_capacity(self, activity_name: str, config: DateConfig) -> Optional[int]:
        """활동별 최대 용량 반환"""
        for activity in config.activities:
            if activity.name == activity_name:
                return activity.max_capacity
        return None
    
    def _calculate_improvement_potential(self, items: List[ScheduleItem], config: DateConfig) -> float:
        """개선 가능성 계산 - 동적 기준 적용"""
        if len(items) < 2:
            return 0.0
        
        # 활동 간 간격 계산
        items_sorted = sorted(items, key=lambda x: x.start_time)
        gaps = []
        
        for i in range(len(items_sorted) - 1):
            gap_hours = (items_sorted[i+1].start_time - items_sorted[i].end_time).total_seconds() / 3600
            gaps.append(gap_hours)
        
        # 개선 가능성 = 가장 긴 간격에서 기본 대기시간(1시간) 제외
        max_gap = max(gaps) if gaps else 0.0
        
        # 🔧 동적 기준: 3시간 → 2시간으로 단축 (더 공격적)
        # 리스크 분석: 간격이 1.5시간 이상이면 개선 가능
        improvement_threshold = 1.5  # 기존 2.0에서 1.5로 단축
        
        improvement_potential = max(0.0, max_gap - improvement_threshold)
        
        # 📊 개선 가능성 로깅
        if improvement_potential > 0:
            self.logger.debug(f"개선 가능성 계산: 최대간격={max_gap:.1f}h, 임계값={improvement_threshold:.1f}h, "
                             f"개선잠재력={improvement_potential:.1f}h")
        
        return improvement_potential
    
    def _analyze_risk_factors(self, analyses: List[StayTimeAnalysis], config: DateConfig) -> dict:
        """체류시간 기준 변경에 따른 리스크 분석"""
        if not analyses:
            return {}
        
        stay_times = [a.stay_time_hours for a in analyses]
        
        # 다양한 기준에 따른 영향 분석
        risk_analysis = {}
        
        # 기준별 대상자 수 계산
        thresholds = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0]
        for threshold in thresholds:
            candidates = [a for a in analyses if a.stay_time_hours >= threshold]
            risk_analysis[f"threshold_{threshold}"] = {
                'count': len(candidates),
                'percentage': len(candidates) / len(analyses) * 100,
                'avg_improvement': sum(a.improvement_potential for a in candidates) / len(candidates) if candidates else 0
            }
        
        # 통계적 기준 분석
        import statistics
        mean_stay = statistics.mean(stay_times)
        std_dev = statistics.stdev(stay_times) if len(stay_times) > 1 else 0
        
        # 상위 퍼센타일 분석
        sorted_times = sorted(stay_times, reverse=True)
        percentiles = [10, 20, 30, 40, 50]
        
        for p in percentiles:
            idx = int(len(sorted_times) * p / 100)
            percentile_value = sorted_times[min(idx, len(sorted_times) - 1)]
            candidates = [a for a in analyses if a.stay_time_hours >= percentile_value]
            
            risk_analysis[f"percentile_{p}"] = {
                'threshold': percentile_value,
                'count': len(candidates),
                'percentage': len(candidates) / len(analyses) * 100
            }
        
        # 리스크 요약
        risk_analysis['summary'] = {
            'total_candidates': len(analyses),
            'mean_stay': mean_stay,
            'std_dev': std_dev,
            'min_stay': min(stay_times),
            'max_stay': max(stay_times),
            'statistical_threshold': mean_stay + std_dev,
            'recommended_threshold': max(3.0, min(mean_stay + std_dev, 
                                                 sorted_times[int(len(sorted_times) * 0.3)]))
        }
        
        return risk_analysis
    
    def _calculate_dynamic_stay_time_threshold(self, analyses: List[StayTimeAnalysis]) -> float:
        """동적 체류시간 기준 계산 - 개선된 버전"""
        if not analyses:
            return 3.0  # 기본값 3시간
        
        stay_times = [analysis.stay_time_hours for analysis in analyses]
        
        # 리스크 분석 수행
        risk_analysis = self._analyze_risk_factors(analyses, None)
        
        # 통계 기반 임계값 계산
        import statistics
        mean_stay = statistics.mean(stay_times)
        median_stay = statistics.median(stay_times)
        
        # 상위 30% 지점 계산
        sorted_times = sorted(stay_times, reverse=True)
        percentile_30_index = int(len(sorted_times) * 0.3)
        percentile_30_value = sorted_times[min(percentile_30_index, len(sorted_times) - 1)]
        
        # 동적 임계값 계산 전략
        std_dev = statistics.stdev(stay_times) if len(stay_times) > 1 else 0
        statistical_threshold = mean_stay + 0.5 * std_dev  # 더 공격적으로 변경 (기존 1.0 → 0.5)
        
        # 🔧 3시간 기준 적용: 통계적 임계값과 상위 30% 중 작은 값, 최소 3시간
        dynamic_threshold = max(3.0, min(statistical_threshold, percentile_30_value))
        
        # 📊 상세 로깅
        self.logger.info(f"📊 체류시간 통계 및 리스크 분석:")
        self.logger.info(f"   평균={mean_stay:.1f}h, 중간값={median_stay:.1f}h, 표준편차={std_dev:.1f}h")
        self.logger.info(f"   상위30%={percentile_30_value:.1f}h, 통계적임계값={statistical_threshold:.1f}h")
        self.logger.info(f"   최종 동적임계값={dynamic_threshold:.1f}h")
        
        # 리스크 분석 결과 로깅
        if 'summary' in risk_analysis:
            summary = risk_analysis['summary']
            self.logger.info(f"   권장임계값={summary['recommended_threshold']:.1f}h")
        
        # 3시간 기준 적용 시 예상 영향
        candidates_3h = len([t for t in stay_times if t >= 3.0])
        candidates_4h = len([t for t in stay_times if t >= 4.0])
        
        self.logger.info(f"📈 기준별 대상자 수:")
        self.logger.info(f"   3시간 기준: {candidates_3h}명 ({candidates_3h/len(stay_times)*100:.1f}%)")
        self.logger.info(f"   4시간 기준: {candidates_4h}명 ({candidates_4h/len(stay_times)*100:.1f}%)")
        
        if candidates_3h > candidates_4h * 2:
            self.logger.warning(f"⚠️ 3시간 기준 시 대상자가 {candidates_3h - candidates_4h}명 증가 - 성능 주의 필요")
        
        return dynamic_threshold

    def _validate_schedule_integrity(self, schedule: List[ScheduleItem], config: DateConfig) -> List[str]:
        """스케줄 무결성 검사 - 그룹 크기 초과와 중복 배정 검사"""
        issues = []
        
        # 그룹별 크기 검사
        group_sizes = defaultdict(int)
        for item in schedule:
            if item.group_id and not item.applicant_id.startswith('dummy'):
                group_sizes[item.group_id] += 1
        
        # Batched 활동 그룹 크기 검사 (활동별 최대 용량 기준)
        for group_id, size in group_sizes.items():
            # 해당 그룹의 활동 정보 확인
            group_items = [item for item in schedule if item.group_id == group_id]
            if group_items:
                activity_name = group_items[0].activity_name
                # 활동별 최대 용량 확인
                max_capacity = self._get_activity_max_capacity(activity_name, config)
                if max_capacity and size > max_capacity:
                    issues.append(f"⚠️ {activity_name} 그룹 {group_id} 크기 초과: {size}명 (최대 {max_capacity}명)")
        
        # 시간-방 중복 배정 검사
        time_room_groups = defaultdict(list)
        for item in schedule:
            if not item.applicant_id.startswith('dummy'):
                key = (item.room_name, item.start_time, item.end_time)
                time_room_groups[key].append(item.group_id)
        
        for (room, start_time, end_time), group_ids in time_room_groups.items():
            unique_groups = set(group_ids)
            if len(unique_groups) > 1:
                issues.append(f"⚠️ 시간-방 중복: {room} {start_time} - 그룹 {', '.join(unique_groups)}")
        
        return issues

    def optimize_stay_times(
        self,
        schedule: List[ScheduleItem],
        config: DateConfig,
        target_improvement_hours: float = 1.0
    ) -> Level4Result:
        """
        체류시간 최적화 - 안전장치 강화 및 동적 임계값 적용
        """
        start_time = time.time()
        
        # 🔧 CRITICAL: 입력 스케줄 무결성 검사
        input_issues = self._validate_schedule_integrity(schedule, config)
        if input_issues:
            self.logger.error(f"입력 스케줄 무결성 오류: {input_issues}")
            return Level4Result(
                success=False,
                original_schedule=schedule,
                optimized_schedule=schedule,
                total_improvement_hours=0.0,
                adjusted_groups=0,
                improvements=[],
                logs=[]
            )
        
        self.logger.info("Level 4 후처리 조정 시작")
        
        try:
            # 1. 현재 체류시간 분석
            analyses = self._analyze_stay_times(schedule)
            self.logger.info(f"체류시간 분석 완료: {len(analyses)}명")
            
            if not analyses:
                self.logger.info("분석할 지원자가 없습니다")
                return Level4Result(
                    success=False,
                    original_schedule=schedule,
                    optimized_schedule=schedule,
                    total_improvement_hours=0.0,
                    adjusted_groups=0,
                    improvements=[],
                    logs=[]
                )
            
            # 2. 문제 케이스 식별 (동적 임계값 적용)
            problem_cases = self._identify_problem_cases_dynamic(analyses)
            self.logger.info(f"문제 케이스 {len(problem_cases)}개 식별")
            
            if not problem_cases:
                self.logger.info("체류시간 개선이 필요한 케이스가 없습니다")
                return Level4Result(
                    success=False,
                    original_schedule=schedule,
                    optimized_schedule=schedule,
                    total_improvement_hours=0.0,
                    adjusted_groups=0,
                    improvements=[],
                    logs=[]
                )
            
            # 3. 조정 가능한 Batched 그룹 찾기
            move_candidates = self._find_move_candidates(schedule, problem_cases, config)
            self.logger.info(f"이동 후보 그룹: {len(move_candidates)}개")
            
            if not move_candidates:
                self.logger.info("이동 가능한 그룹이 없습니다")
                return Level4Result(
                    success=False,
                    original_schedule=schedule,
                    optimized_schedule=schedule,
                    total_improvement_hours=0.0,
                    adjusted_groups=0,
                    improvements=[],
                    logs=[]
                )
            
            # 4. 최적 이동 시뮬레이션
            optimal_moves = self._simulate_optimal_moves(move_candidates, config)
            self.logger.info(f"최적 이동 선택: {len(optimal_moves)}개")
            
            if not optimal_moves:
                self.logger.info("적용 가능한 이동이 없습니다")
                return Level4Result(
                    success=False,
                    original_schedule=schedule,
                    optimized_schedule=schedule,
                    total_improvement_hours=0.0,
                    adjusted_groups=0,
                    improvements=[],
                    logs=[]
                )
            
            # 5. 제약 조건 검증 및 적용
            optimized_schedule = self._apply_moves(schedule, optimal_moves, config)
            
            # 🔧 CRITICAL: 최종 스케줄 무결성 검사
            final_issues = self._validate_schedule_integrity(optimized_schedule, config)
            if final_issues:
                self.logger.error(f"최종 스케줄 무결성 오류: {final_issues}")
                # 원본 스케줄 복원
                return Level4Result(
                    success=False,
                    original_schedule=schedule,
                    optimized_schedule=schedule,
                    total_improvement_hours=0.0,
                    adjusted_groups=0,
                    improvements=[],
                    logs=[]
                )
            
            # 6. 결과 생성
            total_improvement = sum(move.estimated_improvement for move in optimal_moves)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Level 4 후처리 조정 완료: {elapsed_time:.2f}초, {total_improvement:.1f}시간 개선")
            
            result = Level4Result(
                original_schedule=schedule,
                optimized_schedule=optimized_schedule,
                improvements=optimal_moves,
                total_improvement_hours=total_improvement,
                adjusted_groups=len(optimal_moves),
                success=True,
                logs=[f"Level 4 후처리 조정 완료: {total_improvement:.1f}시간 개선"]
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Level 4 후처리 조정 실패: {str(e)}")
            return Level4Result(
                original_schedule=schedule,
                optimized_schedule=schedule,
                improvements=[],
                total_improvement_hours=0.0,
                adjusted_groups=0,
                success=False,
                logs=[f"Level 4 후처리 조정 실패: {str(e)}"]
            )
    
    def _analyze_stay_times(self, schedule: List[ScheduleItem]) -> List[StayTimeAnalysis]:
        """체류시간 분석"""
        applicant_schedules = defaultdict(list)
        
        # 지원자별 스케줄 그룹화
        for item in schedule:
            if not item.applicant_id.startswith('dummy'):
                applicant_schedules[item.applicant_id].append(item)
        
        analyses = []
        for applicant_id, items in applicant_schedules.items():
            # 시간 순 정렬
            items.sort(key=lambda x: x.start_time)
            
            if items:
                first_start = items[0].start_time
                last_end = items[-1].end_time
                stay_time = (last_end - first_start).total_seconds() / 3600
                
                # 개선 가능성 계산 (단순히 마지막 활동을 앞으로 당길 수 있는 시간)
                improvement_potential = self._calculate_improvement_potential(items, None) # Pass config=None
                
                analysis = StayTimeAnalysis(
                    applicant_id=applicant_id,
                    job_code=items[0].job_code,
                    first_activity_start=first_start,
                    last_activity_end=last_end,
                    stay_time_hours=stay_time,
                    activities=items,
                    improvement_potential=improvement_potential
                )
                analyses.append(analysis)
        
        return analyses
    
    def _identify_problem_cases_dynamic(self, analyses: List[StayTimeAnalysis]) -> List[StayTimeAnalysis]:
        """동적 임계값 기반 문제 케이스 식별"""
        # 동적 체류시간 임계값 계산
        dynamic_threshold = self._calculate_dynamic_stay_time_threshold(analyses)
        
        # 체류시간 기준 정렬
        sorted_analyses = sorted(analyses, key=lambda x: x.stay_time_hours, reverse=True)
        
        # 상위 30% 또는 동적 임계값 이상인 경우를 문제 케이스로 식별
        percentile_threshold = sorted_analyses[int(len(sorted_analyses) * 0.3)].stay_time_hours if sorted_analyses else 0
        final_threshold = max(dynamic_threshold, percentile_threshold)
        
        problem_cases = [
            analysis for analysis in sorted_analyses 
            if analysis.stay_time_hours >= final_threshold and analysis.improvement_potential > 0.3
        ]
        
        self.logger.info(f"📊 최종 임계값: {final_threshold:.1f}시간 (동적={dynamic_threshold:.1f}h, 상위30%={percentile_threshold:.1f}h)")
        
        return problem_cases
    
    def _find_move_candidates(
        self, 
        schedule: List[ScheduleItem], 
        problem_cases: List[StayTimeAnalysis],
        config: DateConfig
    ) -> List[GroupMoveCandidate]:
        """조정 가능한 Batched 그룹 찾기"""
        candidates = []
        
        # Batched 활동만 필터링
        batched_items = [item for item in schedule if self._is_batched_activity(item, config)]
        
        # 그룹별로 정리
        group_items = defaultdict(list)
        for item in batched_items:
            if item.group_id:
                group_items[item.group_id].append(item)
        
        for group_id, items in group_items.items():
            if not items:
                continue
                
            # 그룹의 현재 시간
            current_start = min(item.start_time for item in items)
            current_end = max(item.end_time for item in items)
            
            # 이 그룹에 속한 문제 케이스들
            affected_applicants = []
            total_improvement = 0.0
            
            for problem_case in problem_cases:
                if any(item.applicant_id == problem_case.applicant_id for item in items):
                    affected_applicants.append(problem_case.applicant_id)
                    total_improvement += problem_case.improvement_potential
            
            if affected_applicants:
                # 이동 목표 시간 계산 (오후 시간대로 이동)
                target_start = self._calculate_target_time(current_start, config)
                target_end = target_start + (current_end - current_start)
                
                candidate = GroupMoveCandidate(
                    group_id=group_id,
                    activity_name=items[0].activity_name,
                    current_start=current_start,
                    current_end=current_end,
                    target_start=target_start,
                    target_end=target_end,
                    affected_applicants=affected_applicants,
                    estimated_improvement=total_improvement
                )
                candidates.append(candidate)
        
        return candidates
    
    def _simulate_optimal_moves(
        self, 
        candidates: List[GroupMoveCandidate],
        config: DateConfig
    ) -> List[GroupMoveCandidate]:
        """최적 이동 시뮬레이션"""
        # 개선 효과 대비 리스크가 낮은 후보들 선택
        valid_candidates = []
        
        for candidate in candidates:
            # 운영시간 내 체크
            if candidate.target_end <= config.operating_hours[1]:
                # 다른 활동과 충돌 체크 (단순화)
                if self._check_time_conflicts(candidate, config):
                    valid_candidates.append(candidate)
        
        # 개선 효과 순으로 정렬하여 최대 6개 그룹 선택 (더 공격적 설정)
        valid_candidates.sort(key=lambda x: x.estimated_improvement, reverse=True)
        return valid_candidates[:6]
    
    def _apply_moves(
        self, 
        original_schedule: List[ScheduleItem], 
        moves: List[GroupMoveCandidate],
        config: DateConfig
    ) -> List[ScheduleItem]:
        """이동 적용 - 충돌 방지 강화"""
        optimized_schedule = original_schedule.copy()
        used_time_rooms = set()  # 🔧 CRITICAL FIX: 시간-방 충돌 추적
        
        for move in moves:
            # 해당 그룹의 스케줄 아이템들 찾기
            group_items = [
                item for item in optimized_schedule 
                if item.group_id == move.group_id
            ]
            
            if not group_items:
                continue
                
            # 🔧 SAFETY CHECK: 그룹 크기 검증 (활동별 최대 용량 기준)
            max_capacity = self._get_activity_max_capacity(move.activity_name, config)
            if max_capacity and len(group_items) > max_capacity:
                self.logger.warning(f"⚠️ 그룹 {move.group_id} 크기 초과 ({len(group_items)}명 > {max_capacity}명), 이동 건너뜀")
                continue
                
            # 시간 이동 적용
            time_delta = move.target_start - move.current_start
            
            # 새로운 시간과 방 조합 확인
            sample_item = group_items[0]
            new_start = sample_item.start_time + time_delta
            new_end = sample_item.end_time + time_delta
            room_time_key = (sample_item.room_name, new_start, new_end)
            
            # 🔧 CRITICAL FIX: 시간-방 충돌 체크
            if room_time_key in used_time_rooms:
                self.logger.warning(f"⚠️ 그룹 {move.group_id} 시간-방 충돌, 이동 건너뜀: {sample_item.room_name} {new_start}")
                continue
                
            # 충돌이 없으면 이동 실행
            used_time_rooms.add(room_time_key)
            
            for item in group_items:
                # 새로운 시간으로 업데이트 (min_gap_min 제약 적용)
                new_start_time, new_end_time = self._apply_min_gap_constraint(
                    item.start_time + time_delta, item.end_time + time_delta, 5
                )
                
                new_item = ScheduleItem(
                    applicant_id=item.applicant_id,
                    job_code=item.job_code,
                    activity_name=item.activity_name,
                    room_name=item.room_name,
                    start_time=new_start_time,
                    end_time=new_end_time,
                    group_id=item.group_id
                )
                
                # 기존 아이템 교체
                idx = optimized_schedule.index(item)
                optimized_schedule[idx] = new_item
                
                self.logger.info(f"그룹 {move.group_id} 이동: {item.start_time} → {new_item.start_time}")
        
        return optimized_schedule
    
    def _is_batched_activity(self, item: ScheduleItem, config: DateConfig) -> bool:
        """Batched 활동인지 확인"""
        for activity in config.activities:
            if activity.name == item.activity_name:
                return activity.mode == ActivityMode.BATCHED
        return False
    
    def _calculate_target_time(self, current_start: timedelta, config: DateConfig) -> timedelta:
        """목표 이동 시간 계산 - 충돌 방지 개선"""
        # 🔧 CRITICAL FIX: 모든 그룹을 14:00로 보내는 버그 수정
        # 현재 시간보다 늦은 시간대로만 이동 (오후로 이동)
        
        # 오후 시간대 후보들 (5분 단위로 라운딩)
        afternoon_slots = [
            self._round_to_5min(timedelta(hours=13, minutes=0)),
            self._round_to_5min(timedelta(hours=13, minutes=30)), 
            self._round_to_5min(timedelta(hours=14, minutes=0)),
            self._round_to_5min(timedelta(hours=14, minutes=30)),
            self._round_to_5min(timedelta(hours=15, minutes=0)),
            self._round_to_5min(timedelta(hours=15, minutes=30)),
            self._round_to_5min(timedelta(hours=16, minutes=0))
        ]
        
        # 현재 시간보다 늦은 시간대 중 가장 가까운 것 선택
        valid_slots = [slot for slot in afternoon_slots 
                      if slot > current_start and slot <= config.operating_hours[1] - timedelta(hours=1)]
        
        if valid_slots:
            return valid_slots[0]  # 가장 가까운 시간대
        else:
            # 대안: 현재 시간 + 2시간
            target = current_start + timedelta(hours=2)
            if target <= config.operating_hours[1] - timedelta(hours=1):
                return target
            else:
                return current_start  # 이동하지 않음
    
    def _apply_min_gap_constraint(self, start_time: timedelta, end_time: timedelta, global_gap_min: int = 5) -> Tuple[timedelta, timedelta]:
        """
        min_gap_min 제약을 적용하여 시간을 5분 단위로 조정
        
        Args:
            start_time: 시작 시간
            end_time: 종료 시간
            global_gap_min: 최소 간격 (분)
            
        Returns:
            Tuple[timedelta, timedelta]: 조정된 시작/종료 시간
        """
        # 시작 시간을 5분 단위로 조정
        start_minutes = start_time.total_seconds() / 60
        adjusted_start_minutes = round(start_minutes / global_gap_min) * global_gap_min
        adjusted_start = timedelta(minutes=adjusted_start_minutes)
        
        # 종료 시간을 5분 단위로 조정
        end_minutes = end_time.total_seconds() / 60
        adjusted_end_minutes = round(end_minutes / global_gap_min) * global_gap_min
        adjusted_end = timedelta(minutes=adjusted_end_minutes)
        
        return adjusted_start, adjusted_end
    
    def _round_to_5min(self, time_delta: timedelta) -> timedelta:
        """
        timedelta를 5분 단위로 반올림 (하위 호환성)
        
        Args:
            time_delta: 반올림할 시간
            
        Returns:
            timedelta: 5분 단위로 반올림된 시간
        """
        total_minutes = time_delta.total_seconds() / 60
        rounded_minutes = round(total_minutes / 5) * 5
        return timedelta(minutes=rounded_minutes)
    
    def _check_time_conflicts(self, candidate: GroupMoveCandidate, config: DateConfig) -> bool:
        """시간 충돌 체크 (단순화된 버전)"""
        # 실제로는 더 복잡한 충돌 검사 필요
        # 현재는 기본적인 운영시간 체크만 수행
        return (candidate.target_start >= config.operating_hours[0] and 
                candidate.target_end <= config.operating_hours[1]) 