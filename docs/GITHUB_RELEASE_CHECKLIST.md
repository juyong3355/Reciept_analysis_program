# GitHub 업로드 체크리스트

## 개인정보와 비밀정보

- [ ] 원본 PDF·이미지·생성 Excel·OCR 임시 파일이 추적되지 않는다.
- [ ] `git status --ignored`에서 `sample_output` 결과가 ignored로 표시된다.
- [ ] 사용자 로컬 절대 경로, 토큰, 이메일, 실제 카드·사업자번호가 소스에 없다.
- [ ] 공개 저장소라면 `LICENSE`와 보안 연락처를 확정했다.

## 저장소 품질

- [ ] `README.md`의 설치·실행 방법을 새 환경에서 확인했다.
- [ ] `requirements-lock.txt`의 버전이 대상 Python/Windows와 맞는다.
- [ ] 필요 시 빠른 테스트와 CI를 실행했다.
- [ ] 버전과 변경 기록을 확정했다.
- [ ] 기본 브랜치가 `main`이고 의도한 파일만 커밋되었다.

## 업로드 명령 예시

아래 `<REMOTE_URL>`을 실제 비어 있는 GitHub 저장소 주소로 바꿉니다.

```powershell
git remote add origin <REMOTE_URL>
git push -u origin main
```

원격 저장소 생성과 push는 외부 상태를 변경하므로 저장소 소유자가 최종 확인 후 수행합니다.
