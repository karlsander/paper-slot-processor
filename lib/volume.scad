// Nominal liquid volume up to fill_z, before paper/tong displacement, in mm3.
// The rounded bath is analytic. Integrate the inlet's horizontal sections,
// subtracting its overlap with the passage and the main bath exactly once.
function rounded_bath_volume(w, d, r, h) =
    (w * d - (4 - PI) * r * r) * (h - r) +
    (w - 2 * r) * (d - 2 * r) * r +
    (w + d - 4 * r) * PI * r * r / 2 + 2 * PI * r * r * r / 3;

function circle_primitive(r, y) =
    y * sqrt(max(0, r * r - y * y)) + r * r * asin(y / r) * PI / 180;
// Area in the upper half of a circle between x=-half_width and x=half_width,
// from its centre line to y. Inputs outside the circle are clamped.
function circle_strip_area(r, half_width, y) =
    let(p = min(r, half_width), t = sqrt(max(0, r * r - p * p)),
        v = min(r, max(0, y)))
    v <= t ? 2 * p * v : 2 * p * t + circle_primitive(r, v) - circle_primitive(r, t);

function inlet_liquid_area(z) =
    let(span = inlet_offset + wall_thickness + 2,
        y0 = max(-inlet_offset, (pool_z - z) * span / inlet_drain_drop - inlet_offset),
        y1 = min(wall_thickness,
            (pool_z + inlet_channel_height - z) * span / inlet_drain_drop - inlet_offset),
        channel = inlet_pool_diameter * max(0, y1 - y0),
        r = z < pool_z ? 0 : inlet_pool_diameter / 2 +
            (inlet_opening_diameter - inlet_pool_diameter) / 2 *
            min(1, (z - pool_z) / (inlet_land_z - pool_z)),
        overlap = r == 0 || y1 <= y0 ? 0 :
            circle_strip_area(r, inlet_pool_diameter / 2, y1 + inlet_offset) -
            circle_strip_area(r, inlet_pool_diameter / 2, y0 + inlet_offset))
    PI * r * r + channel - overlap;

function sum_values(v, i = 0) = i == len(v) ? 0 : v[i] + sum_values(v, i + 1);
function inlet_fill_volume(level = fill_z, steps = 128) =
    let(z0 = pool_z - inlet_drain_drop, dz = (level - z0) / steps)
    dz * sum_values([for (i = [0 : steps - 1]) inlet_liquid_area(z0 + (i + 0.5) * dz)]);

function greatest_common_divisor(a, b) = b == 0 ? a : greatest_common_divisor(b, a % b);
function rounded_working_ml(volume, parts, max_adjustment, max_volume = 1e99) =
    let(batch = (parts[0] + parts[1]) / greatest_common_divisor(parts[0], parts[1]),
        candidate = round(volume / batch) * batch)
    abs(candidate - volume) <= max_adjustment && candidate <= max_volume ? candidate :
        min(round(volume), floor(max_volume));
function whole_mix_ml(total, parts) =
    let(first = round(total * parts[0] / (parts[0] + parts[1]))) [first, total - first];
