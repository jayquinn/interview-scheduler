# interview_opt_test_v4.py
# -*- coding: utf-8 -*-
"""
면접 스케줄 최적화 시스템
============================================================
Interview Schedule Optimiser – multi-date / multi-grid
============================================================
* parameter_grid_test_v4.csv 에 정의된 파라미터 세트 × 날짜를 순차 탐색
* 첫 SAT+하드룰 통과 해를 찾으면 그 날짜는 종료
* 결과는 schedule_wide.csv 로 누적 저장, 시도 내역은 run_log.csv 기록
"""

import itertools
import pandas as pd


def _build_param_grid() -> pd.DataFrame:
    """기본 파라미터 그리드를 생성한다."""
    seed_rows = [
        dict(priority=0, scenario_id="S_SAFE", wave_len=35, max_wave=18,
             br_offset_A=4, br_offset_B=3, min_gap_min=5, tl_sec=30)
    ]

    grid = []
    for wl, mw, brA, brB, mg in itertools.product(
            [35], [18], [-2,-1,0,1,2], [-2,-1,0,1,2], [5]):
        if wl==50 and mw==16 and brA==3 and brB==2 and mg==5:
            continue
        pr = 1
        if wl > 35: pr += 1
        if mw < 14: pr += 1
        if mg > 10: pr += 1
        grid.append(dict(priority=pr, wave_len=wl, max_wave=mw,
                         br_offset_A=brA, br_offset_B=brB,
                         min_gap_min=mg, tl_sec=30))

    df = (pd.DataFrame(seed_rows + grid)
            .sort_values(["priority","wave_len","min_gap_min","max_wave"])
            .reset_index(drop=True))

    if "scenario_id" not in df.columns:
        df.insert(0, "scenario_id",
                  [f"S{str(i+1).zfill(3)}" for i in range(len(df))])
    else:
        mask = df["scenario_id"].isna() | (df["scenario_id"]=="")
        df.loc[mask, "scenario_id"] = [
            f"S{str(i+1).zfill(3)}" for i in range(mask.sum())
        ]
    return df
# ──────────────────────────────────────


# 공통 import & 상수
import traceback
from datetime import timedelta
from collections import defaultdict

from ortools.sat.python import cp_model





# 하드-룰 검증 함수
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


# ────────────────────────────────
# 2. build_model() –  **엔진**
# ────────────────────────────────
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
                    start_var = model.NewIntVar(0, horizon, f'start_{suffix}')
                    end_var = model.NewIntVar(0, horizon, f'end_{suffix}')
                    
                    presence_var = model.NewBoolVar(f'presence_{suffix}')
                    model.Add(presence_var == master_presence_var)
                    
                    interval_var = model.NewOptionalIntervalVar(start_var, duration, end_var, presence_var, f'interval_{suffix}')
                    intervals[(cid, act_name)] = interval_var
                    presences[(cid, act_name)] = presence_var

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
            
            room_presence_vars = []
            for room_name in possible_rooms:
                presence_var = model.NewBoolVar(f'presence_{cid}_{act_name}_{room_name}')
                room_assignments[(cid, act_name, room_name)] = presence_var
                room_presence_vars.append(presence_var)
                
                v_iv = model.NewOptionalIntervalVar(iv.StartExpr(), ACT_SPACE[act_name]['duration'], iv.EndExpr(), presence_var, f'v_iv_{cid}_{act_name}_{room_name}')
                room_intervals[room_name].append(v_iv)
            
            if room_presence_vars:
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
                        for other_act in acts:
                            if other_act != succ:
                                other_iv = intervals[(cid, other_act)]
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
                    if stick:
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
            

            
        else:
            final_report_df = pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error during model building or solving: {e}", exc_info=True)
        status_name = "ERROR"
        final_report_df = pd.DataFrame()
        all_logs.append(f"\n--- EXCEPTION TRACEBACK ---\n{traceback.format_exc()}")

    return model, status_name, final_report_df, all_logs



