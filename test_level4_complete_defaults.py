#!/usr/bin/env python3
"""
Level 4 후처리 조정이 통합된 시스템으로 완전한 내부 디폴트 데이터 테스트
- 4일간 멀티데이트 (2025-07-01 ~ 2025-07-04)
- 11개 직무 (JOB01 ~ JOB11)
- 총 137명 지원자
- Level 4 후처리 조정 포함
"""

import pandas as pd
from datetime import date, time, datetime
import sys
import traceback
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_complete_ui_default_data():
    """완전한 UI 디폴트 데이터 생성"""
    print("🔧 완전한 UI 디폴트 데이터 생성 중...")
    
    # 1. 기본 활동 템플릿
    default_activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 2. 완전한 멀티 날짜 계획 (137명 총)
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

def test_level4_complete_defaults():
    """Level 4 후처리 조정이 통합된 시스템으로 완전한 디폴트 데이터 테스트"""
    print("=== Level 4 후처리 조정 + 완전한 내부 디폴트 데이터 테스트 ===")
    
    try:
        # 1. 완전한 디폴트 데이터 생성
        config = create_complete_ui_default_data()
        
        # 2. Core 모듈로 설정 빌드
        print(f"\n🔧 Core 모듈로 설정 빌드 중...")
        import core
        cfg = core.build_config(config)
        
        print(f"✅ 설정 빌드 완료")
        print(f"  - Activities: {len(cfg['activities'])} rows")
        print(f"  - Job mapping: {len(cfg['job_acts_map'])} rows")  
        print(f"  - Room plan: {len(cfg['room_plan'])} rows")
        print(f"  - Operation window: {len(cfg['oper_window'])} rows")
        print(f"  - Candidates: {len(cfg['candidates_exp'])} rows")
        
        # 3. 스케줄링 파라미터 설정
        params = {
            "min_gap_min": 5,
            "time_limit_sec": 300,  # 5분 제한 (대규모 데이터)
            "max_stay_hours": 8,
            "group_min_size": 4,
            "group_max_size": 6
        }
        
        print(f"\n⚙️ 스케줄링 파라미터:")
        for k, v in params.items():
            print(f"    {k}: {v}")
        
        # 4. Level 4 후처리 조정 포함 스케줄링 실행
        print(f"\n🚀 Level 4 후처리 조정 포함 스케줄링 시작...")
        start_time = datetime.now()
        
        from solver.api import solve_for_days_v2
        
        # API 호출 (params 딕셔너리 전달)
        status, schedule_df, logs, daily_limit = solve_for_days_v2(
            cfg,
            params=params,
            debug=True
        )
        
        # 결과 딕셔너리 생성
        result = {
            'status': status,
            'schedule': schedule_df,
            'logs': logs.split('\n') if logs else [],
            'message': logs if logs else '',
            'daily_limit': daily_limit
        }
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print(f"✅ 스케줄링 완료! (소요시간: {elapsed:.2f}초)")
        
        # 5. 결과 분석
        print(f"\n📊 결과 분석:")
        print(f"  - 상태: {result['status']}")
        print(f"  - 메시지: {result.get('message', 'N/A')}")
        
        if result['status'] == 'SUCCESS':
            schedule_df = result['schedule']
            
            # 컬럼 이름 확인 및 디버깅
            print(f"  - 스케줄 DataFrame 컬럼: {list(schedule_df.columns)}")
            
            # 기본 통계 (컬럼 이름 확인 후 적절히 수정)
            print(f"  - 총 스케줄 항목: {len(schedule_df)}개")
            
            # 컬럼 이름 매핑 (가능한 후보들)
            candidate_col = None
            date_col = None
            job_col = None
            
            for col in schedule_df.columns:
                if 'candidate' in col.lower() or 'applicant' in col.lower() or 'id' in col.lower():
                    candidate_col = col
                elif 'date' in col.lower():
                    date_col = col
                elif 'job' in col.lower():
                    job_col = col
            
            if candidate_col:
                print(f"  - 총 지원자: {schedule_df[candidate_col].nunique()}명")
            if date_col:
                print(f"  - 총 날짜: {schedule_df[date_col].nunique()}일")
            if job_col:
                print(f"  - 총 직무: {schedule_df[job_col].nunique()}개")
            
            # 날짜별 분포
            if date_col:
                print(f"\n📅 날짜별 스케줄 분포:")
                date_counts = schedule_df.groupby(date_col).size().sort_index()
                for date_str, count in date_counts.items():
                    print(f"    {date_str}: {count}개 항목")
            
            # 활동별 분포 (activity 컬럼 확인)
            activity_col = None
            for col in schedule_df.columns:
                if 'activity' in col.lower():
                    activity_col = col
                    break
            
            if activity_col:
                print(f"\n🎯 활동별 스케줄 분포:")
                activity_counts = schedule_df.groupby(activity_col).size()
                for activity, count in activity_counts.items():
                    print(f"    {activity}: {count}개 항목")
            
            # 체류시간 분석
            print(f"\n⏱️ 체류시간 분석:")
            
            # 시간 관련 컬럼 찾기
            start_col = None
            end_col = None
            for col in schedule_df.columns:
                if 'start' in col.lower() and 'time' in col.lower():
                    start_col = col
                elif 'end' in col.lower() and 'time' in col.lower():
                    end_col = col
            
            if candidate_col and start_col and end_col:
                stay_times = []
                
                for candidate_id in schedule_df[candidate_col].unique():
                    candidate_schedule = schedule_df[schedule_df[candidate_col] == candidate_id]
                    if len(candidate_schedule) > 0:
                        start_time = candidate_schedule[start_col].min()
                        end_time = candidate_schedule[end_col].max()
                        
                        # 시간 타입 확인 및 변환
                        if pd.api.types.is_datetime64_any_dtype(start_time):
                            # 이미 datetime이면 그대로 사용
                            stay_duration = (end_time - start_time).total_seconds() / 3600
                        else:
                            # 문자열이면 datetime으로 변환
                            try:
                                start_dt = pd.to_datetime(start_time)
                                end_dt = pd.to_datetime(end_time)
                                stay_duration = (end_dt - start_dt).total_seconds() / 3600
                            except:
                                # 변환 실패시 0으로 처리
                                stay_duration = 0
                                
                        stay_times.append(stay_duration)
                
                if stay_times:
                    avg_stay = sum(stay_times) / len(stay_times)
                    max_stay = max(stay_times)
                    min_stay = min(stay_times)
                    
                    print(f"    평균 체류시간: {avg_stay:.2f}시간")
                    print(f"    최대 체류시간: {max_stay:.2f}시간")
                    print(f"    최소 체류시간: {min_stay:.2f}시간")
                    
                    # 긴 체류시간 지원자 분석
                    long_stay_candidates = [
                        (candidate_id, stay_time) 
                        for candidate_id, stay_time in zip(schedule_df[candidate_col].unique(), stay_times)
                        if stay_time > 6
                    ]
                    
                    if long_stay_candidates:
                        print(f"    6시간 이상 체류 지원자: {len(long_stay_candidates)}명")
                        for candidate_id, stay_time in long_stay_candidates[:5]:  # 상위 5명만 출력
                            print(f"      {candidate_id}: {stay_time:.2f}시간")
                    else:
                        print(f"    6시간 이상 체류 지원자: 0명")
                else:
                    print(f"    체류시간 분석 불가: 시간 데이터 없음")
            else:
                print(f"    체류시간 분석 불가: 필요한 컬럼 없음 (candidate: {candidate_col}, start: {start_col}, end: {end_col})")
            
            # Level 4 후처리 조정 결과 확인
            print(f"\n🔧 Level 4 후처리 조정 결과:")
            level4_logs = result.get('logs', [])
            level4_applied = False
            
            for log in level4_logs:
                if 'Level 4' in log:
                    print(f"    {log}")
                    if 'groups moved' in log or 'optimized' in log:
                        level4_applied = True
            
            if level4_applied:
                print(f"    ✅ Level 4 후처리 조정이 적용되었습니다!")
            else:
                print(f"    ℹ️ Level 4 후처리 조정이 불필요하다고 판단되었습니다.")
                
        else:
            print(f"❌ 스케줄링 실패: {result.get('message', 'Unknown error')}")
            
            # 오류 로그 출력
            if 'logs' in result:
                print(f"\n📋 오류 로그:")
                for log in result['logs'][-10:]:  # 마지막 10개 로그만 출력
                    print(f"    {log}")
        
        print(f"\n🎉 Level 4 후처리 조정 + 완전한 내부 디폴트 데이터 테스트 완료!")
        
        return result
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        print(f"📋 상세 오류:")
        traceback.print_exc()
        return None

def main():
    """메인 함수"""
    print("Level 4 후처리 조정이 통합된 시스템으로 완전한 내부 디폴트 데이터 테스트")
    print("=" * 80)
    
    result = test_level4_complete_defaults()
    
    if result and result['status'] == 'SUCCESS':
        print("\n🎉 테스트 성공! Level 4 후처리 조정이 통합된 시스템이 완전한 내부 디폴트 데이터로 정상 작동합니다.")
    else:
        print("\n⚠️ 테스트 실패 또는 오류 발생. 개선작업이 필요합니다.")

if __name__ == "__main__":
    main() 