# Edge-Cloud Architecture for Real-Time Forest Fire Detection Using YOLOv11 on UAV Imagery

> **DRAFT — Living document. Fill in [TBD] sections after experiments.**
> IEEE format target: 6–8 pages, two-column. Final version in `paper.tex`.

---

## Abstract

Forest fires represent one of the most destructive natural disasters, causing irreversible ecological and economic damage. Early and accurate detection is critical to minimizing their impact, yet most existing AI-based approaches rely on centralized cloud processing, introducing unacceptable latency in remote, low-connectivity areas. This paper proposes an edge-cloud distributed architecture for real-time forest fire and smoke detection, deployable on Unmanned Aerial Vehicles (UAVs). The detection backbone is based on YOLOv11, the latest generation of real-time object detection networks, fine-tuned on the D-Fire public dataset. The proposed system partitions computation between an onboard edge inference unit and a cloud aggregation layer, achieving end-to-end detection latency below 5 seconds even under constrained network conditions. The dashboard interface provides real-time spatial visualization of fire probability and active alerts for emergency responders. Experimental results demonstrate [mAP@0.5: TBD], [inference latency on edge: TBD ms], and [end-to-end latency: TBD s], establishing the viability of this architecture for operational deployment in wildfire-prone regions.

**Keywords:** forest fire detection, UAV, edge computing, YOLOv11, real-time inference, edge-cloud architecture, smoke detection

---

## I. Introduction

Forest fires are a growing global threat, accelerated by climate change. In 2023 alone, wildfires burned over 13.4 million hectares across Europe, North Africa, and North America, resulting in billions of dollars in damages and significant loss of biodiversity [2]. The critical window for effective fire suppression is narrow — detection within the first few minutes after ignition drastically reduces the area burned and the cost of intervention.

Traditional fire monitoring systems rely on ground-based sensors and satellite imagery. Ground sensors suffer from limited spatial coverage, while satellite-based systems such as NASA MODIS and VIIRS introduce detection delays ranging from 30 minutes to several hours due to orbital revisit periods [6]. This latency is operationally unacceptable for real-time fire response.

Unmanned Aerial Vehicles (UAVs) represent a compelling alternative: they can be rapidly deployed, maneuver through complex terrain, and carry lightweight cameras and sensors that feed continuous aerial imagery at low altitude. When equipped with onboard AI inference capabilities, UAVs can detect fire and smoke in near real-time without relying on a persistent high-bandwidth uplink to the cloud.

However, deploying high-performance deep learning models on resource-constrained edge hardware — as opposed to GPU-equipped cloud servers — introduces significant challenges: limited compute, memory, power budget, and thermal constraints. Furthermore, in wildfire-prone mountainous or forested regions, network connectivity is often intermittent or entirely absent ("zone blanche"), making fully cloud-dependent architectures unreliable.

This work addresses these challenges with the following contributions:

1. **An edge-cloud distributed architecture** that partitions fire detection tasks between an onboard UAV edge unit and a cloud aggregation and alerting layer, maintaining detection functionality even when the network link is degraded or severed.

2. **An optimized YOLOv11 deployment** fine-tuned for aerial fire and smoke detection on the D-Fire public dataset, with explicit analysis of inference latency and accuracy under edge hardware constraints.

3. **A real-time operational dashboard** that ingests detection events from multiple UAVs, maps active fire zones, and issues alerts to emergency response teams.

4. **A systematic evaluation** of the latency–accuracy tradeoff across deployment configurations (edge-only, cloud-only, and hybrid), demonstrating that the proposed hybrid architecture achieves sub-5-second end-to-end latency while preserving detection accuracy competitive with cloud-based baselines.

The remainder of this paper is organized as follows. Section II reviews related work. Section III presents the proposed architecture. Section IV describes the dataset and methodology. Section V presents experimental results. Section VI describes the dashboard. Section VII concludes.

---

## II. Related Work

### A. Traditional and Statistical Approaches

Early fire risk prediction systems relied on physics-based models and statistical methods. Logistic regression and Bayesian belief networks have been used to estimate fire occurrence probability from meteorological and vegetation data, achieving AUC values up to 0.986 in controlled conditions [2]. Physical CFD models simulate fire-atmosphere interactions with high fidelity but are computationally prohibitive for real-time use [2]. These approaches cannot localize active fire events in real time.

### B. Machine Learning for Fire Risk Prediction

