# Render KAMIS SQLite Startup Sync Design

## Goal

Render 무료 웹서비스가 고정 데모 6건 대신 배포 시작 시 KAMIS Open API 전체 데이터를
수집하여 동일한 SQLite 데이터베이스에 적재한 후 FastAPI를 실행하게 한다.

## Runtime Flow

```text
Render deploy
  → python main.py
  → KAMIS API pagination
  → list/dict validation and transform
  → SQLite schema and upsert
  → uvicorn web.app:app
  → /health and price queries
```

`DB_DRIVER=sqlite`를 Blueprint에 명시하여 ETL의 SQLAlchemy engine과 웹서비스의 기본
SQLite URL이 모두 `database/smartshopping.db`를 사용하게 한다. `KAMIS_SERVICE_KEY`는
`sync: false`인 Render 비밀 환경 변수로 선언하고 저장소에는 값을 기록하지 않는다.

## Schema

MySQL 전용 `sql/schema.sql`은 유지한다. 별도의 `sql/sqlite_schema.sql`에 동일한 KAMIS
테이블 5개를 SQLite 문법으로 정의한다. `ensure_schema`는 전달된 engine의 dialect에
따라 스키마 파일을 선택한다. SQLite 데모 seed와 실제 KAMIS ETL이 같은 스키마 파일을
사용하여 열 불일치를 방지한다.

## Failure Policy

KAMIS 응답에서 유효한 가격 행이 0건이면 파이프라인은 실패한다. API 오류, 잘못된 키,
빈 응답 또는 DB 적재 실패 시 Uvicorn을 시작하지 않으므로 Render는 새 배포를 정상으로
전환하지 않는다. 고정 데모 데이터로 조용히 대체하지 않는다.

## Compatibility

- 로컬 MySQL ETL과 `mysql+pymysql` 연결은 유지한다.
- SQLite 데모 seed와 기존 웹/API/health 동작은 유지한다.
- KAMIS CSV 파일과 DB upsert 계약은 유지한다.
- GitHub Actions에서는 실제 KAMIS 호출 대신 fixture와 임시 SQLite DB로 시작 동기화를 검증한다.
- Render 무료 파일시스템 특성상 재배포·재시작 시 KAMIS를 다시 수집하며 장기 이력은 보장하지 않는다.

## Deployment Configuration

Render 시작 명령은 다음으로 변경한다.

```text
python main.py && uvicorn web.app:app --host 0.0.0.0 --port $PORT
```

Blueprint 환경 변수:

- `DB_DRIVER=sqlite`
- `KAMIS_SERVICE_KEY` with `sync: false`

Blueprint 동기화 후 사용자가 Render 대시보드에서 실제 서비스 키를 입력해야 한다.

## Verification

1. SQLite 스키마가 KAMIS loader의 모든 가격 열을 수용한다.
2. fixture 기반 pipeline이 임시 SQLite DB에 실제 행을 적재한다.
3. 빈 KAMIS 결과는 시작 실패로 처리한다.
4. Render 설정 검증기가 새 시작 명령과 환경 변수를 요구한다.
5. 전체 테스트와 컴파일을 통과한 뒤 push한다.
6. 사용자가 Render 비밀키를 등록하고 Blueprint를 동기화한 후 `/health`, 전체 개수,
   필터와 페이지네이션을 공개 URL에서 검증한다.
