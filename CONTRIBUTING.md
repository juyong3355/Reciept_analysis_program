# 기여 가이드

## 개발 환경

Python 3.11 또는 3.12 가상환경을 만들고 `requirements-dev.txt`를 설치한 뒤 프로젝트를 editable 모드로 설치합니다.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pip install --no-deps -e .
```

## 변경 원칙

- 발급처별 규칙은 `parsers/`에 격리하고 공통 정규화·검증 로직과 분리합니다.
- 필드 값을 추가할 때는 `FieldEvidence` 원본 매핑도 함께 기록합니다.
- 페이지 하나의 실패가 전체 파일 처리를 중단하지 않도록 예외를 격리합니다.
- 카드번호, 사업자번호, 주소 등 실제 개인정보를 fixture나 로그에 추가하지 않습니다.
- 원본 영수증과 실제 처리 결과를 커밋하지 않습니다.

## 테스트

빠른 테스트:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.venv\Scripts\python.exe -m pytest -m "not integration and not ocr"
```

실제 영수증 통합 테스트는 공개 가능한 비식별 샘플을 확보한 경우에만 별도로 실행합니다.
