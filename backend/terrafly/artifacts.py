from __future__ import annotations

import hashlib
import io
import json
import struct
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .schemas import Artifact

DISPLAY_WALL_DELTA_THRESHOLD: float = 0.055


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file using chunked binary reading."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(name: str, path: Path, media_type: str) -> Artifact:
    """Create an Artifact descriptor with accurate hash and size metadata."""
    return Artifact(
        name=name,
        filename=path.name,
        media_type=media_type,
        sha256=sha256_file(path),
        bytes=path.stat().st_size,
    )


def _colourize(relative: np.ndarray) -> np.ndarray:
    """Linear colormap interpolation from dark blue to red across 5 control stops."""
    stops = np.array(
        [[15, 23, 42], [14, 116, 144], [34, 197, 94], [250, 204, 21], [239, 68, 68]],
        dtype=np.float32,
    )
    scaled = np.clip(relative, 0, 1) * (len(stops) - 1)
    lower = np.floor(scaled).astype(np.int32)
    upper = np.minimum(lower + 1, len(stops) - 1)
    fraction = (scaled - lower)[..., None]
    return (stops[lower] * (1 - fraction) + stops[upper] * fraction).astype(np.uint8)


def _append_aligned(buffer: bytearray, content: bytes) -> tuple[int, int]:
    """Append content to bytearray with 4-byte boundary padding for glTF binary."""
    pad = (4 - (len(buffer) % 4)) % 4
    buffer.extend(b"\x00" * pad)
    offset = len(buffer)
    buffer.extend(content)
    return offset, len(content)


def _surface_triangle_indices(
    grid: np.ndarray,
    *,
    wall_delta_threshold: float = DISPLAY_WALL_DELTA_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray]:
    """Split display triangles into photo-textured surfaces and synthetic neutral walls."""
    rows, columns = grid.shape
    r, c = np.meshgrid(np.arange(rows - 1), np.arange(columns - 1), indexing="ij")
    i = (r * columns + c).ravel()
    right, below, diag = i + 1, i + columns, i + columns + 1
    t1 = np.stack([i, below, right], axis=1)
    t2 = np.stack([right, below, diag], axis=1)
    triangles = np.vstack([t1, t2])

    flat = grid.ravel()
    heights = flat[triangles]
    is_wall = np.ptp(heights, axis=1) >= wall_delta_threshold
    return (
        triangles[~is_wall].astype("<u4").ravel(),
        triangles[is_wall].astype("<u4").ravel(),
    )


def _surface_normals(grid: np.ndarray) -> np.ndarray:
    """Return smooth unit normals for a height grid in TerraFly mesh coordinates."""
    rows, columns = grid.shape
    aspect = rows / columns
    x_coords = np.linspace(-5, 5, columns, dtype=np.float32)
    z_coords = np.linspace(-5 * aspect, 5 * aspect, rows, dtype=np.float32)
    dz, dx = np.gradient(grid.astype(np.float32), z_coords, x_coords, edge_order=1)
    normals = np.stack((-dx, np.ones_like(grid, dtype=np.float32), -dz), axis=-1)
    lengths = np.linalg.norm(normals, axis=-1, keepdims=True)
    return np.ascontiguousarray(normals / np.maximum(lengths, 1e-8), dtype="<f4")


