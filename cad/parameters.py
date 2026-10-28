"""Millimetre configuration and capacity calculations; no CAD runtime required.

The capacity quadrature and recipe rounding preserve the established v1.8 design.
"""

import math

DEFAULTS = {
    "roll_width": 102,
    "image_aspect": 16 / 9,
    "paper_thickness": 0.3,
    "finger_grip": 8,
    "vertical_stroke": 6,
    "lateral_stroke": 3,
    "immersion_margin": 2,
    "side_clearance": 10,
    "bottom_clearance": 4,
    "bath_gap": 14,
    "freeboard": 7,
    "wall": 3,
    "floor": 4,
    "inside_radius": 2,
    "rim_overhang": 1.8,
    "rim_height": 2,
    "guide_gap": 1.2,
    "guide_thickness": 3,
    "guide_fit": 0.35,
    "guide_skirt": 2,
    "drip_depth": 1.5,
    "wiping_land": 0.4,
    "sight_depth": 1.5,
    "well_bore": 8,
    "well_mouth": 16,
    "well_wall": 2.4,
    "well_flare": 9,
    "recipe_a_concentrate": 1,
    "recipe_a_water": 4,
    "recipe_b_concentrate": 1,
    "recipe_b_water": 4,
    "rounding_limit": 2,
    "module_gap": 2,
    "cradle_floor": 4,
    "cradle_clearance": 0.6,
    "bed_margin": 3,
    "height_margin": 2,
    "print_tilt": 44.2,
}


def clamp(v, lo, hi):
    return min(hi, max(lo, v))


def well_at(p, z):
    if z <= p["pool_z"]:
        return p["well_cx"] - (p["pool_z"] - z), p["well_bore"] / 2
    t = clamp((z - p["pool_z"]) / p["well_flare"], 0, 1)
    return p["well_cx"], p["well_bore"] / 2 + (
        p["well_mouth"] - p["well_bore"]
    ) / 2 * t * t * (3 - 2 * t)


def well_volume(p, level):
    volume = 0
    for a, b in zip(p["well_stations"], p["well_stations"][1:]):
        if level <= a[0]:
            break
        dz = (min(level, b[0]) - a[0]) / 12
        for i in range(12):
            t = (i + 0.5) * dz / (b[0] - a[0])
            cx, r = a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t
            x = p["body_width"] - p["wall"] - cx
            area = (
                math.pi * r * r
                if x <= -r
                else 0
                if x >= r
                else r * r * math.acos(x / r) - x * math.sqrt(max(0, r * r - x * x))
            )
            volume += dz * area
    return volume


def capacity(p, level):
    w, d, r, h = p["inner_width"], p["bath_gap"], p["inside_radius"], level - p["floor"]
    if h <= 0:
        bath = 0
    elif h < r:
        bath = 0
        for i in range(80):
            z = (i + 0.5) * h / 80
            inset = r - math.sqrt(max(0, r * r - (r - z) ** 2))
            bath += (
                h
                / 80
                * ((w - 2 * inset) * (d - 2 * inset) - (4 - math.pi) * (r - inset) ** 2)
            )
    else:
        bath = (
            (w * d - (4 - math.pi) * r * r) * (h - r)
            + (w - 2 * r) * (d - 2 * r) * r
            + (w + d - 4 * r) * math.pi * r * r / 2
            + 2 * math.pi * r**3 / 3
        )
    stop_h = p["bottom_clearance"] - 2
    cap = clamp(level - p["floor"] - stop_h, 0, 2)
    stops = 2 * (
        math.pi * 4 * clamp(level - p["floor"], 0, stop_h)
        + math.pi * (4 * cap - cap**3 / 3)
    )
    return bath - stops + well_volume(p, level)


def displacement(p, level, lift=0):
    return (
        p["roll_width"]
        * p["paper_thickness"]
        * clamp(level - p["paper_bottom"] - lift, 0, p["paper_cut_length"])
    )


