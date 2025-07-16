#!/usr/bin/env python3
"""
체류 시간 하드 제약 통계적 기준 분석
응시자 체류 시간의 상한을 통계적 기준으로 설정하는 방법들을 검토
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class StayTimeConstraintAnalyzer:
    """체류 시간 제약 분석기"""
    
    def __init__(self, data_file: str = 'stay_time_individual_stats.xlsx'):
        """초기화"""
        self.df = pd.read_excel(data_file)
        self.stay_minutes = self.df['stay_duration_minutes'].values
        self.stay_hours = self.stay_minutes / 60
        
        print(f"📊 데이터 로드 완료: {len(self.df)}명 지원자")
        print(f"  - 평균 체류시간: {np.mean(self.stay_hours):.1f}시간")
        print(f"  - 최대 체류시간: {np.max(self.stay_hours):.1f}시간")
        print(f"  - 표준편차: {np.std(self.stay_hours):.1f}시간")
    
    def analyze_basic_statistics(self) -> Dict:
        """기본 통계 분석"""
        print("\n📈 기본 통계 분석")
        print("=" * 50)
        
        stats_dict = {
            'count': len(self.stay_hours),
            'mean': np.mean(self.stay_hours),
            'median': np.median(self.stay_hours),
            'std': np.std(self.stay_hours),
            'min': np.min(self.stay_hours),
            'max': np.max(self.stay_hours),
            'q25': np.percentile(self.stay_hours, 25),
            'q75': np.percentile(self.stay_hours, 75),
            'q90': np.percentile(self.stay_hours, 90),
            'q95': np.percentile(self.stay_hours, 95),
            'q99': np.percentile(self.stay_hours, 99)
        }
        
        print(f"  평균: {stats_dict['mean']:.1f}시간")
        print(f"  중간값: {stats_dict['median']:.1f}시간")
        print(f"  표준편차: {stats_dict['std']:.1f}시간")
        print(f"  75% 분위수: {stats_dict['q75']:.1f}시간")
        print(f"  90% 분위수: {stats_dict['q90']:.1f}시간")
        print(f"  95% 분위수: {stats_dict['q95']:.1f}시간")
        print(f"  99% 분위수: {stats_dict['q99']:.1f}시간")
        
        return stats_dict
    
    def analyze_job_based_constraints(self) -> Dict:
        """직무별 기반 제약 분석"""
        print("\n🏢 직무별 기반 제약 분석")
        print("=" * 50)
        
        job_stats = self.df.groupby('job_code')['stay_duration_minutes'].agg([
            'count', 'mean', 'median', 'std', 'min', 'max',
            lambda x: np.percentile(x, 90),
            lambda x: np.percentile(x, 95)
        ]).round(1)
        
        job_stats.columns = ['count', 'mean', 'median', 'std', 'min', 'max', 'q90', 'q95']
        job_stats['mean_hours'] = job_stats['mean'] / 60
        job_stats['q90_hours'] = job_stats['q90'] / 60
        job_stats['q95_hours'] = job_stats['q95'] / 60
        
        print("직무별 체류시간 통계 (시간 단위):")
        print(job_stats[['count', 'mean_hours', 'q90_hours', 'q95_hours', 'max']].round(1))
        
        # 직무별 권장 제약
        recommendations = {}
        for job_code in job_stats.index:
            q95_hours = job_stats.loc[job_code, 'q95_hours']
            max_hours = job_stats.loc[job_code, 'max'] / 60
            
            # 95% 분위수 + 여유분 (30분)
            recommended_constraint = min(q95_hours + 0.5, max_hours)
            
            recommendations[job_code] = {
                'q95_hours': q95_hours,
                'max_hours': max_hours,
                'recommended_constraint': recommended_constraint,
                'coverage_rate': len(self.df[(self.df['job_code'] == job_code) & 
                                           (self.df['stay_duration_minutes'] <= recommended_constraint * 60)]) / 
                                len(self.df[self.df['job_code'] == job_code]) * 100
            }
        
        print("\n직무별 권장 하드 제약:")
        for job_code, rec in recommendations.items():
            print(f"  {job_code}: {rec['recommended_constraint']:.1f}시간 "
                  f"(95% 분위수: {rec['q95_hours']:.1f}시간, 커버리지: {rec['coverage_rate']:.1f}%)")
        
        return recommendations
    
    def analyze_percentile_based_constraints(self) -> Dict:
        """분위수 기반 제약 분석"""
        print("\n📊 분위수 기반 제약 분석")
        print("=" * 50)
        
        percentiles = [85, 90, 92, 95, 97, 98, 99]
        constraints = {}
        
        for p in percentiles:
            constraint_hours = np.percentile(self.stay_hours, p)
            coverage_count = np.sum(self.stay_hours <= constraint_hours)
            coverage_rate = coverage_count / len(self.stay_hours) * 100
            
            constraints[p] = {
                'constraint_hours': constraint_hours,
                'coverage_count': coverage_count,
                'coverage_rate': coverage_rate,
                'excluded_count': len(self.stay_hours) - coverage_count
            }
        
        print("분위수별 하드 제약 분석:")
        for p, data in constraints.items():
            print(f"  {p}% 분위수: {data['constraint_hours']:.1f}시간 "
                  f"(커버리지: {data['coverage_rate']:.1f}%, 제외: {data['excluded_count']}명)")
        
        return constraints
    
    def analyze_standard_deviation_based_constraints(self) -> Dict:
        """표준편차 기반 제약 분석"""
        print("\n📏 표준편차 기반 제약 분석")
        print("=" * 50)
        
        mean_hours = np.mean(self.stay_hours)
        std_hours = np.std(self.stay_hours)
        
        std_constraints = {}
        for std_multiplier in [1.5, 2.0, 2.5, 3.0]:
            constraint_hours = mean_hours + (std_multiplier * std_hours)
            coverage_count = np.sum(self.stay_hours <= constraint_hours)
            coverage_rate = coverage_count / len(self.stay_hours) * 100
            
            std_constraints[std_multiplier] = {
                'constraint_hours': constraint_hours,
                'coverage_count': coverage_count,
                'coverage_rate': coverage_rate,
                'excluded_count': len(self.stay_hours) - coverage_count
            }
        
        print("표준편차 기반 하드 제약 분석:")
        for std_mult, data in std_constraints.items():
            print(f"  평균 + {std_mult}σ: {data['constraint_hours']:.1f}시간 "
                  f"(커버리지: {data['coverage_rate']:.1f}%, 제외: {data['excluded_count']}명)")
        
        return std_constraints
    
    def analyze_outlier_based_constraints(self) -> Dict:
        """이상치 기반 제약 분석"""
        print("\n🔍 이상치 기반 제약 분석")
        print("=" * 50)
        
        # IQR 방법으로 이상치 탐지
        Q1 = np.percentile(self.stay_hours, 25)
        Q3 = np.percentile(self.stay_hours, 75)
        IQR = Q3 - Q1
        
        # 이상치 기준
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # 수정된 Z-score 방법
        median_hours = np.median(self.stay_hours)
        mad = np.median(np.abs(self.stay_hours - median_hours))
        modified_z_scores = 0.6745 * (self.stay_hours - median_hours) / mad
        
        outlier_indices = np.abs(modified_z_scores) > 3.5
        
        outlier_constraints = {
            'iqr_upper_bound': upper_bound,
            'iqr_outlier_count': np.sum(self.stay_hours > upper_bound),
            'modified_z_outlier_count': np.sum(outlier_indices),
            'modified_z_threshold': median_hours + 3.5 * mad / 0.6745
        }
        
        print(f"IQR 상한: {upper_bound:.1f}시간 (이상치: {outlier_constraints['iqr_outlier_count']}명)")
        print(f"수정 Z-score 임계값: {outlier_constraints['modified_z_threshold']:.1f}시간 "
              f"(이상치: {outlier_constraints['modified_z_outlier_count']}명)")
        
        return outlier_constraints
    
    def analyze_adaptive_constraints(self) -> Dict:
        """적응형 제약 분석"""
        print("\n🔄 적응형 제약 분석")
        print("=" * 50)
        
        # 직무별 가중 평균
        job_weights = self.df.groupby('job_code').size() / len(self.df)
        
        # 직무별 95% 분위수 계산
        job_q95 = {}
        for job_code in self.df['job_code'].unique():
            job_data = self.df[self.df['job_code'] == job_code]['stay_duration_minutes'] / 60
            job_q95[job_code] = np.percentile(job_data, 95)
        
        # 가중 평균 제약
        weighted_constraint = sum(job_q95[job] * job_weights[job] for job in job_q95.keys())
        
        # 전체 95% 분위수
        overall_q95 = np.percentile(self.stay_hours, 95)
        
        # 적응형 제약 (가중 평균 + 전체 분위수의 조합)
        adaptive_constraint = 0.7 * weighted_constraint + 0.3 * overall_q95
        
        adaptive_constraints = {
            'weighted_constraint': weighted_constraint,
            'overall_q95': overall_q95,
            'adaptive_constraint': adaptive_constraint,
            'coverage_rate': np.sum(self.stay_hours <= adaptive_constraint) / len(self.stay_hours) * 100
        }
        
        print(f"가중 평균 제약: {weighted_constraint:.1f}시간")
        print(f"전체 95% 분위수: {overall_q95:.1f}시간")
        print(f"적응형 제약: {adaptive_constraint:.1f}시간 (커버리지: {adaptive_constraints['coverage_rate']:.1f}%)")
        
        return adaptive_constraints
    
    def recommend_constraint_strategies(self) -> Dict:
        """제약 전략 권장"""
        print("\n🎯 하드 제약 전략 권장")
        print("=" * 50)
        
        # 각 방법별 분석 실행
        basic_stats = self.analyze_basic_statistics()
        job_constraints = self.analyze_job_based_constraints()
        percentile_constraints = self.analyze_percentile_based_constraints()
        std_constraints = self.analyze_standard_deviation_based_constraints()
        outlier_constraints = self.analyze_outlier_based_constraints()
        adaptive_constraints = self.analyze_adaptive_constraints()
        
        # 전략별 권장사항
        strategies = {
            'conservative': {
                'method': '95% 분위수',
                'constraint': percentile_constraints[95]['constraint_hours'],
                'coverage': percentile_constraints[95]['coverage_rate'],
                'description': '보수적 접근 - 95% 지원자 커버'
            },
            'balanced': {
                'method': '적응형 제약',
                'constraint': adaptive_constraints['adaptive_constraint'],
                'coverage': adaptive_constraints['coverage_rate'],
                'description': '균형적 접근 - 직무별 특성 반영'
            },
            'aggressive': {
                'method': '90% 분위수',
                'constraint': percentile_constraints[90]['constraint_hours'],
                'coverage': percentile_constraints[90]['coverage_rate'],
                'description': '적극적 접근 - 90% 지원자 커버'
            },
            'outlier_based': {
                'method': '이상치 제거',
                'constraint': outlier_constraints['modified_z_threshold'],
                'coverage': np.sum(self.stay_hours <= outlier_constraints['modified_z_threshold']) / len(self.stay_hours) * 100,
                'description': '이상치 기반 - 통계적 이상치 제거'
            }
        }
        
        print("권장 전략:")
        for strategy_name, strategy_data in strategies.items():
            print(f"  {strategy_name.upper()}: {strategy_data['constraint']:.1f}시간 "
                  f"(커버리지: {strategy_data['coverage']:.1f}%)")
            print(f"    → {strategy_data['description']}")
        
        return strategies
    
    def generate_implementation_formula(self) -> str:
        """구현 공식 생성"""
        print("\n📝 구현 공식")
        print("=" * 50)
        
        # 동적 제약 계산 공식
        formula = """
