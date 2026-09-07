# 🪄 Depth Wizard: Single View Height Estimation & 3D Flythrough

> **Smart India Hackathon (SIH 2026)**  
> *Transforming single 2D optical images into truthful metric height estimations, interactive 3D terrain meshes, and cinematic flythroughs in seconds.*

---

## 🚀 Quick Start (1-Click Local Launch)

### On Windows
1. Double-click **`Start-TerraFly.cmd`** in this folder.
2. Your default web browser will automatically open at `http://127.0.0.1:8000`.
3. To run automated diagnostic & verification tests, double-click **`Check-TerraFly.cmd`**.

### Standard Git Clone / Cross-Platform Setup (Linux / macOS / Windows)
```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/DepthWizard_TerraFly_SIH2026.git
cd DepthWizard_TerraFly_SIH2026

# 2. Create virtual environment
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On Linux/macOS: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
python -m uvicorn terrafly.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
*(The pre-built WebGL 3D frontend in `frontend/dist` is served automatically — no Node.js installation needed!)*

---

## 📁 Project Structure

```text
DepthWizard_TerraFly_SIH2026/
├── Start-TerraFly.cmd                 # 🚀 1-Click launcher (starts backend + frontend UI)
├── Check-TerraFly.cmd                 # 🧪 1-Click automated verification suite
├── requirements.txt                  # 🐍 Python dependencies
├── pyproject.toml                     # 📦 Package configuration
├── LICENSE                            # ⚖️ MIT Open Source License
├── README.md                          # 📖 Comprehensive project guide
│
├── Presentation_and_Pitch/            # 🎯 SIH 2026 Slide deck, Playbooks, and Defense Scripts
│   ├── TerraFly_SIH2026_Pitch_Script.pdf   # 📄 Complete Judge Pitch Script (6 structured sections)
│   ├── TerraFly_SIH_Editable_V2_Official_Logo.pptx # 📊 Official Presentation Slides
│   ├── TerraFly_SIH_Winning_and_Presentation_Playbook.pdf
│   ├── TEAM_TEACHING_GUIDE.pdf
│   ├── TERRAFLY_TERMS_COMPLETE_GUIDE.pdf
│   ├── TerraFly_Source_to_System_Atlas.pdf
│   └── TerraFly_Zero_to_Ownership_Bootcamp.pdf
│
├── sample_data/                       # 🏔️ Bundled satellite imagery & DEM data for instant demo
│   ├── terrafly_terrain_demo_imagery.tif    # Georeferenced Optical Sentinel-style image
│   ├── terrafly_terrain_demo_dem.tif        # Georeferenced Metric Elevation DEM (SRTM)
│   └── terrafly_calibration_demo_input.tif  # Metric calibration demo pair
│
├── backend/                           # 🧠 Ponytail-optimized FastAPI & Scientific Core
│   └── terrafly/
│       ├── artifacts.py               # 3D GLB export, normals, PBR material packaging
│       ├── calibration.py             # Robust affine fitting & held-out validation gates
│       ├── terrain.py                 # Optical + DEM alignment and reprojection
│       ├── imaging.py                 # Multi-format image ingestion (GeoTIFF/PNG/JPG)
│       ├── main.py                    # REST API endpoints & static app mount
│       └── inference/                 # Depth Anything V2 monocular depth & spatial tiling
│
├── frontend/                          # 🌐 WebGL / Three.js 3D Flythrough Dashboard
│   ├── dist/                          # Pre-compiled high-performance production build
│   └── src/                           # React, TypeScript, Three.js 3D Viewer & Drone Flight
│
├── docs/                              # 📚 Scientific documentation, QA, and Architecture
│   ├── JUDGE_QA.md                    # 🗣️ Defense answers to deep technical questions
│   ├── DEMO_SCRIPT.md                 # ⏱️ 2-Minute live demo walkthrough
│   ├── ARCHITECTURE.md                # 📐 System architecture & data flow diagrams
│   └── OPERATOR_GUIDE.md              # 🎮 Complete 3D flight & measurement controls
│
└── scripts/                           # ⚙️ Verification and setup automation
    ├── setup.ps1                      # Environment installer
    ├── start.ps1                      # Server launcher script
    ├── verify.ps1                     # Full test and workflow verification
    └── smoke_terrain_workflow.py      # Headless terrain pipeline smoke test
```

---

## 🎯 2-Minute Judge Live Demo Sequence

1. **Launch App:** Double-click `Start-TerraFly.cmd` (opens `http://127.0.0.1:8000`).
2. **DEM Terrain Flow (Mountain 3D Flythrough):**
   - Click **DEM Terrain** tab.
   - Select `sample_data/terrafly_terrain_demo_imagery.tif` and `sample_data/terrafly_terrain_demo_dem.tif`.
   - Click **Create Terrain Mesh**.
   - Show the textured 3D mountain landscape.
   - Switch to **First-person Mode**: Click scene and use `W/A/S/D` + mouse look for dynamic 3D drone flight!
3. **Photo AI Flow (Single View Depth Estimation):**
   - Click **Photo AI** tab.
   - Upload any optical image or aerial drone photo.
   - Observe Depth Anything V2 generating continuous relative surface depth in seconds.
   - Open **Metric Calibration**, select ground truth points/DSM, and execute validation gates ($R^2$, RMSE) to unlock real-world heights.
4. **Point-to-Point Inspection & Export:**
   - Click Ground Point A and Elevated Point B to read metric difference and slope.
   - Download the full evidence bundle: `.glb` 3D model, `.tif` GeoTIFF, and provenance reports.

---

## 🛡️ Scientific Integrity & Architecture Highlights
- **No False Claims:** Recognizes that single 2D optical images yield relative inverse-depth structure, unlocking true metric elevation *only* when ground truth validation gates pass.
- **Robust Tiling:** Sliding-window inference with feather-edge blending enables processing gigapixel satellite scenes without GPU memory overflow.
- **PBR 3D Graphics:** Three.js textured mesh with smooth central-difference normals, shadow simulation, and synthetic neutral walls on steep cliffs to prevent aerial pixel stretching.
- **Edge & Offline Ready:** Runs 100% offline on standard consumer hardware without requiring internet connectivity or external cloud GPUs.

---

## ⚖️ License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
