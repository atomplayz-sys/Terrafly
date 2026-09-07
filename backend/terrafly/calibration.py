from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from PIL import Image
from rasterio.io import MemoryFile

from .artifacts import _artifact
from .jobs import JobStore
from .schemas import Artifact, CalibrationPoint, JobManifest, ScientificState

CALIBRATION_ARTIFACTS = {
    "calibration_reference",
    "calibration_report",
    "metric_surface",
    "metric_grid",
    "metric_geotiff",
    "error_geotiff",
    "error_preview",
}


class CalibrationInputError(ValueError):
    """The supplied calibration evidence cannot be compared safely."""


def _finite_metrics(predicted: np.ndarray, observed: np.ndarray) -> dict[str, float | int]:
    p, o = np.asarray(predicted, dtype=np.float64), np.asarray(observed, dtype=np.float64)
    valid = np.isfinite(p) & np.isfinite(o)
    if not np.any(valid):
        raise CalibrationInputError("No finite validation observations were supplied.")
    res = p[valid] - o[valid]
    abs_err = np.abs(res)
    den = float(np.sum((o[valid] - np.mean(o[valid])) ** 2))
    return {
        "count": int(res.size),
        "rmse_m": float(np.sqrt(np.mean(res**2))),
        "mae_m": float(np.mean(abs_err)),
        "bias_m": float(np.mean(res)),
        "median_absolute_error_m": float(np.median(abs_err)),
        "p95_absolute_error_m": float(np.percentile(abs_err, 95)),
        "r_squared": (1.0 - float(np.sum(res**2)) / den) if den > 0 else 0.0,
    }


def robust_affine_fit(relative: np.ndarray, elevation: np.ndarray) -> tuple[float, float, np.ndarray]:
    """Fit elevation = scale * relative + offset using a robust, auditable clip/refit loop."""
    x = np.asarray(relative, dtype=np.float64).ravel()
    y = np.asarray(elevation, dtype=np.float64).ravel()
    finite = np.isfinite(x) & np.isfinite(y)
    x, y = x[finite], y[finite]
    if x.size < 6:
        raise CalibrationInputError("At least six finite calibration observations are required.")
    x_low, x_high = np.percentile(x, (10, 90))
    if x_high - x_low < 1e-6:
        raise CalibrationInputError("Calibration observations do not span enough relative values.")

    scale = float((np.median(y[x >= x_high]) - np.median(y[x <= x_low])) / (x_high - x_low))
    offset = float(np.median(y - scale * x))
    inliers = np.ones(x.size, dtype=bool)
    y_span = max(float(np.percentile(y, 95) - np.percentile(y, 5)), 1.0)

    for _ in range(8):
        res = y - (scale * x + offset)
        centre = float(np.median(res[inliers]))
        mad = float(np.median(np.abs(res[inliers] - centre)))
        threshold = max(3.5 * (1.4826 * mad), y_span * 0.001, 1e-5)
        next_inliers = np.abs(res - centre) <= threshold
        if int(next_inliers.sum()) < 6:
            break
        design = np.column_stack((x[next_inliers], np.ones(int(next_inliers.sum()))))
        scale, offset = np.linalg.lstsq(design, y[next_inliers], rcond=None)[0].astype(float)
        if np.array_equal(next_inliers, inliers):
            break
        inliers = next_inliers
    return float(scale), float(offset), inliers


def _sample_bilinear(surface: np.ndarray, points: list[CalibrationPoint]) -> np.ndarray:
    h, w = surface.shape
    values: list[float] = []
    for pt in points:
        if pt.column > w - 1 or pt.row > h - 1:
            raise CalibrationInputError(f"Control point ({pt.column}, {pt.row}) falls outside the {w}×{h} image.")
        x0, y0 = int(np.floor(pt.column)), int(np.floor(pt.row))
        x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)
        dx, dy = pt.column - x0, pt.row - y0
        if not np.isfinite(surface[np.ix_([y0, y1], [x0, x1])]).all():
            raise CalibrationInputError(f"Control point ({pt.column}, {pt.row}) touches a NoData source pixel.")
        val = (
            surface[y0, x0] * (1 - dx) * (1 - dy)
            + surface[y0, x1] * dx * (1 - dy)
            + surface[y1, x0] * (1 - dx) * dy
            + surface[y1, x1] * dx * dy
        )
        values.append(float(val))
    return np.asarray(values, dtype=np.float64)


