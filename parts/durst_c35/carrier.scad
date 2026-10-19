include <parameters.scad>

module c35_outline(width, rear, front, radius=body_corner_radius) {
    translate([-width / 2 + radius, rear + radius])
        offset(r=radius)
            square([width - 2 * radius, front - rear - 2 * radius]);
}

module c35_window_mask(relief=0) {
    translate([0, window_center_y]) union() {
        square([window_x, window_y], center=true);
        if (relief > 0) {
            square([window_x + 2 * relief,
                    window_y - 2 * b_corner_inset_length], center=true);
            square([window_x - 2 * b_corner_inset_length,
                    window_y + 2 * relief], center=true);
        }
    }
}

// Positive Z points outwards from a half's film face. The narrow opening is
// held through aperture_land; the exit is flared for the light path.
module c35_window_void(thickness, relief=0) {
    translate([0, 0, -c35_eps])
        linear_extrude(aperture_land + 2 * c35_eps) c35_window_mask(relief);
    hull() {
        translate([0, 0, aperture_land])
            linear_extrude(c35_eps) c35_window_mask(relief);
        translate([0, 0, thickness])
            linear_extrude(c35_eps)
                offset(delta=aperture_flare) c35_window_mask(relief);
    }
}

module c35_tray(rear, height, plate) {
    // Cut the cavity from one outer extrusion. Separately extruding coincident
    // rounded plate/skirt outlines produces numerical slivers at their seam.
    difference() {
        linear_extrude(height) c35_outline(body_width, rear, body_front_y);
        translate([-skirt_inner_x, rear - 1, plate])
            cube([2 * skirt_inner_x, body_front_y - skirt_wall - rear + 1,
                  height - plate + c35_eps]);
    }
}

module c35_front_groove() {
    translate([0, body_front_y - 5, -c35_eps])
        linear_extrude(front_groove_depth + c35_eps)
            hull() for (x=[-body_width / 2 + 8, body_width / 2 - 8])
                translate([x, 0]) circle(d=1.8);
}

// Small triangular moulding-style ribs tie the exterior skirt to its plate.
module c35_rib(side, y, plate, height) {
    translate([0, y, 0]) rotate([90, 0, 0]) linear_extrude(1.4)
        polygon([[side * (skirt_inner_x + c35_eps), plate - c35_eps],
                 [side * (skirt_inner_x - 3.5), plate - c35_eps],
                 [side * (skirt_inner_x + c35_eps), height - 1.5]]);
}

module c35_grip_cuts(height) {
    for (side=[-1, 1], y=[body_front_y - 17 : 2 : body_front_y - 5])
        translate([side > 0 ? body_width / 2 - 0.4 : -body_width / 2 - c35_eps,
                   y, height - 5])
            cube([0.4 + c35_eps, 0.8, 5 + c35_eps]);
}

module c35_a_outer() {
    difference() {
        union() {
            difference() {
                c35_tray(-hinge_ear_width, outer_height_a, plate_thickness_a);
                translate([-skirt_inner_x, -hinge_ear_width - 1, -c35_eps])
                    cube([2 * skirt_inner_x, a_plate_rear_y + hinge_ear_width + 1,
                          plate_thickness_a + 2 * c35_eps]);
            }
            translate([0, 0, outer_height_a - lip_thickness])
                linear_extrude(lip_thickness)
                    c35_outline(body_width - 0.2, body_front_y - 3, body_front_y + front_lip, 1.5);
            for (side=[-1, 1], y=[a_plate_rear_y + 7, body_front_y - 13])
                c35_rib(side, y, plate_thickness_a, outer_height_a);
        }
        c35_window_void(plate_thickness_a);
        c35_front_groove();
        c35_grip_cuts(outer_height_a);
    }
}

module c35_hinge_pin(side) {
    translate([side * (skirt_inner_x + c35_eps), hinge_y, hinge_z])
        rotate([0, -side * 90, 0]) union() {
            cylinder(h=hinge_pin_length - hinge_pin_tip_length + c35_eps,
                     d=hinge_pin_diameter);
            translate([0, 0, hinge_pin_length - hinge_pin_tip_length])
                cylinder(h=hinge_pin_tip_length + c35_eps,
                         d1=hinge_pin_diameter, d2=hinge_pin_diameter - 0.5);
        }
}

