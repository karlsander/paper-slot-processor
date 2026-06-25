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
clip_pocket_depth = 24;
clip_pocket_top_width = 12;
wiper_slope_height = 16;

// Filling geometry.
inlets_enabled = true;
inlets_on_left_side = true;
inlet_opening_diameter = 25;
inlet_cap_land_height = 10;
inlet_pool_diameter = slot_gap;
inlet_pool_below_fill = 2;
inlet_overlap_into_slot = 2;
inlet_wall = 4;
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

function inlet_x() =
    inlets_on_left_side
        ? wall_thickness + inlet_overlap_into_slot - inlet_pool_diameter / 2
        : wall_thickness + inner_width - inlet_overlap_into_slot +
            inlet_pool_diameter / 2;

function inlet_pool_y(slot_index) =
    slot_yc(slot_index);

function inlet_top_y(slot_index) =
    slot_yc(slot_index) +
    (test_print ? 0 : (slot_index == 0 ? -inlet_top_y_offset
                                       : inlet_top_y_offset));

function inlet_inner_edge_x() =
    inlets_on_left_side
        ? inlet_x() + inlet_opening_diameter / 2
        : inlet_x() - inlet_opening_diameter / 2;

function clip_channel_x0() =
    inlets_enabled && inlets_on_left_side
        ? inlet_inner_edge_x() + inlet_splash_wall_thickness
        : wall_thickness - eps;

function clip_channel_x1() =
    inlets_enabled && !inlets_on_left_side
        ? inlet_inner_edge_x() - inlet_splash_wall_thickness
        : wall_thickness + inner_width + eps;

function clip_channel_width() =
    max(eps, clip_channel_x1() - clip_channel_x0());

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

module paper_clip_channel_void(slot_index) {
    yc = slot_yc(slot_index);

    translate([
        clip_channel_x0(),
        yc - paper_slit_width / 2,
        wiper_apex_z - eps
    ])
        cube([
            clip_channel_width(),
            paper_slit_width,
            outer_height - wiper_apex_z + 2 * eps
        ]);

    translate([
        clip_channel_x0(),
        yc - clip_pocket_top_width / 2,
        wiper_apex_z - eps
    ])
        cube([
            clip_channel_width(),
            clip_pocket_top_width,
            clip_pocket_depth + 2 * eps
        ]);
}

module inlet_void(slot_index) {
    if (inlets_enabled) {
        throat_x0 = inlets_on_left_side
            ? inlet_x() - inlet_pool_diameter / 2 - eps
            : wall_thickness + inner_width - inlet_overlap_into_slot - eps;
        throat_x1 = inlets_on_left_side
            ? wall_thickness + inlet_overlap_into_slot + eps
            : inlet_x() + inlet_pool_diameter / 2 + eps;

        hull() {
            translate([
                inlet_x(),
                inlet_pool_y(slot_index),
                inlet_pool_z - join_overlap
            ])
                cylinder(
                    h = join_overlap,
                    d = inlet_pool_diameter,
                    $fn = inlet_facets
                );

            translate([
                inlet_x(),
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
            inlet_x(),
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
            inlet_x(),
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
                inlet_x(),
                inlet_pool_y(slot_index),
                inlet_pool_z - join_overlap
            ])
                cylinder(
                    h = join_overlap,
                    d = inlet_pool_diameter + 2 * inlet_wall,
                    $fn = inlet_facets
                );

            translate([
                inlet_x(),
                inlet_top_y(slot_index),
                inlet_cap_land_z - join_overlap
            ])
                cylinder(
                    h = join_overlap,
                    d = inlet_opening_diameter + 2 * inlet_wall,
                    $fn = inlet_facets
                );
        }

        translate([
            inlet_x(),
            inlet_top_y(slot_index),
            inlet_cap_land_z - join_overlap
        ])
            cylinder(
                h = inlet_cap_land_height + join_overlap,
                d = inlet_opening_diameter + 2 * inlet_wall,
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

module side_ribs() {
    rib_count = floor((outer_width - 2 * wall_thickness) / rib_spacing);

    if (rib_enabled && (!test_print || test_print_base)) {
        for (i = [0 : rib_count]) {
            x = wall_thickness + i * rib_spacing;
            skip_this_rib =
                inlets_enabled &&
                (inlets_on_left_side
                    ? x < inlet_opening_diameter + inlet_wall
                    : x > outer_width - inlet_opening_diameter - inlet_wall);

            if (!skip_this_rib) {
                translate([x, -rib_depth, -base_height])
                    cube([rib_width, rib_depth, outer_height + base_height - 12]);

                translate([x, outer_depth, -base_height])
                    cube([rib_width, rib_depth, outer_height + base_height - 12]);
            }
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
