"""
단일 날짜 스케줄링: Level 1 → Level 2 → Level 3 → Level 4 (후처리 조정)
"""
import time as time_module
import logging
from typing import Optional, Dict, List, Any, Tuple, Set

from .group_optimizer_v2 import GroupOptimizerV2
from .batched_scheduler import BatchedScheduler
from .individual_scheduler import IndividualScheduler
from .unified_cpsat_scheduler import UnifiedCPSATScheduler
from .level4_post_processor import Level4PostProcessor
from .types import (
    DateConfig, SingleDateResult, Level1Result, Level2Result, 
    Level3Result, Level4Result, Applicant, Activity, ScheduleItem, Group, 
    SchedulingContext, TimeSlot, ActivityMode, ProgressInfo
)


class SingleDateScheduler:
    """단일 날짜에 대한 3단계 스케줄링을 수행하는 클래스"""
    
    # 각 레벨별 시간 제한 (초)
    LEVEL1_TIME_LIMIT = 30
    LEVEL2_TIME_LIMIT = 60  
    LEVEL3_TIME_LIMIT = 30
    LEVEL23_UNIFIED_TIME_LIMIT = 120  # 통합 스케줄러 시간 제한
    
    def __init__(self, logger: Optional[logging.Logger] = None, use_unified_cpsat: bool = True):
        self.logger = logger or logging.getLogger(__name__)
        self.progress_callback: Optional[ProgressCallback] = None
        self.context: Optional[SchedulingContext] = None
        self.use_unified_cpsat = use_unified_cpsat  # 🚀 통합 CP-SAT 사용 여부
        
    def schedule(
        self, 
        config: DateConfig, 
        context: Optional[SchedulingContext] = None
    ) -> SingleDateResult:
        """
        3단계 계층적 스케줄링 실행
        
        Level 1: 그룹 구성 최적화
        Level 2: Batched 활동 스케줄링
        Level 3: Individual/Parallel 활동 스케줄링
        """
        self.context = context
        self.progress_callback = context.progress_callback if context else None
        
        result = SingleDateResult(date=config.date, status="FAILED")
        result.logs.append(f"=== {config.date.date()} 스케줄링 시작 ===")
        
        # 전체 시작 시간
        overall_start_time = time_module.time()
        
        try:
            # 진행 상황 초기화
            self._report_progress("Level1", 0.0, "그룹 구성 최적화 시작")
            
            # Level 1: 그룹 구성
            level1_start = time_module.time()
            level1_result = self._run_level1(config)
            level1_time = time_module.time() - level1_start
            
            if not level1_result:
                result.error_message = "Level 1 실패: 그룹 구성 불가"
                result.logs.append(f"Level 1 실패 ({level1_time:.1f}초)")
                self._report_progress("Level1", 1.0, "그룹 구성 실패", {"error": result.error_message})
                return result
            
            result.level1_result = level1_result
            total_groups = sum(len(groups) for groups in level1_result.groups.values())
            result.logs.append(
                f"Level 1 완료 ({level1_time:.1f}초): "
                f"{total_groups}개 그룹, {level1_result.dummy_count}명 더미"
            )
            self._report_progress("Level1", 1.0, "그룹 구성 완료", {
                "groups": total_groups,
                "dummies": level1_result.dummy_count,
                "time": level1_time
            })
            
            # 🚀 Level 2-3: 통합 CP-SAT 스케줄링 vs 기존 분리 스케줄링
            if self.use_unified_cpsat:
                # ========== 통합 CP-SAT 스케줄링 ==========
                self._report_progress("Level23", 0.0, "🚀 통합 CP-SAT 스케줄링 시작 (Batched + Individual)")
                level23_start = time_module.time()
                level2_result, level3_result = self._run_level23_unified(config, level1_result)
                level23_time = time_module.time() - level23_start
            
                if not level2_result or not level3_result:
                    # 통합 스케줄링 실패시 기존 방식으로 폴백
                    result.error_message = "통합 CP-SAT 스케줄링 실패 - 기존 방식으로 폴백"
                    result.logs.append(f"통합 스케줄링 실패 ({level23_time:.1f}초) - 기존 방식 시도")
                    self._report_progress("Level23", 1.0, "통합 스케줄링 실패 - 기존 방식 폴백", {
                    "error": result.error_message
                })
                    # 기존 방식으로 재시도
                    return self._run_legacy_level23(config, level1_result, result, overall_start_time)
            
            result.level2_result = level2_result
                result.level3_result = level3_result
                level2_time = level23_time  # 시간 호환성
                level3_time = 0  # 통합에서 처리됨
                
            result.logs.append(
                    f"🚀 통합 CP-SAT 완료 ({level23_time:.1f}초): "
                    f"Batched {len(level2_result.schedule)}개, Individual {len(level3_result.schedule)}개"
            )
                self._report_progress("Level23", 1.0, "통합 CP-SAT 스케줄링 완료", {
                    "batched_count": len(level2_result.schedule),
                    "individual_count": len(level3_result.schedule),
                    "time": level23_time
                })
                
            else:
                # ========== 기존 분리 스케줄링 ==========
                level2_result, level3_result, level2_time, level3_time = self._run_legacy_level23_only(config, level1_result)
                
                if not level2_result or not level3_result:
                    result.error_message = "기존 스케줄링 실패"
                    return result
            
            # Level 4: 후처리 조정
            self._report_progress("Level4", 0.0, "후처리 조정 시작")
            level4_start = time_module.time()
            
            # 전체 스케줄 통합 (Level 2 + Level 3)
            all_schedule = []
            all_schedule.extend(level2_result.schedule)
            all_schedule.extend(level3_result.schedule)
            
            # Level 4 후처리 조정 실행
            level4_result = self._run_level4(config, all_schedule)
            level4_time = time_module.time() - level4_start
            
            if not level4_result or not level4_result.success:
                # Level 4 실패해도 기본 스케줄은 유지
                result.logs.append(f"Level 4 후처리 조정 실패 ({level4_time:.1f}초) - 기본 스케줄 유지")
                self._report_progress("Level4", 1.0, "후처리 조정 실패 - 기본 스케줄 유지", {
                    "error": "후처리 조정 실패"
                })
                # 기본 스케줄 사용
                result.schedule = all_schedule
                result.level4_result = level4_result
            else:
                # Level 4 성공 - 최적화된 스케줄 사용
                result.logs.append(
                    f"Level 4 완료 ({level4_time:.1f}초): "
                    f"{level4_result.total_improvement_hours:.1f}시간 개선"
                )
                self._report_progress("Level4", 1.0, "후처리 조정 완료", {
                    "improvement_hours": level4_result.total_improvement_hours,
                    "adjusted_groups": level4_result.adjusted_groups,
                    "time": level4_time
                })
                # 최적화된 스케줄 사용
                result.schedule = level4_result.optimized_schedule
                result.level4_result = level4_result
            
            result.status = "SUCCESS"
            result.error_message = None
            
            total_time = time_module.time() - overall_start_time
            result.logs.append(f"=== 스케줄링 성공 (총 {total_time:.1f}초) ===")
            
            # 최종 완료 보고
            improvement_info = ""
            if level4_result and level4_result.success:
                improvement_info = f" (체류시간 {level4_result.total_improvement_hours:.1f}시간 개선)"
                
            self._report_progress("Complete", 1.0, f"스케줄링 성공{improvement_info}", {
                "total_time": total_time,
                "level1_time": level1_time,
                "level2_time": level2_time, 
                "level3_time": level3_time,
                "level4_time": level4_time,
                "total_schedule": len(result.schedule),
                "level4_improvement": level4_result.total_improvement_hours if level4_result else 0.0
            })
            
        except Exception as e:
            result.error_message = f"예외 발생: {str(e)}"
            result.logs.append(f"예외: {str(e)}")
            self.logger.exception("스케줄링 중 예외 발생")
            self._report_progress("Error", 1.0, f"예외 발생: {str(e)}")
        
        return result
    
    def _run_level1(self, config: DateConfig, dummy_hint: int = 0) -> Optional[Level1Result]:
        """Level 1: 그룹 구성 최적화"""
        try:
            optimizer = GroupOptimizerV2(self.logger)
            
            # 지원자 생성
            applicants = self._create_applicants(config)
            
            # 그룹 최적화 (dummy_hint 전달)
            result = optimizer.optimize(
                applicants=applicants,
                activities=config.activities,
                time_limit=self.LEVEL1_TIME_LIMIT,
                dummy_hint=dummy_hint
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Level 1 오류: {str(e)}")
            return None
    
    def _run_level2(
        self, 
        config: DateConfig, 
        level1_result: Level1Result
    ) -> Optional[Level2Result]:
        """Level 2: Batched 활동 스케줄링"""
        try:
            scheduler = BatchedScheduler(self.logger)
            
            result = scheduler.schedule(
                groups=level1_result.groups,
                config=config,
                time_limit=self.LEVEL2_TIME_LIMIT
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Level 2 오류: {str(e)}")
            return None
    
    def _run_level3(
        self,
        config: DateConfig,
        level1_result: Level1Result,
        level2_result: Level2Result
    ) -> Optional[Level3Result]:
        """Level 3: Individual/Parallel 활동 스케줄링"""
        try:
            # Individual/Parallel 활동이 있는지 확인
            individual_activities = [
                a for a in config.activities 
                if a.mode.value in ['individual', 'parallel']
            ]
            
            # Individual/Parallel 활동이 없으면 바로 성공 반환
            if not individual_activities:
                level3_result = Level3Result()
                level3_result.schedule = []  
                level3_result.unscheduled = []  # 빈 리스트로 설정
                return level3_result
            
            scheduler = IndividualScheduler()
            
            # Level 1 결과에서 모든 지원자 가져오기 (더미 포함)
            all_applicants = level1_result.applicants
            
            # Batched 스케줄 결과를 GroupScheduleResult 형태로 변환
            batched_results = []
            if level2_result and level2_result.group_results:
                batched_results = level2_result.group_results
            
            # Individual 스케줄링 실행
            result = scheduler.schedule_individuals(
                applicants=all_applicants,
                activities=config.activities,
                rooms=config.rooms,
                batched_results=batched_results,
                start_time=config.operating_hours[0],
                end_time=config.operating_hours[1],
                date_str=config.date.strftime('%Y-%m-%d'),
                precedence_rules=config.precedence_rules,
                global_gap_min=config.global_gap_min
            )
            
            if not result:
                return None
                
            # IndividualScheduleResult를 Level3Result로 변환
            level3_result = Level3Result()
            
            # 스케줄 항목 생성
            for applicant_id, time_slots in result.schedule_by_applicant.items():
                for slot in time_slots:
                    # 지원자의 job_code 찾기
                    job_code = None
                    for applicant in all_applicants:
                        if applicant.id == applicant_id:
                            job_code = applicant.job_code
                            break
                    
                    schedule_item = ScheduleItem(
                        applicant_id=applicant_id,
                        job_code=job_code or "UNKNOWN",
                        activity_name=slot.activity_name,
                        room_name=slot.room_name,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                        group_id=slot.group_id
                    )
                    level3_result.schedule.append(schedule_item)
            
            # 스케줄되지 않은 지원자 찾기 (Individual/Parallel 활동 대상자만)
            # Individual/Parallel 활동을 수행해야 하는 지원자들만 체크
            target_applicants = set()
            for applicant in all_applicants:
                if not applicant.is_dummy:
                    for activity in individual_activities:
                        if activity.name in applicant.required_activities:
                            target_applicants.add(applicant.id)
            
            scheduled_ids = set(result.schedule_by_applicant.keys())
            level3_result.unscheduled = list(target_applicants - scheduled_ids)
            
            return level3_result
            
        except Exception as e:
            self.logger.error(f"Level 3 오류: {str(e)}")
            return None
    
    def _run_level4(
        self,
        config: DateConfig,
        all_schedule: List[ScheduleItem]
    ) -> Optional[Level4Result]:
        """Level 4: 후처리 조정"""
        try:
            post_processor = Level4PostProcessor(self.logger)
            
            result = post_processor.optimize_stay_times(
                schedule=all_schedule,
                config=config,
                target_improvement_hours=1.0
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Level 4 오류: {str(e)}")
            return None
    
    def _create_applicants(self, config: DateConfig) -> List[Applicant]:
        """설정을 기반으로 지원자 리스트 생성"""
        applicants = []
        
        for job_code, count in config.jobs.items():
            # 해당 직무가 수행할 활동 추출
            activities = [
                activity.name for activity in config.activities
                if config.job_activity_matrix.get((job_code, activity.name), False)
            ]
            
            # 실제 지원자 생성
            for i in range(count):
                applicants.append(Applicant(
                    id=f"{job_code}_{str(i + 1).zfill(3)}",
                    job_code=job_code,
                    required_activities=activities,
                    is_dummy=False
                ))
        
        return applicants
    
    def _extract_batched_constraints(
        self,
        batched_schedule: List[ScheduleItem],
        groups: Dict[str, List[Group]]
    ) -> Dict[str, List[TimeSlot]]:
        """
        Batched 스케줄에서 개별 지원자의 시간 제약 추출
        
        Returns:
            {applicant_id: [TimeSlot, ...]}
        """
        constraints = {}
        
        # 그룹 ID -> 멤버 매핑 생성
        group_members = {}
        for activity_groups in groups.values():
            for group in activity_groups:
                # 그룹의 지원자 ID 리스트 생성
                member_ids = [app.id for app in group.applicants]
                if hasattr(group, 'dummy_ids'):
                    member_ids.extend(group.dummy_ids)
                group_members[group.id] = member_ids
        
        # Batched 스케줄에서 각 지원자의 시간 제약 추출
        for item in batched_schedule:
            if item.group_id and item.group_id in group_members:
                members = group_members[item.group_id]
                for member_id in members:
                    if member_id not in constraints:
                        constraints[member_id] = []
                    # ScheduleItem에서 TimeSlot 생성
                    time_slot = TimeSlot(
                        start_time=item.start_time,
                        end_time=item.end_time,
                        room_name=item.room_name,
                        activity_name=item.activity_name,
                        applicant_id=member_id,
                        group_id=item.group_id
                    )
                    constraints[member_id].append(time_slot)
        
        return constraints
    
    def _backtrack_from_level2(
        self,
        config: DateConfig,
        result: SingleDateResult
    ) -> SingleDateResult:
        """Level 2 실패시 백트래킹 - Level 1부터 재시도"""
        result.logs.append("=== Level 2 백트래킹 시작 ===")
        result.backtrack_count += 1
        
        self._report_progress("Backtrack", 0.0, f"Level 2 백트래킹 시작 ({result.backtrack_count}회차)", {
            "backtrack_count": result.backtrack_count,
            "level": "Level2"
        })
        
        # 최대 백트래킹 횟수 제한
        MAX_BACKTRACK = 3
        if result.backtrack_count > MAX_BACKTRACK:
            result.logs.append(f"백트래킹 한계 도달 ({MAX_BACKTRACK}회)")
            self._report_progress("Backtrack", 1.0, "백트래킹 한계 도달", {
                "max_backtrack": MAX_BACKTRACK
            })
            return result
            
        # 이전 시도 저장
        if result.level1_result:
            total_groups = sum(len(groups) for groups in result.level1_result.groups.values())
            result.attempted_configs.append({
                'dummy_count': result.level1_result.dummy_count,
                'group_count': total_groups
            })
        
        # 더미 수 조정 전략
        adjustment_strategies = [
            lambda dc: dc + 1,      # 더미 1명 추가
            lambda dc: dc + 2,      # 더미 2명 추가  
            lambda dc: dc * 2,      # 더미 2배로
            lambda dc: dc + 5,      # 더미 5명 추가
        ]
        
        for strategy in adjustment_strategies:
            # 이전 더미 수 계산
            prev_dummy = result.level1_result.dummy_count if result.level1_result else 0
            new_dummy_hint = strategy(prev_dummy)
            
            result.logs.append(f"백트래킹 시도 {result.backtrack_count}: 더미 {prev_dummy} → {new_dummy_hint}")
            
            # Level 1을 더미 힌트와 함께 재시도
            level1_result = self._run_level1(config, dummy_hint=new_dummy_hint)
            
            if not level1_result:
                continue
                
            # Level 2 재시도
            level2_result = self._run_level2(config, level1_result)
            
            if level2_result:
                result.logs.append(f"✅ 백트래킹 성공! 더미 {level1_result.dummy_count}명으로 해결")
                result.level1_result = level1_result
                result.level2_result = level2_result
                
                # Level 3 진행
                level3_result = self._run_level3(config, level1_result, level2_result)
                if level3_result and not level3_result.unscheduled:
                    result.level3_result = level3_result
                    result.status = "SUCCESS"
                    result.error_message = None
                    
                    # 전체 스케줄 통합
                    all_schedule = []
                    all_schedule.extend(level2_result.schedule)
                    all_schedule.extend(level3_result.schedule)
                    result.schedule = all_schedule
                    
                return result
                
        result.logs.append("❌ 모든 백트래킹 전략 실패")
        return result
    
    def _backtrack_from_level3(
        self,
        config: DateConfig,
        result: SingleDateResult  
    ) -> SingleDateResult:
        """Level 3 실패시 백트래킹 - Level 2 또는 1부터 재시도"""
        result.logs.append("=== Level 3 백트래킹 시작 ===")
        result.backtrack_count += 1
        
        # 최대 백트래킹 횟수 제한
        MAX_BACKTRACK = 5
        if result.backtrack_count > MAX_BACKTRACK:
            result.logs.append(f"백트래킹 한계 도달 ({MAX_BACKTRACK}회)")
            return result
            
        # 전략 1: 방 재배치로 Level 3만 재시도
        if result.backtrack_count <= 2:
            result.logs.append("전략 1: 방 재배치로 재시도")
            
            # Individual 스케줄러에 다른 seed나 전략 적용
            # (현재는 같은 방식으로 재시도하므로 효과 제한적)
            level3_result = self._run_level3(config, result.level1_result, result.level2_result)
            
            if level3_result and not level3_result.unscheduled:
                result.logs.append("✅ 방 재배치로 해결!")
                result.level3_result = level3_result
                result.status = "SUCCESS"
                result.error_message = None
                
                # 전체 스케줄 통합
                all_schedule = []
                all_schedule.extend(result.level2_result.schedule)
                all_schedule.extend(level3_result.schedule)
                result.schedule = all_schedule
                
                return result
                
        # 전략 2: Level 2부터 재시도 (다른 시간대 배치)
        result.logs.append("전략 2: Level 2부터 재시도")
        return self._backtrack_from_level2(config, result)

    def _backtrack_from_level4(
        self,
        config: DateConfig,
        result: SingleDateResult
    ) -> SingleDateResult:
        """Level 4 실패시 백트래킹 - 기본 스케줄 유지"""
        result.logs.append("=== Level 4 백트래킹: 기본 스케줄 유지 ===")
        
        # Level 4는 후처리 조정이므로 실패해도 기본 스케줄을 유지
        if result.level2_result and result.level3_result:
            # 기본 스케줄 재구성
            basic_schedule = []
            basic_schedule.extend(result.level2_result.schedule)
            basic_schedule.extend(result.level3_result.schedule)
            
            result.schedule = basic_schedule
            result.status = "SUCCESS"
            result.error_message = None
            result.logs.append("✅ 기본 스케줄로 복원 완료")
        
        return result
        
    def _create_modified_config(self, config: DateConfig, dummy_hint: int) -> DateConfig:
        """더미 힌트를 반영한 수정된 설정 생성"""
        # 실제로는 GroupOptimizer가 자동으로 더미를 계산하므로
        # 여기서는 config를 그대로 반환
        # 향후 필요시 dummy_hint를 전달하는 메커니즘 추가 가능
        return config 

    def _run_level23_unified(
        self, 
        config: DateConfig, 
        level1_result: Level1Result
    ) -> Tuple[Optional[Level2Result], Optional[Level3Result]]:
        """🚀 Level 2-3 통합 CP-SAT 스케줄링"""
        try:
            unified_scheduler = UnifiedCPSATScheduler(self.logger)
            
            level2_result, level3_result = unified_scheduler.schedule_unified(
                config=config,
                level1_result=level1_result,
                time_limit=self.LEVEL23_UNIFIED_TIME_LIMIT
            )
            
            return level2_result, level3_result
            
        except Exception as e:
            self.logger.error(f"통합 CP-SAT 스케줄링 오류: {str(e)}")
            return None, None
    
    def _run_legacy_level23(
        self, 
        config: DateConfig, 
        level1_result: Level1Result,
        result: SingleDateResult,
        overall_start_time: float
    ) -> SingleDateResult:
        """기존 방식으로 폴백 실행"""
        try:
            self.logger.info("🔄 기존 분리 스케줄링 방식으로 폴백")
            
            # Level 2: Batched 스케줄링
            self._report_progress("Level2", 0.0, "Batched 활동 스케줄링 시작 (폴백)")
            level2_start = time_module.time()
            level2_result = self._run_level2(config, level1_result)
            level2_time = time_module.time() - level2_start
            
            if not level2_result:
                result.error_message = "Level 2 실패: Batched 활동 스케줄링 불가"
                result.logs.append(f"Level 2 실패 ({level2_time:.1f}초) - 백트래킹 필요")
                return self._backtrack_from_level2(config, result)
            
            result.level2_result = level2_result
            result.logs.append(f"Level 2 완료 ({level2_time:.1f}초): {len(level2_result.schedule)}개 batched 스케줄")
            
            # Level 3: Individual/Parallel 스케줄링
            self._report_progress("Level3", 0.0, "Individual/Parallel 활동 스케줄링 시작 (폴백)")
            level3_start = time_module.time()
            level3_result = self._run_level3(config, level1_result, level2_result)
            level3_time = time_module.time() - level3_start
            
            if not level3_result or level3_result.unscheduled:
                unscheduled_count = len(level3_result.unscheduled) if level3_result else "전체"
                result.error_message = f"Level 3 실패: {unscheduled_count}명 스케줄링 불가"
                result.logs.append(f"Level 3 실패 ({level3_time:.1f}초) - 백트래킹 필요")
                return self._backtrack_from_level3(config, result)
            
            result.level3_result = level3_result
            result.logs.append(f"Level 3 완료 ({level3_time:.1f}초): {len(level3_result.schedule)}개 스케줄 항목")
            
            # Level 4 및 나머지 처리는 기존 코드에서 계속됨
            return self._continue_from_level4(config, result, overall_start_time)
            
        except Exception as e:
            result.error_message = f"폴백 실행 중 예외: {str(e)}"
            result.logs.append(f"폴백 예외: {str(e)}")
            return result
    
    def _run_legacy_level23_only(
        self, 
        config: DateConfig, 
        level1_result: Level1Result
    ) -> Tuple[Optional[Level2Result], Optional[Level3Result], float, float]:
        """기존 분리 스케줄링만 실행 (시간 포함)"""
        try:
            # Level 2
            level2_start = time_module.time()
            level2_result = self._run_level2(config, level1_result)
            level2_time = time_module.time() - level2_start
            
            if not level2_result:
                return None, None, level2_time, 0
            
            # Level 3
            level3_start = time_module.time()
            level3_result = self._run_level3(config, level1_result, level2_result)
            level3_time = time_module.time() - level3_start
            
            if not level3_result or level3_result.unscheduled:
                return level2_result, None, level2_time, level3_time
            
            return level2_result, level3_result, level2_time, level3_time
            
        except Exception as e:
            self.logger.error(f"기존 스케줄링 오류: {str(e)}")
            return None, None, 0, 0
    
    def _continue_from_level4(
        self, 
        config: DateConfig, 
        result: SingleDateResult,
        overall_start_time: float
    ) -> SingleDateResult:
        """Level 4부터 계속 실행"""
        try:
            # Level 4: 후처리 조정
            self._report_progress("Level4", 0.0, "후처리 조정 시작")
            level4_start = time_module.time()
            
            # 전체 스케줄 통합 (Level 2 + Level 3)
            all_schedule = []
            all_schedule.extend(result.level2_result.schedule)
            all_schedule.extend(result.level3_result.schedule)
            
            # Level 4 후처리 조정 실행
            level4_result = self._run_level4(config, all_schedule)
            level4_time = time_module.time() - level4_start
            
            if not level4_result or not level4_result.success:
                result.logs.append(f"Level 4 후처리 조정 실패 ({level4_time:.1f}초) - 기본 스케줄 유지")
                result.schedule = all_schedule
                result.level4_result = level4_result
            else:
                result.logs.append(f"Level 4 완료 ({level4_time:.1f}초): {level4_result.total_improvement_hours:.1f}시간 개선")
                result.schedule = level4_result.optimized_schedule
                result.level4_result = level4_result
            
            result.status = "SUCCESS"
            result.error_message = None
            
            total_time = time_module.time() - overall_start_time
            result.logs.append(f"=== 스케줄링 성공 (총 {total_time:.1f}초) ===")
            
            return result
            
        except Exception as e:
            result.error_message = f"Level 4 처리 중 예외: {str(e)}"
            result.logs.append(f"Level 4 예외: {str(e)}")
            return result

    def _report_progress(
        self, 
        stage: str, 
        progress: float, 
        message: str, 
        details: Dict = None
    ):
        """진행 상황 보고"""
        if self.progress_callback:
            info = ProgressInfo(
                stage=stage,
                progress=progress,
                message=message,
                details=details or {}
            )
            self.progress_callback(info) 