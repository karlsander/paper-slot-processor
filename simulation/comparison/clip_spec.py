"""Fixed comparison fixture based on v2/guide.scad retaining_clip().

Root rounding is an experimental comparison feature, not a production change.
"""

from dataclasses import dataclass, replace
from itertools import product
from math import isfinite


@dataclass(frozen=True)
class Clip:
    width: float = 12
    depth: float = 9
    height: float = 9
    corner_radius: float = 1
    spine: float = 2
    lower_jaw: float = 1.8
    gap: float = 5.4
    lower_reach: float = 3.8
    root_radius: float = 0

    def validate(self):
        if not all(
            isfinite(v) and v > 0 for k, v in vars(self).items() if k != "root_radius"
        ):
            raise ValueError("Dimensions must be finite and positive")
        if not isfinite(self.root_radius) or self.root_radius < 0:
            raise ValueError("Root radius must be finite and nonnegative")
        if 2 * self.corner_radius >= min(self.width, self.depth):
            raise ValueError("Corner radius consumes the outer profile")
        if self.lower_jaw + self.gap >= self.height:
            raise ValueError("Opening must leave an upper jaw")
        if not self.spine < self.lower_reach < self.depth:
            raise ValueError("Lower jaw must project beyond the spine")


def cases():
    regular = [("default", Clip())]
    regular += [
        (f"grid-{i:02d}", Clip(width=w, gap=g, root_radius=r))
        for i, (w, g, r) in enumerate(
            product((8, 12, 20), (4.6, 5.4, 6.2), (0, 0.3, 0.8))
        )
    ]
    regular += [(f"outer-{r}", Clip(corner_radius=r)) for r in (0.2, 1.8, 3.8)]
    regular += [(f"spine-{v}", Clip(spine=v, root_radius=0.3)) for v in (1.4, 2.8)]
    regular += [(f"jaw-{v}", Clip(lower_jaw=v, root_radius=0.3)) for v in (1.2, 2.4)]
    stress = [(f"root-limit-{r}", Clip(root_radius=r)) for r in (1.6, 2.6, 3.2)]
    return regular, stress


def invalid_cases():
    return [
        replace(Clip(), **change)
        for change in (
            {"width": -1},
            {"gap": 7.2},
            {"corner_radius": 4.5},
            {"spine": 4},
            {"root_radius": -0.1},
            {"width": float("nan")},
        )
    ]
