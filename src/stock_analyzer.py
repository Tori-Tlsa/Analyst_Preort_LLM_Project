"""
Stock Analyzer Module - 주식 데이터 수집 및 변동성 계산

이 모듈은 yfinance를 사용하여 주가 데이터를 수집하고 변동성을 계산합니다.

핵심 기능:
1. yfinance API 호출 시 Rate Limit & Retry (Exponential Backoff)
2. 유효하지 않은 티커 및 상장폐지 종목 처리
3. 결측치 Forward Fill 보간
4. 분기 종료 후 t+1 (1개월) 변동성 계산
5. 상세 로깅

방법론:
- 변동성(Volatility): 분기 마지막 날짜(t)부터 t+1(1개월 후)까지의 일일 수익률 표준편차
  이는 분석가 의견 공개 후 시장의 실제 변동성을 측정
"""

import yfinance as yf
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
from typing import Optional

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def quarter_to_date(year_quarter: str) -> pd.Timestamp:
    """
    YYYY-Q 형식을 분기 마지막 날짜로 변환

    Args:
        year_quarter: 'YYYY-Q' 형식 (예: '2024-1' 또는 '2024-Q1')

    Returns:
        pd.Timestamp: 분기 마지막 날짜
    """
    try:
        parts = year_quarter.replace('Q', '').split('-')
        year = int(parts[0])
        quarter = int(parts[1])
        if quarter == 1:
            return pd.Timestamp(year, 3, 31)
        elif quarter == 2:
            return pd.Timestamp(year, 6, 30)
        elif quarter == 3:
            return pd.Timestamp(year, 9, 30)
        elif quarter == 4:
            return pd.Timestamp(year, 12, 31)
    except Exception:
        pass
    return pd.NaT


def _download_with_retry(ticker: str, start: str, end: str,
                         max_retries: int = 5, backoff_factor: float = 0.5) -> pd.DataFrame:
    """
    yfinance 다운로드에 재시도 로직과 간단한 지수 백오프를 적용.
    RateLimitError가 나거나 네트워크 연결이 불안할 때 유용.
    """
    for attempt in range(1, max_retries + 1):
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            return df
        except Exception as e:
            logger.warning(f"[{ticker}] yfinance 다운로드 실패 (시도 {attempt}): {e}")
            sleep_time = backoff_factor * (2 ** (attempt - 1))
            time.sleep(sleep_time)
    logger.error(f"[{ticker}] yfinance 다운로드 완료 실패 after {max_retries} attempts")
    return pd.DataFrame()


def calculate_volatility(ticker: str, start_date: str, end_date: str) -> float:
    """
    주어진 기간의 주식 변동성(일일 수익률 표준편차) 계산

    에러 핸들링:
    * 티커가 잘못되었거나 delisted 된 경우 NaN을 반환
    * 다운로드 중 에러가 발생하면 재시도 및 로그 출력
    * 누락일은 전일 종가로 보간(fwd fill)하여 계산

    Args:
        ticker: 주식 티커 (예: '005930.KS')
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        변동성 수치 또는 np.nan
    """
    if not isinstance(ticker, str) or not ticker:
        logger.error("유효하지 않은 티커 전달됨")
        return np.nan

    data = _download_with_retry(ticker, start_date, end_date)
    if data.empty or 'Close' not in data.columns:
        logger.warning(f"[{ticker}] 데이터가 비어있거나 Close 컬럼이 없음")
        return np.nan

    # forward fill 결측치
    data['Close'] = data['Close'].ffill()

    if data['Close'].isna().all() or len(data['Close']) < 2:
        return np.nan

    daily_returns = data['Close'].pct_change().dropna()
    if daily_returns.empty:
        return np.nan
    return daily_returns.std()


def calculate_post_quarter_volatility(
    ticker: str,
    quarter_end_date: pd.Timestamp
) -> float:
    """
    [핵심 함수] 분기 종료 후 t+1 (1개월) 변동성 계산

    분석가 의견이 시장에 공개된 분기 마지막 날(t)로부터
    1개월(t+1) 동안의 주가 변동성을 계산합니다.

    이는 LLM 확신도와 시장 변동성의 관계를 측정하기 위한 핵심 지표입니다.

    Args:
        ticker: 주식 티커
        quarter_end_date: 분기 마지막 날짜 (pd.Timestamp)

    Returns:
        float: 변동성 (표준편차) 또는 np.nan

    Example:
        >>> vol = calculate_post_quarter_volatility('005930.KS', pd.Timestamp(2024, 3, 31))
        >>> print(f"변동성: {vol:.6f}")
    """
    if pd.isna(quarter_end_date):
        logger.warning("⚠️ 유효하지 않은 분기 날짜")
        return np.nan

    # t+1 (1개월 후)까지의 기간 설정
    start = quarter_end_date
    end = quarter_end_date + pd.DateOffset(months=1)

    return calculate_volatility(
        ticker,
        start.strftime('%Y-%m-%d'),
        end.strftime('%Y-%m-%d')
    )


def get_stock_ticker_mapping() -> dict:
    """
    한국 주요 기업의 KOSPI/KOSDAQ 티커 매핑

    Returns:
        dict: {회사명: 티커}

    참고:
    - .KS: KOSPI (한국거래소)
    - .KQ: KOSDAQ (코스닥)
    """
    return {
        'LG디스플레이': '034220.KS',
        'LG에너지솔루션': '373220.KS',
        'LG유플러스': '032640.KS',
        'LG전자': '066570.KS',
        'LG화학': '051910.KS',
        'POSCO홀딩스': '005490.KS',
        'SK이노베이션': '096770.KS',
        'SK텔레콤': '017670.KS',
        'SK하이닉스': '000660.KS',
        '기아': '000270.KS',
        '대한항공': '003490.KS',
        '두산에너빌리티': '034020.KS',
        '롯데케미칼': '011170.KS',
        '삼성SDI': '006400.KS',
        '삼성물산': '028260.KS',
        '삼성바이오로직스': '207940.KS',
        '삼성전기': '009150.KS',
        '삼성전자': '005930.KS',
        '삼성중공업': '010140.KS',
        '셀트리온': '068270.KS',
        '신세계': '004170.KS',
        '아모레퍼시픽': '090430.KS',
        '카카오': '035720.KS',
        '카카오게임즈': '293490.KS',
        '쿠쿠홈시스': '284740.KS',
        '한온시스템': '018880.KS',
        '한진칼': '180640.KS',
        '한화에어로스페이스': '012450.KS',
        'KB금융': '105560.KS',
        'NH투자증권': '005940.KS',
        '하나금융지주': '086790.KS',
        '한화': '012450.KS',
        '현대모비스': '012330.KS',
        '효성': '004800.KS',
    }
