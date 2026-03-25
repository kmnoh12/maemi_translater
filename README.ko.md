# 매미번역기

[English README](./README.md)

매미번역기는 매미 소리 분류를 목표로 하는 프로젝트입니다. 현장 녹음 워크플로우, 데이터셋 구축, 머신러닝 실험, 안드로이드 중심 제품 기획을 하나의 저장소에서 함께 관리합니다.

지금 이 저장소는 완성된 앱 배포본이라기보다, 실제로 데이터를 모으고 모델을 실험하고 제품 초안을 발전시키기 위한 작업 기반에 가깝습니다. 핵심은 전체 파이프라인을 재현 가능하게 유지하는 것입니다.

## 한눈에 보기

- 한국 매미 음원 데이터셋을 체계적으로 수집하고 라벨링하기
- 베이스라인, 가중치 모델, CNN, 전이학습 모델을 비교 실험하기
- 안드로이드 우선 UX와 추론 인터페이스를 설계하기
- 대시보드로 예측 결과와 샘플 자산을 검토하기
- 문서, 스크립트, 산출물, 실험 기록을 한 저장소에서 관리하기

## 현재 범위

현재 MVP 기준 가정은 다음과 같습니다.

- 주요 한국 매미 종을 분류 대상으로 둡니다
- 제품 방향은 `Android-first`입니다
- 입력 오디오는 대체로 `5초` 길이를 기준으로 다룹니다
- 분석과 검토는 `3초 내외의 슬라이딩 윈도우` 흐름을 염두에 둡니다
- PC 기반 데이터/ML 작업과 모바일 추론 설계를 함께 지원합니다

## 저장소 구조

```text
.
|-- dashboard/          예측 결과 검토용 대시보드와 샘플 자산
|-- data-workspace/     메타데이터, 매니페스트, 리뷰 큐, 원본/가공 오디오 폴더
|-- design-workspace/   안드로이드 UX 초안, 프롬프트, 와이어프레임, 추론 스펙
|-- docs/               운영 문서, 정책, 단계별 계획, 런북
|-- ml-workspace/       실험, 리포트, 노트북, 학습 산출물, 분석 결과
|-- requirements/       환경 구성용 요구사항 파일
`-- scripts/            데이터 처리, 학습, 검증, 정규화, 대시보드 보조 스크립트
```

## 포함된 내용

### 데이터 파이프라인

- 공개 시드 음원 매니페스트
- YouTube, iNaturalist 수집용 매니페스트
- 저품질 검토 큐와 필터링 리포트
- 세션 메타데이터 검증 스크립트

### 머신러닝 워크스페이스

- 특징 추출 스크립트
- 전통적 ML 베이스라인 및 가중치 기반 학습 흐름
- CNN 및 전이학습 실험 코드
- 저장된 모델 아티팩트와 실험 결과

### 제품 및 UX

- 안드로이드 MVP 와이어프레임
- UX 카피 및 플로우 프롬프트
- 추론 계약 예시
- 샘플 클립과 스펙트로그램이 포함된 대시보드 자산

## 시작하기

### 1. 로컬 환경 점검

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-local-environment.ps1
```

### 2. ML 환경 준비

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-ml-env.ps1
```

### 3. 공개 시드 음원 다운로드 및 정규화

```powershell
py -3.12 .\scripts\download_public_seed_audio.py
powershell -ExecutionPolicy Bypass -File .\scripts\normalize-public-seed-audio.ps1
```

### 4. 세션 메타데이터 검증

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_session_metadata.py
```

### 5. 특징 추출 및 베이스라인 학습

```powershell
.\.venv\Scripts\python.exe .\scripts\extract_manifest_features.py <manifest.csv>
.\.venv\Scripts\python.exe .\scripts\train_baseline_from_features.py <features.npz> <metadata.csv>
```

## 대시보드

예측 결과와 샘플 자산을 빠르게 훑어볼 수 있는 가벼운 대시보드가 포함되어 있습니다.

- 진입점: `dashboard/index.html`
- 페이로드 생성: `.\.venv\Scripts\python.exe .\scripts\build_dashboard_payload.py`

## 먼저 읽으면 좋은 문서

- `docs/00-environment-baseline.md`
- `docs/01-data-collection-spec.md`
- `docs/02-labeling-policy.md`
- `docs/03-ml-experiment-plan.md`
- `docs/04-app-ux-brief.md`
- `docs/05-stage-gates.md`
- `docs/06-next-actions.md`
- `docs/10-android-screen-spec.md`
- `docs/11-baseline-runbook.md`
- `docs/12-worldwide-audio-harvest.md`

## 작업 원칙

- 원본 음원은 덮어쓰지 않습니다
- 근거 없는 파일을 학습 정답 데이터로 밀어 넣지 않습니다
- 세션, 장소, 기기 경계를 고려한 분할을 우선합니다
- 불확실한 경우 보류하는 UX를 기본값으로 둡니다
- 겉보기 완성도보다 재현 가능성과 운영 명확성을 우선합니다

## 현재 상태

이 저장소는 활발히 발전 중인 연구 및 구축 워크스페이스입니다. 문서, 스크립트, 산출물은 이미 많이 들어 있지만, 완성된 서비스라기보다 매미 인식 제품으로 가는 기반 저장소로 보는 편이 맞습니다.

## 라이선스

아직 라이선스가 없습니다. 외부 배포나 협업을 본격화하기 전에 라이선스를 추가하는 것을 권장합니다.
