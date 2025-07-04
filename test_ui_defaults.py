#!/usr/bin/env python3
"""
app.py의 실제 UI 디폴트 값들을 사용한 스케줄러 테스트
init_session_states()에서 설정되는 정확한 값들로 검증
"""

import pandas as pd
from datetime import date, time, datetime
import sys
import traceback

def create_ui_default_data():
    """app.py의 실제 디폴트 값들을 정확히 재현"""
    print("🔧 UI 디폴트 데이터 생성 중...")
    
    # 1. 기본 활동 템플릿 (app.py 라인 77-84)
    default_activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 2. 스마트 직무 매핑 (app.py 라인 87-93) - 멀티 직무 지원
    act_list = default_activities.query("use == True")["activity"].tolist()
    job_data_list = []
    for job_code in ["JOB01", "JOB02"]:  # 멀티데이트 계획의 직무들
        job_row = {"code": job_code, "count": 23}  # 멀티데이트 계획과 일치
        for act in act_list:
            job_row[act] = True
        job_data_list.append(job_row)
    job_acts_map = pd.DataFrame(job_data_list)
    
    # 3. 기본 선후행 제약 (app.py 라인 95-97)
    default_precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}  # 연속배치
    ])
    
    # 4. 기본 운영 시간 (app.py 라인 100-101)
    oper_start_time = time(9, 0)
    oper_end_time = time(17, 30)
    
    # 5. 스마트 방 템플릿 (app.py 라인 104-109)
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},  # 원래 디폴트: 1개, 2명
        "발표면접실": {"count": 2, "cap": 1}   # 원래 디폴트: 2개, 1명
    }
    
    # 6. 방 계획 자동 생성 (app.py 라인 112-121)
    final_plan_dict = {}
    for rt, values in room_template.items():
        final_plan_dict[f"{rt}_count"] = values['count']
        final_plan_dict[f"{rt}_cap"] = values['cap']
    final_plan_dict["date"] = pd.to_datetime("2025-07-01")  # 테스트용 날짜 추가
    room_plan = pd.DataFrame([final_plan_dict])
    
    # 7. 운영 시간 자동 생성 (app.py 라인 124-131) - 멀티 직무 지원
    oper_window_data = []
    for job_code in ["JOB01", "JOB02"]:  # 멀티데이트 계획의 직무들
        oper_window_data.append({
            "start_time": oper_start_time.strftime("%H:%M"),
            "end_time": oper_end_time.strftime("%H:%M"),
            "code": job_code,
            "date": pd.to_datetime("2025-07-01")
        })
    oper_window = pd.DataFrame(oper_window_data)
    
    # 8. 집단면접 설정 (app.py 라인 139-142)
    group_min_size = 4
    group_max_size = 6
    global_gap_min = 5
    max_stay_hours = 5
    
    # 9. 멀티 날짜 계획 (app.py 라인 145-171) - 첫 날만 테스트용으로
    multidate_plans = {
        "2025-07-01": {
            "date": date(2025, 7, 1),
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 23},
                {"code": "JOB02", "count": 23}
            ]
        }
    }
    
    # 10. 가상 지원자 생성 - 멀티데이트 방식으로
    candidates_exp = generate_multidate_candidates(multidate_plans)
    
    # 전체 설정
    config = {
        "activities": default_activities,
        "job_acts_map": job_acts_map,
        "precedence": default_precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "candidates_exp": candidates_exp,
        "room_template": room_template,
        "group_min_size": group_min_size,
        "group_max_size": group_max_size,
        "global_gap_min": global_gap_min,
        "max_stay_hours": max_stay_hours,
        "multidate_plans": multidate_plans,
        "interview_dates": [date(2025, 7, 1)]
    }
    
    print("✅ UI 디폴트 데이터 생성 완료")
    print(f"  - 활동: {len(default_activities)}개 ({', '.join(default_activities['activity'].tolist())})")
    print(f"  - 방 종류: {len(room_template)}개")
    print(f"  - 지원자: {len(candidates_exp)}명 (실제 ID: {candidates_exp['id'].nunique()}명)")
    print(f"  - 선후행 제약: {len(default_precedence)}개")
    print(f"  - 운영시간: {oper_start_time} ~ {oper_end_time}")
    
    return config

