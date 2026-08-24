# 🛒 SmartShopping

### KAMIS Open API 기반 농산물 가격 ETL 파이프라인 및 조회 서비스

> **KAMIS Open API의 농산물 가격 데이터를 자동으로 수집하고, 검증·표준화하여 관계형 데이터베이스에 적재한 뒤 FastAPI를 통해 조회할 수 있도록 구축한 데이터 엔지니어링 프로젝트**

**Web Service**
https://smartshopping-lffu.onrender.com/

**API Docs**
https://smartshopping-lffu.onrender.com/docs

---

# 📌 프로젝트 개요

농산물 가격 데이터를 활용한 기존 프로젝트에서는 XLSX와 PDF 파일을 직접 수집하고 정제하는 방식으로 ETL을 구현했습니다.

하지만 파일 기반 데이터 수집은 새로운 데이터가 필요할 때마다 파일을 다시 확보해야 하고, 서로 다른 형식의 데이터를 각각 처리해야 한다는 한계가 있었습니다.

이를 개선하기 위해 **KAMIS Open API를 데이터 원천으로 사용하여 데이터를 자동으로 수집하고, 반복적으로 실행할 수 있는 ETL 파이프라인으로 재구성했습니다.**

수집한 데이터를 단순히 저장하는 데서 끝내지 않고,

**데이터 수집 → 검증 → 정제 → 관계형 DB 적재 → API 제공 → 테스트 → 배포**

까지 하나의 흐름으로 연결했습니다.

OpenAI Codex 활용
요구사항을 정의한 뒤 Codex를 활용해 구현과 리팩터링을 진행하고, 생성된 코드의 동작을 직접 검토·테스트하며 프로젝트를 완성했습니다.
---

# 🎯 프로젝트 목표

* KAMIS Open API를 이용한 농산물 가격 데이터 자동 수집
* 외부 API 응답 및 데이터 유효성 검증
* 가격·날짜·품목·품종·등급 데이터 표준화
* 반복 실행 가능한 ETL 파이프라인 구축
* 중복 데이터를 방지하는 Upsert 구조 구현
* 관계형 데이터베이스 모델링 및 MySQL 적재
* 분석에 활용할 수 있는 CSV 데이터 생성
* FastAPI를 이용한 가격 조회 서비스 구현
* 자동 테스트와 CI를 통한 데이터 파이프라인 검증
* 실제 웹 환경 배포

---

# 🏗️ Architecture

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/8e962e00-2910-4dcb-a044-243f3823214a" />

---

# 🔄 ETL Pipeline

## 1. Extract

### KAMIS Open API 데이터 자동 수집

기존 파일 기반 수집 방식 대신 KAMIS Open API를 이용해 최근 농산물 도·소매 가격 데이터를 가져오도록 구성했습니다.

```text
KAMIS Open API
      ↓
HTTP Request
      ↓
JSON Response
      ↓
Python dict / list
```

Python의 `urllib`을 이용해 API에 HTTP 요청을 보내고 JSON 응답을 Python 객체로 변환합니다.

API가 여러 페이지로 데이터를 제공하기 때문에 첫 페이지만 가져오는 것이 아니라 **전체 페이지를 순차적으로 요청하여 데이터를 수집하도록 구현했습니다.**

### API 응답 검증

외부 API에서 전달되는 데이터를 그대로 신뢰하지 않고 ETL 단계로 전달하기 전에 검증합니다.

**검증 항목**

* HTTP 요청 성공 여부
* JSON 변환 가능 여부
* 응답 데이터 구조 확인
* API 결과 코드 확인
* 실제 데이터 존재 여부

이를 통해 잘못된 응답이 이후 Transform이나 DB 적재 단계까지 전달되는 것을 방지했습니다.

---

# 🧹 2. Transform

### 데이터 정제 및 표준화

API에서 가져온 Raw Data를 DB와 분석 환경에서 사용할 수 있는 형태로 변환합니다.

**주요 처리**

* 가격 데이터 변환
* 날짜 형식 통일
* 품목·품종·등급 데이터 정리
* 도매/소매 구분 표준화
* 단위 데이터 정리
* 잘못된 값 검증
* 중복 데이터 제거

# 🔍 3. 중복 데이터 처리

ETL은 반복적으로 실행될 수 있기 때문에 동일한 데이터를 계속 INSERT하면 중복 데이터가 발생할 수 있습니다.

이를 방지하기 위해 가격 스냅샷을 다음 정보의 조합으로 식별합니다.

```text
품종
+
등급
+
조사일
+
도매/소매 구분
+
단위
+
단위 크기
```

Transform 단계에서 동일한 데이터를 정리하고, DB에서도 동일한 조건의 데이터가 다시 들어오면 새로운 행을 생성하는 대신 기존 데이터를 갱신하도록 구성했습니다.

---

# 💾 4. Load

### MySQL 관계형 데이터베이스 적재

정제된 데이터를 관계형 구조로 분리하여 MySQL에 저장합니다.

```text
Normalized Data
       ↓
  SQLAlchemy
       ↓
    PyMySQL
       ↓
     MySQL
```

# 🗃️ Data Modeling

API 데이터를 하나의 테이블에 모두 저장하지 않고 데이터의 역할에 따라 테이블을 분리했습니다.

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/4f44da6e-0139-4963-a230-07fe133c5a6f" />

**주요 데이터**

