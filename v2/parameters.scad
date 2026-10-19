// V2: dimensions are millimetres. All parts derive from this one configuration.
/* [Image and roll] */
roll_width = 102;
image_aspect = 16/9; // Long image dimension / roll width. 2 gives a wider panorama.
paper_thickness = 0.3;
finger_grip = 8;
/* [Agitation] */
vertical_stroke = 6; // Lift from the two rounded bottom-edge stops.
lateral_stroke = 3; // Movement either side of centre.
immersion_margin = 2; // Image stays this far under liquid at the top of the stroke.
side_clearance = 10;
bottom_clearance = 4;
bath_gap = 14;
freeboard = 7; // Loaded liquid to the bare vessel rim; includes slosh reserve.
/* [Vessel] */
wall = 3;
floor = 4;
inside_radius = 2;
rim_overhang = 1.8;
rim_height = 2;
/* [Removable guide] */
guide_gap = 1.2; // Gentle default. Also export 0.8 and 0.6 mm trial inserts.
guide_thickness = 3;
guide_fit = 0.35;
guide_skirt = 2;
drip_depth = 1.5;
wiping_land = 0.4;
/* [Fill cue] */
sight_depth = 1.5;
well_bore = 8;
well_mouth = 16;
well_wall = 2.4;
well_flare = 9;
/* [Chemistry] */
recipe_a_concentrate = 1;
recipe_a_water = 4;
recipe_b_concentrate = 1;
recipe_b_water = 4;
recipe_a = [recipe_a_concentrate,recipe_a_water]; // Concentrate : water. User recipe; not a universal RA-4 recipe.
recipe_b = [recipe_b_concentrate,recipe_b_water]; // Independent of A, even when the volumes match.
rounding_limit = 2;
/* [Cradle and heater] */
cradle_depth = 120;
cradle_floor = 4;
cradle_clearance = 0.6;
heater_width = 350; // Flat shared heater; final selection documented separately.
heater_height = 200;
heater_thickness = 3;
heat_spreader_thickness = 1.5;
thermal_pad = 0.5; // Compliant external interface, separate from the printed liquid wall.
guard_gap = 10;
guard_thickness = 2.4;
/* [Printing] */
build_size = [180,180,180];
bed_margin = 3;
height_margin = 2;
print_tilt = 44.2;
$fn = 64;
eps = 0.02;

function clamp(v,lo,hi) = min(hi,max(lo,v));
function total(v,i=0) = i==len(v) ? 0 : v[i]+total(v,i+1);
function lerp(a,b,t) = a+(b-a)*t;
function smooth(t) = t*t*(3-2*t);
function gcd(a,b) = b==0 ? a : gcd(b,a%b);
function rounded_ml(v,parts,lo,hi) =
    let(batch=total(parts)/gcd(parts[0],parts[1]), exact=round(v/batch)*batch)
    abs(exact-v)<=rounding_limit && exact>=lo && exact<=hi ? exact :
    clamp(round(v),ceil(lo),floor(hi));
function mix_ml(v,parts) = let(first=round(v*parts[0]/total(parts))) [first,v-first];

image_length = roll_width*image_aspect;
inner_width = roll_width+2*side_clearance;
body_width = inner_width+2*wall;
body_depth = bath_gap+2*wall;
paper_bottom = floor+bottom_clearance;
image_top = paper_bottom+image_length;
target_loaded_level = image_top+vertical_stroke+immersion_margin;
body_height = target_loaded_level+freeboard;
guide_top = body_height+guide_thickness;
paper_cut_length = ceil(guide_top+finger_grip-paper_bottom);
paper_top = paper_bottom+paper_cut_length;
trim_band = paper_cut_length-image_length;
guide_width = body_width+2*(rim_overhang+guide_fit);
guide_depth = body_depth+rim_overhang+guide_fit; // Rear edge stays flush against the heat spreader.
slit_length = roll_width+2*(lateral_stroke+1);
bath_area = inner_width*bath_gap-(4-PI)*inside_radius*inside_radius;
// First estimate only locates the bowl. Actual empty/loaded levels use the volume solver.
pool_z = target_loaded_level-roll_width*paper_thickness*
    (target_loaded_level-paper_bottom)/bath_area-sight_depth;
well_cx = body_width+well_bore/2+wall;
well_cy = body_depth/2;
well_exit_z = pool_z-(well_cx-(body_width-wall-well_bore/2));
well_top = body_height;
function well_at(z) = z<=pool_z ? [well_cx-(pool_z-z),well_bore/2] :
    [well_cx,lerp(well_bore/2,well_mouth/2,smooth(clamp((z-pool_z)/well_flare,0,1)))];
well_stations = concat(
    [for(i=[0:16]) let(z=lerp(well_exit_z,pool_z,i/16),s=well_at(z)) [z,s[0],s[1]]],
    [for(i=[1:16]) let(z=lerp(pool_z,well_top,i/16),s=well_at(z)) [z,s[0],s[1]]]);
