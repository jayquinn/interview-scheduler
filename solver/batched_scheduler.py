"""
Level 2: Batched 활동 스케줄링 모듈
고정된 그룹으로 batched 모드 활동들의 시간표를 생성합니다.
"""

import pandas as pd
from ortools.sat.python import cp_model
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BatchedScheduler:
    """Batched 활동 스케줄링 최적화"""
    
    def __init__(self,
                 groups: Dict[int, List[str]],
                 batched_activities: pd.DataFrame,
                 room_info: Dict[str, Dict],
                 oper_hours: Dict[str, Tuple[int, int]],
                 precedence_rules: List[Tuple],
                 min_gap_min: int = 5):
        """
        Args:
            groups: {그룹번호: [지원자ID 리스트]}
            batched_activities: batched 모드 활동 정보
            room_info: {방이름: {"capacity": 최대수용인원}}
            oper_hours: {직무코드: (시작분, 종료분)}
            precedence_rules: [(선행활동, 후행활동, 최소간격)]
            min_gap_min: 활동 간 최소 간격(분)
        """
        self.groups = groups
        self.batched_activities = batched_activities
        self.room_info = room_info
        self.oper_hours = oper_hours
        self.precedence_rules = precedence_rules
        self.min_gap_min = min_gap_min
        
        # 활동 정보 딕셔너리로 변환
        self.act_info = {
            row['activity']: {
                'duration': int(row['duration_min']),
                'room_type': row['room_type']
            }
            for _, row in batched_activities.iterrows()
        }
        
    def optimize(self, time_limit_sec: float = 120.0) -> Tuple[Dict, str, str]:
        """
        Batched 활동 스케줄링 최적화 실행
        
        Returns:
            Tuple[schedule, status, logs]:
                - schedule: {(그룹번호, 활동명): {"start": 시작시간(분), "end": 종료시간(분), "room": 배정방}}
                - status: 최적화 상태
                - logs: 실행 로그
        """
        model = cp_model.CpModel()
        logs = []
        
        try:
            # Horizon 계산
            horizon = max(end for _, (_, end) in self.oper_hours.items())
            
            # 변수 정의
            intervals = {}  # (group_id, activity) -> interval_var
            room_assignments = {}  # (group_id, activity, room) -> bool_var
            
            # 각 그룹의 각 batched 활동에 대해 변수 생성
            for group_id, members in self.groups.items():
                for act_name, act_data in self.act_info.items():
                    duration = act_data['duration']
                    
                    # 시간 변수
                    start_var = model.NewIntVar(0, horizon, f'start_g{group_id}_{act_name}')
                    end_var = model.NewIntVar(0, horizon, f'end_g{group_id}_{act_name}')
                    interval_var = model.NewIntervalVar(start_var, duration, end_var, 
                                                       f'interval_g{group_id}_{act_name}')
                    intervals[(group_id, act_name)] = interval_var
                    
                    # 방 배정 변수
                    room_type = act_data['room_type']
                    possible_rooms = [r for r in self.room_info.keys() if r.startswith(room_type)]
                    
                    room_vars = []
                    for room in possible_rooms:
                        room_var = model.NewBoolVar(f'room_g{group_id}_{act_name}_{room}')
                        room_assignments[(group_id, act_name, room)] = room_var
                        room_vars.append(room_var)
                    
                    # 각 활동은 정확히 하나의 방에 배정
                    if room_vars:
                        model.AddExactlyOne(room_vars)
            
            # 제약 1: 같은 그룹의 활동들은 겹치지 않음
            for group_id in self.groups.keys():
                group_intervals = [iv for (g, _), iv in intervals.items() if g == group_id]
                if len(group_intervals) > 1:
                    model.AddNoOverlap(group_intervals)
            
            # 제약 2: 활동 간 최소 간격
            if self.min_gap_min > 0:
                for group_id in self.groups.keys():
                    acts = list(self.act_info.keys())
                    for i in range(len(acts)):
                        for j in range(i + 1, len(acts)):
                            if (group_id, acts[i]) in intervals and (group_id, acts[j]) in intervals:
                                iv1 = intervals[(group_id, acts[i])]
                                iv2 = intervals[(group_id, acts[j])]
                                
                                # 두 활동 사이의 순서를 결정하는 변수
                                b = model.NewBoolVar(f'order_g{group_id}_{acts[i]}_{acts[j]}')
                                model.Add(iv2.StartExpr() >= iv1.EndExpr() + self.min_gap_min).OnlyEnforceIf(b)
                                model.Add(iv1.StartExpr() >= iv2.EndExpr() + self.min_gap_min).OnlyEnforceIf(b.Not())
            
            # 제약 3: 선후행 제약
            for rule in self.precedence_rules:
                if len(rule) >= 3:
                    pred, succ, gap = rule[:3]
                    
                    # batched 활동에만 적용
                    if pred in self.act_info and succ in self.act_info:
                        for group_id in self.groups.keys():
                            if (group_id, pred) in intervals and (group_id, succ) in intervals:
                                pred_iv = intervals[(group_id, pred)]
                                succ_iv = intervals[(group_id, succ)]
                                model.Add(succ_iv.StartExpr() >= pred_iv.EndExpr() + gap)
            
            # 제약 4: 방 용량 제약 (동시에 사용하는 그룹 수가 용량을 초과하지 않음)
            for room_name, room_data in self.room_info.items():
                capacity = room_data['capacity']
                
                # 이 방을 사용하는 모든 interval 수집
                room_intervals = []
                for (group_id, act_name, room), room_var in room_assignments.items():
                    if room == room_name and (group_id, act_name) in intervals:
                        # Optional interval 생성 (room_var가 True일 때만 활성)
                        iv = intervals[(group_id, act_name)]
                        opt_iv = model.NewOptionalIntervalVar(
                            iv.StartExpr(), 
                            self.act_info[act_name]['duration'],
                            iv.EndExpr(),
                            room_var,
                            f'opt_iv_g{group_id}_{act_name}_{room}'
                        )
                        room_intervals.append(opt_iv)
                
                # 방 용량 제약 적용
                if room_intervals:
                    # 각 그룹의 크기를 demand로 사용
                    demands = [len(self.groups[g]) for (g, _, r), _ in room_assignments.items() 
                              if r == room_name][:len(room_intervals)]
                    
                    if len(demands) == len(room_intervals):
                        model.AddCumulative(room_intervals, demands, capacity)
            
            # 제약 5: 운영 시간 제약 (모든 그룹은 같은 운영 시간 사용)
            if self.oper_hours:
                # 첫 번째 운영 시간을 기본값으로 사용
                start_time, end_time = next(iter(self.oper_hours.values()))
                
                for (group_id, act_name), iv in intervals.items():
                    model.Add(iv.StartExpr() >= start_time)
                    model.Add(iv.EndExpr() <= end_time)
            
            # 목적함수: 전체 시간 최소화 (makespan)
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
                schedule = {}
                
                for (group_id, act_name), iv in intervals.items():
                    start_min = solver.Value(iv.StartExpr())
                    end_min = solver.Value(iv.EndExpr())
                    
                    # 배정된 방 찾기
                    assigned_room = None
                    for (g, a, r), room_var in room_assignments.items():
                        if g == group_id and a == act_name and solver.Value(room_var) == 1:
                            assigned_room = r
                            break
                    
                    schedule[(group_id, act_name)] = {
                        'start': start_min,
                        'end': end_min,
                        'room': assigned_room or "미배정"
                    }
                
                # 로그 생성
                logs.append(f"Batched 활동 스케줄링 완료")
                logs.append(f"총 소요시간: {solver.Value(makespan)}분")
                
                # 그룹별 시간표 요약
                for group_id in sorted(self.groups.keys()):
                    logs.append(f"\n그룹 {group_id} 시간표:")
                    group_schedule = [(act, data) for (g, act), data in schedule.items() if g == group_id]
                    group_schedule.sort(key=lambda x: x[1]['start'])
                    
                    for act, data in group_schedule:
                        logs.append(f"  {act}: {data['start']}~{data['end']}분 @{data['room']}")
                
                status_name = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
                return schedule, status_name, "\n".join(logs)
                
            else:
                return {}, solver.StatusName(status), "Batched 활동 스케줄링 실패"
                
        except Exception as e:
            logger.error(f"Batched 스케줄링 중 오류: {e}", exc_info=True)
            return {}, "ERROR", f"오류: {str(e)}"


