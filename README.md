# maemi_translater

이 저장소는 대한민국 매미 울음소리 온디바이스 식별 프로젝트의 **실행 준비용 워크스페이스**다.
지금 단계에서는 앱 구현이나 모델 학습 코드보다, 아래 3가지를 먼저 고정하는 데 초점을 둔다.

1. 녹음본 수집과 라벨링 규칙
2. 로컬 머신러닝 실험 순서와 평가 기준
3. 안드로이드 우선 1차 앱 UX 초안

## 현재 기준선

- 1차 범위: `참매미`, `말매미`, `유지매미`
- 앱 타깃: 안드로이드 우선
- 추론 구조: `학습은 PC`, `추론은 스마트폰`
- 사용자 녹음 길이: `5초`
- 내부 분석 창: `3초 슬라이딩`

## 폴더 구조

- `data-workspace/`: 원본 녹음, 가공 오디오, 메타데이터, 검수 메모
- `ml-workspace/`: 실험 계획, 평가 결과, 모델 비교 기록
- `design-workspace/`: 앱 흐름, UX 문구, LLM 프롬프트, 와이어프레임 초안
- `docs/`: 운영 문서와 체크리스트
- `scripts/`: 로컬 환경 점검 등 보조 스크립트

## 먼저 볼 문서

1. `docs/00-environment-baseline.md`
2. `docs/01-data-collection-spec.md`
3. `docs/02-labeling-policy.md`
4. `docs/03-ml-experiment-plan.md`
5. `docs/04-app-ux-brief.md`
6. `docs/05-stage-gates.md`
7. `docs/06-next-actions.md`
8. `docs/07-public-seed-audio.md`
9. `docs/08-recording-session-convention.md`
10. `docs/10-android-screen-spec.md`
11. `docs/11-baseline-runbook.md`
12. `docs/12-worldwide-audio-harvest.md`

## 지금 해야 할 일

- Python `3.12` 설치 여부를 확정한다.
- `ffmpeg` 설치 여부를 확정한다.
- 첫 현장 수집 지역과 날짜를 잡는다.
- 종 확인 근거를 남길 촬영 방식과 검수 방식을 고정한다.

## 자동화 도구

- 환경 점검: `powershell -ExecutionPolicy Bypass -File .\scripts\check-local-environment.ps1`
- 가상환경 준비: `powershell -ExecutionPolicy Bypass -File .\scripts\setup-ml-env.ps1`
- 공개 시드 음원 다운로드: `py -3.12 .\scripts\download_public_seed_audio.py`
- 공개 시드 음원 정규화: `powershell -ExecutionPolicy Bypass -File .\scripts\normalize-public-seed-audio.ps1`
- 세션 폴더 만들기: `powershell -ExecutionPolicy Bypass -File .\scripts\new-recording-session.ps1`
- 메타데이터 검증: `.\\.venv\\Scripts\\python.exe .\\scripts\\validate_session_metadata.py`
- 특성추출: `.\\.venv\\Scripts\\python.exe .\\scripts\\extract_manifest_features.py <manifest.csv>`
- 특성 기반 학습: `.\\.venv\\Scripts\\python.exe .\\scripts\\train_baseline_from_features.py <features.npz> <metadata.csv>`

## 대시보드

- 로컬 대시보드: `dashboard/index.html`
- 데이터 payload 생성: `.\\.venv\\Scripts\\python.exe .\\scripts\\build_dashboard_payload.py`

## 원칙

- 원본 오디오는 수정하지 않는다.
- 라벨 근거 없는 파일은 학습용 정답셋으로 승격하지 않는다.
- 랜덤 분할 점수보다 세션/장소/기기 홀드아웃 성능을 우선한다.
- 낮은 확신도에서는 답을 보류하는 UX를 기본값으로 삼는다.
