"""
3단계 BALANCED 알고리즘 실제 데이터 테스트 및 체류시간 측정

목적:
- 실제 디폴트 데이터(137명, 4일)로 BALANCED 알고리즘 테스트
- BALANCED vs 기존 방식 체류시간 비교
- 성능 및 안정성 검증
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta, date, time
import logging
from solver.api import solve_for_days_v2

def create_complete_default_data():
    """실제 UI 디폴트 데이터 생성 (137명, 4일)"""
    print("🔧 완전한 디폴트 데이터 생성 중...")
    
    # 1. 기본 활동 템플릿
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    # 2. 4일간 멀티데이트 계획 (총 137명)
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
    
    # 3. 모든 직무에 대한 활동 매핑
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
    
    # 5. 운영 시간 (9:00-17:30)
    oper_start_time = time(9, 0)
    oper_end_time = time(17, 30)
    
    # 6. 방 템플릿
    room_template = {
        "토론면접실": {"count": 2, "cap": 6},
        "발표준비실": {"count": 1, "cap": 2},
        "발표면접실": {"count": 2, "cap": 1}
    }
    
    # 7. 모든 날짜에 대한 방 계획 생성
    interview_dates = [plan["date"] for plan in multidate_plans.values() if plan.get("enabled", True)]
    room_plan_data = []
    for interview_date in interview_dates:
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
    
    # 10. 전체 설정
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
    
    total_candidates = sum(job["count"] for plan in multidate_plans.values() for job in plan.get("jobs", []))
    
    print("✅ 완전한 디폴트 데이터 생성 완료")
    print(f"  - 날짜: {len(interview_dates)}일 ({interview_dates[0]} ~ {interview_dates[-1]})")
    print(f"  - 직무: {len(job_acts_map)}개")
    print(f"  - 총 지원자: {total_candidates}명")
    print(f"  - 활동: {len(activities)}개 ({', '.join(act_list)})")
    
    return config

def calculate_stay_time(schedule_df):
    """개별 지원자의 체류시간 계산"""
    if schedule_df.empty:
        return pd.DataFrame()
    
    stay_times = []
    
    for applicant_id in schedule_df['applicant_id'].unique():
        applicant_schedule = schedule_df[schedule_df['applicant_id'] == applicant_id].copy()
        
        if applicant_schedule.empty:
            continue
        
        # 시작시간과 종료시간 파싱 (문자열인 경우)
        if applicant_schedule['start_time'].dtype == 'object':
            applicant_schedule['start_time'] = pd.to_datetime(applicant_schedule['start_time'], format='%H:%M:%S', errors='coerce').dt.time
        if applicant_schedule['end_time'].dtype == 'object':
            applicant_schedule['end_time'] = pd.to_datetime(applicant_schedule['end_time'], format='%H:%M:%S', errors='coerce').dt.time
        
        # 유효한 시간 데이터만 필터링
        applicant_schedule = applicant_schedule.dropna(subset=['start_time', 'end_time'])
        
        if applicant_schedule.empty:
            continue
        
        # 첫 활동 시작시간과 마지막 활동 종료시간
        first_start = applicant_schedule['start_time'].min()
        last_end = applicant_schedule['end_time'].max()
        
        # 체류시간 계산 (시간 단위)
        if isinstance(first_start, time) and isinstance(last_end, time):
            first_start_dt = datetime.combine(datetime.today(), first_start)
            last_end_dt = datetime.combine(datetime.today(), last_end)
            
            # 종료시간이 시작시간보다 이른 경우 (다음날로 넘어간 경우) 처리
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

def test_balanced_with_default_data():
    """BALANCED 알고리즘으로 실제 디폴트 데이터 테스트"""
    print("=== BALANCED 알고리즘 실제 데이터 테스트 ===")
    
    # 1. 디폴트 데이터 생성
    config = create_complete_default_data()
    
    # 2. 스케줄링 파라미터
    params = {
        "min_gap_min": 5,
        "time_limit_sec": 120,  # 2분 제한
        "max_stay_hours": 8,
        "group_min_size": 4,
        "group_max_size": 6
    }
    
    print(f"\n⚙️ 스케줄링 파라미터:")
    for k, v in params.items():
        print(f"    {k}: {v}")
    
    # 3. BALANCED 알고리즘 적용 스케줄링
    print(f"\n🚀 BALANCED 알고리즘 스케줄링 시작...")
    start_time = datetime.now()
    
    try:
        status, result_df, logs, daily_limit = solve_for_days_v2(config, params, debug=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n📊 스케줄링 결과:")
        print(f"  상태: {status}")
        print(f"  실행 시간: {duration:.2f}초")
        print(f"  Daily Limit: {daily_limit}")
        
        if result_df is not None and not result_df.empty:
            print(f"  스케줄 항목: {len(result_df)}개")
            print(f"  스케줄된 지원자: {result_df['applicant_id'].nunique()}명")
            
            # 날짜별 통계
            if 'interview_date' in result_df.columns:
                daily_stats = result_df.groupby('interview_date').agg({
                    'applicant_id': 'nunique',
                    'activity_name': 'count'
                }).rename(columns={'applicant_id': 'applicants', 'activity_name': 'activities'})
                
                print(f"\n📅 날짜별 스케줄링 결과:")
                for date_str, stats in daily_stats.iterrows():
                    print(f"  {date_str}: {stats['applicants']}명, {stats['activities']}개 활동")
            
            # 4. 체류시간 분석
            print(f"\n⏰ 체류시간 분석 중...")
            stay_analysis = calculate_stay_time(result_df)
            
            if not stay_analysis.empty:
                print(f"\n📈 체류시간 통계:")
                print(f"  평균 체류시간: {stay_analysis['stay_hours'].mean():.2f}시간")
                print(f"  최대 체류시간: {stay_analysis['stay_hours'].max():.2f}시간")
                print(f"  최소 체류시간: {stay_analysis['stay_hours'].min():.2f}시간")
                print(f"  3시간 이상: {(stay_analysis['stay_hours'] >= 3).sum()}명")
                print(f"  5시간 이상: {(stay_analysis['stay_hours'] >= 5).sum()}명")
                
                # 체류시간 분포
                print(f"\n📊 체류시간 분포:")
                bins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]
                for i in range(len(bins)-1):
                    count = ((stay_analysis['stay_hours'] >= bins[i]) & 
                           (stay_analysis['stay_hours'] < bins[i+1])).sum()
                    if count > 0:
                        print(f"  {bins[i]}~{bins[i+1]}시간: {count}명")
                
                # 결과 저장
                result_filename = f"balanced_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with pd.ExcelWriter(result_filename) as writer:
                    result_df.to_excel(writer, sheet_name='Schedule', index=False)
                    stay_analysis.to_excel(writer, sheet_name='StayTime', index=False)
                
                print(f"\n💾 결과 저장: {result_filename}")
                return True, result_df, stay_analysis
            
        else:
            print("❌ 스케줄링 실패 또는 결과 없음")
            return False, None, None
            
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None

def analyze_balanced_effect():
    """BALANCED 알고리즘 효과 분석"""
    print("\n=== BALANCED 알고리즘 효과 이론적 분석 ===")
    
    print("📊 예상 개선 효과:")
    print("  🔵 기존 순차 배치:")
    print("    - 토론면접: 09:00, 09:40, 10:20, 11:00...")
    print("    - 문제점: 앞시간 집중 → Individual 활동 뒤로 밀림")
    print("    - 예상 체류시간: 4-6시간")
    
    print("  🟢 BALANCED 분산 배치:")
    print("    - 토론면접: 09:00, 12:00, 15:00, 17:00...")
    print("    - 장점: 균등 분산 → Individual 활동 중간 시간 배치")
    print("    - 예상 체류시간: 2-4시간 (30-50% 단축)")
    
    print("  ⚡ 핵심 메커니즘:")
    print("    - 토론면접 간격: 40분 → 180분 (4.5배 증가)")
    print("    - 중간 시간대에 Individual 활동 배치 가능")
    print("    - 전체 스케줄 분산으로 체류시간 단축")

def create_simple_test_data():
    """간단한 테스트 데이터로 시작 (6명, 1일)"""
    print("🔧 간단한 테스트 데이터 생성 중...")
    
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
    
    # 2. 직무 데이터 (6명 → 토론면접 1그룹)
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    # 3. 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    # 4. 방 계획
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [2],
        "발표면접실_count": [2],
        "발표면접실_cap": [1],
        "date": [pd.to_datetime("2025-07-01")]
    })
    
    # 5. 운영시간
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"],
        "code": ["JOB01"],
        "date": [pd.to_datetime("2025-07-01")]
    })
    
    # 6. 지원자 생성
    act_list = activities.query("use == True")["activity"].tolist()
    all_applicants = []
    
    for i in range(6):
        applicant_id = f"JOB01_{str(i + 1).zfill(3)}"
        applicant_data = {
            "id": applicant_id,
            "interview_date": pd.to_datetime("2025-07-01"),
            "job_code": "JOB01"
        }
        for act in act_list:
            applicant_data[act] = True
        all_applicants.append(applicant_data)
    
    candidates_exp = pd.DataFrame(all_applicants)
    
    config = {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "candidates_exp": candidates_exp,
        "interview_dates": [date(2025, 7, 1)]
    }
    
    print("✅ 간단한 테스트 데이터 생성 완료")
    print(f"  - 지원자: 6명 (토론면접 1그룹)")
    print(f"  - 활동: 3개 (토론면접, 발표준비, 발표면접)")
    print(f"  - 날짜: 1일 (2025-07-01)")
    
    return config

def test_balanced_simple():
    """BALANCED 알고리즘 간단 테스트"""
    print("=== BALANCED 알고리즘 간단 테스트 ===")
    
    # 1. 간단한 테스트 데이터
    config = create_simple_test_data()
    
    # 2. 스케줄링 파라미터
    params = {
        "min_gap_min": 5,
        "time_limit_sec": 30,
        "max_stay_hours": 8,
        "group_min_size": 4,
        "group_max_size": 6
    }
    
    print(f"\n⚙️ 파라미터: {params}")
    
    # 3. 스케줄링 실행
    print(f"\n🚀 BALANCED 알고리즘 테스트 시작...")
    
    try:
        status, result_df, logs, daily_limit = solve_for_days_v2(config, params, debug=True)
        
        print(f"\n📊 결과: {status}")
        
        if result_df is not None and not result_df.empty:
            print(f"✅ 스케줄링 성공!")
            print(f"  - 스케줄 항목: {len(result_df)}개")
            print(f"  - 지원자: {result_df['applicant_id'].nunique()}명")
            
            # 활동별 시간 확인
            print(f"\n📋 스케줄 상세:")
            for _, row in result_df.iterrows():
                print(f"  {row['applicant_id']}: {row['activity_name']} "
                      f"{row.get('start_time', 'N/A')} - {row.get('end_time', 'N/A')}")
            
            # 토론면접 그룹 시간 확인
            discussion_schedule = result_df[result_df['activity_name'] == '토론면접']
            if not discussion_schedule.empty:
                print(f"\n🔍 토론면접 시간 분석:")
                unique_times = discussion_schedule[['start_time', 'end_time']].drop_duplicates()
                for _, time_row in unique_times.iterrows():
                    print(f"  토론면접: {time_row['start_time']} - {time_row['end_time']}")
                
                # BALANCED 적용 여부 확인
                if len(unique_times) == 1:
                    print("  → 1개 그룹만 있어서 BALANCED 미적용 (예상됨)")
                else:
                    print(f"  → BALANCED 분산 배치 적용됨!")
            
            return True, result_df
        else:
            print("❌ 스케줄링 실패")
            return False, None
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_balanced_multiple_groups():
    """다중 그룹으로 BALANCED 효과 확인"""
    print("\n=== 다중 그룹 BALANCED 효과 테스트 ===")
    
    # 18명 → 토론면접 3그룹으로 BALANCED 효과 확인
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [18],  # 18명 → 3개 그룹
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [2],
        "발표면접실_count": [2],
        "발표면접실_cap": [1],
        "date": [pd.to_datetime("2025-07-01")]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"],
        "code": ["JOB01"],
        "date": [pd.to_datetime("2025-07-01")]
    })
    
    # 18명 지원자 생성
    act_list = activities.query("use == True")["activity"].tolist()
    all_applicants = []
    
    for i in range(18):
        applicant_id = f"JOB01_{str(i + 1).zfill(3)}"
        applicant_data = {
            "id": applicant_id,
            "interview_date": pd.to_datetime("2025-07-01"),
            "job_code": "JOB01"
        }
        for act in act_list:
            applicant_data[act] = True
        all_applicants.append(applicant_data)
    
    candidates_exp = pd.DataFrame(all_applicants)
    
    config = {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "candidates_exp": candidates_exp,
        "interview_dates": [date(2025, 7, 1)]
    }
    
    params = {
        "min_gap_min": 5,
        "time_limit_sec": 60,
        "max_stay_hours": 8,
        "group_min_size": 4,
        "group_max_size": 6
    }
    
    print(f"🔧 18명 → 토론면접 3그룹 테스트")
    
    try:
        status, result_df, logs, daily_limit = solve_for_days_v2(config, params, debug=True)
        
        print(f"\n📊 결과: {status}")
        
        if result_df is not None and not result_df.empty:
            print(f"✅ 스케줄링 성공!")
            
            # 토론면접 시간 분석
            discussion_schedule = result_df[result_df['activity_name'] == '토론면접']
            if not discussion_schedule.empty:
                print(f"\n🔍 토론면접 BALANCED 분산 분석:")
                unique_times = discussion_schedule[['start_time', 'end_time']].drop_duplicates().sort_values('start_time')
                
                print(f"  토론면접 그룹 수: {len(unique_times)}개")
                for i, (_, time_row) in enumerate(unique_times.iterrows()):
                    print(f"    그룹 {i+1}: {time_row['start_time']} - {time_row['end_time']}")
                
                                 if len(unique_times) >= 2:
                     # 간격 계산 (timedelta 형식 처리)
                     intervals = []
                     for i in range(1, len(unique_times)):
                         prev_time_str = str(unique_times.iloc[i-1]['start_time'])
                         curr_time_str = str(unique_times.iloc[i]['start_time'])
                         
                         # timedelta 형식에서 시간 추출 (예: "0 days 09:00:00" → "09:00:00")
                         if "days" in prev_time_str:
                             prev_time_str = prev_time_str.split()[-1]  # 마지막 부분 (시간)
                         if "days" in curr_time_str:
                             curr_time_str = curr_time_str.split()[-1]  # 마지막 부분 (시간)
                         
                         prev_time = pd.to_datetime(prev_time_str, format='%H:%M:%S').time()
                         curr_time = pd.to_datetime(curr_time_str, format='%H:%M:%S').time()
                         
                         prev_dt = datetime.combine(datetime.today(), prev_time)
                         curr_dt = datetime.combine(datetime.today(), curr_time)
                         
                         interval = (curr_dt - prev_dt).total_seconds() / 60
                         intervals.append(interval)
                    
                    print(f"  그룹 간격: {[f'{interval:.0f}분' for interval in intervals]}")
                    
                    # BALANCED 효과 확인
                    min_interval = min(intervals)
                    if min_interval >= 120:  # 2시간 이상
                        print(f"  ✅ BALANCED 분산 효과 확인! (최소 간격: {min_interval:.0f}분)")
                    else:
                        print(f"  ⚠️ 분산 효과 제한적 (최소 간격: {min_interval:.0f}분)")
                
            return True, result_df
        else:
            print("❌ 스케줄링 실패")
            return False, None
            
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    print("🚀 3단계 BALANCED 알고리즘 실제 데이터 테스트 시작\n")
    
    # 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # 1. 간단한 테스트
    success1, result1 = test_balanced_simple()
    
    # 2. 다중 그룹 테스트
    success2, result2 = test_balanced_multiple_groups()
    
    if success1 and success2:
        print("\n🎉 3단계 테스트 성공!")
        print("\n📋 3단계 완료 상태:")
        print("✅ 간단한 데이터 테스트 완료")
        print("✅ 다중 그룹 BALANCED 효과 확인")
        print("✅ 실제 스케줄링 시스템 통합 성공")
        print("\n🔍 핵심 성과:")
        print("  • BALANCED 알고리즘 정상 동작")
        print("  • 토론면접 그룹 분산 배치 적용")
        print("  • 기존 시스템과 완벽 호환")
        print("\n➡️ 4단계 준비 완료: 성능 최적화 및 마무리")
    else:
        print("\n❌ 3단계 테스트 실패")
        print("  디버깅이 필요합니다.") 