def convert_schedule_to_dataframe(schedule: Dict, groups: Dict[int, List[str]], 
                                 the_date: datetime) -> pd.DataFrame:
    """
    스케줄 딕셔너리를 DataFrame으로 변환
    
    Args:
        schedule: {(그룹번호, 활동명): {"start": 분, "end": 분, "room": 방}}
        groups: {그룹번호: [지원자ID 리스트]}
        the_date: 면접 날짜
        
    Returns:
        각 지원자의 활동별 시간표 DataFrame
    """
    rows = []
    base_time = pd.to_datetime(the_date.date().strftime('%Y-%m-%d') + ' 00:00:00')
    
    for (group_id, act_name), time_info in schedule.items():
        # 안전한 키 접근
        if isinstance(time_info, dict):
            start_time = time_info.get('start')
            end_time = time_info.get('end')
            room = time_info.get('room', '미배정')
            
            if start_time is not None and end_time is not None:
                # 해당 그룹의 모든 구성원에 대해 동일한 일정 생성
                for member_id in groups[group_id]:
                    rows.append({
                        'id': member_id,
                        'group_id': group_id,
                        'activity': act_name,
                        'start_time': base_time + timedelta(minutes=start_time),
                        'end_time': base_time + timedelta(minutes=end_time),
                        'room': room
                    })
            else:
                print(f"DEBUG: Missing 'start' or 'end' in time_info for group {group_id}, activity {act_name}")
                print(f"DEBUG: time_info keys: {list(time_info.keys())}")
        else:
            print(f"DEBUG: time_info is not a dict: {type(time_info)} = {time_info}")
    
    return pd.DataFrame(rows) 