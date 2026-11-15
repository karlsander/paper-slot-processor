"""Millimetres; paper thickness is a user-adjustable assumption."""

import math

DEFAULTS = {
    "paper_width": 102,
    "paper_thickness": 0.3,
    "paper_side_clearance": 0.3,
    "guide_height": 0.2,
    "deck_thickness": 4,
    "end_allowance": 20,
    "side_shelf": 14,
    "outer_rail_width": 4,
    "outer_rail_height": 1.6,
    "mask_thickness": 4.8,
    "mask_edge_land": 0.8,
    "mask_bevel": 3.2,
    "mask_side_clearance": 0.4,
    "magnet_diameter": 6,
    "magnet_thickness": 3,
    "magnet_diameter_clearance": 0.3,
    "magnet_depth_clearance": 0.2,
    "locator_diameter": 3.2,
    "locator_height": 2,
    "locator_clearance": 0.5,
    "band_width": 30,
    "minimum_last_band": 8,
    "cover_thickness": 2.8,
    "cover_lap": 0.8,
    "cover_lap_height": 1,
    "cover_clearance": 0.2,
    "joint_clearance": 0.2,
    "joint_depth": 8,
}


def parameters(**overrides):
    if overrides.keys() - DEFAULTS.keys():
        raise ValueError(f"Unknown dimensions: {overrides.keys() - DEFAULTS.keys()}")
    p = DEFAULTS | overrides
    for key, value in p.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{key} must be finite and positive")

    def require(test, message):
        if not test:
            raise ValueError(message)

    p.update(
        image_169=p["paper_width"] * 16 / 9,
        image_43=p["paper_width"] * 4 / 3,
        channel_width=p["paper_width"] + 2 * p["paper_side_clearance"],
        paper_z=p["deck_thickness"] + p["paper_thickness"],
    )
    p["base_length"] = p["image_169"] + 2 * p["end_allowance"]
    p["base_width"] = p["channel_width"] + 2 * p["side_shelf"]
    p["rail_inner"] = p["base_width"] / 2 - p["outer_rail_width"]
    p["mask_width"] = 2 * (p["rail_inner"] - p["mask_side_clearance"])
    p["mask_top"] = p["paper_z"] + p["mask_thickness"]
    p["magnet_x"] = p["base_length"] / 2 - 14
    p["locator_x"] = p["base_length"] / 2 - 4
    p["attachment_y"] = p["channel_width"] / 2 + 5.1
    p["cover_end"] = p["base_width"] / 2 + 8
    p["cover_bottom"] = p["deck_thickness"] + p["outer_rail_height"]
    require(80 <= p["paper_width"] <= 105, "Paper width outside 80–105 mm")
    require(0.25 <= p["paper_thickness"] <= 0.6, "Measure paper thickness: 0.25–0.6 mm")
    require(
        p["guide_height"] <= p["paper_thickness"] - 0.05 + 1e-9,
        "Guides must stay below emulsion",
    )
    for key, lo, hi in [
        ("paper_side_clearance", 0.15, 0.6),
        ("end_allowance", 20, 23),
        ("mask_side_clearance", 0.25, 0.6),
        ("magnet_diameter_clearance", 0.1, 0.5),
        ("magnet_depth_clearance", 0.1, 0.3),
        ("cover_thickness", 2.8, 4),
        ("cover_lap", 0.6, 1),
        ("cover_clearance", 0.15, 0.3),
        ("joint_clearance", 0.15, 0.35),
    ]:
        require(lo <= p[key] <= hi, f"{key} outside supported range")
    require(
        p["deck_thickness"]
        >= p["magnet_thickness"] + p["magnet_depth_clearance"] + 0.8,
        "Magnet floor too thin",
    )
    require(
        p["mask_thickness"]
        >= p["magnet_thickness"] + p["magnet_depth_clearance"] + 1.4,
        "Mask pocket roof too thin",
    )
    require(
        p["mask_edge_land"] >= 0.8
        and p["mask_bevel"] <= p["mask_thickness"] - p["mask_edge_land"],
        "Invalid mask bevel",
    )
    require(
        p["magnet_diameter"] == 6 and p["magnet_thickness"] == 3,
        "Layout requires 6 x 3 mm magnets",
    )
    require(
        p["mask_width"] / 2
        - p["attachment_y"]
        - (p["magnet_diameter"] + p["magnet_diameter_clearance"]) / 2
        >= 1.2,
        "Pocket breaks mask edge",
    )
    require(
        p["locator_height"] + 0.3 < p["mask_thickness"]
        and p["locator_clearance"] >= 0.3,
        "Invalid locating pin clearance",
    )
    require(p["cover_bottom"] - p["paper_z"] >= 0.6, "Cover too close to paper")
    require(
        p["cover_bottom"] + p["cover_thickness"] < p["mask_top"],
        "Mask must stop covers",
    )
    require(
        p["band_width"] >= 24
        and p["image_43"] - 4 * p["band_width"] >= p["minimum_last_band"] >= 8,
        "No usable fifth band",
    )
    require(
        p["cover_lap_height"] >= 0.8
        and p["cover_lap_height"] + p["cover_clearance"] < p["cover_thickness"],
        "Invalid lap height",
    )
    require(
        p["base_length"] / 2 + p["joint_depth"] <= 174
        and p["base_width"] <= 174
        and p["band_width"] + p["cover_lap"] <= 174
        and 2 * p["cover_end"] <= 174,
        "Plate exceeds A1 mini margins",
    )
    return p


def image_length(p, fmt):
    if fmt not in ("16:9", "4:3"):
        raise ValueError("Unknown format")
    return p["image_169"] if fmt == "16:9" else p["image_43"]
