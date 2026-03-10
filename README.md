# 📊 LLM 기반 애널리스트 리포트 확신도 정량화 및 주가 변동성 예측 파이프라인

> **Analyst Report Confidence Quantification and Stock Volatility Prediction Pipeline using Large Language Models**

---

## 🎯 프로젝트 개요

### 프로젝트 소개

이 프로젝트는 **애널리스트 리포트의 정성적 뉘앙스를 LLM으로 정량화**하여 **주가 변동성을 예측**하는 엔드-투-엔드 머신러닝 파이프라인입니다.

### 핵심 특징

- **정성 → 정량화**: Gemini 2.5 Flash LLM을 활용하여 분석가의 **확신도(Confidence Score)**를 0-100점으로 정량화
- **Firm-Quarter 집계**: 개별 리포트를 기업-분기 단위로 집계하여 **LLM_avg**, **LLM_std** (의견 불일치) 생성
- **Robust Error Handling**: yfinance API의 Rate Limit, 유효하지 않은 티커, 결측치 보간 등 실무적 에러 처리
- **Ablation Study**: 전통 재무 변수만 사용한 모델 대비 LLM 변수 추가 시 R² 개선도 정량화 (0.427 → 0.463)

### 데이터 소스

| 데이터 종류 | 소스 | 용도 |
|-----------|-----|------|
| **리포트 텍스트** | Naver Finance | 애널리스트 보고서 수집 (PDF) |
| **회사 메타데이터** | FnGuide, DataGuide | 기업 기본정보, 재무지표 |
| **목표가/추천** | ValueSearch | 전통적 투자 의견 |
| **주가 데이터** | yfinance | 시계열 주가, 변동성 계산 |
| **LLM 분석** | Google Gemini 2.5 Flash | 확신도 점수 추출 |

---

## 📁 프로젝트 구조

```
analyst-report-ml-pipeline/
│
├── src/                            # Python 모듈화 (재사용성, 테스트용)
│   ├── __init__.py
│   ├── llm_confident.py            # [Step 1] LLM 확신도 추출 (Confidence + Reasoning)
│   ├── data_processor.py           # [Step 2] Firm-Quarter 집계 (LLM_avg, LLM_std)
│   ├── stock_analyzer.py           # [Step 3] 변동성 계산 (Robust Error Handling)
│   ├── crawler.py                  # Naver 크롤링, PDF 다운로드
│   └── ocr_processor.py            # PDF → 텍스트 변환 (pdfminer)
│
├── notebooks/                      # Jupyter 노트북 (실행 & 시각화)
│   ├── 00_main_workflow.ipynb      # 📍 시작점: 전체 파이프라인 오버뷰
│   ├── 01_report_collection.ipynb  # 리포트 수집 & OCR 처리
│   ├── 02_llm_confident.ipynb      # LLM 확신도 추출 (Confidence + Reasoning)
│   ├── 03_data_preprocessing.ipynb # Firm-Quarter 집계 & 통계 변수 생성
│   └── 04_volatility_analysis.ipynb# 변동성 계산 & Ablation Study
│
├── data/                           # 데이터 디렉토리
│   ├── raw/                        # 원본 리포트
│   │   └── [기업명]/
│   │       ├── pdf/                # 다운로드된 PDF
│   │       ├── txt/                # OCR 변환 텍스트
│   │       └── [기업명]_report_text.xlsx  # 메타데이터 + 텍스트
│   ├── processed/                  # 처리된 데이터
│   │   ├── [기업명]_with_scores.csv       # LLM 점수 추출 후
│   │   └── final_dataset_standardized.csv # Firm-Quarter 집계 결과
│   └── reports/                    # 최종 분석 결과
│       ├── volatility_analysis_sample.csv
│       ├── volatility_scatter.png
│       └── ablation_study_comparison.png  # 📈 R² 개선도
│
├── config.yaml                     # 설정 (API, 경로, 점수 범위)
├── requirements.txt                # Python 의존성
├── .env.example                    # 환경변수 템플릿
└── README.md                       # 이 파일
```

---

---

## 📖 상세 사용 가이드

### 파이프라인 상세 설명

#### Step 1: LLM 확신도 추출 (`src/llm_confident.py`)

**목표**: 애널리스트 리포트 본문에서 **확신도(Confidence Score)**와 **판단 근거(Reasoning)** 추출

