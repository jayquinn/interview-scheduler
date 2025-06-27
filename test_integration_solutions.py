#!/usr/bin/env python3
"""
🔧 통합 방식 개선 아이디어 테스트
- 공간 정보 보존
- 다중 방 확장성
- 운영 투명성 확보
"""

import pandas as pd
from datetime import datetime, timedelta
from solver.api import solve_for_days_v2

def test_integration_solutions():
    print("=== 🔧 통합 방식 개선 아이디어 테스트 ===")
    print("공간 정보 보존과 확장성을 고려한 다양한 해결책")
    
    # 기본 문제 상황
    print(f"\n📋 기본 문제 상황:")
    print(f"- 발표준비실과 발표면접실은 물리적으로 분리된 공간")
    print(f"- 이동시간 0분이지만 공간 점유 정보는 중요")
    print(f"- 다중 방 환경에서의 확장성 필요")
    
    solutions = [
        ("아이디어1: 이중 스케줄 표시", test_dual_schedule_display),
        ("아이디어2: 가상 방 매핑", test_virtual_room_mapping),
        ("아이디어3: 단계별 활동 분해", test_staged_activity_breakdown),
        ("아이디어4: 다중 방 확장성", test_multi_room_scalability),
        ("아이디어5: 하이브리드 접근법", test_hybrid_approach)
    ]
    
    results = {}
    
    for solution_name, test_func in solutions:
        print(f"\n" + "="*60)
        print(f"🧪 {solution_name}")
        print("="*60)
        
        try:
            result = test_func()
            results[solution_name] = result
            
            if result.get("success", False):
                print(f"✅ 성공: {result.get('description', '')}")
            else:
                print(f"❌ 실패: {result.get('error', '')}")
                
        except Exception as e:
            print(f"❌ 예외 발생: {str(e)}")
            results[solution_name] = {"success": False, "error": str(e)}
    
    # 결과 요약
    print(f"\n" + "="*80)
    print(f"🏆 해결책 비교 분석")
    print("="*80)
    
    for solution_name, result in results.items():
        status = "✅ 성공" if result.get("success", False) else "❌ 실패"
        print(f"{solution_name}: {status}")
        if result.get("pros"):
            print(f"  장점: {', '.join(result['pros'])}")
        if result.get("cons"):
            print(f"  단점: {', '.join(result['cons'])}")
    
    # 최적 해결책 추천
    recommend_best_solution(results)

