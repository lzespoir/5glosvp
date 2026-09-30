from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from .models import RadioGeometry


class GeometryError(ValueError):
    """A geometry request cannot be interpreted in the declared coordinate system."""


def _xyz(value: Mapping[str, object] | Sequence[float]) -> tuple[float, float, float]:
    if isinstance(value, Mapping):
        try:
            return float(value["x"]), float(value["y"]), float(value["z"])
        except (KeyError, TypeError, ValueError) as exc:
            raise GeometryError("POSITION_INVALID: expected x/y/z") from exc
    if len(value) != 3:
        raise GeometryError("POSITION_INVALID: expected three Cartesian coordinates")
    return float(value[0]), float(value[1]), float(value[2])


def compute_radio_geometry(
    aau_position: Mapping[str, object] | Sequence[float],
    ue_position: Mapping[str, object] | Sequence[float],
    convention: str = "SIONNA_SCENE_CARTESIAN",
) -> RadioGeometry:
    """Compute the relative direction from an AAU to a UE in Cartesian space."""
    ax, ay, az = _xyz(aau_position)
    ux, uy, uz = _xyz(ue_position)
    dx, dy, dz = ux - ax, uy - ay, uz - az
    distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    if distance <= 1e-12:
        raise GeometryError("SAME_POSITION: AAU and UE positions coincide")
    horizontal = math.hypot(dx, dy)
    azimuth = math.degrees(math.atan2(dy, dx)) % 360.0
    elevation = math.degrees(math.atan2(dz, horizontal))
    return RadioGeometry(
        distance_3d_m=distance,
        azimuth_deg=azimuth,
        elevation_deg=elevation,
        coordinate_convention=convention,
    )