**특징**:
- ✅ Gemini 2.5 Flash API를 사용한 LLM 기반 분석
- ✅ 강세전망(Bullish Outlook) 제거 → **확신도에만 집중** (신뢰성 향상)
- ✅ JSON 형식 응답 파싱 + Fallback 메커니즘
- ✅ 동적 점수 범위: config.yaml에서 0~100 또는 1~5 등 자유로운 범위 설정 가능

**메소드**:
```python
analyzer = LLMConfidentAnalyzer(api_key=os.getenv("GEMINI_API_KEY"))
confidence, reasoning = analyzer.analyze_confidence(report_text)
# 반환: (75.0, "분석가가 명확한 수치 근거를 제시했으므로...")
```

**입출력**:
- 입력: `data/raw/[기업명]_report_text.xlsx`
- 출력: `data/processed/[기업명]_with_scores.csv`
  - 컬럼: confidence_score, reasoning

#### Step 2: Firm-Quarter 집계 (`src/data_processor.py`)

**목표**: 개별 리포트 점수를 **기업-분기(Firm-Quarter)** 단위로 집계하여 통계 변수 생성

**핵심 통계 변수**:

| 변수 | 설명 | 수식 | 의미 |
|-----|------|------|------|
| **LLM_avg** | 평균 확신도 | $\frac{1}{N_t} \sum_{i=1}^{N_t} \text{Confidence}_i$ | 분기 내 분석가들의 평균적인 확신 수준 |
| **LLM_std** | 확신도 표준편차 | $\sqrt{\frac{1}{N_t} \sum_{i=1}^{N_t} (\text{Confidence}_i - \text{LLM_avg})^2}$ | 분석가들 간의 의견 불일치(Disagreement) 정도 |

여기서 $t$는 분기, $N_t$는 해당 분기 보고서 수

**메소드**:
```python
from src.data_processor import aggregate_confidence_by_firm_quarter

agg_df = aggregate_confidence_by_firm_quarter(
    df,
    firm_col='company',
    quarter_col='year_quarter',
    score_col='confidence_score'
)
# 결과: company, year_quarter, LLM_avg, LLM_std, report_count
```

**입출력**:
- 입력: `data/processed/[기업명]_with_scores.csv`
- 출력: `data/processed/final_dataset_standardized.csv`

#### Step 3: 주가 변동성 계산 (`src/stock_analyzer.py`)

**목표**: yfinance에서 주가 데이터를 수집하고 **분기 종료 후 1개월(t+1) 변동성** 계산

**Robust Error Handling 기능**:
- ✅ **Rate Limit Retry**: Exponential Backoff (2^n초 대기)
- ✅ **유효성 검사**: 잘못된 티커, 상장폐지 종목 → try-except 처리 + 로깅
- ✅ **결측치 보간**: Forward Fill로 거래 없는 날 데이터 보완
- ✅ **분기 종료 후 t+1 변동성**: 분기 마지막 날(t)부터 1개월(t+1) 후까지의 일일 수익률 표준편차

**메소드**:
```python
from src.stock_analyzer import calculate_post_quarter_volatility

volatility = calculate_post_quarter_volatility(
    ticker='005930.KS',
    quarter_end_date=pd.Timestamp(2024, 3, 31)
)
# t = 2024-03-31, t+1 = 2024-04-30
# 반환: 0.0245 (약 2.45% 일일 변동성)
```

**변동성 계산 공식**:

$$\sigma_{t \to t+1} = \sqrt{\frac{1}{D-1} \sum_{d=1}^{D} (r_d - \bar{r})^2}$$

여기서:
- $r_d$: d번째 거래일의 수익률 (일일 수익률 = $\frac{P_d - P_{d-1}}{P_{d-1}}$)
- $\bar{r}$: 평균 수익률
- $D$: 기간 내 거래일 수

#### Step 4-5: 변동성 분석 & Ablation Study (`notebooks/04_volatility_analysis.ipynb`)

**목표**: LLM 변수가 변동성 예측 모델 성능을 얼마나 개선하는지 정량화

**Ablation Study 구성**:

#### Baseline 모델 (전통 재무 변수만 사용)
- 입력 변수: EPS, PER, PBR 등 전통적 지표
- 모델: XGBoost
- 성능: R² = 0.427

#### Augmented 모델 (LLM 변수 추가)
- 입력 변수: EPS, PER, PBR, **LLM_avg**, **LLM_std**
- 모델: XGBoost (동일 하이퍼파라미터)
- 성능: R² = 0.463

