# SmartShopping 배포·CI 설계

작성일: 2026-08-23
상태: 검토 대기
대상: K-TCB IT개발/웹개발 지원용 SmartShopping 웹서비스

## 1. 목적

SmartShopping을 공개 URL에서 검증할 수 있게 하고, 모든 코드 변경에서 자동 테스트가 실행되는 개발 흐름을 제공한다. 배포 플랫폼은 Render 무료 Web Service를 사용하며, 무료 인스턴스의 임시 파일시스템 제약을 시작 시 데모 DB 재생성으로 해결한다.

## 2. 성공 기준

- `GET /health`가 애플리케이션과 DB 준비 상태를 JSON으로 반환한다.
- DB가 준비되지 않으면 헬스체크가 HTTP 503을 반환한다.
- `main` push와 Pull Request에서 전체 테스트 60개 이상이 자동 실행된다.
- Render가 저장소 설정만으로 Python 버전, 빌드, 시작 명령, 헬스체크 경로를 인식한다.
- Render 프로세스가 시작될 때 SQLite 데모 데이터 6건을 재생성한다.
- 공개 서비스에서 `/`, `/api/prices`, `/docs`, `/health`를 확인할 수 있다.
- README에 CI 상태, 공개 URL, 무료 인스턴스의 첫 접속 지연을 정확히 안내한다.

## 3. 범위

### 포함

- DB 준비 상태를 확인하는 `/health`
- GitHub Actions 테스트 워크플로
- Render Blueprint 설정
- 배포 Python 버전 고정
- 배포 시작 시 SQLite 데모 DB 초기화
- README 배포 안내와 실제 화면 캡처

### 제외

- 유료 영구 디스크
- 운영용 MySQL 또는 PostgreSQL 프로비저닝
- 사용자 도메인과 DNS 설정
- 무중단 배포와 다중 인스턴스
- 외부 모니터링·알림 서비스
- KAMIS 정기 수집 스케줄러

## 4. 헬스체크

`GET /health`는 웹 애플리케이션이 실제 가격 조회를 제공할 준비가 되었는지 검사한다.

정상 응답:

```json
{
  "status": "ok",
  "database": "ready"
}
```

- DB에 `SELECT 1`을 실행한다.
- `RecentPriceSnapshot` 테이블 존재 여부와 1건 이상의 데이터를 확인한다.
- 모든 조건이 충족되면 HTTP 200을 반환한다.

장애 응답:

```json
{
  "status": "unavailable",
  "database": "unavailable"
}
```

- SQLAlchemy 오류 또는 테이블·데이터 부재 시 HTTP 503을 반환한다.
- 연결 문자열, 비밀번호, 원본 DB 예외는 응답에 포함하지 않는다.
- 서버 로그에는 원인을 기록한다.

헬스체크는 KAMIS 외부 API를 호출하지 않는다.

## 5. GitHub Actions

`.github/workflows/test.yml`은 다음 이벤트에서 실행한다.

- `main` 브랜치 push
- `main` 대상 Pull Request
- 수동 실행 `workflow_dispatch`

단일 테스트 job은 Ubuntu에서 다음 순서를 수행한다.

1. 저장소 checkout
2. 프로젝트가 고정한 Python 버전 설치
3. pip 캐시 사용
4. `requirements.txt` 설치
5. `PYTHONWARNINGS=error python -m unittest discover -s tests`
6. `python -m compileall -q config.py etl tools web tests`
7. `python tools/seed_demo_db.py`

KAMIS 인증키와 외부 DB는 사용하지 않는다. 테스트는 인메모리 SQLite와 데모 DB만 사용한다.

## 6. Render 배포

저장소 루트의 `render.yaml`에 하나의 무료 Python Web Service를 정의한다.

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `python tools/seed_demo_db.py && uvicorn web.app:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Plan: Free
- Auto deploy: `main` 변경 시 활성화

SQLite DB는 `database/smartshopping.db`에 생성되며 Git에 포함하지 않는다. 무료 Render 인스턴스가 재시작되거나 재배포될 때 로컬 파일이 사라질 수 있으므로 시작 명령이 항상 스키마와 6개 샘플을 재생성한다. 서비스는 읽기 전용 데모이므로 재시드 중 사용자 데이터 유실 문제는 없다.

## 7. Python 버전

`.python-version`에 `3.13`을 기록해 로컬·CI·Render가 Python 3.13 계열의 최신 지원 패치를 사용하게 한다. GitHub Actions도 `python-version-file`로 이 파일을 읽는다.

## 8. 보안과 장애 처리

- 저장소와 Render 설정에 인증키·DB 비밀번호를 기록하지 않는다.
- 배포는 SQLite 데모 모드를 사용하므로 `DATABASE_URL` 비밀값이 필요하지 않다.
- 헬스체크 오류 응답은 고정된 안전한 상태만 반환한다.
- GitHub Actions 로그에 환경변수 전체를 출력하지 않는다.
- Render 시작 실패 시 시드 명령의 비정상 종료로 Uvicorn을 실행하지 않는다.

## 9. 테스트 전략

모든 동작 변경은 TDD로 진행한다.

### 헬스체크 테스트

- 시드 DB에서 HTTP 200과 정확한 정상 상태 반환
- 빈 DB에서 HTTP 503
- SQLAlchemy 오류에서 HTTP 503
- 응답에 원본 오류와 비밀번호가 포함되지 않음

### 배포 구성 검증

- 별도 스크립트가 `render.yaml`을 읽어 필수 build/start/health 설정을 검증
- `.python-version`의 Python 3.13 환경에서 의존성 설치 확인
- CI와 동일한 명령을 로컬에서 실행해 성공 확인
- Uvicorn 실제 프로세스에서 `/health`, `/`, `/api/prices` HTTP 200 확인

CI YAML 자체의 플랫폼 동작은 GitHub push 후 실행 결과로 최종 확인한다.

## 10. 커밋 경계

1. `feat: add database health endpoint`
   - 헬스체크 구현과 API 테스트
2. `ci: run tests for pushes and pull requests`
   - GitHub Actions와 로컬 동일 검증
3. `chore: configure Render deployment`
   - Python 버전, Render Blueprint, 설정 검증 테스트
4. `docs: publish deployed SmartShopping service`
   - 공개 URL, CI 배지, 실제 화면 캡처, 무료 인스턴스 안내

## 11. 외부 작업

코드 커밋만으로 끝나지 않는 작업은 사용자 권한 범위에서 별도로 수행한다.

1. `main`을 GitHub 원격 저장소에 push한다.
2. GitHub Actions 실행 결과를 확인한다.
3. Render 계정에서 GitHub 저장소를 연결하고 Blueprint를 생성한다.
4. 배포 URL의 네 경로를 검증한다.
5. 실제 화면을 캡처하고 README에 반영한다.

GitHub push와 Render 리소스 생성은 외부 상태를 변경하므로 실행 직전에 대상 저장소와 계정을 확인한다.

## 12. 완료 조건

- 로컬 전체 테스트와 컴파일 검사가 통과한다.
- GitHub Actions가 `main`에서 성공한다.
- Render 배포 상태가 Healthy다.
- 공개 URL의 `/`, `/api/prices`, `/docs`, `/health`가 응답한다.
- README의 링크와 화면 캡처가 실제 배포 결과와 일치한다.
- 생성된 SQLite DB와 비밀정보가 Git에 포함되지 않는다.
