"""CadQuery 2.8 free-function port: explicit shapes, no Workplane stack."""

from cadquery.func import box, compound, fillet


def make_clip(p):
    p.validate()
    body = box(p.width, p.depth, p.height).moved(p.width / 2, p.depth / 2, 0)
    body = fillet(body, body.edges("|Z"), p.corner_radius)
    opening = box(p.width + 0.04, p.depth + 1, p.gap).moved(
        p.width / 2, p.spine + (p.depth + 1) / 2, p.lower_jaw
    )
    relief = box(p.width + 0.04, p.depth + 1, p.lower_jaw + 0.02).moved(
        p.width / 2, p.lower_reach + (p.depth + 1) / 2, -0.02
    )
    clip = body - opening - relief
    if p.root_radius:
        roots = [
            edge for edge in clip.edges("|X") if abs(edge.Center().y - p.spine) < 1e-7
        ]
        assert len(roots) == 2, "Expected exactly two jaw roots"
        clip = fillet(clip, compound(roots), p.root_radius)
    return clip
