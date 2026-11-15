"""Explicit concept assumptions and independently testable optical geometry."""

from dataclasses import asdict, dataclass
from itertools import pairwise
from math import cos, isfinite, radians, sin


@dataclass(frozen=True)
class Format:
    key: str
    label: str
    film_width: float
    image_width: float  # along strip travel, not the printed image orientation
    image_height: float
    demo_pitch: float
    frames: int
    pitch_status: str

    @property
    def centers(self):
        return tuple(
            (i - (self.frames - 1) / 2) * self.demo_pitch for i in range(self.frames)
        )

    @property
    def length(self):
        return self.frames * self.demo_pitch + 16

    @property
    def travel(self):
        return self.centers[-1] - self.centers[0]

    @property
    def aperture(self):
        # A small illustrative crop, not a final photographic mask specification.
        return self.image_width - 0.4, self.image_height - 0.4

    def data(self):
        return asdict(self) | {
            "centers": self.centers,
            "length": self.length,
            "travel": self.travel,
            "aperture": self.aperture,
            "enclosed_length": self.length + self.travel + 16,
        }


FORMATS = {
    f.key: f
    for f in (
        Format(
            "135",
            "35 mm full frame",
            35,
            36,
            24,
            38,
            6,
            "nominal template; verify actual strips",
        ),
        Format(
            "half",
            "35 mm half frame",
            35,
            18,
            24,
            19,
            12,
            "nominal template; camera-specific image width",
        ),
        Format(
            "aps",
            "APS",
            24,
            30.2,
            16.7,
            32,
            6,
            "illustrative spacing only; not a sourced standard",
        ),
        Format(
            "110",
            "110",
            16,
            17,
            13,
            20,
            6,
            "illustrative spacing only; not a sourced standard",
        ),
    )
}

VARIANTS = {
    "drawer": "A · Separate mask drawer",
    "collar": "B · Captive mask collar",
    "cassette": "C · Enclosed translating cassette",
}


def validate_centers(centers, image_width):
    if len(centers) < 2 or not all(isfinite(c) for c in centers):
        raise ValueError("At least two finite frame centers are required")
    if not isfinite(image_width) or image_width <= 0:
        raise ValueError("Image width must be positive")
    if any(b - a <= image_width for a, b in pairwise(centers)):
        raise ValueError("Frame centers must increase with a positive image gap")


def visible_area(center, width, height, aperture):
    """Normal-ray intersection of one image with a centered rectangular gate."""
    aw, ah = aperture
    overlap = max(
        0.0, min(center + width / 2, aw / 2) - max(center - width / 2, -aw / 2)
    )
    return overlap * min(height, ah)


def optical_check(fmt, centers=None, aperture=None):
    centers = tuple(fmt.centers if centers is None else centers)
    validate_centers(centers, fmt.image_width)
    aperture = fmt.aperture if aperture is None else aperture
    if not all(isfinite(v) and v > 0 for v in aperture):
        raise ValueError("Aperture dimensions must be positive")
    samples = []
    for selected, origin in enumerate(centers):
        areas = [
            visible_area(c - origin, fmt.image_width, fmt.image_height, aperture)
            for c in centers
        ]
        neighbours = sum(a for i, a in enumerate(areas) if i != selected)
        samples.append(
            {
                "frame": selected + 1,
                "translation": -origin,
                "selected_area_mm2": areas[selected],
                "neighbour_area_mm2": neighbours,
            }
        )
    return samples


def minimum_square_bed(length, width):
    """Numerical in-plane rectangle packing; excludes brim and other margins."""
    return min(
        max(
            length * cos(radians(a / 10)) + width * sin(radians(a / 10)),
            length * sin(radians(a / 10)) + width * cos(radians(a / 10)),
        )
        for a in range(901)
    )


def summary():
    return {
        "evidence_level": "architecture and nominal rigid envelopes only",
        "physical_fit_verified": False,
        "repeatability_measured": False,
        "film_clamping_verified": False,
        "coordinates": "X strip travel; Y front/rear of enlarger; Z optical axis; film centered at Z=0",
        "gate_stack_mm": 4.7,
        "gate_stack_status": "concept allocation; C35 available clearance unknown",
        "formats": {
            k: f.data()
            | {
                "optical_samples": optical_check(f),
                "minimum_square_bed_mm": minimum_square_bed(f.length, 56),
            }
            for k, f in FORMATS.items()
        },
        "negative_control_110_with_35mm_gate": optical_check(
            FORMATS["110"], aperture=(36, 24)
        ),
        "variants": VARIANTS,
    }
