# TerraFly Source-to-System Atlas

**Project:** TerraFly / SIH 2026 problem 26175  
**Verified build:** `TerraFly_FINAL_WINDOWS`  
**Audit date:** 2026-08-28  
**Purpose:** make a beginner able to operate, trace, defend and recreate the actual system.

> The evidence rule used throughout this atlas is: source location + observed/tested behavior + scientific limitation + safe judge wording.

## 1. The one-minute truth

TerraFly is a local terrain workbench with two deliberately separate workflows.

1. **DEM Terrain - recommended:** combine georeferenced optical imagery with a named metre-valued DEM. The DEM supplies geometry and elevations; the imagery supplies color. This is the strongest current mountain demonstration.
2. **Photo AI - experimental:** run the real Depth Anything V2 Large monocular model on one image. The first result is a relative 0-to-1 surface, never metres. A georeferenced input can become a metric DSM-like result only when an independent aligned reference DSM or separate GCP evidence passes the calibration gates.

This separation is the core scientific decision. A good-looking mesh is not automatically measured terrain. `[Code: backend/terrafly/schemas.py:9-13; backend/terrafly/main.py:49-204 | Tests: backend/tests/test_geotiff.py:32-86; backend/tests/test_calibration.py:68-241 | Limitation: metric truth depends on source DEM or independent vertical evidence | Judge: "TerraFly distinguishes supplied elevation, relative AI shape and calibrated metric output instead of presenting them as the same claim."]`

## 2. Exact SIH/ISRO problem identity

**Problem ID:** SIH26175  
**Organization:** Indian Space Research Organisation (ISRO)  
**Exact title:** **DepthWizard - Single-View Height Estimation and 3D Flythrough**

The public SIH listing describes this problem: DEM/DSM data is important for urban planning, disaster management and military applications; conventional stereo, LiDAR and InSAR can be costly, sensor-specific or computationally demanding. The requested system accepts optical RGB remote-sensing imagery, estimates elevation using a pretrained monocular backbone, produces relative outputs for ordinary images and absolute DSM GeoTIFFs when geospatial and vertical reference evidence is supplied, textures a 3D mesh, and supports interactive flythrough plus height/slope inspection. Evaluation is split between DSM accuracy across multiple landscapes and visualization/UX. The expected result is a unified, documented suite producing standard geospatial DSM outputs and accessible 3D exploration.

**Verification locators:** official SIH portal `https://sih.gov.in/sih2026PS#ViewProblemStatement26175`; public cross-check `https://sih-fit.vercel.app/problem/SIH26175`; secondary cross-check `https://sih-buddy.vercel.app/ps/SIH26175`. The official portal is authoritative; mirrors were used only to cross-check the publicly displayed text.

### 2.1 Users, pain, root cause and stakeholders

| Element | TerraFly interpretation |
|---|---|
| Primary users | GIS analysts, planners, disaster-research teams, remote-sensing students and technical evaluators who need an inspectable terrain result without building a bespoke ML/3D stack. |
| Pain | Imagery is visually rich but does not directly expose height; elevation products and viewers require GIS knowledge; monocular AI often produces attractive but uncalibrated shape. |
| Root cause | A single 2D projection loses absolute scale and offset. CRS adds horizontal location, not a vertical datum. Sensor/domain differences introduce spatially varying errors. |
| Stakeholders | ISRO/SIH evaluators, data providers, local authorities, researchers, emergency planners, defense analysts, software operators and people affected by decisions derived from terrain data. |
| Risk owner | The team owns software behavior and claim wording. The data provider owns source DEM accuracy. A deployment organization owns operational validation and policy. |

## 3. Existing approaches and the gap TerraFly addresses

| Existing approach | Strength | Gap for this project | TerraFly position |
|---|---|---|---|
| Global DEM products such as SRTM | Broad coverage, metric elevation and known provenance | Native resolution, datum and surface/terrain meaning may not match a local optical image; not a textured interactive product by itself | DEM Terrain aligns a named source, preserves values and records both grids. It never claims resampling creates detail. |
| Photogrammetry | Strong geometry from overlapping images and camera models | Needs multiple overlapping views, calibration and processing | TerraFly targets a single-view workflow but accepts lower certainty and requires external vertical evidence for metres. |
| LiDAR | High-quality direct range measurements and point clouds | Cost, coverage, acquisition and processing burden | TerraFly can visualize derived elevation but does not replace LiDAR accuracy. |
| InSAR/stereo satellite processing | Can recover elevation over large regions | Sensor/geometry expertise, coherent pairs or stereo acquisitions and expensive pipelines | TerraFly offers a simpler local front end around supplied DEM or a monocular baseline. |
| Google Earth/Bhuvan-style visualization | Excellent global exploration and polished 3D | It is a visualization/data service, not a reproducible user-owned inference pipeline; captured Google Earth output cannot be used to reconstruct 3D under the cited Geo Guidelines | TerraFly exposes source files, arrays, calibration reports and hashes. |
| Desktop GIS such as QGIS | Comprehensive raster inspection, reprojection and analysis | Learning curve and no built-in TerraFly AI/calibration/GLB workflow | TerraFly narrows the task to upload, evidence gate, 3D inspection and export; QGIS remains essential for preparing real data. |
| Monocular-depth models | One-image relative structure with pretrained checkpoints | Scale ambiguity, ordinary-camera domain bias, global tilt and no automatic vertical datum | Photo AI labels the result relative, records the model and exposes a separate evidence gate. |

### 3.1 What is innovative and what is reused

