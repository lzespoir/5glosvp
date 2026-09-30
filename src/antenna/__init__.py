"""Day 13 read-only antenna and A-Matrix domain services."""

from .amatrix_adapter import AMatrixAdapter, AMatrixDataError
from .geometry import compute_radio_geometry
from .models import AngularGrid, AMatrixEntry, AMatrixLibrary, BeamResponse, RadioGeometry

__all__ = [
    "AMatrixAdapter",
    "AMatrixDataError",
    "AMatrixEntry",
    "AMatrixLibrary",
    "AngularGrid",
    "BeamResponse",
    "RadioGeometry",
    "compute_radio_geometry",
]
