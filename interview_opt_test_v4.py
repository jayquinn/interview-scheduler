"""
간소화된 면접 스케줄 최적화 도구 - 핵심 엔진만 포함
"""
import logging
import traceback
from datetime import timedelta, datetime
from pathlib import Path
from collections import defaultdict
import pandas as pd
from ortools.sat.python import cp_model

# 기본 파라미터 (하드코딩)
DEFAULT_MIN_GAP_MIN = 5          # 활동 간 최소 간격(분)
TIME_LIMIT_SEC     = 60.0        # OR-Tools 시간 제한(초)

# 규칙 검증 함수
def verify_rules(wide_df: pd.DataFrame, rules: list) -> list:
    """
    wide_df에 선후행 규칙이 지켜졌는지 검증합니다.
    """
    err_msgs = []
    if wide_df.empty:
        return err_msgs

    for _, row in wide_df.iterrows():
        times = {}
        for col in row.index:
            if col.startswith(('start_', 'end_')) and pd.notna(row[col]):
                parts = col.split('_', 1)
                times[(parts[0], parts[1])] = row[col]

        for rule in rules:
            if len(rule) == 4:
                pred, succ, _, __ = rule
            else:
                pred, succ, _ = rule

            if pred == '__START__':
                succ_start_time = times.get(('start', succ))
                if succ_start_time is None: continue
                
                is_earliest = True
                for (typ, act), time in times.items():
                    if typ == 'start' and act != succ and time < succ_start_time:
                        is_earliest = False
                        break
                if not is_earliest:
                    err_msgs.append(f"Rule Violation: {row['id']} - {succ} is not the first activity.")

            elif succ == '__END__':
                pred_end_time = times.get(('end', pred))
                if pred_end_time is None: continue

                is_latest = True
                for (typ, act), time in times.items():
                    if typ == 'end' and act != pred and time > pred_end_time:
                        is_latest = False
                        break
                if not is_latest:
                    err_msgs.append(f"Rule Violation: {row['id']} - {pred} is not the last activity.")

            else:
                pred_end_time = times.get(('end', pred))
                succ_start_time = times.get(('start', succ))
                if pred_end_time is not None and succ_start_time is not None:
                    if pred_end_time > succ_start_time:
                        err_msgs.append(f"Rule Violation: {row['id']} - {pred} ends after {succ} starts.")
    return err_msgs


def prepare_schedule(solver, intervals, presences, room_assignments, CANDIDATE_SPACE, ACT_SPACE, ROOM_SPACE, the_date, logger):
    """
    Solver 결과를 바탕으로 wide-format DataFrame을 생성합니다.
    """
    rows = []
    base_time = pd.to_datetime(the_date.date().strftime('%Y-%m-%d') + ' 00:00:00')

    for (cid, act_name), iv in intervals.items():
        if solver.Value(presences.get((cid, act_name), 0)) == 1:
            start_min = solver.Value(iv.StartExpr())
            end_min = solver.Value(iv.EndExpr())

            start_time = base_time + pd.Timedelta(minutes=start_min)
            end_time = base_time + pd.Timedelta(minutes=end_min)
            
            assigned_room = "N/A"
            if room_assignments:
                for (r_cid, r_act, r_room), pres_var in room_assignments.items():
                    if r_cid == cid and r_act == act_name and solver.Value(pres_var) == 1:
                        assigned_room = r_room
                        break

            rows.append({
                'id': cid,
                'code': CANDIDATE_SPACE[cid]['job_code'],
                'interview_date': the_date,
                'activity': act_name,
                'loc': assigned_room,
                'start': start_time,
                'end': end_time
            })

    if not rows:
        return pd.DataFrame(), {}
        
    long_df = pd.DataFrame(rows)
    if long_df.empty:
        return pd.DataFrame(), {}

    long_df['start'] = pd.to_datetime(long_df['start'])
    long_df['end'] = pd.to_datetime(long_df['end'])

    wide_df = long_df.pivot_table(
        index=['id', 'code', 'interview_date'],
        columns='activity',
        values=['loc', 'start', 'end'],
        aggfunc='first'
    )
    
    wide_df.columns = [f'{val}_{act}' for val, act in wide_df.columns]
    wide_df = wide_df.reset_index()
    
    return wide_df, {}


