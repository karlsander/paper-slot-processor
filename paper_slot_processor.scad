// Parametric paper slot development tank.
// Open-top, unheated, no plumbing or light traps.
//
// Units: millimeters.
//
// Default setup:
// - 2 chemistry slots
// - Narrow vertical slots for dipping paper held by a clip
// - Side fill inlets with fill-level pool
//
// Printing notes:
// - Print in PETG/ASA/PP if possible; PLA can soften or craze with some chemistry.
// - Use enough perimeters/top-bottom layers to make the walls watertight.
// - Test with water before using chemistry.

$fn = 64;

// Test print mode: one chamber only. Toggle base/ribs separately below.
test_print = false;
test_print_base = true;

// Paper and slot parameters.
paper_width = 120;
paper_height = 120;

// Internal clearances around the paper.
side_clearance = 8;
bottom_clearance = 12;
slot_gap = 12;
freeboard = 28;

// Top wiper and paper-entry geometry.
paper_slit_width = 1;
wiper_land_height = 2;       // short section held at full paper-slit thinness (the wiper)
clip_pocket_depth = 10;      // height of the top funnel region (land + steep funnel) above the apex
clip_pocket_top_width = 12;  // funnel mouth width at the top (also the clip rest width)
wiper_slope_height = 16;
top_round = 1.5;             // rounded-over radius on the top opening rim (nicer to touch)

// Filling geometry.
inlets_enabled = true;
inlets_on_left_side = true;       // side of the first inlet
inlet_alternate_sides = true;     // put each successive inlet on the opposite side
inlet_opening_diameter = 30;      // funnel mouth bore at the top (>= 30 mm)
inlet_cap_land_height = 10;
inlet_pool_diameter = slot_gap;
inlet_pool_below_fill = 2;
inlet_overlap_into_slot = 2;
inlet_wall = 4;                   // wall thickness at the inlet pool (bottom)
inlet_wall_top = 2;               // thinner wall at the funnel mouth (tapers up from inlet_wall)
inlet_top_y_offset = 8;
inlet_facets = 64;
inlet_throat_height = 6;
inlet_splash_wall_thickness = 2;

// Wall and print parameters.
wall_thickness = 4;
floor_thickness = 5;
eps = 0.02;
join_overlap = 0.2;

// Base and stiffness features.
base_height = 6;
base_anchor_depth = 12;
base_extension_front = 42;
base_extension_back = 42;
rib_enabled = true;
rib_width = 8;
rib_depth = 3;
rib_spacing = 48;

// Derived dimensions.
active_slots = test_print ? 1 : 2;
inner_width = paper_width + 2 * side_clearance;
inner_height = paper_height + bottom_clearance + freeboard;
outer_width = inner_width + 2 * wall_thickness;
outer_depth = active_slots * slot_gap + (active_slots + 1) * wall_thickness;
outer_height = inner_height + floor_thickness;
wiper_apex_z = outer_height - clip_pocket_depth;
wiper_edge_z = wiper_apex_z - wiper_slope_height;
inlet_pool_z = wiper_edge_z - inlet_pool_below_fill;
inlet_cap_land_z = outer_height - inlet_cap_land_height;
bottom_z = (test_print && !test_print_base) ? 0 : -base_height;

function slot_y0(slot_index) =
    wall_thickness + slot_index * (slot_gap + wall_thickness);

function slot_y1(slot_index) =
    slot_y0(slot_index) + slot_gap;

function slot_yc(slot_index) =
    slot_y0(slot_index) + slot_gap / 2;

function inlet_left(slot_index) =
    (inlet_alternate_sides && (slot_index % 2 == 1))
        ? !inlets_on_left_side
        : inlets_on_left_side;

function inlet_x(slot_index) =
    inlet_left(slot_index)
        ? wall_thickness + inlet_overlap_into_slot - inlet_pool_diameter / 2
        : wall_thickness + inner_width - inlet_overlap_into_slot +
            inlet_pool_diameter / 2;

function inlet_pool_y(slot_index) =
    slot_yc(slot_index);

function inlet_top_y(slot_index) =
    slot_yc(slot_index) +
    (test_print ? 0 : (slot_index == 0 ? -inlet_top_y_offset
                                       : inlet_top_y_offset));

function inlet_inner_edge_x(slot_index) =
    inlet_left(slot_index)
        ? inlet_x(slot_index) + inlet_opening_diameter / 2
        : inlet_x(slot_index) - inlet_opening_diameter / 2;

