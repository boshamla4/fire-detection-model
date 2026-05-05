"""
Evaluate a trained YOLOv11 model on the D-Fire test set.
Outputs: mAP@0.5, mAP@0.5:0.95, Precision, Recall per class.
Run: python evaluate.py --weights runs/train/fire-yolo11n/weights/best.pt
"""

import argparse
import json
from pathlib import Path
from ultralytics import YOLO


def parse_args():
    p = argparse.ArgumentParser(description="Evaluate YOLOv11 fire detection model")
    p.add_argument("--weights", required=True, help="Path to model weights (.pt)")
    p.add_argument("--data", default="configs/fire-dataset.yaml", help="Dataset config")
    p.add_argument("--split", default="test", choices=["val", "test"])
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--device", default="0")
    p.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    p.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold")
    p.add_argument("--save-json", default="results.json", help="Save metrics to JSON")
    return p.parse_args()


def main():
    args = parse_args()

    model = YOLO(args.weights)

    metrics = model.val(
        data=args.data,
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        conf=args.conf,
        iou=args.iou,
        plots=True,
        save_json=True,
    )

    results = {
        "weights": args.weights,
        "split": args.split,
        "metrics": {
            "precision": float(metrics.box.mp),
            "recall": float(metrics.box.mr),
            "mAP50": float(metrics.box.map50),
            "mAP50_95": float(metrics.box.map),
            "per_class": {
                name: {
                    "precision": float(p),
                    "recall": float(r),
                    "mAP50": float(ap50),
                }
                for name, p, r, ap50 in zip(
                    metrics.names.values(),
                    metrics.box.p,
                    metrics.box.r,
                    metrics.box.ap50,
                )
            },
        },
    }

    print("\n── Evaluation Results ──────────────────────────────")
    print(f"  Precision : {results['metrics']['precision']:.4f}")
    print(f"  Recall    : {results['metrics']['recall']:.4f}")
    print(f"  mAP@0.5   : {results['metrics']['mAP50']:.4f}")
    print(f"  mAP@0.5:95: {results['metrics']['mAP50_95']:.4f}")
    print("\n  Per-class mAP@0.5:")
    for cls, m in results["metrics"]["per_class"].items():
        print(f"    {cls:10s}: {m['mAP50']:.4f}")
    print("────────────────────────────────────────────────────")

    out_path = Path(args.save_json)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nMetrics saved to {out_path}")


if __name__ == "__main__":
    main()
