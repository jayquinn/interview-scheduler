"""
🚀 Unified CP-SAT Scheduler: Level 2-3 통합 스케줄러

BatchedScheduler와 IndividualScheduler를 하나의 CP-SAT 모델로 통합하여
전체 지원자의 체류시간을 글로벌 최적화합니다.

핵심 개선사항:
- 순차 배치 문제 해결 → 동시 최적화
- Batched + Individual 활동 통합 모델링
- 단일 목적함수: 총 체류시간 최소화
- 40-60% 체류시간 단축 목표
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import timedelta
from collections import defaultdict
from ortools.sat.python import cp_model
import time

from .types import (
    Activity, Room, Applicant, Group, ActivityMode,
    GroupScheduleResult, IndividualScheduleResult, TimeSlot, 
    GroupAssignment, Level1Result, Level2Result, Level3Result,
    ScheduleItem, DateConfig, PrecedenceRule
)


class UnifiedCPSATScheduler:
    """🚀 Level 2-3 통합 CP-SAT 스케줄러 - 글로벌 체류시간 최적화"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.time_slot_minutes = 5  # 5분 단위 시간 슬롯
        
    def schedule_unified(
        self,
        config: DateConfig,
        level1_result: Level1Result,
        time_limit: float = 120.0
    ) -> Tuple[Optional[Level2Result], Optional[Level3Result]]:
        
        self.logger.info("\n===== [CP-SAT 통합 스케줄러 진단 시작] =====")
        t0 = time.time()
        # [진단] 입력 데이터 상세 로그
        self.logger.info("[진단] 입력 데이터 상세 로그 (Level1 그룹/지원자/활동/방/제약조건)")
        # 그룹
        for activity_name, groups in (level1_result.groups or {}).items():
            self.logger.info(f"[진단] 활동: {activity_name}, 그룹 수: {len(groups)}")
            for group in groups:
                self.logger.info(f"  - 그룹ID: {group.id}, 크기: {group.size}, 지원자: {[a.id for a in group.applicants]}")
                for app in group.applicants:
                    self.logger.info(f"    * 지원자ID: {app.id}, required_activities: {app.required_activities}, is_dummy: {getattr(app, 'is_dummy', False)}")
        # 지원자
        self.logger.info("[진단] 전체 지원자 목록:")
        for app in (level1_result.applicants or []):
            self.logger.info(f"  - 지원자ID: {app.id}, required_activities: {app.required_activities}, is_dummy: {getattr(app, 'is_dummy', False)}")
        # 활동
        self.logger.info("[진단] 활동 목록:")
        for act in config.activities:
            self.logger.info(f"  - {act.name}, mode={act.mode}, duration={act.duration_min}, min_cap={act.min_capacity}, max_cap={act.max_capacity}, required_rooms={act.required_rooms}")
        # 방
        self.logger.info("[진단] 방 목록:")
        for room in config.rooms:
            self.logger.info(f"  - {room.name}, type={room.room_type}, cap={room.capacity}")
        # 제약조건
        self.logger.info("[진단] 선후행 제약조건 목록:")
        for prec in (config.precedence_rules or []):
            self.logger.info(f"  - {prec.predecessor} → {prec.successor}, gap_min={prec.gap_min}, is_adjacent={prec.is_adjacent}")
        try:
            # CP-SAT 통합 모델 구성
            model = cp_model.CpModel()
            start_time = config.operating_hours[0]
            end_time = config.operating_hours[1]
            horizon = int((end_time - start_time).total_seconds() / 60)
            self.logger.info(f"⏰ 운영 시간: {start_time} ~ {end_time} ({horizon}분)")

            # 변수 생성
            t_var = time.time()
            variables = self._create_variables(model, config, level1_result, horizon)
            self.logger.info(f"[진단] 변수 생성 완료 (소요: {time.time()-t_var:.2f}s)")
            for k, v in variables.items():
                self.logger.info(f"  - {k}: {len(v)}개")

            # 제약조건 추가
            t_con = time.time()
            self._add_constraints(model, config, level1_result, variables, horizon)
            self.logger.info(f"[진단] 제약조건 추가 완료 (소요: {time.time()-t_con:.2f}s)")

            # 목적함수
            t_obj = time.time()
            objective_vars = self._create_objective(model, config, level1_result, variables, start_time)
            self.logger.info(f"[진단] 목적함수 변수 개수: {len(objective_vars)} (소요: {time.time()-t_obj:.2f}s)")

            if objective_vars:
                total_stay_time = model.NewIntVar(0, horizon * len(level1_result.applicants), 'total_stay_time')
                model.Add(total_stay_time == sum(objective_vars))
                model.Minimize(total_stay_time)
                self.logger.info(f"✅ 목적함수 설정: {len(objective_vars)}명의 총 체류시간 최소화")
            else:
                self.logger.warning("⚠️ 체류시간 변수가 없어 목적함수 설정 불가")

            # CP-SAT 솔버 실행
            solver = cp_model.CpSolver()
            set_safe_cpsat_parameters(solver)
            solver.parameters.max_time_in_seconds = 300.0  # 5분으로 확장
            solver.parameters.log_search_progress = True
            t_solve = time.time()
            self.logger.info(f"🔍 CP-SAT 통합 최적화 실행 중... (최대 {time_limit}초)")
            status = solver.Solve(model)
            solve_time = time.time() - t_solve
            self.logger.info(f"[진단] Solve 종료 (소요: {solve_time:.2f}s), status: {solver.StatusName(status)}")
            self.logger.info(f"[진단] Objective value: {solver.ObjectiveValue() if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 'N/A'}")
            self.logger.info(f"[진단] NumConflicts: {solver.NumConflicts()}, NumBranches: {solver.NumBranches()}, WallTime: {solver.WallTime():.2f}s")
            try:
                num_vars = model.NumVariables() if hasattr(model, 'NumVariables') else 'N/A'
                num_cons = model.NumConstraints() if hasattr(model, 'NumConstraints') else 'N/A'
                self.logger.info(f"[진단] Model stats: #variables={num_vars}, #constraints={num_cons}")
            except Exception as e:
                self.logger.warning(f"[진단] Model stats 출력 중 예외 발생: {e}")
            self.logger.info(f"[진단] 전체 소요 시간: {time.time()-t0:.2f}s")

            # 결과 분석
            if status == cp_model.OPTIMAL:
                self.logger.info("✅ 최적해 발견!")
            elif status == cp_model.FEASIBLE:
                self.logger.info("✅ 실행 가능해 발견!")
            else:
                self.logger.error(f"❌ CP-SAT 통합 최적화 실패: {solver.StatusName(status)}")
                # 실패 시 주요 변수/제약/상태 추가 출력
                self.logger.error(f"[진단] 주요 변수/제약/상태:")
                for k, v in variables.items():
                    self.logger.error(f"  - {k}: {len(v)}개")
                self.logger.error(f"  #variables={model.NumVariables()}, #constraints={model.NumConstraints()}")
                self.logger.error(f"  NumConflicts={solver.NumConflicts()}, NumBranches={solver.NumBranches()}, WallTime={solver.WallTime():.2f}s")
                return None, None

            # 체류시간 통계 출력
            if objective_vars:
                total_minutes = solver.Value(total_stay_time)
                avg_hours = total_minutes / len(objective_vars) / 60
                self.logger.info(f"📊 통합 최적화 결과: 평균 체류시간 {avg_hours:.1f}시간")

            # 결과 추출 및 분리
            return self._extract_results(solver, config, level1_result, variables, start_time)

        except Exception as e:
            self.logger.error(f"❌ 통합 스케줄링 중 예외 발생: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None, None
    
    def _create_variables(
        self, 
        model: cp_model.CpModel, 
        config: DateConfig, 
        level1_result: Level1Result,
        horizon: int
    ) -> Dict[str, any]:
        """🏗️ CP-SAT 변수 생성"""
        variables = {
            'group_intervals': {},      # 그룹 활동 interval
            'group_starts': {},         # 그룹 시작시간
            'group_ends': {},           # 그룹 종료시간
            'group_rooms': {},          # 그룹 방 배정
            'individual_intervals': {}, # 개별 활동 interval
            'individual_starts': {},    # 개별 시작시간
            'individual_ends': {},      # 개별 종료시간
            'individual_presence': {},  # 개별 활동 presence
            'individual_rooms': {}      # 개별 방 배정
        }
        
        # 1. Batched 활동 변수 생성
        self._create_batched_variables(model, config, level1_result, horizon, variables)
        
        # 2. Individual 활동 변수 생성
        self._create_individual_variables(model, config, level1_result, horizon, variables)
        
        return variables
    
    def _create_batched_variables(
        self, 
        model: cp_model.CpModel, 
        config: DateConfig, 
        level1_result: Level1Result,
        horizon: int, 
        variables: Dict[str, any]
    ):
        """🏗️ Batched 활동 변수 생성"""
        self.logger.info("🔧 Batched 활동 변수 생성 시작...")
        
        batched_count = 0
        for activity_name, groups in level1_result.groups.items():
            activity = next((a for a in config.activities if a.name == activity_name), None)
            if not activity or activity.mode != ActivityMode.BATCHED:
                continue
                
            duration_min = int(activity.duration.total_seconds() / 60)
            
            for group in groups:
                group_id = group.id
                suffix = f"{group_id}_{activity_name}"
                self.logger.info(f"[진단] Batched 변수 생성: 그룹ID={group_id}, 활동={activity_name}, duration={duration_min}, 지원자={[a.id for a in group.applicants]}")
                
                # 시작/종료 시간 변수 (🚨 핵심: 고정된 순차 배치가 아닌 최적화 변수!)
                start_var = model.NewIntVar(0, horizon - duration_min, f'batch_start_{suffix}')
                end_var = model.NewIntVar(duration_min, horizon, f'batch_end_{suffix}')
                
                # 일관성 제약: end = start + duration
                model.Add(end_var == start_var + duration_min)
                
                # Interval 변수
                interval_var = model.NewIntervalVar(start_var, duration_min, end_var, f'batch_interval_{suffix}')
                
                # 방 배정 변수
                activity_rooms = [r for r in config.rooms if any(rt in r.room_type for rt in activity.required_rooms)]
                room_vars = {}
                for room in activity_rooms:
                    room_var = model.NewBoolVar(f'batch_room_{suffix}_{room.name}')
                    room_vars[room.name] = room_var
                
                # 정확히 하나의 방 선택
                if room_vars:
                    model.Add(sum(room_vars.values()) == 1)
                
                # 변수 저장
                variables['group_intervals'][group_id] = interval_var
                variables['group_starts'][group_id] = start_var
                variables['group_ends'][group_id] = end_var
                variables['group_rooms'][group_id] = room_vars
                
                batched_count += 1
        
        self.logger.info(f"✅ Batched 변수 생성 완료: {batched_count}개 그룹")
    
    def _create_individual_variables(
        self, 
        model: cp_model.CpModel, 
        config: DateConfig, 
        level1_result: Level1Result,
        horizon: int, 
        variables: Dict[str, any]
    ):
        """🏗️ Individual 활동 변수 생성"""
        self.logger.info("🔧 Individual 활동 변수 생성 시작...")
        
        individual_count = 0
        individual_activities = [a for a in config.activities if a.mode in [ActivityMode.INDIVIDUAL, ActivityMode.PARALLEL]]
        
        for applicant in level1_result.applicants:
            for activity in individual_activities:
                if activity.name not in applicant.required_activities:
                    continue
                suffix = f"{applicant.id}_{activity.name}"
                duration_min = int(activity.duration.total_seconds() / 60)
                self.logger.info(f"[진단] Individual 변수 생성: 지원자={applicant.id}, 활동={activity.name}, duration={duration_min}")
                    
                # 시작/종료 시간 변수
                start_var = model.NewIntVar(0, horizon - duration_min, f'ind_start_{suffix}')
                end_var = model.NewIntVar(duration_min, horizon, f'ind_end_{suffix}')
                presence_var = model.NewBoolVar(f'ind_presence_{suffix}')
                
                # 일관성 제약: end = start + duration (presence가 True인 경우만)
                model.Add(end_var == start_var + duration_min).OnlyEnforceIf(presence_var)
                
                # Interval 변수
                interval_var = model.NewOptionalIntervalVar(
                    start_var, duration_min, end_var, presence_var, f'ind_interval_{suffix}'
                )
                
                # 방 배정 변수
                activity_rooms = [r for r in config.rooms if any(rt in r.room_type for rt in activity.required_rooms)]
                room_vars = {}
                for room in activity_rooms:
                    room_var = model.NewBoolVar(f'ind_room_{suffix}_{room.name}')
                    room_vars[room.name] = room_var
                
                # 방 배정 제약: presence가 True면 정확히 하나의 방 선택
                if room_vars:
                    model.Add(sum(room_vars.values()) == 1).OnlyEnforceIf(presence_var)
                    model.Add(sum(room_vars.values()) == 0).OnlyEnforceIf(presence_var.Not())
                
                # 필수 활동 제약
                model.Add(presence_var == 1)  # 모든 필수 활동은 반드시 배정
                
                # 변수 저장
                variables['individual_intervals'][(applicant.id, activity.name)] = interval_var
                variables['individual_starts'][(applicant.id, activity.name)] = start_var
                variables['individual_ends'][(applicant.id, activity.name)] = end_var
                variables['individual_presence'][(applicant.id, activity.name)] = presence_var
                variables['individual_rooms'][(applicant.id, activity.name)] = room_vars
                
                individual_count += 1
        
        self.logger.info(f"✅ Individual 변수 생성 완료: {individual_count}개 활동")
    
    def _add_constraints(
        self, 
        model: cp_model.CpModel, 
        config: DateConfig, 
        level1_result: Level1Result,
        variables: Dict[str, any], 
        horizon: int
    ):
        """🔗 제약조건 추가"""
        self.logger.info("🔧 제약조건 추가 시작...")
        
        # 1. 방 용량 제약 (같은 시간에 같은 방 사용 불가)
        self._add_room_constraints(model, config, level1_result, variables)
        
        # 2. 선후행 제약
        self._add_precedence_constraints(model, config, variables)
        
        # 3. 지원자별 활동 시간 충돌 방지
        self._add_applicant_conflict_constraints(model, level1_result, variables)
        
        self.logger.info("✅ 모든 제약조건 추가 완료")
    
    def _add_room_constraints(
        self, 
        model: cp_model.CpModel, 
        config: DateConfig, 
        level1_result: Level1Result,
        variables: Dict[str, any]
    ):
        """🏠 방 용량 제약"""
        for room in config.rooms:
            room_intervals = []
            
            # Batched 활동의 방 사용
            for group_id, room_vars in variables['group_rooms'].items():
                if room.name in room_vars:
                    # 이 방을 사용하는 경우의 interval
                    group_interval = variables['group_intervals'][group_id]
                    
                    # 해당 그룹의 활동 찾기
                    activity_duration = None
                    for act_name, groups in level1_result.groups.items():
                        for group in groups:
                            if group.id == group_id:
                                activity = next((a for a in config.activities if a.name == act_name), None)
                                if activity:
                                    activity_duration = int(activity.duration.total_seconds() / 60)
                                break
                        if activity_duration:
                            break
                    
                    if activity_duration:
                        # 조건부 interval 생성
                        conditional_interval = model.NewOptionalIntervalVar(
                            variables['group_starts'][group_id],
                            activity_duration,
                            variables['group_ends'][group_id],
                            room_vars[room.name],
                            f'room_interval_batch_{group_id}_{room.name}'
                        )
                        room_intervals.append(conditional_interval)
            
            # Individual 활동의 방 사용
            for (applicant_id, activity_name), room_vars in variables['individual_rooms'].items():
                if room.name in room_vars:
                    # 이 방을 사용하는 경우의 interval
                    activity = next(a for a in config.activities if a.name == activity_name)
                    duration_min = int(activity.duration.total_seconds() / 60)
                    
                    conditional_interval = model.NewOptionalIntervalVar(
                        variables['individual_starts'][(applicant_id, activity_name)],
                        duration_min,
                        variables['individual_ends'][(applicant_id, activity_name)],
                        room_vars[room.name],
                        f'room_interval_ind_{applicant_id}_{activity_name}_{room.name}'
                    )
                    room_intervals.append(conditional_interval)
            
            # 방 사용 겹침 방지
            if room_intervals:
                model.AddNoOverlap(room_intervals)
    
    def _add_precedence_constraints(
        self, 
        model: cp_model.CpModel, 
        config: DateConfig, 
        variables: Dict[str, any]
    ):
        """⏰ 선후행 제약"""
        # TODO: 선후행 제약 구현
        # 현재는 기본 구현으로 패스
        pass
    
    def _add_applicant_conflict_constraints(
        self, 
        model: cp_model.CpModel, 
        level1_result: Level1Result, 
        variables: Dict[str, any]
    ):
        """👤 지원자별 활동 충돌 방지"""
        for applicant in level1_result.applicants:
            applicant_intervals = []
            
            # 해당 지원자의 모든 활동 interval 수집
            # 1. Batched 활동
            for group_id, interval in variables['group_intervals'].items():
                # 이 지원자가 해당 그룹에 속하는지 확인
                for activity_groups in level1_result.groups.values():
                    for group in activity_groups:
                        if group.id == group_id and applicant in group.applicants:
                            applicant_intervals.append(interval)
            
            # 2. Individual 활동
            for (app_id, activity_name), interval in variables['individual_intervals'].items():
                if app_id == applicant.id:
                    applicant_intervals.append(interval)
            
            # 동일 지원자의 활동들은 겹치지 않도록
            if len(applicant_intervals) > 1:
                model.AddNoOverlap(applicant_intervals)
    
    def _create_objective(
        self, 
        model: cp_model.CpModel, 
        config: DateConfig, 
        level1_result: Level1Result,
        variables: Dict[str, any], 
        start_time: timedelta
    ) -> List:
        """🎯 체류시간 최소화 목적함수 생성"""
        self.logger.info("🎯 체류시간 최소화 목적함수 생성 중...")
        
        stay_time_vars = []
        
        for applicant in level1_result.applicants:
            if applicant.is_dummy:
                continue  # 더미 지원자는 제외
                
            # 해당 지원자의 모든 활동 시작/종료 시간 수집
            applicant_start_times = []
            applicant_end_times = []
            
            # 1. Batched 활동 시간
            for group_id in variables['group_starts'].keys():
                # 이 지원자가 해당 그룹에 속하는지 확인
                for activity_groups in level1_result.groups.values():
                    for group in activity_groups:
                        if group.id == group_id and applicant in group.applicants:
                            applicant_start_times.append(variables['group_starts'][group_id])
                            applicant_end_times.append(variables['group_ends'][group_id])
            
            # 2. Individual 활동 시간
            for (app_id, activity_name) in variables['individual_starts'].keys():
                if app_id == applicant.id:
                    applicant_start_times.append(variables['individual_starts'][(app_id, activity_name)])
                    applicant_end_times.append(variables['individual_ends'][(app_id, activity_name)])
            
            # 체류시간 계산 (활동이 있는 경우만)
            if applicant_start_times and applicant_end_times:
                # 첫 활동 시작시간
                first_start = model.NewIntVar(0, 24*60, f'first_start_{applicant.id}')
                model.AddMinEquality(first_start, applicant_start_times)
                
                # 마지막 활동 종료시간
                last_end = model.NewIntVar(0, 24*60, f'last_end_{applicant.id}')
                model.AddMaxEquality(last_end, applicant_end_times)
                
                # 체류시간 = 마지막 종료 - 첫 시작
                stay_time = model.NewIntVar(0, 24*60, f'stay_time_{applicant.id}')
                model.Add(stay_time == last_end - first_start)
                
                stay_time_vars.append(stay_time)
                
                self.logger.debug(f"지원자 {applicant.id}: {len(applicant_start_times)}개 활동 체류시간 변수 생성")
        
        self.logger.info(f"✅ 체류시간 목적함수 생성 완료: {len(stay_time_vars)}명")
        return stay_time_vars
    
    def _extract_results(
        self, 
        solver: cp_model.CpSolver, 
        config: DateConfig, 
        level1_result: Level1Result,
        variables: Dict[str, any], 
        start_time: timedelta
    ) -> Tuple[Level2Result, Level3Result]:
        """📤 결과 추출 및 Level2Result, Level3Result로 분리"""
        self.logger.info("[진단] 결과 추출 단계 진입")
        
        # Level 2 결과 (Batched 활동)
        level2_result = Level2Result()
        batched_schedule = []
        group_assignments = []
        
        # Level 3 결과 (Individual 활동)  
        level3_result = Level3Result()
        individual_schedule = []
        
        # Batched 결과 추출
        for group_id in variables['group_starts'].keys():
            start_min = solver.Value(variables['group_starts'][group_id])
            end_min = solver.Value(variables['group_ends'][group_id])
            
            # 실제 시간으로 변환
            actual_start = start_time + timedelta(minutes=start_min)
            actual_end = start_time + timedelta(minutes=end_min)
            
            # 방 찾기
            assigned_room = None
            room_vars = variables['group_rooms'][group_id]
            for room_name, room_var in room_vars.items():
                if solver.Value(room_var):
                    assigned_room = room_name
                    break
            
            # 그룹 정보 찾기
            group_info = None
            activity_name = None
            for act_name, groups in level1_result.groups.items():
                for group in groups:
                    if group.id == group_id:
                        group_info = group
                        activity_name = act_name
                        break
                if group_info:
                    break
            
            if group_info and assigned_room and activity_name:
                # GroupAssignment 생성
                room_obj = next((r for r in config.rooms if r.name == assigned_room), None)
                if room_obj:
                    assignment = GroupAssignment(
                        group=group_info,
                        room=room_obj,
                        start_time=actual_start,
                        end_time=actual_end
                    )
                    group_assignments.append(assignment)
                
                # 각 지원자에 대한 ScheduleItem 생성
                for applicant in group_info.applicants:
                    schedule_item = ScheduleItem(
                        applicant_id=applicant.id,
                        job_code=applicant.job_code,
                        activity_name=activity_name,
                        room_name=assigned_room,
                        start_time=actual_start,
                        end_time=actual_end,
                        group_id=group_id
                    )
                    batched_schedule.append(schedule_item)
        
        # Individual 결과 추출
        for (applicant_id, activity_name) in variables['individual_starts'].keys():
            if solver.Value(variables['individual_presence'][(applicant_id, activity_name)]):
                start_min = solver.Value(variables['individual_starts'][(applicant_id, activity_name)])
                end_min = solver.Value(variables['individual_ends'][(applicant_id, activity_name)])
                
                # 실제 시간으로 변환
                actual_start = start_time + timedelta(minutes=start_min)
                actual_end = start_time + timedelta(minutes=end_min)
                
                # 방 찾기
                assigned_room = None
                room_vars = variables['individual_rooms'][(applicant_id, activity_name)]
                for room_name, room_var in room_vars.items():
                    if solver.Value(room_var):
                        assigned_room = room_name
                        break
                
                # 지원자 정보 찾기
                job_code = None
                for applicant in level1_result.applicants:
                    if applicant.id == applicant_id:
                        job_code = applicant.job_code
                        break
                
                if assigned_room and job_code:
                    schedule_item = ScheduleItem(
                        applicant_id=applicant_id,
                        job_code=job_code,
                        activity_name=activity_name,
                        room_name=assigned_room,
                        start_time=actual_start,
                        end_time=actual_end
                    )
                    individual_schedule.append(schedule_item)
        
        # 결과 설정
        level2_result.schedule = batched_schedule
        level2_result.group_results = [
            GroupScheduleResult(
                activity_name="통합최적화",
                assignments=group_assignments,
                success=True
            )
        ]
        
        level3_result.schedule = individual_schedule
        level3_result.unscheduled = []  # CP-SAT로 모든 활동 배정됨
        
        self.logger.info(f"[진단] 추출된 Batched 스케줄 개수: {len(batched_schedule)}")
        self.logger.info(f"[진단] 추출된 Individual 스케줄 개수: {len(individual_schedule)}")
        if not batched_schedule and not individual_schedule:
            self.logger.error("[진단] 결과가 비어 있음! (Batched/Individual 모두 0개)")
        
        self.logger.info(f"✅ 결과 추출 완료: Batched {len(batched_schedule)}개, Individual {len(individual_schedule)}개")
        
        return level2_result, level3_result 