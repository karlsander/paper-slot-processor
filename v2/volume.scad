// Capacity is the rounded open vessel plus the portion of the side well outside it.
function round_bath(w,d,r,h) = h<=0 ? 0 : h<r ?
    let(dz=h/80) dz*total([for(i=[0:79])
        let(z=(i+0.5)*dz,b=r-sqrt(max(0,r*r-pow(r-z,2))))
            (w-2*b)*(d-2*b)-(4-PI)*pow(r-b,2)]) :
    (w*d-(4-PI)*r*r)*(h-r)+(w-2*r)*(d-2*r)*r+
        (w+d-4*r)*PI*r*r/2+2*PI*r*r*r/3;
function stops_volume(level) =
    let(r=2,h=bottom_clearance-r,zc=floor+h,cap=clamp(level-zc,0,r))
        2*(PI*r*r*clamp(level-floor,0,h)+PI*(r*r*cap-pow(cap,3)/3));
function paper_displacement(level,lift=0) = roll_width*paper_thickness*
    clamp(level-paper_bottom-lift,0,paper_cut_length);
function circle_right(r,x) = x<=-r ? PI*r*r : x>=r ? 0 :
    r*r*(90-asin(x/r))*PI/180-x*sqrt(max(0,r*r-x*x));
function well_interval(a,b,level,steps=12) = level<=a[0] ? 0 :
    let(top=min(level,b[0]),dz=(top-a[0])/steps)
    dz*total([for(i=[0:steps-1])
        let(t=((a[0]+(i+0.5)*dz)-a[0])/(b[0]-a[0]),
            cx=lerp(a[1],b[1],t),r=lerp(a[2],b[2],t))
        circle_right(r,body_width-wall-cx)]);
function well_volume(level) = total([for(i=[0:len(well_stations)-2])
    well_interval(well_stations[i],well_stations[i+1],level)]);
function capacity(level) = round_bath(inner_width,bath_gap,inside_radius,level-floor)-
    stops_volume(level)+well_volume(level);
function level_for_volume(v,loaded=false,lo=floor,hi=body_height,n=24,lift=0) = n==0 ? (lo+hi)/2 :
    let(mid=(lo+hi)/2,available=capacity(mid)-(loaded?paper_displacement(mid,lift):0))
    available<v ? level_for_volume(v,loaded,mid,hi,n-1,lift) :
        level_for_volume(v,loaded,lo,mid,n-1,lift);