# 동적 체류시간 하드 제약 계산 공식

def calculate_dynamic_stay_constraint(stay_times_data, strategy='balanced'):
    '''
    체류시간 데이터를 기반으로 동적 하드 제약 계산
    
    Parameters:
    - stay_times_data: 체류시간 데이터 (시간 단위)
    - strategy: 전략 ('conservative', 'balanced', 'aggressive', 'outlier_based')
    
    Returns:
    - constraint_hours: 권장 하드 제약 (시간)
    '''
    
    if strategy == 'conservative':
        # 95% 분위수 기반
        return np.percentile(stay_times_data, 95)
    
    elif strategy == 'balanced':
        # 직무별 가중 평균 + 전체 분위수 조합
        job_weights = job_data.groupby('job_code').size() / len(job_data)
        job_q95 = job_data.groupby('job_code')['stay_hours'].quantile(0.95)
        weighted_constraint = sum(job_q95[job] * job_weights[job] for job in job_q95.index)
        overall_q95 = np.percentile(stay_times_data, 95)
        return 0.7 * weighted_constraint + 0.3 * overall_q95
    
    elif strategy == 'aggressive':
        # 90% 분위수 기반
        return np.percentile(stay_times_data, 90)
    
    elif strategy == 'outlier_based':
        # 수정된 Z-score 기반 이상치 제거
        median_hours = np.median(stay_times_data)
        mad = np.median(np.abs(stay_times_data - median_hours))
        return median_hours + 3.5 * mad / 0.6745
    
    else:
        raise ValueError("지원하지 않는 전략입니다.")

# 사용 예시
constraint = calculate_dynamic_stay_constraint(stay_hours, strategy='balanced')
print(f"권장 하드 제약: {constraint:.1f}시간")
"""
        
        print(formula)
        return formula

def main():
    """메인 실행"""
    print("🔍 체류시간 하드 제약 통계적 기준 분석")
    print("=" * 80)
    
    # 분석기 초기화
    analyzer = StayTimeConstraintAnalyzer()
    
    # 전략 권장
    strategies = analyzer.recommend_constraint_strategies()
    
    # 구현 공식 생성
    analyzer.generate_implementation_formula()
    
    print("\n✅ 분석 완료!")
    print("\n💡 권장사항:")
    print("1. 초기에는 'balanced' 전략 사용 (직무별 특성 반영)")
    print("2. 운영 경험 축적 후 'conservative' 또는 'aggressive'로 조정")
    print("3. 정기적으로 데이터 재분석하여 제약값 업데이트")
    print("4. 직무별 차이가 클 경우 직무별 개별 제약 고려")

if __name__ == "__main__":
    main() 