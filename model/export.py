"""
Export a trained YOLOv11 model to ONNX and TensorRT (INT8) for edge deployment.
Run: python export.py --weights runs/train/fire-yolo11n/weights/best.pt
"""

import argparse
import time
from pathlib import Path
from ultralytics import YOLO


def parse_args():
    p = argparse.ArgumentParser(description="Export YOLOv11 for edge deployment")
    p.add_argument("--weights", required=True, help="Trained weights (.pt)")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--format", default="all", choices=["onnx", "engine", "all"],
                   help="Export format: onnx (CPU edge), engine (TensorRT/Jetson), all")
    p.add_argument("--int8", action="store_true", default=True,
                   help="INT8 quantization for TensorRT (reduces size ~4x)")
    p.add_argument("--device", default="0")
    return p.parse_args()


def benchmark_onnx(weights_path: str, imgsz: int):
    """Measure ONNX inference latency (CPU)."""
    import numpy as np
    import onnxruntime as ort

    session = ort.InferenceSession(weights_path, providers=["CPUExecutionProvider"])
    dummy = np.random.randn(1, 3, imgsz, imgsz).astype(np.float32)
    input_name = session.get_inputs()[0].name

    # Warm-up
    for _ in range(5):
        session.run(None, {input_name: dummy})

    times = []
    for _ in range(50):
        t0 = time.perf_counter()
        session.run(None, {input_name: dummy})
        times.append((time.perf_counter() - t0) * 1000)

    avg_ms = sum(times) / len(times)
    print(f"  ONNX CPU inference: {avg_ms:.1f} ms avg over 50 runs")
    return avg_ms


def main():
    args = parse_args()
    weights = Path(args.weights)
    assert weights.exists(), f"Weights not found: {weights}"

    model = YOLO(str(weights))

    if args.format in ("onnx", "all"):
        print("\nExporting to ONNX...")
        onnx_path = model.export(format="onnx", imgsz=args.imgsz, simplify=True)
        print(f"  ONNX model saved: {onnx_path}")
        print("  Benchmarking ONNX on CPU...")
        benchmark_onnx(str(onnx_path), args.imgsz)

    if args.format in ("engine", "all"):
        print("\nExporting to TensorRT (INT8 quantization)...")
        print("  NOTE: Requires NVIDIA GPU + TensorRT installed (Jetson or desktop)")
        engine_path = model.export(
            format="engine",
            imgsz=args.imgsz,
            int8=args.int8,
            device=args.device,
        )
        print(f"  TensorRT engine saved: {engine_path}")

    print("\nExport complete. Deploy the ONNX model on CPU-based edge devices,")
    print("or the TensorRT engine on Jetson Nano / devices with NVIDIA GPU.")


if __name__ == "__main__":
    main()
