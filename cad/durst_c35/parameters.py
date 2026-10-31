"""Millimetres; provisional dimensions are identified in docs/durst-c35/README.md."""

import math

DEFAULTS = {
    "window_x": 36.0,
    "window_y": 24.0,
    "film_width": 35.0,
    "body_width": 94.6,
    "b_rear_margin": 42.0,
    "a_rear_margin": 32.0,
    "front_margin": 34.0,
    "front_lip": 4.0,
    "body_corner_radius": 2.5,
    "outer_height_a": 13.5,
    "outer_height_b": 13.5,
    "sheet_thickness": 1.2,
    "side_wall": 1.2,
    "lip_thickness": 1.2,
    "window_rim_height": 2.5,
    "window_rim_width": 2.0,
    "film_gap": 0.20,
    "aperture_land": 0.4,
    "aperture_flare": 1.2,
    "b_aperture_relief": 0.8,
    "b_corner_inset_length": 1.8,
    "film_pin_spacing": 58.0,
    "film_pin_diameter": 1.6,
    "film_pin_height": 1.2,
    "film_pin_tip_height": 0.35,
    "b_pin_recess_mouth": 6.0,
    "b_pin_recess_bottom": 2.6,
    "b_pin_recess_depth": 1.3,
    "b_pin_floor": 0.6,
    "b_pin_boss_wall": 0.8,
    "hinge_ear_height": 10.0,
    "hinge_ear_width": 7.0,
    "hinge_hole_from_root": 7.0,
    "hinge_ear_thickness": 1.8,
    "hinge_side_clearance": 0.35,
    "hinge_pin_diameter": 2.4,
    "hinge_hole_diameter": 2.9,
    "hinge_tip_engagement": 0.35,
    "hinge_pin_tip_length": 0.4,
}


def parameters(**overrides):
    unknown = overrides.keys() - DEFAULTS.keys()
    if unknown:
        raise ValueError(f"Unknown carrier parameters: {sorted(unknown)}")
    p = DEFAULTS | overrides
    for key, value in p.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{key} must be a finite positive number")

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(
        p["aperture_land"] < p["sheet_thickness"] < p["window_rim_height"],
        "The sheet must be thinner than the local window rim and thicker than its aperture land",
    )
    require(
        p["window_rim_height"] < min(p["outer_height_a"], p["outer_height_b"]),
        "Window rim must be below side edges",
    )
    require(
        p["a_rear_margin"] < p["b_rear_margin"],
        "A rear edge must clear the hinge sweep",
    )
    require(
        p["hinge_pin_diameter"] < p["hinge_hole_diameter"],
        "Hinge needs diametral clearance",
    )
    require(
        p["hinge_hole_diameter"] + 2 < p["hinge_ear_width"],
        "Hinge ear needs material around hole",
    )
    require(
        p["hinge_hole_from_root"] + p["hinge_hole_diameter"] / 2 + 0.6
        < p["hinge_ear_height"],
        "Hinge hole breaks through ear tip",
    )
    require(
        p["hinge_hole_from_root"] + p["hinge_hole_diameter"] / 2 < p["outer_height_a"],
        "Hinge axis outside support",
    )
    require(
        p["film_gap"] < p["film_pin_height"] < p["film_gap"] + p["b_pin_recess_depth"],
        "Film pin must enter blind recess without bottoming",
    )
    require(p["film_pin_tip_height"] < p["film_pin_height"], "Film pin tip too long")
    require(
        p["b_pin_recess_bottom"] > p["film_pin_diameter"], "Film pin recess too narrow"
    )
    require(
        p["b_pin_recess_mouth"] >= p["b_pin_recess_bottom"],
        "Recess must widen toward film",
    )
    require(
        p["b_corner_inset_length"] < min(p["window_x"], p["window_y"]) / 2,
        "Corner insets consume aperture edges",
    )
    require(
        p["front_margin"] > 15 and p["body_corner_radius"] > p["side_wall"],
        "Insufficient front/side geometry",
    )
    p.update(
        window_center_y=p["b_rear_margin"] + p["window_y"] / 2,
        body_front_y=p["b_rear_margin"] + p["window_y"] + p["front_margin"],
        a_plate_rear_y=p["b_rear_margin"] - p["a_rear_margin"],
        hinge_y=-p["hinge_ear_width"] / 2,
        hinge_z=p["film_gap"] - p["hinge_hole_from_root"],
        skirt_inner_x=p["body_width"] / 2 - p["side_wall"],
        b_pin_boss_height=max(
            p["sheet_thickness"], p["b_pin_recess_depth"] + p["b_pin_floor"]
        ),
    )
    p["ear_outer_x"] = p["skirt_inner_x"] - p["hinge_side_clearance"]
    p["ear_inner_x"] = p["ear_outer_x"] - p["hinge_ear_thickness"]
    p["hinge_pin_length"] = (
        p["hinge_side_clearance"] + p["hinge_ear_thickness"] + p["hinge_tip_engagement"]
    )
    p["film_pin_y"] = (
        p["window_center_y"] - p["film_width"] / 2 - p["film_pin_diameter"] / 2
    )
    require(p["hinge_pin_tip_length"] < p["hinge_pin_length"], "Hinge pin tip too long")
    require(
        p["body_width"]
        > p["film_pin_spacing"] + p["b_pin_recess_mouth"] + 2 * p["side_wall"],
        "Film pin bosses meet side walls",
    )
    require(
        p["film_pin_spacing"] / 2 - p["b_pin_recess_mouth"] / 2 - p["b_pin_boss_wall"]
        > p["window_x"] / 2
        + p["b_aperture_relief"]
        + p["aperture_flare"]
        + p["window_rim_width"],
        "Pin bosses meet window rim",
    )
    return p
