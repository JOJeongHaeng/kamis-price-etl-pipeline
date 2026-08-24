# KAMIS-Only ETL Dependency Cleanup Design

## Context

SmartShopping의 운영 데이터 원천은 KAMIS Open API이며 FastAPI 웹서비스도
`RecentPriceSnapshot`과 KAMIS 차원 테이블만 조회한다. 그러나 현재 저장소에는
과거 XLSX/PDF 수집 경로, 전용 테이블과 테스트, 그리고 이를 지원하기 위한 무거운
의존성이 함께 남아 있다. 이 설계는 운영 경로를 KAMIS API 하나로 통합하면서 기존
KAMIS API·CSV·DB·웹 동작을 유지한다.

## Goals

- 실행 경로를 KAMIS HTTP JSON 수집, 정규화, CSV 생성, DB 적재로 단일화한다.
- PDF/XLSX 전용 코드와 테스트 및 의존성을 제거한다.
- KAMIS 처리에서 불필요한 pandas를 Python 기본 자료구조로 대체한다.
- MySQL 운영 DB, SQLite 데모, FastAPI API와 웹 화면, Power BI용 CSV를 유지한다.
- GitHub Actions와 Render 배포 동작을 유지한다.

## Non-goals

- KAMIS API 필드나 웹 API 응답 스키마를 새로 설계하지 않는다.
- 배포 방식, 웹 화면 디자인, 검색 정책을 변경하지 않는다.
- 과거 XLSX/PDF 데이터를 다른 형식으로 마이그레이션하지 않는다.
- 이미 작성된 과거 설계 문서를 삭제하거나 역사를 다시 쓰지 않는다.

## Chosen Approach

완전한 KAMIS 전용 전환을 적용한다. 더 이상 동작하지 않을 레거시 CLI 호환 계층을
남기지 않고 `python main.py`을 유일한 ETL 실행 명령으로 사용한다. 부분 삭제나
무시되는 옵션을 남기는 방식은 실제 구조를 흐리고 사용하지 않는 계약을 계속
유지해야 하므로 채택하지 않는다.

## Runtime Data Flow

```text
KAMIS Open API
      ↓
HTTP Request (Python urllib)
      ↓
JSON Response
      ↓
Validation / Transform (dict, list, datetime)
      ↓
Power BI-compatible CSV + Relational Database
      ↓
FastAPI JSON API + Jinja2 Web UI
```

FastAPI 요청 시 KAMIS를 호출하지 않는다. ETL과 조회 서비스를 분리하여 API 장애가
웹 요청에 직접 전파되지 않게 하며, 웹서비스는 마지막으로 적재된 스냅샷을 조회한다.

## Component Design

### Extraction

`etl/api_extract.py`는 기존과 같이 표준 라이브러리 `urllib`과 `json`을 사용한다.
KAMIS 페이지네이션, HTTP 오류 처리, 응답 헤더 검증 계약은 유지한다.

### Validation and Transformation

`etl/api_transform.py`는 `pandas.DataFrame` 대신
`list[dict[str, object]]`를 반환한다. 텍스트 공백 정리, 가격의 쉼표·원 단위 제거,
날짜 ISO 변환, 필수 필드 누락 행 제외, 동일 스냅샷 키의 마지막 행 유지, 결정적인
정렬 순서를 그대로 보존한다.

스냅샷 중복 키는 다음 필드로 구성한다.

- `item_code`
- `variety_code`
- `grade_code`
- `price_date`
- `product_cls_code`
- `unit`
- `unit_size`

차원 데이터는 스냅샷에서 `Category`, `Product`, `ProductVariant`, `Grade`별로
중복을 제거하고 코드 순서로 정렬한 `list[dict]`로 생성한다.

### CSV Output

`etl/pipeline.py`는 표준 라이브러리 `csv.DictWriter`로 다음 파일을
`data/processed/api_price/`에 생성한다.

- `recent_price_snapshot.csv`
- `category.csv`
- `product.csv`
- `product_variant.csv`
- `grade.csv`

기존 Power BI 소비자를 위해 UTF-8 BOM(`utf-8-sig`), 헤더명, 열 순서와 파일명을
유지한다. 빈 결과에서도 헤더가 있는 CSV를 생성한다.

### Database Loading

