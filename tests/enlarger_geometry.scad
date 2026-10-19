include <../enlarger/parts.scad>
case_name = "paper";
format = "16:9";
cover_count = 0;
ray_sign = 1;

module sentinel() { translate([400, 0, 0]) cube(1); }
module aperture() {
    translate([-image_length(format) / 2, -paper_width / 2])
        square([image_length(format), paper_width]);
}
module above_paper() {
    intersection() {
        children();
        box_at(-200, -200, paper_z + eps, 400, 400, 40);
    }
}

check_parameters() {
    if (case_name == "joint") {
        sentinel();
        intersection() { base_half(true); base_half(false); }
    } else if (case_name == "paper") {
        sentinel();
        intersection() {
            union() { base(); masks(format); }
            // Includes a longer strip fed through the channel, with lateral play.
            for (dy = [-paper_side_clearance, 0, paper_side_clearance])
                box_at(-base_length / 2 - 40, -paper_width / 2 + dy + eps,
                    deck_thickness + eps, base_length + 80, paper_width - 2 * eps,
                    paper_thickness - 2 * eps);
        }
    } else if (case_name == "masks") {
        sentinel();
        intersection() { base(); masks(format); }
    } else if (case_name == "covers") {
        sentinel();
        intersection() {
            union() { base(); masks(format); }
            for (i = [0:3]) intersection() {
                cover(i, format);
                // Exclude intentional contacts with the rail and left-mask stop.
                box_at(cover_start(i, format) + eps, -200, cover_bottom + eps,
                    band_width + cover_lap, 400, 30);
            }
        }
        for (i = [0:2], j = [i+1:3]) intersection() {
            cover(i, format);
            // Separate the intentional butt contact by 0.01 mm; retain the lap.
            translate([eps, 0, 0]) cover(j, format);
        }
    } else if (case_name == "light") {
        sentinel();
        // Rays tilted 30 degrees transversely must reach BOTH long paper edges.
        // Trim X only to exclude the intentionally masked cut boundaries.
        intersection() {
            union() { base(); masks(format); }
            hull() {
                box_at(-image_length(format) / 2 + 5, -paper_width / 2, paper_z + eps,
                    image_length(format) - 10, paper_width, eps);
                box_at(-image_length(format) / 2 + 5,
                    -paper_width / 2 + ray_sign * 15 * tan(30), paper_z + 15,
                    image_length(format) - 10, paper_width, eps);
            }
        }
    } else if (case_name == "exposure") {
        linear_extrude(1) difference() {
            aperture();
            projection() above_paper() {
                base(); masks(format); covers(cover_count, format);
            }
        }
    } else if (case_name == "magnets") {
        sentinel();
        intersection() {
            union() { base(); masks(format); }
            for (s = [-1, 1], t = [-1, 1]) {
                translate([s * magnet_x, t * attachment_y,
                    deck_thickness - magnet_thickness - magnet_depth_clearance + eps])
                    cylinder(h=magnet_thickness - 2 * eps, d=magnet_diameter);
                translate([s * magnet_x, t * attachment_y, paper_z + magnet_depth_clearance])
                    cylinder(h=magnet_thickness - eps, d=magnet_diameter);
            }
        }
    } else assert(false, "Unknown geometry case.");
}
