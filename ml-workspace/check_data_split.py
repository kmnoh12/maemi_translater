import csv, os
from collections import Counter

def analyze(path, label):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    species_count = Counter()
    inat_count = 0
    yt_count = 0
    yt_by_species = Counter()
    inat_by_species = Counter()
    
    for row in rows:
        sp = row['species_code']
        ap = row['audio_path']
        species_count[sp] += 1
        if 'inat' in ap:
            inat_count += 1
            inat_by_species[sp] += 1
        if 'youtube' in ap:
            yt_count += 1
            yt_by_species[sp] += 1
    
    lines = []
    lines.append(f"--- {label} ---")
    lines.append(f"Total: {len(rows)}, iNat: {inat_count}, YouTube: {yt_count}")
    for sp in sorted(species_count.keys()):
        lines.append(f"  {sp}: total={species_count[sp]} inat={inat_by_species.get(sp,0)} yt={yt_by_species.get(sp,0)}")
    return "\n".join(lines)

out = []
out.append(analyze("ml-workspace/experiments/cnn_dataset_combined/cnn_manifest.csv", "COMBINED"))
out.append(analyze("ml-workspace/experiments/cnn_dataset_combined_filtered/cnn_manifest.csv", "FILTERED"))

# Check split
split_path = "ml-workspace/experiments/cnn_dataset_combined_filtered/cnn_manifest_with_split.csv"
if os.path.exists(split_path):
    with open(split_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    sc = Counter(r.get('split','?') for r in rows)
    out.append(f"--- FILTERED SPLIT ---")
    out.append(f"Total: {len(rows)}")
    for k,v in sorted(sc.items()):
        out.append(f"  {k}: {v}")
else:
    out.append("No filtered split file")

with open("ml-workspace/data_analysis_result.txt", "w") as f:
    f.write("\n".join(out))

print("\n".join(out))
