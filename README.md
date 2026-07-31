# SmartShopping Data Engineering Project

전통시장과 대형마트 가격 데이터를 수집·정제·적재하고, SQL 분석과 Power BI 대시보드까지 연결한 데이터 엔지니어링 프로젝트입니다.
해당 프로젝트는 OpenAI Codex를 사용하여 진행했습니다.

## Project Overview

- 목표: 반복적으로 유입되는 농산물 가격 데이터를 안정적으로 정제하고 분석 가능한 형태로 제공
- 정형 데이터 `CSV`, `XLSX`
- 비정형 데이터 `PDF`
- MySQL 적재 테이블
- 분석용 CSV 마트
- Power BI 대시보드

## Key Features

- 스프레드시트와 PDF를 함께 수집하는 ETL 파이프라인
- 품목, 주차, 시장 가격, 주간 리포트 테이블로 정규화
- 주차별/월별 분석용 CSV 마트 생성
- SQL 기반 가격 비교 분석
- Power BI 기반 시각화 대시보드 구성

## Architecture

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/597a14e7-f518-4bf9-908f-77526a3d6ee2" />

## Data Model

주요 테이블은 아래 5개입니다.

- `Item`: 품목명, 단위
- `Week`: 시작일, 종료일, 주차, 연도, 월
- `MarketPrice`: 전통시장 가격, 대형마트 가격
- `WeeklyPrice`: 전주 가격, 현재 가격, 등락률
- `WeeklyReport`: 주간 요약, 주요 이슈, 제철 식재료

ERD 관점 관계는 아래와 같습니다.

- `Item` 1:N `MarketPrice`
- `Item` 1:N `WeeklyPrice`
- `Week` 1:N `MarketPrice`
- `Week` 1:N `WeeklyPrice`
- `Week` 1:1 `WeeklyReport`

## ETL Flow

파이프라인 엔트리포인트는 `main.py`입니다.

1. 원본 데이터 탐색
- `etl.extract`에서 스프레드시트와 PDF 리포트 수집

2. 데이터 유형 판별
- 파일명과 헤더를 기준으로 `weekly` / `market` 데이터셋 분기

3. 정제 및 표준화
- `etl.transform`에서 주간 가격, 시장 가격 정규화
- 중복 행 제거와 컬럼 표준화 수행

4. 주차 메타데이터 생성
- 파일명 또는 헤더 날짜 범위로 `start_date`, `end_date`, `week_no`, `year`, `month` 추론

5. CSV 마트 생성
- `weekly_price.csv`
- `market_price.csv`
- `item.csv`
- `week.csv`
- `weekly_report.csv`
- `price_analysis_mart.csv`

6. 스키마 생성 및 DB 적재
- `sql/schema.sql` 기준으로 MySQL 스키마 생성
- 적재 결과를 분석 및 Power BI에서 활용

## Project Structure

```text
SmartShopping-DataEngineering/
├─ data/
│  ├─ raw/
│  ├─ extracted/
│  └─ processed/
├─ database/
├─ docs/
├─ etl/
│  ├─ extract.py
│  ├─ load.py
│  ├─ pdf_prices.py
│  ├─ pipeline.py
│  ├─ report.py
│  └─ transform.py
├─ sql/
│  └─ schema.sql
├─ tests/
├─ config.py
├─ db.py
├─ main.py
└─ requirements.txt
```

## Tech Stack

- Python
- pandas
- pdfplumber
- SQLAlchemy
- PyMySQL
- MySQL
- Power BI

## SQL Analysis Examples

이 프로젝트에서는 아래와 같은 분석을 수행했습니다.

- 전통시장 평균 가격 vs 대형마트 평균 가격
- 주차별 평균 가격 추이
- 월별 평균 가격 추이
- 품목별 가격 차이 분석
- 전통시장이 더 저렴한 품목 분석
- 대형마트가 더 저렴한 품목 분석
- 품목별 최고가 / 최저가 비교

## Power BI Dashboard

Power BI 대시보드는 3페이지로 구성했습니다.

### 1. Overview

- 전통시장 평균 가격
- 대형마트 평균 가격
- 가격 차이
- 주차별 평균 가격 추이
- 월별 평균 가격 추이
- 품목별 가격 차이

### 2. Item Analysis

- 품목별 최고가 비교
- 품목별 최저가 비교
- 품목별 가격 차이
- 더 저렴한 시장 분포

### 3. Weekly Report

- 주차 선택
- 주간 요약
- 주요 이슈
- 제철 식재료

## Automation

이번 프로젝트에서는 1차 완성 범위를 운영 자동화보다 데이터 파이프라인 구축 자체에 맞췄기 때문에 자동화를 직접 구현하지 않았습니다. 

## Problems Solved

프로젝트 진행 중 해결한 주요 문제는 아래와 같습니다.

- 스프레드시트 헤더/중복 행 정제 문제
- PDF 가격 표 파싱 문제
- 시장 가격 / 주간 가격 데이터 표준화 문제
- 주차 메타데이터 추론 문제
- MySQL 적재용 스키마 정합성 문제

## Improvements

추가 개선 포인트는 아래와 같습니다.

- 자동화 배치 구현
- SQLite 호환 스키마 분기
- Power BI 리포트 배포 자동화
- 데이터 품질 검증 리포트 고도화

## Portfolio Summary

정형/비정형 가격 데이터를 수집하고, ETL 파이프라인으로 정제한 뒤 MySQL 적재, SQL 분석, Power BI 대시보드까지 연결한 end-to-end 데이터 엔지니어링 프로젝트입니다.
