module rr(w,d,h,r=2) {
    linear_extrude(h) hull() for(x=[r,w-r]) for(y=[r,d-r]) translate([x,y]) circle(r=r);
}
module rounded_bath_void() {
    hull() for(x=[wall+inside_radius,body_width-wall-inside_radius])
        for(y=[wall+inside_radius,body_depth-wall-inside_radius])
            for(z=[floor+inside_radius,body_height+10])
                translate([x,y,z]) sphere(r=inside_radius);
}
module bottom_stops() {
    for(x=[body_width/3,body_width*2/3]) translate([x,body_depth/2,floor-eps]) {
        cylinder(r=2,h=bottom_clearance-2+eps);
        translate([0,0,bottom_clearance-2+eps]) sphere(r=2);
    }
}
// Circular horizontal sections; a continuously descending passage has no blind sump.
module well_loft(extra=0,extend=0) {
    rings=[for(s=well_stations) [s[0]+(s[0]==well_top?extend:0),s[1],s[2]+extra]];
    n=$fn;
    vertices=[for(s=rings) for(j=[0:n-1])
        [s[1]+s[2]*cos(j*360/n),well_cy+s[2]*sin(j*360/n),s[0]]];
    faces=concat(
        [[for(j=[0:n-1]) j]],
        [for(k=[0:len(rings)-2]) for(j=[0:n-1])
            [k*n+j,(k+1)*n+j,(k+1)*n+(j+1)%n,k*n+(j+1)%n]],
        [[for(j=[n-1:-1:0]) (len(rings)-1)*n+j]]);
    intersection() {
        polyhedron(vertices,faces,convexity=12);
        // Flat rear surface lets the bowl and vessel meet the same heat spreader.
        translate([-vessel_xmax,-100,-1]) cube([3*vessel_xmax,body_depth+100,body_height+extend+3]);
    }
}
module well_frame(id=0) {
    if(id==0) translate([body_width,0,0]) mirror([1,0,0]) children();
    else children();
}
module liquid_void(id=0) {
    difference() {
        union() { rounded_bath_void(); well_frame(id) well_loft(0,2); }
        bottom_stops();
    }
}
module tactile(n,size=8) {
    for(i=[0:n-1]) translate([i*4,0,0]) rr(2,size,1,0.9);
}
module front_text(s,x,z,size,depth=0.6) {
    translate([x,-eps,z]) rotate([90,0,0])
        linear_extrude(depth+eps) text(s,size=size,halign="center",valign="center",font="Liberation Sans:style=Bold");
}
module paper(lift=0,side=0) {
    translate([wall+side_clearance+side,body_depth/2-paper_thickness/2,paper_bottom+lift])
        cube([roll_width,paper_thickness,paper_cut_length]);
}
