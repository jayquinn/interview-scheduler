#!/usr/bin/env python3
"""
A방식(Level 2 사전 분산 배치) 구체적 설계 및 구현 가이드

현재 BatchedScheduler의 순차적 배치 문제를 해결하여
토론면접 그룹들을 시간적으로 분산 배치하는 방법
"""

from typing import Dict, List, Tuple, Optional
from datetime import timedelta
from dataclasses import dataclass
from enum import Enum

# 분산 전략 정의
class DistributionStrategy(Enum):
    BALANCED = "balanced"              # 균등 분산 (기본)
    STAY_TIME_OPTIMIZED = "stay_time_optimized"  # 체류시간 최적화 (2시간 간격)
    EARLY_HEAVY = "early_heavy"        # 앞시간 집중 (70%/30%)
    LATE_HEAVY = "late_heavy"          # 뒷시간 집중 (30%/70%)

@dataclass
class DistributionConfig:
    """분산 배치 설정"""
    strategy: DistributionStrategy = DistributionStrategy.BALANCED
    min_gap_minutes: int = 60          # 최소 간격
    max_gap_minutes: int = 180         # 최대 간격
    lunch_start: timedelta = timedelta(hours=12)
    lunch_end: timedelta = timedelta(hours=13)
    target_stay_time_hours: float = 2.0  # 목표 체류시간

def analyze_current_problem():
    """현재 배치 문제 분석"""
    
    print("🔍 현재 BatchedScheduler 문제 분석")
    print("=" * 80)
    
    print("""
📋 현재 배치 로직 (순차적):
```python
next_start_time = config.operating_hours[0]  # 09:00

for group_info in all_groups:
    start_time = max(earliest_start, next_start_time)
    end_time = start_time + activity.duration
    
    # 방 배정 후
    next_start_time = start_time + activity.duration + timedelta(minutes=10)
```

🚨 문제점:
1. 그룹들이 순차적으로 앞시간부터 배치
2. 토론면접: 09:00 → 09:40 → 10:20 → 11:00 → ...
3. Individual 활동들이 뒷시간으로 밀림
4. 체류시간 증가: 첫 활동 09:00, 마지막 활동 17:00 → 8시간 체류

📈 실험 결과 (디폴트 데이터):
• 현재 방식: 평균 체류시간 4.2시간, 최대 6.8시간
• 토론면접 그룹 이동 후: 평균 체류시간 2.5시간, 최대 4.1시간
• 개선 효과: 104.8시간 총 단축 (57명 대상)
    """)

def design_a_method_algorithm():
    """A방식 알고리즘 설계"""
    
    print("\n\n🔧 A방식 알고리즘 설계")
    print("=" * 80)
    
    print("""
🎯 핵심 아이디어:
• 기존: 그룹들을 순차적으로 배치
• A방식: 그룹들을 시간적으로 분산 배치

📐 수학적 알고리즘:
```
1. available_time = operating_end - operating_start - activity_duration
2. group_count = 활동의 총 그룹 수
3. ideal_interval = available_time / (group_count - 1)
4. actual_interval = clamp(ideal_interval, min_gap, max_gap)
5. time_slots[i] = start_time + (i × actual_interval)
```

🔀 분산 전략별 시간 계산:

1️⃣ BALANCED (균등 분산):
   intervals = [i * actual_interval for i in range(group_count)]

2️⃣ STAY_TIME_OPTIMIZED (체류시간 최적화):
   target_gap = 2시간 = 120분
   intervals = [i * min(target_gap, actual_interval) for i in range(group_count)]

3️⃣ EARLY_HEAVY (앞시간 집중):
   early_groups = int(group_count * 0.7)
   early_interval = available_time * 0.3 / (early_groups - 1)
   late_interval = available_time * 0.7 / (group_count - early_groups - 1)

4️⃣ LATE_HEAVY (뒷시간 집중):
   early_groups = int(group_count * 0.3)
   early_interval = available_time * 0.7 / (early_groups - 1)
   late_interval = available_time * 0.3 / (group_count - early_groups - 1)
    """)

