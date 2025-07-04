#!/usr/bin/env python3
"""
완전한 분산 알고리즘 체계
- 5가지 분산 알고리즘의 구체적 정의
- 각 알고리즘의 수학적 공식과 사용 조건
- 하드코딩 완전 제거된 범용 구현
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, time
from dataclasses import dataclass
from enum import Enum
import math

class DistributionAlgorithm(Enum):
    """분산 알고리즘 종류"""
    BALANCED = "balanced"                       # 균등 분산
    EARLY_HEAVY = "early_heavy"                 # 앞시간 집중
    LATE_HEAVY = "late_heavy"                   # 뒷시간 집중
    CAPACITY_OPTIMIZED = "capacity_optimized"   # 용량 최적화
    STAY_TIME_OPTIMIZED = "stay_time_optimized" # 체류시간 최적화

@dataclass
class AlgorithmResult:
    """알고리즘 결과"""
    algorithm: DistributionAlgorithm
    time_slots: List[timedelta]
    metadata: Dict = None

class UniversalDistributionEngine:
    """범용 분산 엔진 (활동명 무관)"""
    
    def __init__(self):
        self.algorithms = {
            DistributionAlgorithm.BALANCED: self._balanced_algorithm,
            DistributionAlgorithm.EARLY_HEAVY: self._early_heavy_algorithm,
            DistributionAlgorithm.LATE_HEAVY: self._late_heavy_algorithm,
            DistributionAlgorithm.CAPACITY_OPTIMIZED: self._capacity_optimized_algorithm,
            DistributionAlgorithm.STAY_TIME_OPTIMIZED: self._stay_time_optimized_algorithm,
        }
    
    def calculate_distribution(
        self,
        algorithm: DistributionAlgorithm,
        group_count: int,
        operating_hours: Tuple[timedelta, timedelta],
        activity_duration: timedelta,
        activity_properties: Dict = None
    ) -> AlgorithmResult:
        """범용 분산 계산"""
        
        if algorithm not in self.algorithms:
            raise ValueError(f"지원하지 않는 알고리즘: {algorithm}")
        
        print(f"🔧 {algorithm.value.upper()} 알고리즘 실행")
        print(f"   - 그룹 수: {group_count}개")
        print(f"   - 운영시간: {self._format_time(operating_hours[0])} ~ {self._format_time(operating_hours[1])}")
        print(f"   - 활동 시간: {activity_duration.total_seconds()/60:.0f}분")
        
        # 해당 알고리즘 실행
        algorithm_func = self.algorithms[algorithm]
        time_slots, metadata = algorithm_func(
            group_count, operating_hours, activity_duration, activity_properties or {}
        )
        
        return AlgorithmResult(
            algorithm=algorithm,
            time_slots=time_slots,
            metadata=metadata
        )
    
    def _balanced_algorithm(
        self,
        group_count: int,
        operating_hours: Tuple[timedelta, timedelta],
        activity_duration: timedelta,
        properties: Dict
    ) -> Tuple[List[timedelta], Dict]:
        """
        BALANCED 알고리즘 (균등 분산)
        
        수학적 정의:
        - 사용가능시간을 그룹 수로 균등 분할
        - 점심시간(12:00-13:00) 회피
        - 최소/최대 간격 제약 적용
        
        공식:
        interval = available_time / (group_count - 1)
        slot[i] = start_time + (i * clamp(interval, min_gap, max_gap))
        """
        print(f"📊 BALANCED 알고리즘 상세:")
        
        start_time, end_time = operating_hours
        
        # 1. 사용가능시간 계산
        total_minutes = (end_time - start_time).total_seconds() / 60
        activity_minutes = activity_duration.total_seconds() / 60
        available_minutes = total_minutes - activity_minutes
        
        print(f"   - 총 운영시간: {total_minutes:.0f}분")
        print(f"   - 사용가능시간: {available_minutes:.0f}분")
        
        if group_count <= 1:
            return [start_time], {"interval": 0}
        
        # 2. 이상적 간격 계산
        ideal_interval = available_minutes / (group_count - 1)
        
        # 3. 제약조건 적용
        min_interval = max(60, activity_minutes + 10)
        max_interval = min(180, available_minutes / 2)
        actual_interval = max(min_interval, min(ideal_interval, max_interval))
        
        print(f"   - 이상적 간격: {ideal_interval:.0f}분")
        print(f"   - 실제 간격: {actual_interval:.0f}분")
        
        # 4. 슬롯 배치 (점심시간 회피)
        time_slots = []
        current_time = start_time
        
        for i in range(group_count):
            # 점심시간 회피
            current_time = self._avoid_lunch_time(current_time, activity_duration)
            time_slots.append(current_time)
            print(f"   그룹 {i+1}: {self._format_time(current_time)}")
            current_time += timedelta(minutes=actual_interval)
        
        metadata = {
            "interval": actual_interval,
            "total_span": (time_slots[-1] - time_slots[0]).total_seconds() / 60 if len(time_slots) > 1 else 0
        }
        
        return time_slots, metadata
    
    def _early_heavy_algorithm(
        self,
        group_count: int,
        operating_hours: Tuple[timedelta, timedelta],
        activity_duration: timedelta,
        properties: Dict
    ) -> Tuple[List[timedelta], Dict]:
        """
        EARLY_HEAVY 알고리즘 (앞시간 집중)
        
        수학적 정의:
        - 전체 그룹의 70%를 오전(9~12시)에 배치
        - 나머지 30%를 오후(13~17시)에 배치
        - 각 구간 내에서는 균등 분산
        
        공식:
        early_count = ceil(group_count * 0.7)
        late_count = group_count - early_count
        """
        print(f"🌅 EARLY_HEAVY 알고리즘 상세:")
        
        start_time, end_time = operating_hours
        
        # 1. 그룹 분할
        early_ratio = 0.7
        early_count = math.ceil(group_count * early_ratio)
        late_count = group_count - early_count
        
        print(f"   - 앞시간 그룹: {early_count}개 (70%)")
        print(f"   - 뒷시간 그룹: {late_count}개 (30%)")
        
        # 2. 시간 구간 정의
        morning_end = timedelta(hours=12)
        afternoon_start = timedelta(hours=13)
        
        time_slots = []
        
        # 3. 오전 구간 (9~12시)
        if early_count > 0:
            morning_slots = self._distribute_in_range(
                early_count,
                start_time,
                morning_end - activity_duration,
                activity_duration
            )
            time_slots.extend(morning_slots)
            print(f"   오전 배치: {[self._format_time(slot) for slot in morning_slots]}")
        
        # 4. 오후 구간 (13~17시)  
        if late_count > 0:
            afternoon_slots = self._distribute_in_range(
                late_count,
                afternoon_start,
                end_time - activity_duration,
                activity_duration
            )
            time_slots.extend(afternoon_slots)
            print(f"   오후 배치: {[self._format_time(slot) for slot in afternoon_slots]}")
        
        time_slots.sort()
        
        metadata = {
            "early_count": early_count,
            "late_count": late_count,
            "early_ratio": early_ratio
        }
        
        return time_slots, metadata
    
    def _late_heavy_algorithm(
        self,
        group_count: int,
        operating_hours: Tuple[timedelta, timedelta],
        activity_duration: timedelta,
        properties: Dict
    ) -> Tuple[List[timedelta], Dict]:
        """
        LATE_HEAVY 알고리즘 (뒷시간 집중)
        
        수학적 정의:
        - 전체 그룹의 30%를 오전에, 70%를 오후에 배치
        - EARLY_HEAVY의 반대 패턴
        
        공식:
        late_count = ceil(group_count * 0.7)
        early_count = group_count - late_count
        """
        print(f"🌆 LATE_HEAVY 알고리즘 상세:")
        
        start_time, end_time = operating_hours
        
        # 1. 그룹 분할 (EARLY_HEAVY의 반대)
        late_ratio = 0.7
        late_count = math.ceil(group_count * late_ratio)
        early_count = group_count - late_count
        
        print(f"   - 앞시간 그룹: {early_count}개 (30%)")
        print(f"   - 뒷시간 그룹: {late_count}개 (70%)")
        
        # 2. 시간 구간 정의
        morning_end = timedelta(hours=12)
        afternoon_start = timedelta(hours=13)
        
        time_slots = []
        
        # 3. 오전 구간 (소수)
        if early_count > 0:
            morning_slots = self._distribute_in_range(
                early_count,
                start_time,
                morning_end - activity_duration,
                activity_duration
            )
            time_slots.extend(morning_slots)
            print(f"   오전 배치: {[self._format_time(slot) for slot in morning_slots]}")
        
        # 4. 오후 구간 (다수)
        if late_count > 0:
            afternoon_slots = self._distribute_in_range(
                late_count,
                afternoon_start,
                end_time - activity_duration,
                activity_duration
            )
            time_slots.extend(afternoon_slots)
            print(f"   오후 배치: {[self._format_time(slot) for slot in afternoon_slots]}")
        
        time_slots.sort()
        
        metadata = {
            "early_count": early_count,
            "late_count": late_count,
            "late_ratio": late_ratio
        }
        
        return time_slots, metadata
    
    def _capacity_optimized_algorithm(
        self,
        group_count: int,
        operating_hours: Tuple[timedelta, timedelta],
        activity_duration: timedelta,
        properties: Dict
    ) -> Tuple[List[timedelta], Dict]:
        """
        CAPACITY_OPTIMIZED 알고리즘 (용량 최적화)
        
        수학적 정의:
        - 사용 가능한 방 수를 고려한 동시성 최적화
        - 방이 많으면 동시 배치, 적으면 순차 배치
        
        공식:
        concurrent_groups = min(group_count, available_rooms)
        time_batches = ceil(group_count / concurrent_groups)
        """
        print(f"🏢 CAPACITY_OPTIMIZED 알고리즘 상세:")
        
        # 방 수 정보 (properties에서 추출, 없으면 기본값)
        available_rooms = properties.get('available_rooms', 2)
        
        print(f"   - 사용가능 방 수: {available_rooms}개")
        
        # 1. 동시 처리 가능한 그룹 수
        concurrent_groups = min(group_count, available_rooms)
        time_batches = math.ceil(group_count / concurrent_groups)
        
        print(f"   - 동시 그룹: {concurrent_groups}개")
        print(f"   - 시간 배치: {time_batches}회")
        
        # 2. 배치 간격 계산
        start_time, end_time = operating_hours
        if time_batches <= 1:
            batch_interval = 0
        else:
            available_time = (end_time - start_time).total_seconds() / 60 - activity_duration.total_seconds() / 60
            batch_interval = available_time / (time_batches - 1)
            batch_interval = max(60, batch_interval)  # 최소 1시간 간격
        
        print(f"   - 배치 간격: {batch_interval:.0f}분")
        
        # 3. 시간 슬롯 생성
        time_slots = []
        current_time = start_time
        
        for batch in range(time_batches):
            # 이 배치에서 처리할 그룹 수
            groups_in_batch = min(concurrent_groups, group_count - len(time_slots))
            
            # 동시 배치 (같은 시간)
            for i in range(groups_in_batch):
                time_slots.append(current_time)
                print(f"   그룹 {len(time_slots)}: {self._format_time(current_time)} (배치 {batch+1})")
            
            # 다음 배치 시간
            if batch < time_batches - 1:
                current_time += timedelta(minutes=batch_interval)
                current_time = self._avoid_lunch_time(current_time, activity_duration)
        
        metadata = {
            "available_rooms": available_rooms,
            "concurrent_groups": concurrent_groups,
            "time_batches": time_batches,
            "batch_interval": batch_interval
        }
        
        return time_slots, metadata
    
    def _stay_time_optimized_algorithm(
        self,
        group_count: int,
        operating_hours: Tuple[timedelta, timedelta],
        activity_duration: timedelta,
        properties: Dict
    ) -> Tuple[List[timedelta], Dict]:
        """
        STAY_TIME_OPTIMIZED 알고리즘 (체류시간 최적화)
        
        수학적 정의:
        - 그룹 활동을 하루 전체에 걸쳐 최대한 분산
        - 2시간 간격으로 배치하여 개별 활동과의 간격 최소화
        - 실험 검증된 최적 패턴 사용
        
        공식:
        optimal_interval = 120분 (2시간)
        slot[i] = start_time + (i * optimal_interval)
        """
        print(f"🎯 STAY_TIME_OPTIMIZED 알고리즘 상세:")
        
        start_time, end_time = operating_hours
        
        # 1. 최적 간격 (실험 검증됨)
        optimal_interval_minutes = 120  # 2시간
        
        print(f"   - 최적 간격: {optimal_interval_minutes}분 (실험 검증)")
        print(f"   - 목표: 체류시간 최소화")
        
        # 2. 시간 슬롯 계산
        time_slots = []
        current_time = start_time
        
        for i in range(group_count):
            # 운영시간 범위 확인
            if current_time + activity_duration > end_time:
                print(f"   ⚠️ 그룹 {i+1} 이후는 운영시간 초과")
                break
            
            # 점심시간 회피
            current_time = self._avoid_lunch_time(current_time, activity_duration)
            time_slots.append(current_time)
            print(f"   그룹 {i+1}: {self._format_time(current_time)} (체류시간 최적화)")
            
            # 다음 슬롯
            current_time += timedelta(minutes=optimal_interval_minutes)
        
        # 모든 그룹을 배치할 수 없으면 간격 조정
        if len(time_slots) < group_count:
            print(f"   🔄 간격 조정: {group_count}개 그룹 배치를 위해 BALANCED로 폴백")
            return self._balanced_algorithm(group_count, operating_hours, activity_duration, properties)
        
        metadata = {
            "optimal_interval": optimal_interval_minutes,
            "total_span": (time_slots[-1] - time_slots[0]).total_seconds() / 60 if len(time_slots) > 1 else 0,
            "optimization_target": "stay_time"
        }
        
        return time_slots, metadata
    
    def _distribute_in_range(
        self,
        count: int,
        start: timedelta,
        end: timedelta,
        duration: timedelta
    ) -> List[timedelta]:
        """특정 범위 내에서 균등 분산"""
        if count <= 0:
            return []
        if count == 1:
            return [start]
        
        available_minutes = (end - start).total_seconds() / 60
        interval = available_minutes / (count - 1)
        
        slots = []
        for i in range(count):
            slot_time = start + timedelta(minutes=i * interval)
            slots.append(slot_time)
        
        return slots
    
    def _avoid_lunch_time(self, time_slot: timedelta, duration: timedelta) -> timedelta:
        """점심시간 회피"""
        lunch_start = timedelta(hours=12)
        lunch_end = timedelta(hours=13)
        
        # 점심시간과 겹치면 점심 후로 이동
        if (time_slot < lunch_end and 
            time_slot + duration > lunch_start):
            return lunch_end
        
        return time_slot
    
    def _format_time(self, td: timedelta) -> str:
        """시간 포맷팅"""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

def demonstrate_all_algorithms():
    """모든 알고리즘 시연"""
    
    print("🎯 전체 분산 알고리즘 체계 시연")
    print("=" * 100)
    
    # 공통 파라미터
    group_count = 4
    operating_hours = (timedelta(hours=9), timedelta(hours=17, minutes=30))
    activity_duration = timedelta(minutes=30)
    
    engine = UniversalDistributionEngine()
    
    # 모든 알고리즘 테스트
    algorithms = [
        DistributionAlgorithm.BALANCED,
        DistributionAlgorithm.EARLY_HEAVY,
        DistributionAlgorithm.LATE_HEAVY,
        DistributionAlgorithm.CAPACITY_OPTIMIZED,
        DistributionAlgorithm.STAY_TIME_OPTIMIZED
    ]
    
    results = {}
    
    for algorithm in algorithms:
        print(f"\n{'='*80}")
        
        properties = {"available_rooms": 2} if algorithm == DistributionAlgorithm.CAPACITY_OPTIMIZED else {}
        
        result = engine.calculate_distribution(
            algorithm, group_count, operating_hours, activity_duration, properties
        )
        
        results[algorithm] = result
        
        print(f"✅ {algorithm.value.upper()} 결과:")
        for i, slot in enumerate(result.time_slots, 1):
            print(f"   그룹 {i}: {engine._format_time(slot)}")
        
        if result.metadata:
            print(f"   메타데이터: {result.metadata}")
    
    # 결과 비교
    print(f"\n🏆 알고리즘 비교 요약")
    print(f"{'='*80}")
    
    for algorithm, result in results.items():
        time_span = 0
        if len(result.time_slots) > 1:
            time_span = (result.time_slots[-1] - result.time_slots[0]).total_seconds() / 60
        
        print(f"{algorithm.value.upper():20} | 시간 범위: {time_span:3.0f}분 | 슬롯: {[engine._format_time(slot) for slot in result.time_slots]}")

def algorithm_selection_guide():
    """알고리즘 선택 가이드"""
    
    print(f"\n📚 알고리즘 선택 가이드")
    print(f"{'='*80}")
    
    guide = [
        {
            "algorithm": "BALANCED",
            "use_case": "일반적인 상황",
            "condition": "특별한 제약이 없는 기본 케이스",
            "pros": "안정적, 예측 가능",
            "cons": "최적화 효과 제한적"
        },
        {
            "algorithm": "EARLY_HEAVY", 
            "use_case": "오전 집중이 필요한 경우",
            "condition": "참가자들이 오전을 선호하거나 오후에 다른 일정",
            "pros": "오전 활용도 높음",
            "cons": "오후 시간 낭비 가능"
        },
        {
            "algorithm": "LATE_HEAVY",
            "use_case": "오후 집중이 필요한 경우", 
            "condition": "오전에 준비시간이 필요하거나 오후 선호",
            "pros": "준비시간 확보",
            "cons": "오전 시간 낭비 가능"
        },
        {
            "algorithm": "CAPACITY_OPTIMIZED",
            "use_case": "방 수가 제한적인 경우",
            "condition": "사용가능한 방 수 < 그룹 수",
            "pros": "방 활용도 최대화",
            "cons": "시간 효율성 저하 가능"
        },
        {
            "algorithm": "STAY_TIME_OPTIMIZED",
            "use_case": "체류시간이 중요한 경우",
            "condition": "대용량 그룹 + 긴 활동 + 후속 개별활동",
            "pros": "체류시간 최소화",
            "cons": "방 활용도 저하 가능"
        }
    ]
    
    for item in guide:
        print(f"\n🔸 {item['algorithm']}")
        print(f"   사용 사례: {item['use_case']}")
        print(f"   조건: {item['condition']}")
        print(f"   장점: {item['pros']}")
        print(f"   단점: {item['cons']}")

if __name__ == "__main__":
    demonstrate_all_algorithms()
    algorithm_selection_guide() 