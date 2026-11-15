module vessel(id=0) {
    difference() {
        union() {
            rr(body_width,body_depth,body_height,1.2);
            translate([-rim_overhang,-rim_overhang,body_height-rim_height])
                rr(body_width+2*rim_overhang,body_depth+rim_overhang-0.1,rim_height,1.5);
            // The outside loft begins inside the shell; its cap is not a liquid trap.
            well_frame(id) well_loft(well_wall);
            translate([body_width/2-2*id,0.3,body_height-30]) rotate([90,0,0]) tactile(id+1);
        }
        liquid_void(id);
        // Recess letters into the front wall, well away from the heater face.
        translate([body_width/2,0.6,body_height*0.45]) rotate([90,0,0])
            linear_extrude(0.7) text(id==0?"A":"B",size=26,halign="center",valign="center",font="Liberation Sans:style=Bold");
        // Shallow horizontal mark on the side bowl at the calibrated empty fill.
        well_frame(id) translate([well_cx,well_cy,empty_level-0.3]) difference() {
            cylinder(r=well_at(empty_level)[1]+0.4,h=0.6);
            cylinder(r=well_at(empty_level)[1]-0.01,h=0.6);
        }
    }
}
module vessel_print(id=0) {
    // Lean the long axis inside the Y/Z diagonal. Broad walls remain >=44 degrees.
    dx = id==0 ? vessel_xmax-body_width : rim_overhang;
    translate([(build_size[0]-vessel_print_bounds[0])/2,
        (build_size[1]-vessel_print_bounds[1])/2,0]) {
        translate([dx,body_height*sin(print_tilt)+rim_overhang*cos(print_tilt),0])
            rotate([print_tilt,0,0]) vessel(id);
        // Two-layer sacrificial foot, trimmed off after printing. Keeps the first edge
        // attached without putting support inside a liquid-contacting surface.
        translate([dx+1,body_height*sin(print_tilt)+rim_overhang*cos(print_tilt)-3,0])
            rr(body_width-2,6,0.4,1);
    }
}
module water(level=empty_level,loaded=false,lift=0,id=0) {
    difference() {
        intersection() {
            liquid_void(id);
            translate([-vessel_xmax,-5,0]) cube([3*vessel_xmax,body_depth+10,level]);
        }
        if(loaded) paper(lift);
    }
}
