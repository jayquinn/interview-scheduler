# 면접 스케줄링 시스템 체류시간 최적화: 수학적 접근법 제안

## 🚨 **현재 CAPACITY_OPTIMIZED의 치명적 문제점**

### 📋 제약 조건 분석 결과
```python
# 현재 시스템의 실제 제약 조건
직무별_방_격리 = {
    "직무A": ["토론면접실A1", "토론면접실A2"],  # A방만 사용 가능
    "직무B": ["토론면접실B1", "토론면접실B2"],  # B방만 사용 가능
    "직무C": ["토론면접실C1"]                 # C방만 사용 가능
}

# CAPACITY_OPTIMIZED가 가정하는 것 (잘못됨)
전체_방_풀 = ["토론면접실A1", "토론면접실A2", "토론면접실B1", "토론면접실B2", "토론면접실C1"]
# ❌ 모든 직무가 모든 방을 사용할 수 있다고 잘못 가정
```

### ❌ **CAPACITY_OPTIMIZED 실현 불가능 판정**
1. **직무별 방 격리 무시**: 직무A는 A방만 사용 가능한데 전체 방 개수로 계산
2. **동시 진행 가능성 과대평가**: 같은 접미사 방 내에서만 동시 진행 가능  
3. **자원 제약 모델링 오류**: 전역 방 풀이 아닌 접미사별 방 풀이 실제 제약

---

## 🎯 **추천 수학적 방법론 (우선순위별)**

### 🥇 **1순위: Multi-Resource JSSP with Machine Eligibility**

**선택 이유:**
- 현재 문제와 **정확히 매칭**
- 직무별 방 제약을 자연스럽게 모델링
- 수학적으로 엄밀하고 최적해 보장 가능

**수학적 모델링:**
```
문제 정의:
- J = {jobs}, M = {machines/rooms}, T = {time slots}
- E(j,m) = 1 if job j can use machine m (eligibility)
- 목적함수: minimize Σ(체류시간)

제약 조건:
1. x[j,m,t] ∈ {0,1}: job j가 machine m에서 time t에 시작
2. Σ(m,t) x[j,m,t] = 1: 각 job은 정확히 한 번 스케줄
3. x[j,m,t] ≤ E(j,m): 적격성 제약 (직무별 방 제약)
4. Σ(j) x[j,m,t] ≤ 1: 자원 제약 (방 용량)
5. 선후행 제약: 발표준비 → 발표면접
```

**구현 방법:**
- **OR-Tools CP-SAT** + 커스텀 제약
- 예상 구현 기간: **4-6주**
- 예상 개선: **20-40% 체류시간 단축**

---

### 🥈 **2순위: Hybrid MILP-CP Decomposition**

**접근법:**
```
마스터 문제 (MILP): 전체 시간 배치 최적화
- 변수: 각 그룹의 시작 시간
- 목적함수: 체류시간 최소화
- 제약: 운영시간, 기본 선후행

서브 문제 (CP): 제약 만족 검증
- 방 할당 실현 가능성 확인
- 직무별 방 제약 만족
- 자원 용량 제약 확인
```

**장점:**
- MILP의 최적성 + CP의 제약 처리력
- 복잡한 제약을 CP로 깔끔하게 처리
- 모듈화로 유지보수 용이

---

### 🥉 **3순위: Constraint Programming with Global Constraints**

**빠른 구현 접근법:**
```python
# OR-Tools CP-SAT 순수 구현
model = cp_model.CpModel()

# 인터벌 변수: 각 그룹의 시간 구간
intervals = {}
for group in groups:
    intervals[group] = model.NewIntervalVar(
        start, duration, end, f'group_{group}'
    )

# 글로벌 제약: 방 용량 + 직무별 적격성
for room_suffix in ['A', 'B', 'C']:
    eligible_groups = get_eligible_groups(room_suffix)
    model.AddNoOverlap([intervals[g] for g in eligible_groups])
```

