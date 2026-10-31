// Commercial mat and metal plate stay in the frame; vessels release independently.
module guard_tile() {
    w=guard_tile_width; h=guard_tile_height;
    slot_w=(w-16-6)/3; slot_h=(h-16-9)/4;
    difference() {
        rr(w,h,guard_thickness,2);
        for(x=[4,w-4]) for(y=[4,36,h-36,h-4]) translate([x,y,0]) screw_hole(d=3.4,h=guard_thickness+1);
        for(x=[w/2-4,w/2+4]) for(y=[4,h-4])
            translate([x,y,0]) screw_hole(d=3.4,h=guard_thickness+1);
        for(i=[0:2]) for(j=[0:3])
            translate([8+i*(slot_w+3),8+j*(slot_h+3),-eps])
                rr(slot_w,slot_h,guard_thickness+2*eps,2);
    }
}
module guard_link() {
    difference() {
        rr(16,16,3,2);
        for(x=[4,12]) for(y=[4,12]) translate([x,y,0]) screw_hole(d=3.4,h=4);
    }
}
module guard_mount() {
    // Local Z=0 is the metal edge, Y=0 is its front face. Jaws touch only
    // unheated metal margins; the back beam clears the mat's active envelope.
    rear=heat_spreader_thickness+heater_thickness+guard_gap;
    difference() {
        union() {
            translate([-8,-2.4,-6]) cube([16,2.4,8.4]);
            translate([-8,heat_spreader_thickness+0.35,-6]) cube([16,2.4,8.4]);
            translate([-8,-2.4,0]) cube([16,heat_spreader_thickness+5.15,2.4]);
            translate([-8,heat_spreader_thickness+0.35,-7.5])
                cube([16,rear-heat_spreader_thickness-0.35,7.5]);
        }
        translate([0,rear+eps,-4]) rotate([90,0,0]) cylinder(d=3.4,h=rear+1);
        translate([0,heat_spreader_thickness+0.35+2.6,-4]) rotate([90,0,0])
            cylinder(d=6.5,h=2.7,$fn=6);
    }
}
module guard_mount_print() {
    translate([8,2.4,8]) rotate([0,90,0]) guard_mount();
}
module strap_anchor() {
    // Side-mounted on the bare metal margin, below the filling well. A 15 mm
    // strap passes through the front eye without crossing or squeezing the mat.
    difference() {
        linear_extrude(22) polygon([
            [-10,-8],[8,-8],[8,0],[0,0],[0,heat_spreader_thickness+0.35],
            [8,heat_spreader_thickness+0.35],[8,heat_spreader_thickness+2.75],
            [-2.4,heat_spreader_thickness+2.75],[-2.4,-2.4],[-10,-2.4]]);
        translate([-7,-8-eps,2.5]) cube([4,6+2*eps,17]);
    }
}
module strap_anchor_print() {
    translate([10,8,0]) strap_anchor();
}
// Loose, rounded edge capture. Nothing pierces or compresses the mat.
module mat_keeper(reach=8,width=6) {
    back=heat_spreader_thickness+heater_thickness+0.6;
    yz=[[-2.4,-reach-3],[0,-reach-3],[0,0],
        [back,0],[back,-reach+1.7],[heat_spreader_thickness+0.35,-reach+1.7],
        [heat_spreader_thickness+0.35,-reach+0.2],[back,-reach+0.2],
        [back,-reach-3],[back+2.4,-reach-3],[back+2.4,2.4],[-2.4,2.4]];
    rotate([0,90,0]) linear_extrude(width,center=true)
        polygon([for(p=yz) [-p[1],p[0]]]);
}
module mat_keeper_print(reach=8) {
    translate([reach+3,2.4,3]) rotate([0,90,0]) mat_keeper(reach);
}
module installed_mat_keepers(id=0) {
    // Narrow keepers avoid both the vessel and its lower plate clamps.
    translate([vessel_x()-3.5,heater_y,spreader_bottom]) mirror([0,0,1]) mat_keeper(24);
    translate([id==0?vessel_x()+body_width+3.5:vessel_x()-3.5,heater_y,spreader_top]) mat_keeper(8);
    for(side=[0:1]) translate([spreader_left+side*spreader_width,heater_y,spreader_bottom+24+heater_height/4])
        rotate([0,side==0?-90:90,0]) mat_keeper(8);
}
module cable_saddle() {
    difference() {
        rr(22,14,10,2);
        translate([4,7,0]) screw_hole(d=4.4,h=11);
        translate([15,-eps,10]) rotate([-90,0,0]) cylinder(d=6.4,h=14+2*eps);
        for(x=[10.5,18.5]) translate([x,3,-eps]) cube([2.5,8,10+2*eps]);
        translate([10.5,3,-eps]) cube([10.5,8,2.2]);
    }
}
module installed_heater_fittings(id=0) {
    // Two identical panels per chamber, each within the A1 mini bed.
    for(row=[0:1])
        color("DimGray") translate([spreader_left,guard_y,spreader_bottom+row*guard_tile_height])
            rotate([90,0,0]) guard_tile();
    // Four 1 mm washers space the joining link off the panel backs.
    color("Gray") translate([cradle_width/2-8,guard_y+4,spreader_bottom+guard_tile_height-8])
        rotate([90,0,0]) guard_link();
    // Side-edge mounts clear the lower clamps and the upper filling wells.
    for(side=[0:1]) for(z=[spreader_bottom+36,spreader_top-36])
        color("DimGray") translate([spreader_left+side*spreader_width,heater_y,z])
            rotate([0,side==0?-90:90,0]) guard_mount();
    for(side=[0:1]) color("DarkSlateGray")
        translate([spreader_left+side*spreader_width,heater_y,strap_z-11])
            if(side==0) strap_anchor(); else mirror([1,0,0]) strap_anchor();
    color("DarkSlateGray") installed_mat_keepers(id);
    color("DimGray") installed_cable_saddle();
}
module installed_cable_saddle() {
    // Use the outer side of the base, clear of the joining links and next tank.
    translate([12,30,cradle_floor]) rotate([0,0,180]) cable_saddle();
}
module interface_pads() {
    translate([vessel_x()+2,vessel_y+body_depth,cradle_floor+6])
        cube([body_width-4,thermal_pad,pad_height]);
}