function clip_channel_x0(slot_index) =
    inlets_enabled && inlet_left(slot_index)
        ? inlet_inner_edge_x(slot_index) + inlet_splash_wall_thickness
        : wall_thickness - eps;

function clip_channel_x1(slot_index) =
    inlets_enabled && !inlet_left(slot_index)
        ? inlet_inner_edge_x(slot_index) - inlet_splash_wall_thickness
        : wall_thickness + inner_width + eps;

function clip_channel_width(slot_index) =
    max(eps, clip_channel_x1(slot_index) - clip_channel_x0(slot_index));

module x_extruded_yz(x_start, length, points_yz, convexity = 10) {
    translate([x_start, 0, 0])
        rotate([0, 90, 0])
            linear_extrude(height = length, convexity = convexity)
                polygon(points = [
                    for (p = points_yz) [-p[1], p[0]]
                ]);
}

module lower_chamber_void(slot_index) {
    y0 = slot_y0(slot_index);
    y1 = slot_y1(slot_index);
    yc = slot_yc(slot_index);

    x_extruded_yz(
        wall_thickness - eps,
        inner_width + 2 * eps,
        [
            [y0, floor_thickness],
            [y1, floor_thickness],
            [y1, wiper_edge_z],
            [yc + paper_slit_width / 2, wiper_apex_z],
            [yc - paper_slit_width / 2, wiper_apex_z],
            [y0, wiper_edge_z]
        ]
    );
}

// One thin capsule (stadium) cross-section: two end cylinders spanning x1..x2
// at height z. Hulling these between levels lofts a pill-shaped solid with
// fully rounded short ends.
module capsule_disk(x1, x2, yc, z, r) {
    for (x = [x1, x2])
        translate([x, yc, z])
            cylinder(h = eps, r = r, $fn = 48);
}

module paper_clip_channel_void(slot_index) {
    yc = slot_yc(slot_index);
    land_top_z = wiper_apex_z + wiper_land_height;
    r_mouth = clip_pocket_top_width / 2;             // mouth half-width / end radius
    r_slit = paper_slit_width / 2;

    // End-cap centres, inset so even the rounded top lip stays within the clip
    // channel (clear of the inlet splash wall / outer wall).
    x1 = clip_channel_x0(slot_index) + r_mouth + top_round;
    x2 = clip_channel_x0(slot_index) + clip_channel_width(slot_index) - r_mouth - top_round;

    // Pill-shaped clip chamber, lofted top -> down through capsule cross-sections:
    //   rounded-over top rim (quarter round, radius top_round)
    //   -> steep funnel mouth -> short 1 mm wiper land.
    // Because every level is a capsule (two end cylinders), the short sides of
    // the opening are fully rounded -> stadium / pill shape.
    levels = [
        [outer_height,                     r_mouth + top_round],
        [outer_height - top_round * 0.707, r_mouth + top_round * 0.707],
        [outer_height - top_round,         r_mouth],
        [land_top_z,                       r_slit],
        [wiper_apex_z - eps,               r_slit]
    ];

    for (i = [0 : len(levels) - 2])
        hull() {
            capsule_disk(x1, x2, yc, levels[i][0],     levels[i][1]);
            capsule_disk(x1, x2, yc, levels[i + 1][0], levels[i + 1][1]);
        }
}

module inlet_void(slot_index) {
    if (inlets_enabled) {
        throat_x0 = inlet_left(slot_index)
            ? inlet_x(slot_index) - inlet_pool_diameter / 2 - eps
            : wall_thickness + inner_width - inlet_overlap_into_slot - eps;
        throat_x1 = inlet_left(slot_index)
            ? wall_thickness + inlet_overlap_into_slot + eps
            : inlet_x(slot_index) + inlet_pool_diameter / 2 + eps;

        hull() {
            translate([
                inlet_x(slot_index),
                inlet_pool_y(slot_index),
                inlet_pool_z - join_overlap
            ])
                cylinder(
                    h = join_overlap,
                    d = inlet_pool_diameter,
                    $fn = inlet_facets
                );

            translate([
                inlet_x(slot_index),
                inlet_top_y(slot_index),
                inlet_cap_land_z - join_overlap
            ])
                cylinder(
                    h = join_overlap,
                    d = inlet_opening_diameter,
                    $fn = inlet_facets
                );
        }

        translate([
            inlet_x(slot_index),
            inlet_top_y(slot_index),
            inlet_cap_land_z - join_overlap
        ])
            cylinder(
                h = inlet_cap_land_height + join_overlap + eps,
                d = inlet_opening_diameter,
                $fn = inlet_facets
            );

        translate([
            throat_x0,
            slot_y0(slot_index) - eps,
            inlet_pool_z - eps
        ])
            cube([
                throat_x1 - throat_x0,
                slot_gap + 2 * eps,
                inlet_throat_height + eps
            ]);
    }
}