module c35_film_pin(x) {
    translate([x, film_pin_y, -c35_eps]) union() {
        cylinder(h=film_pin_height - film_pin_tip_height + c35_eps,
                 d=film_pin_diameter);
        translate([0, 0, film_pin_height - film_pin_tip_height])
            cylinder(h=film_pin_tip_height + c35_eps,
                     d1=film_pin_diameter, d2=film_pin_diameter - 0.5);
    }
}

// Assembly coordinates: A's inner face is horizontal at Z=0, skirt below it.
module c35_a() {
    union() {
        mirror([0, 0, 1]) c35_a_outer();
        for (side=[-1, 1]) c35_hinge_pin(side);
        for (x=[-film_pin_spacing / 2, film_pin_spacing / 2]) c35_film_pin(x);
        // Stops lie beyond the 35 mm film path and set a reproducible gap.
        for (x=[-body_width / 2 + 6, body_width / 2 - 6],
             y=[a_plate_rear_y + 12, body_front_y - 12])
            translate([x, y, -c35_eps]) cylinder(d=2, h=film_gap + c35_eps);
    }
}

// B ear profile in local Y/Z: its free tip is 10 mm below the film face.
module c35_b_ear_profile() {
    union() {
        translate([-hinge_ear_width + 1.5, -hinge_ear_height + 1.5])
            offset(r=1.5)
                square([hinge_ear_width - 3, hinge_ear_height + plate_thickness_b - 3]);
        // Root overlaps the plate, rather than merely touching its rear edge.
        translate([-hinge_ear_width, -0.6])
            square([hinge_ear_width + 2.2, plate_thickness_b + 0.6]);
    }
}

module c35_b_ear(side) {
    x0 = side > 0 ? ear_inner_x : -ear_outer_x;
    difference() {
        translate([x0, 0, 0])
            multmatrix([[0,0,1,0], [1,0,0,0], [0,1,0,0], [0,0,0,1]])
                linear_extrude(hinge_ear_thickness) c35_b_ear_profile();
        translate([x0 - c35_eps, hinge_y, -hinge_hole_from_root])
            rotate([0, 90, 0])
                cylinder(d=hinge_hole_diameter, h=hinge_ear_thickness + 2 * c35_eps);
    }
}

module c35_b_local() {
    difference() {
        union() {
            c35_tray(0, outer_height_b, plate_thickness_b);
            for (side=[-1, 1]) {
                c35_b_ear(side);
                for (y=[15, body_front_y - 13])
                    c35_rib(side, y, plate_thickness_b, outer_height_b);
            }
        }
        c35_window_void(plate_thickness_b, b_aperture_relief);
        c35_front_groove();
        // A recessed exterior panel leaves a raised window rim without making
        // the maximum slot-fitting plate any thicker than plate_thickness_b.
        if (b_outer_recess > 0)
            translate([0, 0, plate_thickness_b - b_outer_recess])
                linear_extrude(b_outer_recess + c35_eps) difference() {
                    c35_outline(body_width - 9, 5, body_front_y - 5, 2);
                    offset(r=aperture_flare + 2) c35_window_mask(b_aperture_relief);
                }
        for (x=[-film_pin_spacing / 2, film_pin_spacing / 2])
            translate([x, film_pin_y, -c35_eps])
                cylinder(h=b_pin_recess_depth + c35_eps,
                         d1=b_pin_recess_mouth, d2=b_pin_recess_bottom);
        // Recessed label on the outside front; never on a film-contact face.
        translate([0, body_front_y - 0.45, outer_height_b / 2])
            rotate([90, 0, 180]) linear_extrude(0.45 + c35_eps)
                text("C35  B", size=4, font="Liberation Sans:style=Bold",
                     halign="center", valign="center");
    }
}

module c35_b(angle=0) {
    translate([0, hinge_y, hinge_z]) rotate([angle, 0, 0])
        translate([0, -hinge_y, film_gap - hinge_z]) c35_b_local();
}

module c35_assembly(angle=0) {
    color([0.22, 0.27, 0.31]) c35_a();
    color([0.65, 0.72, 0.75]) c35_b(angle);
}

module c35_a_print() {
    translate([0, 0, outer_height_a]) c35_a();
}

module c35_b_print() {
    // Film face upward; supports touch exterior surfaces, not the film face.
    translate([0, 0, outer_height_b]) rotate([0, 180, 0]) c35_b_local();
}
