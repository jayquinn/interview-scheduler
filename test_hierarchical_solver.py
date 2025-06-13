# test_hierarchical_solver.py
"""
계층적 솔버 테스트 스크립트
다양한 시나리오로 계층적 솔버를 테스트합니다.
"""

import pandas as pd
from datetime import datetime
import logging

from utils.test_data import get_test_scenario
from solver.hierarchical_solver import HierarchicalSolver
from solver.group_formation import check_group_size_compatibility

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_scenario(scenario_name: str):
    """특정 시나리오를 테스트합니다."""
    print(f"\n{'='*60}")
    print(f"테스트 시나리오: {scenario_name}")
    print(f"{'='*60}")
    
    # 테스트 데이터 로드
    config = get_test_scenario(scenario_name)
    
    # 활동 정보 출력
    activities = config['activities']
    print("\n활동 정보:")
    print(activities[['activity', 'mode', 'duration_min', 'min_cap', 'max_cap']])
    
    # 그룹 크기 호환성 체크
    is_compatible, error_msg = check_group_size_compatibility(activities)
    if not is_compatible:
        print(f"\n❌ 그룹 크기 호환성 오류: {error_msg}")
        return
    
    # 직무별 인원수 출력
    job_acts_map = config['job_acts_map']
    print(f"\n직무별 인원수:")
    for _, row in job_acts_map.iterrows():
        print(f"  - {row['code']}: {row['count']}명")
    print(f"  총 {job_acts_map['count'].sum()}명")
    
    # 계층적 솔버 설정
    hierarchical_config = {
        'activities': activities,
        'candidates': config['candidates'],
        'room_info': {},  # 간단한 테스트를 위해 room_info 구성
        'oper_hours': {'JOB01': (540, 1080)},  # 9:00-18:00
        'precedence': [],
        'job_similarity_groups': config.get('job_similarity_groups', []),
        'prefer_job_separation': config.get('prefer_job_separation', True),
        'min_gap_min': 5,
        'the_date': datetime(2025, 1, 1),
        'time_limit_sec': 60.0
    }
    
    # Room 정보 구성
    room_plan = config['room_plan']
    for col in room_plan.columns:
        if col.endswith('_count'):
            room_type = col.replace('_count', '')
            count = int(room_plan[col].iloc[0])
            cap_col = f"{room_type}_cap"
            cap = int(room_plan[cap_col].iloc[0])
            
            for i in range(1, count + 1):
                room_name = f"{room_type}{i}" if count > 1 else room_type
                hierarchical_config['room_info'][room_name] = {'capacity': cap}
    
    # 모든 직무에 동일한 운영시간 적용
    for code in job_acts_map['code']:
        hierarchical_config['oper_hours'][code] = (540, 1080)  # 9:00-18:00
    
    # 선후행 제약 변환
    if 'precedence' in config and not config['precedence'].empty:
        for _, rule in config['precedence'].iterrows():
            hierarchical_config['precedence'].append((
                rule['predecessor'],
                rule['successor'],
                rule.get('gap_min', 0),
                rule.get('adjacent', False)
            ))
    
    print("\n계층적 솔버 실행 중...")
    
    # 계층적 솔버 실행
    solver = HierarchicalSolver(hierarchical_config)
    schedule_df, status, logs = solver.solve()
    
    print(f"\n상태: {status}")
    print("\n실행 로그:")
    print("-" * 40)
    print(logs)
    print("-" * 40)
    
    if status in ["OPTIMAL", "FEASIBLE"] and not schedule_df.empty:
        print(f"\n✅ 스케줄링 성공!")
        print(f"생성된 스케줄: {len(schedule_df)}명")
        
        # 그룹 정보 출력
        if 'group_id' in schedule_df.columns:
            group_summary = schedule_df.groupby('group_id').agg({
                'id': 'count',
                'code': lambda x: x.value_counts().to_dict()
            })
            print("\n그룹별 구성:")
            for group_id, row in group_summary.iterrows():
                print(f"  그룹 {group_id}: {row['id']}명 - {row['code']}")
    else:
        print(f"\n❌ 스케줄링 실패: {status}")


def main():
    """메인 테스트 함수"""
    # 1. Batched 시나리오 테스트
    test_scenario("batched")
    
    # 2. 복잡한 시나리오 테스트
    # test_scenario("complex")
    
    # 3. 스트레스 테스트
    # test_scenario("stress")


if __name__ == "__main__":
    main() 