**Existing technology reused:** FastAPI, Pydantic, Pillow, Rasterio, NumPy, PyTorch, Transformers, Depth Anything V2, React, TypeScript, Three.js, glTF/GLB, pytest and Vitest. The model and formats are not claimed as inventions. `[Source: THIRD_PARTY_NOTICES.md:1-24; pyproject.toml; frontend/package.json | Evidence: production build and test suite | Limitation: upstream licenses and domain limits apply | Judge: "We integrated established open tools and a real pretrained baseline into an auditable local workflow."]`

**TerraFly engineering contribution:** the explicit scientific state machine; two honest workflows; raw/canonical/display separation; output-direction regression; bounded affine-aligned tiling; exact-grid independent calibration gates; locked metric artifacts; texture/normal-aware GLB; point measurements; per-job hashes and manifests; local release verification. These are integration and evidence-design contributions, not a new foundation model.

## 4. Feasibility and impact

### 4.1 Engineering feasibility

- **Demonstrated:** packaged backend 40/40 tests; frontend 10/10 tests; frontend production build; real CUDA inference; DEM Terrain smoke; calibration oracle; browser interaction; zero browser console errors during the audited flows.
- **Resource shape:** a configured 25 MB upload limit, 50 million pixel limit and 768 MiB processing estimate; tiling defaults of 1024 with 128 overlap and a 256-tile cap. `[Code: config.py:11-31; imaging.py:45-59; inference/tiling.py:8-99 | Tests: test_api.py:86-121; test_tiling.py:9-64 | Limitation: time and GPU memory still scale with scene size | Judge: "The runtime uses explicit size and tile bounds rather than accepting unbounded inputs."]`
- **Local deployment:** prebuilt frontend and API share a loopback address. The first setup and uncached checkpoint require internet and several gigabytes; after caching, scene data stays local. `[Code: main.py:233-239; scripts/start.ps1:1-115 | Evidence: live package at 127.0.0.1:8012 | Limitation: not a zero-install air-gapped archive | Judge: "It runs locally after one-time dependency and model setup."]`

### 4.2 Scientific feasibility

- **Proved:** deterministic preservation/alignment of a supplied metric DEM; explicit relative output; robust positive affine calibration; independent validation and fail-closed artifacts.
- **Not proved:** real Photo AI height accuracy across urban, sparse, hilly and forested data. A global affine fit cannot cure local model errors.
- **Best current scientific demo:** a real, licensed optical GeoTIFF and matching DEM, visibly attributed, in DEM Terrain.

### 4.3 Deployment feasibility

The current package is appropriate for a controlled judge laptop or lab workstation. It is not an operational cloud service: there is no authentication, multi-user scheduler, remote storage, monitoring service-level objective or completed production security review. Bind-to-loopback and path checks reduce local risk but do not establish enterprise readiness.

### 4.4 Demonstrated, potential and unproved impact

| Level | What may be said |
|---|---|
| Demonstrated | TerraFly turns a supplied optical+DEM pair into auditable textured metric terrain; runs a real monocular baseline; locks metric AI outputs until evidence passes; exports arrays, reports, GeoTIFF and GLB; supports interactive comparison. |
| Potential | Faster terrain briefing, education, preliminary visual inspection, source alignment checking and a foundation for future flood/slope/line-of-sight modules. |
| Not demonstrated | Disaster prediction, military readiness, survey-grade accuracy, operational reliability, real Himalayan accuracy, general urban building-height accuracy or commercial licensing suitability. |

## 5. Scientific states: evidence, not a visual switch

```text
PNG/JPG input ----------------------> Relative
                                       0..1, no CRS, no metres

GeoTIFF image ----------------------> Georeferenced Relative
                                       0..1 + horizontal CRS/transform
                                       still no vertical scale/datum

Georeferenced Relative + independent reference/GCP gate PASS
                                    -> Metric Calibrated
                                       AI-derived metres + datum evidence

Optical GeoTIFF + named metre DEM ---> Metric Source DEM
                                       metres inherited from source DEM
```

The schema encodes four labels because the two metric states have different evidence origins. `[Code: schemas.py:9-13 | Test: test_api.py:94-112; test_geotiff.py:32-86 | Limitation: a label cannot validate dishonest evidence | Judge: "Metric Source DEM means supplied elevation; Metric Calibrated means an AI surface transformed only after independent validation."]`

**Relative:** normalized float32 0-to-1 shape. No metres.  
**Georeferenced Relative:** same vertical ambiguity plus CRS, affine transform, bounds and horizontal pixel size.  
**Metric Source DEM:** the named DEM already supplies metre values and datum/source declaration.  
**Metric Calibrated:** an AI surface receives a positive affine scale/offset only after gates pass.

## 6. Workflow one: DEM Terrain

### 6.1 Step-by-step