def generate_multidate_candidates(multidate_plans):
    """멀티데이트 계획으로부터 지원자 데이터 생성"""
    all_candidates = []
    
    for date_key, plan in multidate_plans.items():
        if plan.get("enabled", True):
            interview_date = plan["date"]
            for job in plan.get("jobs", []):
                code = job["code"]
                count = job["count"]
                
                # 각 지원자는 모든 활동을 해야 함
                activities = ["토론면접", "발표준비", "발표면접"]
                
                for i in range(1, count + 1):
                    candidate_id = f"{code}_{str(i).zfill(3)}"
                    for act in activities:
                        all_candidates.append({
                            'id': candidate_id, 
                            'code': code, 
                            'activity': act,
                            'interview_date': interview_date
                        })
    
    if not all_candidates:
        return pd.DataFrame(columns=['id', 'code', 'activity', 'interview_date'])
    
    return pd.DataFrame(all_candidates)

def test_ui_defaults_with_solver():
    """실제 UI 디폴트 값으로 솔버 테스트"""
    print("\n🚀 UI 디폴트 설정으로 솔버 테스트...")
    
    try:
        config = create_ui_default_data()
        
        # Core 모듈로 설정 빌드
        import core
        cfg = core.build_config(config)
        
        print(f"\n📋 설정 확인:")
        print(f"  - Activities: {len(cfg['activities'])} rows")
        print(f"  - Job mapping: {len(cfg['job_acts_map'])} rows")
        print(f"  - Room plan: {len(cfg['room_plan'])} rows")
        print(f"  - Candidates: {len(cfg['candidates_exp'])} rows")
        
        # 활동별 정보 확인
        for _, row in cfg['activities'].iterrows():
            print(f"    {row['activity']}: {row['mode']}, {row['duration_min']}분, {row['min_cap']}-{row['max_cap']}명")
        
        # 방 정보 확인
        room_plan = cfg['room_plan'].iloc[0]
        print(f"\n🏢 방 구성:")
        for col in room_plan.index:
            if '_count' in col:
                room_type = col.replace('_count', '')
                count = int(room_plan[col])
                cap_col = f"{room_type}_cap"
                cap = int(room_plan.get(cap_col, 1))
                print(f"    {room_type}: {count}개, 수용인원 {cap}명")
        
        # 지원자 분포 확인
        print(f"\n👥 지원자 분포:")
        job_counts = cfg['candidates_exp'].groupby('code')['id'].nunique()
        for code, count in job_counts.items():
            print(f"    {code}: {count}명")
        
        # 솔버 파라미터 (UI 디폴트 값 사용)
        params = {
            "min_gap_min": config['global_gap_min'],
            "time_limit_sec": 60,  # 충분한 시간
            "max_stay_hours": config['max_stay_hours'],
            "group_min_size": config['group_min_size'],
            "group_max_size": config['group_max_size']
        }
        
        print(f"\n⚙️ 솔버 파라미터:")
        for k, v in params.items():
            print(f"    {k}: {v}")
        
        # 실제 UI에서 사용하는 v2 스케줄러 테스트
        print(f"\n🔥 계층적 스케줄러 v2 테스트...")
        
        from solver.api import solve_for_days_v2
        
        status, final_wide, logs, daily_limit = solve_for_days_v2(cfg, params, debug=True)
        
        print(f"\n📊 결과:")
        print(f"  Status: {status}")
        print(f"  Daily Limit: {daily_limit}")
        print(f"  Schedule Count: {len(final_wide) if final_wide is not None else 0}")
        
        if final_wide is not None and not final_wide.empty:
            print("✅ UI 디폴트 설정 검증 성공!")
            
            # 상세 분석
            print(f"\n📈 스케줄링 결과 분석:")
            print(f"  - 총 스케줄 항목: {len(final_wide)}개")
            
            if 'applicant_id' in final_wide.columns:
                scheduled_applicants = final_wide['applicant_id'].nunique()
                total_applicants = cfg['candidates_exp']['id'].nunique()
                print(f"  - 스케줄된 지원자: {scheduled_applicants}/{total_applicants}명 ({scheduled_applicants/total_applicants*100:.1f}%)")
            
            # 활동별 분석
            activity_counts = {}
            for col in final_wide.columns:
                if col.startswith('start_'):
                    activity = col.replace('start_', '')
                    non_null_count = final_wide[col].notna().sum()
                    if non_null_count > 0:
                        activity_counts[activity] = non_null_count
            
            print(f"  - 활동별 스케줄:")
            for activity, count in activity_counts.items():
                print(f"    {activity}: {count}명")
            
            # 시간 분포 확인
            if activity_counts:
                # time 컬럼이 있으면 사용 (timedelta 형식)
                if 'time' in final_wide.columns:
                    time_values = final_wide['time'].dropna()
                    if not time_values.empty:
                        earliest_sec = time_values.min().total_seconds()
                        latest_sec = time_values.max().total_seconds()
                        earliest_time = f"{int(earliest_sec//3600):02d}:{int((earliest_sec%3600)//60):02d}"
                        latest_time = f"{int(latest_sec//3600):02d}:{int((latest_sec%3600)//60):02d}"
                        print(f"  - 시간 범위: {earliest_time} ~ {latest_time}")
                else:
                    # 기존 방식 (datetime 컬럼)
                    first_activity = list(activity_counts.keys())[0]
                    start_col = f'start_{first_activity}'
                    if start_col in final_wide.columns:
                        try:
                            start_times = pd.to_datetime(final_wide[start_col].dropna())
                            if not start_times.empty:
                                earliest = start_times.min().strftime('%H:%M')
                                latest = start_times.max().strftime('%H:%M')
                                print(f"  - 시간 범위: {earliest} ~ {latest}")
                        except TypeError:
                            print(f"  - 시간 데이터 형식 분석 스킵")
            
            # 배치형 활동 분석 (토론면접) - v2 스케줄러 결과 형식 고려
            try:
                # v2 스케줄러 결과에서 그룹 정보 추출
                if 'group_id' in final_wide.columns and 'activity_name' in final_wide.columns:
                    discussion_df = final_wide[final_wide['activity_name'] == '토론면접']
                    if not discussion_df.empty:
                        discussion_groups = discussion_df.groupby(['start_time', 'end_time', 'room_name']).size()
                        print(f"  - 토론면접 그룹:")
                        for (start, end, room), size in discussion_groups.items():
                            if pd.notna(start):
                                try:
                                    start_time = pd.to_datetime(start).strftime('%H:%M')
                                    end_time = pd.to_datetime(end).strftime('%H:%M')
                                    print(f"    {start_time}-{end_time} ({room}): {size}명")
                                except:
                                    print(f"    {start}-{end} ({room}): {size}명")
                elif 'start_토론면접' in final_wide.columns:
                    # 기존 형식
                    discussion_groups = final_wide.groupby(['start_토론면접', 'end_토론면접', 'room_토론면접']).size()
                    if not discussion_groups.empty:
                        print(f"  - 토론면접 그룹:")
                        for (start, end, room), size in discussion_groups.items():
                            if pd.notna(start):
                                start_time = pd.to_datetime(start).strftime('%H:%M')
                                end_time = pd.to_datetime(end).strftime('%H:%M')
                                print(f"    {start_time}-{end_time} ({room}): {size}명")
            except Exception as e:
                print(f"  - 토론면접 그룹 분석 스킵: {e}")
            
            return True, final_wide
        else:
            print("❌ UI 디폴트 설정 검증 실패")
            if logs:
                print(f"\n로그:\n{logs}")
            return False, None
            
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        traceback.print_exc()
        return False, None

def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("🧪 app.py UI 디폴트 설정 검증 테스트")
    print("=" * 80)
    
    # Core 모듈 임포트 테스트
    try:
        import core
        from solver.api import solve_for_days_v2
        print("✅ 모듈 임포트 성공")
    except Exception as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        return
    
    # UI 디폴트 설정 테스트
    success, result = test_ui_defaults_with_solver()
    
    if success:
        print("\n🎉 UI 디폴트 설정 검증 성공!")
        
        # 결과 저장
        if result is not None:
            try:
                result_file = "ui_defaults_test_result.xlsx"
                result.to_excel(result_file, index=False)
                print(f"✅ 결과 저장: {result_file}")
            except Exception as e:
                print(f"⚠️ 결과 저장 실패: {e}")
    else:
        print("\n❌ UI 디폴트 설정 검증 실패")
    
    print("=" * 80)

if __name__ == "__main__":
    main() 