def _embedded_texture_png(rgb: np.ndarray, *, maximum_side: int = 2048) -> tuple[bytes, list[int]]:
    """Encode a native-resolution source image for GLB, with a bounded safety cap."""
    image = Image.fromarray(np.asarray(rgb, dtype=np.uint8), mode="RGB")
    if max(image.size) > maximum_side:
        image.thumbnail((maximum_side, maximum_side), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue(), [image.height, image.width]


def _write_glb(
    path: Path,
    grid: np.ndarray,
    rgb: np.ndarray,
    *,
    scientific_state: str = "Relative",
    units: str = "relative_0_1",
    numeric_source: str = "relative_surface.npy",
    mesh_name: str = "Relative surface",
    display_only_processing: bool = True,
    wall_delta_threshold: float = DISPLAY_WALL_DELTA_THRESHOLD,
) -> None:
    """Write a textured, lit display GLB with neutral synthetic steep faces."""
    rows, columns = grid.shape
    aspect = rows / columns
    positions = np.empty((rows * columns, 3), dtype="<f4")
    positions[:, 0] = np.tile(np.linspace(-5, 5, columns, dtype=np.float32), rows)
    positions[:, 1] = grid.astype(np.float32).ravel()
    positions[:, 2] = np.repeat(np.linspace(-5 * aspect, 5 * aspect, rows, dtype=np.float32), columns)

    uvs = np.empty((rows * columns, 2), dtype="<f4")
    uvs[:, 0] = np.tile(np.linspace(0, 1, columns, dtype=np.float32), rows)
    uvs[:, 1] = np.repeat(np.linspace(1, 0, rows, dtype=np.float32), columns)

    normals = _surface_normals(grid).reshape(-1, 3)
    textured_idx, wall_idx = _surface_triangle_indices(grid, wall_delta_threshold=wall_delta_threshold)
    tex_bytes, tex_shape = _embedded_texture_png(rgb)

    bin_buf = bytearray()
    p_off, p_len = _append_aligned(bin_buf, positions.tobytes())
    uv_off, uv_len = _append_aligned(bin_buf, uvs.tobytes())
    n_off, n_len = _append_aligned(bin_buf, normals.tobytes())
    img_off, img_len = _append_aligned(bin_buf, tex_bytes)

    bviews: list[dict[str, Any]] = [
        {"buffer": 0, "byteOffset": p_off, "byteLength": p_len, "target": 34962},
        {"buffer": 0, "byteOffset": uv_off, "byteLength": uv_len, "target": 34962},
        {"buffer": 0, "byteOffset": n_off, "byteLength": n_len, "target": 34962},
        {"buffer": 0, "byteOffset": img_off, "byteLength": img_len},
    ]
    accessors: list[dict[str, Any]] = [
        {
            "bufferView": 0,
            "componentType": 5126,
            "count": len(positions),
            "type": "VEC3",
            "min": positions.min(0).astype(float).tolist(),
            "max": positions.max(0).astype(float).tolist(),
        },
        {
            "bufferView": 1,
            "componentType": 5126,
            "count": len(uvs),
            "type": "VEC2",
            "min": uvs.min(0).astype(float).tolist(),
            "max": uvs.max(0).astype(float).tolist(),
        },
        {
            "bufferView": 2,
            "componentType": 5126,
            "count": len(normals),
            "type": "VEC3",
            "min": normals.min(0).astype(float).tolist(),
            "max": normals.max(0).astype(float).tolist(),
        },
    ]
    primitives: list[dict[str, Any]] = []

    def _add_idx(indices: np.ndarray, mat_id: int) -> None:
        if not indices.size:
            return
        off, length = _append_aligned(bin_buf, indices.tobytes())
        bv_idx = len(bviews)
        bviews.append({"buffer": 0, "byteOffset": off, "byteLength": length, "target": 34963})
        acc_idx = len(accessors)
        accessors.append({
            "bufferView": bv_idx,
            "componentType": 5125,
            "count": int(indices.size),
            "type": "SCALAR",
            "min": [int(indices.min())],
            "max": [int(indices.max())],
        })
        primitives.append({
            "attributes": {"POSITION": 0, "TEXCOORD_0": 1, "NORMAL": 2},
            "indices": acc_idx,
            "material": mat_id,
            "mode": 4,
        })

    _add_idx(textured_idx, mat_id=0)
    _add_idx(wall_idx, mat_id=1)
    while len(bin_buf) % 4:
        bin_buf.append(0)

    doc: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "TerraFly 1.0"},
        "buffers": [{"byteLength": len(bin_buf)}],
        "bufferViews": bviews,
        "accessors": accessors,
        "images": [{"name": "TerraFly source photo", "bufferView": 3, "mimeType": "image/png"}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "textures": [{"name": "TerraFly source photo", "sampler": 0, "source": 0}],
        "materials": [
            {
                "name": "Embedded source photo",
                "doubleSided": True,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1, 1, 1, 1],
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0,
                    "roughnessFactor": 0.92,
                },
            },
            {
                "name": "Synthetic neutral steep faces",
                "doubleSided": True,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.34, 0.39, 0.37, 1],
                    "metallicFactor": 0,
                    "roughnessFactor": 1,
                },
            },
        ],
        "meshes": [{
            "name": mesh_name,
            "primitives": primitives,
            "extras": {
                "scientific_state": scientific_state,
                "units": units,
                "vertical_scale_metric": False,
                "orientation": "row 0 is image top; column 0 is image left",
                "geometry_source": "display_grid.json",
                "numeric_source": numeric_source,
                "display_only_processing": display_only_processing,
                "embedded_texture": "native source RGB, PNG, maximum side 2048 pixels",
                "embedded_texture_shape": tex_shape,
                "normals": "smooth per-vertex central-difference normals",
                "material_model": "pbrMetallicRoughness",
                "steep_face_material": "synthetic neutral; aerial colour disabled",
                "wall_delta_threshold": wall_delta_threshold,
            },
        }],
        "nodes": [{"mesh": 0, "name": f"TerraFly {mesh_name.lower()}"}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    json_bytes = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((-len(json_bytes)) % 4)
    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_buf)
    glb = (
        struct.pack("<4sII", b"glTF", 2, total_len)
        + struct.pack("<I4s", len(json_bytes), b"JSON")
        + json_bytes
        + struct.pack("<I4s", len(bin_buf), b"BIN\x00")
        + bytes(bin_buf)
    )
    path.write_bytes(glb)