1. **Optical GeoTIFF validation.** The upload is chunk-limited; safe names and extensions are checked; Rasterio inspects bands, shape, CRS, affine transform, bounds, masks and pixel count. `[Code: imaging.py:31-137; main.py:69-136 | Test: test_api.py:81-121; test_terrain.py:65-137 | Limitation: syntactic validity does not prove imagery quality | Judge: "We reject unsafe, corrupt, oversized or ungeoreferenced inputs before processing."]`
2. **DEM validation.** TerraFly requires one band, CRS, finite valid values, a recognized metre unit or an explicit metre source declaration, and enough valid pixels. `[Code: terrain.py:34-77 | Tests: test_terrain.py:139-176 | Limitation: values can still be inaccurate or use a wrong declared datum | Judge: "We validate the raster contract; the named provider remains the elevation authority."]`
3. **CRS/transform/overlap inspection.** Optical and DEM bounds are transformed into a common spatial comparison. Insufficient overlap fails before metric output. `[Code: terrain.py:84-145 | Test: test_terrain.py:139-155 | Limitation: overlap does not prove temporal or semantic match | Judge: "Both files must cover the same place; a filename match is not enough."]`
4. **Reprojection and resampling.** Rasterio reprojects the DEM onto the optical grid using bilinear resampling while preserving NoData. The alignment report records original/output grid and the method. `[Code: terrain.py:84-145 | Test: test_terrain.py:65-137 | Limitation: a 30 m DEM resampled to 10 m remains 30 m information | Judge: "Alignment changes the grid, not the source resolution or accuracy."]`
5. **Metric-array preservation.** The aligned metre array is saved as `aligned_source_dem.npy` and `metric_surface.npy`; invalid cells remain masked/NoData. `[Code: terrain.py:171-192,213-348 | Test: test_terrain.py:65-137 | Limitation: inherited source uncertainty is not estimated | Judge: "The scientific array remains in source metres; display processing is separate."]`
6. **Display normalization.** Valid metre values are robustly mapped for mesh height/color only. `[Code: terrain.py:148-168 | Test: test_terrain.py:65-137 | Limitation: visual exaggeration can mislead without the legend | Judge: "Normalization and exaggeration affect display, never the saved elevations."]`
7. **Mesh and texture.** A grid of height pixels becomes vertices and triangles; the optical image becomes a texture. UVs place image pixels on the mesh, normals support lighting and PBR material. `[Code: artifacts.py:83-296; terrain.py:213-348 | Test: test_artifacts.py:31-128 | Limitation: a height field has one height per x/y and cannot model overhangs | Judge: "Geometry comes from the DEM and color comes from the optical image."]`
8. **Measurement.** A/B clicks sample the metric analysis grid; projected metre CRS enables horizontal distance and slope. `[Code: surfaceGeometry.ts:122-200; SurfaceViewer.tsx:262-317; App.tsx:155-186 | Test: SurfaceViewer.test.ts:15-142 | Limitation: sampled/downsampled viewer values are inspection values, not survey certification | Judge: "The original metric arrays remain the scientific export; clicks support interactive comparison."]`
9. **Evidence exports.** The job contains the aligned source, metric arrays/GeoTIFF, alignment report, display grids, texture, GLB, diagnostics, source copies and SHA-256 manifest. `[Code: terrain.py:171-348; artifacts.py:18-33 | Test: test_terrain.py:65-137; terrain smoke PASS | Limitation: hashes prove byte identity, not correctness | Judge: "The bundle records exactly which input and derived bytes produced the scene."]`

### 6.2 The mountain answer

Mountains generally look better through DEM Terrain because geometry comes from measured/sourced elevation rather than image brightness. Snow, shadow and ridge contrast remain texture, not height evidence. The bundled mountain pair is synthetic and demonstrates software only. A judge-ready real scene must use licensed matching optical imagery and DEM with visible source, datum, bounds and attribution. `[Docs: docs/REAL_TERRAIN_DATA_GUIDE.md:5-51; docs/DEMO_SCRIPT.md:21-59 | Evidence: live screenshot 02 | Limitation: no real Himalayan pair is bundled | Judge: "This scene demonstrates the workflow; source accuracy belongs to the cited DEM."]`

## 7. Workflow two: Photo AI

### 7.1 Input to canonical relative surface

1. **Validation and preprocessing.** PNG/JPG/TIFF are decoded safely; a GeoTIFF retains spatial metadata; a single band is repeated into RGB with an out-of-domain warning; image modes are normalized to three channels. `[Code: imaging.py:140-175; pipeline.py:18-48 | Test: test_api.py:16-92 | Limitation: three identical thermal channels do not make an optical model scientifically valid | Judge: "Single-band execution proves software compatibility only."]`
2. **Model loading.** The normal adapter lazily loads `depth-anything/Depth-Anything-V2-Large-hf`, resolves the exact checkpoint revision and caches it. `[Code: depth_anything_v2.py:11-73; factory.py:9-23 | Evidence: verified revision 7581137... and CUDA | Limitation: CC-BY-NC-4.0 checkpoint and general-image training restrict use/claims | Judge: "Every job records the real model revision; it is a relative baseline, not our trained overhead model."]`
3. **CUDA and fallback.** The adapter selects CUDA when available, uses autocast, and catches CUDA out-of-memory to clear memory, move to CPU and retry. `[Code: depth_anything_v2.py:74-158 | Evidence: real CUDA smoke | Limitation: CPU fallback is slower and was not benchmarked for every input size | Judge: "The device and fallback warning are recorded in the job."]`
4. **Raw prediction.** The untouched model field is saved as `raw_model_output.npy`. `[Code: pipeline.py:44-76; artifacts.py:735-888 | Test: test_api.py:16-79 | Limitation: raw values have arbitrary scale/offset | Judge: "We retain the raw field so the conversion can be audited."]`
5. **Direction convention and historical repair.** Depth Anything V2 relative output behaves as inverse depth/proximity, where larger/nearer is mapped to higher surface in a near-nadir scene. The earlier extra inversion made roofs holes. The convention is now explicit and normalized once. `[Code: conventions.py:9-98 | Tests: test_adapter_contract.py:24-55; test_artifacts.py:130-166 | Limitation: near-nadir assumption and ordering test do not establish metric truth | Judge: "A synthetic raised-roof regression prevents the repaired direction bug from returning."]`
6. **Robust normalization.** Global 2nd and 98th percentiles limit outlier influence; the canonical float32 array becomes 0-to-1. `[Code: conventions.py:29-98 | Test: test_adapter_contract.py:47-55 | Limitation: relative contrast can vary by scene | Judge: "The canonical result is relative by design and is never labelled metres."]`

