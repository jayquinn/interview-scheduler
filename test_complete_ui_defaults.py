#!/usr/bin/env python3
"""
app.py의 완전한 UI 디폴트 값들을 사용한 스케줄러 테스트
- 4일간 멀티데이트 (2025-07-01 ~ 2025-07-04)
- 11개 직무 (JOB01 ~ JOB11)
- 총 137명 지원자
"""

import pandas as pd
from datetime import date, time, datetime
import sys
import traceback

def create_complete_ui_default_data():
    """app.py의 완전한 UI 디폴트 값들을 정확히 재현"""
    print("🔧 완전한 UI 디폴트 데이터 생성 중...")
    
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
    
    # 2. 완전한 멀티 날짜 계획 (app.py 라인 152-179)
    multidate_plans = {
        "2025-07-01": {
            "date": date(2025, 7, 1),
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 23},
                {"code": "JOB02", "count": 23}
            ]
        },
        "2025-07-02": {
            "date": date(2025, 7, 2),
            "enabled": True,
            "jobs": [
                {"code": "JOB03", "count": 20},
                {"code": "JOB04", "count": 20}
            ]
        },
        "2025-07-03": {
            "date": date(2025, 7, 3),
            "enabled": True,
            "jobs": [
                {"code": "JOB05", "count": 12},
                {"code": "JOB06", "count": 15},
                {"code": "JOB07", "count": 6}
            ]
        },
        "2025-07-04": {
            "date": date(2025, 7, 4),
            "enabled": True,
            "jobs": [
                {"code": "JOB08", "count": 6},
                {"code": "JOB09", "count": 6},
                {"code": "JOB10", "count": 3},
                {"code": "JOB11", "count": 3}
            ]
        }
    }
    
    # 총 지원자 수 계산
    total_candidates = 0
    all_dates = []
    all_job_codes = []
    
    for date_key, plan in multidate_plans.items():
        if plan.get("enabled", True):
            all_dates.append(plan["date"])
            for job in plan.get("jobs", []):
                all_job_codes.append(job["code"])
                total_candidates += job.get("count", 0)
    
    print(f"📊 총 규모: {len(all_dates)}일간, {len(all_job_codes)}개 직무, {total_candidates}명 지원자")
    
    # 3. 모든 직무에 대한 job_acts_map 생성
    act_list = default_activities.query("use == True")["activity"].tolist()
    job_data_list = []
    
    for date_key, plan in multidate_plans.items():
        for job in plan.get("jobs", []):
            job_row = {"code": job["code"], "count": job["count"]}
            for act in act_list:
                job_row[act] = True
            job_data_list.append(job_row)
    
    job_acts_map = pd.DataFrame(job_data_list)
    
    # 4. 기본 선후행 제약
    default_precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 5. 기본 운영 시간
    oper_start_time = time(9, 0)
    oper_end_time = time(17, 30)
    
    # 6. 스마트 방 템플릿
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 7. 모든 날짜에 대한 방 계획 생성
    room_plan_data = []
    for interview_date in all_dates:
        room_plan_dict = {"date": pd.to_datetime(interview_date)}
        for rt, values in room_template.items():
            room_plan_dict[f"{rt}_count"] = values['count']
            room_plan_dict[f"{rt}_cap"] = values['cap']
        room_plan_data.append(room_plan_dict)
    
    room_plan = pd.DataFrame(room_plan_data)
    
    # 8. 모든 날짜와 직무에 대한 운영 시간 생성
    oper_window_data = []
    for date_key, plan in multidate_plans.items():
        interview_date = plan["date"]
        for job in plan.get("jobs", []):
            oper_window_data.append({
                "start_time": oper_start_time.strftime("%H:%M"),
                "end_time": oper_end_time.strftime("%H:%M"),
                "code": job["code"],
                "date": pd.to_datetime(interview_date)
            })
    
    oper_window = pd.DataFrame(oper_window_data)
    
    # 9. 집단면접 설정
    group_min_size = 4
    group_max_size = 6
    global_gap_min = 5
    max_stay_hours = 5
    
    # 10. 완전한 지원자 생성
    candidates_exp = generate_complete_multidate_candidates(multidate_plans)
    
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
        "interview_dates": all_dates
    }
    
    print("✅ 완전한 UI 디폴트 데이터 생성 완료")
    print(f"  - 활동: {len(default_activities)}개 ({', '.join(default_activities['activity'].tolist())})")
    print(f"  - 면접 날짜: {len(all_dates)}일 ({all_dates[0]} ~ {all_dates[-1]})")
    print(f"  - 직무: {len(all_job_codes)}개 ({all_job_codes[0]} ~ {all_job_codes[-1]})")
    print(f"  - 지원자: {len(candidates_exp)}개 항목 (실제 {candidates_exp['id'].nunique()}명)")
    print(f"  - 방 종류: {len(room_template)}개")
    print(f"  - 선후행 제약: {len(default_precedence)}개")
    print(f"  - 운영시간: {oper_start_time} ~ {oper_end_time}")
    
    return config

