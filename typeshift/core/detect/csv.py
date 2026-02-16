"""CSV platform detection."""

from app.services.csv_importers.detection import DETECTABLE_PLATFORMS, detect_csv_platform

__all__ = ["DETECTABLE_PLATFORMS", "detect_csv_platform"]