### 7.2 Large images and tiles

When the trigger is exceeded, TerraFly makes an overlapping bounded tile grid. Neighboring crops can have different arbitrary depth scale and offset, so each tile is aligned to accumulated overlap by a positive affine relation. Feather weights blend edges, and the complete raw field is normalized once. `[Code: depth_anything_v2.py:94-137; tiling.py:8-99 | Tests: test_tiling.py:9-64; script: smoke_tiled_model.py | Limitation: overlap agreement can propagate model bias and does not create absolute scale | Judge: "Tiling is a memory/detail engineering method, not an accuracy claim."]`

### 7.3 Canonical versus display artifacts

`relative_surface.npy` is immutable scientific input for later calibration. A copy becomes `display_grid.json` after isolated-spike suppression, RGB-guided smoothing, conservative roof flattening and an extreme-delta safety cap. `[Code: artifacts.py:299-519,735-888 | Test: test_artifacts.py:168-210 | Limitation: cleanup can make shapes look better without making them truer | Judge: "Display cleanup never changes canonical arrays or metric measurements."]`

The GLB embeds the real source texture, UVs, smooth normals, triangle indices and a lit PBR material. Steep faces use neutral shading because a top-down image contains no genuine facade pixels. `[Code: artifacts.py:83-296 | Test: test_artifacts.py:31-128 | Limitation: neutral walls are visual honesty, not recovered facade data | Judge: "We avoid stretching roof pixels down steep walls."]`

## 8. Metric calibration: how metres unlock

The model surface is converted by `elevation_m = scale * relative + offset`. TerraFly fits this robustly and requires `scale > 0`. Two evidence modes exist.

- **Reference DSM:** same CRS, width, height and affine transform as the Photo AI input. A spatial checkerboard is reserved before fitting.
- **GCP:** control points fit the transform; separate validation points evaluate it. The API supports this path; the current UI exposes the reference-raster path.

`[Code: calibration.py:54-118,348-532; main.py:157-204 | Tests: test_calibration.py:68-241 | Limitation: users can still supply non-independent or inaccurate evidence | Judge: "Controls determine scale and offset; held-out evidence decides whether metric files exist."]`

### 8.1 Exact gates

| Gate | Rule in code | Why | Rejection behavior |
|---|---|---|---|
| Positive scale | fitted scale must be greater than zero | Prevents a direction-flipped metric surface | report saved; metric files absent |
| Relative span | control relative span at least 0.05 | Avoids fitting metres to nearly flat/no-information predictions | same |
| Inlier ratio | at least 0.75 | Robust fit must explain most controls | same |
| Spatial coverage | at least 40% of both x and y axes | Prevents clustered controls from pretending to represent the scene | same |
| Held-out evidence | sufficient independent validation samples | Training error cannot approve itself | same |
| Held-out RMSE | at or below user-declared threshold | Connects pass/fail to a visible tolerance | same |
| R-squared | at least 0.50 | Requires the affine result to explain meaningful variation | same |

The gate logic is centralized in `calibration.py:136-163`; pass-only writing is in `calibration.py:276-345`. Poor evidence creates `calibration_report.json` and residual diagnostics but keeps `metric_surface.npy`/`.tif` locked. Tests cover pass, mismatch, rejection, GCP pass and NoData preservation at `test_calibration.py:68-241`.

### 8.2 Why the bundled near-zero RMSE is not accuracy

The bundled reference is deliberately generated from the model output using approximately `40 * relative + 100`, with training-only outliers. The verified run recovered scale about 40 and offset about 100 with held-out RMSE about 0.000002 m. That proves array orientation, split isolation, robust fitting, gate logic, metric file writing, hashes and UI state. It cannot prove performance on an independent landscape because the "truth" was constructed from the prediction. `[Evidence: sample_data/terrafly_calibration_demo_metadata.json; verified 18-artifact CUDA job | Limitation: synthetic oracle | Judge: "Near-zero error belongs to the software oracle and is excluded from our model metric card."]`

## 9. The 3D system from pixels to interaction

```text
height pixel (row, col)
  -> vertex (x, displayed height, z)
  -> two triangles per grid cell using index triples
  -> UV coordinate maps the optical texture
  -> neighboring triangles produce a smooth unit normal
  -> PBR material + movable directional light
  -> camera controls and raycaster
  -> point A/B sample analysis or metric grid
```

