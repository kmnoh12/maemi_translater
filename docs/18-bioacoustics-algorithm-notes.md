# Bioacoustics Algorithm Notes

## Why move beyond the current baseline
- The current feature-engineered baseline is a good sanity check.
- It is not strong enough for the hardest confusion pair: `aemaemi <-> chammaemi`.
- Bird audio systems usually lean on spectrogram-based CNNs or pretrained bioacoustic embeddings, not only MFCC summary statistics.

## References to copy from bird-audio practice
- BirdNET:
  - real-world bird sound recognition pipeline built around spectrogram-based deep learning
  - useful lesson: short segments, strong local patterns, mobile-friendly inference
  - Source: https://birdnet.cornell.edu/home/
- BirdNET Analyzer:
  - emphasizes segmentation + spectrogram classification workflow
  - Source: https://birdnet.cornell.edu/analyzer/
- Google bird-audio research:
  - separation and robust audio representation can improve classification in mixed/noisy recordings
  - Source: https://research.google/pubs/improving-bird-classification-with-unsupervised-sound-separation/

## What to apply to this cicada project
1. Keep 3-second windows for now.
2. Export log-mel spectrogram images per window.
3. Split by `observation_id`, never by random image rows.
4. Train a small CNN only after the image dataset and split manifest are stable.
5. Keep the abstain rule even after the CNN, because field audio remains messy.

## Immediate local pipeline
- `extract_logmel_embedding_features.py`
  - richer 1D vector features for quick comparison
- `export_cnn_spectrogram_dataset.py`
  - window-level image export for CNN training
- `build_group_split_manifest.py`
  - observation-level train/val/test separation
- `train_cnn_experiment.py`
  - runtime scaffold that waits for TensorFlow installation

## Important caveat
- This PC currently does not have TensorFlow, PyTorch, or ONNX Runtime installed.
- So today the right move is to prepare the dataset and experiment structure first, then install a deep-learning runtime and run the CNN next.