def level_for_volume(p, volume, loaded=False, lift=0):
    lo, hi = p["floor"], p["body_height"]
    for _ in range(24):
        mid = (lo + hi) / 2
        if capacity(p, mid) - (displacement(p, mid, lift) if loaded else 0) < volume:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def parameters(**overrides):
    unknown = overrides.keys() - DEFAULTS.keys()
    if unknown:
        raise ValueError(f"Unknown parameters: {sorted(unknown)}")
    p = DEFAULTS | overrides
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in p.values()):
        raise ValueError("All parameters must be finite numbers")

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(p["roll_width"] > 40 and 1 <= p["image_aspect"] <= 3, "Invalid paper size")
    require(
        p["paper_thickness"] > 0 and p["guide_gap"] >= p["paper_thickness"] + 0.2,
        "Guide gap must clear paper",
    )
    require(
        p["vertical_stroke"] >= 0
        and p["lateral_stroke"] >= 0
        and p["immersion_margin"] >= 1,
        "Invalid agitation",
    )
    require(
        p["side_clearance"] >= p["lateral_stroke"] + 3
        and p["bath_gap"] >= p["well_bore"] + 2,
        "Insufficient bath clearance",
    )
    require(
        p["wall"] >= 2.4
        and p["floor"] >= 3
        and 0 < p["inside_radius"] < p["bath_gap"] / 2,
        "Invalid wall or floor",
    )
    require(
        p["bottom_clearance"] >= 4 and p["freeboard"] >= 7 and p["finger_grip"] >= 6,
        "Insufficient paper clearance",
    )
    require(
        0.15 <= p["guide_fit"] <= 0.7 and 0 < p["guide_skirt"] < p["freeboard"] - 1,
        "Invalid guide fit",
    )
    require(
        p["drip_depth"] >= 1
        and p["wiping_land"] > 0
        and p["drip_depth"] + p["wiping_land"] < p["guide_thickness"],
        "Invalid guide taper",
    )
    require(
        p["well_mouth"] >= p["well_bore"] >= 6
        and p["well_wall"] >= 2
        and p["well_flare"] > 0,
        "Invalid well",
    )
    require(
        0.3 <= p["cradle_clearance"] <= 1
        and p["cradle_floor"] >= 3
        and p["module_gap"] >= 0,
        "Invalid base",
    )
    require(
        40 <= p["print_tilt"] <= 45
        and p["bed_margin"] >= 3
        and p["height_margin"] >= 2,
        "Invalid print reserve",
    )
    for letter in "ab":
        parts = [p[f"recipe_{letter}_{key}"] for key in ("concentrate", "water")]
        require(
            all(v > 0 and int(v) == v for v in parts),
            "Recipe parts must be positive integers",
        )
        p[f"recipe_{letter}"] = list(map(int, parts))
    p["image_length"] = p["roll_width"] * p["image_aspect"]
    p["inner_width"] = p["roll_width"] + 2 * p["side_clearance"]
    p["body_width"] = p["inner_width"] + 2 * p["wall"]
    p["body_depth"] = p["bath_gap"] + 2 * p["wall"]
    p["paper_bottom"] = p["floor"] + p["bottom_clearance"]
    p["image_top"] = p["paper_bottom"] + p["image_length"]
    p["target_loaded_level"] = (
        p["image_top"] + p["vertical_stroke"] + p["immersion_margin"]
    )
    p["body_height"] = p["target_loaded_level"] + p["freeboard"]
    p["guide_top"] = p["body_height"] + p["guide_thickness"]
    p["paper_cut_length"] = math.ceil(
        p["guide_top"] + p["finger_grip"] - p["paper_bottom"]
    )
    p["paper_top"] = p["paper_bottom"] + p["paper_cut_length"]
    p["trim_band"] = p["paper_cut_length"] - p["image_length"]
    p["guide_width"] = p["body_width"] + 2 * (p["rim_overhang"] + p["guide_fit"])
    p["guide_depth"] = p["body_depth"] + p["rim_overhang"] + p["guide_fit"]
    p["slit_length"] = p["roll_width"] + 2 * (p["lateral_stroke"] + 1)
    area = p["inner_width"] * p["bath_gap"] - (4 - math.pi) * p["inside_radius"] ** 2
    p["pool_z"] = (
        p["target_loaded_level"]
        - p["roll_width"]
        * p["paper_thickness"]
        * (p["target_loaded_level"] - p["paper_bottom"])
        / area
        - p["sight_depth"]
    )
    p["well_cx"] = p["body_width"] + p["well_bore"] / 2 + p["wall"]
    p["well_cy"] = p["body_depth"] / 2
    p["well_exit_z"] = p["pool_z"] - (
        p["well_cx"] - (p["body_width"] - p["wall"] - p["well_bore"] / 2)
    )
    p["well_top"] = p["body_height"]
    zs = [
        p["well_exit_z"] + (p["pool_z"] - p["well_exit_z"]) * i / 16 for i in range(17)
    ]
    zs += [p["pool_z"] + (p["well_top"] - p["pool_z"]) * i / 16 for i in range(1, 17)]
    p["well_stations"] = [[z, *well_at(p, z)] for z in zs]
    p["vessel_xmax"] = p["well_cx"] + p["well_mouth"] / 2 + p["well_wall"]
    p["cradle_width"] = p["body_width"] + 2 * (p["vessel_xmax"] - p["body_width"]) + 8
    # Preserve the shared footprint and future heater interfaces of v1.8.
    p.update(
        cradle_depth=max(68, p["body_depth"] + 48),
        vessel_y=24,
        clip_width=12,
        socket_wall=3,
        socket_height=32,
    )
    p["vessel_pitch"] = p["cradle_depth"] + p["module_gap"]
    p["base_width"] = p["cradle_width"]
    p["base_depth"] = 2 * p["cradle_depth"] + p["module_gap"]
    p["vessel_x"] = (p["cradle_width"] - p["body_width"]) / 2
    p["nominal_ml"] = (
        capacity(p, p["target_loaded_level"])
        - displacement(p, p["target_loaded_level"])
    ) / 1000
    p["min_ml"] = (
        max(
            capacity(p, p["pool_z"] + 0.5),
            capacity(p, p["image_top"] + p["vertical_stroke"] + 1)
            - displacement(p, p["image_top"] + p["vertical_stroke"] + 1),
        )
        / 1000
        + 0.12
    )
    p["max_ml"] = (
        min(
            capacity(p, p["pool_z"] + 2.5),
            capacity(p, p["body_height"] - 6) - displacement(p, p["body_height"] - 6),
        )
        / 1000
        - 0.12
    )
    batch = sum(p["recipe_a"]) // math.gcd(*p["recipe_a"])
    exact = math.floor(p["nominal_ml"] / batch + 0.5) * batch
    p["working_ml"] = (
        exact
        if abs(exact - p["nominal_ml"]) <= p["rounding_limit"]
        and p["min_ml"] <= exact <= p["max_ml"]
        else clamp(
            math.floor(p["nominal_ml"] + 0.5),
            math.ceil(p["min_ml"]),
            math.floor(p["max_ml"]),
        )
    )
    p["empty_level"] = level_for_volume(p, p["working_ml"] * 1000)
    p["loaded_level"] = level_for_volume(p, p["working_ml"] * 1000, True)
    for letter in "ab":
        first = math.floor(
            p["working_ml"] * p[f"recipe_{letter}"][0] / sum(p[f"recipe_{letter}"])
            + 0.5
        )
        p[f"amounts_{letter}"] = [first, p["working_ml"] - first]
    p["actual_sight_depth"] = p["empty_level"] - p["pool_z"]
    p["visible_pool_ml"] = (
        well_volume(p, p["empty_level"]) - well_volume(p, p["pool_z"])
    ) / 1000
    a = math.radians(p["print_tilt"])
    p["vessel_print_bounds"] = [
        p["vessel_xmax"] + p["rim_overhang"],
        p["body_height"] * math.sin(a)
        + (p["body_depth"] + p["rim_overhang"]) * math.cos(a),
        p["body_height"] * math.cos(a)
        + max(p["body_depth"], p["well_cy"] + p["well_mouth"] / 2 + p["well_wall"])
        * math.sin(a),
    ]
    p["build_size"] = [180, 180, 180]
    p["usable_xy"] = [180 - 2 * p["bed_margin"]] * 2
    p["usable_z"] = 180 - p["height_margin"]
    require(p["body_depth"] >= p["well_mouth"] + 4, "Well needs a flat rear wall")
    require(
        p["pool_z"] + p["well_flare"] <= p["well_top"]
        and p["well_exit_z"] > p["floor"] + p["inside_radius"],
        "Well exceeds vessel",
    )
    require(
        p["min_ml"] <= p["working_ml"] <= p["max_ml"]
        and abs(p["working_ml"] - p["nominal_ml"]) <= p["rounding_limit"],
        "No safe rounded fill",
    )
    require(
        p["loaded_level"] >= p["image_top"] + p["vertical_stroke"] + 1
        and p["body_height"] - p["loaded_level"] >= 6,
        "Insufficient immersion/freeboard",
    )
    require(0.5 <= p["actual_sight_depth"] <= 2.5, "Invalid fill cue")
    require(
        p["base_width"] <= p["usable_xy"][0] and p["base_depth"] <= p["usable_xy"][1],
        "Shared base exceeds reserved A1 mini area",
    )
    require(
        all(
            v <= limit
            for v, limit in zip(
                p["vessel_print_bounds"], p["usable_xy"] + [p["usable_z"]]
            )
        ),
        "Vessel exceeds reserved A1 mini area",
    )
    return p
