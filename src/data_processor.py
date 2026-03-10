"""
Data Processor Module - 데이터 전처리 및 통계 변수 생성

이 모듈은 LLM 추출 점수를 정제하고, 기업-분기(Firm-Quarter) 단위로 집계하여
통계 변수를 생성합니다.

핵심 기능:
1. 결측값 처리 (mean, forward_fill, drop)
2. 컬럼명 표준화
3. Firm-Quarter 집계를 통한 LLM_avg, LLM_std 생성 (핵심)
4. 수치형 데이터 정규화 (Z-score)

방법론:
- LLM_avg: 기업-분기 내 평균 확신도 (분석가들의 평균 확신 수준)
- LLM_std: 기업-분기 내 확신도 표준편차 (분석가들 간 의견 불일치 정도)
"""

import pandas as pd
import numpy as np
import logging

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def rename_financial_columns(df: pd.DataFrame, rename_map: dict) -> pd.DataFrame:
    """
    금융 데이터 컬럼명 표준화

    Args:
        df: 입력 DataFrame
        rename_map: 컬럼명 매핑 딕셔너리 (기존명 -> 새로운명)

    Returns:
        DataFrame: 컬럼명이 변경된 DataFrame
    """
    df_renamed = df.rename(columns=rename_map)
    changed = [v for k, v in rename_map.items() if k in df.columns]
    logger.info(f"✅ 컬럼명 표준화 완료: {changed}")
    return df_renamed


def select_final_columns(df: pd.DataFrame, final_columns: list) -> pd.DataFrame:
    """
    최종 분석에 필요한 컬럼만 선택

    Args:
        df: 입력 DataFrame
        final_columns: 선택할 컬럼명 리스트

    Returns:
        DataFrame: 선택된 컬럼만 포함한 DataFrame
    """
    available_cols = [c for c in final_columns if c in df.columns]
    missing_cols = [c for c in final_columns if c not in df.columns]
    if missing_cols:
        logger.warning(f"⚠️ 존재하지 않는 컬럼 (제외됨): {missing_cols}")
    return df[available_cols]


def fill_missing_values(df: pd.DataFrame, method: str = 'mean') -> pd.DataFrame:
    """
    결측값 처리

    Args:
        df: 입력 DataFrame
        method: 처리 방법
            - 'mean': 각 숫자형 컬럼의 평균값으로 대체
            - 'forward_fill': 이전 값으로 대체
            - 'drop': 결측값 행 제거

    Returns:
        DataFrame: 결측값이 처리된 DataFrame
    """
    df_filled = df.copy()
    before_count = df_filled.isnull().sum().sum()

    if method == 'mean':
        numeric_cols = df_filled.select_dtypes(include=[np.number]).columns
        df_filled[numeric_cols] = df_filled[numeric_cols].fillna(df_filled[numeric_cols].mean())
    elif method == 'forward_fill':
        df_filled = df_filled.fillna(method='ffill')
    elif method == 'drop':
        df_filled = df_filled.dropna()
        logger.info(f"✅ 결측값 제거: {len(df)} → {len(df_filled)} 행")
        return df_filled
    else:
        logger.warning(f"⚠️ 알 수 없는 method: {method}")
        return df_filled

    after_count = df_filled.isnull().sum().sum()
    logger.info(f"✅ 결측값 처리 (method='{method}'): {before_count} → {after_count}")
    return df_filled