vessel_xmax = well_cx+well_mouth/2+well_wall;
cradle_width = max(vessel_xmax+24,heater_width/2-3);
vessel_pitch = cradle_width;
vessel_y = (cradle_depth-body_depth)/2;
clip_width = 12;
spreader_width = heater_width+16;
spreader_height = heater_height+32;
heater_y = vessel_y+body_depth+thermal_pad;
guard_y = heater_y+heat_spreader_thickness+heater_thickness+guard_gap+guard_thickness;
guard_tile_width = spreader_width/3;
guard_tile_height = spreader_height/2;
spreader_bottom = cradle_floor+3;
spreader_top = spreader_bottom+spreader_height;
strap_z = cradle_floor+body_height*0.65;
anchor_length = spreader_top-strap_z;
function vessel_x(id) = id==0 ? cradle_width-6-body_width : 6;

include <volume.scad>
nominal_ml = (capacity(target_loaded_level)-paper_displacement(target_loaded_level))/1000;
min_ml = max(capacity(pool_z+0.5),
    capacity(image_top+vertical_stroke+1)-paper_displacement(image_top+vertical_stroke+1))/1000+0.12;
max_ml = min(capacity(pool_z+2.5),
    capacity(body_height-6)-paper_displacement(body_height-6))/1000-0.12;
// Equal vessels share a volume. Recipe A can prefer an exact batch; B is independent.
working_ml = rounded_ml(nominal_ml,recipe_a,min_ml,max_ml);
empty_level = level_for_volume(working_ml*1000);
loaded_level = level_for_volume(working_ml*1000,true);
amounts_a = mix_ml(working_ml,recipe_a);
amounts_b = mix_ml(working_ml,recipe_b);
actual_sight_depth = empty_level-pool_z;
visible_pool_ml = (well_volume(empty_level)-well_volume(pool_z))/1000;
usable_xy = [build_size[0]-2*bed_margin,build_size[1]-2*bed_margin];
usable_z = build_size[2]-height_margin;
vessel_print_bounds = [vessel_xmax+rim_overhang,
    body_height*sin(print_tilt)+(body_depth+rim_overhang)*cos(print_tilt),
    body_height*cos(print_tilt)+max(body_depth,well_cy+well_mouth/2+well_wall)*sin(print_tilt)];

module valid() {
    assert(roll_width>40 && image_aspect>=1 && image_aspect<=3);
    assert(paper_thickness>0 && guide_gap>=paper_thickness+0.2);
    assert(side_clearance>=lateral_stroke+3 && bath_gap>=well_bore+2);

    assert(vertical_stroke>=0 && lateral_stroke>=0 && immersion_margin>=1);
    assert(wall>=2.4 && floor>=3 && inside_radius>0 && inside_radius<bath_gap/2);
    assert(bottom_clearance>=4 && freeboard>=7 && finger_grip>=6);
    assert(guide_fit>=0.15 && guide_fit<=0.7 && guide_skirt<freeboard-1);
    assert(drip_depth+wiping_land<guide_thickness && drip_depth>=1);
    assert(well_mouth>=well_bore && well_bore>=6 && well_wall>=2);
    assert(body_depth>=well_mouth+4,"The flat rear of the bowl needs at least 2 mm of wall.");
    assert(pool_z+well_flare<=well_top && well_exit_z>floor+inside_radius);
    assert(min(recipe_a)>0 && min(recipe_b)>0 && floor(recipe_a[0])==recipe_a[0] && floor(recipe_a[1])==recipe_a[1]);
    assert(floor(recipe_b[0])==recipe_b[0] && floor(recipe_b[1])==recipe_b[1]);
    assert(min_ml<=working_ml && working_ml<=max_ml && abs(working_ml-nominal_ml)<=rounding_limit);
    assert(loaded_level>=image_top+vertical_stroke+1 && body_height-loaded_level>=6);
    assert(actual_sight_depth>=0.5 && actual_sight_depth<=2.5);
    assert(print_tilt>=40 && print_tilt<=45);
    assert(thermal_pad>=0 && thermal_pad<=2 && guard_gap>=8 && guard_gap<=20);
    assert(heater_thickness>=1 && heater_thickness<=8 && heat_spreader_thickness>=1 && heat_spreader_thickness<=3);
    assert(anchor_length>=35 && anchor_length<=usable_xy[0]-3,"Heater height does not suit these strap anchors.");
    assert(guard_tile_width<=usable_xy[0] && guard_tile_height<=usable_xy[1]);
    assert(cradle_width<=usable_xy[0] && cradle_depth<=usable_xy[1],"Cradle half exceeds the printer bed.");
    assert(vessel_print_bounds[0]<=usable_xy[0] && vessel_print_bounds[1]<=usable_xy[1] &&
        vessel_print_bounds[2]<=usable_z,"Image size and clearance exceed the A1 mini in the documented tilted orientation.");
    children();
}
