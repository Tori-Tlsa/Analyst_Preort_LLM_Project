# 📊 Analyst Report LLM Pipeline & Volatility Prediction
[![Award](https://img.shields.io/badge/Award-최우수논문상-gold.svg)]()

> **LLM 기반 애널리스트 리포트 확신도 정량화 및 주가 변동성 예측 머신러닝 파이프라인**
> 비정형 텍스트 데이터(애널리스트 리포트)의 정성적 뉘앙스를 **Gemini 2.5 Flash**를 활용해 수치화하고, 이를 바탕으로 기업별/분기별 주가 변동성을 예측합니다.

## 💡 Background & Motivation
**"애널리스트 리포트의 행간에 숨겨진 진짜 뉘앙스를 수치화할 수 없을까?"**

시장에는 매일 수많은 증권사 리포트가 쏟아지지만, 대부분 '매수(Buy)' 의견에 편향되어 있어 실제 투자 지표로 활용하기 까다로운 비정형 데이터입니다. 

본 프로젝트는 이러한 한계를 극복하기 위해 다음과 같은 아이디어에서 출발했습니다.
1. **문제 제기:** 단순한 단어 빈도수(TF-IDF)나 감성 분석으로는 리포트에 담긴 분석가의 '진짜 확신'을 파악하기 어렵다.
2. **해결책 (LLM 도입):** 뛰어난 문맥 파악 능력을 가진 **LLM(Gemini 2.5 Flash)**이 리포트를 직접 읽고, 논리적 근거의 탄탄함을 평가해 **'확신도(Confidence Score)'**라는 정량적 지표로 변환하게 만들자.
3. **가치 창출:** 이렇게 수치화된 확신도와 분석가들 사이의 의견 불일치(표준편차) 데이터를 전통적인 퀀트(Quant) 모델에 결합하여, 향후 주가의 변동성(Volatility)을 더 정확하게 예측해 보자.

## 🏆 Project Highlights
- **[최우수논문상 수상] 2025년 정보기술학회 추계 종합 학술대회 및 대학생 논문 경진대회**
- **비정형 데이터의 정량화:** 애널리스트 리포트 내 강세 전망(Bullish) 편향을 통제하고, 순수한 '확신도(Confidence Score, 0~100)'만 추출하는 프롬프트 엔지니어링 적용
- **시장 불확실성 지표 도출:** 개별 리포트를 기업-분기(Firm-Quarter) 단위로 집계하여 분석가 간의 **의견 불일치 정도(`LLM_std`)**를 새로운 변동성 예측 변수로 생성
- **예측 성능 입증:** 기존 재무 지표(EPS, PER 등) 기반 Baseline 모델 대비, LLM 변수를 추가한 모델(XGBoost)의 **예측 성능(R²)이 8.43% 향상**됨을 증명 (Ablation Study)

## 🏗️ Data Pipeline Architecture
본 프로젝트는 데이터 수집부터 최종 모델 평가까지의 End-to-End 파이프라인을 포함합니다.

1. **Data Collection & OCR:** 네이버 금융 리포트 PDF 크롤링 및 텍스트 추출 (`pdfminer`)
2. **LLM Inference:** Gemini 2.5 Flash API를 통한 확신도 점수 및 판단 근거(Reasoning) 추출
3. **Feature Engineering:** 기업-분기별 데이터 집계 및 `yfinance` API를 통한 주가 변동성 매핑
4. **Modeling & Evaluation:** XGBoost 기반 학습 및 전통 재무 변수와의 중요도(Feature Importance) 비교

## 📈 Key Results
- **Baseline Model (전통 재무 지표):** R² = 0.427
- **Augmented Model (재무 지표 + LLM 확신도/표준편차):** R² = 0.463
- **Performance Gain:** **ΔR² = 0.036 (상대적 개선도 8.43% 🚀)**
> *LLM이 추출한 '애널리스트의 텍스트 뉘앙스'가 실제 주가 변동성을 예측하는 데 유의미한 알파(Alpha) 창출 변수임을 확인했습니다.*

## 📁 Repository Structure
```text
├── src/                          # 파이프라인 핵심 모듈
│   ├── llm_confident.py          # Gemini API 기반 확신도 추출 로직
│   ├── data_processor.py         # Firm-Quarter 데이터 집계
│   ├── stock_analyzer.py         # 주가 데이터 수집 및 변동성 계산 (Rate Limit 처리)
│   └── crawler.py                # 리포트 PDF 크롤링 및 OCR 변환
├── notebooks/                    # 단계별 실행 및 시각화 노트북 (00~04)
├── config.yaml                   # LLM 프롬프트, API, 경로 설정
└── requirements.txt              # 의존성 패키지
```
*(💡 원본 데이터셋 및 임시 파일은 용량 문제로 `.gitignore` 처리되어 있으며, 코드 실행 시 자동 생성됩니다.)*

## 🚀 Quick Start
### 1. Prerequisites
```bash
git clone https://github.com/Tori-Tlsa/Analyst_Preort_LLM_Project.git
cd Analyst_Preort_LLM_Project
pip install -r requirements.txt
```

### 2. Configuration
프로젝트 루트에 `.env` 파일을 생성하고 발급받은 Gemini API 키를 입력합니다.
```env
GEMINI_API_KEY="your_api_key_here"
```

### 3. Execution
`notebooks/00_main_workflow.ipynb` 파일을 열어 전체 파이프라인의 실행 흐름을 확인하고 구동할 수 있습니다. 각 세부 모듈의 단위 테스트 및 시각화는 01~04번 노트북을 참고하세요.

## 🛠️ Tech Stack
- **LLM/AI:** Google Gemini 2.5 Flash
- **Machine Learning:** XGBoost, Scikit-learn
- **Data Engineering:** Pandas, yfinance, pdfminer.six, BeautifulSoup4
