// Helpers use dimensions loaded by parameters.scad.
module capsule_slice(x1, x2, yc, z, r) {
    hull() for (x = [x1, x2]) translate([x, yc, z]) cylinder(h = eps, r = r);
}
module rounded_rect_slice(x0, y0, w, d, z, r) {
    hull() for (x = [x0 + r, x0 + w - r]) for (y = [y0 + r, y0 + d - r])
        translate([x, y, z]) cylinder(h = eps, r = r);
}
module inlet_frame(i) {
    translate([outer_width / 2, i == 0 ? 0 : outer_depth, 0])
        rotate([0, 0, i == 0 ? 0 : 180]) children();
}
module entry_slice(i, z, r) {
    capsule_slice(entry_centres[0], entry_centres[1], slot_yc(i), z, r);
}
