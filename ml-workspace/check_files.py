import csv
from collections import Counter

def count_unique_files(path, label):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    inat_files = set()
    yt_files = set()
    inat_windows = 0
    yt_windows = 0
    
    for row in rows:
        ap = row['audio_path']
        if 'inat' in ap:
            inat_files.add(ap)
            inat_windows += 1
        if 'youtube' in ap:
            yt_files.add(ap)
            yt_windows += 1
    
    lines = []
    lines.append(f"--- {label} ---")
    lines.append(f"iNat:    {len(inat_files):>5} files -> {inat_windows:>6} windows")
    lines.append(f"YouTube: {len(yt_files):>5} files -> {yt_windows:>6} windows")
    lines.append(f"iNat avg windows/file:    {inat_windows/max(len(inat_files),1):.1f}")
    lines.append(f"YouTube avg windows/file: {yt_windows/max(len(yt_files),1):.1f}")
    
    # per-species breakdown
    sp_inat = Counter()
    sp_yt = Counter()
    sp_inat_f = {}
    sp_yt_f = {}
    for row in rows:
        sp = row['species_code']
        ap = row['audio_path']
        if 'inat' in ap:
            sp_inat[sp] += 1
            sp_inat_f.setdefault(sp, set()).add(ap)
        if 'youtube' in ap:
            sp_yt[sp] += 1
            sp_yt_f.setdefault(sp, set()).add(ap)
    
    lines.append("\nPer species (files / windows):")
    all_sp = sorted(set(list(sp_inat.keys()) + list(sp_yt.keys())))
    for sp in all_sp:
        i_f = len(sp_inat_f.get(sp, set()))
        i_w = sp_inat[sp]
        y_f = len(sp_yt_f.get(sp, set()))
        y_w = sp_yt[sp]
        lines.append(f"  {sp:20s}: iNat={i_f:>3}files/{i_w:>5}win  YT={y_f:>3}files/{y_w:>5}win")
    
    return "\n".join(lines)

out = []
out.append(count_unique_files("ml-workspace/experiments/cnn_dataset_combined/cnn_manifest.csv", "COMBINED"))
out.append("")
out.append(count_unique_files("ml-workspace/experiments/cnn_dataset_combined_filtered/cnn_manifest.csv", "FILTERED"))

result = "\n".join(out)
with open("ml-workspace/file_count_result.txt", "w") as f:
    f.write(result)
print(result)
