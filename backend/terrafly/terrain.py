from __future__ import annotations

import hashlib
import json
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.fill import fillnodata
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject

from .artifacts import _artifact, sha256_file, write_surface_artifacts
from .calibration import _write_metric_grid
from .config import Settings
from .imaging import inspect_image
from .jobs import JobStore
from .schemas import Artifact, JobManifest, JobStatus, ScientificState


class TerrainInputError(ValueError):
    """The supplied image/DEM pair cannot form an honest terrain product."""


@dataclass(slots=True)
class DemInspection:
    metadata: dict[str, Any]
    geospatial: dict[str, Any]


def inspect_source_dem(data: bytes, filename: str, max_pixels: int) -> DemInspection:
    if Path(filename).suffix.lower() not in {".tif", ".tiff"}:
        raise TerrainInputError("Terrain mode requires a single-band DEM GeoTIFF.")
    try:
        with MemoryFile(data) as mem, mem.open() as ds:
            if ds.count != 1:
                raise TerrainInputError("The source DEM must contain exactly one raster band.")
            if ds.crs is None:
                raise TerrainInputError("The source DEM needs a CRS so it can be aligned to the optical image.")
            if ds.width < 2 or ds.height < 2:
                raise TerrainInputError("The source DEM must be at least 2×2 pixels.")
            if ds.width * ds.height > max_pixels:
                raise TerrainInputError(f"The source DEM exceeds the {max_pixels}-pixel safety limit.")
            vals = ds.read(1, masked=True).filled(np.nan).astype(np.float64)
            valid = vals[np.isfinite(vals)]
            if valid.size < 16:
                raise TerrainInputError("The source DEM needs at least 16 finite elevation samples.")
            tf = ds.transform
            return DemInspection(
                metadata={
                    "filename": filename, "width": ds.width, "height": ds.height, "dtype": ds.dtypes[0],
                    "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                    "valid_fraction": float(valid.size / vals.size),
                    "minimum_m": float(valid.min()), "maximum_m": float(valid.max()),
                    "reported_vertical_units": ds.units[0] or None,
                },
                geospatial={
                    "crs": ds.crs.to_string(), "transform": [tf.a, tf.b, tf.c, tf.d, tf.e, tf.f],
                    "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
                    "pixel_size": [abs(tf.a), abs(tf.e)],
                    "horizontal_units": ds.crs.linear_units if ds.crs.is_projected else "degree",
                    "nodata": ds.nodata,
                },
            )
    except TerrainInputError:
        raise
    except Exception as exc:
        raise TerrainInputError(f"Unreadable source DEM GeoTIFF: {exc}") from exc