def _source_valid_mask(input_path: Path) -> np.ndarray:
    with rasterio.open(input_path) as src:
        return src.dataset_mask() > 0


def _spatial_coverage(points: list[CalibrationPoint], shape: tuple[int, int]) -> dict[str, float]:
    h, w = shape
    cols = np.asarray([p.column for p in points], dtype=np.float64)
    rows = np.asarray([p.row for p in points], dtype=np.float64)
    return {
        "column_fraction": float((cols.max() - cols.min()) / max(w - 1, 1)),
        "row_fraction": float((rows.max() - rows.min()) / max(h - 1, 1)),
    }


def _gate(
    *,
    scale: float,
    relative_span: float,
    inlier_ratio: float,
    evaluation: dict[str, float | int],
    max_rmse_m: float,
    coverage: dict[str, float],
    minimum_evaluation_count: int,
) -> tuple[bool, list[str]]:
    fails: list[str] = []
    if not np.isfinite(scale) or scale <= 0:
        fails.append("The fitted vertical scale is not positive.")
    if relative_span < 0.05:
        fails.append("Calibration evidence spans less than 0.05 relative units.")
    if inlier_ratio < 0.75:
        fails.append("Fewer than 75% of calibration observations agree with one affine scale and offset.")
    if int(evaluation["count"]) < minimum_evaluation_count:
        fails.append(f"Held-out evaluation needs at least {minimum_evaluation_count} valid observations.")
    if float(evaluation["rmse_m"]) > max_rmse_m:
        fails.append(f"Held-out RMSE {float(evaluation['rmse_m']):.3f} m exceeds the declared {max_rmse_m:.3f} m limit.")
    if float(evaluation["r_squared"]) < 0.5:
        fails.append("Held-out R² is below 0.50.")
    if coverage["column_fraction"] < 0.4 or coverage["row_fraction"] < 0.4:
        fails.append("Calibration evidence does not cover at least 40% of both image axes.")
    return not fails, fails


def _remove_old_calibration(job_dir: Path, manifest: JobManifest) -> None:
    retained = []
    for art in manifest.artifacts:
        if art.name in CALIBRATION_ARTIFACTS or art.name == "manifest":
            if art.name in CALIBRATION_ARTIFACTS:
                (job_dir / art.filename).unlink(missing_ok=True)
        else:
            retained.append(art)
    manifest.artifacts = retained


def _write_manifest(store: JobStore, manifest: JobManifest) -> None:
    job_dir = store.job_dir(manifest.job_id)
    manifest.artifacts = [a for a in manifest.artifacts if a.name != "manifest"]
    store.save(manifest)
    path = job_dir / "job_manifest.json"
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    manifest.artifacts.append(_artifact("manifest", path, "application/json"))
    store.save(manifest)


def _write_metric_geotiff(
    path: Path,
    input_path: Path,
    values: np.ndarray,
    *,
    vertical_datum: str,
    source_description: str,
    kind: str,
) -> None:
    with rasterio.open(input_path) as src:
        prof = src.profile.copy()
        prof.update(driver="GTiff", count=1, dtype="float32", nodata=-9999.0, compress="deflate", predictor=3)
        out = np.where(np.isfinite(values), values, -9999.0).astype(np.float32)
        with rasterio.open(path, "w", **prof) as dst:
            dst.write(out, 1)
            dst.set_band_description(1, kind)
            dst.update_tags(
                units="metre",
                vertical_datum=vertical_datum,
                calibration_source=source_description,
                calibration_model="elevation_m = scale * relative_surface + offset",
                scientific_state="Metric Calibrated",
            )