**장점:**
- 구현 기간: **2-3주**
- 위험도: **낮음**
- 기존 OR-Tools 활용

---

## 🔬 **구체적 구현 제안**

### 📅 **Phase 1 (2-3주): CP 프로토타입**
```python
def create_cp_model_with_eligibility():
    """직무별 방 제약을 고려한 CP 모델"""
    model = cp_model.CpModel()
    
    # 1. 그룹별 인터벌 변수 생성
    intervals = create_group_intervals(model, groups)
    
    # 2. 직무별 방 적격성 제약
    for suffix in room_suffixes:
        eligible_intervals = get_eligible_intervals(intervals, suffix)
        available_rooms = get_rooms_by_suffix(suffix)
        
        # 용량 제약: 동시에 사용 가능한 방 수 제한
        model.AddCumulative(
            eligible_intervals, 
            demands=[1] * len(eligible_intervals),
            capacity=len(available_rooms)
        )
    
    # 3. 선후행 제약
    add_precedence_constraints(model, intervals)
    
    # 4. 체류시간 최소화 목적함수
    minimize_stay_time(model, intervals)
    
    return model
```

### 📅 **Phase 2 (4-6주): 완전한 JSSP 구현**
- Machine Eligibility 완전 구현
- 다양한 목적함수 지원
- 성능 최적화

---

## 📊 **예상 성과**

### 🎯 **정량적 목표**
| 방법론 | 구현 기간 | 체류시간 단축 | 위험도 | 비용 |
|--------|-----------|---------------|--------|------|
| CP 프로토타입 | 2-3주 | 10-25% | 낮음 | 낮음 |
| JSSP 완전 구현 | 4-6주 | 20-40% | 중간 | 중간 |
| Hybrid 접근 | 5-7주 | 15-30% | 높음 | 높음 |

### 📈 **실험 기반 추정**
- **현재 최대 체류시간**: 6.8시간
- **목표 최대 체류시간**: 4.0시간 이하
- **3시간+ 체류자 비율**: 30.7% → 10% 이하

---

## 🚀 **실행 계획**

### 🔥 **즉시 실행 가능 (1주일)**
```python
# 1. 현재 CAPACITY_OPTIMIZED 알고리즘 제거
# 2. BALANCED 알고리즘을 접미사별로 개선
def improved_balanced_with_eligibility():
    """접미사별 BALANCED 알고리즘"""
    for suffix in room_suffixes:
        eligible_groups = get_groups_by_suffix(suffix)
        available_rooms = get_rooms_by_suffix(suffix)
        
        # 접미사별 균등 분산
        distribute_groups_evenly(eligible_groups, available_rooms)
```

### 🎯 **중기 계획 (1-2개월)**
1. **Week 1-2**: CP 프로토타입 구현
2. **Week 3-4**: 성능 테스트 및 튜닝  
3. **Week 5-6**: JSSP 완전 구현
4. **Week 7-8**: 실환경 테스트

### 🏆 **장기 비전 (3-6개월)**
- 실시간 재스케줄링 지원
- 다목적 최적화 (체류시간 + 만족도)
- AI 기반 수요 예측 통합

---

## 💡 **결론 및 권고사항**

### ✅ **즉시 조치 필요**
1. **CAPACITY_OPTIMIZED 알고리즘 사용 중단**
2. **Multi-Resource JSSP 방법론 적용 시작**
3. **CP-based 프로토타입 우선 구현**

### 🎯 **실용적 접근**
- 이론적 완벽성보다는 **점진적 개선**
- 기존 시스템과의 **호환성 유지**  
- **측정 가능한 개선 목표** 설정

### 🔬 **장기적 투자**
- 수학적으로 엄밀한 방법론으로 **근본적 해결**
- 확장 가능한 아키텍처로 **미래 요구사항 대응**
- **산업 표준 수준**의 최적화 성능 달성 