# Forest Fire Detection — Edge-Cloud Architecture with YOLOv11

Real-time forest fire and smoke detection using a distributed edge-cloud architecture, deployed on UAVs. Companion project to the IEEE paper *"Edge-Cloud Architecture for Real-Time Forest Fire Detection Using YOLOv11 on UAV Imagery"*.

## Repository Structure

```
fire-detection-model/
├── article/              # IEEE paper (Markdown draft + LaTeX)
│   ├── paper.md          # Living draft — updated throughout the project
│   ├── paper.tex         # Final IEEE LaTeX version
│   └── figures/          # Plots and screenshots for the paper
├── model/                # YOLOv11 training and evaluation
│   ├── train.py
│   ├── evaluate.py
│   ├── export.py         # Export to ONNX/TensorRT for edge
│   ├── requirements.txt
│   └── configs/
│       └── fire-dataset.yaml
├── edge/                 # Simulated UAV edge inference node
│   ├── inference.py      # Runs YOLO, pushes events to Supabase
│   ├── buffer.py         # Offline event buffer for disconnected mode
│   └── requirements.txt
├── dashboard/
│   ├── frontend/         # Next.js dashboard (deployed on Vercel)
│   └── supabase/         # Database schema and migrations
└── presentation/         # Beamer LaTeX slides
    └── slides.tex
```

## Quickstart

### 1. Dataset

Download the **D-Fire** dataset from Kaggle:
```
https://www.kaggle.com/datasets/decorrespondent/d-fire
```
Extract to `model/data/d-fire/` and update `model/configs/fire-dataset.yaml` with the path.

### 2. Train the model

```bash
cd model
pip install -r requirements.txt
python train.py
```

Training produces weights in `runs/train/fire-yolo11n/weights/best.pt`.

### 3. Export for edge deployment

```bash
python export.py --weights runs/train/fire-yolo11n/weights/best.pt
```

### 4. Set up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Run `dashboard/supabase/schema.sql` in the SQL editor
3. Copy your project URL and anon key

### 5. Run the edge simulation

```bash
cd edge
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase credentials
python inference.py --source path/to/fire_video.mp4
```

### 6. Run the dashboard locally

```bash
cd dashboard/frontend
npm install
cp .env.example .env.local   # fill in Supabase credentials
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 7. Deploy to Vercel

```bash
cd dashboard/frontend
npx vercel --prod
```
Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` to Vercel environment variables.

## Live Demo

Dashboard: [https://fire-detection-model.vercel.app](https://fire-detection-model.vercel.app)

## Author

Alaaeddine Bouchamla  
M1 Telecommunications Engineering — ENISO, Sousse, Tunisia
