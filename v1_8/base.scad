// A single dry stand. Wet parts are the unchanged v2 vessels and guides.
base_width = cradle_width;
base_depth = 2*cradle_depth+module_gap;
socket_wall = 3;
socket_height = 32;

module valid_base() {
    assert(base_width<=usable_xy[0] && base_depth<=usable_xy[1],
        "Shared base exceeds the reserved A1 mini bed area.");
    assert(cradle_clearance>=0.3 && cradle_clearance<=1);
    assert(cradle_floor+socket_height<=usable_z);
    children();
}

module bath_socket(id) {
    translate([vessel_x(id)-cradle_clearance-socket_wall,
               id*vessel_pitch+vessel_y-cradle_clearance-socket_wall,cradle_floor-eps])
        difference() {
            rr(body_width+2*(cradle_clearance+socket_wall),
               body_depth+2*(cradle_clearance+socket_wall),socket_height+eps,
               1.2+cradle_clearance+socket_wall);
            translate([socket_wall,socket_wall,-eps])
                rr(body_width+2*cradle_clearance,body_depth+2*cradle_clearance,
                   socket_height+3*eps,1.2+cradle_clearance);
        }
}

module shared_base() {
    valid_base() difference() {
        union() {
            rr(base_width,base_depth,cradle_floor,3);
            for(id=[0:1]) bath_socket(id);
            for(id=[0:1]) translate([12,id*vessel_pitch+9,cradle_floor]) tactile(id+1);
        }
        for(id=[0:1]) translate([base_width/2,id*vessel_pitch+11,cradle_floor-0.6])
            linear_extrude(0.7) text(str(id==0?"A":"B","  ",working_ml," ml"),
                size=5,halign="center",valign="center",font="Liberation Sans:style=Bold");
    }
}

module unheated_assembly(explode=0) {
    color("SlateGray") shared_base();
    for(id=[0:1]) module_position(id) vessel_position(id,explode) {
        color(id==0?"SteelBlue":"CadetBlue") vessel(id);
        color("Goldenrod") translate([0,0,body_height+explode]) guide(id);
        color("Orange") translate([0,0,explode]) installed_clips();
    }
}
