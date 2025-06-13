"""
테스트 데이터 생성 유틸리티 모듈
개발과 테스트를 위한 샘플 데이터를 생성합니다.
"""

import pandas as pd
from datetime import datetime, time
from typing import Dict, List, Optional


def create_basic_test_scenario() -> Dict:
    """
    기본 테스트 시나리오: 개별 면접만 있는 단순한 케이스
    
    Returns:
        테스트용 설정 딕셔너리
    """
    # 활동 정의
    activities = pd.DataFrame({
        "use": [True, True, True, True],
        "activity": ["서류검증", "인성면접", "직무면접", "임원면접"],
        "mode": ["individual"] * 4,
        "duration_min": [10, 20, 30, 15],
        "room_type": ["검증실", "면접실A", "면접실B", "임원실"],
        "min_cap": [1] * 4,
        "max_cap": [1] * 4,
    })
    
    # 직무별 활동 매핑
    job_acts_map = pd.DataFrame({
        "code": ["DEV", "PM"],
        "count": [10, 5],
        "서류검증": [True, True],
        "인성면접": [True, True],
        "직무면접": [True, True],
        "임원면접": [True, False],  # PM은 임원면접 없음
    })
    
    # 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "__START__", "successor": "서류검증", "gap_min": 0, "adjacent": False},
        {"predecessor": "서류검증", "successor": "인성면접", "gap_min": 5, "adjacent": False},
        {"predecessor": "인성면접", "successor": "직무면접", "gap_min": 10, "adjacent": False},
    ])
    
    # 운영 공간 (템플릿)
    room_plan = pd.DataFrame([{
        "검증실_count": 2,
        "검증실_cap": 1,
        "면접실A_count": 3,
        "면접실A_cap": 1,
        "면접실B_count": 3,
        "면접실B_cap": 1,
        "임원실_count": 1,
        "임원실_cap": 1,
    }])
    
    # 운영 시간 (템플릿)
    oper_window = pd.DataFrame([{
        "start_time": "09:00",
        "end_time": "18:00",
    }])
    
    return {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
    }


def create_mixed_test_scenario() -> Dict:
    """
    혼합 테스트 시나리오: individual + parallel 모드
    
    Returns:
        테스트용 설정 딕셔너리
    """
    # 활동 정의
    activities = pd.DataFrame({
        "use": [True, True, True, True, True],
        "activity": ["서류검증", "인성검사", "인성면접", "직무면접", "커피챗"],
        "mode": ["individual", "parallel", "individual", "individual", "parallel"],
        "duration_min": [10, 60, 20, 30, 15],
        "room_type": ["검증실", "검사실", "면접실A", "면접실B", "라운지"],
        "min_cap": [1, 1, 1, 1, 1],
        "max_cap": [1, 10, 1, 1, 5],  # parallel 모드는 용량이 큼
    })
    
    # 직무별 활동 매핑
    job_acts_map = pd.DataFrame({
        "code": ["DEV", "QA", "PM"],
        "count": [8, 6, 4],
        "서류검증": [True, True, True],
        "인성검사": [True, True, True],
        "인성면접": [True, True, True],
        "직무면접": [True, True, True],
        "커피챗": [True, False, True],  # QA는 커피챗 없음
    })
    
    # 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "__START__", "successor": "서류검증", "gap_min": 0, "adjacent": False},
        {"predecessor": "서류검증", "successor": "인성검사", "gap_min": 5, "adjacent": False},
        {"predecessor": "인성검사", "successor": "인성면접", "gap_min": 10, "adjacent": False},
        {"predecessor": "커피챗", "successor": "__END__", "gap_min": 0, "adjacent": False},
    ])
    
    # 운영 공간
    room_plan = pd.DataFrame([{
        "검증실_count": 2,
        "검증실_cap": 1,
        "검사실_count": 1,
        "검사실_cap": 10,
        "면접실A_count": 3,
        "면접실A_cap": 1,
        "면접실B_count": 3,
        "면접실B_cap": 1,
        "라운지_count": 1,
        "라운지_cap": 5,
    }])
    
    # 운영 시간
    oper_window = pd.DataFrame([{
        "start_time": "09:00",
        "end_time": "18:00",
    }])
    
    return {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
    }


