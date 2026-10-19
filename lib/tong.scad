// Smooth pads protect the paper edge. Arms overlap the handle over a full area.
module tong_profile(gripping = false) {
    gap = gripping ? tong_closed_gap : tong_gap_jaw;
    difference() {
        union() {
            polygon([
                [-gap / 2 - tong_arm_thickness, 0],
                [ gap / 2 + tong_arm_thickness, 0],
                [ tong_gap_top / 2 + tong_arm_thickness, tong_arm_length],
                [-tong_gap_top / 2 - tong_arm_thickness, tong_arm_length]
            ]);
            translate([0, tong_arm_length + tong_handle_height / 2 - 2])
                offset(r = 2) square([tong_handle_width - 4, tong_handle_height - 4], center = true);
        }
        polygon([
            [-tong_inner(-eps, gap), -eps], [tong_inner(-eps, gap), -eps],
            [tong_gap_top / 2, tong_arm_length - 2], [-tong_gap_top / 2, tong_arm_length - 2]
        ]);
        translate([0, tong_arm_length - 2]) circle(d = tong_gap_top);
    }
    for (s = [-1, 1]) hull() for (v = [2, tong_pad_length])
        translate([s * (gap / 2 - tong_pad_depth / 2), v]) circle(r = tong_pad_depth / 2);
}
module tong(gripping = false) { linear_extrude(height = tong_grip_width) tong_profile(gripping); }
module collar() {
    difference() {
        translate([-collar_outer_u / 2, -collar_inner_z / 2 - collar_wall, 0])
            cube([collar_outer_u, collar_inner_z + 2 * collar_wall, collar_height]);
        translate([-collar_gap / 2, -collar_inner_z / 2, -eps])
            cube([collar_gap, collar_inner_z, collar_height + 2 * eps]);
        // Snap onto the neck sideways: a closed ring cannot pass the grip pads.
        // Short retaining lips and a flared lead-in permit a removable C-shaped collar.
        translate([0, 0, -eps]) linear_extrude(height = collar_height + 2 * eps)
            polygon([
                [-collar_snap_gap / 2, collar_inner_z / 2 - eps],
                [ collar_snap_gap / 2, collar_inner_z / 2 - eps],
                [ collar_gap / 2, collar_inner_z / 2 + collar_wall + eps],
                [-collar_gap / 2, collar_inner_z / 2 + collar_wall + eps]
            ]);
    }
}
module parked_collar() {
    translate([0, tong_arm_length - 2, tong_grip_width / 2]) rotate([90, 0, 0]) collar();
}
module gripping_collar() {
    translate([0, tong_reach + collar_height, tong_grip_width / 2]) rotate([90, 0, 0]) collar();
}
// Nominal flex pose for clearance checks, not a mechanical force simulation.
module immersed_tong(i) {
    multmatrix([[0, 0, 1, (outer_width - tong_grip_width) / 2],
                [1, 0, 0, slot_yc(i)],
                [0, 1, 0, fill_z - tong_pad_length], [0, 0, 0, 1]]) {
        tong(true);
        gripping_collar();
    }
}
module tong_plate() {
    tong();
    translate([tong_gap_jaw / 2 + tong_arm_thickness + plate_gap + collar_outer_u / 2,
        collar_inner_z / 2 + collar_wall, 0]) collar();
}