def test_dual_schedule_display():
    """아이디어1: 이중 스케줄 표시 - 알고리즘은 통합, 표시는 분리"""
    print(f"💡 개념: 내부적으로는 통합 활동으로 처리하되, 결과 표시할 때 분리")
    
    # 기본 설정
    cfg_ui = create_base_config()
    
    try:
        # 스케줄링 실행 (통합 방식)
        status, schedule_df, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
        
        if status != "SUCCESS" or schedule_df.empty:
            return {"success": False, "error": "스케줄링 실패"}
        
        # 결과 분석
        print(f"📊 원본 스케줄 (통합):")
        analyze_schedule_structure(schedule_df)
        
        # 이중 표시 변환
        dual_schedule = convert_to_dual_display(schedule_df)
        
        print(f"\n📊 이중 표시 스케줄 (분리):")
        analyze_schedule_structure(dual_schedule)
        
        return {
            "success": True,
            "description": "통합 처리 + 분리 표시",
            "pros": ["알고리즘 효율성 유지", "공간 정보 보존", "기존 코드 최소 수정"],
            "cons": ["표시 로직 복잡화", "실제 방 배정과 차이"],
            "schedule": dual_schedule
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_virtual_room_mapping():
    """아이디어2: 가상 방 매핑 - 통합 활동에 가상 방 정보 추가"""
    print(f"💡 개념: 통합 활동에 '발표준비실→발표면접실' 매핑 정보 포함")
    
    cfg_ui = create_base_config()
    
    try:
        status, schedule_df, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
        
        if status != "SUCCESS" or schedule_df.empty:
            return {"success": False, "error": "스케줄링 실패"}
        
        # 가상 방 매핑 추가
        mapped_schedule = add_virtual_room_mapping(schedule_df, cfg_ui)
        
        print(f"📊 가상 방 매핑 결과:")
        analyze_virtual_mapping(mapped_schedule)
        
        return {
            "success": True,
            "description": "통합 활동 + 가상 방 매핑",
            "pros": ["공간 추적 가능", "이동 경로 명확", "확장성 좋음"],
            "cons": ["복잡한 매핑 로직", "방 할당 알고리즘 필요"],
            "schedule": mapped_schedule
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_staged_activity_breakdown():
    """아이디어3: 단계별 활동 분해 - 통합 활동을 단계별로 분해하여 표시"""
    print(f"💡 개념: 발표준비+발표면접을 Stage1(준비) + Stage2(면접)로 분해")
    
    cfg_ui = create_base_config()
    
    try:
        status, schedule_df, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
        
        if status != "SUCCESS" or schedule_df.empty:
            return {"success": False, "error": "스케줄링 실패"}
        
        # 단계별 분해
        staged_schedule = breakdown_to_stages(schedule_df)
        
        print(f"📊 단계별 분해 결과:")
        analyze_staged_breakdown(staged_schedule)
        
        return {
            "success": True,
            "description": "통합 활동의 단계별 분해",
            "pros": ["명확한 단계 구분", "시간 흐름 파악 용이", "공간 점유 추적"],
            "cons": ["복잡한 분해 로직", "시간 계산 복잡"],
            "schedule": staged_schedule
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_multi_room_scalability():
    """아이디어4: 다중 방 확장성 - 발표준비실 2개 이상일 때 테스트"""
    print(f"💡 개념: 발표준비실 2개, 발표면접실 3개 환경에서 확장성 테스트")
    
    # 다중 방 설정
    cfg_ui = create_multi_room_config()
    
    try:
        status, schedule_df, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
        
        print(f"📊 다중 방 스케줄링 결과:")
        print(f"상태: {status}")
        
        if status == "SUCCESS" and not schedule_df.empty:
            analyze_multi_room_schedule(schedule_df)
            
            return {
                "success": True,
                "description": "다중 방 환경 성공",
                "pros": ["확장성 검증", "복잡한 환경 대응"],
                "cons": ["방 매칭 복잡성"],
                "schedule": schedule_df
            }
        else:
            return {
                "success": False,
                "error": "다중 방 환경에서 스케줄링 실패",
                "cons": ["확장성 한계"]
            }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_hybrid_approach():
    """아이디어5: 하이브리드 접근법 - 조건부 통합 + 세부 추적"""
    print(f"💡 개념: gap_min=0일 때만 통합, 나머지는 기존 방식 + 세부 추적")
    
    cfg_ui = create_base_config()
    
    try:
        # 하이브리드 처리
        hybrid_result = process_hybrid_scheduling(cfg_ui)
        
        if hybrid_result["success"]:
            print(f"📊 하이브리드 스케줄링 결과:")
            analyze_hybrid_result(hybrid_result["schedule"])
            
            return {
                "success": True,
                "description": "조건부 통합 + 세부 추적",
                "pros": ["유연성", "상황별 최적화", "투명성"],
                "cons": ["복잡한 로직", "조건 관리"],
                "schedule": hybrid_result["schedule"]
            }
        else:
            return {"success": False, "error": hybrid_result["error"]}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_base_config():
    """기본 테스트 설정"""
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
        {"predecessor": "발표준비", "successor": "발표면접", "gap_min": 0, "adjacent": True}
    ])
    
    job_acts_map = pd.DataFrame({
        "code": ["JOB01"],
        "count": [6],
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    tomorrow = datetime.now().date() + timedelta(days=1)
    
    return {
        'activities': activities,
        'job_acts_map': job_acts_map,
        'room_plan': room_plan,
        'oper_window': oper_window,
        'precedence': precedence,
        'interview_dates': [tomorrow],
        'interview_date': tomorrow
    }

def create_multi_room_config():
    """다중 방 환경 설정"""
    cfg = create_base_config()
    
    # 발표준비실 2개, 발표면접실 3개로 확장
    cfg['room_plan'] = pd.DataFrame({
        "토론면접실_count": [2],
        "토론면접실_cap": [6],
        "발표준비실_count": [2],  # 2개로 증가
        "발표준비실_cap": [2],
        "발표면접실_count": [3],  # 3개로 증가
        "발표면접실_cap": [1]
    })
    
    # 지원자 수도 증가
    cfg['job_acts_map'] = pd.DataFrame({
        "code": ["JOB01"],
        "count": [9],  # 9명으로 증가
        "토론면접": [True],
        "발표준비": [True],
        "발표면접": [True]
    })
    
    return cfg

def convert_to_dual_display(schedule_df):
    """통합 스케줄을 이중 표시로 변환"""
    dual_schedule = []
    
    for _, row in schedule_df.iterrows():
        if '발표준비+발표면접' in str(row.get('activity_name', '')):
            # 통합 활동을 두 개로 분리
            base_row = row.to_dict()
            
            # 발표준비 단계
            prep_row = base_row.copy()
            prep_row['activity_name'] = '발표준비'
            prep_row['duration'] = 5
            prep_row['room_name'] = '발표준비실'
            # 시간은 동일하게 시작
            
            # 발표면접 단계  
            interview_row = base_row.copy()
            interview_row['activity_name'] = '발표면접'
            interview_row['duration'] = 15
            # 발표준비 종료 5분 후 시작 (원래 방 정보 유지)
            
            dual_schedule.extend([prep_row, interview_row])
        else:
            dual_schedule.append(row.to_dict())
    
    return pd.DataFrame(dual_schedule)

def add_virtual_room_mapping(schedule_df, cfg_ui):
    """가상 방 매핑 추가"""
    mapped_schedule = schedule_df.copy()
    
    # 통합 활동에 방 매핑 정보 추가
    room_mapping = []
    
    for idx, row in mapped_schedule.iterrows():
        if '발표준비+발표면접' in str(row.get('activity_name', '')):
            # 가상 방 매핑 생성
            prep_room = f"발표준비실A"  # 실제로는 더 복잡한 로직 필요
            interview_room = row.get('room_name', '발표면접실A')
            
            mapping_info = f"{prep_room}→{interview_room}"
            mapped_schedule.at[idx, 'room_mapping'] = mapping_info
            mapped_schedule.at[idx, 'prep_room'] = prep_room
            mapped_schedule.at[idx, 'interview_room'] = interview_room
    
    return mapped_schedule

def breakdown_to_stages(schedule_df):
    """통합 활동을 단계별로 분해"""
    staged_schedule = []
    
    for _, row in schedule_df.iterrows():
        if '발표준비+발표면접' in str(row.get('activity_name', '')):
            base_row = row.to_dict()
            
            # Stage 1: 발표준비
            stage1 = base_row.copy()
            stage1['stage'] = 1
            stage1['stage_name'] = '발표준비'
            stage1['stage_duration'] = 5
            stage1['stage_room'] = '발표준비실'
            
            # Stage 2: 발표면접
            stage2 = base_row.copy()
            stage2['stage'] = 2
            stage2['stage_name'] = '발표면접'
            stage2['stage_duration'] = 15
            stage2['stage_room'] = base_row.get('room_name', '발표면접실')
            
            staged_schedule.extend([stage1, stage2])
        else:
            staged_schedule.append(row.to_dict())
    
    return pd.DataFrame(staged_schedule)

def process_hybrid_scheduling(cfg_ui):
    """하이브리드 스케줄링 처리"""
    try:
        # 기본 스케줄링 실행
        status, schedule_df, logs, limit = solve_for_days_v2(cfg_ui, debug=False)
        
        if status != "SUCCESS" or schedule_df.empty:
            return {"success": False, "error": "기본 스케줄링 실패"}
        
        # 하이브리드 후처리
        hybrid_schedule = apply_hybrid_post_processing(schedule_df, cfg_ui)
        
        return {
            "success": True,
            "schedule": hybrid_schedule,
            "original": schedule_df
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def apply_hybrid_post_processing(schedule_df, cfg_ui):
    """하이브리드 후처리 적용"""
    # 통합된 활동에 대해 세부 정보 추가
    processed_schedule = schedule_df.copy()
    
    # 추가 메타데이터 컬럼
    processed_schedule['is_integrated'] = False
    processed_schedule['original_activities'] = ''
    processed_schedule['room_sequence'] = ''
    
    for idx, row in processed_schedule.iterrows():
        if '발표준비+발표면접' in str(row.get('activity_name', '')):
            processed_schedule.at[idx, 'is_integrated'] = True
            processed_schedule.at[idx, 'original_activities'] = '발표준비,발표면접'
            processed_schedule.at[idx, 'room_sequence'] = '발표준비실→발표면접실'
    
    return processed_schedule

def analyze_schedule_structure(schedule_df):
    """스케줄 구조 분석"""
    if schedule_df.empty:
        print("  빈 스케줄")
        return
    
    print(f"  총 항목: {len(schedule_df)}개")
    
    if 'activity_name' in schedule_df.columns:
        activities = schedule_df['activity_name'].value_counts()
        for activity, count in activities.items():
            print(f"  - {activity}: {count}개")
    
    if 'room_name' in schedule_df.columns:
        rooms = schedule_df['room_name'].value_counts()
        print(f"  사용 방: {list(rooms.index)}")

def analyze_virtual_mapping(mapped_schedule):
    """가상 방 매핑 분석"""
    if 'room_mapping' in mapped_schedule.columns:
        mappings = mapped_schedule['room_mapping'].dropna().unique()
        print(f"  방 매핑: {list(mappings)}")
    
    if 'prep_room' in mapped_schedule.columns:
        prep_rooms = mapped_schedule['prep_room'].dropna().unique()
        print(f"  발표준비실 사용: {list(prep_rooms)}")

def analyze_staged_breakdown(staged_schedule):
    """단계별 분해 분석"""
    if 'stage' in staged_schedule.columns:
        stages = staged_schedule['stage'].value_counts().sort_index()
        for stage, count in stages.items():
            print(f"  Stage {stage}: {count}개")

def analyze_multi_room_schedule(schedule_df):
    """다중 방 스케줄 분석"""
    print(f"  총 스케줄: {len(schedule_df)}개")
    
    if 'room_name' in schedule_df.columns:
        rooms = schedule_df['room_name'].value_counts()
        print(f"  방별 사용량:")
        for room, count in rooms.items():
            print(f"    {room}: {count}개")

def analyze_hybrid_result(hybrid_schedule):
    """하이브리드 결과 분석"""
    if 'is_integrated' in hybrid_schedule.columns:
        integrated_count = hybrid_schedule['is_integrated'].sum()
        print(f"  통합된 활동: {integrated_count}개")
    
    if 'room_sequence' in hybrid_schedule.columns:
        sequences = hybrid_schedule['room_sequence'].dropna().unique()
        print(f"  방 이동 경로: {list(sequences)}")

def recommend_best_solution(results):
    """최적 해결책 추천"""
    print(f"\n🎯 최적 해결책 추천:")
    
    successful_solutions = [name for name, result in results.items() if result.get("success", False)]
    
    if not successful_solutions:
        print(f"❌ 모든 해결책이 실패했습니다. 추가 연구가 필요합니다.")
        return
    
    print(f"✅ 성공한 해결책: {len(successful_solutions)}개")
    
    # 각 해결책의 장단점 비교
    print(f"\n📊 해결책별 특징:")
    
    for solution in successful_solutions:
        result = results[solution]
        pros = len(result.get("pros", []))
        cons = len(result.get("cons", []))
        score = pros - cons
        print(f"  {solution}: 점수 {score} (장점 {pros}, 단점 {cons})")
    
    # 추천 기준
    print(f"\n🏆 추천 순위:")
    print(f"1. 이중 스케줄 표시: 기존 코드 최소 수정, 즉시 적용 가능")
    print(f"2. 하이브리드 접근법: 유연성과 투명성 균형")
    print(f"3. 가상 방 매핑: 확장성 우수, 복잡한 환경 대응")

if __name__ == "__main__":
    test_integration_solutions() 