def _align_dem(imagery_path: Path, dem_path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    with rasterio.open(imagery_path) as img, rasterio.open(dem_path) as dem:
        if img.crs is None or dem.crs is None:
            raise TerrainInputError("Both terrain inputs need a CRS.")
        src = dem.read(1, masked=True).filled(np.nan).astype(np.float32)
        aligned = np.full((img.height, img.width), np.nan, dtype=np.float32)
        exact_grid = (
            img.crs == dem.crs and img.width == dem.width and img.height == dem.height
            and np.allclose([img.transform.a, img.transform.b, img.transform.c, img.transform.d, img.transform.e, img.transform.f],
                            [dem.transform.a, dem.transform.b, dem.transform.c, dem.transform.d, dem.transform.e, dem.transform.f],
                            rtol=0, atol=1e-9)
        )
        if exact_grid:
            aligned[:] = src
            resampling = "none; grids were already identical"
        else:
            reproject(
                source=src, destination=aligned, src_transform=dem.transform, src_crs=dem.crs,
                src_nodata=np.nan, dst_transform=img.transform, dst_crs=img.crs, dst_nodata=np.nan,
                resampling=Resampling.bilinear, init_dest_nodata=True,
            )
            resampling = "bilinear reprojection onto the optical image grid"
        
        img_valid = img.dataset_mask() > 0
        aligned[~img_valid] = np.nan
        val_frac = float(np.count_nonzero(np.isfinite(aligned) & img_valid) / max(int(img_valid.sum()), 1))
        if val_frac < 0.90:
            raise TerrainInputError(
                f"The DEM covers only {val_frac:.1%} of valid optical pixels after alignment; at least 90% is required. "
                "Download both files for the same area of interest."
            )
        valid = aligned[np.isfinite(aligned)]
        if valid.size < 64 or float(np.ptp(valid)) < 1.0:
            raise TerrainInputError("The aligned DEM does not contain enough finite elevation variation.")
        
        tf_d, tf_i = dem.transform, img.transform
        report = {
            "schema_version": "1.0", "alignment": resampling, "exact_input_grid": exact_grid,
            "source_dem": {"crs": dem.crs.to_string(), "shape": [dem.height, dem.width], "transform": [tf_d.a, tf_d.b, tf_d.c, tf_d.d, tf_d.e, tf_d.f], "pixel_size": [abs(tf_d.a), abs(tf_d.e)], "nodata": dem.nodata},
            "output_grid": {"crs": img.crs.to_string(), "shape": [img.height, img.width], "transform": [tf_i.a, tf_i.b, tf_i.c, tf_i.d, tf_i.e, tf_i.f], "pixel_size": [abs(tf_i.a), abs(tf_i.e)]},
            "valid_coverage_fraction": val_frac,
            "important": "Reprojection/resampling changes the grid but does not improve the DEM's native spatial resolution or accuracy.",
        }
        return aligned, img_valid, report


def _display_normalize(metric: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    valid = metric[np.isfinite(metric)].astype(np.float64)
    low, high = np.percentile(valid, (0.5, 99.5)).astype(float)
    if high - low < 1.0:
        low, high = float(valid.min()), float(valid.max())
    filled = fillnodata(
        metric.astype(np.float32), mask=np.isfinite(metric).astype(np.uint8),
        max_search_distance=max(metric.shape), smoothing_iterations=0,
    ).astype(np.float32)
    filled[~np.isfinite(filled)] = float(np.median(valid))
    relative = np.clip((filled - low) / max(high - low, 1e-6), 0, 1).astype(np.float32)
    return relative, {
        "clip_p005_m": low, "clip_p995_m": high,
        "source_minimum_m": float(valid.min()), "source_maximum_m": float(valid.max()),
        "nodata_filled_for_display_only": int(np.count_nonzero(~np.isfinite(metric))),
    }


def _write_metric_geotiff(
    output_path: Path,
    imagery_path: Path,
    metric: np.ndarray,
    *,
    source_description: str,
    vertical_datum: str,
) -> None:
    with rasterio.open(imagery_path) as img:
        prof = img.profile.copy()
        prof.update(driver="GTiff", count=1, dtype="float32", nodata=-9999.0, compress="deflate", predictor=3)
        out = np.where(np.isfinite(metric), metric, -9999.0).astype(np.float32)
        with rasterio.open(output_path, "w", **prof) as dst:
            dst.write(out, 1)
            dst.set_band_description(1, "source DEM elevation aligned to optical grid")
            dst.update_tags(
                units="metre", vertical_datum=vertical_datum, elevation_source=source_description,
                processing="source DEM reprojected/resampled to optical image grid where required",
                scientific_state="Metric Source DEM",
            )


def _write_manifest(store: JobStore, manifest: JobManifest) -> None:
    job_dir = store.job_dir(manifest.job_id)
    manifest.artifacts = [a for a in manifest.artifacts if a.name != "manifest"]
    store.save(manifest)
    path = job_dir / "job_manifest.json"
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    manifest.artifacts.append(_artifact("manifest", path, "application/json"))
    store.save(manifest)


def run_source_dem_job(job_id: str, settings: Settings) -> None:
    store = JobStore(settings.jobs_root)
    manifest = store.get(job_id)
    job_dir = store.job_dir(job_id)
    img_path = job_dir / str(manifest.input["stored_filename"])
    dem_path = job_dir / str(manifest.input["dem"]["stored_filename"])
    try:
        manifest.status, manifest.stage, manifest.progress = JobStatus.RUNNING, "validation", 15
        store.save(manifest)
        inspected = inspect_image(img_path.read_bytes(), str(manifest.input["filename"]), settings.max_pixels)
        if inspected.geospatial is None:
            raise TerrainInputError("Terrain mode requires a georeferenced optical GeoTIFF.")

        manifest.stage, manifest.progress = "preprocessing", 40
        store.save(manifest)
        metric, _, alignment = _align_dem(img_path, dem_path)
        relative, normalization = _display_normalize(metric)

        manifest.stage, manifest.progress = "meshing", 75
        store.save(manifest)
        source_desc = str(manifest.calibration["evidence"]["source_description"])
        v_datum = str(manifest.calibration["evidence"]["vertical_datum"])
        rep_v_units = manifest.input["dem"].get("reported_vertical_units")
        conversion = {
            "source": "uploaded metric DEM", "operation": "robust normalization for display geometry only",
            "metric_values_changed": False, "display_normalization": normalization,
        }
        artifacts = write_surface_artifacts(
            job_dir, relative, inspected.rgb,
            raw_model_output=np.where(np.isfinite(metric), metric, np.nan).astype(np.float32),
            conversion_diagnostics=conversion, source_kind="source_dem",
        )
        metric_path = job_dir / "metric_surface.npy"
        np.save(metric_path, metric.astype(np.float32), allow_pickle=False)
        artifacts.append(_artifact("metric_surface", metric_path, "application/octet-stream"))
        
        metric_grid_path = job_dir / "metric_analysis_grid.json"
        _write_metric_grid(metric_grid_path, job_dir / "relative_grid.json", metric, vertical_datum=v_datum, measurement_role="source DEM elevation samples for 3D point analysis")
        artifacts.append(_artifact("metric_grid", metric_grid_path, "application/json"))

        gtiff_path = job_dir / "metric_surface.tif"
        _write_metric_geotiff(gtiff_path, img_path, metric, source_description=source_desc, vertical_datum=v_datum)
        artifacts.append(_artifact("metric_geotiff", gtiff_path, "image/tiff"))
        artifacts.append(_artifact("source_dem", dem_path, "image/tiff"))

        rep = {
            **alignment, "source_description": source_desc, "vertical_datum": v_datum, "vertical_units": "metre",
            "source_dem_reported_vertical_units": rep_v_units, "source_dem_filename": manifest.input["dem"]["filename"],
            "source_dem_sha256": manifest.input["dem"]["sha256"], "display_normalization": normalization,
            "accuracy_statement": "TerraFly validated format, coverage, and alignment. Elevation accuracy remains the responsibility of the named DEM source.",
        }
        rep_path = job_dir / "terrain_alignment_report.json"
        rep_path.write_text(json.dumps(rep, indent=2), encoding="utf-8")
        artifacts.append(_artifact("terrain_alignment_report", rep_path, "application/json"))

        manifest.artifacts = artifacts
        manifest.scientific_state = ScientificState.METRIC_SOURCE_DEM
        manifest.units = "metre"
        manifest.model = {"adapter": "source_dem", "checkpoint": "uploaded metric DEM", "revision": manifest.input["dem"]["sha256"], "device": "not applicable"}
        manifest.configuration.update({
            "workflow": "source_dem_terrain", "inference_mode": "not_used", "geometry_source": "uploaded_dem",
            "alignment": alignment, "display_normalization": normalization, "display_cleanup": "disabled for source DEM terrain",
        })
        manifest.calibration.update({
            "status": "source_dem", "metric_output_allowed": True,
            "reason": "Elevation values come directly from the named source DEM; no monocular scale fitting was used.",
            "alignment": alignment,
        })
        t_warns = [w for w in manifest.warnings if "does not establish vertical scale" not in w]
        manifest.warnings = list(dict.fromkeys(t_warns + [
            "Optical georeferencing locates the texture; vertical values come from the named source DEM.",
            (f"The source DEM reports its vertical units as {rep_v_units}; TerraFly accepted them as metres." if rep_v_units else "The source DEM did not include a band-unit tag; its numeric values are treated as metres from the source declaration."),
            "Metric heights originate from the uploaded DEM. TerraFly checked alignment but did not independently certify the DEM's accuracy.",
            "Any vertical exaggeration changes only the display; downloaded metric values remain unchanged.",
        ]))
        manifest.status, manifest.stage, manifest.progress = JobStatus.COMPLETE, "complete", 100
        _write_manifest(store, manifest)
    except Exception as exc:
        manifest.status, manifest.stage = JobStatus.FAILED, "failed"
        manifest.error = str(exc)
        manifest.warnings.append("The terrain job failed without claiming a metric result.")
        manifest.configuration["diagnostic"] = traceback.format_exc(limit=8)
        store.save(manifest)