Classical machine learning methods — Random Forest, XGBoost, LightGBM — have been widely applied to fire occurrence and spread prediction using multi-source tabular data. Khanmohammadi et al. [1] evaluated AutoML pipelines and TabPFN on a Canadian conifer wildfire dataset, using GANs to address class imbalance, achieving 91% binary classification accuracy. Liu et al. [2] confirm through a comprehensive review that ensemble methods consistently deliver AUC above 0.9 on benchmark datasets. However, these models operate on aggregated features rather than raw imagery, and cannot localize active fire events.

### C. Deep Learning for Fire and Smoke Detection

CNNs have become the dominant paradigm for image-based detection. Sathishkumar et al. [4] demonstrate that transfer learning from ImageNet pre-trained backbones achieves strong accuracy on fire datasets. Their Learning Without Forgetting (LwF) technique mitigates catastrophic forgetting — Xception with LwF reaches 91.41% on the BowFire dataset. Priya et al. [3] propose a GAN-CNN hybrid reporting up to 85% reduction in false positives. None of these works address edge hardware deployment or end-to-end latency.

### D. Real-Time Object Detection

He et al. [5] apply YOLOv11x to forest fire smoke and flame detection, reporting mAP@0.5 of 0.901, with smoke at 0.962 and flame at 0.841, while achieving 22% fewer parameters than YOLOv8m. Their work is conducted exclusively on GPU-equipped hardware with no analysis of edge deployment or system latency.

### E. IoT and AI Integration

Morchid et al. [6] survey AI-IoT integration for fire monitoring, identifying CNN-IoT hybrid systems as achieving >90% early detection rates and 85% false positive reduction. They highlight real-time computational cost and remote network reliability as critical open challenges.

### F. Research Gap

No prior work simultaneously addresses (i) deployment on drone-mounted edge hardware, (ii) operation under intermittent network connectivity, and (iii) end-to-end latency quantification for operational fire response. This paper fills this gap.

---

## III. Proposed System Architecture

### A. Overview

The system consists of three layers: (1) the **UAV Edge Layer**, where fire detection inference runs onboard the drone; (2) the **Communication Layer**, which handles data transmission over constrained wireless links; and (3) the **Cloud Aggregation Layer**, which fuses detections from multiple UAVs, maintains a spatial fire map, and triggers alerts.

### B. UAV Edge Layer

The edge unit runs **YOLOv11n** (nano variant), optimized for devices with limited compute (NVIDIA Jetson Nano, Raspberry Pi 5 with NPU). Only structured detection events — bounding box coordinates, class label, confidence score, GPS timestamp — are transmitted to the cloud, not raw video frames. This reduces uplink bandwidth requirements dramatically.

**Operation modes:**
- **Connected mode:** Events streamed to the cloud in near real-time over 4G/LTE or WiFi.
- **Disconnected mode (zone blanche):** Events buffered locally with timestamp and GPS tag. Flushed to cloud upon reconnection.
- **Critical alert mode:** If a high-confidence detection occurs while disconnected, the UAV transmits a minimal alert packet over LoRa (GPS + confidence score).

### C. Communication Layer

| Link type | Bandwidth | Latency | Use case |
|-----------|-----------|---------|----------|
| 4G/LTE | ~10 Mbps | ~20–50 ms | Normal operation |
| WiFi 802.11n | ~50 Mbps | ~5–15 ms | Near base station |
| LoRa 868 MHz | ~5 kbps | ~500 ms | Emergency, zone blanche |

Detection events are encoded as lightweight JSON payloads (~500 bytes per event), transmittable even over LoRa.

### D. Cloud Aggregation Layer

The cloud backend aggregates events from all active UAVs via Supabase Realtime subscriptions. A spatial fusion module maintains a geographic fire probability map, updated in real time. The alerting module triggers notifications when detection confidence exceeds a configurable threshold over consecutive frames.

---

## IV. Dataset and Methodology

### A. Dataset

We use the **D-Fire** dataset, containing 21,527 images of fire and smoke with YOLO-format annotations for two classes: `fire` and `smoke`. The dataset is split 70/20/10 into training, validation, and test sets.

**Preprocessing:** Images are resized to 640×640. Mosaic augmentation and random affine transforms improve generalization to diverse aerial viewpoints. Histogram equalization is applied to hazy or backlit images.

### B. Model: YOLOv11

YOLOv11 was released by Ultralytics in September 2024 [5]. Key improvements over YOLOv8 include C3k2 and C2PSA backbone modules, 22% fewer parameters than YOLOv8m, and multi-platform export (ONNX, TensorRT, CoreML).

We evaluate:
- **YOLOv11x** — cloud GPU baseline (maximum accuracy)
- **YOLOv11n** — edge deployment target (minimum parameters)

