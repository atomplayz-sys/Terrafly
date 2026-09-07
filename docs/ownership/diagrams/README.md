# Editable TerraFly diagrams

The `.mmd` files are the editable diagram sources. Matching `.png` files are rendered for the PDFs by `docs/ownership/tools/build_ownership_pack.py`. Update the Mermaid text and the corresponding diagram definition in that script together.

- `01_runtime_architecture.mmd` - browser, API, workers, evidence and viewer.
- `02_scientific_states.mmd` - evidence-dependent state transitions.
- `03_dem_terrain_flow.mmd` - supplied DEM workflow.
- `04_photo_ai_flow.mmd` - real model relative workflow.
- `05_calibration_gate.mmd` - pass/rejection logic.
- `06_pixels_to_mesh.mmd` - raster values to GLB/viewer/measurement.
- `07_request_flows.mmd` - five end-to-end request paths.

