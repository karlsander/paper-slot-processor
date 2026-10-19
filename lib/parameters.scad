// Shared settings for every matching part. Units: mm. Also accepts CLI -D overrides.
/* [Paper and chambers] */
paper_width = 120;
paper_height = 120;
paper_thickness = 0.3;
paper_face_clearance = 0.6; // Per face; independent of cap fit.
chamber_count = 2; // [1:2]
side_clearance = 8;
bottom_clearance = 8;
slot_gap = 12;
entry_end_clearance = 2;
paper_slit_width = 8; // Admits the closed tong jaws; not a contact squeegee.
/* [Shell and entry] */
wall_thickness = 4;
floor_thickness = 5;
floor_round = 2;
entry_mouth_width = 12;
entry_depth = 8;
entry_land_height = 2;
entry_slope_height = 8;
top_round = 1;
fill_headroom = 4;
/* [Fill and pour openings] */
inlets_enabled = true;
inlet_opening_diameter = 40;
inlet_pool_diameter = 12;
inlet_wall = 3;
inlet_wall_top = 2;
inlet_cap_land_height = 6;
inlet_splash_gap = 3;
inlet_pool_below_fill = 2;
inlet_drain_drop = 2; // Passage slopes down toward the chamber.
inlet_channel_height = 10;
fill_mark_depth = 0.6;
/* [Engraved labels] */
chamber_labels = true;
chamber_names = ["A", "B"];
chamber_label_size = 24;
label_depth = 0.6;
base_volume_labels = true; // A-side base only, when the base is enabled.
base_label_size = 7;
mix_parts = [1, 4]; // Display order: one part : four parts, e.g. 100:400.
volume_rounding_limit_ml = 2; // Prefer an exact whole-ml ratio within this adjustment.
/* [Base and reinforcement] */
base_enabled = true;
base_height = 4;
base_edge_height = 1.2; // Six solid 0.2 mm layers at the edge, rather than a knife edge.
base_extension = 48;
rib_enabled = true;
rib_width = 6;
rib_depth = 3;
rib_spacing = 45;
/* [Caps] */
cap_clearance = 0.35; // Per side, shared by both plug types.
cap_lid_thickness = 3;
slit_cap_overlap = 0.75;
slit_cap_rib_depth = 4;
cap_tab_length = 10;
inlet_cap_overhang = 2;
/* [Tong] */
tong_grip_width = 30;
tong_arm_thickness = 2.6;
tong_arm_length = 100;
tong_gap_top = 0.6;
tong_gap_jaw = 5;
tong_pad_depth = 0.8;
tong_pad_length = 8;
tong_handle_width = 12;
tong_handle_height = 10;
collar_clearance = 0.6;
collar_wall = 4;
collar_height = 6;
tong_entry_clearance = 0.3;
tong_rim_clearance = 10; // Allows adjustment of grip below the nominal locking position.
/* [Printer] */
build_size = [180, 180, 180]; // A1 mini nominal volume.
bed_margin = 3; // Each XY edge, for adhesion aids.
height_margin = 2;
check_build_volume = true;
/* [Rendering] */
$fn = 64;
eps = 0.02;

// Derived dimensions. Accessories never maintain independent copies.
base_z = base_enabled ? base_height : 0;
mouth_radius = entry_mouth_width / 2 + top_round;
slit_radius = paper_slit_width / 2;
// Reserve a rectangular passage inside the faceted semicircular ends.
// Using overall capsule length alone overstates the usable width for a real sheet.
slit_safe_radius = slit_radius * cos(180 / $fn) - eps;
slit_chord = sqrt(max(0, slit_safe_radius * slit_safe_radius -
    pow(paper_thickness / 2 + paper_face_clearance, 2)));
inner_width = max(paper_width + 2 * side_clearance,
    paper_width + 2 * entry_end_clearance + 2 * (mouth_radius - slit_chord));