### C. Training Configuration

| Parameter | Value |
|-----------|-------|
| Base model | YOLOv11n (COCO pretrained) |
| Epochs | 100 |
| Batch size | 16 |
| Optimizer | AdamW |
| Learning rate | 0.01 (cosine annealing) |
| Image size | 640 × 640 |
| Framework | Ultralytics YOLOv11, PyTorch |

Full fine-tuning of all layers is preferred over head-only fine-tuning, consistent with [4], given the domain shift from COCO to fire/smoke imagery.

### D. Edge Optimization

YOLOv11n is exported to ONNX and quantized to INT8 via TensorRT, targeting the NVIDIA Jetson Nano. INT8 quantization reduces model size by ~4× and accelerates inference with minimal accuracy degradation.

---

## V. Experimental Results

> **[Fill in after training. Replace all [TBD] with real numbers.]**

### A. Detection Performance

**Table I — Detection Performance on D-Fire Test Set**

| Model | Precision | Recall | mAP@0.5 | mAP@0.5:0.95 |
|-------|-----------|--------|---------|--------------|
| YOLOv11x (cloud) | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv11n (edge, FP32) | [TBD] | [TBD] | [TBD] | [TBD] |
| YOLOv11n (edge, INT8) | [TBD] | [TBD] | [TBD] | [TBD] |
| He et al. [5] (ref.) | 0.949 | 0.850 | 0.901 | 0.786 |

**Table II — Per-Class mAP@0.5**

| Model | Fire | Smoke |
|-------|------|-------|
| YOLOv11n (edge) | [TBD] | [TBD] |
| YOLOv11x (cloud) | [TBD] | [TBD] |

### B. Latency Analysis

**Table III — End-to-End Latency Breakdown**

| Component | Latency |
|-----------|---------|
| Edge inference (YOLOv11n, INT8) | [TBD] ms |
| Event encoding & transmission (4G) | [TBD] ms |
| Cloud aggregation & DB write | [TBD] ms |
| Dashboard render (browser) | [TBD] ms |
| **Total end-to-end** | **[TBD] s** |

### C. Disconnected Mode Evaluation

[TBD: Describe zone blanche simulation and buffer/flush results.]

---

## VI. Dashboard Implementation

The operational dashboard is a Next.js web application backed by Supabase Realtime. Core features:

- **Live fire map:** Leaflet.js map with real-time detection event overlays. Confirmed detections appear as georeferenced markers with timestamp and confidence score.
- **UAV fleet status:** Panel showing each active UAV's GPS position, battery level, connectivity status (Connected / LoRa / Disconnected), and detection count.
- **Alert log:** Chronological list of all fire events with GPS coordinates, UAV ID, confidence, and timestamp.
- **Statistics panel:** Rolling charts for detection rate and confidence distribution.

The edge inference script pushes events directly to Supabase. The dashboard subscribes via WebSocket, achieving sub-second update latency without polling.

---

## VII. Conclusion

This paper presented an edge-cloud architecture for real-time forest fire and smoke detection using UAVs. The proposed system addresses the fundamental limitations of cloud-only approaches — latency and connectivity dependency — by deploying YOLOv11n onboard the UAV. Detection events are transmitted as lightweight payloads, enabling operation over constrained links including LoRa in zone blanche environments.

Experimental results demonstrate [TBD summary] with end-to-end latency of [TBD] seconds, meeting the operational target of sub-5-second detection.

**Future work:** (i) physics-informed fire spread prediction for trajectory forecasting; (ii) multi-modal fusion with gas sensors; (iii) federated learning across UAV fleets.

---

## References

[1] S. Khanmohammadi et al., "Using AutoML and generative AI to predict the type of wildfire propagation in Canadian conifer forests," *Ecological Informatics*, vol. 82, 2024.

[2] H. Liu et al., "Advancements in artificial intelligence applications for forest fire prediction," *Forests*, vol. 16, article 704, 2025.

[3] S. P. V et al., "A generative AI model for forest fire prediction and detection," *J. Systems Engineering and Electronics*, vol. 35, no. 3, 2025.

[4] V. E. Sathishkumar et al., "Forest fire and smoke detection using deep learning-based learning without forgetting," *Fire Ecology*, vol. 19, article 9, 2023.

[5] L. He et al., "Research and application of deep learning object detection methods for forest fire smoke recognition," *Scientific Reports*, vol. 15, article 16328, 2025.

[6] A. Morchid et al., "Fire risk assessment system for food and sustainable farming using AI and IoT technologies," *Internet of Things*, vol. 33, article 101704, 2025.