def _write_metric_grid(
    path: Path,
    relative_grid_path: Path,
    metric: np.ndarray,
    *,
    vertical_datum: str,
    measurement_role: str = "calibrated elevation samples for 3D point analysis",
) -> None:
    """Write metric samples on the exact same grid used by the 3D viewer."""
    rel_grid = json.loads(relative_grid_path.read_text(encoding="utf-8"))
    r_idx = np.asarray(rel_grid["row_indices"], dtype=np.int64)
    c_idx = np.asarray(rel_grid["column_indices"], dtype=np.int64)
    sampled = metric[np.ix_(r_idx, c_idx)].astype(np.float64)
    values = [float(v) if np.isfinite(v) else None for v in sampled.ravel()]
    path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "shape": list(sampled.shape),
            "source_shape": list(metric.shape),
            "row_indices": r_idx.tolist(),
            "column_indices": c_idx.tolist(),
            "orientation": rel_grid["orientation"],
            "units": "metre",
            "vertical_datum": vertical_datum,
            "measurement_role": measurement_role,
            "geometry_source": "relative_grid.json",
            "values": values,
        }, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )


def _error_preview(error: np.ndarray) -> np.ndarray:
    valid = error[np.isfinite(error)]
    limit = max(float(np.percentile(np.abs(valid), 95)), 1e-6)
    scaled = np.clip(error / limit, -1, 1)
    rgb = np.zeros((*error.shape, 3), dtype=np.uint8)
    neg, pos = scaled < 0, scaled > 0
    rgb[..., :] = 245
    rgb[neg, 0] = (245 * (1 + scaled[neg])).astype(np.uint8)
    rgb[neg, 1] = (245 * (1 + scaled[neg])).astype(np.uint8)
    rgb[pos, 1] = (245 * (1 - scaled[pos])).astype(np.uint8)
    rgb[pos, 2] = (245 * (1 - scaled[pos])).astype(np.uint8)
    rgb[~np.isfinite(error)] = 35
    return rgb


def _finish(
    store: JobStore,
    manifest: JobManifest,
    report: dict[str, Any],
    *,
    accepted: bool,
    metric: np.ndarray | None = None,
    reference: np.ndarray | None = None,
    reference_bytes: bytes | None = None,
) -> JobManifest:
    job_dir = store.job_dir(manifest.job_id)
    _remove_old_calibration(job_dir, manifest)
    if reference_bytes is not None:
        ref_path = job_dir / "calibration_reference.tif"
        ref_path.write_bytes(reference_bytes)
        manifest.artifacts.append(_artifact("calibration_reference", ref_path, "image/tiff"))

    if accepted and metric is not None:
        metric_path = job_dir / "metric_surface.npy"
        np.save(metric_path, metric.astype(np.float32), allow_pickle=False)
        manifest.artifacts.append(_artifact("metric_surface", metric_path, "application/octet-stream"))
        
        grid_path = job_dir / "metric_analysis_grid.json"
        _write_metric_grid(grid_path, job_dir / "relative_grid.json", metric, vertical_datum=str(report["evidence"]["vertical_datum"]))
        manifest.artifacts.append(_artifact("metric_grid", grid_path, "application/json"))

        gtiff_path = job_dir / "metric_surface.tif"
        _write_metric_geotiff(
            gtiff_path, job_dir / manifest.input["stored_filename"], metric,
            vertical_datum=str(report["evidence"]["vertical_datum"]),
            source_description=str(report["evidence"]["source_description"]),
            kind="calibrated elevation",
        )
        manifest.artifacts.append(_artifact("metric_geotiff", gtiff_path, "image/tiff"))

        if reference is not None:
            err = metric - reference
            err_path = job_dir / "calibration_error.tif"
            _write_metric_geotiff(
                err_path, job_dir / manifest.input["stored_filename"], err,
                vertical_datum=str(report["evidence"]["vertical_datum"]),
                source_description=str(report["evidence"]["source_description"]),
                kind="calibration residual (candidate minus reference)",
            )
            manifest.artifacts.append(_artifact("error_geotiff", err_path, "image/tiff"))
            prev_path = job_dir / "calibration_error_preview.png"
            Image.fromarray(_error_preview(err), mode="RGB").save(prev_path, optimize=True)
            manifest.artifacts.append(_artifact("error_preview", prev_path, "image/png"))

    rep_path = job_dir / "calibration_report.json"
    rep_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    manifest.artifacts.append(_artifact("calibration_report", rep_path, "application/json"))
    manifest.calibration = report
    if accepted:
        manifest.scientific_state = ScientificState.METRIC_CALIBRATED
        manifest.units = "metre"
        note = "Metric outputs passed held-out validation; their vertical datum and error metrics are recorded in the calibration report."
    else:
        manifest.scientific_state = ScientificState.GEOREFERENCED_RELATIVE
        manifest.units = "relative_0_1"
        note = "Calibration evidence was evaluated but did not pass; metric output remains locked."
    manifest.warnings = list(dict.fromkeys(manifest.warnings + [note]))
    _write_manifest(store, manifest)
    return manifest