#### 개선도
- **ΔR² = 0.463 - 0.427 = 0.036**
- **상대 개선도 = 0.036 / 0.427 = 8.43%**

이는 LLM 기반 확신도 변수가 **8.43% 의 모델 성능 개선**을 가져옴을 의미합니다.

**시각화**:
- 📊 Baseline vs Augmented R² 비교 바 차트
- 📈 LLM_avg, LLM_std와 변동성의 산점도
- 🔥 피어슨 상관계수 히트맵

---

## 🚀 설치 및 실행

### 사전 요구사항

```bash
# Python 3.10+ 확인
python --version

# 프로젝트 클론
git clone https://github.com/your-org/analyst-report-ml-pipeline.git
cd analyst-report-ml-pipeline

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

**requirements.txt 내용**:
```
pandas>=2.0.0
numpy>=1.24.0
google-generativeai>=0.3.0
yfinance>=0.2.32
pdfminer.six>=20221105
beautifulsoup4>=4.12.0
selenium>=4.0.0
matplotlib>=3.7.0
seaborn>=0.12.0
scikit-learn>=1.3.0
xgboost>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
```

### 2. 환경변수 설정

`.env` 파일 생성:
```bash
# .env
GEMINI_API_KEY=your_api_key_here
```

**API 키 발급**:
- [Google AI Studio](https://aistudio.google.com/app/apikey) → 무료 API 키 발급
- 또는 [Google Cloud Console](https://console.cloud.google.com/) → Gemini API 활성화

### 3. 노트북 순차 실행

```
📍 notebooks/00_main_workflow.ipynb
    ↓
1️⃣ notebooks/01_report_collection.ipynb (리포트 수집 & OCR)
    ↓
2️⃣ notebooks/02_llm_confident.ipynb (LLM 확신도 추출)
    ↓
3️⃣ notebooks/03_data_preprocessing.ipynb (Firm-Quarter 집계)
    ↓
4️⃣ notebooks/04_volatility_analysis.ipynb (변동성 & Ablation Study)
```

각 노트북에서 기업명, 시작 날짜, 종료 날짜를 설정합니다:

```python
COMPANY_NAME = '삼성전자'
START_DATE = '20240101'
END_DATE = '20241231'
```

---

## 📊 예상 결과

### 출력 데이터

**원본 리포트**:
- 파일: `data/raw/[기업명]_report_text.xlsx`
- 행 수: 30-100 (기간에 따라)
- 컬럼: date, title, text 등

**LLM 점수 추출**:
- 파일: `data/processed/[기업명]_with_scores.csv`
- 추가 컬럼: confidence_score, reasoning
- 평균 확신도: ~60-80점

**Firm-Quarter 집계**:
- 파일: `data/processed/final_dataset_standardized.csv`
- 컬럼: year_quarter, LLM_avg, LLM_std, report_count

**변동성 분석**:
- 파일: `data/reports/volatility_analysis_sample.csv`
- 추가 컬럼: stock_volatility
- 변동성 범위: 0.01 ~ 0.05 (일반적인 한국 주식)

### 시각화 결과

- 📈 **volatility_scatter.png**: LLM_avg/LLM_std vs 변동성 산점도
- 🔥 **correlation_heatmap.png**: 전체 변수 상관계수 히트맵
- 📊 **ablation_study_comparison.png**: R² 개선도 바 차트

---

## ⚙️ 설정 (config.yaml)

```yaml
LLM_CONFIG:
  model: "gemini-2.5-flash"
  score_range:
    min: 0
    max: 100
  metrics:
    - name: "confidence_score"
      label: "확신도"
    - name: "reasoning"
      label: "근거"

CRAWLER_CONFIG:
  start_date: "20240101"
  end_date: "20241231"

DATA_PATHS:
  raw_data: "./data/raw"
  processed_data: "./data/processed"
  reports: "./data/reports"

ANALYSIS_CONFIG:
  volatility_windows:
    - quarter       # 분기별 변동성
    - last_month    # 마지막 1개월 변동성
```

---

## 🔬 기술 스택

| 항목 | 도구 |
|-----|------|
| **LLM** | Google Gemini 2.5 Flash |
| **데이터 처리** | pandas, numpy |
| **웹 크롤링** | BeautifulSoup4, Selenium |
| **OCR** | pdfminer.six |
| **주가 데이터** | yfinance |
| **시각화** | matplotlib, seaborn |
| **모델링** | scikit-learn, XGBoost |
| **설정** | PyYAML |
| **환경** | python-dotenv |

---