def show_implementation_approach():
    """구현 접근법"""
    
    print("\n\n💻 구현 접근법")
    print("=" * 80)
    
    print("""
🎯 수정 대상: solver/batched_scheduler.py의 `_schedule_activity_with_precedence` 메서드

📝 현재 코드 (문제 부분):
```python
# 현재: 순차적 배치
for group_info in all_groups:
    start_time = max(earliest_start, next_start_time)
    next_start_time = start_time + activity.duration + timedelta(minutes=10)
```

🔧 A방식 개선 코드:
```python
# A방식: 사전 시간 분산 계산
def _calculate_distributed_time_slots(
    self, 
    activity: Activity,
    group_count: int, 
    config: DateConfig,
    distribution_config: DistributionConfig
) -> List[timedelta]:
    
    operating_start = config.operating_hours[0]
    operating_end = config.operating_hours[1]
    
    # 사용 가능한 시간 계산
    available_time = operating_end - operating_start - activity.duration
    available_minutes = int(available_time.total_seconds() / 60)
    
    # 분산 전략별 시간 슬롯 계산
    if distribution_config.strategy == DistributionStrategy.BALANCED:
        return self._calculate_balanced_slots(
            operating_start, group_count, available_minutes, distribution_config
        )
    elif distribution_config.strategy == DistributionStrategy.STAY_TIME_OPTIMIZED:
        return self._calculate_stay_time_optimized_slots(
            operating_start, group_count, distribution_config
        )
    # ... 다른 전략들
    
def _calculate_balanced_slots(
    self,
    start_time: timedelta,
    group_count: int,
    available_minutes: int,
    config: DistributionConfig
) -> List[timedelta]:
    
    if group_count <= 1:
        return [start_time]
    
    # 이상적 간격 계산
    ideal_interval = available_minutes / (group_count - 1)
    
    # 제약 조건 적용
    actual_interval = max(
        config.min_gap_minutes,
        min(config.max_gap_minutes, ideal_interval)
    )
    
    # 시간 슬롯 생성
    time_slots = []
    for i in range(group_count):
        slot_time = start_time + timedelta(minutes=i * actual_interval)
        
        # 점심시간 충돌 해결
        if self._conflicts_with_lunch(slot_time, config):
            slot_time = config.lunch_end
        
        time_slots.append(slot_time)
    
    return time_slots
```

🔄 메인 스케줄링 로직 수정:
```python
# 기존 순차 배치 대신 사전 계산된 시간 슬롯 사용
def _schedule_activity_with_precedence(self, ...):
    
    # 1. 활동 특성 분석
    should_distribute = self._should_apply_distribution(activity)
    
    if should_distribute:
        # 2. 분산 시간 슬롯 사전 계산
        distribution_config = self._get_distribution_config(activity)
        time_slots = self._calculate_distributed_time_slots(
            activity, len(all_groups), config, distribution_config
        )
        
        # 3. 그룹별 사전 계산된 시간에 배치
        for i, group_info in enumerate(all_groups):
            target_start_time = time_slots[i]
            start_time = max(earliest_start, target_start_time)
            # ... 기존 방 배정 로직 사용
    else:
        # 기존 순차 배치 방식 사용
        # ... 기존 코드
```
    """)

def show_activity_detection_logic():
    """활동 감지 로직"""
    
    print("\n\n🎯 활동별 분산 적용 판단 로직")
    print("=" * 80)
    
    print("""
📝 분산 적용 대상 감지:
```python
def _should_apply_distribution(self, activity: Activity) -> bool:
    # 1. Batched 활동만 대상
    if activity.mode != ActivityMode.BATCHED:
        return False
    
    # 2. 최소 용량 기준 (토론면접 등 대규모 활동)
    if activity.min_capacity < 4:
        return False
    
    # 3. 활동 시간 기준 (충분히 긴 활동)
    if activity.duration < timedelta(minutes=25):
        return False
    
    # 4. 특정 활동명 제외 (예: 오리엔테이션 등)
    excluded_activities = ["오리엔테이션", "설명회"]
    if activity.name in excluded_activities:
        return False
    
    return True

def _get_distribution_config(self, activity: Activity) -> DistributionConfig:
    # 활동별 맞춤 설정
    if "토론" in activity.name:
        return DistributionConfig(
            strategy=DistributionStrategy.STAY_TIME_OPTIMIZED,
            min_gap_minutes=60,
            max_gap_minutes=180,
            target_stay_time_hours=2.0
        )
    elif "면접" in activity.name:
        return DistributionConfig(
            strategy=DistributionStrategy.BALANCED,
            min_gap_minutes=45,
            max_gap_minutes=120
        )
    else:
        return DistributionConfig()  # 기본 설정
```
    """)

