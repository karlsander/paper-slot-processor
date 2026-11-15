module slot_slice(gap,z) {
    translate([(body_width-slit_length)/2,body_depth/2-gap/2,z])
        rr(slit_length,gap,eps,min(gap/2,0.6));
}
module guide(id=0,gap=guide_gap,closed=false) {
    difference() {
        union() {
            translate([-(rim_overhang+guide_fit),-(rim_overhang+guide_fit),0])
                rr(guide_width,guide_depth,guide_thickness,1.5);
            // Locating skirt ends above the liquid, so there is no submerged joint.
            translate([wall+guide_fit,wall+guide_fit,-guide_skirt]) difference() {
                rr(inner_width-2*guide_fit,bath_gap-2*guide_fit,guide_skirt+eps,inside_radius);
                translate([1.5,1.5,-eps]) rr(inner_width-2*guide_fit-3,bath_gap-2*guide_fit-3,guide_skirt+2*eps,1);
            }
            translate([9,-rim_overhang-guide_fit+0.2,0.6]) rotate([90,0,0]) tactile(id+1,1.8);
        }
        if(!closed) {
            low=guide_thickness-drip_depth-wiping_land;
            hull() { slot_slice(gap+4,-guide_skirt-eps); slot_slice(gap,low); }
            hull() { slot_slice(gap,low-eps); slot_slice(gap,low+wiping_land+eps); }
            hull() { slot_slice(gap,guide_thickness-drip_depth); slot_slice(gap+4,guide_thickness+eps); }

        }
        translate([body_width-12,body_depth/2,guide_thickness-0.6])
            linear_extrude(0.7) text(str(id==0?"A":"B",closed?"":str(" ",gap)),size=3,
                halign="center",valign="center",font="Liberation Sans:style=Bold");
    }
}
module retaining_clip() {
    // Slides over the front rim and the guide. No holes enter the vessel.
    difference() {
        rr(clip_width,9,9,1);
        translate([-eps,2,1.8]) cube([clip_width+2*eps,8,5.4]);
        // The lower jaw catches only the projecting rim, not the vessel wall below it.
        translate([-eps,3.8,-eps]) cube([clip_width+2*eps,6,1.8+eps]);
    }
}
module clip_print() { translate([0,0,clip_width]) rotate([0,90,0]) retaining_clip(); }
module installed_clips() {
    for(x=[body_width/4,body_width*3/4])
        translate([x-clip_width/2,-4.2,body_height-2.2-1.8]) retaining_clip();
}
module guide_print(id=0,gap=guide_gap,closed=false) {
    // Top on bed: the shallow underside taper rises without an internal support.
    translate([rim_overhang+guide_fit,body_depth,guide_thickness])
        rotate([180,0,0]) guide(id,gap,closed);
}
