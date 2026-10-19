// Liquid capacity in mm3, including the tapered chamber roof and the inlet.
// The rounded bath is analytic. Integrate the inlet's horizontal sections,
// subtracting their overlap with the main bath exactly once.
function rounded_bath_volume(w, d, r, h) =
    (w * d - (4 - PI) * r * r) * (h - r) +
    (w - 2 * r) * (d - 2 * r) * r +
    (w + d - 4 * r) * PI * r * r / 2 + 2 * PI * r * r * r / 3;

function interpolate(a, b, t) = a + (b - a) * t;
function roof_fraction(z) = min(1, max(0, (z - shoulder_z) / entry_slope_height));
function roof_area(z) =
    let(t = roof_fraction(z), w = interpolate(inner_width - 2 * floor_round, entry_straight, t),
        d = interpolate(slot_gap - 2 * floor_round, 0, t), r = interpolate(floor_round, slit_radius, t))
    w * d + 2 * r * (w + d) + PI * r * r;
function bath_volume(level) =
    rounded_bath_volume(inner_width, slot_gap, floor_round, min(level, shoulder_z) - floor_z) +
    (level <= shoulder_z ? 0 : (level - shoulder_z) / 6 *
        (roof_area(shoulder_z) + 4 * roof_area((shoulder_z + level) / 2) + roof_area(level)));
function bath_front_y(z) = wall_thickness + roof_fraction(z) * (slot_gap - paper_slit_width) / 2;
function paper_displacement(level) = paper_width * paper_thickness *
    min(paper_height, max(0, level - paper_bottom_z));
function liquid_capacity(level) = bath_volume(level) + (inlets_enabled ? inlet_fill_volume(level) : 0);

// Circular section outside the bath's front wall. The overlap with the bath
// is excluded, so the same liquid is never counted twice.
function circle_below_y(r, y) = y <= -r ? 0 : y >= r ? PI * r * r :
    r * r * (90 + asin(y / r)) * PI / 180 + y * sqrt(max(0, r * r - y * y));
function inlet_area_at(z, cy, r) = circle_below_y(r, bath_front_y(z) - cy);
function inlet_interval_volume(a, b, level, steps = 8) =
    level <= a[0] ? 0 :
    let(top = min(level, b[0]), dz = (top - a[0]) / steps)
    dz * sum_values([for (i = [0 : steps - 1])
        let(z = a[0] + (i + 0.5) * dz, t = (z - a[0]) / (b[0] - a[0]))
        inlet_area_at(z, interpolate(a[1], b[1], t), interpolate(a[2], b[2], t))]);
function sum_values(v, i = 0) = i == len(v) ? 0 : v[i] + sum_values(v, i + 1);
function inlet_fill_volume(level = fill_z) = sum_values([
    for (i = [0 : len(inlet_stations) - 2])
        inlet_interval_volume(inlet_stations[i], inlet_stations[i + 1], level)]);
// Volume of the shallow bowl pool above the start of the flare.
function inlet_bowl_volume(level) = sum_values([
    for (i = [inlet_path_steps : len(inlet_stations) - 2])
        inlet_interval_volume(inlet_stations[i], inlet_stations[i + 1], level)]);
function level_for_volume(volume, loaded = false,
        lo = floor_z + floor_round, hi = max_fill_z, iterations = 22) =
    iterations == 0 ? (lo + hi) / 2 :
    let(mid = (lo + hi) / 2,
        capacity = liquid_capacity(mid) - (loaded ? paper_displacement(mid) : 0))
    capacity < volume ? level_for_volume(volume, loaded, mid, hi, iterations - 1) :
        level_for_volume(volume, loaded, lo, mid, iterations - 1);

function greatest_common_divisor(a, b) = b == 0 ? a : greatest_common_divisor(b, a % b);
function rounded_working_ml(volume, parts, max_adjustment, max_volume = 1e99, min_volume = 0) =
    let(batch = (parts[0] + parts[1]) / greatest_common_divisor(parts[0], parts[1]),
        candidate = round(volume / batch) * batch)
    abs(candidate - volume) <= max_adjustment && candidate <= max_volume && candidate >= min_volume ? candidate :
        max(ceil(min_volume), min(round(volume), floor(max_volume)));
function whole_mix_ml(total, parts) =
    let(first = round(total * parts[0] / (parts[0] + parts[1]))) [first, total - first];