* 조사일
* 도매/소매
* 단위
* 현재 가격
* 전일 가격
* 전주 가격
* 전월 가격
* 전년 가격
* 데이터 수집 시각

---

# 🌐 FastAPI 조회 서비스

ETL을 통해 적재한 데이터가 실제 서비스에서 어떻게 활용될 수 있는지 확인하기 위해 FastAPI 기반 가격 조회 API를 구현했습니다.

```text
User
 ↓
FastAPI
 ↓
Service
 ↓
Repository
 ↓
Database
```

### 주요 기능

* 농산물 가격 조회
* 품목명 검색
* 도매/소매 필터
* 페이지네이션
* 입력값 검증
* DB 상태 확인

### API Example

```http
GET /api/prices?q=배추&market_type=retail&page=1&page_size=20
```

---

# 💡 ETL과 웹 요청을 분리한 이유

초기에는 사용자가 가격을 조회할 때 KAMIS API를 직접 호출하는 구조도 고려할 수 있었습니다.

하지만 이렇게 구성하면,

```text
사용자
 ↓
FastAPI
 ↓
KAMIS API
```

외부 API의 응답 속도나 장애 상황이 서비스에 직접 영향을 줄 수 있습니다.

따라서 데이터 수집과 서비스 조회를 분리했습니다.

```text
[데이터 수집]

KAMIS
 ↓
ETL
 ↓
Database


[서비스]

User
 ↓
FastAPI
 ↓
Database
```

KAMIS 데이터는 ETL 단계에서 미리 검증하고 DB에 적재하며, 사용자의 조회 요청은 **외부 API가 아닌 DB를 대상으로 처리**합니다.

이를 통해 데이터 수집 과정과 사용자 요청을 독립적으로 관리할 수 있도록 구성했습니다.

---

# 📊 분석용 데이터

ETL 결과는 DB뿐만 아니라 CSV 형태로도 생성합니다.

```text
recent_price_snapshot.csv
category.csv
product.csv
product_variant.csv
grade.csv
```

CSV는 Power BI 등 외부 분석 도구에서 바로 사용할 수 있도록 **UTF-8 BOM 형식**으로 저장했습니다.

---

# 🧪 Data Validation & Testing

프로젝트에서 중요하게 생각한 부분은 **데이터를 가져오는 것보다 가져온 데이터가 정확한지 검증하는 과정**이었습니다.

## API 검증

```text
HTTP Response
      ↓
JSON Decode
      ↓
Response Structure
      ↓
Result Code
      ↓
Data
```

## Transform 검증

* 가격 변환 가능 여부
* 날짜 형식 확인
* 필수 데이터 확인
* 텍스트 표준화
* 중복 데이터 제거

## Database 검증

* 관계형 데이터 정상 적재
* FK 관계 유지
* 동일 Snapshot 중복 방지
* Upsert 동작 확인

## Service 검증

* 가격 조회
* 검색
* 필터
* 페이지네이션
* 잘못된 요청 처리
* DB 상태 확인

---

# 🚀 Deployment

Render를 이용해 FastAPI 서비스를 실제 웹 환경에 배포했습니다.

```text
GitHub
   ↓
Render
   ↓
Dependencies Install
   ↓
KAMIS ETL
   ↓
SQLite
   ↓
Uvicorn
   ↓
FastAPI
```

웹 서버를 실행하기 전에 KAMIS 데이터를 수집·적재하도록 구성했습니다.

ETL 과정에서 API 오류가 발생하거나 유효 데이터가 존재하지 않는 경우 웹 서버를 실행하지 않도록 하여 **데이터가 준비되지 않은 빈 서비스가 정상 배포되는 것을 방지**했습니다.

또한 `/health` 엔드포인트를 이용해 서비스와 DB의 준비 상태를 확인할 수 있도록 구성했습니다.

---

# 🛠️ Tech Stack

### Data Engineering

`Python` `KAMIS Open API` `JSON` `urllib` `Decimal`

### Database

`MySQL` `SQLite` `SQLAlchemy` `PyMySQL`

### Backend

`FastAPI` `Pydantic` `Uvicorn`

### Frontend

`Jinja2` `HTML` `CSS`

### Data Analysis

`CSV` `Power BI`

### Test / CI / Deployment

`unittest` `httpx2` `GitHub Actions` `Render`

---

# 📂 주요 코드 구조

```text
etl/
├─ api_extract.py
├─ api_transform.py
├─ load.py
└─ pipeline.py

sql/
├─ schema.sql
└─ sqlite_schema.sql

web/
├─ app.py
├─ database.py
├─ models.py
├─ repository.py
├─ schemas.py
└─ service.py

tests/
tools/
main.py
config.py
render.yaml
requirements.txt
```

### `api_extract.py`

KAMIS Open API 호출 및 JSON 데이터 수집

### `api_transform.py`

가격·날짜·텍스트 표준화 및 중복 제거

### `load.py`

관계형 DB 데이터 적재 및 Upsert

### `pipeline.py`

Extract → Transform → CSV → Load 전체 과정 제어

---

# 💬 프로젝트 한 줄 요약

> **KAMIS Open API에서 농산물 가격 데이터를 자동으로 수집하고 검증·표준화하여 관계형 DB에 적재한 뒤, FastAPI와 분석용 CSV를 통해 활용할 수 있도록 구축한 End-to-End 데이터 엔지니어링 프로젝트**
