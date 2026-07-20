"""
Semi-Automatic Labeler for Custom YOLO Training
=================================================
Runs the current YOLO model on all extracted frames to generate
pre-annotations. You review and correct them via a tkinter GUI.

Usage:
    cd hybrid-model
    python semi_auto_labeler.py

Controls:
    - Left click + drag: Draw new bounding box (appears as "person")
    - Number keys 0-5: Change class of last drawn box
        0=person, 1=pipe_sprayer, 2=stripping_cup, 3=teat_cup_on, 4=teat_cup_off, 5=dip_applicator
    - Right click on box: Delete box
    - 'a': Accept current image (save and go to next)
    - 's': Skip current image (don't save)
    - 'd': Delete last box
    - 'q': Quit and save progress

The script:
1. Loads all frames from data/frames/
2. Runs YOLO model to pre-annotate
3. Shows you the image with pre-annotations
4. You correct any mistakes (add/remove/adjust boxes)
5. Saves to data/labels/annotations.json
"""

import json
import tkinter as tk
from tkinter import Canvas
from pathlib import Path
from PIL import Image, ImageTk
import cv2
import numpy as np
from ultralytics import YOLO
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
CLASSES = ["person", "pipe_sprayer", "stripping_cup", "teat_cup_on", "teat_cup_off", "dip_applicator"]

# Paths
PROJECT_ROOT = Path(__file__).parent
FRAMES_DIR = PROJECT_ROOT / "data" / "frames"
LABELS_FILE = PROJECT_ROOT / "data" / "labels" / "annotations.json"
MODEL_PATH = PROJECT_ROOT / "models" / "milking_custom" / "weights" / "best.pt"

# Load existing annotations if any
def load_annotations():
    if LABELS_FILE.exists():
        with open(LABELS_FILE) as f:
            raw = json.load(f)
        # Convert old format to new format
        if "images" not in raw:
            converted = {"images": {}, "classes": CLASSES}
            for path, boxes in raw.items():
                converted["images"][path] = {
                    "boxes": [{"x1": b["x1"], "y1": b["y1"], "x2": b["x2"], "y2": b["y2"], "class_id": b["class"]} for b in boxes]
                }
            return converted
        return raw
    return {"images": {}, "classes": CLASSES}

def save_annotations(data):
    LABELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LABELS_FILE, "w") as f:
        json.dump(data, f, indent=2)

