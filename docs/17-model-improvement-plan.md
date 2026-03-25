# Model Improvement Plan

## Goal
- Raise real-world reliability, not just overall cross-validation accuracy.
- Reduce the main confusion pair: `aemaemi <-> chammaemi`.
- Improve Korea-field performance before expanding model complexity.

## Current baseline limits
- Feature set is still `mfcc20_plus_spectral_stats_v1`.
- Final decision is dominated by simple 3-second window voting.
- Korea recordings are a small fraction of the total library.
- The confusion pair `aemaemi -> chammaemi` is one of the largest remaining errors.

## Immediate experiments
1. Korea-weighted logistic baseline
   - Increase weight for Korea recordings.
   - Increase additional weight for the focus pair `aemaemi/chammaemi`.
   - Compare against the existing baseline on:
     - overall accuracy
     - overall macro F1
     - Korea-only accuracy
     - Korea focus-pair accuracy

2. Focus-pair report
   - Track only `aemaemi <-> chammaemi`.
   - Use this report as the release gate for model changes.

3. Abstain rule simulation
   - If `top1-top2 gap < threshold` or `votes gap <= threshold`, classify as `low_confidence`.
   - Measure how much error drops when low-confidence cases are withheld.

## Next model candidates
1. Pretrained audio embedding + linear head
   - Best next step for small-to-medium data.
   - Candidate outputs should still be exportable to mobile later.

2. Small spectrogram CNN
   - Good comparison model after the embedding baseline.
   - Use only after the Korea-focused evaluation set is stable.

## Data priorities
1. More Korea recordings for:
   - `aemaemi`
   - `chammaemi`
   - `yujimaemi`
2. More hard cases:
   - mixed background noise
   - farther microphone distance
   - lower SNR
   - multiple calling individuals
3. Add `no_cicada` and `unknown` sets before app-level deployment.

## Release rule
- Do not trust overall accuracy alone.
- Treat the following as minimum gates:
  - Korea-only report must improve or stay stable.
  - Korea focus-pair report must improve.
  - Top confusion counts for `aemaemi -> chammaemi` must go down.
