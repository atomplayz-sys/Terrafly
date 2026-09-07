# TerraFly inconsistencies and implementation limitations

No runtime code was changed during this documentation audit. These items should be discussed or repaired in a future engineering task.

| Priority | Finding | Evidence | Consequence / recommended follow-up |
|---|---|---|---|
| High | The current Photo AI system has no independent real-world accuracy result. | `docs/MODEL_METRIC_CARD.md:1-27`; `docs/MODEL_UPGRADE_EVALUATION.md`; evaluator in `evaluation.py:9-50` | Keep all accuracy claims blocked. Acquire licensed, aligned RGB-DSM/nDSM truth and run geographic held-out benchmarks. |
| High | The packaged release is not a zero-install offline bundle. | `docs/OPERATOR_GUIDE.md:16-28`; `scripts/setup.ps1`; no packaged `.venv`, `node_modules` or model weights | A new judging laptop needs internet and substantial setup. Prepare one already-tested machine and a documented backup video/results bundle. |
| High | The PS asks for absolute DSM from single optical input using SRTM/GCP scale recovery; the implementation offers either DEM-sourced geometry or global affine calibration. | `terrain.py:213-348`; `calibration.py:348-532`; `docs/PS_REQUIREMENTS_TRACEABILITY.md` | Do not describe DEM Terrain as AI recovery or affine calibration as local-error correction. A coarse-DEM fusion method remains future work. |
| Medium | `docs/ARCHITECTURE.md` presents a three-state chain but omits the separate `Metric Source DEM` state represented by the schema and UI. | `docs/ARCHITECTURE.md`; `schemas.py:9-13`; `App.tsx:188-288` | Use the ownership atlas state diagram as the authoritative explanation; update the older architecture page later. |
| Medium | The synthetic terrain generator records `units=metre` as a dataset tag, while live intake warns that no band-unit tag exists. | `scripts/create_terrain_demo.py`; verified live DEM UI; `terrain.py:34-77` reads band units | The numeric values are explicitly treated as metres by the source declaration, but fixture metadata and reader convention should be harmonized. |
| Medium | "Offline/local" language can be read too broadly. | `README.md`; `docs/OPERATOR_GUIDE.md:16-28`; `depth_anything_v2.py:11-158` | Say "local after one-time setup and model caching". Do not promise air-gapped installation from the source archive. |
| Medium | GCP calibration exists in the API but the current UI exposes only the reference-raster form. | `main.py:186-204`; `api.ts:3-73`; `App.tsx:360-406` | GCP is an API capability, not a judge-ready click path. Demonstrate reference DSM unless a separate API demo is rehearsed. |
| Medium | First-person navigation has no collision, gravity or terrain-following. | `SurfaceViewer.tsx:318-344` | Call it free-flight inspection, not a physically realistic drone simulation. |
| Medium | The display cleanup and Structures layer can look more regular than the canonical surface. | `artifacts.py:299-519,590-732`; `LIMITATIONS.md` | Repeat that cleanup is display-only and structures are nonsemantic. Measurements use analysis/metric grids, not structure extrusion. |
| Medium | Full-resolution scientific arrays and the downsampled viewer mesh have different roles. | `artifacts.py:735-888`; `SurfaceViewer.tsx:112-260`; `JUDGE_QA.md:63-65` | Do not call the interactive mesh full-resolution survey geometry. Exported arrays/GeoTIFF carry the numeric evidence. |
| Low | The job manifest cannot hash itself. | `artifacts.py:18-33,735-888`; verified artifact hash set | Explain that the manifest records all other artifacts; self-hashing would be recursive. |
| Low | Generated `__pycache__`, runtime jobs and the production bundle appear in the package inventory beside authored source. | packaged file tree | File-atlas readers can confuse generated files with source. Use `FILE_GUIDE.md` and the ownership source index. |
| Low | Historic reports contain earlier milestone test counts as well as final counts. | `handoff/DAY_*_TEST_REPORT.md`; `handoff/FINAL_TEST_REPORT.md`; `PROJECT_STATUS.md` | Quote only the date-stamped final verification: 40 backend tests and 10 frontend tests on 2026-08-28. |

## Non-negotiable scientific limitations

- A PNG/JPG cannot supply CRS, horizontal scale, vertical units or datum.
- A georeferenced GeoTIFF can still be vertically relative.
- A global positive affine transform cannot repair local nonlinear errors, misregistration or domain shift.
- SRTM/DEM accuracy and resolution remain those of the source provider; reprojection is alignment, not super-resolution.
- Snow, cloud, haze, shadow, forest canopy, water, oblique viewing and global perspective bias can distort Photo AI.
- Near-zero error from the bundled oracle is deliberately excluded from the model metric card.
- No current output proves Himalayan, city-wide, disaster, military, survey-grade or operational accuracy.

