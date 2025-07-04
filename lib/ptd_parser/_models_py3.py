from dataclasses import dataclass, field
from typing import List, Tuple

__all__ = [
    "TendonPoint",
    "TendonData",
    "TendonSet",
]


@dataclass
class TendonPoint:
    """High/low profile point along a tendon span."""

    distance_mm: float  # Distance from live-end
    height_mm: int  # Height (positive up) relative to soffit


@dataclass
class TendonData:
    """Main tendon record extracted from a PTD export."""

    id: int
    length_mm: float
    start_xy_mm: Tuple[float, float]
    end_xy_mm: Tuple[float, float]
    tendon_type: int  # 1 = straight, 2 = pan (per PTD spec)
    strand_type: float  # e.g. 12.7, 15.2
    strand_count: int
    start_type: int = 1  # 1=stress, 2=pan, 3=dead
    end_type: int = 3  # 1=stress, 2=pan, 3=dead
    points: List["TendonPoint"] = field(default_factory=list)

    def add_point(self, point: "TendonPoint") -> None:
        self.points.append(point)


@dataclass
class TendonSet:
    """Simple container for multiple tendons."""

    tendons: List["TendonData"] = field(default_factory=list)

    def append(self, tendon: "TendonData") -> None:
        self.tendons.append(tendon)

    def __iter__(self):
        return iter(self.tendons)

    def __len__(self):
        return len(self.tendons) 