outer_width = inner_width + 2 * wall_thickness;
outer_depth = chamber_count * slot_gap + (chamber_count + 1) * wall_thickness;
floor_z = base_z + floor_thickness;
fill_z = floor_z + bottom_clearance + paper_height;
shoulder_z = fill_z + fill_headroom;
throat_z = shoulder_z + entry_slope_height;
land_z = throat_z + entry_land_height;
outer_height = land_z + entry_depth;
entry_centres = [wall_thickness + mouth_radius, wall_thickness + inner_width - mouth_radius];
entry_straight = entry_centres[1] - entry_centres[0];
entry_length = entry_straight + paper_slit_width;
inlet_offset = inlet_opening_diameter / 2 + inlet_splash_gap;
pool_z = fill_z - inlet_pool_below_fill;
inlet_land_z = outer_height - inlet_cap_land_height;
inlet_outer_radius = inlet_opening_diameter / 2 + inlet_wall_top;
pool_outer_radius = inlet_pool_diameter / 2 + inlet_wall;
inlet_support_height = inlet_offset + pool_outer_radius + 2;
chamber_label_top = inlets_enabled ? pool_z - inlet_wall - inlet_support_height : shoulder_z;
chamber_label_z = (base_z + chamber_label_top) / 2;
fill_mark_radius = inlet_pool_diameter / 2 +
    (inlet_opening_diameter - inlet_pool_diameter) / 2 * (fill_z - pool_z) / (inlet_land_z - pool_z);
slit_cap_radius = mouth_radius + slit_cap_overlap;
slit_lid_width = 2 * slit_cap_radius;
slit_lid_length = entry_straight + slit_lid_width;
inlet_cap_radius = inlet_outer_radius + inlet_cap_overhang;
inlet_plug_length = inlet_cap_land_height - 1;
tong_closed_gap = 2 * tong_pad_depth + paper_thickness;
tong_reach = outer_height - fill_z + tong_pad_length + tong_rim_clearance;
// Nominal straight-arm flex geometry. Spring force and wet grip need a printed test.
collar_gap = 2 * tong_arm_thickness + tong_gap_top +
    (tong_closed_gap - tong_gap_top) * (1 - tong_reach / tong_arm_length);
collar_snap_gap = 2 * tong_arm_thickness + tong_gap_top - 0.3;
collar_inner_z = tong_grip_width + 2 * collar_clearance;
collar_outer_u = collar_gap + 2 * collar_wall;
plate_gap = 8;
usable_xy = [build_size[0] - 2 * bed_margin, build_size[1] - 2 * bed_margin];
usable_height = build_size[2] - height_margin;
tank_front = max(base_enabled ? base_extension : 0,
    inlets_enabled ? inlet_offset + inlet_outer_radius : 0, rib_enabled ? rib_depth : 0);
tank_back = max(base_enabled ? base_extension : 0,
    inlets_enabled && chamber_count == 2 ? inlet_offset + inlet_outer_radius : 0,
    rib_enabled ? rib_depth : 0);
max_paper_width = min(usable_xy[0] - (outer_width - paper_width),
    usable_xy[0] - (slit_lid_length + cap_tab_length - paper_width));
max_paper_height = usable_height - (outer_height - paper_height);
include <volume.scad>
nominal_bath_ml = (rounded_bath_volume(inner_width, slot_gap, floor_round, fill_z - floor_z) +
    (inlets_enabled ? inlet_fill_volume() : 0)) / 1000;
// Reserve the paper (including a mesh tolerance on each face) and a conservative
// rectangular envelope for both immersed tong arms and pads below the entry.
loaded_capacity_ml = (rounded_bath_volume(inner_width, slot_gap, floor_round, shoulder_z - floor_z) +
    (inlets_enabled ? inlet_fill_volume(shoulder_z) : 0) -
    paper_width * paper_height * (paper_thickness + 2 * eps) -
    2 * tong_grip_width * (tong_arm_thickness * (tong_pad_length + fill_headroom) +
        tong_pad_depth * (tong_pad_length + 2 * eps))) / 1000;
