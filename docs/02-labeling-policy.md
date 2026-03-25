# 라벨링 정책

## 필수 라벨 필드

- `species_label`
  - `chammaemi`
  - `malmaemi`
  - `yujimaemi`
  - `unknown`
- `label_confidence`
  - `confirmed`
  - `probable`
  - `uncertain`
- `acoustic_quality`
  - `good`
  - `fair`
  - `poor`
- `mixture_flag`
  - `single_species`
  - `possible_multiple_species`
  - `no_cicada_detected`

## label_evidence 값

- `adult_photo`
- `exuvia_photo`
- `expert_verified`
- `repeated_field_observation`

## 운영 원칙

- `confirmed`만 학습용 핵심 정답셋에 우선 포함한다.
- `probable`는 보조 학습 또는 검토 후보로만 쓴다.
- `uncertain`은 평가셋에 넣지 않는다.
- `possible_multiple_species`는 1차 분류 학습에서 제외하고 별도 검토 큐로 보낸다.
- `no_cicada_detected`는 존재 여부 판단 실험에 사용한다.

## 검수 흐름

1. 1차 입력자가 세션 메타데이터를 작성한다.
2. 2차 검수자가 종 라벨과 품질을 검토한다.
3. 충돌 시 검수 메모를 남기고 `uncertain`으로 보류한다.

## 1차 MVP 운영 규칙

- 앱 결과는 단일 종 우선으로 보여준다.
- 내부 데이터에서는 `unknown`, `possible_multiple_species`, `no_cicada_detected`를 별도 상태로 관리한다.
