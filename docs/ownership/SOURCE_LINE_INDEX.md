# TerraFly source and line index

Verified against the packaged project on 2026-08-28. Line numbers refer to the editable source in `TerraFly_FINAL_WINDOWS`, not generated bundles or cached bytecode.

## Runtime and scientific contract

| Concern | Primary implementation | Verification evidence |
|---|---|---|
| Runtime limits and model configuration | `backend/terrafly/config.py:11-31` | `backend/tests/test_api.py:86-121`; live capabilities request |
| Scientific states and manifest schema | `backend/terrafly/schemas.py:9-83` | `backend/tests/test_api.py:94-112`; `backend/tests/test_geotiff.py:32-86` |
| Job IDs, atomic state and paths | `backend/terrafly/jobs.py:15-69` | `backend/tests/test_api.py:123-131` |
| Upload limits and image/GeoTIFF inspection | `backend/terrafly/imaging.py:15-175` | `backend/tests/test_api.py:16-92`; `backend/tests/test_geotiff.py:32-86` |
| API routes and static application | `backend/terrafly/main.py:20-239` | `backend/tests/test_api.py:16-143`; live browser run |
| Photo AI worker | `backend/terrafly/pipeline.py:13-96` | `backend/tests/test_api.py:16-79`; real CUDA smoke run |
| DEM Terrain worker | `backend/terrafly/terrain.py:34-348` | `backend/tests/test_terrain.py:65-176`; terrain smoke run |
| Calibration worker and gates | `backend/terrafly/calibration.py:18-532` | `backend/tests/test_calibration.py:68-241`; real calibration smoke run |
| Metric evaluation | `backend/terrafly/evaluation.py:9-50` | `backend/tests/test_evaluation.py:10-54` |

## AI inference

| Concern | Primary implementation | Verification evidence |
|---|---|---|
| Adapter result contract | `backend/terrafly/inference/base.py:9-19` | `backend/tests/test_adapter_contract.py:12-65` |
| Direction and one-time normalization | `backend/terrafly/inference/conventions.py:9-98` | `backend/tests/test_adapter_contract.py:24-55`; `backend/tests/test_artifacts.py:130-166` |
| Real DAV2 Large adapter, CUDA and CPU fallback | `backend/terrafly/inference/depth_anything_v2.py:11-158` | `scripts/smoke_real_model.py`; `scripts/smoke_real_api.py`; verified CUDA run |
| Adapter selection and test-only lock | `backend/terrafly/inference/factory.py:9-23` | `backend/tests/test_adapter_contract.py:57-65` |
| Deterministic test adapter | `backend/terrafly/inference/deterministic.py:9-41` | `backend/tests/test_adapter_contract.py:12-22` |
| Bounded tiling, overlap alignment and blending | `backend/terrafly/inference/tiling.py:8-99` | `backend/tests/test_tiling.py:9-64`; `scripts/smoke_tiled_model.py` |

## Artifacts and 3D

| Concern | Primary implementation | Verification evidence |
|---|---|---|
| Hashing and color map | `backend/terrafly/artifacts.py:18-45` | `backend/tests/test_api.py:16-79`; smoke hash verification |
| Train/evaluation spatial split helper | `backend/terrafly/artifacts.py:56-80` | `backend/tests/test_calibration.py:68-140` |
| Vertex normals | `backend/terrafly/artifacts.py:83-98` | `backend/tests/test_artifacts.py:31-128` |
| Textured GLB writer | `backend/terrafly/artifacts.py:101-296` | `backend/tests/test_artifacts.py:31-166` |
| Display-only cleanup | `backend/terrafly/artifacts.py:299-519` | `backend/tests/test_artifacts.py:168-210` |
| Tilt diagnostics | `backend/terrafly/artifacts.py:522-560` | `height_diagnostics.json` in verified real-model job |
| Optional nonsemantic structures | `backend/terrafly/artifacts.py:590-732` | `reconstructed_structures.json`; frontend geometry tests |
| Artifact bundle writer | `backend/terrafly/artifacts.py:735-888` | manifest and 18 verified artifact hashes |

## Frontend

| Concern | Primary implementation | Verification evidence |
|---|---|---|
| API helpers and multipart forms | `frontend/src/api.ts:3-73` | `frontend/src/App.test.tsx:10-190` |
| Shared API types | `frontend/src/types.ts:1-54` | TypeScript build and Vitest |
| Workflow selection, upload, polling and evidence UI | `frontend/src/App.tsx:41-501` | `frontend/src/App.test.tsx:10-190`; live browser run |
| 3D scene, controls, raycasting and cleanup | `frontend/src/SurfaceViewer.tsx:18-440` | `frontend/src/SurfaceViewer.test.ts:15-142`; live browser run |
| Mesh, colors, structures and measurements | `frontend/src/surfaceGeometry.ts:3-255` | `frontend/src/SurfaceViewer.test.ts:15-142` |
| Responsive visual system | `frontend/src/styles.css:1-239` | production build; live screenshots at desktop viewport |
| React entry point | `frontend/src/main.tsx:1-5` | production build |

## Launch, verification and demonstration

| File | Main responsibility | Evidence |
|---|---|---|
| `Start-TerraFly.cmd:1-6` | Windows double-click entry point | live packaged launch |
| `scripts/start.ps1:1-115` | Environment checks, port ownership, local server and browser | live packaged launch at `127.0.0.1` |
| `scripts/setup.ps1:1-140` | One-time Python, frontend and model setup | operator guide documents network requirement |
| `scripts/verify.ps1:1-110` | Fast/full release verification | fast and full smoke scripts |
| `scripts/smoke_terrain_workflow.py:1-154` | End-to-end DEM Terrain evidence | verified PASS, 15 artifacts |
| `scripts/smoke_final_workflow.py:1-205` | Synthetic calibration oracle | verified PASS, 18 hashes |
| `scripts/smoke_real_api.py:1-166` | Real model API and artifact check | verified CUDA run |
| `scripts/smoke_real_model.py:1-86` | Direct real adapter check | model revision/device evidence |
| `scripts/smoke_tiled_model.py:1-129` | Real tiled inference | tiling smoke contract |
| `scripts/benchmark_height_model.py:1-211` | Independent reference evaluation | `docs/MODEL_METRIC_CARD.md:1-27` remains BLOCKED |
| `scripts/compare_model_variants.py:1-185` | Checkpoint comparison on matched truth | no accuracy claim without data |
| `scripts/create_terrain_demo.py:1-155` | Reproducible synthetic terrain fixture | `sample_data/terrafly_terrain_demo_metadata.json` |
| `scripts/create_calibration_demo.py:1-172` | Reproducible software oracle fixture | `sample_data/terrafly_calibration_demo_metadata.json` |

## Reading order for a complete beginner

1. `README.md:3-101` and `docs/OPERATOR_GUIDE.md:1-175`.
2. `backend/terrafly/schemas.py:9-83` to learn the states and job vocabulary.
3. `frontend/src/api.ts:3-73`, then `backend/terrafly/main.py:20-239` to see the browser-to-server contract.
4. `backend/terrafly/terrain.py:34-348` and `backend/terrafly/pipeline.py:18-96` as the two workers.
5. `backend/terrafly/calibration.py:136-163,276-532` for the evidence gate.
6. `backend/terrafly/artifacts.py:101-296,735-888` and `frontend/src/SurfaceViewer.tsx:112-440` for 3D and outputs.
7. Read the matching test beside every subsystem before changing it.

