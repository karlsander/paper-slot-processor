module chamber_void(i) {
    // Round all four bottom corners, including end walls, for rinsing.
    hull() {
        for (x = [wall_thickness + floor_round, wall_thickness + inner_width - floor_round])
            for (y = [slot_y0(i) + floor_round, slot_y0(i) + slot_gap - floor_round])
                translate([x, y, floor_z + floor_round]) sphere(r = floor_round);
        rounded_rect_slice(wall_thickness, slot_y0(i), inner_width, slot_gap, shoulder_z, floor_round);
    }
    hull() {
        rounded_rect_slice(wall_thickness, slot_y0(i), inner_width, slot_gap, shoulder_z, floor_round);
        entry_slice(i, throat_z, slit_radius);
    }
    hull() { entry_slice(i, throat_z - eps, slit_radius); entry_slice(i, land_z, slit_radius); }
    hull() {
        entry_slice(i, land_z - eps, slit_radius);
        entry_slice(i, outer_height - top_round, entry_mouth_width / 2);
    }
    // Chamfered rim, without a sharp full-thickness wiper edge.
    hull() {
        entry_slice(i, outer_height - top_round - eps, entry_mouth_width / 2);
        entry_slice(i, outer_height + eps, mouth_radius);
    }
}
module inlet_void(i) {
    if (inlets_enabled) inlet_frame(i) {
        hull() {
            translate([0, -inlet_offset, pool_z]) cylinder(h = eps, d = inlet_pool_diameter);
            translate([0, -inlet_offset, inlet_land_z]) cylinder(h = eps, d = inlet_opening_diameter);
        }
        translate([0, -inlet_offset, inlet_land_z - eps])
            cylinder(h = inlet_cap_land_height + 3 * eps, d = inlet_opening_diameter);
        // Lower edge of this shallow mark indicates the nominal fill level.
        if (fill_mark_depth > 0)
            translate([-3, -inlet_offset - fill_mark_radius - fill_mark_depth, fill_z])
                cube([6, 2 * fill_mark_depth + 1, 0.6]);
        // Broad passage slopes into this chamber; no blind sump in its floor.
        hull() {
            translate([-inlet_pool_diameter / 2, -inlet_offset, pool_z])
                cube([inlet_pool_diameter, eps, inlet_channel_height]);
            translate([-inlet_pool_diameter / 2, wall_thickness + 2, pool_z - inlet_drain_drop])
                cube([inlet_pool_diameter, eps, inlet_channel_height]);
        }
    }
}
module inlet_body(i) {
    if (inlets_enabled) inlet_frame(i) {
        // Short 45-degree buttress replaces the solid full-height tower.
        hull() {
            translate([-pool_outer_radius, -eps, pool_z - inlet_wall - inlet_support_height])
                cube([2 * pool_outer_radius, wall_thickness + eps, eps]);
            translate([0, -inlet_offset, pool_z - inlet_wall]) cylinder(h = eps, r = pool_outer_radius);
            translate([-pool_outer_radius, 0, pool_z - inlet_wall - inlet_drain_drop])
                cube([2 * pool_outer_radius, wall_thickness + eps, eps]);
        }
        hull() {
            translate([0, -inlet_offset, pool_z - inlet_wall]) cylinder(h = eps, r = pool_outer_radius);
            translate([0, -inlet_offset, inlet_land_z]) cylinder(h = eps, r = inlet_outer_radius);
        }
        translate([0, -inlet_offset, inlet_land_z - eps])
            cylinder(h = inlet_cap_land_height + eps, r = inlet_outer_radius);
        hull() {
            translate([-pool_outer_radius, -inlet_offset, pool_z - inlet_wall])
                cube([2 * pool_outer_radius, eps, inlet_channel_height + 2 * inlet_wall]);
            translate([-pool_outer_radius, wall_thickness, pool_z - inlet_wall - inlet_drain_drop])
                cube([2 * pool_outer_radius, 2 + eps, inlet_channel_height + 2 * inlet_wall]);
        }
    }
}
module tank_base() {
    if (base_enabled) {
        hull() {
            rounded_rect_slice(0, -base_extension, outer_width, outer_depth + 2 * base_extension, 0, 3);
            rounded_rect_slice(0, -base_extension, outer_width, outer_depth + 2 * base_extension, base_edge_height, 3);
        }
        hull() {
            rounded_rect_slice(0, -base_extension, outer_width, outer_depth + 2 * base_extension, base_edge_height, 3);
            rounded_rect_slice(0, 0, outer_width, outer_depth, base_height, 3);
        }
    }
}
module tank_ribs() {
    count = max(1, ceil((outer_width - 2 * wall_thickness) / rib_spacing));
    if (rib_enabled) for (i = [0 : count]) {
        x = wall_thickness + i * (inner_width - rib_width) / count;
        if (!inlets_enabled || abs(x + rib_width / 2 - outer_width / 2) > pool_outer_radius + rib_width)
            for (y = [-rib_depth, outer_depth - eps])
                translate([x, y, base_z]) cube([rib_width, rib_depth + eps, shoulder_z - base_z]);
    }
}
module tank() {
    difference() {
        union() {
            translate([0, 0, base_z]) cube([outer_width, outer_depth, outer_height - base_z]);
            tank_base();
            tank_ribs();
            for (i = [0 : chamber_count - 1]) inlet_body(i);
            if (chamber_labels) for (i = [0 : chamber_count - 1]) inlet_frame(i)
                translate([-outer_width / 2 + wall_thickness + 7, eps, outer_height - 12])
                    rotate([90, 0, 0]) linear_extrude(height = 0.6 + eps)
                        text(str(i + 1), size = 7, font = "Liberation Sans:style=Bold");
        }
        for (i = [0 : chamber_count - 1]) { chamber_void(i); inlet_void(i); }
    }
}