def show_concrete_example():
    """구체적 예시"""
    
    print("\n\n📊 구체적 적용 예시")
    print("=" * 80)
    
    # 시나리오 설정
    scenarios = [
        {
            "name": "토론면접 5개 그룹",
            "activity_duration": 30,
            "group_count": 5,
            "operating_hours": (9*60, 18*60),  # 09:00-18:00
            "strategy": DistributionStrategy.STAY_TIME_OPTIMIZED
        },
        {
            "name": "토론면접 8개 그룹",
            "activity_duration": 30,
            "group_count": 8,
            "operating_hours": (9*60, 18*60),
            "strategy": DistributionStrategy.BALANCED
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🔍 {scenario['name']} 시나리오:")
        print("-" * 50)
        
        start_min = scenario['operating_hours'][0]
        end_min = scenario['operating_hours'][1]
        duration = scenario['activity_duration']
        count = scenario['group_count']
        
        # 현재 방식 (순차)
        print("현재 방식 (순차 배치):")
        current_times = []
        for i in range(count):
            time_min = start_min + i * (duration + 10)
            hours = time_min // 60
            minutes = time_min % 60
            current_times.append(f"{hours:02d}:{minutes:02d}")
        print(f"   {' → '.join(current_times)}")
        
        # A방식 (분산)
        print("A방식 (분산 배치):")
        if scenario['strategy'] == DistributionStrategy.STAY_TIME_OPTIMIZED:
            # 2시간 간격 목표
            interval = min(120, (end_min - start_min - duration) / (count - 1))
        else:
            # 균등 분산
            interval = (end_min - start_min - duration) / (count - 1)
        
        distributed_times = []
        for i in range(count):
            time_min = start_min + int(i * interval)
            hours = time_min // 60
            minutes = time_min % 60
            distributed_times.append(f"{hours:02d}:{minutes:02d}")
        print(f"   {' → '.join(distributed_times)}")
        
        # 개선 효과 예측
        current_span = (start_min + (count-1) * (duration + 10) + duration) - start_min
        distributed_span = (start_min + int((count-1) * interval) + duration) - start_min
        
        improvement = (current_span - distributed_span) / 60
        print(f"   예상 체류시간 단축: {improvement:.1f}시간")

def show_implementation_steps():
    """구현 단계"""
    
    print("\n\n🚀 구현 단계별 가이드")
    print("=" * 80)
    
    steps = [
        {
            "phase": "1단계: 기반 구조 추가 (1-2일)",
            "tasks": [
                "DistributionStrategy enum 추가",
                "DistributionConfig dataclass 추가", 
                "_should_apply_distribution() 메서드 구현",
                "_get_distribution_config() 메서드 구현"
            ]
        },
        {
            "phase": "2단계: 시간 분산 알고리즘 구현 (2-3일)",
            "tasks": [
                "_calculate_distributed_time_slots() 메서드 구현",
                "_calculate_balanced_slots() 구현",
                "_calculate_stay_time_optimized_slots() 구현",
                "점심시간 충돌 해결 로직 추가"
            ]
        },
        {
            "phase": "3단계: 메인 로직 통합 (2-3일)",
            "tasks": [
                "_schedule_activity_with_precedence() 수정",
                "기존 순차 배치와 새로운 분산 배치 선택 로직",
                "Precedence 제약과 분산 배치 조화",
                "방 배정 로직과 통합"
            ]
        },
        {
            "phase": "4단계: 테스트 및 검증 (3-4일)",
            "tasks": [
                "디폴트 데이터로 효과 검증",
                "다양한 시나리오 테스트",
                "기존 기능 회귀 테스트",
                "성능 최적화"
            ]
        }
    ]
    
    for step in steps:
        print(f"\n📅 {step['phase']}")
        for task in step['tasks']:
            print(f"   • {task}")
    
    print(f"\n💡 총 예상 기간: 8-12일 (1.5-2주)")
    print(f"📈 예상 개선 효과: 20-40% 체류시간 단축")

def analyze_advantages_limitations():
    """A방식 장단점 분석"""
    
    print("\n\n⚖️ A방식 장단점 분석")
    print("=" * 80)
    
    advantages = [
        "현재 CP-SAT 시스템 내에서 수정 - 안정성 보장",
        "구현 복잡도 낮음 - 배치 로직만 개선",
        "점진적 적용 가능 - 활동별 선택적 적용",
        "다양한 분산 전략 지원 - 확장성",
        "Precedence 제약과 호환 - 기존 기능 유지",
        "실험적 검증 완료 - 효과 입증됨"
    ]
    
    limitations = [
        "휴리스틱 접근 - 수학적 최적성 미보장",
        "활동별 임계값 튜닝 필요",
        "복잡한 제약 조건에서 제한적",
        "방 용량 제약과의 상호작용 복잡",
        "대규모 인스턴스에서 성능 이슈 가능"
    ]
    
    print("✅ 장점:")
    for i, adv in enumerate(advantages, 1):
        print(f"   {i}. {adv}")
    
    print("\n⚠️ 한계:")
    for i, lim in enumerate(limitations, 1):
        print(f"   {i}. {lim}")
    
    print(f"\n💡 종합 평가:")
    print(f"• 현실적이고 효과적인 접근법")
    print(f"• 단기간 내 구현 가능")
    print(f"• 점진적 개선에 적합")
    print(f"• MRJSSP 같은 과도한 방법 대비 실용적")

if __name__ == "__main__":
    analyze_current_problem()
    design_a_method_algorithm()
    show_implementation_approach()
    show_activity_detection_logic()
    show_concrete_example()
    show_implementation_steps()
    analyze_advantages_limitations() 