"""Explicit assembly and operating paths shared by checking and rendering."""

import math
from dataclasses import asdict, dataclass, replace

from .model import closure_stations


@dataclass(frozen=True)
class State:
    holder_x: float
    assembly_y: float = 0
    film_z: float = 0
    lid_z: float = 0
    clips_out: float = 0
    clips_release: float = 0
    lower_z: float = 0
    cap_z: float = 0
    cap_angle: float = 90
    dock_pin_z: float = 0
    dock_angle: float = 90
    index_release: float = 0
    machine: bool = True
    cartridge: bool = True
    receiver_y: float = 0
    receiver_z: float = 0
    stage_z: float = 0

    def data(self):
        return asdict(self)


def sequences(p):
    first = -p.fmt.centers[0]
    closed = State(first)
    loading = replace(
        closed,
        machine=False,
        film_z=24,
        lid_z=46,
        clips_out=7,
        lower_z=-36,
        cap_z=75,
        cap_angle=0,
        dock_pin_z=9,
        dock_angle=0,
    )
    specs = []

    def phase(group, label, start, **changes):
        end = replace(start, **changes)
        specs.append(
            {"group": group, "label": label, "start": start.data(), "end": end.data()}
        )
        return end

    s = phase("load", "Place the strip against the frame lands", loading, film_z=0)
    s = phase("load", "Lower the full-length lid", s, lid_z=0)
    s = phase("load", "Flex the six clip catches", s, clips_release=0.3)
    s = phase("load", "Slide the six closure clips home", s, clips_out=0)
    s = phase("load", "Release the catches into their recesses", s, clips_release=0)
    s = phase("load", "Seat the holder in its format collar", s, lower_z=0)
    s = phase("load", "Lower the matching mask cap", s, cap_z=0)
    s = phase("load", "Turn the four cap locks", s, cap_angle=90)
    s = replace(closed, cartridge=False, receiver_y=130)
    s = phase("install", "Depress the enlarger's spring stage", s, stage_z=-3)
    s = phase(
        "install", "Align the permanent receiver with the slot", s, receiver_z=-1.5
    )
    s = phase("install", "Slide the receiver to the rear stop", s, receiver_y=0)
    phase("install", "Let the stage seat the receiver", s, receiver_z=0, stage_z=0)
    # The receiver stays in the machine; the dock pins are lifted during travel.
    s = replace(closed, assembly_y=130, dock_pin_z=9, dock_angle=0)
    s = phase("dock", "Slide the prepared cartridge into the receiver", s, assembly_y=0)
    s = phase("dock", "Lower the two front dock pins", s, dock_pin_z=0)
    s = phase("dock", "Turn the pins to retain the collar", s, dock_angle=90)
    phase("dock", "Collar seated; the strip can now advance", s)
    s = closed
    phase("advance", "Frame 1 locked at the mask", s)
    for i, center in enumerate(p.fmt.centers[1:], 2):
        s = phase(
            "advance", f"Retract the index tooth before frame {i}", s, index_release=4
        )
        s = phase("advance", f"Slide to frame {i}", s, holder_x=-center)
        s = phase("advance", f"Frame {i}: release to register", s, index_release=0)
    s = phase("advance", "Release to return to frame 1", s, index_release=4)
    s = phase("advance", "Slide back to the original frame", s, holder_x=first)
    phase("advance", "Frame 1 registered again", s, index_release=0)
    # Removal is the reverse docking path, then daylight disassembly.
    s = phase("remove", "Unlock the collar from the receiver", closed, dock_angle=0)
    s = phase("remove", "Lift the two dock pins", s, dock_pin_z=9)
    phase("remove", "Withdraw the complete cartridge", s, assembly_y=130)
    return specs


def interpolate(phase, t):
    a, b = phase["start"], phase["end"]
    return State(
        **{k: a[k] if isinstance(a[k], bool) else a[k] + (b[k] - a[k]) * t for k in a}
    )


def samples(p, steps=5):
    result = []
    for i, phase in enumerate(sequences(p)):
        # More samples for long translation, fewer for small manual operations.
        travel = max(
            abs(phase["end"][k] - phase["start"][k])
            for k in (
                "holder_x",
                "assembly_y",
                "cap_z",
                "lower_z",
                "lid_z",
                "film_z",
                "receiver_y",
                "receiver_z",
                "stage_z",
            )
        )
        count = max(steps, math.ceil(travel / 5) + 1)
        for j in range(count):
            result.append(
                {
                    "phase": i,
                    "label": phase["label"],
                    "group": phase["group"],
                    "t": j / (count - 1),
                    "state": interpolate(phase, j / (count - 1)).data(),
                }
            )
    return result


def placement(name, p, state):
    """Return translation and rotation about the part's own lock center."""
    y = state.assembly_y
    if name == "receiver":
        return (0, state.receiver_y, state.receiver_z), (0, 0), 0
    if name == "fixture-stage":
        return (0, 0, state.stage_z), (0, 0), 0
    if name.startswith("fixture"):
        return (0, 0, 0), (0, 0), 0
    if name in ("base", "lid", "film") or name.startswith("closure-"):
        z = state.lid_z if name == "lid" else (state.film_z if name == "film" else 0)
        if name.startswith("closure-"):
            side = next(
                side
                for x in closure_stations(p)
                for side in (-1, 1)
                if name == f"closure-{x:g}-{side}"
            )
            y += side * state.clips_out
        return (state.holder_x, y, z), (0, 0), 0
    if name.startswith("cap-lock-"):
        x, cy = next(
            (x, cy)
            for x in (-18, 18)
            for cy in (-31, 31)
            if name == f"cap-lock-{x:g}-{cy:g}"
        )
        return (0, y, state.lower_z), (x, cy), state.cap_angle
    if name.startswith("dock-lock-"):
        x = -18 if name == "dock-lock--18" else 18
        return (
            (0, y, state.lower_z + state.dock_pin_z),
            (x, 48),
            state.dock_angle + (90 if x > 0 else 0),
        )
    z = state.cap_z if name == "collar-cap" else state.lower_z
    return (0, y, z), (0, 0), 0
