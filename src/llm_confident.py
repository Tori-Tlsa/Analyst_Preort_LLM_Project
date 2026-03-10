"""
LLM Confident Module - 확신도 기반 점수 추출
Gemini 2.5 Flash를 사용하여 애널리스트 리포트에서 확신도(Confidence Score)와
판단 근거(Reasoning) 추출

이 모듈은 분석가의 전망에 대한 확신 수준을 정량화합니다.
- 강세전망(Bullish Outlook) 지표는 의도적으로 제거되었습니다
- 이유: 신뢰성을 위해 확신도(의견의 확실함)에만 집중
"""

import google.generativeai as genai
import re
import os
import logging
from typing import Tuple, Optional
import time

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LLMConfidentAnalyzer:
    """
    Gemini 기반 확신도(Confidence Score) 분석 엔진

    리포트 텍스트에서 분석가의 확신 수준(score_min ~ score_max)을 추출하고,
    그 근거(Reasoning)를 함께 반환합니다.

    주요 특징:
    - 정규화된 점수 범위 (기본값: 0~100)
    - JSON 형식 응답 파싱
    - Fallback 메커니즘 (JSON 파싱 실패 시 숫자 추출 시도)
    """

    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-flash",
                 score_min: int = 0, score_max: int = 100):
        """
        초기화

        Args:
            api_key: Gemini API 키 (없으면 환경변수에서 로드)
            model_name: 사용할 모델명 (기본값: gemini-2.5-flash)
            score_min: 확신도 최소 범위 (기본값: 0)
            score_max: 확신도 최대 범위 (기본값: 100)

        Raises:
            ValueError: API 키가 없을 경우
        """
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경변수를 설정해주세요.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.score_min = score_min
        self.score_max = score_max
        self.model_name = model_name

        logger.info(f"✅ Gemini LLM 초기화 완료 (모델: {model_name}, 범위: {score_min}~{score_max})")

    def analyze_confidence(self, text: str) -> Optional[Tuple[float, str]]:
        """
        텍스트에서 확신도 점수와 판단 근거를 추출합니다.

        Args:
            text: 분석 대상 리포트 본문 (최대 1500자 사용)

        Returns:
            Tuple[confidence_score (float), reasoning_str (str)] 또는 None
            - confidence_score: score_min ~ score_max 범위의 정수
            - reasoning_str: 확신도 근거를 설명하는 텍스트 (2-3문장)
        """
        try:
            if not isinstance(text, str) or not text.strip():
                logger.warning("⚠️ 빈 텍스트 입력")
                return None

            # 프롬프트: 정규화된 점수 범위를 동적으로 포함
            prompt = f"""당신은 금융 분석가의 텍스트를 분석하는 NLP 전문가입니다.

아래 애널리스트 리포트를 읽고 분석가의 '확신도(Confidence Level)'를 평가하세요.

**확신도(Confidence Level) 평가 기준:**
- {self.score_min}점: 매우 불확실 (헤징 표현 다수, "~할 수 있다" 등 조건부 표현, 모호한 전망)
- {(self.score_min + self.score_max) // 2}점: 중간 (일부 확실한 근거 있음, 부분적 헤징)
- {self.score_max}점: 매우 확실 (명확한 수치 근거, 단호한 표현, 강한 확신)

**출력 형식 (JSON):**
{{"confidence": <숫자만>, "reason": "<확신도 근거를 2-3문장으로>"}}

리포트 내용:
{text[:1500]}
"""
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # JSON 파싱: confidence와 reason 추출
            match = re.search(
                r'\{\s*["\']?confidence["\']?\s*:\s*(\d+).*?["\']?reason["\']?\s*:\s*["\'](.+?)["\']?\s*\}',
                response_text,
                re.DOTALL | re.IGNORECASE
            )

            if match:
                confidence = int(match.group(1))
                reason = match.group(2).strip()

                # 범위 강제
                confidence = max(self.score_min, min(self.score_max, confidence))

                logger.info(f"✅ 확신도 추출: {confidence}점, 근거: {reason[:50]}...")
                return confidence, reason
            else:
                # Fallback: 숫자만 추출
                scores = re.findall(r'\b(\d{1,3})\b', response_text)
                if scores:
                    confidence = int(scores[0])
                    confidence = max(self.score_min, min(self.score_max, confidence))
                    logger.warning(f"⚠️ JSON 파싱 실패, 숫자 fallback: {confidence}점")
                    return confidence, "(근거 자동 생성 실패)"

                logger.error(f"❌ 확신도/근거 추출 실패. 응답: {response_text[:100]}")
                return None

        except Exception as e:
            logger.error(f"❌ Gemini API 호출 중 오류: {e}")
            return None

    def normalize_score(self, confidence: float) -> Optional[float]:
        """
        점수를 0-1 범위로 정규화합니다.

        Args:
            confidence: 확신도 점수 (score_min ~ score_max)

        Returns:
            정규화된 값 (0.0 ~ 1.0) 또는 None
        """
        if confidence is None:
            return None
        if self.score_max == self.score_min:
            return 0.0
        return (confidence - self.score_min) / (self.score_max - self.score_min)
