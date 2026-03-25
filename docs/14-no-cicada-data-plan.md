# No Cicada Data Plan

## Why this matters
- The current baseline only answers "which cicada species is this?"
- A real app must also answer:
  - Is there any cicada sound at all?
  - Is the clip too noisy to trust?
  - Is this mixed with traffic, wind, birds, or people?

## New label layer
- `presence_label`
  - `cicada_present`
  - `no_cicada`
  - `unclear`
- `noise_type`
  - `wind`
  - `traffic`
  - `voices`
  - `birds`
  - `water`
  - `indoor`
  - `mixed`
  - `other`

## Folder scaffold
- `data-workspace/raw_audio/no_cicada/`
- `data-workspace/derived_audio/no_cicada/`
- `data-workspace/metadata/no_cicada_manifest.csv`

## Collection targets
- At least 300 clips before first binary gate
- At least 50 clips per major noise type
- At least 3 phone models
- Both quiet and noisy outdoor settings

## Release gate
- The app should be allowed to say:
  - "매미 소리가 뚜렷하지 않습니다"
  - "배경 소음이 커서 다시 녹음해 주세요"
- Do not ship a species-only classifier without this path.