class SemiAutoLabeler:
    def __init__(self, root):
        self.root = root
        self.root.title("Semi-Auto Labeler — Click 'Accept' or 'Skip'")
        
        # Load model
        print("Loading YOLO model...")
        self.model = YOLO(str(MODEL_PATH) if MODEL_PATH.exists() else "yolov8n.pt")
        print("Model loaded")
        
        # Load existing annotations
        self.annotations = load_annotations()
        
        # Get all frames
        self.all_frames = []
        for task_dir in sorted(FRAMES_DIR.iterdir()):
            if task_dir.is_dir():
                for img in sorted(task_dir.glob("*.jpg")):
                    rel_path = str(img.relative_to(FRAMES_DIR))
                    if rel_path not in self.annotations["images"]:
                        self.all_frames.append(img)
        
        self.current_idx = 0
        self.boxes = []  # Current image boxes: [(x1,y1,x2,y2,class_id)]
        self.drawing = False
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None
        
        # Setup GUI
        self.canvas_width = 900
        self.canvas_height = 600
        self.canvas = tk.Canvas(root, width=self.canvas_width, height=self.canvas_height, bg='black')
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        tk.Button(btn_frame, text="Accept (a)", command=self.accept, bg='green', fg='white', width=15).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(btn_frame, text="Skip (s)", command=self.skip, bg='orange', width=15).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(btn_frame, text="Delete Last (d)", command=self.delete_last, bg='red', fg='white', width=15).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(btn_frame, text="Quit (q)", command=self.quit, bg='gray', fg='white', width=15).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.status_label = tk.Label(btn_frame, text="", font=("Arial", 12))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Bindings
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        self.root.bind("a", lambda e: self.accept())
        self.root.bind("s", lambda e: self.skip())
        self.root.bind("d", lambda e: self.delete_last())
        self.root.bind("q", lambda e: self.quit())
        # Number keys 0-5 to change class of last drawn box
        for i in range(6):
            self.root.bind(str(i), lambda e, c=i: self.change_last_class(c))
        
        self.image_on_canvas = None
        self.photo = None
        self.scale = 1.0
        
        # Auto-annotate first image
        if self.all_frames:
            self.auto_annotate_current()
        
    def auto_annotate_current(self):
        if self.current_idx >= len(self.all_frames):
            self.status_label.config(text="All images labeled!")
            return
        
        img_path = self.all_frames[self.current_idx]
        
        # Run YOLO
        results = self.model(str(img_path), conf=0.15, verbose=False)[0]
        
        self.boxes = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id < len(CLASSES):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                self.boxes.append((x1, y1, x2, y2, cls_id))
        
        self.show_image()
        
    def show_image(self):
        if self.current_idx >= len(self.all_frames):
            return
        
        img_path = self.all_frames[self.current_idx]
        img = cv2.imread(str(img_path))
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Draw boxes
        for (x1, y1, x2, y2, cls_id) in self.boxes:
            color = self.get_color(cls_id)
            cv2.rectangle(img_rgb, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            label = CLASSES[cls_id] if cls_id < len(CLASSES) else f"cls_{cls_id}"
            cv2.putText(img_rgb, label, (int(x1), int(y1)-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Resize to fit canvas
        h, w = img_rgb.shape[:2]
        self.scale = min(self.canvas_width / w, self.canvas_height / h)
        new_w = int(w * self.scale)
        new_h = int(h * self.scale)
        img_resized = cv2.resize(img_rgb, (new_w, new_h))
        
        self.photo = ImageTk.PhotoImage(image=Image.fromarray(img_resized))
        if self.image_on_canvas:
            self.canvas.delete(self.image_on_canvas)
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Scale boxes for display
        self.scaled_boxes = []
        for (x1, y1, x2, y2, cls_id) in self.boxes:
            self.scaled_boxes.append((x1*self.scale, y1*self.scale, x2*self.scale, y2*self.scale, cls_id))
        
        # Update status
        rel_path = img_path.relative_to(FRAMES_DIR)
        n_pred = len(self.boxes)
        self.status_label.config(text=f"[{self.current_idx+1}/{len(self.all_frames)}] {rel_path} — {n_pred} predictions")
        
    def get_color(self, cls_id):
        colors = [
            (255, 0, 0),    # person - blue
            (0, 255, 0),    # pipe_sprayer - green
            (0, 0, 255),    # stripping_cup - red
            (255, 255, 0),  # teat_cup_on - cyan
            (255, 0, 255),  # teat_cup_off - magenta
            (0, 255, 255),  # dip_applicator - yellow
        ]
        return colors[cls_id % len(colors)]
    
    def on_press(self, event):
        self.drawing = True
        self.start_x = event.x
        self.start_y = event.y
        
    def on_drag(self, event):
        if self.drawing:
            if self.current_rect:
                self.canvas.delete(self.current_rect)
            self.current_rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline='yellow', width=2
            )
    
    def on_release(self, event):
        if self.drawing:
            self.drawing = False
            if self.current_rect:
                self.canvas.delete(self.current_rect)
                self.current_rect = None
            
            # Convert to original coordinates
            x1 = min(self.start_x, event.x) / self.scale
            y1 = min(self.start_y, event.y) / self.scale
            x2 = max(self.start_x, event.x) / self.scale
            y2 = max(self.start_y, event.y) / self.scale
            
            if abs(x2-x1) > 5 and abs(y2-y1) > 5:  # Minimum size
                # Add box as person (class 0) immediately
                self.boxes.append((x1, y1, x2, y2, 0))
                self.show_image()
    
    def change_last_class(self, cls_id):
        if self.boxes:
            x1, y1, x2, y2, _ = self.boxes[-1]
            self.boxes[-1] = (x1, y1, x2, y2, cls_id)
            self.show_image()
    
    def on_right_click(self, event):
        # Find box under cursor
        for i, (x1, y1, x2, y2, cls_id) in enumerate(self.scaled_boxes):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.boxes.pop(i)
                self.show_image()
                return
    
    def delete_last(self):
        if self.boxes:
            self.boxes.pop()
            self.show_image()
    
    def accept(self):
        if self.current_idx >= len(self.all_frames):
            return
        
        img_path = self.all_frames[self.current_idx]
        rel_path = str(img_path.relative_to(FRAMES_DIR))
        
        # Save with original coordinates
        self.annotations["images"][rel_path] = {
            "boxes": [{"x1": x1, "y1": y1, "x2": x2, "y2": y2, "class_id": cls_id} 
                      for (x1, y1, x2, y2, cls_id) in self.boxes]
        }
        
        save_annotations(self.annotations)
        print(f"Saved: {rel_path} ({len(self.boxes)} boxes)")
        
        self.current_idx += 1
        if self.current_idx < len(self.all_frames):
            self.auto_annotate_current()
        else:
            self.status_label.config(text="All images labeled!")
    
    def skip(self):
        self.current_idx += 1
        if self.current_idx < len(self.all_frames):
            self.auto_annotate_current()
        else:
            self.status_label.config(text="All images labeled!")
    
    def quit(self):
        save_annotations(self.annotations)
        print(f"Saved progress. {len(self.annotations['images'])} images labeled.")
        self.root.destroy()

def main():
    root = tk.Tk()
    root.geometry("950x700")
    app = SemiAutoLabeler(root)
    root.mainloop()

if __name__ == "__main__":
    main()
