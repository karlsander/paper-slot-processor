include <parameters.scad>

// Coordinates: X follows the roll; Y spans its width; Z=0 is the baseboard.
module box_at(x, y, z, dx, dy, dz) { translate([x, y, z]) cube([dx, dy, dz]); }

module dovetail_2d() {
    for (y = [-base_width / 4, base_width / 4])
        translate([0, y]) polygon([[-1, -7], [0, -7], [joint_depth, -10],
                                  [joint_depth, 10], [0, 7], [-1, 7]]);
}

module half_outline(left=true) {
    if (left) union() {
        translate([-base_length / 2, -base_width / 2]) square([base_length / 2, base_width]);
        dovetail_2d();
    } else difference() {
        translate([joint_clearance, -base_width / 2])
            square([base_length / 2 - joint_clearance, base_width]);
        offset(delta=joint_clearance) dovetail_2d();
    }
}

module full_deck() {
    difference() {
        union() {
            box_at(-base_length / 2, -base_width / 2, 0, base_length, base_width, deck_thickness);
            for (s = [-1, 1]) {
                // One-layer shallow guide beside (never over) the paper.
                box_at(-base_length / 2, s > 0 ? channel_width / 2 : -channel_width / 2 - 2,
                    deck_thickness, base_length, 2, guide_height);
                box_at(-base_length / 2, s > 0 ? rail_inner : -base_width / 2,
                    deck_thickness, base_length, outer_rail_width, outer_rail_height);
            }
            for (s = [-1, 1], t = [-1, 1])
                translate([s * locator_x, t * attachment_y, deck_thickness - eps])
                    cylinder(h=locator_height + eps, d1=locator_diameter, d2=locator_diameter - 0.4);
        }
        for (s = [-1, 1], t = [-1, 1])
            translate([s * magnet_x, t * attachment_y,
                       deck_thickness - magnet_thickness - magnet_depth_clearance])
                cylinder(h=magnet_thickness + magnet_depth_clearance + eps,
                         d=magnet_diameter + magnet_diameter_clearance);
    }
}

module base_half(left=true) {
    intersection() {
        full_deck();
        translate([0, 0, -eps]) linear_extrude(deck_thickness + locator_height + 2 * eps)
            half_outline(left);
    }
}

module base() { base_half(true); base_half(false); }

module end_mask(format="16:9", side=1) {
    assert(format == "16:9" || format == "4:3", "Unknown mask format.");
    // Rotate the entire right-hand part for the left end, including its pegs.
    // Peg Y positions are generated in world order so both ends locate all four covers.
    rotate([0, 0, side < 0 ? 180 : 0]) difference() {
        union() {
            box_at(image_length(format) / 2, -mask_width / 2, paper_z,
                (base_length - image_length(format)) / 2, mask_width, mask_thickness);
            for (i = [0:3])
                translate([cover_pin_x, side * band_center(i), mask_top - eps])
                    cylinder(h=cover_pin_height + eps, d1=cover_pin_diameter,
                        d2=cover_pin_diameter - 0.4);
        }
        // Bottom 0.8 mm defines the cut line; upper edge retreats from the image.
        translate([image_length(format) / 2, mask_width / 2 + eps, paper_z])
            rotate([90, 0, 0]) linear_extrude(mask_width + 2 * eps)
                polygon([[-eps, mask_edge_land], [mask_bevel, mask_thickness + eps],
                         [-eps, mask_thickness + eps]]);
        for (t = [-1, 1]) {
            translate([magnet_x, t * attachment_y, paper_z - eps])
                cylinder(h=magnet_thickness + magnet_depth_clearance + eps,
                         d=magnet_diameter + magnet_diameter_clearance);
            translate([locator_x, t * attachment_y, paper_z - eps])
                cylinder(h=locator_height + 0.3 + eps, d=locator_diameter + locator_clearance);
        }
        // The format/end label stays visible in the fifth (uncovered) band.
        translate([cover_pin_x, side * band_center(4), mask_top - 0.4])
            linear_extrude(0.4 + eps) rotate([0, 0, 90])
                text(str(format, side < 0 ? " L" : " R"), size=3,
                    halign="center", valign="center", font="Liberation Sans:style=Bold");
    }
}

module masks(format="16:9") { for (s = [-1, 1]) end_mask(format, s); }