module inlet_body(slot_index) {
    if (inlets_enabled) {
        translate([
            inlet_x(slot_index),
            inlet_pool_y(slot_index),
            bottom_z
        ])
            cylinder(
                h = inlet_pool_z - bottom_z,
                d = inlet_pool_diameter + 2 * inlet_wall,
                $fn = inlet_facets
            );

        hull() {
            translate([
                inlet_x(slot_index),
                inlet_pool_y(slot_index),
                inlet_pool_z - join_overlap
            ])
                cylinder(
                    h = join_overlap,
                    d = inlet_pool_diameter + 2 * inlet_wall,
                    $fn = inlet_facets
                );

            translate([
                inlet_x(slot_index),
                inlet_top_y(slot_index),
                inlet_cap_land_z - join_overlap
            ])
                cylinder(
                    h = join_overlap,
                    d = inlet_opening_diameter + 2 * inlet_wall_top,
                    $fn = inlet_facets
                );
        }

        translate([
            inlet_x(slot_index),
            inlet_top_y(slot_index),
            inlet_cap_land_z - join_overlap
        ])
            cylinder(
                h = inlet_cap_land_height + join_overlap,
                d = inlet_opening_diameter + 2 * inlet_wall_top,
                $fn = inlet_facets
            );
    }
}

module all_slot_voids() {
    for (i = [0 : active_slots - 1]) {
        lower_chamber_void(i);
        paper_clip_channel_void(i);
        inlet_void(i);
    }
}

module all_inlet_bodies() {
    for (i = [0 : active_slots - 1]) {
        inlet_body(i);
    }
}

module supportless_stabilizer_base() {
    if (!test_print || test_print_base) {
        translate([0, 0, -base_height])
            cube([outer_width, outer_depth, base_height + eps]);

        x_extruded_yz(
            0,
            outer_width,
            [
                [-base_extension_front, -base_height],
                [base_anchor_depth, -base_height],
                [base_anchor_depth, join_overlap],
                [0, join_overlap]
            ],
            4
        );

        x_extruded_yz(
            0,
            outer_width,
            [
                [outer_depth - base_anchor_depth, -base_height],
                [outer_depth + base_extension_back, -base_height],
                [outer_depth, join_overlap],
                [outer_depth - base_anchor_depth, join_overlap]
            ],
            4
        );
    }
}

// A rib column at x clashes with an inlet on the same side whose funnel mouth
// overhangs that face (front = y<0, back = y>outer_depth).
function rib_x_near_inlet(slot_index, x) =
    inlet_left(slot_index)
        ? x < inlet_opening_diameter + inlet_wall
        : x > outer_width - inlet_opening_diameter - inlet_wall;

function inlet_overhangs_face(slot_index, is_back) =
    is_back
        ? inlet_top_y(slot_index) + inlet_opening_diameter / 2 > outer_depth
        : inlet_top_y(slot_index) - inlet_opening_diameter / 2 < 0;

function rib_blocked(x, is_back) =
    inlets_enabled &&
    len([
        for (i = [0 : active_slots - 1])
            if (rib_x_near_inlet(i, x) && inlet_overhangs_face(i, is_back)) 1
    ]) > 0;

module side_ribs() {
    rib_count = floor((outer_width - 2 * wall_thickness) / rib_spacing);
    rib_z = outer_height + base_height - 12;

    if (rib_enabled && (!test_print || test_print_base)) {
        for (i = [0 : rib_count]) {
            x = wall_thickness + i * rib_spacing;

            if (!rib_blocked(x, false))
                translate([x, -rib_depth, -base_height])
                    cube([rib_width, rib_depth, rib_z]);

            if (!rib_blocked(x, true))
                translate([x, outer_depth, -base_height])
                    cube([rib_width, rib_depth, rib_z]);
        }
    }
}

module tank_shell() {
    difference() {
        union() {
            cube([outer_width, outer_depth, outer_height]);
            supportless_stabilizer_base();
            all_inlet_bodies();
            side_ribs();
        }

        all_slot_voids();
    }
}

module paper_slot_processor() {
    tank_shell();
}

paper_slot_processor();
