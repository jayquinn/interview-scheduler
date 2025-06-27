import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def analyze_scheduling_problem():
    print("=== 🔍 스케줄링 문제 근본 원인 분석 ===")
    
    # 디폴트 설정
    activities = pd.DataFrame({
        "use": [True, True, True],
        "activity": ["토론면접", "발표준비", "발표면접"],
        "mode": ["batched", "parallel", "individual"],
        "duration_min": [30, 5, 15],
        "room_type": ["토론면접실", "발표준비실", "발표면접실"],
        "min_cap": [4, 1, 1],
        "max_cap": [6, 2, 1],
    })
    
    room_plan = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [1],
        "발표준비실_cap": [2],
        "발표면접실_count": [2],
        "발표면접실_cap": [1]
    })
    
    oper_window = pd.DataFrame({
        "start_time": ["09:00"],
        "end_time": ["17:30"]
    })
    
    precedence = pd.DataFrame([
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 5, "adjacent": True}
    ])
    
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    cfg_ui = {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }
    
    print("\n=== 📊 현재 제약 조건 분석 ===")
    print(f"지원자 수: {job_acts_map['count'].sum()}명")
    print(f"토론면접: 30분, batched, 방 2개(각 6명)")
    print(f"발표준비: 5분, parallel, 방 1개(2명)")
    print(f"발표면접: 15분, individual, 방 2개(각 1명)")
    print(f"선후행: 발표준비 → 5분 → 발표면접 (adjacent=True)")
    
    # 이론적 분석
    print(f"\n=== 🧮 이론적 스케줄링 분석 ===")
    
    # 토론면접 분석
    discussion_groups = 6 // 6  # 6명을 6명씩 그룹화
    if 6 % 6 > 0:
        discussion_groups += 1
    discussion_total_time = discussion_groups * 30  # 각 그룹 30분
    print(f"토론면접: {discussion_groups}개 그룹 × 30분 = {discussion_total_time}분")
    
    # 발표준비 분석
    prep_groups = 6 // 2  # 6명을 2명씩 그룹화
    if 6 % 2 > 0:
        prep_groups += 1
    prep_total_time = prep_groups * 5  # 각 그룹 5분
    print(f"발표준비: {prep_groups}개 그룹 × 5분 = {prep_total_time}분")
    
    # 발표면접 분석
    interview_groups = 6 // 1  # 6명을 1명씩
    interview_time_per_batch = (interview_groups // 2) * 15  # 2개 방 병렬
    if interview_groups % 2 > 0:
        interview_time_per_batch += 15
    print(f"발표면접: {interview_groups}명, 2개 방 병렬 → {interview_time_per_batch}분")
    
    print(f"\n=== 🎯 핵심 문제점 식별 ===")
    print(f"1. 발표준비 그룹 수: {prep_groups}개")
    print(f"2. 발표면접실 수: 2개")
    print(f"3. 연속배치 요구: 발표준비 완료 후 정확히 5분 후 발표면접")
    
    # 시간 충돌 분석
    print(f"\n=== ⏰ 시간 충돌 패턴 분석 ===")
    
    # 실제 스케줄링 실행
    status, result, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
    
    if result is not None and not result.empty:
        print(f"스케줄링 성공: {len(result)}개 항목")
        
        # 활동별 시간 분석
        for activity in ["토론면접", "발표준비", "발표면접"]:
            activity_data = result[result['activity_name'] == activity]
            if not activity_data.empty:
                start_times = sorted(activity_data['start_time'].unique())
                print(f"\n{activity} 시작 시간:")
                for i, start_time in enumerate(start_times):
                    participants = activity_data[activity_data['start_time'] == start_time]['applicant_id'].tolist()
                    print(f"  {i+1}차: {start_time} - 참가자: {participants}")
        
        # 선후행 제약 위반 분석
        print(f"\n=== 🚨 선후행 제약 위반 상세 분석 ===")
        
        violations = []
        for applicant_id in sorted(result['applicant_id'].unique()):
            applicant_data = result[result['applicant_id'] == applicant_id]
            
            prep_data = applicant_data[applicant_data['activity_name'] == '발표준비']
            interview_data = applicant_data[applicant_data['activity_name'] == '발표면접']
            
            if not prep_data.empty and not interview_data.empty:
                prep_end = prep_data.iloc[0]['end_time']
                interview_start = interview_data.iloc[0]['start_time']
                
                # 시간 차이 계산
                if hasattr(prep_end, 'total_seconds'):
                    prep_end_min = prep_end.total_seconds() / 60
                else:
                    prep_end_min = prep_end.hour * 60 + prep_end.minute
                
                if hasattr(interview_start, 'total_seconds'):
                    interview_start_min = interview_start.total_seconds() / 60
                else:
                    interview_start_min = interview_start.hour * 60 + interview_start.minute
                
                gap = interview_start_min - prep_end_min
                
                if abs(gap - 5) > 0.1:
                    violations.append({
                        'applicant': applicant_id,
                        'prep_end': prep_end,
                        'interview_start': interview_start,
                        'gap': gap,
                        'expected': 5
                    })
        
        print(f"총 위반 건수: {len(violations)}/{len(result['applicant_id'].unique())}")
        
        for violation in violations:
            print(f"  {violation['applicant']}: {violation['gap']:.1f}분 간격 (예상: {violation['expected']}분)")
            
            # 위반 원인 분석
            applicant_data = result[result['applicant_id'] == violation['applicant']]
            discussion_data = applicant_data[applicant_data['activity_name'] == '토론면접']
            
            if not discussion_data.empty:
                discussion_end = discussion_data.iloc[0]['end_time']
                if hasattr(discussion_end, 'total_seconds'):
                    discussion_end_min = discussion_end.total_seconds() / 60
                else:
                    discussion_end_min = discussion_end.hour * 60 + discussion_end.minute
                
                if hasattr(violation['prep_end'], 'total_seconds'):
                    prep_end_min = violation['prep_end'].total_seconds() / 60
                else:
                    prep_end_min = violation['prep_end'].hour * 60 + violation['prep_end'].minute
                
                discussion_to_prep = prep_end_min - discussion_end_min
                print(f"    토론면접 종료 → 발표준비 완료: {discussion_to_prep:.1f}분")
        
        # 방 사용 패턴 분석
        print(f"\n=== 🏢 방 사용 패턴 분석 ===")
        
        for room_type in ["발표준비실", "발표면접실A", "발표면접실B"]:
            room_data = result[result['room_name'].str.contains(room_type.replace("A", "").replace("B", ""), na=False)]
            if not room_data.empty:
                print(f"\n{room_type}:")
                for _, row in room_data.iterrows():
                    print(f"  {row['start_time']} ~ {row['end_time']}: {row['applicant_id']} ({row['activity_name']})")
    
    else:
        print("❌ 스케줄링 실패")
    
    print(f"\n=== 💡 문제 해결 아이디어 ===")
    print("1. 🔄 스케줄링 순서 변경: individual → parallel → batched")
    print("2. 🎯 역방향 스케줄링: 발표면접 시간을 먼저 확정하고 발표준비 시간 역산")
    print("3. 🧩 통합 스케줄링: precedence 쌍을 하나의 단위로 처리")
    print("4. 🔀 시간 슬롯 교환: 충돌 시 기존 배치를 재조정")
    print("5. 📐 수학적 최적화: 제약 만족 문제(CSP)로 모델링")

if __name__ == "__main__":
    analyze_scheduling_problem() 