| Concept | TerraFly implementation | Limitation / judge wording |
|---|---|---|
| Height pixels | Relative, display or metric grids carry one value per raster cell. `surfaceGeometry.ts:202-255` | One height per x/y; no overhangs. |
| Vertices and indices | A regular grid is built into indexed triangles. `artifacts.py:112-296`; `surfaceGeometry.ts:202-255` | Mesh may be downsampled for responsiveness. |
| Normals | Neighbor gradients create unit normals for lighting. `artifacts.py:83-98` | Lighting reveals shape but is not evidence. |
| UV and texture | UV coordinates map embedded `texture.png` onto the surface. `artifacts.py:112-296` | Steep faces do not have source facade pixels. |
| PBR material | Lit material responds to movable sun. `artifacts.py:112-296`; `SurfaceViewer.tsx:112-260` | It is a visual material, not reflectance calibration. |
| Neutral steep faces | Strong slopes use neutral shading. `artifacts.py:112-296` | Avoids invented/stretched texture; it is not reconstructed wall color. |
| Orbit | left drag rotate, right drag pan, wheel zoom. `SurfaceViewer.tsx:112-220` | Inspection control only. |
| First-person | pointer-lock look, WASD, Q/E and Shift. `SurfaceViewer.tsx:318-344` | Free flight; no collision/gravity. |
| Photo/height colors | Separate material/color modes and numeric legend. `SurfaceViewer.tsx:45-110,389-440`; `surfaceGeometry.ts:32-64` | Height colors use relative or metric units exactly as labelled. |
| Wireframe and lighting | toggles expose topology and normals. `SurfaceViewer.tsx:45-220` | Visual QA, not quantitative accuracy. |
| Exaggeration | display-only vertex multiplier. `SurfaceViewer.tsx:45-110`; `surfaceGeometry.ts:202-255` | Never changes `.npy`/GeoTIFF. |
| A/B sampling | raycaster maps intersection UV to analysis grid; bilinear sample returns relative/metres. `SurfaceViewer.tsx:262-317`; `surfaceGeometry.ts:144-200` | Output inherits grid/source uncertainty. |
| Distance and slope | projected CRS transform supplies horizontal metres, then rise/run. `App.tsx:155-186`; `surfaceGeometry.ts:122-142` | Disabled if horizontal units are not metres. |
| Structures | convex extrusions from raised connected candidates. `artifacts.py:590-732`; `surfaceGeometry.ts:66-105` | Nonsemantic visual layer; can contain trees or miss roofs. |

## 10. Five exact request flows

### Flow A - Upload button to Photo AI result

1. `App.tsx:41-153,188-288` stores the selected file and starts submission.
2. `api.ts:3-34` constructs multipart `POST /api/jobs`.
3. `main.py:49-67` validates/saves input, creates a job and schedules the worker.
4. `pipeline.py:18-96` inspects/preprocesses, selects the adapter and runs inference.
5. `factory.py:9-23` chooses real or explicitly allowed test adapter; `depth_anything_v2.py:11-158` predicts.
6. `conventions.py:9-98` applies direction and canonical normalization.
7. `artifacts.py:735-888` writes numeric, preview, texture, diagnostics, structures and GLB outputs.
8. `jobs.py:28-63` updates `job.json` atomically; artifact hashes populate the manifest.
9. `App.tsx:80-153` polls `api.ts:36-46` until complete.
10. `App.tsx:290-480` passes artifact URLs to `SurfaceViewer.tsx:18-440`.
11. Evidence: `test_api.py:16-79`, `test_adapter_contract.py:24-55`, `App.test.tsx:10-190`, verified real CUDA live run.

**Failure prevented:** deterministic test inference cannot be silently enabled. **Limitation:** output remains relative until external evidence. **Judge:** "The browser result can be traced through one typed route, one worker and a hash-bound artifact set."

### Flow B - DEM upload to measured terrain

1. `App.tsx:188-288` selects DEM Terrain and collects optical, DEM, source and datum.
2. `api.ts:48-69` posts multipart data to `/api/terrain-jobs`.
3. `main.py:69-136` validates both inputs and creates the job.
4. `terrain.py:34-145` checks the DEM, overlap and alignment.
5. `terrain.py:148-192,213-348` preserves metric values, creates display data, GeoTIFF, report and mesh.
6. `jobs.py:28-63` persists progress and completion; `App.tsx:80-153` polls.
7. `SurfaceViewer.tsx:18-440` receives metric analysis grid and terrain mode.
8. Evidence: `test_terrain.py:65-176`, terrain smoke PASS, live screenshot 02.

**Failure prevented:** insufficient overlap and non-metre unit are rejected. **Limitation:** source DEM accuracy is not improved. **Judge:** "TerraFly makes a supplied elevation product inspectable and auditable; it does not call resampling super-resolution."

### Flow C - Calibration request to passed or rejected result

1. `App.tsx:360-406` shows the reference DSM form for a georeferenced relative job.
2. `api.ts:36-46` posts the reference and declared RMSE limit to `/api/jobs/{id}/calibrate/reference`.
3. `main.py:157-184` validates job state and dispatches calibration.
4. `calibration.py:348-461` requires exact grid/CRS/affine, builds a checkerboard holdout and robustly fits controls.
5. `calibration.py:136-163` evaluates every gate.
6. `calibration.py:276-345` always writes the report; only a pass writes metric files and changes state.
7. `App.tsx:80-153,408-480` reloads/polls and renders Passed or Rejected evidence.
8. Evidence: `test_calibration.py:68-241`, verified live screenshots 03-04.

**Failure prevented:** training error cannot approve the reference workflow. **Limitation:** a globally good affine score can hide class/local errors. **Judge:** "Rejection is a valid evidence result; the product does not create metric files to satisfy the demo."

### Flow D - Artifact link to downloaded file

1. `App.tsx:408-480` renders only artifacts present in the manifest.
2. `api.ts:71-73` builds `/api/jobs/{id}/artifacts/{name}`.
3. `main.py:206-219` validates job ID, resolves the artifact and checks containment/existence.
4. FastAPI returns the exact stored bytes; SHA-256 in the manifest enables verification.
5. Evidence: `test_api.py:16-79,123-131`; verified 18 artifact hashes.

**Failure prevented:** path traversal. **Limitation:** a matching hash proves identity, not scientific quality. **Judge:** "Downloads are bound to the selected job and each non-manifest artifact has a recorded digest."