def calibrate_reference(
    store: JobStore,
    manifest: JobManifest,
    reference_bytes: bytes,
    reference_filename: str,
    source_description: str,
    vertical_datum: str,
    max_rmse_m: float,
) -> JobManifest:
    if manifest.geospatial is None:
        raise CalibrationInputError("Metric calibration requires a georeferenced input GeoTIFF.")
    job_dir = store.job_dir(manifest.job_id)
    surface = np.load(job_dir / "relative_surface.npy", allow_pickle=False)
    source_valid = _source_valid_mask(job_dir / manifest.input["stored_filename"])
    try:
        with MemoryFile(reference_bytes) as mem, mem.open() as ds:
            if ds.count != 1:
                raise CalibrationInputError("The reference DSM must contain exactly one raster band.")
            exp_tf = np.asarray(manifest.geospatial["transform"], dtype=float)
            act_tf = np.asarray([ds.transform.a, ds.transform.b, ds.transform.c, ds.transform.d, ds.transform.e, ds.transform.f])
            if ds.crs is None or ds.crs.to_string() != manifest.geospatial["crs"]:
                raise CalibrationInputError("Reference DSM CRS must exactly match the input GeoTIFF CRS.")
            if ds.width != surface.shape[1] or ds.height != surface.shape[0]:
                raise CalibrationInputError("Reference DSM width and height must exactly match the input.")
            if not np.allclose(act_tf, exp_tf, rtol=0, atol=1e-9):
                raise CalibrationInputError("Reference DSM pixel grid and affine transform must exactly match the input.")
            reference = ds.read(1, masked=True).filled(np.nan).astype(np.float64)
    except CalibrationInputError:
        raise
    except Exception as exc:
        raise CalibrationInputError(f"Unreadable reference GeoTIFF: {exc}") from exc

    valid = source_valid & np.isfinite(reference) & np.isfinite(surface)
    rows, cols = np.indices(surface.shape)
    held_out = ((rows // max(surface.shape[0] // 4, 1)) + (cols // max(surface.shape[1] // 4, 1))) % 4 == 0
    training, eval_mask = valid & ~held_out, valid & held_out
    if int(valid.sum()) < 256 or int(training.sum()) < 128 or int(eval_mask.sum()) < 64:
        raise CalibrationInputError("Reference DSM needs at least 256 aligned valid pixels with a usable held-out split.")

    tr_idx = np.flatnonzero(training)
    if tr_idx.size > 50_000:
        tr_idx = tr_idx[np.linspace(0, tr_idx.size - 1, 50_000).astype(int)]
    x_tr, y_tr = surface.ravel()[tr_idx], reference.ravel()[tr_idx]
    scale, offset, inliers = robust_affine_fit(x_tr, y_tr)
    evaluation = _finite_metrics(scale * surface[eval_mask] + offset, reference[eval_mask])
    rel_span = float(np.percentile(x_tr, 95) - np.percentile(x_tr, 5))
    v_rows, v_cols = np.nonzero(valid)
    coverage = {
        "column_fraction": float((v_cols.max() - v_cols.min()) / max(surface.shape[1] - 1, 1)),
        "row_fraction": float((v_rows.max() - v_rows.min()) / max(surface.shape[0] - 1, 1)),
    }
    accepted, fails = _gate(
        scale=scale, relative_span=rel_span, inlier_ratio=float(inliers.mean()),
        evaluation=evaluation, max_rmse_m=max_rmse_m, coverage=coverage, minimum_evaluation_count=64,
    )
    report = {
        "schema_version": "1.0",
        "method": "aligned_reference_dsm",
        "status": "passed" if accepted else "rejected",
        "metric_output_allowed": accepted,
        "reason": "Held-out reference DSM evaluation passed every declared quality gate." if accepted else " ".join(fails),
        "evidence": {
            "source_description": source_description, "vertical_datum": vertical_datum,
            "reference_filename": reference_filename, "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
            "alignment": "exact CRS, dimensions, and affine transform",
        },
        "fit": {
            "equation": "elevation_m = scale * relative_surface + offset",
            "scale_m_per_relative_unit": scale, "offset_m": offset,
            "training_count": int(x_tr.size), "training_inlier_count": int(inliers.sum()),
            "training_inlier_ratio": float(inliers.mean()), "relative_p05_p95_span": rel_span,
        },
        "evaluation": evaluation,
        "quality_gate": {
            "passed": accepted, "declared_max_rmse_m": max_rmse_m, "minimum_r_squared": 0.5,
            "minimum_inlier_ratio": 0.75, "minimum_axis_coverage": 0.4, "coverage": coverage,
            "failures": fails, "split": "spatial checkerboard; evaluation pixels were never used for fitting",
        },
    }
    metric = np.where(source_valid, scale * surface + offset, np.nan).astype(np.float32)
    return _finish(
        store, manifest, report, accepted=accepted,
        metric=metric if accepted else None, reference=reference if accepted else None, reference_bytes=reference_bytes,
    )


def calibrate_gcps(
    store: JobStore,
    manifest: JobManifest,
    *,
    controls: list[CalibrationPoint],
    validation: list[CalibrationPoint],
    source_description: str,
    vertical_datum: str,
    max_rmse_m: float,
) -> JobManifest:
    if manifest.geospatial is None:
        raise CalibrationInputError("Metric calibration requires a georeferenced input GeoTIFF.")
    job_dir = store.job_dir(manifest.job_id)
    surface = np.load(job_dir / "relative_surface.npy", allow_pickle=False)
    source_valid = _source_valid_mask(job_dir / manifest.input["stored_filename"])
    masked_surface = np.where(source_valid, surface, np.nan)
    x_tr = _sample_bilinear(masked_surface, controls)
    y_tr = np.asarray([p.elevation_m for p in controls], dtype=np.float64)
    x_ev = _sample_bilinear(masked_surface, validation)
    y_ev = np.asarray([p.elevation_m for p in validation], dtype=np.float64)
    scale, offset, inliers = robust_affine_fit(x_tr, y_tr)
    evaluation = _finite_metrics(scale * x_ev + offset, y_ev)
    rel_span = float(np.percentile(x_tr, 95) - np.percentile(x_tr, 5))
    coverage = _spatial_coverage(controls + validation, surface.shape)
    accepted, fails = _gate(
        scale=scale, relative_span=rel_span, inlier_ratio=float(inliers.mean()),
        evaluation=evaluation, max_rmse_m=max_rmse_m, coverage=coverage, minimum_evaluation_count=3,
    )
    report = {
        "schema_version": "1.0",
        "method": "ground_control_points",
        "status": "passed" if accepted else "rejected",
        "metric_output_allowed": accepted,
        "reason": "Independent validation GCPs passed every declared quality gate." if accepted else " ".join(fails),
        "evidence": {
            "source_description": source_description, "vertical_datum": vertical_datum,
            "controls": [p.model_dump() for p in controls], "validation": [p.model_dump() for p in validation],
        },
        "fit": {
            "equation": "elevation_m = scale * relative_surface + offset",
            "scale_m_per_relative_unit": scale, "offset_m": offset,
            "training_count": len(controls), "training_inlier_count": int(inliers.sum()),
            "training_inlier_ratio": float(inliers.mean()), "relative_p05_p95_span": rel_span,
        },
        "evaluation": evaluation,
        "quality_gate": {
            "passed": accepted, "declared_max_rmse_m": max_rmse_m, "minimum_r_squared": 0.5,
            "minimum_inlier_ratio": 0.75, "minimum_axis_coverage": 0.4, "coverage": coverage,
            "failures": fails, "split": "validation points were independent and never used for fitting",
        },
    }
    metric = np.where(source_valid, scale * surface + offset, np.nan).astype(np.float32)
    return _finish(store, manifest, report, accepted=accepted, metric=metric if accepted else None)
