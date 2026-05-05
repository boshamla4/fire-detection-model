"""
YOLOv11 training script for forest fire and smoke detection.
Dataset: D-Fire (https://github.com/gaiasd/DFireDataset)
"""

import argparse
from pathlib import Path
from ultralytics import YOLO


def parse_args():
    p = argparse.ArgumentParser(description="Train YOLOv11 for fire detection")
    p.add_argument("--model", default="yolo11n.pt", help="Base model weights (yolo11n.pt / yolo11x.pt)")
    p.add_argument("--data", default="configs/fire-dataset.yaml", help="Dataset config path")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="0", help="CUDA device (0) or 'cpu'")
    p.add_argument("--name", default="fire-yolo11n", help="Run name under runs/train/")
    p.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    return p.parse_args()


def main():
    args = parse_args()

    model = YOLO(args.model)

    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        name=args.name,
        resume=args.resume,
        # Augmentation
        mosaic=1.0,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        # Optimizer
        optimizer="AdamW",
        lr0=0.01,
        lrf=0.01,
        cos_lr=True,
        warmup_epochs=3,
        # Logging
        plots=True,
        save=True,
        save_period=10,
        val=True,
    )

    print(f"\nTraining complete. Best weights: {results.save_dir}/weights/best.pt")
    print(f"Results saved to: {results.save_dir}")


if __name__ == "__main__":
    main()