### Flow E - Viewer click to measurement

1. `SurfaceViewer.tsx:262-317` raycasts the mouse into the visible mesh.
2. The intersection UV maps to raster coordinates.
3. `surfaceGeometry.ts:144-200` bilinearly samples metric or relative analysis data.
4. `SurfaceViewer.tsx` sends A/B points to `App.tsx`.
5. `App.tsx:155-186` calculates vertical difference and, for projected metre CRS, distance and slope.
6. Evidence: `SurfaceViewer.test.ts:15-142`; live A/B interaction.

**Failure prevented:** display exaggeration is not used as the numeric value. **Limitation:** the analysis grid can be downsampled. **Judge:** "The click samples the analysis data associated with the mesh, not screen height or lighting."

## 11. File-by-file atlas

Read each row as a compact call graph: **purpose; entry points; dependencies; input -> output; protected failure; evidence; beginner start.**

### 11.1 Launch and backend

| File | Atlas |
|---|---|
| `Start-TerraFly.cmd` | Double-click entry; calls `scripts/start.ps1`; no data input -> launcher process; prevents a user from memorizing commands; verified by packaged live launch; read all 6 lines. |
| `scripts/start.ps1` | Checks environment/port and starts Uvicorn; called by CMD; calls PowerShell process/network helpers; project path -> local server/log; avoids attaching to unrelated port owner; live launch; read endpoint and port functions first. |
| `backend/terrafly/config.py` | Central limits/model/runtime paths; imported by routes/workers; environment -> Settings; prevents scattered unsafe defaults; API limit tests; read `Settings`. |
| `schemas.py` | Pydantic vocabulary for states/jobs/artifacts/calibration; called across API/worker/UI JSON; validated data -> serialized contract; prevents undocumented shapes; capability/API tests; start with `ScientificState`. |
| `jobs.py` | Per-job directory and atomic state store; called by routes/workers; job ID and updates -> `job.json`; prevents path escape/partial writes; deletion security test; read `_job_dir` then `save`. |
| `imaging.py` | Safe upload and raster/image inspection; called by routes/workers; byte stream -> saved/decoded metadata; prevents oversized, corrupt and decompression-bomb input; API tests; read `save_upload`, `inspect_geotiff`, `load_normal_image`. |
| `main.py` | FastAPI composition and routes; called by Uvicorn; calls validators, workers and static files; HTTP -> jobs/files; prevents invalid state/path access; API tests; read `/health`, capabilities, then the five job/artifact routes. |
| `pipeline.py` | Photo AI orchestration; called by Photo route background task; calls imaging, adapter, conventions/artifacts/jobs; input image -> relative bundle; catches failure and records it; API and real smoke; read `run_pipeline` top to bottom. |
| `terrain.py` | DEM Terrain orchestration; called by terrain route; calls Rasterio alignment and artifact helpers; optical+DEM -> metric terrain bundle; prevents bad overlap/unit claims; terrain tests; read validation, alignment, then worker. |
| `calibration.py` | Robust affine fit, independent split/gates and pass-only metric export; called by calibration routes; relative+evidence -> report and optional metric bundle; prevents training-error metric claims; calibration tests; read `_gate`, reference and GCP functions. |
| `artifacts.py` | Hashes, grids, cleanup, GLB, diagnostics and artifact manifest entries; called by both workers/calibration; arrays+texture -> files; prevents canonical/display confusion and broken GLB contracts; artifact tests; read writer then follow helper calls. |
| `evaluation.py` | Masked real height metrics; called by benchmarking scripts; prediction+truth -> RMSE/MAE/bias/correlation; refuses mismatched/insufficient evidence; evaluation tests; read single evaluator. |

### 11.2 Inference

| File | Atlas |
|---|---|
| `inference/base.py` | Adapter interface and `Prediction`; factory/workers depend on it; image -> raw field/metadata; prevents incompatible adapters; adapter tests; read the dataclass and protocol. |
| `inference/factory.py` | Selects real vs test adapter; called by pipeline; settings -> adapter; prevents accidental test-only production use; contract test at line 57; read entire file. |
| `inference/depth_anything_v2.py` | Loads/predicts with DAV2 Large, CUDA/autocast, tiling and OOM CPU retry; called by factory; RGB -> raw prediction; prevents unrecorded fallback; real smoke; read load then predict. |
| `inference/conventions.py` | Declares inverse-depth/depth direction and robust global normalization; called after prediction; raw -> canonical relative; prevents roof-as-hole inversion; regression tests; read `to_relative_surface`. |
| `inference/tiling.py` | Plans bounded overlapping tiles, fits positive affine overlap and feathers; called by real adapter; large RGB -> blended raw field; prevents gaps/unbounded tiles/seams; tiling tests; read starts then blend loop. |
| `inference/deterministic.py` | Fast predictable offline test field; selected only behind safety flag; image -> deterministic raw result; prevents tests downloading GB model; adapter/API tests; never present it as production AI. |

### 11.3 Frontend