def _local_median(values: np.ndarray, radius: int = 1) -> tuple[np.ndarray, np.ndarray]:
    padded = np.pad(values, radius, mode="reflect")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (radius * 2 + 1, radius * 2 + 1))
    median = np.median(windows, axis=(-2, -1))
    mad = np.median(np.abs(windows - median[..., None, None]), axis=(-2, -1))
    return median.astype(np.float32), mad.astype(np.float32)


def _remove_isolated_outliers(values: np.ndarray) -> tuple[np.ndarray, int]:
    median, mad = _local_median(values)
    padded = np.pad(values, 1, mode="reflect")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3))
    neighbour_support = np.sum(np.abs(windows - values[..., None, None]) <= 0.035, axis=(-2, -1))
    threshold = np.maximum(0.075, 6.0 * mad + 0.015)
    replace = (np.abs(values - median) > threshold) & (neighbour_support <= 3)
    cleaned = values.copy()
    cleaned[replace] = median[replace]
    return cleaned, int(np.count_nonzero(replace))


def _joint_bilateral_filter(
    values: np.ndarray,
    guidance: np.ndarray,
    *,
    radius: int = 2,
    spatial_sigma: float = 1.35,
    colour_sigma: float = 0.14,
    height_sigma: float = 0.10,
) -> np.ndarray:
    """RGB-guided bilateral filter for the bounded viewer grid."""
    source, guide = values.astype(np.float32), guidance.astype(np.float32) / 255.0
    psource = np.pad(source, radius, mode="reflect")
    pguide = np.pad(guide, ((radius, radius), (radius, radius), (0, 0)), mode="reflect")
    weighted = np.zeros_like(source, dtype=np.float64)
    total_w = np.zeros_like(source, dtype=np.float64)
    h, w = source.shape
    for ro in range(-radius, radius + 1):
        for co in range(-radius, radius + 1):
            ss = psource[radius + ro : radius + ro + h, radius + co : radius + co + w]
            sg = pguide[radius + ro : radius + ro + h, radius + co : radius + co + w]
            w_val = np.exp(
                -(ro * ro + co * co) / (2 * spatial_sigma**2)
                - np.square(sg - guide).sum(2) / (2 * colour_sigma**2)
                - np.square(ss - source) / (2 * height_sigma**2)
            )
            weighted += ss * w_val
            total_w += w_val
    return (weighted / np.maximum(total_w, 1e-12)).astype(np.float32)


