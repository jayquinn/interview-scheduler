# solver/three_stage_optimizer.py
"""
3단계 계층적 면접 스케줄링 최적화 모듈
Level 1: 그룹 구성 최적화
Level 2: Batched 활동 스케줄링
Level 3: Individual/Parallel 활동 스케줄링
"""

import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple, Optional, Set, Any
from datetime import datetime, timedelta, time as dt_time
import time
from ortools.sat.python import cp_model
import string
from collections import defaultdict

class GroupOptimizer:
    """Level 1: 그룹 구성 최적화"""
    
    def __init__(self, job_acts_map: pd.DataFrame, activities: pd.DataFrame, 
                 group_min: int, group_max: int, logger):
        self.job_acts_map = job_acts_map
        self.activities = activities
        self.group_min = group_min
        self.group_max = group_max
        self.logger = logger
        
    def optimize_groups(self) -> Dict[str, Any]:
        """직무별로 최적의 그룹을 구성하고 더미 지원자를 추가"""
        self.logger.info("Level 1: 그룹 구성 최적화 시작")
        
        # batched 활동 확인
        batched_acts = self.activities[self.activities['mode'] == 'batched']
        if batched_acts.empty:
            return {'groups': {}, 'dummy_count': 0, 'all_candidates': []}
        
        groups = {}
        dummy_count = 0
        all_candidates = []
        
        # 직무별로 그룹 구성
        for _, job_row in self.job_acts_map.iterrows():
            job_code = job_row['code']
            total_count = int(job_row['count'])
            
            # 이 직무가 batched 활동을 하는지 확인
            has_batched = False
            for act in batched_acts['activity']:
                if job_row.get(act, False):
                    has_batched = True
                    break
                    
            if not has_batched:
                # batched 활동이 없으면 개별 지원자로만 처리
                for i in range(1, total_count + 1):
                    candidate_id = f"{job_code}_{str(i).zfill(3)}"
                    all_candidates.append({
                        'id': candidate_id,
                        'job_code': job_code,
                        'is_dummy': False,
                        'group_id': None
                    })
                continue
                
            self.logger.info(f"직무 {job_code}: {total_count}명 그룹 구성")
            
            # 그룹 수 최소화 알고리즘
            best_config = self._find_optimal_grouping(total_count)
            
            # 그룹 생성
            job_groups = []
            member_idx = 1
            
            for g_idx in range(best_config['groups']):
                group_id = f"{job_code}_G{g_idx + 1}"
                members = []
                
                # 마지막 그룹 처리
                if g_idx == best_config['groups'] - 1 and best_config['dummies'] > 0:
                    # 실제 남은 인원
                    remaining = total_count - (g_idx * best_config['size'])
                    
                    # 실제 인원 추가
                    for _ in range(remaining):
                        candidate_id = f"{job_code}_{str(member_idx).zfill(3)}"
                        members.append(candidate_id)
                        all_candidates.append({
                            'id': candidate_id,
                            'job_code': job_code,
                            'is_dummy': False,
                            'group_id': group_id
                        })
                        member_idx += 1
                    
                    # 더미 추가
                    for d in range(best_config['dummies']):
                        dummy_count += 1
                        dummy_id = f"DUMMY_{job_code}_{str(dummy_count).zfill(3)}"
                        members.append(dummy_id)
                        all_candidates.append({
                            'id': dummy_id,
                            'job_code': job_code,
                            'is_dummy': True,
                            'group_id': group_id
                        })
                else:
                    # 일반 그룹
                    for _ in range(best_config['size']):
                        if member_idx <= total_count:
                            candidate_id = f"{job_code}_{str(member_idx).zfill(3)}"
                            members.append(candidate_id)
                            all_candidates.append({
                                'id': candidate_id,
                                'job_code': job_code,
                                'is_dummy': False,
                                'group_id': group_id
                            })
                            member_idx += 1
                
                job_groups.append({
                    'group_id': group_id,
                    'job_code': job_code,
                    'members': members,
                    'size': len(members)
                })
                
            groups[job_code] = job_groups
            self.logger.info(f"  → {len(job_groups)}개 그룹 생성 (더미 {best_config['dummies']}명)")
            
        # batched 활동이 없는 개별 지원자들도 추가
        for _, job_row in self.job_acts_map.iterrows():
            job_code = job_row['code']
            total_count = int(job_row['count'])
            
            # 이미 그룹화된 직무는 스킵
            if job_code in groups:
                continue
                
            # 개별 지원자 추가
            for i in range(1, total_count + 1):
                candidate_id = f"{job_code}_{str(i).zfill(3)}"
                all_candidates.append({
                    'id': candidate_id,
                    'job_code': job_code,
                    'is_dummy': False,
                    'group_id': None
                })
                
        return {
            'groups': groups,
            'dummy_count': dummy_count,
            'all_candidates': all_candidates
        }
        
    def _find_optimal_grouping(self, total: int) -> Dict[str, int]:
        """주어진 인원에 대한 최적의 그룹 구성을 찾음"""
        best_groups = float('inf')
        best_config = None
        
        # 큰 사이즈부터 시도 (그룹 수 최소화)
        for size in range(self.group_max, self.group_min - 1, -1):
            full_groups = total // size
            remainder = total % size
            
            if remainder == 0:
                # 완벽한 구성
                return {'size': size, 'groups': full_groups, 'dummies': 0}
            elif remainder >= self.group_min:
                # 나머지도 그룹 구성 가능
                return {'size': size, 'groups': full_groups + 1, 'dummies': 0}
            else:
                # 더미 필요
                dummies_needed = self.group_min - remainder
                total_groups = full_groups + 1
                if total_groups < best_groups:
                    best_groups = total_groups
                    best_config = {
                        'size': size,
                        'groups': total_groups,
                        'dummies': dummies_needed
                    }
                    
        return best_config


