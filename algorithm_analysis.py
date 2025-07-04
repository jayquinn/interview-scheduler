#!/usr/bin/env python3
"""
BALANCED vs CAPACITY_OPTIMIZED 알고리즘 상세 분석
"""

import math

def analyze_balanced_algorithm():
    """BALANCED 알고리즘 상세 분석"""
    
    print('🔧 BALANCED 알고리즘 상세 분석')
    print('=' * 80)
    
    print('\n📝 수학적 정의:')
    print('''
목표: 사용가능한 시간을 그룹들 사이에 균등하게 분배

공식:
1. available_time = total_operating_time - activity_duration
2. ideal_interval = available_time / (group_count - 1)
3. actual_interval = clamp(ideal_interval, min_constraint, max_constraint)
4. time_slot[i] = start_time + (i × actual_interval)
5. 점심시간 충돌 시 자동 조정
    ''')
    
    # 구체적 예시
    scenarios = [
        {'name': '기본 케이스', 'group_count': 3, 'duration': 30, 'expected': '균등한 2시간+ 간격'},
        {'name': '많은 그룹', 'group_count': 6, 'duration': 30, 'expected': '촘촘한 배치'},
        {'name': '긴 활동', 'group_count': 4, 'duration': 60, 'expected': '간격 조정'}
    ]
    
    for scenario in scenarios:
        print(f'\n🔍 시나리오: {scenario["name"]}')
        print(f'   그룹 수: {scenario["group_count"]}개')
        print(f'   활동 시간: {scenario["duration"]}분')
        print(f'   예상: {scenario["expected"]}')
        
        # 계산 과정
        operating_minutes = 8.5 * 60  # 09:00-17:30
        activity_minutes = scenario['duration']
        available_minutes = operating_minutes - activity_minutes
        
        if scenario['group_count'] > 1:
            ideal_interval = available_minutes / (scenario['group_count'] - 1)
        else:
            ideal_interval = 0
            
        min_interval = max(60, activity_minutes + 10)
        max_interval = min(180, available_minutes / 2)
        actual_interval = max(min_interval, min(ideal_interval, max_interval))
        
        print(f'   계산 결과:')
        print(f'     - 사용가능시간: {available_minutes:.0f}분')
        print(f'     - 이상적 간격: {ideal_interval:.0f}분')
        print(f'     - 실제 간격: {actual_interval:.0f}분')
        
        # 시간 슬롯 배치
        print(f'   시간 배치:')
        current_minutes = 9 * 60  # 09:00
        for i in range(scenario['group_count']):
            hours = int(current_minutes // 60)
            minutes = int(current_minutes % 60)
            print(f'     그룹 {i+1}: {hours:02d}:{minutes:02d}')
            current_minutes += actual_interval
        print('-' * 60)

def analyze_capacity_optimized_algorithm():
    """CAPACITY_OPTIMIZED 알고리즘 상세 분석"""
    
    print('\n🏢 CAPACITY_OPTIMIZED 알고리즘 상세 분석')
    print('=' * 80)
    
    print('\n📝 수학적 정의:')
    print('''
목표: 제한된 방 자원을 고려하여 최적 시간 배치

공식:
1. concurrent_groups = min(group_count, available_rooms)
2. time_batches = ceil(group_count / concurrent_groups)
3. batch_interval = available_time / (time_batches - 1)
4. 각 배치에서 concurrent_groups만큼 동시 배치
5. time_slot[batch][group] = start_time + (batch × batch_interval)
    ''')
    
    # 구체적 예시
    scenarios = [
        {'name': '방 부족 (심각)', 'groups': 8, 'rooms': 2, 'expected': '4번 배치, 각 2개씩'},
        {'name': '방 부족 (보통)', 'groups': 6, 'rooms': 3, 'expected': '2번 배치, 각 3개씩'},
        {'name': '방 충분', 'groups': 3, 'rooms': 5, 'expected': '1번 배치, 3개 동시'}
    ]
    
    for scenario in scenarios:
        print(f'\n🔍 시나리오: {scenario["name"]}')
        print(f'   그룹 수: {scenario["groups"]}개')
        print(f'   사용가능 방: {scenario["rooms"]}개')
        print(f'   예상: {scenario["expected"]}')
        
        # 계산 과정
        concurrent_groups = min(scenario['groups'], scenario['rooms'])
        time_batches = math.ceil(scenario['groups'] / concurrent_groups)
        
        available_minutes = 8.5 * 60 - 30  # 운영시간 - 활동시간
        if time_batches > 1:
            batch_interval = available_minutes / (time_batches - 1)
            batch_interval = max(60, batch_interval)
        else:
            batch_interval = 0
        
        print(f'   계산 결과:')
        print(f'     - 동시 처리 그룹: {concurrent_groups}개')
        print(f'     - 필요 배치 횟수: {time_batches}회')
        print(f'     - 배치 간격: {batch_interval:.0f}분')
        
        # 시간 슬롯 배치
        print(f'   시간 배치:')
        current_minutes = 9 * 60  # 09:00
        
        for batch in range(time_batches):
            groups_in_batch = min(concurrent_groups, scenario['groups'] - batch * concurrent_groups)
            hours = int(current_minutes // 60)
            minutes = int(current_minutes % 60)
            
            if groups_in_batch == 1:
                print(f'     배치 {batch+1}: {hours:02d}:{minutes:02d} (그룹 {batch * concurrent_groups + 1})')
            else:
                group_range = range(batch * concurrent_groups + 1, batch * concurrent_groups + groups_in_batch + 1)
                print(f'     배치 {batch+1}: {hours:02d}:{minutes:02d} (그룹 {list(group_range)}) - 동시 진행')
            
            current_minutes += batch_interval
        print('-' * 60)

def compare_algorithms():
    """두 알고리즘 직접 비교"""
    
    print('\n⚔️ BALANCED vs CAPACITY_OPTIMIZED 직접 비교')
    print('=' * 80)
    
    print('🔍 테스트 조건: 6개 그룹, 2개 방, 30분 활동')
    
    print('\n📊 BALANCED 결과:')
    print('  - 모든 그룹을 시간적으로 균등 분산')
    print('  - 방 제약 무시하고 시간 최적화')
    print('  - 09:00, 10:42, 12:24, 14:06, 15:48, 17:30 (예상)')
    print('  - 장점: 체류시간 최소화')
    print('  - 단점: 방 부족 시 실제로는 불가능할 수 있음')
    
    print('\n📊 CAPACITY_OPTIMIZED 결과:')
    print('  - 방 제약을 우선 고려')
    print('  - 3번의 배치, 각각 2개 그룹씩 동시')
    print('  - 09:00 (그룹1,2), 12:15 (그룹3,4), 15:30 (그룹5,6)')
    print('  - 장점: 실제 실행 가능성 높음')
    print('  - 단점: 체류시간이 더 길 수 있음')

def algorithm_selection_guide():
    """알고리즘 선택 가이드"""
    
    print('\n📚 언제 어떤 알고리즘을 사용해야 하나?')
    print('=' * 80)
    
    guide = [
        {'condition': '방 수 >= 그룹 수', 'choice': 'BALANCED', 'reason': '방 제약 없음, 시간 분산 우선'},
        {'condition': '방 수 << 그룹 수', 'choice': 'CAPACITY_OPTIMIZED', 'reason': '방 제약이 주요 제약'},
        {'condition': '긴 운영시간', 'choice': 'BALANCED', 'reason': '시간 여유로 균등 분산 효과적'},
        {'condition': '짧은 운영시간', 'choice': 'CAPACITY_OPTIMIZED', 'reason': '동시 처리로 모든 그룹 배치'},
        {'condition': '체류시간 최적화 우선', 'choice': 'BALANCED', 'reason': '시간 분산이 체류시간 단축'},
        {'condition': '자원 활용도 우선', 'choice': 'CAPACITY_OPTIMIZED', 'reason': '방 활용도 최대화'}
    ]
    
    for item in guide:
        print(f'\n🔸 {item["condition"]}')
        print(f'   권장: {item["choice"]}')
        print(f'   이유: {item["reason"]}')

def critical_analysis():
    """비판적 분석"""
    
    print('\n⚠️ 비판적 분석: 두 알고리즘의 한계')
    print('=' * 80)
    
    print('\n🔍 BALANCED 알고리즘의 문제점:')
    print('1. 방 제약 무시: 실제로는 불가능한 스케줄 생성 가능')
    print('2. 임의적 제약조건: min_interval(60분), max_interval(180분) 근거 부족')
    print('3. 점심시간 처리: 단순한 회피 로직, 최적화 없음')
    print('4. 활동 순서 고려 안됨: 선후행 관계 무시')
    
    print('\n🔍 CAPACITY_OPTIMIZED 알고리즘의 문제점:')
    print('1. 체류시간 최적화 부족: 방 활용도만 고려')
    print('2. 동시 배치의 한계: 모든 그룹이 동시에 끝나면 다음 활동 병목')
    print('3. 시간 분산 부족: 배치 수가 적으면 긴 대기시간')
    print('4. 점심시간 고려 부족: 배치 시점에서만 회피')
    
    print('\n🎯 두 알고리즘 공통 한계:')
    print('1. 휴리스틱 기반: 최적해 보장 안됨')
    print('2. 정적 배치: 동적 상황 변화 대응 부족')
    print('3. 단일 목표: 체류시간 vs 방 활용도 트레이드오프 고려 안됨')
    print('4. 검증 부족: 실제 데이터 기반 성능 측정 필요')

if __name__ == "__main__":
    # 전체 분석 실행
    analyze_balanced_algorithm()
    analyze_capacity_optimized_algorithm()
    compare_algorithms()
    algorithm_selection_guide()
    critical_analysis() 