| File | Atlas |
|---|---|
| `frontend/src/main.tsx` | React bootstrap; Vite calls it; mounts `App`; HTML root -> UI; prevents scattered entry logic; build; read all 5 lines. |
| `types.ts` | TypeScript mirror of backend contract; imported by App/viewer/API; JSON -> typed objects; prevents field-name drift; build/tests; start with `JobManifest`. |
| `api.ts` | Fetch/multipart helpers; called by App; calls FastAPI routes; UI values -> requests/JSON; prevents duplicated URL/form logic; App tests; read create/get/calibrate/artifact helpers. |
| `App.tsx` | Workflow, uploads, polling, states, evidence, calibration and measurement display; calls API and viewer; user actions -> result workspace; prevents unavailable artifacts appearing active; App tests/live browser; read state, submit, polling, result sections. |
| `SurfaceViewer.tsx` | Three.js scene, controls, mesh loading, raycasting and UI toolbar; called by App; grid/texture URLs -> interactive canvas/A-B points; cleanup prevents WebGL leaks; viewer tests/live browser; read setup, raycast, first-person, cleanup. |
| `surfaceGeometry.ts` | Pure geometry/colors/measurement helpers; called by viewer; grids -> BufferGeometry and samples; prevents coordinate inversion and display-height measurements; viewer tests; start with `sampleMeasurementValue` then `createSurface`. |
| `styles.css` | Design tokens, layout and responsive breakpoints; loaded by main; class names -> visual hierarchy; prevents unusable narrow layout; build/live screenshots; start with variables and breakpoints near lines 215/226. |
| `App.test.tsx` | UI scientific contract tests; Vitest runs it; mocked API -> rendered states/actions; prevents labels/controls drifting; 10-test frontend total; read test names first. |
| `SurfaceViewer.test.ts` | Pure orientation, sampling, distance and structures tests; Vitest runs it; arrays -> expected geometry; prevents axis/height mistakes; read all cases. |

### 11.4 Backend tests and verification scripts

| File | What it owns |
|---|---|
| `tests/test_api.py` | End-to-end relative workflow, artifacts/hashes, invalid/oversized input, memory budget, capability contract, safe deletion and prebuilt UI. |
| `tests/test_geotiff.py` | CRS/transform preservation while vertical state remains locked. |
| `tests/test_terrain.py` | DEM success, alignment report/GLB, insufficient overlap and non-metre rejection. |
| `tests/test_calibration.py` | Reference pass, exact-grid rejection, poor-evidence lock, independent GCP pass and NoData. |
| `tests/test_artifacts.py` | Orientation, embedded texture/UV/normals/PBR, raised building and display cleanup immutability. |
| `tests/test_adapter_contract.py` | Determinism, direction, constant field and test-adapter interlock. |
| `tests/test_tiling.py` | Last-pixel coverage, asymmetric orientation, tile cap and affine overlap alignment. |
| `tests/test_evaluation.py` | Hand-calculated metrics, masks, insufficient evidence and geospatial matching. |
| `scripts/verify.ps1` | Orchestrates fast/full verification and records failure. |
| `smoke_terrain_workflow.py` | Runs the packaged DEM path and checks state, ranges and 15 artifacts. |
| `smoke_final_workflow.py` | Runs the complete synthetic calibration oracle and checks 18 hashes. |
| `smoke_real_api.py` / `smoke_real_model.py` | Prove the real adapter/checkpoint/device rather than the deterministic test adapter. |
| `smoke_tiled_model.py` | Proves the real large-image tiled path executes. |
| `benchmark_height_model.py` | Computes real metrics only on aligned reference truth and writes a metric card. |
| `compare_model_variants.py` | Compares checkpoint variants only on matched independent evidence. |
| `create_terrain_demo.py` / `create_calibration_demo.py` | Recreate synthetic fixtures with metadata; they are software demos, not acquired truth. |

## 12. Runtime artifact atlas

| Artifact | Contains / created by / consumed by | Never mistake it for |
|---|---|---|
| `raw_model_output.npy` | Untouched float model field; `pipeline.py` + `artifacts.py`; audit/calibration diagnostics | metres, probability or display-cleaned height |
| `relative_surface.npy` | Canonical float32 0-to-1 surface; `conventions.py`/`artifacts.py`; calibration and numeric download | absolute DSM |
| `relative_preview.png` | Colorized 8-bit human preview; artifact writer; UI comparison | numeric truth or training label |
| `texture.png` | Safe RGB source copy, embedded/capped for GLB; artifact writer; viewer/GLB | a height map |
| `relative_height_16bit.png` | 16-bit relative height encoding; artifact writer; external visualization | metres without scale/offset |
| `relative_grid.json` | Downsampled canonical numeric grid and metadata; artifact writer; viewer analysis | full-resolution array |
| `display_grid.json` | Downsampled display-cleaned surface; artifact writer; mesh | calibration/measurement truth |
| `reconstructed_structures.json` | Convex candidates for visual extrusions; artifact writer; viewer | verified building footprints/heights |
| `relative_surface.glb` | Portable indexed textured height mesh with normals/UV/material; artifact writer; external viewers | survey mesh or semantic city model |
| `height_diagnostics.json` | Plane-fit/global-tilt and cleanup reporting; artifact writer; evidence panel | an automatic correction or accuracy score |
| `job.json` | Mutable per-job state/progress/config/warnings/artifact list; job store; polling | immutable release manifest |
| `job_manifest.json` | Provenance snapshot, model/input metadata and hashes of other artifacts; artifact writer; audit UI | a self-hash or proof of accuracy |
| `aligned_source_dem.npy` | Source DEM resampled on optical grid, in metres/NoData; terrain worker; metric export/analysis | higher-resolution evidence than source DEM |
| `metric_surface.npy` | Full-resolution metre array from source DEM or passing calibration; terrain/calibration; scientific analysis | proof that upstream truth/model is accurate |
| `metric_analysis_grid.json` | Viewer-size metre sample grid; terrain/calibration; A/B clicks | full-resolution surface |
| `metric_surface.tif` | CRS/affine/NoData/metre-tagged GeoTIFF; terrain or pass-only calibration; GIS | automatically survey-grade DSM |
| `terrain_alignment_report.json` | Source/output CRS, transforms, resolution, overlap, resampling, source and datum; terrain worker; evidence UI | a quality certificate for source DEM |
| `calibration_reference.tif` | Exact evidence raster copied into the job; calibration worker; audit | independent truth unless provenance demonstrates it |
| `calibration_report.json` | fit, gates, held-out metrics, pass/rejection reasons; calibration worker; UI | model benchmark across unseen landscapes |
| `calibration_error.tif` | Candidate metric minus aligned reference residuals in metres; calibration worker; GIS diagnosis | absolute error where reference itself is wrong |
| `calibration_error_preview.png` | Colorized residual preview; calibration worker; UI | numeric residual array |

