// Squeeze tong with a sliding lock collar, for handling a sheet in
// paper_slot_processor.scad.
//
// The arms splay (narrow at the handle, wide at the jaws) into a shallow
// self-locking wedge. A separate collar rides on the arms: slide it DOWN toward
// the jaws and it cams the arms together, clamping ~grip_width of the sheet's
// edge and holding by friction; slide it UP to the handle and the arms spring
// open to release. The collar is captive -- the wide handle and wide jaws stop
// it leaving the arms.
//
// Handheld: the tong rides above the tank, only the paper enters the slot, so
// it is not constrained to the 12 mm slot width. Clip near the front edge.
//
// Assembly: squeeze the arms by hand and slip the collar on over the jaws.
//
// Printing: the tong stands as modelled (profile on the bed) so the sprung
// neck flexes in-layer; the collar prints as a short upright ring (open hole,
// no supports). show = "plate" lays both out; "assembled" previews them.
//
// Units: millimeters.

$fn = 64;

// ---- Grip / size ----
grip_width      = 30;     // How much of the paper edge the jaws hold (Z).
paper_thickness = 0.3;

// ---- Arms (splayed wedge) ----
arm_thickness = 4;
gap_top       = 0.6;      // Inner gap just below the handle (collar parks here).
gap_jaw       = 6;        // Inner gap at the jaw tips at rest (open).
arm_v         = 50;       // Straight arm length below the handle.

// ---- Jaws ----
tooth_count = 3;
tooth_depth = 0.9;
tooth_pitch = 4;
tooth_v0    = 3;

// ---- Handle (wider than the collar, so the collar stays captive) ----
handle_w = 13;
handle_h = 9;

// ---- Sliding collar ----
collar_gap_u   = 8.8;     // Inner opening (closing direction). Must sit
                          // between the handle-end and jaw-end arm widths.
collar_z_clear = 0.6;     // Clearance per side in the grip-width direction.
collar_wall    = 3;
collar_h       = 12;

// ---- Render ----
show      = "plate";      // "plate", "assembled", "tong", or "collar".
plate_gap = 8;

eps = 0.02;

// ---- Derived ----
in_top   = gap_top / 2;
in_jaw   = gap_jaw / 2;
out_top  = in_top + arm_thickness;
out_jaw  = in_jaw + arm_thickness;
width_jaw = 2 * out_jaw;
collar_in_z = grip_width + 2 * collar_z_clear;
collar_out_u = collar_gap_u + 2 * collar_wall;

function inner_u(v) = in_jaw + (in_top - in_jaw) * (v / arm_v);

module tong2d() {
    union() {
        // Splayed arms.
        polygon([[ in_jaw, 0], [ out_jaw, 0], [ out_top, arm_v], [ in_top, arm_v]]);
        polygon([[-in_jaw, 0], [-out_jaw, 0], [-out_top, arm_v], [-in_top, arm_v]]);

        // Handle: a wide rounded cap that also blocks the collar.
        translate([0, arm_v + handle_h / 2])
            offset(r = 3)
                square([handle_w - 6, handle_h - 6], center = true);

        // Grip teeth on the inner faces.
        for (s = [-1, 1])
            for (i = [0 : tooth_count - 1]) {
                yv   = tooth_v0 + i * tooth_pitch;
                base = s * inner_u(yv);
                apex = s * (inner_u(yv) - tooth_depth);
                polygon([
                    [base, yv],
                    [base, yv + tooth_pitch * 0.6],
                    [apex, yv + tooth_pitch * 0.3]
                ]);
            }
    }
}

module tong() {
    linear_extrude(height = grip_width) tong2d();
}

module collar() {
    difference() {
        translate([
            -collar_out_u / 2,
            -(collar_in_z / 2 + collar_wall),
            0
        ])
            cube([collar_out_u, collar_in_z + 2 * collar_wall, collar_h]);

        translate([-collar_gap_u / 2, -collar_in_z / 2, -eps])
            cube([collar_gap_u, collar_in_z, collar_h + 2 * eps]);
    }
}

module plate() {
    tong();
    translate([out_jaw + plate_gap + collar_out_u / 2, 0, 0])
        collar();
}

if (show == "plate")
    plate();
else if (show == "assembled") {
    tong();
    // Collar shown parked high on the arms (release position).
    translate([0, arm_v - 6, grip_width / 2])
        rotate([90, 0, 0])
            collar();
}
else if (show == "tong")
    tong();
else if (show == "collar")
    collar();
