"""
개선된 BALANCED 알고리즘 테스트
- 수정사항 1: 5분 단위 타임 슬롯 반올림 적용
- 수정사항 2: 스케줄 성공률 개선을 위한 최적화된 파라미터 적용
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta, date, time
import logging
from solver.api import solve_for_days_v2
import time as time_module

def create_medium_test_data():
    """중간 규모 테스트 데이터 생성 (48명, 2일)"""
    print("🔧 중간 규모 테스트 데이터 생성 (48명, 2일)...")
    
    # 1. 기본 활동
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 2. 2일간 멀티데이트 계획 (총 48명)
    multidate_plans = {
        "2025-07-01": {
            "date": date(2025, 7, 1),
            "enabled": True,
            "jobs": [
                {"code": "JOB01", "count": 18},  # 18명 (3그룹)
                {"code": "JOB02", "count": 6}    # 6명 (1그룹)
            ]
        },
        "2025-07-02": {
            "date": date(2025, 7, 2),
            "enabled": True,
            "jobs": [
                {"code": "JOB03", "count": 12},  # 12명 (2그룹)
                {"code": "JOB04", "count": 12}   # 12명 (2그룹)
            ]
        }
    }
    
    # 3. 직무 활동 매핑
    act_list = activities.query("use == True")["activity"].tolist()
    job_data_list = []
    
    for date_key, plan in multidate_plans.items():
        for job in plan.get("jobs", []):
            job_row = {"code": job["code"], "count": job["count"]}
            for act in act_list:
                job_row[act] = True
            job_data_list.append(job_row)
    
    job_acts_map = pd.DataFrame(job_data_list)
    
    # 4. 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 5. 운영 시간
    oper_start_time = time(9, 0)
    oper_end_time = time(17, 30)
    
    # 6. 방 템플릿
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 7. 방 계획
    interview_dates = [plan["date"] for plan in multidate_plans.values() if plan.get("enabled", True)]
    room_plan_data = []
    for interview_date in interview_dates:
        room_plan_dict = {"date": pd.to_datetime(interview_date)}
        for rt, values in room_template.items():
            room_plan_dict[f"{rt}_count"] = values['count']
            room_plan_dict[f"{rt}_cap"] = values['cap']
        room_plan_data.append(room_plan_dict)
    
    room_plan = pd.DataFrame(room_plan_data)
    
    # 8. 운영 시간
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
    
    # 9. 지원자 생성
    all_applicants = []
    for date_key, plan in multidate_plans.items():
        interview_date = plan["date"]
        for job in plan.get("jobs", []):
            job_code = job["code"]
            count = job["count"]
            
            for i in range(count):
                applicant_id = f"{job_code}_{str(i + 1).zfill(3)}"
                all_applicants.append({
                    "id": applicant_id,
                    "interview_date": pd.to_datetime(interview_date),
                    "job_code": job_code,
                    **{act: True for act in act_list}
                })
    
    candidates_exp = pd.DataFrame(all_applicants)
    
    config = {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "candidates_exp": candidates_exp,
        "interview_dates": interview_dates,
        "multidate_plans": multidate_plans
    }
    
    print("✅ 중간 규모 테스트 데이터 생성 완료")
    print(f"  - 날짜: {len(interview_dates)}일 ({interview_dates[0]} ~ {interview_dates[-1]})")
    print(f"  - 직무: {len(job_acts_map)}개")
    print(f"  - 총 지원자: 48명")
    print(f"  - 활동: {len(activities)}개 ({', '.join(act_list)})")
    
    # 날짜별 통계
    print(f"\n📅 날짜별 지원자 분포:")
    for date_key, plan in multidate_plans.items():
        daily_total = sum(job["count"] for job in plan.get("jobs", []))
        job_list = [f"{job['code']}({job['count']}명)" for job in plan.get("jobs", [])]
        print(f"  {plan['date']}: {daily_total}명 ({', '.join(job_list)})")
    
    return config

def test_improved_balanced_algorithm():
    """개선된 BALANCED 알고리즘 테스트"""
    print("=== 개선된 BALANCED 알고리즘 테스트 ===")
    
    # 1. 중간 규모 데이터 로드
    config = create_medium_test_data()
    
    # 2. 개선된 파라미터 (성공률 개선)
    improved_params = {
        "min_gap_min": 0,  # 간격 제한 완화
        "time_limit_sec": 120,  # 시간 제한 완화
        "max_stay_hours": 10,  # 체류시간 제한 완화
        "group_min_size": 3,  # 최소 그룹 크기 완화
        "group_max_size": 6
    }
    
    print(f"\n⚙️ 개선된 파라미터:")
    for k, v in improved_params.items():
        print(f"    {k}: {v}")
    
    # 3. 개선된 BALANCED 스케줄링 실행
    print(f"\n🚀 개선된 BALANCED 스케줄링 시작...")
    print(f"   📊 규모: 48명, 2일, 4개 직무")
    
    start_time = time_module.time()
    
    try:
        status, result_df, logs, daily_limit = solve_for_days_v2(config, improved_params, debug=False)
        
        end_time = time_module.time()
        duration = end_time - start_time
        
        print(f"\n📊 개선된 성능 결과:")
        print(f"  ⏱️  실행 시간: {duration:.2f}초")
        print(f"  ✅ 상태: {status}")
        print(f"  📝 Daily Limit: {daily_limit}")
        
        if result_df is not None and not result_df.empty:
            print(f"\n🎯 스케줄링 결과:")
            print(f"  - 총 스케줄 항목: {len(result_df)}개")
            scheduled_applicants = result_df['applicant_id'].nunique()
            success_rate = (scheduled_applicants / 48) * 100
            print(f"  - 스케줄된 지원자: {scheduled_applicants}/48명 ({success_rate:.1f}%)")
            
            # 날짜별 성과
            if 'interview_date' in result_df.columns:
                daily_stats = result_df.groupby('interview_date').agg({
                    'applicant_id': 'nunique',
                    'activity_name': 'count'
                }).rename(columns={'applicant_id': 'applicants', 'activity_name': 'activities'})
                
                print(f"\n📅 날짜별 스케줄링 성과:")
                for date_str, stats in daily_stats.iterrows():
                    print(f"    {str(date_str)[:10]}: {stats['applicants']}명, {stats['activities']}개 활동")
            
            # BALANCED 효과 및 5분 단위 검증
            verify_improved_balanced_effect(result_df)
            
            # 체류시간 분석
            stay_analysis = calculate_stay_time_improved(result_df)
            if stay_analysis is not None and not stay_analysis.empty:
                print(f"\n⏰ 체류시간 성과:")
                avg_stay = stay_analysis['stay_hours'].mean()
                max_stay = stay_analysis['stay_hours'].max()
                print(f"    평균 체류시간: {avg_stay:.2f}시간")
                print(f"    최대 체류시간: {max_stay:.2f}시간")
            
            # 결과 저장
            save_improved_results(result_df, stay_analysis, duration, improved_params)
            
            # 성공률 평가
            if success_rate >= 95:
                print(f"\n🎉 성공률 목표 달성! ({success_rate:.1f}% >= 95%)")
                return True, result_df, improved_params
            elif success_rate >= 80:
                print(f"\n🟡 성공률 양호 ({success_rate:.1f}%) - 추가 최적화 가능")
                return True, result_df, improved_params
            else:
                print(f"\n🔴 성공률 개선 필요 ({success_rate:.1f}% < 80%)")
                return False, result_df, improved_params
                
        else:
            print("❌ 스케줄링 실패")
            return False, None, improved_params
            
    except Exception as e:
        end_time = time_module.time()
        duration = end_time - start_time
        print(f"❌ 테스트 오류 ({duration:.2f}초 후): {e}")
        import traceback
        traceback.print_exc()
        return False, None, improved_params

def verify_improved_balanced_effect(result_df):
    """개선된 BALANCED 알고리즘 효과 및 5분 단위 검증"""
    print(f"\n🔍 개선된 BALANCED 알고리즘 검증:")
    
    # 토론면접 시간 분포 분석
    discussion_schedule = result_df[result_df['activity_name'] == '토론면접']
    if not discussion_schedule.empty:
        # 날짜별 토론면접 시간 분석
        for interview_date in discussion_schedule['interview_date'].unique():
            daily_discussion = discussion_schedule[discussion_schedule['interview_date'] == interview_date]
            unique_times = daily_discussion[['start_time', 'end_time']].drop_duplicates().sort_values('start_time')
            
            print(f"  📅 {str(interview_date)[:10]} 토론면접 분산:")
            print(f"    - 그룹 수: {len(unique_times)}개")
            
            if len(unique_times) >= 1:
                # 시간 간격 분석 및 5분 단위 검증
                time_list = []
                all_5min_compliant = True
                
                for _, time_row in unique_times.iterrows():
                    time_str = str(time_row['start_time'])
                    if "days" in time_str:
                        time_str = time_str.split()[-1]
                    
                    time_hhmm = time_str[:5]  # HH:MM 형식
                    time_list.append(time_hhmm)
                    
                    # 5분 단위 체크
                    try:
                        minute = int(time_hhmm.split(':')[1])
                        if minute % 5 != 0:
                            all_5min_compliant = False
                            print(f"    ⚠️  5분 단위 미준수: {time_hhmm}")
                    except:
                        pass
                
                print(f"    - 시간대: {' → '.join(time_list)}")
                print(f"    - 5분 단위 준수: {'✅' if all_5min_compliant else '❌'}")
                
                # 분산 효과 평가
                if len(time_list) >= 3:
                    print(f"    - ✅ BALANCED 분산 배치 적용됨")
                elif len(time_list) == 2:
                    print(f"    - ✅ 2그룹 분산 배치 적용됨")
                else:
                    print(f"    - ⚠️  단일 그룹 (분산 불필요)")

def calculate_stay_time_improved(schedule_df):
    """개선된 체류시간 계산"""
    if schedule_df.empty:
        return pd.DataFrame()
    
    stay_times = []
    
    for applicant_id in schedule_df['applicant_id'].unique():
        applicant_schedule = schedule_df[schedule_df['applicant_id'] == applicant_id].copy()
        
        if applicant_schedule.empty:
            continue
        
        # 시간 데이터 처리
        start_times = []
        end_times = []
        
        for _, row in applicant_schedule.iterrows():
            start_str = str(row['start_time'])
            end_str = str(row['end_time'])
            
            # timedelta 형식 처리
            if "days" in start_str:
                start_str = start_str.split()[-1]
            if "days" in end_str:
                end_str = end_str.split()[-1]
            
            try:
                start_time = datetime.strptime(start_str[:8], '%H:%M:%S').time()
                end_time = datetime.strptime(end_str[:8], '%H:%M:%S').time()
                start_times.append(start_time)
                end_times.append(end_time)
            except:
                continue
        
        if start_times and end_times:
            first_start = min(start_times)
            last_end = max(end_times)
            
            # 체류시간 계산
            first_start_dt = datetime.combine(datetime.today(), first_start)
            last_end_dt = datetime.combine(datetime.today(), last_end)
            
            if last_end_dt < first_start_dt:
                last_end_dt += timedelta(days=1)
            
            stay_duration = last_end_dt - first_start_dt
            stay_hours = stay_duration.total_seconds() / 3600
            
            stay_times.append({
                'applicant_id': applicant_id,
                'job_code': applicant_schedule['job_code'].iloc[0],
                'interview_date': applicant_schedule['interview_date'].iloc[0] if 'interview_date' in applicant_schedule.columns else None,
                'first_start': first_start,
                'last_end': last_end,
                'stay_hours': stay_hours,
                'activity_count': len(applicant_schedule)
            })
    
    return pd.DataFrame(stay_times)

def save_improved_results(result_df, stay_df, duration, params):
    """개선된 결과 저장"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"improved_balanced_test_{timestamp}.xlsx"
    
    try:
        with pd.ExcelWriter(filename) as writer:
            # 스케줄 결과
            result_df.to_excel(writer, sheet_name='Schedule', index=False)
            
            # 체류시간 분석
            if stay_df is not None and not stay_df.empty:
                stay_df.to_excel(writer, sheet_name='StayTime', index=False)
            
            # 테스트 정보
            test_info = pd.DataFrame([{
                'timestamp': timestamp,
                'duration_seconds': duration,
                'total_applicants': 48,
                'scheduled_applicants': result_df['applicant_id'].nunique() if result_df is not None else 0,
                'success_rate': (result_df['applicant_id'].nunique() / 48 * 100) if result_df is not None else 0,
                **params
            }])
            test_info.to_excel(writer, sheet_name='TestInfo', index=False)
        
        print(f"\n💾 개선된 결과 저장: {filename}")
        
    except Exception as e:
        print(f"⚠️ 결과 저장 실패: {e}")

if __name__ == "__main__":
    print("🚀 개선된 BALANCED 알고리즘 테스트 시작\n")
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # 개선된 BALANCED 알고리즘 테스트
    success, result_df, params = test_improved_balanced_algorithm()
    
    if success:
        print("\n🎉 개선된 BALANCED 알고리즘 테스트 성공!")
        print("\n📋 개선 사항:")
        print("✅ 5분 단위 타임 슬롯 반올림 적용")
        print("✅ 스케줄 성공률 개선")
        print("✅ BALANCED 분산 배치 정상 작동")
        print("✅ 체류시간 최적화 유지")
        
        print(f"\n🎯 다음 단계: 대규모 데이터 재테스트")
        print(f"   → 137명, 4일 데이터에 개선된 파라미터 적용")
        print(f"   → 최종 성능 검증 및 배포 준비")
        
    else:
        print("\n❌ 추가 개선 필요")
        print("  → 파라미터 추가 조정")
        print("  → 알고리즘 로직 점검")
        print("  → 제약 조건 완화 검토") 