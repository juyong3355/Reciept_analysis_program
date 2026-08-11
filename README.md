# 영수증 자동 처리 MVP

쿠팡·네이버 영수증 PDF/이미지를 로컬 PC에서 읽고, 거래 정보를 검토·수정한 뒤 세무 정리용 Excel로 저장하는 Windows 데스크톱 애플리케이션입니다.

## 주요 기능

- PDF, JPG, JPEG, PNG 파일 선택 및 드래그 앤 드롭
- 텍스트 PDF 자동 추출과 이미지 PDF/사진 OCR 자동 전환
- 쿠팡·네이버 문서 분류 및 전용 파서, 기타 영수증의 보수적인 일반 파서
- 파일·페이지 단위 오류 격리와 SHA-256 기반 중복 후보 탐지
- 사업자등록번호, 금액 관계, 필수 필드, OCR 신뢰도 검증
- 원본 미리보기, 추출 결과 검색·필터·수동 수정
- `세무정리`, `상세내역`, `오류내역`, `원본매핑` 4개 시트 Excel 출력
- 원본 파일과 OCR 결과를 외부 서버로 보내지 않는 로컬 처리

## 실행 환경

- Windows 10/11
- Python 3.11 또는 3.12 (64비트 권장)
- 최초 OCR 실행 시 PaddleOCR 모델 다운로드를 위한 인터넷 연결
- OCR 모델 설치 후에는 영수증 처리가 로컬에서 수행됩니다.

## 빠른 설치

저장소 루트에서 `setup_windows.bat`를 실행합니다. 설치가 끝나면 `run_app.bat`로 프로그램을 시작할 수 있습니다.

수동 설치:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m pip install --no-deps -e .
.venv\Scripts\python.exe -m receipt_mvp gui
```

개발 의존성과 테스트 도구까지 설치하려면 다음을 사용합니다.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 사용 순서

1. `run_app.bat`를 실행합니다.
2. 영수증 파일을 창에 끌어놓거나 파일 선택 버튼으로 추가합니다.
3. 분석 완료 후 상태가 `확인 필요`인 행을 원본 미리보기와 비교합니다.
4. 필요한 값을 수정하고 저장할 열을 선택합니다.
5. Excel 저장 버튼으로 결과 파일을 생성합니다.

처음 OCR을 실행하면 모델을 내려받고 초기화하므로 시간이 더 걸릴 수 있습니다. 긴 네이버 이미지 PDF는 CPU 환경에서 페이지별 OCR 시간이 누적됩니다.

## 명령행

```powershell
# GUI 실행
python -m receipt_mvp gui

# 표준 데이터 모델의 JSON Schema 출력
python -m receipt_mvp schema --output receipt-schema.json

# 버전 확인
python -m receipt_mvp --version
```

## 검증 범위

개발 중 자동 테스트 33개가 통과했습니다. 실제 예시 자료 검증은 쿠팡 PDF 18페이지 전체와 네이버 PDF 대표 1페이지를 대상으로 완료했습니다. 사용자 요청에 따라 네이버 나머지 26페이지 전체 OCR 및 이후의 장시간 테스트는 생략했습니다.

따라서 현재 버전은 MVP이며, 새로운 발급 양식이나 긴 네이버 영수증 묶음을 운영에 투입하기 전에는 결과 검토가 필요합니다. 상세 내용은 [테스트 보고서](docs/TEST_REPORT.md)와 [알려진 제한사항](docs/KNOWN_LIMITATIONS.md)을 확인하세요.

## 개인정보와 Git 관리

- 원본 영수증, 생성 Excel, OCR 임시 이미지, 로그는 커밋하지 않습니다.
- `sample_output/`은 `.gitkeep`만 추적하며 실제 결과 파일은 `.gitignore`에서 제외합니다.
- 테스트용 실데이터 경로는 환경 변수로만 전달하고 소스에 하드코딩하지 않습니다.
- 로그 유틸리티는 카드·사업자번호 등 민감 패턴을 마스킹합니다.

## 프로젝트 구조

```text
src/receipt_mvp/
  extractors/    PDF·이미지 입력 및 페이지 추출
  ocr/           이미지 전처리와 PaddleOCR 어댑터
  classifiers/   발급처·문서 유형 분류
  parsers/       쿠팡·네이버·일반 영수증 파서
  normalizers/   날짜·금액·식별번호 정규화
  validators/    금액·사업자번호·중복·상태 검증
  exporters/     Excel 워크북 생성 및 재열기 검증
  services/      전체 처리 파이프라인
  ui/            PySide6 데스크톱 UI
tests/           단위·구성요소·통합·UI 테스트
docs/            구조·검증·제한사항·릴리스 문서
```

설계 세부사항은 [아키텍처 문서](docs/ARCHITECTURE.md)를 참고하세요.

## GitHub 업로드 전 확인

[GitHub 릴리스 체크리스트](docs/GITHUB_RELEASE_CHECKLIST.md)에 따라 원본 영수증·파생 파일이 추적되지 않는지 확인한 뒤 원격 저장소를 연결하세요.

## 라이선스

현재 `pyproject.toml`은 `Proprietary`로 표시되어 있습니다. 공개 저장소로 배포하려면 소유자가 적절한 라이선스를 결정하고 `LICENSE` 파일을 추가해야 합니다.