`etl/load.py`는 DataFrame이 아닌 행 목록을 입력받는다. KAMIS 차원 upsert와
`RecentPriceSnapshot`의 복합 식별 키 및 갱신 필드는 유지한다. MySQL 스키마에서는
사용하지 않는 `Item`, `Week`, `MarketPrice`, `WeeklyPrice`, `WeeklyReport`를
제거하고 KAMIS 테이블 및 `KAMISPriceAnalysis` View만 유지한다.

SQLite 데모는 `tools/seed_demo_db.py`의 KAMIS 전용 스키마와 데이터를 계속 사용한다.
운영 MySQL URL은 `mysql+pymysql`을 유지한다.

### CLI and Configuration

`main.py`은 인자 없이 KAMIS 파이프라인을 실행한다. 다음 레거시 옵션은 제거한다.

- `--raw-dir`
- `--skip-pdfs`
- `--include-api`
- `--api-only`

`config.py`에서는 raw/extracted/weekly/market/mart 디렉터리 설정을 제거하고 KAMIS
CSV 디렉터리, 스키마, MySQL/SQLite 및 KAMIS API 설정만 유지한다.

### Removed Legacy Components

PDF/XLSX 전용 추출·변환 모듈, 수동 도구와 해당 테스트를 제거한다. 혼합 파이프라인의
날짜 추론, 주간 보고서, 시장가격 분석 mart와 레거시 DB loader도 제거한다.

### Dependencies

직접 사용하는 런타임 및 검증 의존성만 `requirements.txt`에 명시한다.

- 유지: FastAPI, Pydantic, SQLAlchemy, PyMySQL, Jinja2, Uvicorn
- 테스트/설정 검증 유지: httpx2, PyYAML
- 제거: pandas, numpy, openpyxl, et_xmlfile, pdfplumber, pdfminer.six,
  pypdfium2, Pillow 및 PDF/Excel 처리에 따라 설치되던 패키지
- 제거: 실제 URL에서 사용하지 않는 mysql-connector-python
- 전이 의존성은 직접 import하거나 프로젝트 계약으로 고정할 필요가 없으면 목록에서 제거한다.

## External Compatibility

다음 외부 동작은 유지한다.

- KAMIS 전 페이지 데이터 수집과 오류 처리
- 정규화된 가격과 날짜 값, 중복 제거 결과
- KAMIS CSV 파일명, 인코딩, 헤더와 열 순서
- KAMIS DB 테이블의 upsert 결과
- 가격 조회, 필터, 페이지네이션, FastAPI 응답 형식
- Jinja2 웹 검색 화면과 빈 `market_type` 처리
- `/health`, SQLite 데모, GitHub Actions와 Render 설정

레거시 XLSX/PDF CLI와 테이블은 현재 운영 계약이 아니므로 호환 대상에서 제외한다.

## Testing Strategy

TDD로 다음 경계를 순서대로 검증한다.

1. list/dict 기반 KAMIS 정규화가 기존 값·중복·정렬 계약을 보존하는지 확인한다.
2. 차원 생성 결과가 정확한 행과 순서를 갖는지 확인한다.
3. CSV가 헤더, UTF-8 BOM, 열 순서와 빈 결과 동작을 보존하는지 확인한다.
4. KAMIS loader가 SQLite 테스트 DB에서 차원과 스냅샷을 upsert하는지 확인한다.
5. 단일 `run_pipeline()`이 수집부터 CSV와 DB 적재까지 연결하는지 확인한다.
6. 전체 테스트로 API, 웹, 필터, 페이지네이션, health, SQLite 데모와 배포 검증을 확인한다.

삭제 자체를 소스 문자열로 검사하는 테스트는 만들지 않는다. 삭제 전용 테스트는 제거하고
현재 실행 경로의 관찰 가능한 결과를 검증한다.

## Documentation

README의 핵심 설명을 다음 내용으로 갱신한다.

> KAMIS Open API에서 농산물 가격 데이터를 수집하고, 응답 데이터를 정제 및 표준화한 뒤 관계형 데이터베이스에 적재하는 ETL 파이프라인입니다. 적재된 데이터는 FastAPI를 통해 조회할 수 있으며 분석 및 시각화에 활용할 수 있습니다.

기술 스택, 아키텍처, 실행 명령, DB 모델, Power BI 안내는 KAMIS 전용 구조만 설명한다.
과거 문서는 이력으로 보존하지만 현재 실행 안내에서는 참조하지 않는다.
