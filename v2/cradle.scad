module screw_hole(d=4.4,h=30) { translate([0,0,-eps]) cylinder(d=d,h=h+2*eps); }
module cradle(id=0) {
    vx=vessel_x(id);
    difference() {
        union() {
            rr(cradle_width,cradle_depth,cradle_floor,3);
            // Front and side guides leave the broad rear face clear for the heater plate.
            for(x=[vx-cradle_clearance-3,vx+body_width+cradle_clearance])
                translate([x,vessel_y-3,cradle_floor]) rr(3,body_depth,44,1);
            for(x=[vx,vx+body_width-15])
                translate([x,vessel_y-cradle_clearance-3,cradle_floor]) rr(15,3,44,1);
            // Low filleted feet stiffen the guide posts without enclosing the vessel.
            for(x=[vx-3,vx+body_width]) hull() {
                translate([x,vessel_y-3,cradle_floor]) cube([3,3,35]);
                translate([x,vessel_y-17,cradle_floor]) cube([3,3,1]);
            }
            translate([cradle_width/2-2*id,24,cradle_floor]) tactile(id+1);
        }
        // Both halves use the same connector pattern; spare outside holes accept accessories.
        for(x=[8,cradle_width-8]) for(y=[9,cradle_depth-9]) {
            translate([x,y,0]) screw_hole();
            translate([x,y,-eps]) cylinder(d=8.1,h=2.6,$fn=6);
        }
        // Heater clamps sit beyond the vessel footprint, below the side well.
        hx=id==0?8:cradle_width-24;
        for(dy=[6,22]) translate([hx+8,heater_y-12+dy,0]) {
            screw_hole(d=3.4,h=cradle_floor+1);
            translate([0,0,-eps]) cylinder(d=6.5,h=2.5,$fn=6);
        }
        translate([cradle_width/2,14,cradle_floor-0.6]) linear_extrude(0.7)
            text(id==0?"A":"B",size=12,halign="center",valign="center",font="Liberation Sans:style=Bold");
        if(id==0) {
            translate([cradle_width/2,37,cradle_floor-0.6]) linear_extrude(0.7)
                text(str(working_ml," ml"),size=7,halign="center",valign="center",font="Liberation Sans:style=Bold");
            translate([cradle_width/2,cradle_depth-26,cradle_floor-0.6]) linear_extrude(0.7)
                text(str("A ",amounts_a[0],":",amounts_a[1],"  B ",amounts_b[0],":",amounts_b[1]),
                    size=4,halign="center",valign="center",font="Liberation Sans:style=Bold");
        }
    }
}
module cradle_link() {
    difference() {
        rr(32,14,3,2);
        for(x=[8,24]) translate([x,7,0]) screw_hole(h=4);
    }
}
module heater_clamp() {
    // Clamp ONLY the unheated bottom margin of the metal spreader. The mat remains flat.
    difference() {
        rr(16,28,20,1.5);
        translate([-eps,12,spreader_bottom-cradle_floor])
            cube([16+2*eps,heat_spreader_thickness+0.35,21-(spreader_bottom-cradle_floor)]);
        for(y=[6,22]) translate([8,y,0]) screw_hole(d=3.4,h=21);
        // M3 screw with captive rear nut presses on the metal, never on the heater.
        translate([8,29,12]) rotate([90,0,0]) cylinder(d=3.4,h=17);
        translate([8,28.1,12]) rotate([90,0,0]) cylinder(d=6.5,h=2.7,$fn=6);
    }
}
module heater_spreader() {
    translate([(2*cradle_width-spreader_width)/2,heater_y,spreader_bottom])
        cube([spreader_width,heat_spreader_thickness,spreader_height]);
}
module heater_mat() {
    translate([(2*cradle_width-heater_width)/2,heater_y+heat_spreader_thickness,spreader_bottom+24])
        cube([heater_width,heater_thickness,heater_height]);
}
module assembly(explode=0,with_guides=true,with_heater=true,layer="all") {
    for(id=[0:1]) translate([id*(cradle_width+explode),0,0]) {
        if(layer=="all" || layer=="body") color("SlateGray") cradle(id);
        translate([vessel_x(id),vessel_y,cradle_floor+explode]) {
            if(layer=="all" || layer=="body") color(id==0?"SteelBlue":"CadetBlue") vessel(id);
            if(with_guides && (layer=="all" || layer=="details")) color("Goldenrod") translate([0,0,body_height+explode]) guide(id);
            if(with_guides && explode==0 && (layer=="all" || layer=="details")) color("Orange") installed_clips();
        }
        if(with_heater && (layer=="all" || layer=="details")) color("DimGray")
            translate([id==0?8:cradle_width-24,heater_y-12,cradle_floor]) heater_clamp();
    }
    if(explode==0 && (layer=="all" || layer=="details")) for(y=[2,cradle_depth-16])
        color("DimGray") translate([cradle_width-16,y,cradle_floor]) cradle_link();
    if(with_heater && explode==0) {
        if(layer=="all" || layer=="hardware") {
            color("Silver") heater_spreader();
            color("DarkSlateGray") heater_mat();
            color("LightSlateGray") interface_pads();
        }
        if(layer=="all" || layer=="details") installed_heater_fittings();
    }
}
