import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else r"ml-workspace\reports\cnn_experiment_filtered_report.json"
out_path = sys.argv[2] if len(sys.argv) > 2 else r"ml-workspace\filtered_report_summary.txt"
d = json.load(open(path, "r", encoding="utf-8"))

lines = []
lines.append(f"Train: {d['dataset']['train_rows']}  Val: {d['dataset']['val_rows']}  Test: {d['dataset']['test_rows']}")
lines.append(f"Best val acc: {d['training']['best_val_accuracy']:.4f}")
lines.append(f"Test accuracy: {d['test_metrics']['accuracy']:.4f}")
lines.append(f"Macro F1: {d['test_metrics']['macro avg']['f1-score']:.4f}")
lines.append("")
lines.append("Per-class metrics:")
for k, v in d['test_metrics'].items():
    if isinstance(v, dict) and 'precision' in v and k not in ('macro avg', 'weighted avg'):
        lines.append(f"  {k:20s}  p={v['precision']:.3f}  r={v['recall']:.3f}  f1={v['f1-score']:.3f}  n={v['support']}")
lines.append("")
lines.append("Top confusion pairs:")
for pair in d['confusion_matrix']['off_diagonal'][:15]:
    lines.append(f"  {pair['true']:20s} -> {pair['pred']:20s}  count={pair['count']}")

text = "\n".join(lines)
print(text)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)
