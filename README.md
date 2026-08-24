# SmartShopping

[![Test](https://github.com/JOJeongHaeng/kamis-price-etl-pipeline/actions/workflows/test.yml/badge.svg)](https://github.com/JOJeongHaeng/kamis-price-etl-pipeline/actions/workflows/test.yml)

KAMIS Open API에서 농산물 가격 데이터를 수집하고, 응답 데이터를 정제 및 표준화한 뒤 관계형 데이터베이스에 적재하는 ETL 파이프라인입니다. 적재된 데이터는 FastAPI를 통해 조회할 수 있으며 분석 및 시각화에 활용할 수 있습니다.

- 배포 웹서비스: <https://smartshopping-lffu.onrender.com/>
- API 문서: <https://smartshopping-lffu.onrender.com/docs>
- 상태 확인: <https://smartshopping-lffu.onrender.com/health>

## 주요 기능

- KAMIS 최근일자 도·소매가격 JSON 전체 페이지 수집
- 가격·날짜·텍스트 검증 및 표준화
- 동일 상품 스냅샷 중복 제거와 결정적인 정렬
- MySQL 관계형 테이블 upsert
- Power BI에서 읽을 수 있는 UTF-8 BOM CSV 생성
- FastAPI 가격 조회, 품목명 검색, 도·소매 필터, 페이지네이션
- Jinja2 기반 웹 검색 화면
- SQLite 데모 및 Render KAMIS 데이터와 `/health` 준비 상태 확인
- GitHub Actions 테스트와 Render Blueprint 배포

## 데이터 흐름

```text
KAMIS Open API
      ↓
HTTP Request (urllib)
      ↓
JSON Response
      ↓
Validation / Transform (dict, list, datetime, Decimal)
      ↓
CSV + Relational Database
      ↓
FastAPI JSON API + Jinja2 Web UI
```

웹 요청과 외부 데이터 수집은 분리되어 있습니다. ETL이 KAMIS 데이터를 먼저 DB에 적재하고, FastAPI는 마지막으로 적재된 스냅샷만 조회합니다.

## 기술 스택

- Python 3.13
- FastAPI, Pydantic, Uvicorn
- SQLAlchemy, PyMySQL, MySQL
- SQLite 데모 데이터베이스
- Jinja2, HTML, CSS
- Python `urllib`, `json`, `csv`, `datetime`, `decimal`
- unittest, httpx2
- GitHub Actions, Render, PyYAML
- Power BI 호환 CSV

## 설치

Windows PowerShell 기준입니다.

```powershell
git clone https://github.com/JOJeongHaeng/kamis-price-etl-pipeline.git
cd kamis-price-etl-pipeline
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` 값을 현재 환경에 맞게 설정합니다. 프로젝트는 환경 변수를 직접 읽으므로 실행 전에 PowerShell 세션 또는 배포 환경에 등록해야 합니다.

```env
KAMIS_SERVICE_KEY=공공데이터포털_서비스키
KAMIS_API_URL=https://apis.data.go.kr/B552845/recent/price
KAMIS_API_TIMEOUT=15
KAMIS_API_PAGE_SIZE=1000

DB_DRIVER=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=smartshopping
DB_USER=root
DB_PASSWORD=비밀번호
```

## KAMIS ETL 실행

MySQL 데이터베이스를 먼저 생성하고 환경 변수를 설정한 뒤 실행합니다.

```powershell
python main.py
```

파이프라인은 다음 작업을 한 번에 수행합니다.

1. KAMIS API의 모든 페이지 요청
2. 응답 헤더와 JSON 구조 검증
3. 가격, 날짜, 품목·품종·등급 정보 표준화
4. 중복 제거와 차원 데이터 생성
5. CSV 생성
6. MySQL 스키마 생성 및 데이터 upsert

API의 페이지 크기는 최대 1,000건으로 제한하며 `KAMIS_API_PAGE_SIZE`로 더 작은 값을 지정할 수 있습니다.

## 데이터베이스

MySQL 연결 URL은 다음 형식으로 생성됩니다.

```text
mysql+pymysql://DB_USER:DB_PASSWORD@DB_HOST:DB_PORT/DB_NAME
```

현재 스키마는 KAMIS 데이터에 필요한 구조만 포함합니다.

- `Category`: 품목 부류
- `Product`: 품목과 부류 관계
- `ProductVariant`: 품목별 품종
- `Grade`: 등급
- `RecentPriceSnapshot`: 조사일·도소매 구분·단위별 현재 및 비교 가격
- `KAMISPriceAnalysis`: 품목 정보를 결합하고 데이터 신선도를 계산하는 MySQL View

스냅샷은 품종, 등급, 조사일, 도·소매 구분, 단위, 단위 크기의 조합으로 식별됩니다. 같은 조합을 다시 적재하면 가격과 비교 가격 및 수집 시각을 갱신합니다.

## Power BI용 CSV

ETL 실행 후 `data/processed/api_price/`에 다음 파일이 생성됩니다.

- `recent_price_snapshot.csv`
- `category.csv`
- `product.csv`
- `product_variant.csv`
- `grade.csv`

파일은 UTF-8 BOM으로 저장되며 헤더와 열 순서가 고정되어 있습니다. Power BI에서는 폴더 또는 텍스트/CSV 데이터 원본으로 불러와 코드 열을 기준으로 관계를 구성할 수 있습니다.

```text
Category 1 ─ N Product 1 ─ N ProductVariant 1 ─ N RecentPriceSnapshot N ─ 1 Grade
```

## 로컬 웹 데모

SQLite 데모 DB에 반복 가능한 샘플 데이터를 적재합니다.

```powershell
python tools/seed_demo_db.py
uvicorn web.app:app --host 127.0.0.1 --port 8000
```

브라우저에서 다음 주소를 사용할 수 있습니다.

- 웹 화면: <http://127.0.0.1:8000/>
- 가격 API: <http://127.0.0.1:8000/api/prices>
- API 문서: <http://127.0.0.1:8000/docs>
- 상태 확인: <http://127.0.0.1:8000/health>

웹 DB는 `DATABASE_URL`이 있으면 해당 DB를 사용하고, 없으면 `database/smartshopping.db`를 사용합니다.

### 가격 API 예시

```text
GET /api/prices?q=배추&market_type=retail&page=1&page_size=20
```

- `q`: 품목명 부분 검색
- `market_type`: `retail` 또는 `wholesale`; 생략하면 전체
- `page`: 1부터 시작
- `page_size`: 1~100

웹 화면의 전체 시장 옵션은 빈 값을 서버에서 `None`으로 정규화합니다. JSON API에서는 빈 문자열이 아니라 `market_type` 매개변수를 생략해야 합니다.

## 테스트

```powershell
python -m unittest discover -s tests -v
python -m compileall -q config.py etl tools web tests
```

테스트 범위에는 KAMIS 수집·변환·DB 적재·CSV, 가격 조회·필터·페이지네이션, FastAPI와 웹 화면, `/health`, SQLite 데모, GitHub Actions와 Render 설정, 배포 스모크 테스트가 포함됩니다.

## CI와 Render 배포

`.github/workflows/test.yml`은 `main` push와 pull request에서 의존성 설치, 전체 테스트, Python 컴파일, SQLite 데모 적재를 실행합니다.

`render.yaml`은 다음 배포 계약을 정의합니다.

- 서비스명: `smartshopping`
- 빌드: `pip install -r requirements.txt`
- 시작: `python main.py && uvicorn web.app:app --host 0.0.0.0 --port $PORT`
- 상태 확인: `/health`
- `main` 자동 배포

Render는 웹서버를 시작하기 전에 `python main.py`로 KAMIS 전체 데이터를 SQLite에
수집·적재합니다. Blueprint를 처음 동기화할 때 Render 대시보드에서
`KAMIS_SERVICE_KEY`의 비밀값을 입력해야 하며, 키를 저장소나 `render.yaml`에 직접
기록하면 안 됩니다.

무료 서비스의 SQLite 파일은 영구 디스크가 아니므로 재배포·재시작 시 KAMIS 데이터를
다시 수집합니다. API 오류, 잘못된 키 또는 유효 데이터 0건이면 Uvicorn을 시작하지 않아
빈 서비스가 정상 배포되는 것을 막습니다. `tools/seed_demo_db.py`의 6건 샘플은 로컬 개발과
CI 스모크 테스트에만 사용됩니다.

## 프로젝트 구조

```text
SmartShopping/
├─ etl/
│  ├─ api_extract.py       # KAMIS HTTP/JSON 수집
│  ├─ api_transform.py     # list/dict 기반 정규화와 차원 생성
│  ├─ load.py              # SQLAlchemy KAMIS upsert
│  └─ pipeline.py          # CSV 및 DB 파이프라인 조정
├─ sql/
│  ├─ schema.sql           # MySQL KAMIS 스키마와 분석 View
│  └─ sqlite_schema.sql    # Render·로컬 SQLite KAMIS 스키마
├─ web/                    # FastAPI, 조회 서비스, 템플릿과 정적 파일
├─ tools/
│  ├─ seed_demo_db.py      # SQLite 데모 데이터
│  ├─ smoke_test_deployment.py
│  └─ validate_deployment_config.py
├─ tests/
├─ main.py
├─ render.yaml
└─ requirements.txt
```