class BatchedScheduler:
    """Level 2: Batched 활동 스케줄링"""
    
    def __init__(self, groups: Dict[str, Any], activities: pd.DataFrame, 
                 room_info: Dict, oper_hours: Dict, precedence: List,
                 global_gap: int, logger):
        self.groups = groups
        self.activities = activities
        self.room_info = room_info
        self.oper_hours = oper_hours
        self.precedence = precedence
        self.global_gap = global_gap
        self.logger = logger
        self.time_distribution_weight = 0.0  # 백트래킹 시 조정
        
    def schedule_batched(self) -> Dict[str, Any]:
        """Level 2: 모든 batched 활동을 그룹 단위로 스케줄링"""
        self.logger.info("Level 2: Batched/Parallel 활동 스케줄링 시작")
        
        all_groups = self.groups['groups']
        
        # Level 2에서 처리할 활동들 (batched + adjacent parallel)
        level2_acts = self.activities  # 이미 필터링된 상태
        batched_acts = level2_acts[level2_acts['mode'] == 'batched']
        parallel_acts = level2_acts[level2_acts['mode'] == 'parallel']
        
        self.logger.info(f"Level 2 활동: {len(batched_acts)} batched, {len(parallel_acts)} parallel")
        
        # 후속 활동 용량 분석 (adjacent 제약 체크)
        capacity_warnings = []
        
        # CP-SAT 모델 생성
        model = cp_model.CpModel()
        
        # 변수 정의
        group_vars = {}  # {group_id}_{activity}_start/end
        room_assign_vars = {}  # {job_code}_suffix_{room_type}
        interval_vars = {}  # interval variables
        
        # 방 타입별 정보 파싱
        room_types_info = self._parse_room_info()
        
        # 운영 시간 정보 추출
        if self.oper_hours:
            # oper_hours는 {job_code: (start_min, end_min)} 형태의 딕셔너리
            # 모든 직무의 운영시간이 동일하다고 가정하고 첫 번째 값 사용
            first_job = next(iter(self.oper_hours))
            start_minutes, end_minutes = self.oper_hours[first_job]
            
            # 분을 시간:분 형식으로 변환
            start_hour = start_minutes // 60
            start_min = start_minutes % 60
            end_hour = end_minutes // 60
            end_min = end_minutes % 60
        else:
            # 기본값
            start_hour, start_min = 9, 0
            end_hour, end_min = 18, 0
            start_minutes = 540  # 9*60
            end_minutes = 1080   # 18*60
        
        total_minutes = end_minutes - start_minutes
        
        # 1. 각 그룹의 활동별 시작/종료 시간 변수 생성
        for job_code, job_groups in all_groups.items():
            for group in job_groups:
                group_id = group['group_id']
                
                for _, act in level2_acts.iterrows():  # batched_acts 대신 level2_acts 사용
                    act_name = act['activity']
                    duration = int(act['duration_min'])
                    mode = act.get('mode', 'individual')
                    
                    # Parallel 활동은 개인별로 처리되므로 그룹 멤버별로 변수 생성
                    if mode == 'parallel':
                        # 그룹의 각 멤버에 대해 변수 생성 (더미 포함)
                        for member_id in group['members']:
                                
                            # 멤버별 시작/종료 시간 변수
                            start_var = model.NewIntVar(0, total_minutes - duration, 
                                                      f"{member_id}_{act_name}_start")
                            end_var = model.NewIntVar(duration, total_minutes, 
                                                    f"{member_id}_{act_name}_end")
                            
                            group_vars[f"{member_id}_{act_name}_start"] = start_var
                            group_vars[f"{member_id}_{act_name}_end"] = end_var
                            
                            # duration 제약
                            model.Add(end_var == start_var + duration)
                            
                            # Interval 변수 생성
                            interval = model.NewIntervalVar(start_var, duration, end_var, 
                                                          f"{member_id}_{act_name}_interval")
                            interval_vars[f"{member_id}_{act_name}"] = interval
                    else:
                        # Batched 활동은 그룹 단위로 처리
                        # 시작/종료 시간 변수
                        start_var = model.NewIntVar(0, total_minutes - duration, 
                                                  f"{group_id}_{act_name}_start")
                        end_var = model.NewIntVar(duration, total_minutes, 
                                                f"{group_id}_{act_name}_end")
                        
                        group_vars[f"{group_id}_{act_name}_start"] = start_var
                        group_vars[f"{group_id}_{act_name}_end"] = end_var
                        
                        # duration 제약
                        model.Add(end_var == start_var + duration)
                        
                        # Interval 변수 생성
                        interval = model.NewIntervalVar(start_var, duration, end_var, 
                                                      f"{group_id}_{act_name}_interval")
                        interval_vars[f"{group_id}_{act_name}"] = interval
        
        # 2. 방 접미사 할당 변수 (같은 직무는 같은 접미사 사용)
        job_codes = sorted(all_groups.keys())
        for idx, job_code in enumerate(job_codes):
            for room_type, suffixes in room_types_info.items():
                if len(suffixes) > 1:
                    # 이 직무가 사용할 접미사 인덱스 (0부터 시작)
                    suffix_var = model.NewIntVar(0, len(suffixes)-1, 
                                               f"{job_code}_suffix_{room_type}")
                    room_assign_vars[f"{job_code}_suffix_{room_type}"] = suffix_var
                    
                    # 직무별로 A(0) 또는 B(1)를 번갈아 할당
                    # JOB01→A(0), JOB02→B(1), JOB03→A(0), JOB04→B(1), ...
                    model.Add(suffix_var == idx % len(suffixes))
        
        # 3. 제약 조건 추가
        self._add_constraints(model, group_vars, room_assign_vars, 
                            [g for groups in all_groups.values() for g in groups],
                            level2_acts, interval_vars, room_types_info)
        
        # 4. 최적화 목표: 전체 완료 시간 최소화
        all_end_times = []
        for var_name, var in group_vars.items():
            if var_name.endswith('_end'):
                all_end_times.append(var)
        
        if all_end_times:
            max_end_time = model.NewIntVar(0, total_minutes, "max_end_time")
            model.AddMaxEquality(max_end_time, all_end_times)
            model.Minimize(max_end_time)
        
        # 5. 솔버 실행
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        status = solver.Solve(model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            # 스케줄 추출
            schedule = {}
            room_assignments = {}
            
            for job_code, job_groups in all_groups.items():
                for group in job_groups:
                    group_id = group['group_id']
                    schedule[group_id] = {}
                    
                    for _, act in level2_acts.iterrows():  # batched_acts 대신 level2_acts 사용
                        act_name = act['activity']
                        room_type = act['room_type']
                        mode = act.get('mode', 'individual')
                        
                        if mode == 'parallel':
                            # Parallel 활동은 멤버별로 스케줄 생성
                            for member_id in group['members']:
                                if member_id not in schedule:
                                    schedule[member_id] = {}
                                
                                start_time = solver.Value(group_vars[f"{member_id}_{act_name}_start"])
                                end_time = solver.Value(group_vars[f"{member_id}_{act_name}_end"])
                                
                                # 방 할당 (parallel은 같은 방을 공유할 수 있음)
                                suffixes = room_types_info.get(room_type, [''])
                                
                                # Parallel 활동도 균등하게 방 배분
                                if len(suffixes) > 1:
                                    # 같은 직무의 그룹은 같은 방을 사용
                                    job_code = group['job_code']
                                    suffix_var_name = f"{job_code}_suffix_{room_type}"
                                    if suffix_var_name in room_assign_vars:
                                        suffix_idx = solver.Value(room_assign_vars[suffix_var_name])
                                        suffix = suffixes[suffix_idx]
                                    else:
                                        # 직무 코드에 따라 라운드로빈 할당
                                        job_codes = sorted(all_groups.keys())
                                        job_idx = job_codes.index(job_code)
                                        suffix_idx = job_idx % len(suffixes)
                                        suffix = suffixes[suffix_idx]
                                else:
                                    suffix = suffixes[0] if suffixes else ''
                                
                                room_name = f"{room_type}{suffix}"
                                
                                schedule[member_id][act_name] = {
                                    'start': start_time,
                                    'end': end_time,
                                    'room': room_name
                                }
                        else:
                            # Batched 활동은 그룹 단위로 스케줄
                            start_time = solver.Value(group_vars[f"{group_id}_{act_name}_start"])
                            end_time = solver.Value(group_vars[f"{group_id}_{act_name}_end"])
                            
                            # 방 접미사 결정
                            suffixes = room_types_info.get(room_type, [''])
                            if len(suffixes) > 1 and f"{job_code}_suffix_{room_type}" in room_assign_vars:
                                suffix_idx = solver.Value(room_assign_vars[f"{job_code}_suffix_{room_type}"])
                                suffix = suffixes[suffix_idx]
                            else:
                                suffix = suffixes[0] if suffixes else ''
                            
                            room_name = f"{room_type}{suffix}"
                            
                            schedule[group_id][act_name] = {
                                'start': start_time,
                                'end': end_time,
                                'room': room_name
                            }
                        
                        if group_id not in room_assignments:
                            room_assignments[group_id] = {}
                        room_assignments[group_id][room_type] = suffix
            
            self.logger.info(f"Level 2 완료: {len(schedule)}개 그룹 스케줄링 성공")
            
            return {
                'schedule': schedule,
                'room_assignments': room_assignments
            }
        
        else:
            self.logger.error(f"Level 2 실패: CP-SAT status = {solver.StatusName(status)}")
            return None
            
    def _parse_room_info(self) -> Dict[str, List[str]]:
        """방 정보를 타입별로 파싱 - 알파벳 접미사 우선"""
        room_types_info = defaultdict(list)
        
        for room_name in self.room_info.keys():
            # 방 이름에서 타입과 접미사 분리
            # 입력 형태: "토론면접실A", "토론면접실B" 또는 "토론면접실"
            
            # 뒤에서부터 단일 대문자 알파벳 찾기
            if room_name and room_name[-1].isupper() and len(room_name) > 1:
                # 마지막 문자가 대문자 알파벳인 경우
                base_name = room_name[:-1]
                suffix = room_name[-1]
            else:
                # 접미사가 없는 경우
                base_name = room_name
                suffix = ''
            
            # 접미사가 있으면 그대로 사용, 없으면 빈 문자열
            room_types_info[base_name].append(suffix)
            
        # 각 타입별로 접미사 정렬
        for room_type in room_types_info:
            suffixes = room_types_info[room_type]
            # 빈 문자열 제거하고 정렬
            suffixes = [s for s in suffixes if s]
            if not suffixes:
                # 접미사가 없는 단일 방인 경우
                room_types_info[room_type] = ['']
            else:
                room_types_info[room_type] = sorted(suffixes)
            
        return dict(room_types_info)
        
    def _add_constraints(self, model, group_vars, room_assign_vars, 
                        all_groups, batched_acts, interval_vars, room_types_info):
        """CP-SAT 모델에 제약 조건 추가"""
        
        # 활동들을 batched와 parallel로 분류
        level2_acts = self.activities  # 이미 필터링된 상태
        batched_activities = level2_acts[level2_acts['mode'] == 'batched']
        parallel_activities = level2_acts[level2_acts['mode'] == 'parallel']
        
        # 1. 같은 직무의 모든 그룹은 같은 접미사 사용 (이미 직무 인덱스로 고정됨)
        
        # 2. Precedence 제약 (선후행 관계)
        for group in all_groups:
            group_id = group['group_id']
            
            for prec_rule in self.precedence:
                if len(prec_rule) >= 3:
                    pred, succ, gap = prec_rule[0], prec_rule[1], prec_rule[2] if len(prec_rule) > 2 else self.global_gap
                    is_adjacent = prec_rule[3] if len(prec_rule) > 3 else False
                else:
                    continue
                    
                if pred == "__START__" or succ == "__END__":
                    continue  # Level 2에서는 처리하지 않음
                    
                # 두 활동이 모두 Level 2에 있는지 확인
                pred_in_level2 = any(level2_acts['activity'] == pred)
                succ_in_level2 = any(level2_acts['activity'] == succ)
                
                if pred_in_level2 and succ_in_level2:
                    # 활동 모드 확인
                    pred_mode = level2_acts[level2_acts['activity'] == pred].iloc[0]['mode'] if pred_in_level2 else None
                    succ_mode = level2_acts[level2_acts['activity'] == succ].iloc[0]['mode'] if succ_in_level2 else None
                    
                    if pred_mode == 'batched' and succ_mode == 'parallel' and is_adjacent:
                        # Batched → Parallel adjacent: 그룹의 모든 멤버가 동시에 시작
                        batched_var = group_vars.get(f"{group_id}_{pred}_start")
                        batched_duration = int(batched_activities[batched_activities['activity'] == pred].iloc[0]['duration_min'])
                        
                        if batched_var:
                            for member_id in group['members']:
                                parallel_var = group_vars.get(f"{member_id}_{succ}_start")
                                if parallel_var:
                                    # 모든 멤버가 batched 활동 종료 후 즉시 parallel 시작
                                    model.Add(parallel_var == batched_var + batched_duration + gap)
                    
                    elif pred_mode == 'parallel' and succ_mode == 'parallel':
                        # Parallel → Parallel: 개인별 제약
                        for member_id in group['members']:
                            pred_var = group_vars.get(f"{member_id}_{pred}_start")
                            succ_var = group_vars.get(f"{member_id}_{succ}_start")
                            
                            if pred_var and succ_var:
                                pred_duration = int(parallel_activities[parallel_activities['activity'] == pred].iloc[0]['duration_min'])
                                if is_adjacent:
                                    model.Add(succ_var == pred_var + pred_duration + gap)
                                else:
                                    model.Add(succ_var >= pred_var + pred_duration + gap)
                    
                    elif pred_mode == 'batched' and succ_mode == 'batched':
                        # Batched → Batched: 그룹 단위 제약
                        pred_var = group_vars.get(f"{group_id}_{pred}_start")
                        succ_var = group_vars.get(f"{group_id}_{succ}_start")
                        
                        if pred_var and succ_var:
                            pred_duration = int(batched_activities[batched_activities['activity'] == pred].iloc[0]['duration_min'])
                            if is_adjacent:
                                model.Add(succ_var == pred_var + pred_duration + gap)
                            else:
                                model.Add(succ_var >= pred_var + pred_duration + gap)
                
                # Parallel → Individual adjacent는 Level 3에서 처리
                # 하지만 Level 2에서 미리 parallel 활동의 종료 시간을 제약할 수 있음
                elif pred_in_level2 and not succ_in_level2:
                    # Level 2 활동 → Level 3 활동 연결
                    if is_adjacent and pred_mode == 'parallel':
                        # Parallel 활동들이 동일 시간에 끝나도록 제약
                        member_end_times = []
                        for member_id in group['members']:
                            pred_var = group_vars.get(f"{member_id}_{pred}_start")
                            if pred_var:
                                pred_duration = int(parallel_activities[parallel_activities['activity'] == pred].iloc[0]['duration_min'])
                                end_time = pred_var + pred_duration
                                member_end_times.append(end_time)
                        
                        # 모든 멤버가 동시에 끝나도록
                        if len(member_end_times) > 1:
                            for i in range(1, len(member_end_times)):
                                model.Add(member_end_times[i] == member_end_times[0])

        # 3. 방 용량 제약 - 같은 방에서 시간이 겹치지 않도록
        # 개별 방별로 interval 수집 (A와 B를 구분)
        room_intervals_by_suffix = defaultdict(lambda: defaultdict(list))
        
        # 각 그룹/활동에 대한 방 할당을 추적
        room_assignments_tracking = {}
        
        for room_type, suffixes in room_types_info.items():
            # Batched 활동의 interval과 방 할당
            for job_code, job_groups in all_groups.items():
                for group in job_groups:
                    for _, act in batched_activities.iterrows():
                        if act['room_type'] == room_type:
                            interval_key = f"{group['group_id']}_{act['activity']}"
                            if interval_key in interval_vars:
                                # 이 그룹이 사용할 접미사
                                if len(suffixes) > 1 and f"{job_code}_suffix_{room_type}" in room_assign_vars:
                                    suffix_var = room_assign_vars[f"{job_code}_suffix_{room_type}"]
                                    # 각 접미사별로 interval 추가
                                    for idx, suffix in enumerate(suffixes):
                                        # 이 접미사를 사용하는 경우의 interval
                                        is_using_suffix = model.NewBoolVar(f"{interval_key}_uses_{suffix}")
                                        model.Add(suffix_var == idx).OnlyEnforceIf(is_using_suffix)
                                        model.Add(suffix_var != idx).OnlyEnforceIf(is_using_suffix.Not())
                                        
                                        # Optional interval 생성
                                        opt_interval = model.NewOptionalIntervalVar(
                                            interval_vars[interval_key].StartExpr(),
                                            interval_vars[interval_key].SizeExpr(),
                                            interval_vars[interval_key].EndExpr(),
                                            is_using_suffix,
                                            f"{interval_key}_opt_{suffix}"
                                        )
                                        room_intervals_by_suffix[room_type][suffix].append(opt_interval)
                                else:
                                    # 단일 방인 경우
                                    suffix = suffixes[0] if suffixes else ''
                                    room_intervals_by_suffix[room_type][suffix].append(interval_vars[interval_key])
            
            # Parallel 활동의 interval (각 멤버 포함)
            for group in all_groups:
                for member_id in group['members']:
                    for _, act in parallel_activities.iterrows():
                        if act['room_type'] == room_type:
                            interval_key = f"{member_id}_{act['activity']}"
                            if interval_key in interval_vars:
                                suffix = suffixes[0] if suffixes else ''
                                room_intervals_by_suffix[room_type][suffix].append(interval_vars[interval_key])
        
        # 각 개별 방별로 용량 제약 추가
        for room_type, suffix_intervals in room_intervals_by_suffix.items():
            for suffix, intervals in suffix_intervals.items():
                if intervals:
                    # 특정 방의 용량 가져오기
                    room_name = f"{room_type}{suffix}"
                    room_capacity = self.room_info.get(room_name, {}).get('capacity', 1)
                    
                    # 이 특정 방에 대한 Cumulative 제약
                    model.AddCumulative(intervals, [1] * len(intervals), room_capacity)
        
        # 방 할당은 이미 직무 인덱스에 따라 A/B를 번갈아 사용하도록 설정됨


class IndividualScheduler:
    """Level 3: Individual/Parallel 활동 스케줄링"""
    
    def __init__(self, groups_result: Dict, batched_schedule: Dict,
                 activities: pd.DataFrame, job_acts_map: pd.DataFrame,
                 room_info: Dict, oper_hours: Dict, precedence: List, 
                 global_gap: int, max_stay_hours: int, logger):
        self.groups_result = groups_result
        self.batched_schedule = batched_schedule
        self.activities = activities
        self.job_acts_map = job_acts_map
        self.room_info = room_info
        self.oper_hours = oper_hours
        self.precedence = precedence
        self.global_gap = global_gap
        self.max_stay_hours = max_stay_hours
        self.logger = logger
        
    def schedule_individual(self, the_date: pd.Timestamp) -> pd.DataFrame:
        """Individual/Parallel 활동을 고정된 batched 시간을 고려하여 스케줄링"""
        self.logger.info("Level 3: Individual/Parallel 활동 스케줄링 시작")
        
        # Level 2에서 처리된 활동들 확인
        level2_activities = set()
        if 'schedule' in self.batched_schedule:
            for entity_id, activities in self.batched_schedule['schedule'].items():
                for act_name in activities.keys():
                    level2_activities.add(act_name)
        
        # Level 3에서 처리할 활동만 필터링 (Level 2에서 처리되지 않은 활동들)
        all_activities = self.activities.copy()
        individual_acts = all_activities[
            (all_activities['mode'].isin(['individual', 'parallel'])) & 
            (~all_activities['activity'].isin(level2_activities))
        ]
        
        # Level 2에서 처리된 활동들
        batched_acts = all_activities[all_activities['activity'].isin(level2_activities)]
        
        self.logger.info(f"Level 3 활동: {len(individual_acts)}개 (Level 2에서 {len(batched_acts)}개 처리됨)")
        
        # Individual 활동이 없으면 빈 DataFrame 반환 (batched는 이미 Level 2에서 처리됨)
        if individual_acts.empty:
            self.logger.info("Individual/Parallel 활동이 없습니다. Level 3 스킵")
            return pd.DataFrame()
            
        # 모든 지원자 정보 준비
        all_candidates = self.groups_result['all_candidates']
        
        # 기존 build_model을 위한 데이터 구조 준비
        candidate_info = {}
        for cand in all_candidates:
            cand_id = cand['id']
            job_code = cand['job_code']
            
            # 이 지원자가 해야 할 활동들
            activities_list = []
            
            # job_acts_map에서 이 직무가 실제로 하는 활동만 추가
            job_row = self.job_acts_map[self.job_acts_map['code'] == job_code]
            if not job_row.empty:
                job_row = job_row.iloc[0]
                
                # Individual/Parallel 활동만 추가 (batched는 이미 Level 2에서 처리됨)
                for _, act in individual_acts.iterrows():
                    act_name = act['activity']
                    if act_name in job_row and job_row[act_name]:
                        activities_list.append(act_name)
                        
                # Batched 활동은 Level 3에서 제외
                # (이미 Level 2에서 스케줄링 완료)
                
            candidate_info[cand_id] = {
                'job_code': job_code,
                'activities': activities_list
            }
            
        # 활동 정보
        act_info = {}
        for _, act in self.activities.iterrows():
            act_info[act['activity']] = {
                'duration': int(act['duration_min']),
                'min_ppl': int(act.get('min_cap', 1)),
                'max_ppl': int(act.get('max_cap', 1)),
                'required_rooms': [act['room_type']]
            }
            
        # CP-SAT 모델로 스케줄링
        from interview_opt_test_v4 import build_model
        
        # Batched 스케줄을 고정 제약으로 변환
        fixed_schedule = {}
        if self.batched_schedule and 'schedule' in self.batched_schedule:
            # 날짜의 기준 시간 (00:00)
            base_time = datetime.combine(the_date.date(), dt_time(0, 0))
            
            for group_id, activities in self.batched_schedule['schedule'].items():
                # 그룹 정보 찾기
                group_info = None
                for job_groups in self.groups_result['groups'].values():
                    for g in job_groups:
                        if g['group_id'] == group_id:
                            group_info = g
                            break
                    if group_info:
                        break
                
                if group_info:
                    # 각 멤버의 batched 활동을 고정 스케줄로 추가
                    for member_id in group_info['members']:
                        if member_id not in fixed_schedule:
                            fixed_schedule[member_id] = {}
                            
                        for act_name, timing in activities.items():
                            fixed_schedule[member_id][act_name] = {
                                'start': timing['start'],
                                'end': timing['end'],
                                'room': timing['room']
                            }
        
        # Level 3용 precedence 필터링
        # batched 활동과 관련된 제약은 제거하고, individual 활동 간의 제약만 유지
        filtered_precedence = []
        batched_act_names = set(batched_acts['activity'].tolist())
        individual_act_names = set(individual_acts['activity'].tolist())
        parallel_act_names = set(self.activities[self.activities['mode'] == 'parallel']['activity'].tolist())
        
        # Adjacent 제약이 있는 parallel → individual 전환 확인
        has_parallel_to_individual_adjacent = False
        parallel_to_individual_rules = []
        
        for rule in self.precedence:
            pred = rule[0]
            succ = rule[1]
            is_adjacent = rule[3] if len(rule) > 3 else False
            
            # parallel → individual adjacent 제약 감지
            if (pred in parallel_act_names and succ in individual_act_names and is_adjacent):
                has_parallel_to_individual_adjacent = True
                self.logger.warning(f"감지: {pred}(parallel) → {succ}(individual) adjacent 제약")
                # 이 제약은 특별 처리를 위해 저장
                parallel_to_individual_rules.append(rule)
                # filtered_precedence에는 추가하지 않음 (나중에 다르게 처리)
            # __START__/__END__와 individual 활동 간의 제약 처리
            elif pred == "__START__":
                # __START__ → individual 활동: batched 활동 이후로 조정
                if succ in individual_act_names:
                    # batched 활동들의 최대 종료 시간 이후에 시작하도록
                    # 이는 fixed_schedule을 통해 암묵적으로 처리됨
                    continue
            elif succ == "__END__":
                # individual 활동 → __END__: 유지
                if pred in individual_act_names:
                    filtered_precedence.append(rule)
            else:
                # 둘 다 individual/parallel 활동인 경우만 유지
                if (pred in individual_act_names or pred in parallel_act_names) and \
                   (succ in individual_act_names or succ in parallel_act_names):
                    # parallel → individual adjacent는 이미 처리했으므로 제외
                    if not (pred in parallel_act_names and succ in individual_act_names and is_adjacent):
                        filtered_precedence.append(rule)
                # batched → individual 또는 individual → batched는 
                # fixed_schedule과 시간 제약으로 처리
        
        # 특별 처리: parallel → individual adjacent 제약이 있는 경우
        if has_parallel_to_individual_adjacent:
            self.logger.info("Parallel → Individual adjacent 제약에 대한 특별 처리 모드 활성화")
            
            # 그룹별로 parallel 활동의 최대 종료 시간을 계산하여 
            # individual 활동의 최소 시작 시간으로 설정
            group_parallel_end_times = {}
            
            # fixed_schedule에서 그룹별 정보 추출
            for member_id, activities in fixed_schedule.items():
                # 그룹 찾기
                group_id = None
                for job_groups in self.groups_result['groups'].values():
                    for g in job_groups:
                        if member_id in g['members']:
                            group_id = g['group_id']
                            break
                    if group_id:
                        break
                
                if group_id:
                    for act_name, timing in activities.items():
                        # parallel 활동인지 확인
                        act_info = self.activities[self.activities['activity'] == act_name]
                        if not act_info.empty and act_info.iloc[0].get('mode') == 'parallel':
                            # 이 그룹의 parallel 활동 종료 시간 업데이트
                            if group_id not in group_parallel_end_times:
                                group_parallel_end_times[group_id] = {}
                            if act_name not in group_parallel_end_times[group_id]:
                                group_parallel_end_times[group_id][act_name] = timing['end']
                            else:
                                # 같은 그룹의 최대 종료 시간 유지
                                group_parallel_end_times[group_id][act_name] = max(
                                    group_parallel_end_times[group_id][act_name], 
                                    timing['end']
                                )
            
            # 그룹별 최대 parallel 종료 시간을 fixed_schedule에 추가 제약으로 반영
            # (이미 fixed_schedule에 있는 것은 제외)
            for member_id in candidate_info.keys():
                # 그룹 찾기
                group_id = None
                for job_groups in self.groups_result['groups'].values():
                    for g in job_groups:
                        if member_id in g['members']:
                            group_id = g['group_id']
                            break
                    if group_id:
                        break
                
                if group_id and group_id in group_parallel_end_times:
                    # 이 멤버의 individual 활동에 대한 최소 시작 시간 제약 추가
                    for p_rule in parallel_to_individual_rules:
                        pred_act = p_rule[0]  # parallel
                        succ_act = p_rule[1]  # individual
                        
                        if pred_act in group_parallel_end_times[group_id]:
                            max_end_time = group_parallel_end_times[group_id][pred_act]
                            
                            # config에 추가 제약 정보 전달
                            if 'group_constraints' not in config:
                                config['group_constraints'] = {}
                            if member_id not in config['group_constraints']:
                                config['group_constraints'][member_id] = {}
                            
                            # individual 활동은 그룹의 모든 parallel이 끝난 후에 시작
                            config['group_constraints'][member_id][succ_act] = {
                                'min_start': max_end_time + p_rule[2]  # gap 추가
                            }
        
        config = {
            'the_date': the_date,
            'act_info': act_info,
            'candidate_info': candidate_info,
            'room_info': self.room_info,
            'oper_hours': self.oper_hours,
            'rules': filtered_precedence,  # 필터링된 precedence 사용
            'min_gap_min': self.global_gap,
            'time_limit_sec': 60.0,
            'num_cpus': 8,
            'fixed_schedule': fixed_schedule  # 고정된 batched 스케줄 전달
        }
        
        model, status, result_df, logs = build_model(config, self.logger)
        
        if status in ['OPTIMAL', 'FEASIBLE'] and result_df is not None:
            self.logger.info(f"Level 3 완료: {len(result_df)}명 스케줄링 성공")
            return result_df
        else:
            self.logger.error("Level 3 실패: Individual 활동 스케줄링 불가")
            return None


def _check_stay_duration(schedule_df: pd.DataFrame, max_stay_hours: int, 
                        logger) -> Tuple[bool, List[str]]:
    """각 지원자의 체류시간이 최대 체류시간을 초과하는지 검증"""
    violations = []
    
    if schedule_df.empty:
        return True, violations
        
    # 각 지원자별로 체류시간 계산
    for candidate_id, cand_schedule in schedule_df.groupby('id'):
            
        # 시작 시간과 종료 시간 계산
        # 컬럼명이 다를 수 있으므로 체크
        start_col = 'start' if 'start' in cand_schedule.columns else 'start_time'
        end_col = 'end' if 'end' in cand_schedule.columns else 'end_time'
        
        start_times = pd.to_datetime(cand_schedule[start_col])
        end_times = pd.to_datetime(cand_schedule[end_col])
        
        if len(start_times) == 0:
            continue
            
        first_start = start_times.min()
        last_end = end_times.max()
        
        # 체류시간 계산 (시간 단위)
        stay_duration_hours = (last_end - first_start).total_seconds() / 3600
        
        if stay_duration_hours > max_stay_hours:
            violations.append(
                f"{candidate_id}: {stay_duration_hours:.1f}시간 "
                f"(최대 {max_stay_hours}시간 초과)"
            )
            
    if violations:
        logger.warning(f"체류시간 위반 {len(violations)}건 발생")
        for v in violations[:5]:  # 최대 5개만 표시
            logger.warning(f"  - {v}")
        if len(violations) > 5:
            logger.warning(f"  ... 외 {len(violations)-5}건")
            
    return len(violations) == 0, violations


def _combine_schedules(batched_result: Dict, individual_schedule: pd.DataFrame,
                      groups_result: Dict, the_date: pd.Timestamp) -> pd.DataFrame:
    """Level 2 batched 결과와 Level 3 individual 결과를 통합"""
    
    # Individual 스케줄이 없으면 빈 DataFrame
    if individual_schedule is None or individual_schedule.empty:
        individual_schedule = pd.DataFrame()
    
    # Batched 스케줄을 DataFrame으로 변환
    batched_rows = []
    if batched_result and 'schedule' in batched_result:
        for entity_id, activities in batched_result['schedule'].items():
            # entity_id가 그룹 ID인지 개인 ID인지 확인
            is_group_id = entity_id.startswith('group_')
            
            if is_group_id:
                # 그룹 정보 찾기
                group_info = None
                for job_groups in groups_result['groups'].values():
                    for g in job_groups:
                        if g['group_id'] == entity_id:
                            group_info = g
                            break
                    if group_info:
                        break
                        
                if group_info:
                    # 각 멤버의 batched 활동 추가 (더미 포함)
                    for member_id in group_info['members']:
                            
                        job_code = group_info['job_code']
                        
                        for act_name, timing in activities.items():
                            # 시간을 datetime으로 변환 
                            # timing['start']와 timing['end']는 하루의 시작(00:00)부터의 분 단위
                            base_time = datetime.combine(the_date.date(), dt_time(0, 0))
                            start_time = base_time + timedelta(minutes=timing['start'])
                            end_time = base_time + timedelta(minutes=timing['end'])
                            
                            batched_rows.append({
                                'id': member_id,
                                'activity': act_name,
                                'start_time': start_time,
                                'end_time': end_time,
                                'room': timing['room'],
                                'job_code': job_code,
                                'interview_date': the_date
                            })
            else:
                # 개인별 스케줄 (parallel 활동)
                # 직무 코드 찾기
                job_code = None
                for job_groups in groups_result['groups'].values():
                    for g in job_groups:
                        if entity_id in g['members']:
                            job_code = g['job_code']
                            break
                    if job_code:
                        break
                
                if job_code:
                    for act_name, timing in activities.items():
                        base_time = datetime.combine(the_date.date(), dt_time(0, 0))
                        start_time = base_time + timedelta(minutes=timing['start'])
                        end_time = base_time + timedelta(minutes=timing['end'])
                        
                        batched_rows.append({
                            'id': entity_id,
                            'activity': act_name,
                            'start_time': start_time,
                            'end_time': end_time,
                            'room': timing['room'],
                            'job_code': job_code,
                            'interview_date': the_date
                        })
    
    batched_df = pd.DataFrame(batched_rows)
    
    # Individual과 Batched 결과 병합
    if not batched_df.empty and not individual_schedule.empty:
        combined = pd.concat([individual_schedule, batched_df], ignore_index=True)
    elif not batched_df.empty:
        combined = batched_df
    else:
        combined = individual_schedule
    
    # 빈 DataFrame이면 그대로 반환
    if combined.empty:
        return combined
        
    # 컬럼명 정규화 (solver.py와 일관성 유지)
    # interview_opt_test_v4.py의 long format과 호환되도록
    if 'start_time' in combined.columns:
        combined['start'] = combined['start_time']
    if 'end_time' in combined.columns:
        combined['end'] = combined['end_time']
    if 'room' in combined.columns:
        combined['loc'] = combined['room']
    if 'job_code' not in combined.columns and 'code' in combined.columns:
        combined['job_code'] = combined['code']
        
    # 필수 컬럼만 유지
    required_cols = ['id', 'activity', 'start', 'end', 'loc', 'job_code', 'interview_date']
    available_cols = [col for col in required_cols if col in combined.columns]
    
    return combined[available_cols]


def _handle_partial_results(groups_result: Dict, batched_result: Dict, 
                          the_date: pd.Timestamp, logs: List[str]) -> pd.DataFrame:
    """Level 2나 3이 실패했을 때 부분 결과를 처리"""
    partial_rows = []
    
    if batched_result and 'schedule' in batched_result:
        # Level 2 결과만이라도 사용
        for entity_id, activities in batched_result['schedule'].items():
            if entity_id.startswith('group_'):
                # 그룹 정보 찾기
                group_info = None
                for job_groups in groups_result['groups'].values():
                    for g in job_groups:
                        if g['group_id'] == entity_id:
                            group_info = g
                            break
                    if group_info:
                        break
                
                if group_info:
                    for member_id in group_info['members']:
                        for act_name, timing in activities.items():
                            base_time = datetime.combine(the_date.date(), dt_time(0, 0))
                            start_time = base_time + timedelta(minutes=timing['start'])
                            end_time = base_time + timedelta(minutes=timing['end'])
                            
                            partial_rows.append({
                                'id': member_id,
                                'activity': act_name,
                                'start': start_time,
                                'end': end_time,
                                'loc': timing['room'],
                                'job_code': group_info['job_code'],
                                'interview_date': the_date
                            })
    
    if partial_rows:
        logs.append(f"부분 결과 활용: {len(partial_rows)}개 활동 스케줄")
        return pd.DataFrame(partial_rows)
    
    return pd.DataFrame()


def solve_with_three_stages(cfg_ui: dict, params: dict, 
                           the_date: pd.Timestamp, candidates_for_day: pd.DataFrame,
                           debug: bool = False) -> Tuple[str, Optional[pd.DataFrame], List[str], Optional[Dict]]:
    """3단계 계층적 최적화를 수행"""
    logger = st.logger.get_logger("three_stage")
    logs = []
    
    # 그룹 정보를 항상 추적
    group_info_for_ui = {
        'member_to_group': {},  
        'group_sizes': {}       
    }
    
    try:
        # 데이터 준비
        activities = cfg_ui['activities']
        job_acts_map = cfg_ui['job_acts_map']
        
        # batched 활동 확인
        batched_acts = activities[activities['mode'] == 'batched']
        if batched_acts.empty:
            logs.append("batched 활동이 없어 3단계 최적화가 필요없습니다.")
            return "NO_BATCHED", None, logs, None
            
        # parallel 활동도 함께 확인 (batched와 adjacent한 경우 Level 2에서 함께 처리)
        parallel_acts = activities[activities['mode'] == 'parallel']
        precedence_df = cfg_ui.get('precedence', pd.DataFrame())
        
        # Batched → Parallel adjacent 체인 확인
        level2_activities = batched_acts.copy()
        if not precedence_df.empty and 'adjacent' in precedence_df.columns:
            for _, rule in precedence_df.iterrows():
                if rule.get('adjacent', False):
                    pred = rule['predecessor']
                    succ = rule['successor']
                    
                    # Batched → Parallel adjacent인 경우
                    pred_act = activities[activities['activity'] == pred]
                    succ_act = activities[activities['activity'] == succ]
                    
                    if not pred_act.empty and not succ_act.empty:
                        pred_mode = pred_act.iloc[0].get('mode', 'individual')
                        succ_mode = succ_act.iloc[0].get('mode', 'individual')
                        
                        if pred_mode == 'batched' and succ_mode == 'parallel':
                            # Parallel 활동도 Level 2에서 함께 처리
                            level2_activities = pd.concat([level2_activities, succ_act], ignore_index=True)
                            logs.append(f"Adjacent 체인 감지: {pred} → {succ}, Level 2에서 함께 처리")
        
        # 그룹 크기 가져오기
        group_min = int(batched_acts.iloc[0]['min_cap'])
        group_max = int(batched_acts.iloc[0]['max_cap'])
        
        # 제약 조건 타당성 검사
        # Batched → Individual/Parallel adjacent 제약 확인
        room_plan = cfg_ui.get('room_plan', pd.DataFrame())
        precedence_df = cfg_ui.get('precedence', pd.DataFrame())
        if not precedence_df.empty and 'adjacent' in precedence_df.columns:
            for _, rule in precedence_df.iterrows():
                if not rule.get('adjacent', False):
                    continue
                    
                pred = rule['predecessor']
                succ = rule['successor']
                
                # 선행 활동과 후행 활동의 모드 확인
                pred_act = activities[activities['activity'] == pred]
                succ_act = activities[activities['activity'] == succ]
                
                if pred_act.empty or succ_act.empty:
                    continue
                    
                pred_mode = pred_act.iloc[0].get('mode', 'individual')
                succ_mode = succ_act.iloc[0].get('mode', 'individual')
                
                # Batched/Parallel → Individual adjacent 제약 검사
                if pred_mode in ['batched', 'parallel'] and succ_mode == 'individual':
                    pred_cap = int(pred_act.iloc[0].get('max_cap', 1))
                    succ_room_type = succ_act.iloc[0]['room_type']
                    succ_room_count = 0
                    
                    if room_plan is not None and not room_plan.empty:
                        count_col = f"{succ_room_type}_count"
                        if count_col in room_plan.columns:
                            succ_room_count = int(room_plan[count_col].iloc[0])
                    
                    # 그룹 크기나 parallel 용량이 individual 방 수보다 크면 adjacent 불가능
                    effective_cap = group_max if pred_mode == 'batched' else pred_cap
                    
                    if effective_cap > succ_room_count:
                        error_msg = (
                            f"⚠️ 구조적 문제 감지: {pred}({pred_mode}, {effective_cap}명) → "
                            f"{succ}(individual, {succ_room_count}개 방) adjacent 제약은 불가능합니다.\n"
                            f"   이유: {effective_cap}명이 동시에 {pred}을 마치고 {succ}으로 가야 하는데, "
                            f"{succ}은 {succ_room_count}명만 동시 수용 가능합니다.\n"
                            f"   해결책: 1) adjacent를 false로 변경, 2) {succ} 방을 {effective_cap}개로 증설, "
                            f"3) 그룹 크기를 {succ_room_count}명으로 축소"
                        )
                        logs.append(error_msg)
                        logger.warning(error_msg)
                        # 계속 진행하되 실패할 가능성이 높음을 경고
        
        logs.append(f"=== 3단계 최적화 시작 (날짜: {the_date.date()}) ===")
        logs.append(f"그룹 크기: {group_min}~{group_max}명")
        
        # Level 1: 그룹 구성
        try:
            logs.append("Level 1 시작: 그룹 구성 최적화")
            group_optimizer = GroupOptimizer(job_acts_map, activities, group_min, group_max, logger)
            groups_result = group_optimizer.optimize_groups()
        except Exception as e:
            logs.append(f"Level 1 오류: {str(e)}")
            raise
        
        if not groups_result['groups']:
            logs.append("Level 1 실패: 그룹 구성 불가")
            return "LEVEL1_FAIL", None, logs, None
            
        # 그룹 구성 상세 정보 로깅
        total_groups = sum(len(g) for g in groups_result['groups'].values())
        logs.append(f"Level 1 완료: {total_groups}개 그룹 생성")
        
        # 그룹 정보를 즉시 UI용으로 변환 (에러가 발생해도 이 정보는 유지)
        group_number = 1
        for job_code, job_groups in groups_result['groups'].items():
            logs.append(f"  - {job_code}: {len(job_groups)}개 그룹")
            for i, group in enumerate(job_groups):
                real_members = [m for m in group['members'] if not m.startswith('DUMMY_')]
                dummy_members = [m for m in group['members'] if m.startswith('DUMMY_')]
                logs.append(f"    그룹 {i+1}: 실제 {len(real_members)}명 + 더미 {len(dummy_members)}명 = 총 {len(group['members'])}명")
                # 그룹 멤버 상세 정보 (처음 2개 그룹만)
                if i < 2:
                    logs.append(f"      멤버: {', '.join(group['members'][:5])}{'...' if len(group['members']) > 5 else ''}")
                
                # UI용 그룹 정보 생성
                group_info_for_ui['group_sizes'][group_number] = len(group['members'])
                for member_id in group['members']:
                    group_info_for_ui['member_to_group'][member_id] = group_number
                group_number += 1
        
        # Room 정보 준비
        room_plan = cfg_ui.get('room_plan', pd.DataFrame())
        room_info = {}
        
        if not room_plan.empty:
            for room_type in activities['room_type'].dropna().unique():
                count_col = f"{room_type}_count"
                cap_col = f"{room_type}_cap"
                
                if count_col in room_plan.columns:
                    count = int(room_plan[count_col].iloc[0])
                    cap = int(room_plan[cap_col].iloc[0]) if cap_col in room_plan.columns else 1
                    
                    if count == 1:
                        room_info[room_type] = {'capacity': cap}
                    else:
                        # 알파벳 접미사로 방 생성
                        for i in range(count):
                            suffix = string.ascii_uppercase[i]
                            room_name = f"{room_type}{suffix}"
                            room_info[room_name] = {'capacity': cap}
                            
        # 운영 시간 준비
        oper_window = cfg_ui.get('oper_window', pd.DataFrame())
        oper_hours = {}
        
        if not oper_window.empty:
            start_time_str = oper_window['start_time'].iloc[0]
            end_time_str = oper_window['end_time'].iloc[0]
            
            # 시간을 분 단위로 변환
            start_time = pd.to_datetime(start_time_str).time()
            end_time = pd.to_datetime(end_time_str).time()
            
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            
            # 모든 직무에 동일한 운영시간 적용
            for job_code in job_acts_map['code'].unique():
                oper_hours[job_code] = (start_minutes, end_minutes)
                
        # Precedence 준비
        precedence_df = cfg_ui.get('precedence', pd.DataFrame())
        precedence = []
        
        if not precedence_df.empty:
            for _, row in precedence_df.iterrows():
                precedence.append((
                    row['predecessor'],
                    row['successor'],
                    int(row.get('gap_min', params.get('global_gap_min', 5))),
                    bool(row.get('adjacent', False))
                ))
        
        # Level 2: Batched (+ Adjacent Parallel) 스케줄링
        batched_scheduler = BatchedScheduler(
            groups_result, level2_activities,  # batched_acts 대신 level2_activities 사용
            room_info, oper_hours, precedence, 
            params.get('global_gap_min', 5), logger
        )
        batched_result = batched_scheduler.schedule_batched()
        
        if batched_result is None:
            logs.append("Level 2 실패: Batched 활동 스케줄링 불가")
            return "LEVEL2_FAIL", None, logs, None
            
        logs.append("Level 2 완료: Batched 활동 스케줄링 성공")
        
        # Level 3: Individual 스케줄링 (백트래킹 포함)
        max_retries = 3
        backtrack_count = 0
        
        # individual 활동이 있는지 확인
        individual_acts = activities[activities['mode'].isin(['individual', 'parallel'])]
        logs.append(f"Individual/Parallel 활동 수: {len(individual_acts)}")
        
        while backtrack_count < max_retries:
            try:
                logs.append(f"Level 3 시도 {backtrack_count + 1}/{max_retries}")
                individual_scheduler = IndividualScheduler(
                    groups_result, batched_result, activities, job_acts_map,
                    room_info, oper_hours, precedence, params.get('global_gap_min', 5),
                    params.get('max_stay_hours', 8), logger
                )
                final_schedule = individual_scheduler.schedule_individual(the_date)
            except Exception as e:
                logs.append(f"Level 3 오류: {str(e)}")
                raise
            
            if final_schedule is not None and not final_schedule.empty:
                # 성공
                logs.append(f"Level 3 성공: {len(final_schedule)}개 활동 스케줄링")
                break
            elif final_schedule is not None and final_schedule.empty and individual_acts.empty:
                # Individual 활동이 없는 경우 - 정상
                logs.append("Level 3: Individual 활동이 없어 스킵")
                break
            
            # Level 3 실패 시 백트래킹
            backtrack_count += 1
            logs.append(f"Level 3 실패, 백트래킹 시도 {backtrack_count}/{max_retries}")
            
            if backtrack_count < max_retries:
                # Level 2를 다른 전략으로 재시도
                logs.append("Level 2 재시도: 시간 분산 전략 적용")
                
                # 솔버 파라미터 조정 (시간 분산을 위해)
                batched_scheduler.time_distribution_weight = backtrack_count * 0.3
                batched_result = batched_scheduler.schedule_batched()
                
                if batched_result is None:
                    logs.append("Level 2 재시도도 실패")
                    return "LEVEL2_FAIL", None, logs, None
                    
        if final_schedule is None:
            logs.append("Level 3 최종 실패: 모든 백트래킹 시도 소진")
            return "LEVEL3_FAIL", None, logs, None
            
        # Level 2와 Level 3 결과 통합
        # final_schedule이 None인 경우 빈 DataFrame으로 처리
        if final_schedule is None:
            final_schedule = pd.DataFrame()
            logs.append("Level 3 결과가 None, 빈 DataFrame으로 처리")
            
        combined_schedule = _combine_schedules(
            batched_result, final_schedule, groups_result, the_date
        )
        
        # 결과 검증
        if combined_schedule.empty:
            logs.append("⚠️ 통합된 스케줄이 비어있음")
            # batched 결과만이라도 있으면 성공으로 처리
            if batched_result and 'schedule' in batched_result and batched_result['schedule']:
                logs.append("Batched 결과는 있음 - 재변환 시도")
        else:
            logs.append(f"통합 완료: {len(combined_schedule)}개 항목")
        
        # 체류시간 검증
        max_stay_hours = params.get('max_stay_hours', 8)
        stay_valid, stay_violations = _check_stay_duration(
            combined_schedule, max_stay_hours, logger
        )
        
        if not stay_valid:
            logs.append(f"⚠️ 체류시간 제약 위반: {len(stay_violations)}건")
            logs.extend(stay_violations[:5])  # 처음 5개만 로그에 추가
            # 현재는 경고만 하고 진행 (나중에 백트래킹 시 사용)
        
        logs.append("=== 3단계 최적화 완료 ===")
        
        return "OK", combined_schedule, logs, group_info_for_ui if group_info_for_ui['member_to_group'] else None
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logs.append(f"❌ 3단계 최적화 오류: {str(e)}")
        logs.append("상세 오류:")
        logs.extend(error_trace.split('\n')[:20])  # 처음 20줄만
        
        # 오류 유형별 분석
        if "KeyError" in str(e):
            logs.append("\n⚠️ 데이터 키 오류 - 필수 설정이 누락되었을 수 있습니다.")
        elif "ValueError" in str(e):
            logs.append("\n⚠️ 값 오류 - 잘못된 입력값이 있을 수 있습니다.")
        elif "IndexError" in str(e):
            logs.append("\n⚠️ 인덱스 오류 - 빈 데이터를 참조하려 했을 수 있습니다.")
        
        logger.error(f"3단계 최적화 중 오류: {str(e)}\n{error_trace}")
        
        # 에러가 발생해도 Level 1에서 생성한 그룹 정보는 반환
        return "ERROR", None, logs, group_info_for_ui if group_info_for_ui['member_to_group'] else None 