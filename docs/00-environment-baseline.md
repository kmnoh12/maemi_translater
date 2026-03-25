# 로컬 환경 기준선

## 현재 확인된 상태

- Python 설치:
  - `3.12` at `C:\Users\kmnoh\AppData\Local\Programs\Python\Python312\python.exe`
  - `3.14` at `C:\Python314\python.exe`
  - `3.13` at `C:\Users\kmnoh\AppData\Local\Programs\Python\Python313\python.exe`
- `Node.js 24.11.1` 확인
- `git 2.49.0` 확인
- `winget 1.12.470` 확인
- `ffmpeg 8.0.1` 설치 완료
- 프로젝트 전용 `.venv` 생성 완료
- 핵심 오디오/ML 패키지 설치 완료

## 권장 기준

- 표준 Python 버전: `3.12`
- 이유:
  - 오디오 처리와 ML 패키지는 최신 메이저보다 안정 버전 호환성이 좋은 편이다.
  - 3.13/3.14는 일부 패키지에서 대응이 늦을 수 있다.
- 오디오 변환 도구: `ffmpeg`
- 가상환경: 프로젝트 전용 `.venv`

## 준비 순서

1. Python `3.12` 설치
2. `ffmpeg` 설치 및 PATH 등록
3. 프로젝트 전용 가상환경 생성
4. 오디오/ML 패키지 호환성 점검

## 보류 사항

- 아직 모델 학습 코드는 만들지 않았다.
- 아직 앱 빌드 툴체인을 설정하지 않았다.

## 완료 기준

- `py -0p`에 3.12가 보인다.
- `ffmpeg`가 새 셸 또는 직접 경로에서 정상 동작한다.
- 전용 가상환경이 생성되고 사용 규칙이 문서화된다.
