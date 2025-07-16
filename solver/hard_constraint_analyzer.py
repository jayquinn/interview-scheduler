#!/usr/bin/env python3
"""
날짜별 90% 분위수 하드 제약 분석기
1차 스케줄링 결과를 분석하여 날짜별 하드 제약값을 산출
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date
import logging

class HardConstraintAnalyzer:
    """날짜별 하드 제약 분석기"""
    
    def __init__(self, percentile: float = 90.0):
        """
        초기화
        
        Args:
            percentile: 사용할 분위수 (기본값: 90.0)
        """
        self.percentile = percentile
        self.logger = logging.getLogger(__name__)
        
    def analyze_stay_times_by_date(self, schedule_df: pd.DataFrame) -> Dict:
        """
        스케줄 결과에서 날짜별 체류시간 분석
        
        Args:
            schedule_df: 스케줄 DataFrame
            
        Returns:
            날짜별 분석 결과
        """
        if schedule_df.empty:
            self.logger.warning("빈 스케줄 데이터")
            return {}
        
        # 지원자별 체류시간 계산
        stay_times = self._calculate_stay_times(schedule_df)
        
        if stay_times.empty:
            self.logger.warning("체류시간을 계산할 수 있는 데이터가 없습니다")
            return {}
        
        # 날짜별로 그룹화하여 분석
        date_analysis = {}
        
        for interview_date, group_data in stay_times.groupby('interview_date'):
            stay_hours = group_data['stay_hours'].values
            
            if len(stay_hours) == 0:
                continue
                
            # 통계 계산
            stats = {
                'count': len(stay_hours),
                'mean': np.mean(stay_hours),
                'median': np.median(stay_hours),
                'std': np.std(stay_hours),
                'min': np.min(stay_hours),
                'max': np.max(stay_hours),
                'q25': np.percentile(stay_hours, 25),
                'q75': np.percentile(stay_hours, 75),
                f'q{int(self.percentile)}': np.percentile(stay_hours, self.percentile),
                'q95': np.percentile(stay_hours, 95),
                'q99': np.percentile(stay_hours, 99)
            }
            
            # 하드 제약값 설정 (90% 분위수)
            hard_constraint = stats[f'q{int(self.percentile)}']
            
            # 초과자 분석
            exceed_count = np.sum(stay_hours > hard_constraint)
            exceed_rate = exceed_count / len(stay_hours) * 100
            
            date_analysis[interview_date] = {
                'stats': stats,
                'hard_constraint_hours': hard_constraint,
                'exceed_count': exceed_count,
                'exceed_rate': exceed_rate,
                'stay_times': stay_hours.tolist()
            }
            
            self.logger.info(f"날짜 {interview_date}: "
                           f"제약값 {hard_constraint:.1f}시간, "
                           f"초과자 {exceed_count}명 ({exceed_rate:.1f}%)")
        
        return date_analysis
    
    def _calculate_stay_times(self, schedule_df: pd.DataFrame) -> pd.DataFrame:
        """
        지원자별 체류시간 계산
        
        Args:
            schedule_df: 스케줄 DataFrame
            
        Returns:
            지원자별 체류시간 DataFrame
        """
        stay_data = []
        
        # 지원자별로 그룹화
        for applicant_id in schedule_df['applicant_id'].unique():
            applicant_data = schedule_df[schedule_df['applicant_id'] == applicant_id]
            
            if applicant_data.empty:
                continue
            
            # 더미 지원자 제외
            if str(applicant_id).startswith('dummy'):
                continue
            
            # 시간 정보 수집
            all_start_times = []
            all_end_times = []
            
            for _, row in applicant_data.iterrows():
                try:
                    start_time = row['start_time']
                    end_time = row['end_time']
                    
                    # 시간 형식 변환
                    if isinstance(start_time, str):
                        start_time = pd.to_datetime(start_time, format='%H:%M:%S').time()
                    if isinstance(end_time, str):
                        end_time = pd.to_datetime(end_time, format='%H:%M:%S').time()
                    
                    # timedelta로 변환
                    from datetime import timedelta
                    if hasattr(start_time, 'hour'):
                        start_td = timedelta(hours=start_time.hour, minutes=start_time.minute, seconds=start_time.second)
                    else:
                        # 이미 timedelta인 경우
                        start_td = start_time
                        
                    if hasattr(end_time, 'hour'):
                        end_td = timedelta(hours=end_time.hour, minutes=end_time.minute, seconds=end_time.second)
                    else:
                        # 이미 timedelta인 경우
                        end_td = end_time
                    
                    all_start_times.append(start_td)
                    all_end_times.append(end_td)
                    
                except Exception as e:
                    self.logger.debug(f"시간 파싱 오류 (applicant_id: {applicant_id}): {e}")
                    continue
            
            if all_start_times and all_end_times:
                # 전체 체류시간 = 첫 번째 활동 시작 ~ 마지막 활동 종료
                total_start = min(all_start_times)
                total_end = max(all_end_times)
                # 5분 단위로 라운딩
                stay_duration_minutes = (total_end - total_start).total_seconds() / 60
                stay_duration_hours = round(stay_duration_minutes / 5) * 5 / 60
                
                # 메타 정보
                interview_date = applicant_data['interview_date'].iloc[0]
                job_code = applicant_data['job_code'].iloc[0]
                
                stay_data.append({
                    'applicant_id': applicant_id,
                    'interview_date': interview_date,
                    'job_code': job_code,
                    'stay_hours': stay_duration_hours,
                    'start_time': total_start,
                    'end_time': total_end,
                    'activity_count': len(applicant_data)
                })
        
        return pd.DataFrame(stay_data)
    
    def generate_constraint_report(self, date_analysis: Dict) -> pd.DataFrame:
        """
        제약 분석 리포트 생성
        Args:
            date_analysis: 날짜별 분석 결과
        Returns:
            제약 분석 리포트 DataFrame
        """
        if not date_analysis:
            return pd.DataFrame()
        report_data = []
        for interview_date, analysis in date_analysis.items():
            stats = analysis['stats']
            report_data.append({
                'interview_date': interview_date,
                'applicant_count': stats['count'],
                'mean_stay_hours': round(stats['mean'], 2),
                'median_stay_hours': round(stats['median'], 2),
                'min_stay_hours': round(stats['min'], 2),
                'max_stay_hours': round(stats['max'], 2),
                'std_stay_hours': round(stats['std'], 2),
                f'q{int(self.percentile)}_hours': round(stats[f'q{int(self.percentile)}'], 2),
                'q95_hours': round(stats['q95'], 2),
                'hard_constraint_hours': round(analysis['hard_constraint_hours'], 2),
                'exceed_count': analysis['exceed_count'],
                'exceed_rate': round(analysis['exceed_rate'], 1),
                'percentile': self.percentile  # 항상 포함
            })
        report_df = pd.DataFrame(report_data)
        # 날짜 순으로 정렬
        report_df['interview_date'] = pd.to_datetime(report_df['interview_date'])
        report_df = report_df.sort_values('interview_date')
        return report_df
    
    def get_hard_constraints(self, date_analysis: Dict) -> Dict[str, float]:
        """
        날짜별 하드 제약값 추출
        
        Args:
            date_analysis: 날짜별 분석 결과
            
        Returns:
            날짜별 하드 제약값 딕셔너리
        """
        constraints = {}
        
        for interview_date, analysis in date_analysis.items():
            constraints[str(interview_date)] = analysis['hard_constraint_hours']
        
        return constraints
    
    def validate_constraints(self, date_analysis: Dict, 
                           min_applicants: int = 5,
                           max_exceed_rate: float = 15.0) -> Dict:
        """
        제약값 유효성 검증
        
        Args:
            date_analysis: 날짜별 분석 결과
            min_applicants: 최소 지원자 수 (분위수 신뢰도)
            max_exceed_rate: 최대 허용 초과율 (%)
            
        Returns:
            검증 결과
        """
        validation_results = {}
        
        for interview_date, analysis in date_analysis.items():
            stats = analysis['stats']
            exceed_rate = analysis['exceed_rate']
            
            issues = []
            
            # 지원자 수 검증
            if stats['count'] < min_applicants:
                issues.append(f"지원자 수 부족 ({stats['count']}명 < {min_applicants}명)")
            
            # 초과율 검증
            if exceed_rate > max_exceed_rate:
                issues.append(f"초과율 높음 ({exceed_rate:.1f}% > {max_exceed_rate}%)")
            
            # 제약값이 너무 낮은지 검증 (최소 2시간)
            if analysis['hard_constraint_hours'] < 2.0:
                issues.append(f"제약값 너무 낮음 ({analysis['hard_constraint_hours']:.1f}시간 < 2.0시간)")
            
            validation_results[str(interview_date)] = {
                'is_valid': len(issues) == 0,
                'issues': issues,
                'recommendation': self._generate_recommendation(issues, analysis)
            }
        
        return validation_results
    
    def _generate_recommendation(self, issues: List[str], analysis: Dict) -> str:
        """권장사항 생성"""
        if not issues:
            return "제약값 적절함"
        
        recommendations = []
        
        for issue in issues:
            if "지원자 수 부족" in issue:
                recommendations.append("더 많은 지원자 데이터 필요 또는 수동 제약 설정 고려")
            elif "초과율 높음" in issue:
                recommendations.append("분위수를 상향 조정 고려 (예: 95%)")
            elif "제약값 너무 낮음" in issue:
                recommendations.append("최소 제약값 설정 필요")
        
        return "; ".join(recommendations) if recommendations else "추가 검토 필요" 