def generate_complete_multidate_candidates(multidate_plans):
    """완전한 멀티데이트 계획으로부터 지원자 데이터 생성"""
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

def test_complete_ui_defaults():
    """완전한 UI 디폴트 설정으로 솔버 테스트"""
    print("\n🚀 완전한 UI 디폴트 설정으로 솔버 테스트...")
    
    try:
        config = create_complete_ui_default_data()
        
        # Core 모듈로 설정 빌드
        import core
        cfg = core.build_config(config)
        
        print(f"\n📋 설정 확인:")
        print(f"  - Activities: {len(cfg['activities'])} rows")
        print(f"  - Job mapping: {len(cfg['job_acts_map'])} rows")
        print(f"  - Room plan: {len(cfg['room_plan'])} rows")
        print(f"  - Operation window: {len(cfg['oper_window'])} rows")
        print(f"  - Candidates: {len(cfg['candidates_exp'])} rows")
        
        # 활동별 정보 확인
        print(f"\n🎯 활동 구성:")
        for _, row in cfg['activities'].iterrows():
            print(f"  {row['activity']}: {row['mode']}, {row['duration_min']}분, {row['min_cap']}-{row['max_cap']}명")
        
        # 방 정보 확인
        print(f"\n🏢 방 구성 (각 날짜별):")
        sample_room = cfg['room_plan'].iloc[0]
        for col in sample_room.index:
            if '_count' in col:
                room_type = col.replace('_count', '')
                count = int(sample_room[col])
                cap_col = f"{room_type}_cap"
                cap = int(sample_room.get(cap_col, 1))
                print(f"  {room_type}: {count}개, 수용인원 {cap}명")
        
        # 날짜별 지원자 분포 확인
        print(f"\n👥 날짜별 지원자 분포:")
        date_job_counts = cfg['candidates_exp'].groupby(['interview_date', 'code'])['id'].nunique().reset_index()
        
        # 날짜 형식 변환 처리
        try:
            date_job_counts['date_str'] = pd.to_datetime(date_job_counts['interview_date']).dt.strftime('%m/%d')
        except:
            # 이미 문자열이거나 다른 형식인 경우
            date_job_counts['date_str'] = date_job_counts['interview_date'].astype(str)
        
        for date_str in date_job_counts['date_str'].unique():
            date_data = date_job_counts[date_job_counts['date_str'] == date_str]
            job_list = []
            total_for_date = 0
            for _, row in date_data.iterrows():
                job_list.append(f"{row['code']}({row['id']}명)")
                total_for_date += row['id']
            print(f"  {date_str}: {', '.join(job_list)} = 총 {total_for_date}명")
        
        total_unique_candidates = cfg['candidates_exp']['id'].nunique()
        print(f"  📊 전체 합계: {total_unique_candidates}명")
        
        # 솔버 파라미터
        params = {
            "min_gap_min": config['global_gap_min'],
            "time_limit_sec": 120,  # 대규모 처리를 위해 충분한 시간
            "max_stay_hours": config['max_stay_hours'],
            "group_min_size": config['group_min_size'],
            "group_max_size": config['group_max_size']
        }
        
        print(f"\n⚙️ 솔버 파라미터:")
        for k, v in params.items():
            print(f"  {k}: {v}")
        
        # 계층적 스케줄러 v2로 멀티데이트 테스트
        print(f"\n🔥 계층적 스케줄러 v2로 멀티데이트 테스트...")
        
        from solver.api import solve_for_days_v2
        
        status, final_wide, logs, daily_limit = solve_for_days_v2(cfg, params, debug=True)
        
        print(f"\n📊 결과:")
        print(f"  Status: {status}")
        print(f"  Daily Limit: {daily_limit}")
        print(f"  Schedule Count: {len(final_wide) if final_wide is not None else 0}")
        
        if final_wide is not None and not final_wide.empty:
            print("✅ 완전한 UI 디폴트 설정 검증 성공!")
            
            # 상세 분석
            print(f"\n📈 멀티데이트 스케줄링 결과 분석:")
            print(f"  - 총 스케줄 항목: {len(final_wide)}개")
            
            # 지원자 수 분석
            if 'applicant_id' in final_wide.columns:
                scheduled_applicants = final_wide['applicant_id'].nunique()
                total_applicants = cfg['candidates_exp']['id'].nunique()
                success_rate = scheduled_applicants/total_applicants*100
                print(f"  - 스케줄된 지원자: {scheduled_applicants}/{total_applicants}명 ({success_rate:.1f}%)")
            
            # 날짜별 분석
            if 'interview_date' in final_wide.columns:
                date_counts = final_wide.groupby('interview_date')['applicant_id'].nunique() if 'applicant_id' in final_wide.columns else final_wide['interview_date'].value_counts()
                print(f"  - 날짜별 스케줄:")
                for date_val, count in date_counts.items():
                    if pd.notna(date_val):
                        try:
                            date_str = pd.to_datetime(date_val).strftime('%m/%d')
                        except:
                            date_str = str(date_val)
                        print(f"    {date_str}: {count}명")
            
            # 직무별 분석  
            if 'job_code' in final_wide.columns:
                job_counts = final_wide.groupby('job_code')['applicant_id'].nunique() if 'applicant_id' in final_wide.columns else final_wide['job_code'].value_counts()
                print(f"  - 직무별 스케줄:")
                for job_code, count in job_counts.items():
                    print(f"    {job_code}: {count}명")
            
            return True, final_wide
        else:
            print("❌ 완전한 UI 디폴트 설정 검증 실패")
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
    print("🧪 완전한 app.py UI 디폴트 설정 검증 테스트")
    print("🚀 4일간 멀티데이트, 11개 직무, 137명 지원자")
    print("=" * 80)
    
    # Core 모듈 임포트 테스트
    try:
        import core
        from solver.api import solve_for_days_v2
        print("✅ 모듈 임포트 성공")
    except Exception as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        return
    
    # 완전한 UI 디폴트 설정 테스트
    success, result = test_complete_ui_defaults()
    
    if success:
        print("\n🎉 완전한 UI 디폴트 설정 검증 성공!")
        
        # 결과 저장
        if result is not None:
            try:
                result_file = "complete_ui_defaults_test_result.xlsx"
                result.to_excel(result_file, index=False)
                print(f"✅ 결과 저장: {result_file}")
            except Exception as e:
                print(f"⚠️ 결과 저장 실패: {e}")
    else:
        print("\n❌ 완전한 UI 디폴트 설정 검증 실패")
    
    print("=" * 80)

if __name__ == "__main__":
    main() 