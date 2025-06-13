# solver/mixed_scheduler.py
"""
Level 3: Mixed 활동 스케줄링 모듈
고정된 batched 시간표를 바탕으로 individual/parallel 활동을 스케줄링합니다.
"""

import pandas as pd
from ortools.sat.python import cp_model
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MixedScheduler:
    """Individual/Parallel 활동을 고정된 Batched 시간표와 통합하는 스케줄러"""
    
    def __init__(self,
                 candidates: pd.DataFrame,
                 groups: Dict[int, List[str]],
                 batched_schedule: Dict,
                 individual_activities: pd.DataFrame,
                 parallel_activities: pd.DataFrame,
                 room_info: Dict[str, Dict],
                 oper_hours: Dict[str, Tuple[int, int]],
                 precedence_rules: List[Tuple],
                 min_gap_min: int = 5):
        """
        Args:
            candidates: 지원자 정보
            groups: {그룹번호: [지원자ID 리스트]}
            batched_schedule: {(그룹번호, 활동명): {"start": 분, "end": 분, "room": 방}}
            individual_activities: individual 모드 활동 정보
            parallel_activities: parallel 모드 활동 정보
            room_info: {방이름: {"capacity": 최대수용인원}}
            oper_hours: {직무코드: (시작분, 종료분)}
            precedence_rules: [(선행활동, 후행활동, 최소간격)]
            min_gap_min: 활동 간 최소 간격(분)
        """
        self.candidates = candidates
        self.groups = groups
        self.batched_schedule = batched_schedule
        self.individual_activities = individual_activities
        self.parallel_activities = parallel_activities
        self.room_info = room_info
        self.oper_hours = oper_hours
        self.precedence_rules = precedence_rules
        self.min_gap_min = min_gap_min
        
        # 지원자별 그룹 매핑
        self.candidate_to_group = {}
        for group_id, members in groups.items():
            for member in members:
                self.candidate_to_group[member] = group_id
        
        # 활동 정보 통합
        self.act_info = {}
        for _, row in individual_activities.iterrows():
            self.act_info[row['activity']] = {
                'mode': 'individual',
                'duration': int(row['duration_min']),
                'room_type': row['room_type']
            }
        for _, row in parallel_activities.iterrows():
            self.act_info[row['activity']] = {
                'mode': 'parallel',
                'duration': int(row['duration_min']),
                'room_type': row['room_type']
            }
    
    def _get_fixed_intervals_for_candidate(self, candidate_id: str) -> List[Tuple[int, int, str]]:
        """지원자의 고정된 batched 활동 시간을 반환"""
        fixed_intervals = []
        
        if candidate_id in self.candidate_to_group:
            group_id = self.candidate_to_group[candidate_id]
            
            for (g_id, act_name), schedule in self.batched_schedule.items():
                if g_id == group_id:
                    # 안전한 키 접근
                    if isinstance(schedule, dict):
                        start_time = schedule.get('start')
                        end_time = schedule.get('end')
                        
                        if start_time is not None and end_time is not None:
                            fixed_intervals.append((
                                start_time,
                                end_time,
                                act_name
                            ))
                        else:
                            # 키가 없는 경우 로깅
                            print(f"DEBUG: Missing 'start' or 'end' key in schedule for group {g_id}, activity {act_name}")
                            print(f"DEBUG: Available keys: {list(schedule.keys())}")
                    else:
                        print(f"DEBUG: schedule is not a dict: {type(schedule)} = {schedule}")
        
        return sorted(fixed_intervals, key=lambda x: x[0])
    
    def optimize(self, time_limit_sec: float = 120.0) -> Tuple[pd.DataFrame, str, str]:
        """
        Individual/Parallel 활동 스케줄링 최적화 실행
        
        Returns:
            Tuple[schedule_df, status, logs]:
                - schedule_df: 전체 스케줄 DataFrame
                - status: 최적화 상태
                - logs: 실행 로그
        """
        model = cp_model.CpModel()
        logs = []
        
        try:
            # Horizon 계산
            horizon = max(end for _, (_, end) in self.oper_hours.items())
            
            # 변수 정의
            intervals = {}  # (candidate_id, activity) -> interval_var
            room_assignments = {}  # (candidate_id, activity, room) -> bool_var
            
            # 각 지원자의 individual/parallel 활동에 대해 변수 생성
            for _, candidate in self.candidates.iterrows():
                cid = candidate['id']
                job_code = candidate['job_code']
                
                # 이 지원자가 수행해야 할 활동 결정 (실제 구현에서는 job_acts_map 참조)
                # 여기서는 모든 individual/parallel 활동을 수행한다고 가정
                candidate_activities = list(self.act_info.keys())
                
                for act_name, act_data in self.act_info.items():
                    if act_name not in candidate_activities:
                        continue
                    
                    duration = act_data['duration']
                    
                    # 시간 변수
                    start_var = model.NewIntVar(0, horizon, f'start_{cid}_{act_name}')
                    end_var = model.NewIntVar(0, horizon, f'end_{cid}_{act_name}')
                    interval_var = model.NewIntervalVar(start_var, duration, end_var,
                                                       f'interval_{cid}_{act_name}')
                    intervals[(cid, act_name)] = interval_var
                    
                    # 방 배정 변수
                    room_type = act_data['room_type']
                    possible_rooms = [r for r in self.room_info.keys() if r.startswith(room_type)]
                    
                    room_vars = []
                    for room in possible_rooms:
                        room_var = model.NewBoolVar(f'room_{cid}_{act_name}_{room}')
                        room_assignments[(cid, act_name, room)] = room_var
                        room_vars.append(room_var)
                    
                    # 각 활동은 정확히 하나의 방에 배정
                    if room_vars:
                        model.AddExactlyOne(room_vars)
            
            # 제약 1: 같은 지원자의 활동들은 겹치지 않음
            for cid in self.candidates['id']:
                # 고정된 batched 활동 시간
                fixed_intervals = self._get_fixed_intervals_for_candidate(cid)
                
                # individual/parallel 활동들
                candidate_intervals = [(act, iv) for (c, act), iv in intervals.items() if c == cid]
                
                # 모든 활동 간 겹침 방지
                for act_name, iv in candidate_intervals:
                    # 고정된 시간과 겹치지 않도록
                    for fixed_start, fixed_end, fixed_act in fixed_intervals:
                        # iv는 fixed 구간 전에 끝나거나 후에 시작
                        b = model.NewBoolVar(f'no_overlap_{cid}_{act_name}_{fixed_act}')
                        model.Add(iv.EndExpr() <= fixed_start).OnlyEnforceIf(b)
                        model.Add(iv.StartExpr() >= fixed_end).OnlyEnforceIf(b.Not())
                
                # individual/parallel 활동끼리도 겹치지 않음
                if len(candidate_intervals) > 1:
                    model.AddNoOverlap([iv for _, iv in candidate_intervals])
            
            # 제약 2: 활동 간 최소 간격
            if self.min_gap_min > 0:
                for cid in self.candidates['id']:
                    acts = [(act, iv) for (c, act), iv in intervals.items() if c == cid]
                    for i in range(len(acts)):
                        for j in range(i + 1, len(acts)):
                            act1, iv1 = acts[i]
                            act2, iv2 = acts[j]
                            
                            b = model.NewBoolVar(f'gap_{cid}_{act1}_{act2}')
                            model.Add(iv2.StartExpr() >= iv1.EndExpr() + self.min_gap_min).OnlyEnforceIf(b)
                            model.Add(iv1.StartExpr() >= iv2.EndExpr() + self.min_gap_min).OnlyEnforceIf(b.Not())
            
            # 제약 3: 선후행 제약
            for rule in self.precedence_rules:
                if len(rule) >= 3:
                    pred, succ, gap = rule[:3]
                    
                    for cid in self.candidates['id']:
                        # 선행이 batched이고 후행이 individual/parallel인 경우
                        if pred in [act for (_, act), _ in self.batched_schedule.items()]:
                            if (cid, succ) in intervals:
                                # 해당 지원자의 batched 활동 시간 찾기
                                group_id = self.candidate_to_group.get(cid)
                                if group_id is not None:
                                    for (g, act), sched in self.batched_schedule.items():
                                        if g == group_id and act == pred:
                                            succ_iv = intervals[(cid, succ)]
                                            model.Add(succ_iv.StartExpr() >= sched['end'] + gap)
                        
                        # 둘 다 individual/parallel인 경우
                        elif (cid, pred) in intervals and (cid, succ) in intervals:
                            pred_iv = intervals[(cid, pred)]
                            succ_iv = intervals[(cid, succ)]
                            model.Add(succ_iv.StartExpr() >= pred_iv.EndExpr() + gap)
            
            # 제약 4: 방 용량 제약
            for room_name, room_data in self.room_info.items():
                capacity = room_data['capacity']
                
                # individual 활동: 용량 1로 처리
                individual_intervals = []
                for (cid, act_name), iv in intervals.items():
                    if self.act_info[act_name]['mode'] == 'individual':
                        for (c, a, r), room_var in room_assignments.items():
                            if c == cid and a == act_name and r == room_name:
                                opt_iv = model.NewOptionalIntervalVar(
                                    iv.StartExpr(),
                                    self.act_info[act_name]['duration'],
                                    iv.EndExpr(),
                                    room_var,
                                    f'opt_iv_{cid}_{act_name}_{room_name}'
                                )
                                individual_intervals.append(opt_iv)
                
                # parallel 활동: 실제 용량 사용
                parallel_intervals = []
                parallel_demands = []
                for (cid, act_name), iv in intervals.items():
                    if self.act_info[act_name]['mode'] == 'parallel':
                        for (c, a, r), room_var in room_assignments.items():
                            if c == cid and a == act_name and r == room_name:
                                opt_iv = model.NewOptionalIntervalVar(
                                    iv.StartExpr(),
                                    self.act_info[act_name]['duration'],
                                    iv.EndExpr(),
                                    room_var,
                                    f'opt_iv_{cid}_{act_name}_{room_name}'
                                )
                                parallel_intervals.append(opt_iv)
                                parallel_demands.append(1)  # 각 지원자는 1명분의 용량 사용
                
                # individual과 parallel을 함께 처리
                all_intervals = individual_intervals + parallel_intervals
                all_demands = [1] * len(individual_intervals) + parallel_demands
                
                if all_intervals:
                    model.AddCumulative(all_intervals, all_demands, capacity)
            
            # 제약 5: 운영 시간 제약
            for (cid, act_name), iv in intervals.items():
                job_code = self.candidates[self.candidates['id'] == cid]['job_code'].iloc[0]
                if job_code in self.oper_hours:
                    start_time, end_time = self.oper_hours[job_code]
                    model.Add(iv.StartExpr() >= start_time)
                    model.Add(iv.EndExpr() <= end_time)
            
            # 목적함수: 대기시간 최소화
            total_waiting_time = []
            for cid in self.candidates['id']:
                cid_intervals = [(act, iv) for (c, act), iv in intervals.items() if c == cid]
                fixed_intervals = self._get_fixed_intervals_for_candidate(cid)
                
                # 모든 시간 구간 통합 후 정렬
                all_times = []
                for act, iv in cid_intervals:
                    all_times.append(('var', act, iv.StartExpr(), iv.EndExpr()))
                for start, end, act in fixed_intervals:
                    all_times.append(('fixed', act, start, end))
                
                # 인접한 활동 간 대기시간 계산
                # (이 부분은 복잡하므로 간소화)
                
            # 간단히 전체 소요시간 최소화로 대체
            makespan = model.NewIntVar(0, horizon, 'makespan')
            for iv in intervals.values():
                model.Add(makespan >= iv.EndExpr())
            model.Minimize(makespan)
            
            # 솔버 실행
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = time_limit_sec
            solver.parameters.num_search_workers = 8
            solver.parameters.log_search_progress = True
            
            status = solver.Solve(model)
            
            # 결과 처리
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                # 결과를 DataFrame으로 변환
                rows = []
                
                # Batched 활동 추가
                for (group_id, act_name), schedule in self.batched_schedule.items():
                    for member_id in self.groups[group_id]:
                        rows.append({
                            'id': member_id,
                            'activity': act_name,
                            'mode': 'batched',
                            'start_min': schedule['start'],
                            'end_min': schedule['end'],
                            'room': schedule['room'],
                            'group_id': group_id
                        })
                
                # Individual/Parallel 활동 추가
                for (cid, act_name), iv in intervals.items():
                    start_min = solver.Value(iv.StartExpr())
                    end_min = solver.Value(iv.EndExpr())
                    
                    # 배정된 방 찾기
                    assigned_room = None
                    for (c, a, r), room_var in room_assignments.items():
                        if c == cid and a == act_name and solver.Value(room_var) == 1:
                            assigned_room = r
                            break
                    
                    rows.append({
                        'id': cid,
                        'activity': act_name,
                        'mode': self.act_info[act_name]['mode'],
                        'start_min': start_min,
                        'end_min': end_min,
                        'room': assigned_room or "미배정",
                        'group_id': self.candidate_to_group.get(cid)
                    })
                
                schedule_df = pd.DataFrame(rows)
                
                # 로그 생성
                logs.append(f"전체 스케줄링 완료")
                logs.append(f"총 소요시간: {solver.Value(makespan)}분")
                logs.append(f"스케줄된 활동 수: {len(schedule_df)}")
                
                status_name = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
                return schedule_df, status_name, "\n".join(logs)
                
            else:
                return pd.DataFrame(), solver.StatusName(status), "스케줄링 실패"
                
        except Exception as e:
            logger.error(f"Mixed 스케줄링 중 오류: {e}", exc_info=True)
            return pd.DataFrame(), "ERROR", f"오류: {str(e)}" 