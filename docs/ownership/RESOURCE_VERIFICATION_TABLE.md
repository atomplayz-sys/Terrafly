# TerraFly learning resource verification table

Checked 2026-08-28. Official/project-author sources are preferred. Approximate study time means the required subset, not the whole site. Detailed exercises and gate questions are in the bootcamp.

| ID | Exact title | Owner | URL | Required part | Time | Covers |
|---|---|---|---|---|---:|---|
| R01 | CS50's Introduction to Programming with Python | Harvard CS50 | https://cs50.harvard.edu/python/ | Weeks 0-6; focus functions, conditions, loops, exceptions, libraries, tests, file I/O | 8 h | Python, tests, files |
| R02 | The Python Tutorial | Python Software Foundation | https://docs.python.org/3/tutorial/ | Sections 3, 4, 6, 7, 8 and 12 | 3 h | Syntax, modules, I/O, errors, environments |
| R03 | NumPy: the absolute basics for beginners | NumPy | https://numpy.org/doc/stable/user/absolute_beginners.html | Arrays, shape, ndim, size, dtype, indexing, broadcasting | 2 h | Arrays, shapes, dtypes |
| R04 | Image Processing in OpenCV | OpenCV | https://docs.opencv.org/4.x/d2/d96/tutorial_py_table_of_contents_imgproc.html | Color conversion, geometric transforms, smoothing, gradients | 2 h | Image preprocessing and edges |
| R05 | But what is a neural network? Deep learning chapter 1 | 3Blue1Brown | https://www.youtube.com/watch?v=aircAruvnKk | Entire video | 19 min | Neural-network fundamentals |
| R06 | Learn the Basics | PyTorch | https://docs.pytorch.org/tutorials/beginner/basics/intro.html | Tensors, datasets, model, autograd, optimization, save/load | 4 h | Inference vs training, tensors |
| R07 | Automatic Mixed Precision | PyTorch | https://docs.pytorch.org/tutorials/recipes/recipes/amp_recipe.html | `autocast`, `GradScaler`, timing/memory | 45 min | CUDA memory and mixed precision |
| R08 | Monocular depth estimation | Hugging Face | https://huggingface.co/docs/transformers/tasks/monocular_depth_estimation | Task definition, inference pipeline, fine-tuning overview, evaluation | 1.5 h | Transformers and monocular depth |
| R09 | Depth Anything V2 | Depth Anything authors | https://depth-anything-v2.github.io/ | Abstract, method summary, relative versus metric models | 45 min | Current model context |
| R10 | Depth Anything V2 repository | Depth Anything authors | https://github.com/DepthAnything/Depth-Anything-V2 | README, usage, model table, license notes | 1 h | Checkpoints and limitations |
| R11 | Depth-Anything-V2-Large-hf model card | Hugging Face / authors | https://huggingface.co/depth-anything/Depth-Anything-V2-Large-hf | Model details, intended use, license | 30 min | Exact TerraFly checkpoint |
| R12 | Introduction to Satellite Remote Sensing for Air Quality Applications, Part 1 | NASA ARSET | https://www.youtube.com/watch?v=vGU4UqhHhAA | Sensors; spatial, spectral, radiometric and temporal resolution | 72 min | Remote sensing fundamentals |
| R13 | Introduction to Digital Elevation Models: 2025 Spring Webinar Series | OpenTopography | https://opentopography.org/node/3375 | DEM/DTM/DSM, interpolation, global and high-resolution sources | 75 min | Elevation models |
| R14 | A Gentle Introduction to GIS | QGIS Project | https://docs.qgis.org/3.44/en/docs/gentle_gis_introduction/index.html | Raster Data chapter and Coordinate Reference Systems chapter | 3 h | Raster, CRS, projected vs geographic |
| R15 | About the Browser | Copernicus Data Space Ecosystem | https://documentation.dataspace.copernicus.eu/Applications/Browser.html | Search, visualize, AOI and analytical image download | 1 h | Copernicus Browser |
| R16 | Sentinel-2 L2A | Copernicus Data Space Ecosystem | https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html | Band table; B02/B03/B04 are 10 m | 30 min | Optical satellite data |
| R17 | Sentinel-2 L2A examples | Copernicus Data Space Ecosystem | https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process/Examples/S2L2A.html | True color `[B04,B03,B02]` | 20 min | True-color composition |
| R18 | Shuttle Radar Topography Mission (SRTM) | NASA Earthdata | https://www.earthdata.nasa.gov/data/instruments/srtm | Mission, coverage, products and limitations | 45 min | Source DEM |
| R19 | Python Quickstart | Rasterio | https://rasterio.readthedocs.io/en/stable/quickstart.html | Open/read, metadata, bands, bounds, transform, CRS, write | 1.5 h | GeoTIFF and Rasterio |
| R20 | NOAA/NOS's VDatum: A tutorial on datums | NOAA | https://vdatum.noaa.gov/docs/datums.html | Horizontal vs vertical datum concepts | 1 h | Vertical datums |
| R21 | Tutorial - User Guide | FastAPI | https://fastapi.tiangolo.com/tutorial/ | First Steps, Request Body, Errors, Background Tasks, Static Files, Testing | 3 h | REST API and jobs |
| R22 | Request Files | FastAPI | https://fastapi.tiangolo.com/tutorial/request-files/ | `UploadFile`, multipart forms and limits | 45 min | File uploads |
| R23 | Models | Pydantic | https://docs.pydantic.dev/latest/concepts/models/ | Validated models, fields and serialization | 1 h | Job/manifest schema |
| R24 | Quick Start | React | https://react.dev/learn | Components, state, events, conditional rendering, lists | 2 h | TerraFly UI |
| R25 | TypeScript for the New Programmer | Microsoft TypeScript | https://www.typescriptlang.org/docs/handbook/typescript-from-scratch.html | JS-to-TS mental model and type checking | 1 h | Frontend types |
| R26 | Fundamentals | Three.js | https://threejs.org/manual/en/fundamentals.html | Scene, camera, renderer, mesh, geometry, material, light | 1.5 h | 3D viewer |
| R27 | Custom BufferGeometry | Three.js | https://threejs.org/manual/en/custom-buffergeometry.html | Positions, indices, normals and UV attributes | 1 h | Height-field mesh |
| R28 | glTF Tutorial | Khronos Group | https://github.khronos.org/glTF-Tutorials/gltfTutorial/ | Scenes/nodes, buffers, accessors, meshes, materials, textures | 2 h | GLB artifact |
| R29 | Linear Regression, Clearly Explained!!! | StatQuest | https://www.youtube.com/watch?v=7ArmBVF2dCs | 0:37-14:15 for fit/R-squared; 25:26 for F-distribution context | 28 min | Scale and offset calibration |
| R30 | R-squared, Clearly Explained!!! | StatQuest | https://www.youtube.com/watch?v=2AQKmw14mHM | Entire video | 11 min | R-squared gate |
| R31 | Cross-validation: evaluating estimator performance | scikit-learn | https://scikit-learn.org/stable/modules/cross_validation.html | Hold-out principle, validation vs test, CV | 1 h | Train/validation/test separation |
| R32 | Common pitfalls and recommended practices | scikit-learn | https://scikit-learn.org/stable/common_pitfalls.html | Inconsistent preprocessing, leakage, randomness | 1 h | Leakage and reproducibility |
| R33 | Metrics and scoring: quantifying the quality of predictions | scikit-learn | https://scikit-learn.org/stable/modules/model_evaluation.html | Regression metrics: MAE, RMSE, R2 | 1 h | Evaluation metrics |
| R34 | 2023 IEEE GRSS Data Fusion Contest | IEEE GRSS | https://www.grss-ieee.org/community/technical-committees/2023-ieee-grss-data-fusion-contest/ | Track 2, terms, data, citation | 1 h | Multi-city optical/SAR, masks and nDSM |
| R35 | Model Cards | Hugging Face | https://huggingface.co/docs/hub/model-cards | Metadata, intended uses, limitations, evaluation | 45 min | Model governance |
| R36 | Geo Guidelines | Google | https://about.google/brand-resource-center/products-and-services/geo-guidelines/ | Attribution and Google Earth restrictions | 30 min | Imagery use and attribution |
| R37 | About CC Licenses | Creative Commons | https://creativecommons.org/share-your-work/cclicenses/ | BY, SA, NC and ND conditions | 30 min | Data/media licensing |
| R38 | Get Started | pytest | https://docs.pytest.org/en/stable/getting-started.html | Discovery, assertions, exceptions and temporary paths | 1 h | Backend tests |
| R39 | Getting Started | Vitest | https://vitest.dev/guide/ | Writing tests and `vitest run` | 45 min | Frontend tests |
| R40 | Secure Hash Standard | NIST | https://www.nist.gov/publications/secure-hash-standard | Purpose of SHA digests and change detection | 30 min | SHA-256 evidence |

## Verification notes

- Links and titles were checked from the linked publisher/project pages or the video's public record on 2026-08-28.
- YouTube timelines can shift if a publisher replaces a video; recheck before a future semester.
- DFC23 access is conditional on its current terms. The table is a learning path, not permission to redistribute data.
- Google Earth may be used only within applicable guidelines; TerraFly must not use captured Earth output to reconstruct a 3D model.

