import cv2
import argparse
import time
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--task", default="task_01_precleaning")
parser.add_argument("--frames_dir", default="hybrid-model/data/frames")
parser.add_argument("--config", default="configs/default.yaml")
parser.add_argument("--max_frames", type=int, default=500)
parser.add_argument("--no_display", action="store_true")
args = parser.parse_args()

# Lazy import of project modules
import sys
# Ensure we can import project src modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import load_config
from detection.multimodal_feature_extractor import MultimodalFeatureExtractor
from temporal.lstm_model import MilkingActionLSTM

config = load_config(args.config)

# Initialize multimodal extractor and LSTM
mm = MultimodalFeatureExtractor(config)

from config import get_device
device = get_device(config)
lstm = MilkingActionLSTM(
    input_size=config.lstm.input_size,
    hidden_size=config.lstm.hidden_size,
    num_layers=config.lstm.num_layers,
    num_classes=config.lstm.num_classes,
    dropout=config.lstm.dropout,
    bidirectional=config.lstm.bidirectional
)
import torch
lstm.to(device)

# Load weights
ckpt = Path(config.checkpoints_dir) / "best_model.pt"
if ckpt.exists():
    chk = torch.load(str(ckpt), map_location=device)
    lstm.load_state_dict(chk['model_state_dict'])
    print(f"Loaded weights from {ckpt}")
else:
    print(f"No LSTM weights found at {ckpt}, running with random init")

from collections import deque
buffer = deque(maxlen=config.lstm.sequence_length)

frames_path = Path(args.frames_dir) / args.task
files = sorted(frames_path.glob('*.jpg'))[: args.max_frames]
print(f"Running inference on {len(files)} frames from {frames_path}")

for i, f in enumerate(files):
    img = cv2.imread(str(f))
    if img is None:
        continue
    feat = mm.extract_features(img).feature_vector
    buffer.append(feat)

    if len(buffer) < config.lstm.sequence_length:
        continue

    seq = np.array(buffer)
    seq_t = torch.FloatTensor(seq).unsqueeze(0).to(device)
    with torch.no_grad():
        output, att = lstm(seq_t, return_attention=True)
        probs = torch.softmax(output, dim=1)
        conf, pred = torch.max(probs, dim=1)
        conf = conf.item(); pred = pred.item()
    if conf >= config.inference.lstm_threshold:
        task_names = ["Pre-cleaning","Stripping","Machine attachment","Milking (active)","Detachment","Post-dip"]
        print(f"Frame {i}: Detected {task_names[pred]} (conf={conf:.2f})")
    if not args.no_display:
        # simple visualization
        disp = img.copy()
        cv2.putText(disp, f"Pred: {pred} ({conf:.2f})", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0),2)
        cv2.imshow('Inference', disp)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

if not args.no_display:
    cv2.destroyAllWindows()
print('Done')
