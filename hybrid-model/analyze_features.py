"""Analyze feature importance by class."""
import numpy as np
from pathlib import Path

data_dir = Path("data/processed_v2")
all_sequences = np.load(data_dir / "all_sequences.npy")
all_labels = np.load(data_dir / "all_labels.npy")

print(f"Data shape: {all_sequences.shape}")
print(f"Labels: {np.unique(all_labels, return_counts=True)}")

# For each feature dimension, compute mean per class and see which are most discriminative
n_features = all_sequences.shape[2]
n_classes = len(np.unique(all_labels))

# Compute ANOVA F-statistic for each feature
from sklearn.feature_selection import f_classif

# Reshape: (n_samples, seq_len, n_features) -> (n_samples, seq_len * n_features)
X_flat = all_sequences.reshape(all_sequences.shape[0], -1)
y = all_labels

f_scores, p_values = f_classif(X_flat, y)

# Top 20 features
top_indices = np.argsort(f_scores)[::-1][:30]
print("\nTop 30 discriminative features (flattened indices):")
for idx in top_indices:
    seq_idx = idx // 512
    feat_idx = idx % 512
    print(f"  Dim {idx:4d} (seq_t={seq_idx:2d}, feat={feat_idx:3d}): F={f_scores[idx]:.3f}, p={p_values[idx]:.4f}")

# Now analyze per-frame features (averaged across sequence)
X_mean = all_sequences.mean(axis=1)  # (150, 512)
f_scores_mean, p_values_mean = f_classif(X_mean, y)

top_mean = np.argsort(f_scores_mean)[::-1][:30]
print("\nTop 30 discriminative features (sequence-averaged):")
feature_names = {
    0: "person_count", 1: "object_count", 2: "person_conf", 3: "obj_conf",
    330: "person_vzone", 331: "near_ground", 332: "standing_tall",
    333: "person_hzone", 334: "far_left", 335: "far_right",
    340: "speed", 341: "h_speed", 342: "v_speed", 343: "moving_flag",
    350: "aspect_ratio", 351: "posture_change", 352: "bending", 353: "standing",
    360: "udder_dist", 361: "near_udder",
    370: "walking_range", 371: "walking_flag",
}
for idx in top_mean:
    name = feature_names.get(idx, f"feat_{idx}")
    print(f"  Dim {idx:3d} ({name:20s}): F={f_scores_mean[idx]:.3f}, p={p_values_mean[idx]:.4f}")

# Per-class feature means for top features
print("\nPer-class means for top action features:")
action_dims = [330, 331, 332, 333, 334, 335, 340, 341, 342, 343, 350, 351, 352, 353, 360, 361, 370, 371]
task_names = ["TASK-01", "TASK-02", "TASK-03", "TASK-04", "TASK-05", "TASK-06"]
for dim in action_dims:
    name = feature_names.get(dim, f"feat_{dim}")
    means = [X_mean[y == i, dim].mean() for i in range(6)]
    print(f"  {name:20s}: " + " | ".join(f"{t}={m:.3f}" for t, m in zip(task_names, means)))
    print
