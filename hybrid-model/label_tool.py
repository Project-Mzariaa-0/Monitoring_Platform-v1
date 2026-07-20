"""
Simple bounding box labeling tool for milking parlor objects.
Usage: python label_tool.py

Controls:
  - Click and drag to draw bounding box
  - Press 1-6 to assign class label
  - Press 's' to save annotation
  - Press 'n' for next image
  - Press 'p' for previous image
  - Press 'q' to quit
"""
import os
import json
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

CLASSES = {
    1: "person",
    2: "pipe_sprayer",
    3: "stripping_cup",
    4: "teat_cup_on",
    5: "teat_cup_off",
    6: "dip_applicator",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "frames")
LABELS_DIR = os.path.join(os.path.dirname(__file__), "data", "labels")
ANNOTATION_FILE = os.path.join(LABELS_DIR, "annotations.json")


class LabelTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Milking Parlor - Bounding Box Labeler")
        self.root.geometry("1200x800")

        self.images = []
        self.current_idx = 0
        self.annotations = {}
        self.current_class = 1
        self.rect_id = None
        self.start_x = 0
        self.start_y = 0
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.load_annotations()
        self.setup_ui()
        self.load_images()

    def setup_ui(self):
        # Top bar
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(top, text="Load Folder", command=self.load_images).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Save", command=self.save_annotations).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Prev (p)", command=self.prev_image).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Next (n)", command=self.next_image).pack(side=tk.LEFT, padx=2)

        self.lbl_info = tk.Label(top, text="No images loaded")
        self.lbl_info.pack(side=tk.LEFT, padx=10)

        # Class selector
        cls_frame = tk.Frame(self.root)
        cls_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(cls_frame, text="Class:").pack(side=tk.LEFT)
        self.class_var = tk.StringVar(value="1: person")
        for k, v in CLASSES.items():
            rb = tk.Radiobutton(cls_frame, text=f"{k}: {v}", variable=self.class_var,
                                value=f"{k}: {v}", command=lambda k=k: self.set_class(k))
            rb.pack(side=tk.LEFT, padx=3)

        # Canvas
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(canvas_frame, bg="#1a1b23", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)
        self.root.bind("n", lambda e: self.next_image())
        self.root.bind("p", lambda e: self.prev_image())
        self.root.bind("s", lambda e: self.save_annotations())
        self.root.bind("q", lambda e: self.root.quit())
        self.root.bind("d", lambda e: self.delete_last_box())

        # Status bar
        self.status = tk.Label(self.root, text="Controls: drag=draw box | right-click=delete box | d=delete last | n/p=next/prev | s=save", anchor=tk.W)
        self.status.pack(fill=tk.X, padx=5, pady=2)

    def load_images(self):
        folder = filedialog.askdirectory(title="Select frames folder")
        if not folder:
            return
        self.images = []
        for root_dir, dirs, files in os.walk(folder):
            for f in sorted(files):
                if f.lower().endswith((".jpg", ".jpeg", ".png")):
                    self.images.append(os.path.join(root_dir, f))
        self.current_idx = 0
        self.lbl_info.config(text=f"0/{len(self.images)} images")
        if self.images:
            self.show_image()

    def load_annotations(self):
        if os.path.exists(ANNOTATION_FILE):
            with open(ANNOTATION_FILE, "r") as f:
                self.annotations = json.load(f)

    def save_annotations(self):
        os.makedirs(LABELS_DIR, exist_ok=True)
        with open(ANNOTATION_FILE, "w") as f:
            json.dump(self.annotations, f, indent=2)
        self.export_yolo_format()
        self.status.config(text=f"Saved {len(self.annotations)} annotations")

    def export_yolo_format(self):
        for img_path, boxes in self.annotations.items():
            label_path = os.path.join(LABELS_DIR, os.path.splitext(os.path.basename(img_path))[0] + ".txt")
            img = Image.open(img_path)
            w, h = img.size
            lines = []
            for box in boxes:
                cls = box["class"]
                x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
                cx = ((x1 + x2) / 2) / w
                cy = ((y1 + y2) / 2) / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            with open(label_path, "w") as f:
                f.write("\n".join(lines))

    def set_class(self, k):
        self.current_class = k

    def show_image(self):
        if not self.images:
            return
        path = self.images[self.current_idx]
        img = Image.open(path)

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 10:
            canvas_w = 900
            canvas_h = 600

        self.scale = min(canvas_w / img.width, canvas_h / img.height)
        new_w = int(img.width * self.scale)
        new_h = int(img.height * self.scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        self.offset_x = (canvas_w - new_w) // 2
        self.offset_y = (canvas_h - new_h) // 2

        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.photo)

        # Draw existing annotations
        if path in self.annotations:
            for box in self.annotations[path]:
                self.draw_box(box, save=False)

        self.lbl_info.config(text=f"{self.current_idx + 1}/{len(self.images)} - {os.path.basename(path)}")
        self.status.config(text=f"Class: {CLASSES[self.current_class]} | Press 1-6 to change class, drag to draw box")

    def draw_box(self, box, save=True):
        x1 = box["x1"] * self.scale + self.offset_x
        y1 = box["y1"] * self.scale + self.offset_y
        x2 = box["x2"] * self.scale + self.offset_x
        y2 = box["y2"] * self.scale + self.offset_y
        color = ["", "#22c55e", "#f97316", "#eab308", "#3b82f6", "#a855f7", "#ec4899"][box["class"]]
        rect = self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
        label = self.canvas.create_text(x1, y1 - 10, text=CLASSES[box["class"]], fill=color, font=("Arial", 10, "bold"), anchor=tk.W)

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#ffffff", width=2, dash=(4, 2))

    def on_drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if not self.rect_id:
            return
        self.canvas.delete(self.rect_id)
        self.rect_id = None

        x1 = (min(self.start_x, event.x) - self.offset_x) / self.scale
        y1 = (min(self.start_y, event.y) - self.offset_y) / self.scale
        x2 = (max(self.start_x, event.x) - self.offset_x) / self.scale
        y2 = (max(self.start_y, event.y) - self.offset_y) / self.scale

        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            return

        path = self.images[self.current_idx]
        if path not in self.annotations:
            self.annotations[path] = []

        box = {"class": self.current_class, "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}
        self.annotations[path].append(box)
        self.draw_box(box, save=False)
        self.status.config(text=f"Added {CLASSES[self.current_class]} box | Press 's' to save")

    def on_right_click(self, event):
        path = self.images[self.current_idx]
        if path not in self.annotations:
            return
        # Find closest box and delete it
        img_x = (event.x - self.offset_x) / self.scale
        img_y = (event.y - self.offset_y) / self.scale
        min_dist = float("inf")
        min_idx = -1
        for i, box in enumerate(self.annotations[path]):
            cx = (box["x1"] + box["x2"]) / 2
            cy = (box["y1"] + box["y2"]) / 2
            dist = ((img_x - cx) ** 2 + (img_y - cy) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        if min_idx >= 0 and min_dist < 100:
            removed = self.annotations[path].pop(min_idx)
            self.show_image()
            self.status.config(text=f"Deleted {CLASSES[removed['class']]} box")

    def delete_last_box(self):
        path = self.images[self.current_idx]
        if path in self.annotations and self.annotations[path]:
            removed = self.annotations[path].pop()
            self.show_image()
            self.status.config(text=f"Deleted last {CLASSES[removed['class']]} box")

    def next_image(self):
        if self.current_idx < len(self.images) - 1:
            self.current_idx += 1
            self.show_image()

    def prev_image(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.show_image()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = LabelTool()
    app.run()
