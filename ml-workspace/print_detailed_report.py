import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "ml-workspace/reports/cnn_experiment_filtered_report.json"
d = json.load(open(path, "r", encoding="utf-8"))

# Per-class as simple CSV
with open("ml-workspace/per_class_results.csv", "w", encoding="utf-8") as f:
    f.write("class,precision,recall,f1,support\n")
    for k, v in d["test_metrics"].items():
        if isinstance(v, dict) and "precision" in v and k not in ("macro avg", "weighted avg"):
            f.write(f"{k},{v['precision']:.4f},{v['recall']:.4f},{v['f1-score']:.4f},{v['support']}\n")

# Confusion pairs
with open("ml-workspace/confusion_pairs.csv", "w", encoding="utf-8") as f:
    f.write("true,pred,count\n")
    for pair in d["confusion_matrix"]["off_diagonal"][:20]:
        f.write(f"{pair['true']},{pair['pred']},{pair['count']}\n")

print("Written per_class_results.csv and confusion_pairs.csv")