module cover(i=0) {
    assert(i >= 0 && i <= 3 && i == floor(i), "Cover index must be 0 to 3.");
    lo = -paper_width / 2 + i * band_width;
    hi = lo + band_width;
    body_lo = i == 0 ? lo - cover_lap : lo + cover_clearance;
    difference() {
        union() {
            box_at(-cover_end, body_lo, mask_top, 2 * cover_end, hi - body_lo, cover_thickness);
            if (i < 3) // No tongue into the fifth, always-exposed band.
                box_at(-cover_end, hi - eps, mask_top, 2 * cover_end,
                    cover_lap + eps, cover_lap_height);
            // Raised grip stays over the masked tail; no need to get a nail under a blade.
            hull() {
                box_at(cover_end - 5, band_center(i) - 7, mask_top + cover_thickness - eps,
                    4, 14, eps);
                box_at(cover_end - 4.5, band_center(i) - 6.5, mask_top + cover_thickness + 4 - eps,
                    3, 13, eps);
            }
        }
        if (i > 0)
            // A 45-degree underside replaces a floating horizontal cantilever.
            translate([-cover_end - eps, lo, mask_top]) rotate([90, 0, 90])
                linear_extrude(2 * cover_end + 2 * eps)
                    polygon([[-eps, -eps], [cover_lap + cover_lap_gap, -eps],
                        [cover_lap + cover_lap_gap, cover_lap_height + cover_lap_gap],
                        [-eps, cover_lap_height + cover_lap + 2 * cover_lap_gap + eps]]);
        for (s = [-1, 1])
            translate([s * cover_pin_x, band_center(i), mask_top - eps])
                cylinder(h=cover_thickness + 2 * eps, d=cover_pin_diameter + cover_pin_clearance);
        // Finger end has both a numeral and a tactile count. No through-holes over the image.
        translate([-cover_end + 2.7, band_center(i), mask_top + cover_thickness - 0.4])
            linear_extrude(0.4 + eps) rotate([0, 0, 90])
                text(str(i + 1), size=4, halign="center", valign="center", font="Liberation Sans:style=Bold");
        for (n = [0:i])
            translate([cover_end - 3, band_center(i) + (n - i / 2) * 3,
                       mask_top + cover_thickness + 4 - 0.6]) cylinder(h=0.6 + eps, d=1.6);
    }
}

module covers(count=4) { if (count > 0) for (i = [0:count-1]) cover(i); }

module paper(length=base_length + 20) {
    box_at(-length / 2, -paper_width / 2, deck_thickness, length, paper_width, paper_thickness);
}

module base_plate(left=true) {
    translate([left ? base_length / 2 : 0, base_width / 2, 0]) base_half(left);
}

module mask_plate(format="16:9") {
    depth = (base_length - image_length(format)) / 2;
    for (s = [-1, 1])
        translate([s < 0 ? base_length / 2 : depth + 6 - image_length(format) / 2,
                   mask_width / 2, -paper_z]) end_mask(format, s);
}

module cover_plate(i=0) {
    // Diagonal placement keeps each long cover in one piece on the A1 mini.
    extent = (2 * cover_end + band_width + 2 * cover_lap) / sqrt(2);
    translate([extent / 2, extent / 2, -mask_top]) rotate([0, 0, 45])
        translate([0, -band_center(i), 0]) cover(i);
}

module fit_crop() {
    box_at(base_length / 2 - 24, -base_width / 2, -eps,
        24, base_width / 2 - paper_width / 2 + band_width, 30);
}

module fit_plate() {
    translate([-base_length / 2 + 24, base_width / 2, 0]) intersection() { base(); fit_crop(); }
    translate([30 - image_169 / 2, mask_width / 2, -paper_z])
        intersection() { end_mask("16:9"); fit_crop(); }
    translate([56 - base_length / 2 + 16, paper_width / 2 + cover_lap, -mask_top])
        intersection() {
            cover(0);
            box_at(base_length / 2 - 16, -base_width / 2, 0, 16, base_width, 30);
        }
}

module assembly(format="16:9", cover_count=0, exploded=0) {
    color("#454e55") base();
    color("#fff3d6") paper();
    translate([0, 0, exploded]) color("#327a94") masks(format);
    translate([0, 0, 2 * exploded])
        for (i = [0:cover_count-1]) if (cover_count > 0)
            color([0.9 - 0.1 * i, 0.56 - 0.08 * i, 0.19]) cover(i);
}
