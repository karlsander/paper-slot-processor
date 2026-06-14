// Parametric duplicate for a 120 medium format film spool.
// Print one, test-fit in the camera/back, then adjust the parameters below.
//
// Orientation: spool axis is the X axis.
// Units: millimeters.

$fn = 96;

// Overall spool dimensions.
overall_width = 63.0;        // Outside face to outside face.
flange_diameter = 25.0;      // Outer diameter of the spool flanges.
flange_thickness = 1.8;
core_diameter = 8.0;         // Diameter of the film/backing-paper core.

// End geometry. Many cameras tolerate variation here, but measure yours.
axle_hole_diameter = 2.6;    // Set to 0 for no through-bore.
drive_slot_width = 2.2;      // Narrow dimension of each winding-key slot.
drive_slot_length = 8.0;     // Long dimension of each winding-key slot.
drive_slot_depth = 3.0;      // How far the slot is cut into each end.

// Film leader slot in the core.
leader_slot_enabled = true;
leader_slot_count = 4;       // Evenly spaced radial slots around the core.
leader_slot_width = 1.4;

// Print tuning.
clearance = 0.15;
eps = 0.02;

module cyl_x(length, diameter) {
    rotate([0, 90, 0])
        cylinder(h = length, d = diameter, center = true);
}

module end_drive_slot(x_sign) {
    translate([
        x_sign * (overall_width / 2 - drive_slot_depth / 2 + eps),
        0,
        0
    ])
        cube([
            drive_slot_depth + 2 * eps,
            drive_slot_width + clearance,
            drive_slot_length + clearance
        ], center = true);
}

module leader_slot(angle = 0) {
    inner_width = overall_width - 2 * flange_thickness;

    // A straight slot through the core for inserting backing paper.
    rotate([angle, 0, 0])
        cube([
            inner_width + 2 * eps,
            core_diameter + 2 * eps,
            leader_slot_width + clearance
        ], center = true);
}

module leader_slots() {
    for (i = [0 : leader_slot_count - 1]) {
        leader_slot(i * 180 / leader_slot_count);
    }
}

module spool_body() {
    union() {
        // Core.
        cyl_x(overall_width, core_diameter);

        // Left and right flanges.
        translate([-overall_width / 2 + flange_thickness / 2, 0, 0])
            cyl_x(flange_thickness, flange_diameter);

        translate([overall_width / 2 - flange_thickness / 2, 0, 0])
            cyl_x(flange_thickness, flange_diameter);
    }
}

module film_spool_120() {
    difference() {
        spool_body();

        if (axle_hole_diameter > 0) {
            cyl_x(overall_width + 2 * eps, axle_hole_diameter + clearance);
        }

        end_drive_slot(-1);
        end_drive_slot(1);

        if (leader_slot_enabled) {
            leader_slots();
        }
    }
}

film_spool_120();
