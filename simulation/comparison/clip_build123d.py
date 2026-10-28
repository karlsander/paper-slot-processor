"""build123d algebra port, with optional fillets at the two inner jaw roots."""

import build123d as bd


def make_clip(p):
    p.validate()
    minimum = (bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)
    body = bd.Box(p.width, p.depth, p.height, align=minimum)
    body = bd.fillet(body.edges().filter_by(bd.Axis.Z), p.corner_radius)
    opening = bd.Pos(-0.02, p.spine, p.lower_jaw) * bd.Box(
        p.width + 0.04, p.depth + 1, p.gap, align=minimum
    )
    relief = bd.Pos(-0.02, p.lower_reach, -0.02) * bd.Box(
        p.width + 0.04, p.depth + 1, p.lower_jaw + 0.02, align=minimum
    )
    clip = body - opening - relief
    if p.root_radius:
        roots = (
            clip.edges()
            .filter_by(bd.Axis.X)
            .filter_by(lambda edge: abs(edge.center().Y - p.spine) < 1e-7)
        )
        assert len(roots) == 2, "Expected exactly two jaw roots"
        clip = bd.fillet(roots, p.root_radius)
    return clip