def aggregate_confidence_by_firm_quarter(
    df: pd.DataFrame,
    firm_col: str = 'company',
    quarter_col: str = 'year_quarter',
    score_col: str = 'confidence_score'
) -> pd.DataFrame:
    """
    [핵심 함수] 기업-분기(Firm-Quarter) 단위 집계로 LLM_avg, LLM_std 생성

    개별 애널리스트 리포트의 확신도 점수를 기업-분기 단위로 집계하여,
    각 분기 내 평균 확신도(LLM_avg)와 표준편차(LLM_std)를 계산합니다.

    통계적 의미:
    - LLM_avg: 해당 분기 분석가들의 평균적인 확신 수준
    - LLM_std: 분석가들 간의 의견 불일치 정도 (disagreement)
      → 높은 LLM_std는 분석가 간 의견이 엇갈림을 의미
      → 낮은 LLM_std는 분석가 간 의견이 일치함을 의미

    Args:
        df: 원본 리포트 데이터 (각 행 = 개별 리포트/분석가)
        firm_col: 기업명 컬럼 (기본값: 'company')
        quarter_col: 분기 컬럼명 (기본값: 'year_quarter', 형식: '2024-Q1')
        score_col: 확신도 점수 컬럼 (기본값: 'confidence_score')

    Returns:
        DataFrame: 다음 컬럼 포함
            - {firm_col}: 기업명
            - {quarter_col}: 연도-분기 (예: '2024-Q1')
            - LLM_avg: 평균 확신도
            - LLM_std: 확신도 표준편차
            - count: 해당 분기 보고서 수

    Raises:
        ValueError: 필수 컬럼이 존재하지 않을 경우

    Example:
        >>> df = pd.DataFrame({
        ...     'company': ['Samsung', 'Samsung'],
        ...     'year_quarter': ['2024-Q1', '2024-Q1'],
        ...     'confidence_score': [75.0, 85.0]
        ... })
        >>> agg = aggregate_confidence_by_firm_quarter(df)
        >>> print(agg)
            company year_quarter  LLM_avg  LLM_std  count
        0  Samsung       2024-Q1     80.0      7.07      2
    """
    # 필수 컬럼 확인
    if firm_col not in df.columns or quarter_col not in df.columns or score_col not in df.columns:
        raise ValueError(f"필수 컬럼 누락: {firm_col}, {quarter_col}, {score_col}")

    # Firm-Quarter 그룹별 집계
    grouped = df.groupby([firm_col, quarter_col])[score_col].agg(
        ['mean', 'std', 'count']
    )
    grouped = grouped.rename(columns={'mean': 'LLM_avg', 'std': 'LLM_std', 'count': 'report_count'})
    grouped = grouped.reset_index()

    # 단일 보고서인 경우 LLM_std = NaN → 0으로 처리 (의견 불일치 없음)
    grouped['LLM_std'] = grouped['LLM_std'].fillna(0.0)

    logger.info(f"✅ Firm-Quarter 집계 완료: {len(grouped)} 개 기업-분기 조합 생성")
    logger.info(f"   - LLM_avg 범위: {grouped['LLM_avg'].min():.2f} ~ {grouped['LLM_avg'].max():.2f}")
    logger.info(f"   - LLM_std 범위: {grouped['LLM_std'].min():.2f} ~ {grouped['LLM_std'].max():.2f}")
    logger.info(f"   - 평균 보고서 수/분기: {grouped['report_count'].mean():.1f}")

    return grouped


def standardize_numeric_columns(df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
    """
    숫자형 컬럼 표준화 (Z-score: 평균=0, 표준편차=1)

    Args:
        df: 입력 DataFrame
        columns: 표준화할 컬럼명 리스트 (None이면 모든 숫자형 컬럼)

    Returns:
        DataFrame: Z-score 표준화된 DataFrame
    """
    df_std = df.copy()

    if columns is None:
        columns = df_std.select_dtypes(include=[np.number]).columns.tolist()

    for col in columns:
        if col in df_std.columns:
            mean = df_std[col].mean()
            std_val = df_std[col].std()
            if std_val != 0:
                df_std[col] = (df_std[col] - mean) / std_val
            else:
                logger.warning(f"⚠️ '{col}' 표준편차=0 (표준화 스킵)")

    logger.info(f"✅ Z-score 표준화 완료: {len(columns)} 개 컬럼")
    return df_std
