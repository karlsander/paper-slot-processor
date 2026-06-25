// Drop-in caps that close the open paper slots on top of
// paper_slot_processor.scad. One cap per chemistry chamber (print 2 for the
// default 2-slot tank). They cover the slot against dust, light, and
// evaporation between sessions; lift them out before loading paper.
//
// A locating rib noses into the slot to centre the cap and block the gap, a
// lip rests on the top face around the slot, and a flat tab past the open end
// gives a fingerhold.
//
// Print as modelled: lid flat on the bed, rib pointing up. No supports needed.
// To use, flip the cap so the rib drops into the slot and the pull tab sits at
// the end away from the inlets.
//
// Units: millimeters.

$fn = 64;

// --- Keep in sync with paper_slot_processor.scad ----------------------------
wall_thickness = 4;
inner_width = 136;            // paper_width + 2 * side_clearance.
slot_gap = 12;
clip_pocket_top_width = 12;   // Width (Y) of the open slot at the top face.
clip_pocket_depth = 24;       // Pocket depth before the slot necks to the slit.

inlets_enabled = true;        // Side inlets shorten the usable slot in X.
inlet_opening_diameter = 25;
inlet_overlap_into_slot = 2;
inlet_splash_wall_thickness = 2;
// ----------------------------------------------------------------------------

// Fit and cap geometry.
cap_clearance = 0.35;         // Per-side gap between the locating rib and slot.
rib_depth = 10;               // How far the rib noses in (< clip_pocket_depth).
rib_lead_in = 1.2;            // Chamfer at the rib tip for easy starting.
lid_thickness = 3;
lid_overhang_y = 1.5;         // Lip onto the top face each side (Y).
lid_overhang_x = 2;           // Lip onto the end walls (X).
pull_tab_length = 16;         // Flat fingerhold past the open (non-inlet) end.
eps = 0.02;

// Derived slot opening (a single chamber; both chambers share the same size).
inlet_pool_diameter = slot_gap;
inlet_intrusion = inlets_enabled
    ? inlet_overlap_into_slot - inlet_pool_diameter / 2
        + inlet_opening_diameter / 2 + inlet_splash_wall_thickness
    : 0;
slot_length = inner_width - inlet_intrusion;
slot_width = clip_pocket_top_width;

rib_x = slot_length - 2 * cap_clearance;
rib_y = slot_width - 2 * cap_clearance;
lid_x = slot_length + 2 * lid_overhang_x;
lid_y = slot_width + 2 * lid_overhang_y;

module rib_solid() {
    // Straight body...
    translate([-rib_x / 2, -rib_y / 2, 0])
        cube([rib_x, rib_y, rib_depth - rib_lead_in + eps]);

    // ...tapering to a smaller tip so it starts easily and prints supportless.
    translate([0, 0, rib_depth - rib_lead_in])
        hull() {
            translate([-rib_x / 2, -rib_y / 2, 0])
                cube([rib_x, rib_y, eps]);

            translate([
                -(rib_x - 2 * rib_lead_in) / 2,
                -(rib_y - 2 * rib_lead_in) / 2,
                rib_lead_in - eps
            ])
                cube([
                    rib_x - 2 * rib_lead_in,
                    rib_y - 2 * rib_lead_in,
                    eps
                ]);
        }
}

module slit_cap() {
    union() {
        // Cover plate plus an integral pull tab off the open end.
        translate([-lid_x / 2, -lid_y / 2, 0])
            cube([lid_x + pull_tab_length, lid_y, lid_thickness]);

        // Locating rib (points up as printed; drops into the slot in use).
        translate([0, 0, lid_thickness - eps])
            rib_solid();
    }
}

slit_cap();