def create_batched_test_scenario() -> Dict:
    """
    집단면접 테스트 시나리오: individual + batched 모드
    
    Returns:
        테스트용 설정 딕셔너리
    """
    # 활동 정의
    activities = pd.DataFrame({
        "use": [True, True, True, True, True],
        "activity": ["서류검증", "집단토론", "프레젠테이션", "개별면접", "최종평가"],
        "mode": ["individual", "batched", "batched", "individual", "individual"],
        "duration_min": [10, 60, 45, 30, 15],
        "room_type": ["검증실", "토론실", "발표실", "면접실", "평가실"],
        "min_cap": [1, 4, 3, 1, 1],
        "max_cap": [1, 6, 5, 1, 1],
    })
    
    # 직무별 활동 매핑
    job_acts_map = pd.DataFrame({
        "code": ["DEV", "PM", "DESIGN"],
        "count": [12, 8, 6],
        "서류검증": [True, True, True],
        "집단토론": [True, True, True],
        "프레젠테이션": [True, True, True],
        "개별면접": [True, True, True],
        "최종평가": [True, True, True],
    })
    
    # 선후행 제약
    precedence = pd.DataFrame([
        {"predecessor": "__START__", "successor": "서류검증", "gap_min": 0, "adjacent": False},
        {"predecessor": "서류검증", "successor": "집단토론", "gap_min": 10, "adjacent": False},
        {"predecessor": "집단토론", "successor": "프레젠테이션", "gap_min": 15, "adjacent": False},
        {"predecessor": "프레젠테이션", "successor": "개별면접", "gap_min": 10, "adjacent": False},
        {"predecessor": "개별면접", "successor": "최종평가", "gap_min": 5, "adjacent": False},
    ])
    
    # 운영 공간
    room_plan = pd.DataFrame([{
        "검증실_count": 3,
        "검증실_cap": 1,
        "토론실_count": 2,
        "토론실_cap": 6,
        "발표실_count": 2,
        "발표실_cap": 5,
        "면접실_count": 4,
        "면접실_cap": 1,
        "평가실_count": 2,
        "평가실_cap": 1,
    }])
    
    # 운영 시간
    oper_window = pd.DataFrame([{
        "start_time": "09:00",
        "end_time": "18:00",
    }])
    
    # 유사 직무 그룹 (선택사항)
    job_similarity_groups = [["DEV", "PM"], ["DESIGN"]]
    
    return {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "job_similarity_groups": job_similarity_groups,
        "prefer_job_separation": True,
    }


def create_complex_test_scenario() -> Dict:
    """
    복잡한 테스트 시나리오: 모든 모드 혼합
    
    Returns:
        테스트용 설정 딕셔너리
    """
    # 활동 정의
    activities = pd.DataFrame({
        "use": [True] * 8,
        "activity": [
            "서류검증",      # individual
            "인성검사",      # parallel
            "집단토론",      # batched
            "케이스스터디",  # batched
            "개별PT",        # individual
            "심층면접",      # individual
            "역량평가",      # parallel
            "최종면담"       # individual
        ],
        "mode": ["individual", "parallel", "batched", "batched", 
                "individual", "individual", "parallel", "individual"],
        "duration_min": [10, 60, 90, 60, 20, 45, 30, 15],
        "room_type": ["검증실", "검사실", "토론실", "스터디룸", 
                     "PT룸", "면접실", "평가실", "면담실"],
        "min_cap": [1, 1, 4, 3, 1, 1, 1, 1],
        "max_cap": [1, 20, 6, 5, 1, 1, 10, 1],
    })
    
    # 직무별 활동 매핑
    job_acts_map = pd.DataFrame({
        "code": ["DEV", "QA", "PM", "DESIGN", "DATA"],
        "count": [10, 8, 6, 5, 5],
    })
    
    # 모든 활동을 모든 직무에 매핑
    for activity in activities['activity']:
        job_acts_map[activity] = True
    
    # 선후행 제약 (복잡한 흐름)
    precedence = pd.DataFrame([
        {"predecessor": "__START__", "successor": "서류검증", "gap_min": 0, "adjacent": False},
        {"predecessor": "서류검증", "successor": "인성검사", "gap_min": 5, "adjacent": False},
        {"predecessor": "인성검사", "successor": "집단토론", "gap_min": 15, "adjacent": False},
        {"predecessor": "집단토론", "successor": "케이스스터디", "gap_min": 20, "adjacent": False},
        {"predecessor": "케이스스터디", "successor": "개별PT", "gap_min": 10, "adjacent": False},
        {"predecessor": "개별PT", "successor": "심층면접", "gap_min": 5, "adjacent": True},
        {"predecessor": "심층면접", "successor": "역량평가", "gap_min": 10, "adjacent": False},
        {"predecessor": "역량평가", "successor": "최종면담", "gap_min": 5, "adjacent": False},
        {"predecessor": "최종면담", "successor": "__END__", "gap_min": 0, "adjacent": False},
    ])
    
    # 운영 공간 (대규모)
    room_plan = pd.DataFrame([{
        "검증실_count": 4,
        "검증실_cap": 1,
        "검사실_count": 1,
        "검사실_cap": 20,
        "토론실_count": 3,
        "토론실_cap": 6,
        "스터디룸_count": 3,
        "스터디룸_cap": 5,
        "PT룸_count": 5,
        "PT룸_cap": 1,
        "면접실_count": 6,
        "면접실_cap": 1,
        "평가실_count": 1,
        "평가실_cap": 10,
        "면담실_count": 3,
        "면담실_cap": 1,
    }])
    
    # 운영 시간 (긴 운영시간)
    oper_window = pd.DataFrame([{
        "start_time": "08:00",
        "end_time": "20:00",
    }])
    
    # 유사 직무 그룹
    job_similarity_groups = [
        ["DEV", "QA", "DATA"],  # 기술직군
        ["PM", "DESIGN"]        # 기획/디자인직군
    ]
    
    return {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "job_similarity_groups": job_similarity_groups,
        "prefer_job_separation": True,
    }