def prepare_schedule_long(solver, intervals, presences, room_assignments, CANDIDATE_SPACE, ACT_SPACE, ROOM_SPACE, the_date, logger):
    """'long-form' DataFrame을 생성합니다."""
    
    rows = []
    for (cid, act_name), iv in intervals.items():
        if solver.Value(presences[(cid, act_name)]):
            start_time = timedelta(minutes=solver.Value(iv.StartExpr()))
            end_time = timedelta(minutes=solver.Value(iv.EndExpr()))
            
            room_name = "N/A"
            for r_name, p_var in room_assignments.items():
                if r_name[0] == cid and r_name[1] == act_name and solver.Value(p_var):
                    room_name = r_name[2]
                    break

            rows.append({
                'id': cid,
                'activity': act_name,
                'start_time': the_date + start_time,
                'end_time': the_date + end_time,
                'room': room_name,
                'job_code': CANDIDATE_SPACE[cid]['job_code'],
                'interview_date': the_date.date()
            })
            
    if not rows:
        return pd.DataFrame()
        
    df = pd.DataFrame(rows)
    return df


# OR-Tools 모델 빌드 및 실행
def build_model(config, logger):
    """
    주어진 설정을 바탕으로 CP-MODEL을 빌드합니다.
    """
    model = cp_model.CpModel()
    all_logs = []

    try:
        the_date = config['the_date']
        MIN_GAP = config['min_gap_min']
        ACT_SPACE = config['act_info']
        rules = config.get('rules', [])
        CANDIDATE_SPACE = config['candidate_info']
        ROOM_SPACE = config['room_info']
        OPER_HOURS = config['oper_hours']
        CANDIDATE_ACTS = {cid: data['activities'] for cid, data in CANDIDATE_SPACE.items()}
        CIDS = list(CANDIDATE_SPACE.keys())
        
        # 고정된 스케줄 (batched 활동 등)
        fixed_schedule = config.get('fixed_schedule', {})
        
        # 그룹 제약 (batched → parallel → individual 흐름에서 사용)
        group_constraints = config.get('group_constraints', {})
        
        all_rule_activities = set()
        for rule in rules:
            if len(rule) == 4:
                pred, succ, _, __ = rule
            else:
                pred, succ, _ = rule
            if pred != '__START__': all_rule_activities.add(pred)
            if succ != '__END__': all_rule_activities.add(succ)

        missing_activities = all_rule_activities - set(ACT_SPACE.keys())
        if missing_activities:
            raise ValueError(f"설정 오류: 다음 활동에 대한 장소(Room) 설정이 누락되었습니다: {', '.join(missing_activities)}")

        horizon = 0
        if OPER_HOURS:
            for _, (start, end) in OPER_HOURS.items():
                horizon = max(horizon, end)
        
        intervals, presences, room_assignments = {}, {}, {}
        optimize_for_max_scheduled = config.get('optimize_for_max_scheduled', False)
        candidate_master_presences = []

        for cid in CIDS:
            master_presence_var = model.NewBoolVar(f'master_presence_{cid}')
            if optimize_for_max_scheduled:
                candidate_master_presences.append(master_presence_var)
            else:
                model.Add(master_presence_var == 1)

            for act_name in CANDIDATE_ACTS.get(cid, []):
                if act_name in ACT_SPACE:
                    duration = ACT_SPACE[act_name]['duration']
                    suffix = f"{cid}_{act_name}"
                    
                    # 고정된 스케줄이 있는지 확인
                    if cid in fixed_schedule and act_name in fixed_schedule[cid]:
                        # 고정된 시간 사용
                        fixed_info = fixed_schedule[cid][act_name]
                        start_var = model.NewIntVar(fixed_info['start'], fixed_info['start'], f'start_{suffix}')
                        end_var = model.NewIntVar(fixed_info['end'], fixed_info['end'], f'end_{suffix}')
                    else:
                        # 일반적인 변수 생성
                        start_var = model.NewIntVar(0, horizon, f'start_{suffix}')
                        end_var = model.NewIntVar(0, horizon, f'end_{suffix}')
                    
                    presence_var = model.NewBoolVar(f'presence_{suffix}')
                    model.Add(presence_var == master_presence_var)
                    
                    interval_var = model.NewOptionalIntervalVar(start_var, duration, end_var, presence_var, f'interval_{suffix}')
                    intervals[(cid, act_name)] = interval_var
                    presences[(cid, act_name)] = presence_var
                    
                    # 그룹 제약 적용 (최소 시작 시간)
                    if cid in group_constraints and act_name in group_constraints[cid]:
                        min_start = group_constraints[cid][act_name].get('min_start', 0)
                        if min_start > 0:
                            model.Add(start_var >= min_start)

        for cid in CIDS:
            cid_intervals = [iv for (c, _), iv in intervals.items() if c == cid]
            if len(cid_intervals) > 1:
                model.AddNoOverlap(cid_intervals)

        if MIN_GAP > 0:
            for cid in CIDS:
                acts = CANDIDATE_ACTS.get(cid, [])
                for i in range(len(acts)):
                    for j in range(i + 1, len(acts)):
                        act1, act2 = acts[i], acts[j]
                        if (cid, act1) in intervals and (cid, act2) in intervals:
                            iv1, iv2 = intervals[(cid, act1)], intervals[(cid, act2)]
                            b = model.NewBoolVar(f'gap_{cid}_{act1}_{act2}')
                            model.Add(iv2.StartExpr() >= iv1.EndExpr() + MIN_GAP).OnlyEnforceIf(b)
                            model.Add(iv1.StartExpr() >= iv2.EndExpr() + MIN_GAP).OnlyEnforceIf(b.Not())

        room_intervals = defaultdict(list)
        for (cid, act_name), iv in intervals.items():
            required_rooms = ACT_SPACE[act_name].get('required_rooms', [])
            possible_rooms = [r_name for r_type in required_rooms for r_name in ROOM_SPACE if r_name.startswith(r_type)]
            
            # 고정된 방이 있는지 확인
            fixed_room = None
            if cid in fixed_schedule and act_name in fixed_schedule[cid]:
                fixed_room = fixed_schedule[cid][act_name].get('room')
            
            room_presence_vars = []
            for room_name in possible_rooms:
                if fixed_room and room_name != fixed_room:
                    # 고정된 방이 아니면 사용하지 않음
                    presence_var = model.NewBoolVar(f'presence_{cid}_{act_name}_{room_name}')
                    model.Add(presence_var == 0)
                else:
                    presence_var = model.NewBoolVar(f'presence_{cid}_{act_name}_{room_name}')
                    if fixed_room and room_name == fixed_room:
                        # 고정된 방이면 반드시 사용
                        model.Add(presence_var == presences[(cid, act_name)])
                
                room_assignments[(cid, act_name, room_name)] = presence_var
                room_presence_vars.append(presence_var)
                
                v_iv = model.NewOptionalIntervalVar(iv.StartExpr(), ACT_SPACE[act_name]['duration'], iv.EndExpr(), presence_var, f'v_iv_{cid}_{act_name}_{room_name}')
                room_intervals[room_name].append(v_iv)
            
            if room_presence_vars and not fixed_room:
                model.AddExactlyOne(room_presence_vars)

        for room_name, iv_list in room_intervals.items():
            if len(iv_list) > 1:
                capacity = ROOM_SPACE[room_name].get('capacity', 1)
                model.AddCumulative(iv_list, [1]*len(iv_list), capacity)

        for rule in rules:
            if len(rule) == 4:
                pred, succ, gap, stick = rule
            else:
                pred, succ, gap = rule
                stick = False

            for cid in CIDS:
                acts = CANDIDATE_ACTS.get(cid, [])
                
                # Rule 1: __START__ → succ
                if pred == '__START__':
                    if succ in acts:
                        succ_iv = intervals[(cid, succ)]
                        # fixed_schedule에서 이미 스케줄된 활동들의 최대 종료 시간 확인
                        # 운영 시작 시간 가져오기
                        job_code = CANDIDATE_SPACE[cid]['job_code']
                        oper_start_time = OPER_HOURS[job_code][0] if job_code in OPER_HOURS else 0
                        min_start_time = oper_start_time  # 기본 운영 시작 시간
                        
                        if cid in fixed_schedule:
                            for fixed_act, fixed_info in fixed_schedule[cid].items():
                                if 'end' in fixed_info:
                                    # fixed 활동 종료 후에 시작해야 함 (gap은 precedence rule의 값 사용)
                                    rule_gap = gap if len(rule) > 2 else MIN_GAP
                                    min_start_time = max(min_start_time, fixed_info['end'] + rule_gap)
                        
                        # succ는 fixed 활동들 이후에 시작
                        model.Add(succ_iv.StartExpr() >= min_start_time)
                        
                        # 다른 individual 활동들보다는 먼저
                        for other_act in acts:
                            if other_act != succ and (cid, other_act) in intervals:
                                other_iv = intervals[(cid, other_act)]
                                # 다른 활동도 fixed가 아닌 경우에만
                                if not (cid in fixed_schedule and other_act in fixed_schedule[cid]):
                                    model.Add(succ_iv.EndExpr() <= other_iv.StartExpr())

                # Rule 2: pred → __END__
                elif succ == '__END__':
                    if pred in acts:
                        pred_iv = intervals[(cid, pred)]
                        for other_act in acts:
                            if other_act != pred:
                                other_iv = intervals[(cid, other_act)]
                                model.Add(pred_iv.StartExpr() >= other_iv.EndExpr())

                # Rule 3: pred → succ
                elif pred in acts and succ in acts:
                    pred_iv = intervals[(cid, pred)]
                    succ_iv = intervals[(cid, succ)]
                    
                    # Parallel → Individual adjacent 특별 처리
                    if stick and pred in ACT_SPACE and succ in ACT_SPACE:
                        pred_mode = 'parallel' if ACT_SPACE[pred].get('max_ppl', 1) > 1 else 'individual'
                        succ_mode = 'individual' if ACT_SPACE[succ].get('max_ppl', 1) == 1 else 'parallel'
                        
                        if pred_mode == 'parallel' and succ_mode == 'individual':
                            # Parallel 활동을 같이 끝낸 사람들이 Individual로 순차적으로 이동
                            # Adjacent를 "유연한 연속"으로 해석
                            # 같은 시간에 pred를 끝낸 다른 사람들을 고려하여 유연한 gap 허용
                            flexible_gap = gap + ACT_SPACE[succ]['duration'] * 2  # 여유 시간 추가
                            model.Add(succ_iv.StartExpr() >= pred_iv.EndExpr() + gap)
                            model.Add(succ_iv.StartExpr() <= pred_iv.EndExpr() + flexible_gap)
                        else:
                            # 일반적인 adjacent 제약
                            model.Add(succ_iv.StartExpr() == pred_iv.EndExpr() + gap)
                    elif stick:
                        model.Add(succ_iv.StartExpr() == pred_iv.EndExpr() + gap)
                    else:
                        model.Add(succ_iv.StartExpr() >= pred_iv.EndExpr() + gap)

        for cid, data in CANDIDATE_SPACE.items():
            if data['job_code'] in OPER_HOURS:
                start_time, end_time = OPER_HOURS[data['job_code']]
                for act_name in CANDIDATE_ACTS.get(cid, []):
                    if (cid, act_name) in intervals:
                        iv = intervals[(cid, act_name)]
                        model.Add(iv.StartExpr() >= start_time)
                        model.Add(iv.EndExpr() <= end_time)

        if optimize_for_max_scheduled:
            model.Maximize(sum(candidate_master_presences))

        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = config.get('num_cpus', 8)
        solver.parameters.log_search_progress = True
        solver.parameters.max_time_in_seconds = config.get('time_limit_sec', 180.0)
        status = solver.Solve(model)
        status_name = solver.StatusName(status)

        if status == cp_model.FEASIBLE:
            all_logs.append(">> 솔버 시간 초과: 최적 해를 보장할 수 없지만, 실행 가능한 스케줄을 반환합니다.")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            final_report_df, _ = prepare_schedule(solver, intervals, presences, room_assignments, CANDIDATE_SPACE, ACT_SPACE, ROOM_SPACE, the_date, logger)
            err_msgs = verify_rules(final_report_df, rules)
            if err_msgs:
                logger.warning("Rule violations found:")
                for msg in err_msgs: logger.warning(msg)
                status_name = 'RULE_VIOLATED'
            
            # Use the new long-form schedule preparation
            final_report_df_long = prepare_schedule_long(solver, intervals, presences, room_assignments, CANDIDATE_SPACE, ACT_SPACE, ROOM_SPACE, the_date, logger)
            
        else:
            final_report_df = pd.DataFrame()
            final_report_df_long = pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error during model building or solving: {e}", exc_info=True)
        status_name = "ERROR"
        final_report_df = pd.DataFrame()
        final_report_df_long = pd.DataFrame()
        all_logs.append(f"\n--- EXCEPTION TRACEBACK ---\n{traceback.format_exc()}")

    return model, status_name, final_report_df_long, all_logs
