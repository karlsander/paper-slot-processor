// Commercial mat and metal plate stay in the frame; vessels release independently.
module guard_tile() {
    w=guard_tile_width; h=guard_tile_height;
    slot_w=(w-16-6)/3; slot_h=(h-16-9)/4;
    difference() {
        rr(w,h,guard_thickness,2);
        for(x=[4,w-4]) for(y=[4,h-4]) translate([x,y,0]) screw_hole(d=3.4,h=guard_thickness+1);
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
            translate([-8,heat_spreader_thickness+0.35,-8])
                cube([16,rear-heat_spreader_thickness-0.35,8]);
        }
        translate([0,rear+eps,-4]) rotate([90,0,0]) cylinder(d=3.4,h=rear+1);
        translate([0,heat_spreader_thickness+0.35+2.6,-4]) rotate([90,0,0])
            cylinder(d=6.5,h=2.7,$fn=6);
    }
}
module guard_mount_print() {
    translate([8,2.4,8]) rotate([0,90,0]) guard_mount();
}
module strap_anchor(retain_mat=false) {
    // A 6 mm spine fits between the guides. The 15 mm strap loops are below the
    // bowls; unclipping a strap leaves the whole vessel free to lift out.
    if(retain_mat) mat_keeper(reach=8,width=6);
    // Extrude one outline: avoids coplanar union seams in the long flat spine.
    yz=[[-8,-anchor_length],[0,-anchor_length],[0,0],
        [heat_spreader_thickness+0.35,0],[heat_spreader_thickness+0.35,-6],
        [heat_spreader_thickness+2.75,-6],[heat_spreader_thickness+2.75,2.4],
        [-3,2.4],[-3,-anchor_length+22],[-8,-anchor_length+22]];
    rotate([0,90,0]) linear_extrude(6,center=true) difference() {
        polygon([for(p=yz) [-p[1],p[0]]]);
        translate([anchor_length-19.5,-6]) square([17,4]);
    }
}
module strap_anchor_print(retain_mat=false) {
    translate([anchor_length,8,3]) rotate([0,90,0]) strap_anchor(retain_mat);
}
// Loose, rounded edge capture. Nothing pierces or compresses the mat.
module mat_keeper(reach=8,width=10) {
    back=heat_spreader_thickness+heater_thickness+0.6;
    yz=[[-2.4,-reach-3],[0,-reach-3],[0,0],
        [back,0],[back,-reach+1.7],[heat_spreader_thickness+0.35,-reach+1.7],
        [heat_spreader_thickness+0.35,-reach+0.2],[back,-reach+0.2],
        [back,-reach-3],[back+2.4,-reach-3],[back+2.4,2.4],[-2.4,2.4]];
    rotate([0,90,0]) linear_extrude(width,center=true)
        polygon([for(p=yz) [-p[1],p[0]]]);
}
module mat_keeper_print(reach=8) {
    translate([reach+3,2.4,5]) rotate([0,90,0]) mat_keeper(reach);
}
module installed_mat_keepers() {
    left=(2*cradle_width-spreader_width)/2;
    translate([cradle_width,heater_y,spreader_bottom]) mirror([0,0,1]) mat_keeper(24);
    for(id=[0:1]) translate([left+id*spreader_width,heater_y,spreader_bottom+24+heater_height/2])
        rotate([0,id==0?-90:90,0]) mat_keeper(8);
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
module installed_heater_fittings() {
    left=(2*cradle_width-spreader_width)/2;
    // Six identical printable tiles, joined by two four-hole links.
    for(col=[0:2]) for(row=[0:1])
        color("DimGray") translate([left+col*guard_tile_width,guard_y,spreader_bottom+row*guard_tile_height])
            rotate([90,0,0]) guard_tile();
    for(col=[1:2]) color("Gray")
        translate([left+col*guard_tile_width-8,guard_y+3,spreader_bottom+guard_tile_height-8])
            rotate([90,0,0]) guard_link();
    for(x=[left+4,left+spreader_width-4]) {
        color("DimGray") translate([x,heater_y,spreader_top]) guard_mount();
        color("DimGray") translate([x,heater_y,spreader_bottom]) mirror([0,0,1]) guard_mount();
    }
    for(x=[10,cradle_width,2*cradle_width-10])
        color("DarkSlateGray") translate([x,heater_y,spreader_top]) strap_anchor(retain_mat=x==cradle_width);
    color("DarkSlateGray") installed_mat_keepers();
    color("DimGray") installed_cable_saddle();
}
module installed_cable_saddle() {
    translate([4,cradle_depth-16,cradle_floor]) cable_saddle();
}
module interface_pads() {
    for(id=[0:1]) translate([id*cradle_width+vessel_x(id)+2,vessel_y+body_depth,cradle_floor+6])
        cube([body_width-4,thermal_pad,body_height-12]);
}