def _connected_components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    rows, columns = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components: list[list[tuple[int, int]]] = []
    for start_r, start_c in zip(*np.nonzero(mask), strict=True):
        if visited[start_r, start_c]:
            continue
        stack = [(int(start_r), int(start_c))]
        visited[start_r, start_c] = True
        comp: list[tuple[int, int]] = []
        while stack:
            r, c = stack.pop()
            comp.append((r, c))
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < columns and mask[nr, nc] and not visited[nr, nc]:
                    visited[nr, nc] = True
                    stack.append((nr, nc))
        components.append(comp)
    return components


def _flatten_rooftop_candidates(values: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Flatten conservative raised connected regions for display geometry only."""
    rows, columns = values.shape
    r_axis = np.linspace(-1.0, 1.0, rows, dtype=np.float64)
    c_axis = np.linspace(-1.0, 1.0, columns, dtype=np.float64)
    rg, cg = np.meshgrid(r_axis, c_axis, indexing="ij")
    design = np.column_stack((np.ones(values.size), rg.ravel(), cg.ravel()))
    coeff, *_ = np.linalg.lstsq(design, values.ravel(), rcond=None)
    residual = values - (design @ coeff).reshape(values.shape)
    threshold = max(float(np.percentile(residual, 80)), 0.03)
    raised = residual >= threshold
    padded = np.pad(raised.astype(np.uint8), 1)
    support = np.zeros_like(raised, dtype=np.uint8)
    for ro in range(3):
        for co in range(3):
            support += padded[ro : ro + rows, co : co + columns]
    raised &= support >= 4

    min_area = max(5, int(round(values.size * 0.00015)))
    max_area = max(min_area, int(round(values.size * 0.35)))
    flattened = values.copy()
    reg_count = px_count = 0
    for comp in _connected_components(raised):
        if not min_area <= len(comp) <= max_area:
            continue
        c_vals = np.asarray([values[r, c] for r, c in comp], dtype=np.float32)
        if (float(np.percentile(c_vals, 90) - np.percentile(c_vals, 10))) > 0.18:
            continue
        roof = float(np.median(c_vals))
        for r, c in comp:
            flattened[r, c] = roof
        reg_count += 1
        px_count += len(comp)
    return flattened, reg_count, px_count


def _maximum_adjacent_delta(values: np.ndarray) -> float:
    deltas: list[float] = []
    if values.shape[0] > 1:
        deltas.append(float(np.max(np.abs(np.diff(values, axis=0)))))
    if values.shape[1] > 1:
        deltas.append(float(np.max(np.abs(np.diff(values, axis=1)))))
    return max(deltas, default=0.0)


def _limit_display_slopes(values: np.ndarray, *, maximum_delta: float = 0.5, iterations: int = 4) -> np.ndarray:
    """Bound adjacent display heights without touching the measurement surface."""
    limited = values.astype(np.float32).copy()
    for _ in range(iterations):
        for r in range(limited.shape[0]):
            for c in range(1, limited.shape[1]):
                limited[r, c] = np.clip(limited[r, c], limited[r, c - 1] - maximum_delta, limited[r, c - 1] + maximum_delta)
            for c in range(limited.shape[1] - 2, -1, -1):
                limited[r, c] = np.clip(limited[r, c], limited[r, c + 1] - maximum_delta, limited[r, c + 1] + maximum_delta)
        for c in range(limited.shape[1]):
            for r in range(1, limited.shape[0]):
                limited[r, c] = np.clip(limited[r, c], limited[r - 1, c] - maximum_delta, limited[r - 1, c] + maximum_delta)
            for r in range(limited.shape[0] - 2, -1, -1):
                limited[r, c] = np.clip(limited[r, c], limited[r + 1, c] - maximum_delta, limited[r + 1, c] + maximum_delta)
    return limited


def build_display_grid(relative_grid: np.ndarray, guidance_rgb: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Create a traceable visual mesh grid while preserving the canonical grid."""
    source, guidance = np.asarray(relative_grid, dtype=np.float32), np.asarray(guidance_rgb, dtype=np.uint8)
    if source.ndim != 2 or guidance.shape != (*source.shape, 3):
        raise ValueError("Display grid and RGB guidance dimensions must match.")
    cleaned, outlier_count = _remove_isolated_outliers(source)
    smoothed = _joint_bilateral_filter(cleaned, guidance)
    flattened, rooftop_regions, rooftop_pixels = _flatten_rooftop_candidates(smoothed)
    limited = np.clip(_limit_display_slopes(flattened), 0, 1).astype(np.float32)
    diagnostics: dict[str, Any] = {
        "scientific_role": "display geometry only",
        "numeric_surface_unchanged": True,
        "canonical_numeric_source": "relative_surface.npy",
        "canonical_sample_grid": "relative_grid.json",
        "pipeline": [
            "isolated_3x3_robust_outlier_replacement",
            "rgb_and_height_guided_joint_bilateral_radius_2",
            "raised_connected_region_median_rooftop_flattening",
            "display_only_adjacent_slope_limit",
        ],
        "outlier_pixels_replaced": outlier_count,
        "rooftop_regions_flattened": rooftop_regions,
        "rooftop_pixels_flattened": rooftop_pixels,
        "maximum_adjacent_delta_before": _maximum_adjacent_delta(source),
        "maximum_adjacent_delta_after": _maximum_adjacent_delta(limited),
        "maximum_adjacent_delta_limit": 0.5,
        "wall_face_delta_threshold": DISPLAY_WALL_DELTA_THRESHOLD,
        "wall_texture_policy": "neutral synthetic material; no top-down photo sampling",
        "warning": (
            "Filtering, flattening, slope limiting, and wall shading improve display geometry only. "
            "They are not used for relative or metric measurements."
        ),
    }
    return limited, diagnostics


def surface_tilt_diagnostics(relative: np.ndarray) -> dict[str, Any]:
    """Report a dominant image-plane trend without altering the numeric surface."""
    rows = np.linspace(0, relative.shape[0] - 1, min(relative.shape[0], 256)).astype(int)
    cols = np.linspace(0, relative.shape[1] - 1, min(relative.shape[1], 256)).astype(int)
    sampled = relative[np.ix_(rows, cols)].astype(np.float64)
    rg, cg = np.meshgrid(np.linspace(-1, 1, sampled.shape[0]), np.linspace(-1, 1, sampled.shape[1]), indexing="ij")
    values = sampled.ravel()
    design = np.column_stack((np.ones(values.size), rg.ravel(), cg.ravel()))
    coeff, *_ = np.linalg.lstsq(design, values, rcond=None)
    fitted = design @ coeff
    tot_var = float(np.square(values - values.mean()).sum())
    res_var = float(np.square(values - fitted).sum())
    plane_fraction = 0.0 if tot_var <= 1e-12 else 1.0 - res_var / tot_var

    def correlation(axis: np.ndarray) -> float:
        if float(values.std()) <= 1e-12 or float(axis.std()) <= 1e-12:
            return 0.0
        return float(np.corrcoef(values, axis)[0, 1])

    return {
        "method": "least_squares_plane_on_max_256x256_sample",
        "plane_coefficients": {"offset": float(coeff[0]), "normalized_row": float(coeff[1]), "normalized_column": float(coeff[2])},
        "plane_variance_fraction": float(np.clip(plane_fraction, 0.0, 1.0)),
        "row_correlation": correlation(rg.ravel()),
        "column_correlation": correlation(cg.ravel()),
        "warning": ("A dominant image-plane trend is present; it may be monocular perspective bias, not terrain slope." if plane_fraction >= 0.5 else None),
        "correction_applied": False,
    }


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    unique = sorted(set(points))
    if len(unique) <= 2:
        return unique

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def reconstruct_structure_candidates(grid: np.ndarray) -> dict[str, Any]:
    """Find conservative raised components for an optional visual extrusion layer."""
    rows, columns = grid.shape
    rg, cg = np.meshgrid(np.linspace(-1, 1, rows), np.linspace(-1, 1, columns), indexing="ij")
    values = grid.astype(np.float64).ravel()
    design = np.column_stack((np.ones(values.size), rg.ravel(), cg.ravel()))
    coeff, *_ = np.linalg.lstsq(design, values, rcond=None)
    residual = grid.astype(np.float64) - (design @ coeff).reshape(grid.shape)
    threshold = max(float(np.percentile(residual, 82)), 0.035)
    candidate = residual >= threshold
    padded = np.pad(candidate.astype(np.uint8), 1)
    neighbours = sum(padded[ro : ro + rows, co : co + columns] for ro in range(3) for co in range(3))
    candidate &= neighbours >= 4

    visited = np.zeros_like(candidate, dtype=bool)
    min_area = max(4, int(round(candidate.size * 0.0002)))
    max_area = max(min_area, int(round(candidate.size * 0.35)))
    structures: list[dict[str, Any]] = []

    for sr, sc in zip(*np.nonzero(candidate), strict=True):
        if visited[sr, sc]:
            continue
        stack = [(int(sr), int(sc))]
        visited[sr, sc] = True
        comp: list[tuple[int, int]] = []
        while stack:
            r, c = stack.pop()
            comp.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < columns and candidate[nr, nc] and not visited[nr, nc]:
                        visited[nr, nc] = True
                        stack.append((nr, nc))
        if not min_area <= len(comp) <= max_area:
            continue

        c_set = set(comp)
        ring = {
            (r + dr, c + dc)
            for r, c in comp
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if 0 <= r + dr < rows and 0 <= c + dc < columns and (r + dr, c + dc) not in c_set
        }
        roof_rel = float(np.median([grid[r, c] for r, c in comp]))
        base_rel = float(np.median([grid[r, c] for r, c in ring])) if ring else float(np.percentile(grid, 25))
        rel_height = roof_rel - base_rel
        if rel_height < 0.025:
            continue

        fps: list[tuple[float, float]] = []
        for r, c in comp:
            for rc, cc in ((r - 0.5, c - 0.5), (r - 0.5, c + 0.5), (r + 0.5, c - 0.5), (r + 0.5, c + 0.5)):
                fps.append((float(np.clip(cc / max(columns - 1, 1), 0, 1)), float(np.clip(rc / max(rows - 1, 1), 0, 1))))
        hull = _convex_hull(fps)
        if len(hull) < 3:
            continue
        if len(hull) > 16:
            hull = [hull[i] for i in np.linspace(0, len(hull) - 1, 16).astype(int)]

        v_score = float(np.clip(0.35 + 0.35 * rel_height / 0.2 + 0.3 * len(comp) / max(min_area * 8, 1), 0, 0.95))
        structures.append({
            "footprint": [{"x_fraction": pt[0], "y_fraction": pt[1]} for pt in hull],
            "base_relative": float(np.clip(base_rel, 0, 1)),
            "roof_relative": float(np.clip(roof_rel, 0, 1)),
            "relative_height": float(np.clip(rel_height, 0, 1)),
            "pixel_area_on_viewer_grid": len(comp),
            "visual_score": v_score,
        })

    structures.sort(key=lambda item: float(item["relative_height"]) * int(item["pixel_area_on_viewer_grid"]), reverse=True)
    structures = structures[:36]
    for idx, s in enumerate(structures, start=1):
        s["id"] = f"candidate-{idx:02d}"
    return {
        "schema_version": "1.0",
        "method": "detrended_relative_height_components_v1",
        "scientific_role": "optional visual reconstruction candidates",
        "source": "display_grid.json",
        "affects_numeric_dsm": False,
        "candidate_threshold_residual": threshold,
        "minimum_component_area": min_area,
        "score_role": "visual ranking heuristic only; not a calibrated probability",
        "warning": "Candidates come from local relative-height contrast, not semantic building labels. They may include trees or miss low-contrast roofs.",
        "structures": structures,
    }


def write_surface_artifacts(
    job_dir: Path,
    relative: np.ndarray,
    rgb: np.ndarray,
    *,
    raw_model_output: np.ndarray,
    conversion_diagnostics: dict[str, Any],
    tilt_diagnostics: dict[str, Any] | None = None,
    source_kind: str = "model",
) -> list[Artifact]:
    """Write complete evidence bundle and GLB/JSON/PNG artifacts for visual and numeric workflows."""
    if relative.ndim != 2 or relative.shape != rgb.shape[:2]:
        raise ValueError("Surface and texture dimensions must match.")
    if not np.isfinite(relative).all():
        raise ValueError("Surface contains non-finite values.")
    raw_model_output = np.asarray(raw_model_output, dtype=np.float32)
    if raw_model_output.ndim != 2 or raw_model_output.shape != relative.shape:
        raise ValueError("Raw model output and relative height dimensions must match.")
    if source_kind not in {"model", "source_dem"}:
        raise ValueError("Unsupported surface artifact source kind.")

    source_dem = source_kind == "source_dem"
    raw_path = job_dir / ("aligned_source_dem.npy" if source_dem else "raw_model_output.npy")
    np.save(raw_path, raw_model_output, allow_pickle=False)
    surface_path = job_dir / "relative_surface.npy"
    np.save(surface_path, relative.astype(np.float32), allow_pickle=False)
    preview_path = job_dir / "relative_preview.png"
    Image.fromarray(_colourize(relative), mode="RGB").save(preview_path, optimize=True)
    texture_path = job_dir / "texture.png"
    Image.fromarray(rgb.astype(np.uint8), mode="RGB").save(texture_path, optimize=True)
    height_path = job_dir / "relative_height_16bit.png"
    Image.fromarray(np.round(np.clip(relative, 0, 1) * 65535).astype(np.uint16)).save(height_path)

    max_grid_side = 192
    y_index = np.linspace(0, relative.shape[0] - 1, min(relative.shape[0], max_grid_side)).astype(int)
    x_index = np.linspace(0, relative.shape[1] - 1, min(relative.shape[1], max_grid_side)).astype(int)
    grid = relative[np.ix_(y_index, x_index)].astype(float)
    grid_colours = rgb[np.ix_(y_index, x_index)]
    grid_path = job_dir / "relative_grid.json"
    grid_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "shape": list(grid.shape),
            "source_shape": list(relative.shape),
            "row_indices": y_index.tolist(),
            "column_indices": x_index.tolist(),
            "orientation": {"row_zero": "image_top", "column_zero": "image_left"},
            "values": grid.ravel().tolist(),
        }, separators=(",", ":")),
        encoding="utf-8",
    )

    if source_dem:
        display_grid = grid.astype(np.float32).copy()
        display_diagnostics: dict[str, Any] = {
            "processing_mode": "source_dem_faithful",
            "numeric_surface_unchanged": True,
            "outlier_pixels_replaced": 0,
            "rooftop_regions_flattened": 0,
            "rooftop_pixels_flattened": 0,
            "slope_cap_applied": False,
            "reason": "A supplied DEM is already the geometry source; AI-oriented roof cleanup and smoothing are disabled.",
        }
    else:
        display_grid, display_diagnostics = build_display_grid(grid.astype(np.float32), grid_colours)

    display_grid_path = job_dir / "display_grid.json"
    display_grid_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "shape": list(display_grid.shape),
            "source_shape": list(relative.shape),
            "row_indices": y_index.tolist(),
            "column_indices": x_index.tolist(),
            "orientation": {"row_zero": "image_top", "column_zero": "image_left"},
            "scientific_role": "display geometry only",
            "numeric_source": surface_path.name,
            "analysis_grid": grid_path.name,
            "wall_delta_threshold": 2.0 if source_dem else DISPLAY_WALL_DELTA_THRESHOLD,
            "values": display_grid.ravel().tolist(),
        }, separators=(",", ":")),
        encoding="utf-8",
    )

    structure_path = job_dir / "reconstructed_structures.json"
    if not source_dem:
        structure_path.write_text(json.dumps(reconstruct_structure_candidates(display_grid), indent=2), encoding="utf-8")

    glb_path = job_dir / ("terrain_surface.glb" if source_dem else "relative_surface.glb")
    _write_glb(
        glb_path,
        display_grid,
        rgb,
        scientific_state="Metric Source DEM" if source_dem else "Relative",
        units="metre measurements; normalized display geometry" if source_dem else "relative_0_1",
        numeric_source="metric_surface.npy" if source_dem else "relative_surface.npy",
        mesh_name="Source DEM terrain" if source_dem else "Relative surface",
        display_only_processing=True,
        wall_delta_threshold=2.0 if source_dem else DISPLAY_WALL_DELTA_THRESHOLD,
    )

    diagnostic_path = job_dir / ("terrain_diagnostics.json" if source_dem else "height_diagnostics.json")
    diagnostic_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "conversion": conversion_diagnostics,
            ("aligned_source_dem" if source_dem else "raw_model_output"): {
                "filename": raw_path.name,
                "shape": list(raw_model_output.shape),
                "dtype": str(raw_model_output.dtype),
                "preserved_before_height_conversion": not source_dem,
                "source_role": "aligned metric DEM used for terrain geometry" if source_dem else "untouched model prediction",
            },
            "relative_height": {
                "filename": surface_path.name,
                "shape": list(relative.shape),
                "dtype": "float32",
                "minimum": float(relative.min()),
                "maximum": float(relative.max()),
            },
            "geometry": {
                "source": display_grid_path.name,
                "canonical_numeric_source": "metric_surface.npy" if source_dem else surface_path.name,
                "canonical_analysis_grid": grid_path.name,
                "display_processing_changes_measurements": False,
                "colour_preview_is_geometry_source": False,
                "mesh_grid_max_side": max_grid_side,
                "processing": display_diagnostics,
            },
            "global_tilt_indicator": tilt_diagnostics or surface_tilt_diagnostics(relative),
        }, indent=2),
        encoding="utf-8",
    )

    artifacts = [
        _artifact("source_dem_aligned" if source_dem else "raw_model_output", raw_path, "application/octet-stream"),
        _artifact("numeric_surface", surface_path, "application/octet-stream"),
        _artifact("preview", preview_path, "image/png"),
        _artifact("texture", texture_path, "image/png"),
        _artifact("height_texture", height_path, "image/png"),
        _artifact("surface_grid", grid_path, "application/json"),
        _artifact("display_grid", display_grid_path, "application/json"),
        _artifact("glb_mesh", glb_path, "model/gltf-binary"),
        _artifact("height_diagnostics", diagnostic_path, "application/json"),
    ]
    if not source_dem:
        artifacts.append(_artifact("structure_layer", structure_path, "application/json"))
    return artifacts
