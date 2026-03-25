# 안드로이드 1차 화면 명세서

## 목적

- 개발 전에 화면 단위 책임과 입출력 값을 고정한다.
- 결과적으로 UI 구현 시점에 “이 화면이 무엇을 보여줘야 하는지”를 다시 결정하지 않게 한다.

## 공통 규칙

- 앱은 1차에서 `참매미`, `말매미`, `유지매미` 중심으로 시작하되 내부 구조는 확장 가능하게 둔다.
- 화면 문구는 정답 단정형 대신 가능성 표현을 쓴다.
- 확신이 낮으면 결과 대신 재녹음 행동을 우선 노출한다.
- 1차 결과 객체는 최소 아래 값을 가진다고 가정한다.
  - `top_label`
  - `top_probability`
  - `candidate_labels`
  - `low_confidence`
  - `no_cicada_detected`
  - `mixture_possible`

## Screen 1. Home

- 목적: 녹음 시작 전 진입점과 사용 기대치를 제공
- 주요 요소:
  - 화면 제목
  - 5초 녹음 안내
  - 지원 종 요약
  - `녹음 시작` 버튼
- 필요 상태:
  - 마이크 권한 미허용
  - 마이크 권한 허용
- 사용자 액션:
  - 권한 요청
  - 녹음 시작

## Screen 2. Recording

- 목적: 5초 녹음 진행 표시
- 주요 요소:
  - 남은 시간 타이머
  - 녹음 안내 문구
  - 취소 버튼
- 필요 상태:
  - recording_active
  - recording_cancelled
  - recording_complete
- 표시 규칙:
  - 진행 중에는 복잡한 정보 대신 자세 안내만 보여준다.

## Screen 3. Quality Check

- 목적: 분석 전에 음질과 신호 존재 여부를 점검
- 입력:
  - 녹음된 원본 오디오
  - 간단 품질 점검 결과
- 주요 요소:
  - `분석 가능`
  - `재녹음 권장`
  - `매미 소리 없음`
- 필요 상태:
  - quality_pass
  - quality_retry
  - no_cicada
- 사용자 액션:
  - 다시 녹음
  - 그래도 분석
  - 홈으로 이동

## Screen 4. Analyzing

- 목적: 특징 추출 및 종 분류 대기 화면
- 주요 요소:
  - 로딩 인디케이터
  - 짧은 진행 문구
- 비기능 요구:
  - 1차 MVP에서는 2초 안쪽으로 끝나는 경험이 목표

## Screen 5. Result High Confidence

- 목적: top-1 결과를 중심으로 설명
- 입력:
  - `top_label`
  - `top_probability`
  - 보조 후보 2개
- 주요 요소:
  - 대표 종명
  - 간단 설명
  - 다음 후보
  - 종 설명 보기 버튼
  - 다시 녹음 버튼
- 표시 규칙:
  - 확신 높음이어도 “가능성이 높다” 표현 유지

## Screen 6. Result Low Confidence

- 목적: 답 보류와 재시도 유도
- 입력:
  - `candidate_labels`
  - `low_confidence = true`
  - `mixture_possible` 또는 품질 경고
- 주요 요소:
  - 불확실 안내 문구
  - 재녹음 팁 2~3개
  - 후보 보기 버튼
  - 다시 녹음 버튼
- 표시 규칙:
  - top-1 숫자만 크게 노출하지 않는다.

## Screen 7. Species Detail

- 목적: 종의 설명과 구분 포인트 제공
- 입력:
  - 종명
  - 간단 소개
  - 비슷한 종과 차이
  - 주로 들리는 시기/장소
- 주요 요소:
  - 종 소개 카드
  - 유사 종 비교 문구
  - 다시 녹음 버튼

## 네비게이션 요약

- Home -> Recording
- Recording -> Quality Check
- Quality Check -> Analyzing
- Quality Check -> Recording
- Analyzing -> Result High Confidence
- Analyzing -> Result Low Confidence
- Result High Confidence -> Species Detail
- Result Low Confidence -> Species Detail
- Result High Confidence -> Recording
- Result Low Confidence -> Recording

## 구현 전 확인할 것

- low confidence 기준값을 언제부터 적용할지
- no_cicada와 quality_retry를 같은 화면으로 합칠지
- candidate_labels를 2개만 보여줄지 3개까지 보여줄지
- 종 설명 데이터의 최소 항목을 무엇으로 고정할지