max_mix_volume_ml = loaded_capacity_ml - 0.15; // Reserve calculation/mesh tolerance.
// Prefer a complete ratio batch (multiples of 5 ml for 1:4). When that would
// change the nominal fill by more than 2 ml, round the total and first amount;
// derive the second amount by subtraction so the printed sum is always exact.
working_volume_ml = rounded_working_ml(nominal_bath_ml, mix_parts, volume_rounding_limit_ml, max_mix_volume_ml);
mix_ml = whole_mix_ml(working_volume_ml, mix_parts);
mix_first_ml = mix_ml[0];
mix_second_ml = mix_ml[1];
volume_label = str(working_volume_ml, " ml");
mix_label = str(mix_first_ml, ":", mix_second_ml);
function slot_y0(i) = wall_thickness + i * (slot_gap + wall_thickness);
function slot_yc(i) = slot_y0(i) + slot_gap / 2;
function tong_inner(v, gap = tong_gap_jaw) = gap / 2 + (tong_gap_top - gap) / 2 * v / tong_arm_length;
function entry_radius_at_depth(d) = d <= top_round ? mouth_radius - d :
    slit_radius + (entry_mouth_width / 2 - slit_radius) * (entry_depth - d) / (entry_depth - top_round);

module validate_parameters() {
    assert(chamber_count == 1 || chamber_count == 2, "chamber_count must be 1 or 2.");
    assert(paper_width > 0 && paper_height > 0 && paper_thickness > 0);
    assert(side_clearance >= 0 && bottom_clearance >= floor_round);
    assert(wall_thickness >= 2 && floor_thickness >= 2 && floor_round > 0);
    assert(slot_gap > 2 * floor_round && inner_width > 2 * mouth_radius);
    assert(paper_face_clearance > 0 && slit_safe_radius > paper_thickness / 2 + paper_face_clearance,
        "Paper guide needs clearance.");
    assert(entry_length >= paper_width + 2 * entry_end_clearance);
    assert(entry_mouth_width >= paper_slit_width && entry_mouth_width <= slot_gap);
    assert(top_round > 0 && entry_depth > top_round && entry_land_height > 0);
    assert(entry_slope_height >= (slot_gap - paper_slit_width) / 2, "Chamber roof taper is too steep.");
    assert(fill_headroom > 0 && cap_clearance > 0 && cap_lid_thickness >= 2);
    assert(slit_cap_rib_depth > top_round && slit_cap_rib_depth < entry_depth);
    assert(entry_radius_at_depth(slit_cap_rib_depth) > cap_clearance);
    assert(chamber_count == 1 || slit_lid_width + 0.4 <= slot_gap + wall_thickness,
        "Adjacent slit caps need a gap; reduce the lip or increase wall_thickness.");
    assert(inlet_cap_land_height >= 3 && inlet_plug_length > 0);
    assert(!inlets_enabled || (inlet_opening_diameter >= inlet_pool_diameter &&
        inlet_wall >= 2 && inlet_wall_top >= 2 && inlet_channel_height > 0));
    assert(!inlets_enabled || inlet_land_z > pool_z + (inlet_opening_diameter - inlet_pool_diameter) / 2,
        "Increase headroom or reduce the inlet diameter for a supportless funnel.");
    assert(!inlets_enabled || pool_z - inlet_wall - inlet_support_height > base_z);
    assert(!inlets_enabled || inlet_splash_gap > inlet_cap_overhang, "Inlet cap crowds the tank.");
    assert(!inlets_enabled || 2 * inlet_outer_radius <= outer_width);
    assert(!inlets_enabled || (inlet_pool_diameter > 0 && pool_outer_radius <= inlet_outer_radius));
    assert(!inlets_enabled || pool_z + inlet_channel_height + inlet_wall < throat_z,
        "Fill passage roof must stay below the paper entry.");
    assert(!inlets_enabled || pool_z - inlet_drain_drop > floor_z + floor_round);
    assert(inlet_drain_drop > 0 && inlet_pool_below_fill > 0);
    assert(fill_mark_depth >= 0 && fill_mark_depth <= inlet_wall_top / 2);
    assert(label_depth > 0 && label_depth <= wall_thickness / 2);
    assert(!chamber_labels || (len(chamber_names) >= chamber_count && chamber_label_size > 0 &&
        chamber_label_size + 4 < chamber_label_top - base_z && chamber_label_size + 4 < inner_width),
        "Chamber labels need space below the inlets.");
    assert(len(mix_parts) == 2 && mix_parts[0] > 0 && mix_parts[1] > 0 &&
        mix_parts[0] == floor(mix_parts[0]) && mix_parts[1] == floor(mix_parts[1]),
        "Mixing parts must be positive whole numbers.");
    assert(volume_rounding_limit_ml >= 0.5 && volume_rounding_limit_ml <= 2);
    assert(working_volume_ml > 0 && abs(working_volume_ml - nominal_bath_ml) <= volume_rounding_limit_ml,
        "Increase fill_headroom to accommodate the paper, tong and rounded fill volume.");
    assert(!base_volume_labels || !base_enabled || (base_label_size > 0 &&
        base_extension > 2 * base_label_size + 4 &&
        label_depth <= base_edge_height / 2), "Base engraving needs enough width and solid thickness.");
    assert(!base_enabled || (base_edge_height > 0 && base_height > base_edge_height && base_extension >= tank_front - eps &&
        base_extension >= tank_back - eps), "Base must support the inlet footprint.");
    assert(rib_spacing > rib_width && rib_width > 0 && rib_depth > 0);
    assert(tong_arm_length > collar_height + tong_pad_length && tong_arm_thickness > 0);
    assert(tong_arm_length > tong_reach + collar_height + 2);
    assert(tong_rim_clearance > 0 && tong_entry_clearance > 0);
    assert(paper_slit_width >= 2 * tong_arm_thickness + tong_closed_gap + 2 * tong_entry_clearance,
        "Widen the guide so the closed tong can immerse the paper edge.");
    assert(tong_gap_top > 0 && tong_gap_jaw > 2 * tong_pad_depth + paper_thickness);
    assert(collar_gap > 2 * (tong_inner(tong_arm_length - 2 - collar_height) +
        tong_arm_thickness) + 0.4, "Collar cannot park freely on the open tong.");
    assert(tong_handle_width > collar_gap && collar_wall >= 2 && collar_clearance > 0);
    assert(collar_snap_gap > 0 && collar_gap > collar_snap_gap + 0.5,
        "Snap collar needs retaining lips and clearance around the arms.");
    assert(tong_handle_width > 4 && tong_handle_height > 4 && tong_pad_depth > 0 && tong_pad_length > 2);
    assert(bed_margin >= 0 && height_margin >= 0 && cap_tab_length > 0 && slit_cap_overlap > 0);
    assert(!check_build_volume || (outer_width <= usable_xy[0] &&
        outer_depth + tank_front + tank_back <= usable_xy[1] && outer_height <= usable_height),
        "Tank exceeds the configured printer volume/margins.");
    assert(!check_build_volume || (slit_lid_length + cap_tab_length <= usable_xy[0] &&
        chamber_count * (slit_lid_width + plate_gap) - plate_gap <= usable_xy[1]), "Slit caps exceed plate.");
    assert(!check_build_volume || (chamber_count * (2 * inlet_cap_radius + plate_gap) - plate_gap <=
        usable_xy[0] && 2 * inlet_cap_radius + cap_tab_length <= usable_xy[1]), "Inlet caps exceed plate.");
    assert(!check_build_volume || (max(tong_handle_width, tong_gap_jaw + 2 * tong_arm_thickness) / 2 +
        tong_gap_jaw / 2 + tong_arm_thickness + plate_gap + collar_outer_u <= usable_xy[0] &&
        max(tong_arm_length + tong_handle_height - 2, collar_inner_z + 2 * collar_wall) <= usable_xy[1] &&
        max(tong_grip_width, collar_height) <= usable_height), "Tong plate exceeds printer volume.");
    children();
}
