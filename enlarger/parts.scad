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
    // The outside wings retain vertical end-stop faces for the transverse covers.
    rotate([0, 0, side < 0 ? 180 : 0]) difference() {
        box_at(image_length(format) / 2, -mask_width / 2, paper_z,
            (base_length - image_length(format)) / 2, mask_width, mask_thickness);
        // Bevel only over the paper: the wings outside it are square stops.
        translate([image_length(format) / 2, channel_width / 2, paper_z])
            rotate([90, 0, 0]) linear_extrude(channel_width)
                polygon([[-eps, mask_edge_land], [mask_bevel, mask_thickness + eps],
                         [-eps, mask_thickness + eps]]);
        for (t = [-1, 1]) {
            translate([magnet_x, t * attachment_y, paper_z - eps])
                cylinder(h=magnet_thickness + magnet_depth_clearance + eps,
                         d=magnet_diameter + magnet_diameter_clearance);
            translate([locator_x, t * attachment_y, paper_z - eps])
                cylinder(h=locator_height + 0.3 + eps, d=locator_diameter + locator_clearance);
        }
        translate([base_length / 2 - 10, 0, mask_top - 0.4])
            linear_extrude(0.4 + eps) rotate([0, 0, 90])
                text(str(format, side < 0 ? " L" : " R"), size=3,
                    halign="center", valign="center", font="Liberation Sans:style=Bold");
    }
}

module masks(format="16:9") { for (s = [-1, 1]) end_mask(format, s); }

module cover(i=0, format="16:9") {
    assert(i >= 0 && i <= 3 && i == floor(i), "Cover index must be 0 to 3.");
    lo = cover_start(i, format);
    hi = lo + band_width;
    center = band_center(i, format);
    difference() {
        union() {
            box_at(lo, -cover_end, cover_bottom, band_width, 2 * cover_end, cover_thickness);
            if (i < 3) // No tongue into the fifth, always-exposed band.
                box_at(hi - eps, -cover_end, cover_bottom, cover_lap + eps,
                    2 * cover_end, cover_lap_height);
            // Lift grip is outside the paper and outside the side rail.
            hull() {
                box_at(center - 7, cover_end - 5, cover_bottom + cover_thickness - eps,
                    14, 4, eps);
                box_at(center - 6.5, cover_end - 4.5, cover_bottom + cover_thickness + 4 - eps,
                    13, 3, eps);
            }
        }
        if (i > 0)
            // A 45-degree underside replaces a floating horizontal cantilever.
            translate([lo, cover_end + eps, cover_bottom]) rotate([90, 0, 0])
                linear_extrude(2 * cover_end + 2 * eps)
                    polygon([[-eps, -eps], [cover_lap + cover_lap_gap, -eps],
                        [cover_lap + cover_lap_gap, cover_lap_height + cover_lap_gap],
                        [-eps, cover_lap_height + cover_lap + 2 * cover_lap_gap + eps]]);
        // Numeral at one end and tactile count on the other; no through-holes.
        translate([center, -cover_end + 3.5, cover_bottom + cover_thickness - 0.4])
            linear_extrude(0.4 + eps)
                text(str(i + 1), size=4, halign="center", valign="center", font="Liberation Sans:style=Bold");
        for (n = [0:i])
            translate([center + (n - i / 2) * 3, cover_end - 3,
                       cover_bottom + cover_thickness + 4 - 0.6]) cylinder(h=0.6 + eps, d=1.6);
    }
}

module covers(count=4, format="16:9") { if (count > 0) for (i = [0:count-1]) cover(i, format); }

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
    translate([-cover_start(i), cover_end, -cover_bottom]) cover(i);
}

module fit_crop() {
    box_at(-base_length / 2, paper_width / 2 - 6, -eps,
        42, cover_end - paper_width / 2 + 6, 30);
}

module fit_plate() {
    translate([base_length / 2, -paper_width / 2 + 6, 0]) intersection() { base(); fit_crop(); }
    translate([52 + base_length / 2, -paper_width / 2 + 6, -paper_z])
        intersection() { end_mask("16:9", -1); fit_crop(); }
    translate([82 + image_169 / 2, -paper_width / 2 + 6, -cover_bottom])
        intersection() { cover(0); fit_crop(); }
}

module assembly(format="16:9", cover_count=0, exploded=0) {
    color("#454e55") base();
    color("#fff3d6") paper();
    translate([0, 0, exploded]) color("#327a94") masks(format);
    translate([0, 0, 2 * exploded])
        for (i = [0:cover_count-1]) if (cover_count > 0)
            color([0.9 - 0.1 * i, 0.56 - 0.08 * i, 0.19]) cover(i, format);
}
