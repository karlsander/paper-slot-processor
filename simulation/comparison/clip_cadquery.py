"""CadQuery Workplane port, using the same geometry and root selection rule."""

import cadquery as cq


def make_clip(p):
    p.validate()
    body = (
        cq.Workplane("XY")
        .box(p.width, p.depth, p.height, centered=False)
        .edges("|Z")
        .fillet(p.corner_radius)
    )
    opening = (
        cq.Workplane("XY")
        .box(p.width + 0.04, p.depth + 1, p.gap, centered=False)
        .translate((-0.02, p.spine, p.lower_jaw))
    )
    relief = (
        cq.Workplane("XY")
        .box(p.width + 0.04, p.depth + 1, p.lower_jaw + 0.02, centered=False)
        .translate((-0.02, p.lower_reach, -0.02))
    )
    clip = body.cut(opening).cut(relief)
    if p.root_radius:
        roots = clip.edges("|X").filter(
            lambda edge: abs(edge.Center().y - p.spine) < 1e-7
        )
        assert roots.size() == 2, "Expected exactly two jaw roots"
        clip = roots.fillet(p.root_radius)
    return clip.val()