All non-manifest artifacts receive SHA-256 digests in the manifest. Hashes detect changed bytes; they do not validate units, provenance or scientific meaning. `[Code: artifacts.py:18-33,735-888 | Evidence: verified 18 hashes | Limitation: integrity is not accuracy | Judge: "Hashes support reproducibility, while calibration and source metadata support meaning."]`

## 13. Security, privacy, licensing and repeatability

- **Local bind:** start script serves loopback; scene data is not intentionally uploaded to a cloud service. First model/dependency retrieval uses the network.
- **Input safety:** bounded bytes, pixels and estimated memory; accepted content; corrupt/bomb checks; finite/NoData checks.
- **Path safety:** opaque validated job IDs, contained artifact resolution and safe deletion rules.
- **Privacy limit:** local operation is helpful for sensitive scenes, but Windows permissions, logs, caches and user practices still matter.
- **Model license:** current Large HF checkpoint is documented as CC-BY-NC-4.0; do not claim commercial readiness.
- **Data license:** every real scene must record provider, product, acquisition date, terms, attribution, CRS, datum, resolution and hashes.
- **Google Earth:** do not use screenshots/captured output to reconstruct a 3D model. Use only permitted, attributed visual comparison.
- **Repeatability:** record exact source/model revision, environment, inputs, settings, artifacts, hashes and test output.

## 14. Verification record for this atlas

| Check | Audited result |
|---|---|
| Packaged backend | 40 passed, 1 dependency warning, 3.87 s |
| Frontend | 2 files, 10 tests passed, 22.16 s |
| Production frontend build | passed; 23 modules; chunk-size advisory only |
| DEM Terrain smoke | PASS; 640x480; about 841.2 to 5962.5 m; 15 artifacts |
| Real Photo AI + calibration | PASS on CUDA; DAV2 Large revision `7581137eff8d4e94f6e796d3baea0e9fa79b22d2`; 18 hashes; synthetic oracle gate passed |
| Live browser | both workflows, calibration pass, downloads/viewer controls; no console errors |
| Source/release comparison | selected backend, frontend and prebuilt entry hashes matched the inspected source release |

This proves the documented software path on the audited computer. It does not establish model accuracy on independent real scenes.

## 15. Judge demonstration and wording

### 15.1 Recommended 6-minute sequence

1. Say the two-workflow truth in 25 seconds.
2. Run **DEM Terrain** with the bundled pair or, preferably, a rehearsed licensed real pair.
3. Show Photo vs Height colors, wireframe, movable light and A/B ridge/valley measurement.
4. Open the alignment report, metric GeoTIFF and manifest. State source/datum and native resolutions.
5. Switch briefly to **Photo AI** and point to `relative - not metres`, real model revision and limitation warning.
6. Show the synthetic calibration pass and immediately call it a software oracle.
7. Finish with the blocked real metric card and the staged DFC23 training/evaluation plan.

### 15.2 Never say

- "A Google Earth screenshot gives us true mountain geometry."
- "The AI knows the metres from one image."
- "Resampling increased DEM resolution."
- "The bundled RMSE proves accuracy."
- "Structures are detected buildings."
- "This predicts disasters" or "This is survey-grade."

### 15.3 Defensible closing

"TerraFly's current strength is not a magical screenshot-to-truth claim. It is a complete, local and inspectable pipeline that separates relative AI shape, georeferencing, supplied elevation and calibrated metres; records the evidence; refuses metric artifacts when validation fails; and already produces a strong measured-mountain experience from a named DEM."

## 16. Known inconsistencies and next decisions

See `docs/ownership/INCONSISTENCIES_AND_LIMITATIONS.md` and `docs/ownership/CLAIMS_LEDGER.md`. The most important are the missing independent real Photo AI benchmark, the one-time internet/setup requirement, the older architecture diagram omitting `Metric Source DEM`, the GCP API/UI mismatch and the difference between a downsampled viewer mesh and full-resolution scientific arrays.

## 17. Recreate TerraFly in the right order

1. Define the states and the rule that no ordinary image produces metres.
2. Implement safe input/raster inspection and a job store.
3. Implement the deterministic test adapter and relative artifact contract.
4. Add the real DAV2 adapter with raw preservation, direction regression and device metadata.
5. Add bounded tiling and tests.
6. Add textured GLB and viewer with separate photo/height/measurement grids.
7. Add DEM Terrain with explicit source/datum and alignment report.
8. Add calibration only with separated controls/validation and fail-closed artifacts.
9. Add release scripts, hashes, live browser checks and honest documentation.
10. Acquire independent evidence before publishing any real accuracy number.

The source-and-line map for every step is `docs/ownership/SOURCE_LINE_INDEX.md`.