def create_stress_test_scenario() -> Dict:
    """
    스트레스 테스트 시나리오: 많은 지원자, 제한된 자원
    
    Returns:
        테스트용 설정 딕셔너리
    """
    # 활동 정의 (짧은 활동들)
    activities = pd.DataFrame({
        "use": [True] * 5,
        "activity": ["스크리닝", "그룹평가", "토론", "면접", "피드백"],
        "mode": ["individual", "batched", "batched", "individual", "parallel"],
        "duration_min": [5, 30, 45, 20, 10],
        "room_type": ["스크린실", "평가실", "토론실", "면접실", "피드백실"],
        "min_cap": [1, 6, 5, 1, 1],
        "max_cap": [1, 8, 6, 1, 15],
    })
    
    # 많은 지원자
    job_acts_map = pd.DataFrame({
        "code": ["J01", "J02", "J03", "J04"],
        "count": [25, 20, 15, 10],  # 총 70명
    })
    
    for activity in activities['activity']:
        job_acts_map[activity] = True
    
    # 간단한 선후행
    precedence = pd.DataFrame([
        {"predecessor": "스크리닝", "successor": "그룹평가", "gap_min": 5, "adjacent": False},
        {"predecessor": "그룹평가", "successor": "토론", "gap_min": 10, "adjacent": False},
        {"predecessor": "토론", "successor": "면접", "gap_min": 5, "adjacent": False},
    ])
    
    # 제한된 공간
    room_plan = pd.DataFrame([{
        "스크린실_count": 2,
        "스크린실_cap": 1,
        "평가실_count": 1,
        "평가실_cap": 8,
        "토론실_count": 1,
        "토론실_cap": 6,
        "면접실_count": 3,
        "면접실_cap": 1,
        "피드백실_count": 1,
        "피드백실_cap": 15,
    }])
    
    # 짧은 운영 시간
    oper_window = pd.DataFrame([{
        "start_time": "09:00",
        "end_time": "17:00",
    }])
    
    return {
        "activities": activities,
        "job_acts_map": job_acts_map,
        "precedence": precedence,
        "room_plan": room_plan,
        "oper_window": oper_window,
        "prefer_job_separation": False,  # 자원이 부족하므로 직무 혼합 허용
    }


def generate_candidates_from_job_map(job_acts_map: pd.DataFrame, 
                                   interview_date: str = "2025-01-01") -> pd.DataFrame:
    """
    job_acts_map을 기반으로 지원자 데이터를 생성합니다.
    
    Args:
        job_acts_map: 직무별 활동 매핑 DataFrame
        interview_date: 면접 날짜
        
    Returns:
        지원자 정보 DataFrame
    """
    candidates = []
    
    for _, row in job_acts_map.iterrows():
        job_code = row['code']
        count = int(row['count'])
        
        for i in range(count):
            candidate_id = f"{job_code}_{str(i+1).zfill(3)}"
            candidates.append({
                'id': candidate_id,
                'job_code': job_code,
                'interview_date': interview_date
            })
    
    return pd.DataFrame(candidates)


def get_test_scenario(scenario_name: str = "basic") -> Dict:
    """
    지정된 테스트 시나리오를 반환합니다.
    
    Args:
        scenario_name: 시나리오 이름 
            ("basic", "mixed", "batched", "complex", "stress")
            
    Returns:
        테스트용 설정 딕셔너리
    """
    scenarios = {
        "basic": create_basic_test_scenario,
        "mixed": create_mixed_test_scenario,
        "batched": create_batched_test_scenario,
        "complex": create_complex_test_scenario,
        "stress": create_stress_test_scenario,
    }
    
    if scenario_name not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario_name}. Available: {list(scenarios.keys())}")
    
    config = scenarios[scenario_name]()
    
    # 지원자 데이터 자동 생성
    config['candidates'] = generate_candidates_from_job_map(config['job_acts_map'])
    
    return config 