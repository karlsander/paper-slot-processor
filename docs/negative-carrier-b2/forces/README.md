# B2 force study

These are solved solid-element finite-element models of the B2 CAD geometry,
using CalculiX 2.23 and quadratic C3D10 tetrahedra. The mechanism video is a
separate prescribed-motion render. Neither the video nor this study establishes
physical fit or exposure-to-exposure registration in the real enlarger.

## Models and load cases

| Model | Boundary conditions and loading | What it addresses |
|---|---|---|
| Film-edge wedge | Actual 24 mm frame section; base/lid held at their film-side cut; wedge guided laterally and advanced 0.25, 0.5, 1, 0.5, 0 mm | Local jaw/frame compliance, seating and withdrawal with friction |
| Narrow 110 holder | Same edge wedge moved inward beside the 110 film margin | Check the corrected small-format force path |
| Docking wedge | Actual crossbar/flange sections held at their remote cuts; both jaws and the flange/receiver interface in contact | Local docking clamp and withdrawal loads |
| Docking travel limit | Same local clamp at 2 mm travel, where the integral stop first touches | Jaw load at the travel limit; not force applied after hitting the stop |
| Index shoe and tapered bearing | Rail cut at Y=43 held in Y/Z but free in X; screw head's remote cut guided on its axis; free shoe between cone and three notch faces | 2, 5 and 10 N seating, and ±2 N rail disturbance at 5 N preload |
| Screw and nut separately | One engaged turn carries the full 5, 15 or 30 N axial load; actual helical solids | Structural screening under deliberately concentrated bearing loads |

The index contact uses zero friction: lateral location must come from the notch
geometry. The frame clamp uses assumed friction coefficients 0.3 and 0.1; the
dock also has a zero-friction control. The friction coefficients are not measured
properties of these prints. Withdrawal reactions are values along the stated
displacement cycle, not measured whole-cartridge pull-out ratings. The six
clamps' load sharing, film compression and film/holder friction are not solved.

The screw/nut cases are **prescribed-bearing structural screens**, not a solved
distribution of contact across the mating threads. An attempted full helical
contact model produced unreliable projection/convergence behaviour and was
rejected. Its results are excluded from the report and deliverable. Tightening
torque, backdrive, thread stripping, wear and repeated use remain unvalidated.

## Design decisions from the solved cases

The remote front-key layout was discarded because the thin frame bent between
the key and film. The final six wedges act beside the film margins. The refined
35 mm local model gives **1.24 N film-side reaction at 0.5 mm snugging travel**
and 3.01 N at 1 mm. Refining from 1.2 to 0.8 mm mesh size changes those reactions
by approximately 4%; these are reactions at one modeled section, not measured
film pressure or the retention force of the complete holder.

The 110 clamps and sleeve supports move inward with the film width. At the same
1.2 mm mesh size and 0.5 mm travel, this gives 1.286 N versus 1.287 N for 35 mm.
The discarded wide-span 110 version gave only about 0.10 N. Its apparent
closure was therefore not sufficient evidence of useful clamping.

The docking wedge now has longer jaws and a 2 mm travel stop. Thick short jaws
needed about 40 N at 0.5 mm travel; thinning them alone still needed about 20 N.
The refined final wedge needs 0.95 N at 0.5 mm and 1.91 N at 1 mm; refinement
changes these drive forces by about 1.4%. With the assumed friction coefficient
0.3, withdrawal back to 0.5 mm requires approximately 0.80 N in the opposite
direction. The zero-friction control does not retain the wedge, confirming that
retention depends on the actual printed surfaces.
The final 2 mm travel-limit case needs **3.81 N drive force**, with a peak
integration-point von Mises stress of 4.86 MPa. This is a displacement-controlled
local model up to first contact with the stop, not a prediction of arbitrary
force applied against the stop.

The indexing screw now seats on a broad taper in the shoe. Clearance around
the capture flange remains available for assembly and lifting, but no longer
serves as the lateral locating surface. The receiver also gains broad bevelled
side references and a rear stop so that docking location has geometric support.
The local index fixture assumes a guided screw axis. Radial play or eccentric
seating of the printed screw/nut is not included; repeatability must therefore
be checked with the complete printed sleeve, rather than inferred from the
small local deflections alone.

At 5 N seating force, the refined rail moves about +0.00198/−0.00193 mm relative
to its seated position under ±2 N disturbance. Coarse-to-fine changes in these
increments are approximately 10% and 20%. **Index contact compliance is not
fully mesh-converged.** Axial seating displacement is especially sensitive:
the two meshes differ by about 0.001 mm, corresponding to 48–52% at 5 N and
500% at 2 N; at 10 N the difference is 11%. These figures remain in the report
and are not used as a micron-level registration claim or a seating-force rating.
The prescribed 4.8 mm release motion and 0.9 mm nominal rail clearance are much
larger than these local elastic movements, but real printing/assembly variation
is still unmeasured.

At 30 N axial load, the refined prescribed-bearing screens give peak von Mises
values of **4.80 MPa in the screw and 5.39 MPa in the nut**. These are screening
results under the stated constraints, not thread load ratings.
Their force-weighted loading-patch displacements change by approximately 1.0%
and 0.8%, respectively, between the two meshes. Peak stresses change by about
3.6% and 7%; they are not strength allowables.

## Material and temperature

The baseline uses Bambu PETG Basic's published XY and Z tensile moduli of
2780 and 2550 MPa. Poisson ratio 0.38 and the shear moduli are estimates. Layer
directions match the proposed STL orientations: wedge layers normal to model Y,
nut/sleeve layers normal to X, other parts normal to Z. Integration-point tensors
are transformed from the solver's material-local coordinates before reporting.

The service target is **35 °C**. The manufacturer does not provide a suitable
printed-material temperature-dependent constitutive law or creep/relaxation
data. A 70% stiffness case is a sensitivity scenario, **not calibrated 35 °C
behaviour or a guaranteed lower bound**. No thermal field, plasticity, damage,
creep or fatigue model is invented. Published mean strengths are not design
allowables; a von Mises value below a tensile strength does not establish printed
part safety. Layer-normal tensile peaks are included separately in the data.

Source: [Bambu PETG Basic technical data sheet](https://store.bblcdn.com/s1/default/cb94589bf7994fdcbfa833badefae9cd/Bambu_PETG_Basic_Technical_Data_Sheet.pdf).

## Numerical checks

The study requires valid native solids, positive tetrahedral corner and quadrature Jacobians,
mesh/native volume agreement within 1.5%, solver completion without errors,
all requested load steps and independently balanced reactions. Mesh refinement
is reported for the index, film wedge, dock, screw and nut. Sharp-edge peak
stress changes are retained rather than treated as converged allowables.
Curved C3D10 volume is integrated using the five-point tetrahedron rule; a
corner-only volume would underestimate the small curved bearing head. Additional
checks include the four stiffness integration points and a regression that
rejects an inverted midside node even when the corner orientation is positive.

The 110 model omits the separated base/lid contact pair to avoid an unnecessary
contact search across the gap. It checks a conservative remaining Z gap after
deformation at every step. Docking drive force is reported separately from the
flange's remote support reaction: much of the clamp load closes locally through
the flange/receiver contact, so that remote Z reaction is not total jaw preload.

Contact uses the geometrically nonlinear mortar formulation. The normal penalty
is 100000 N/mm³, with finite tangential regularization for friction. Actual
constrained degrees of freedom are used when summing reactions. CalculiX adds
the mortar contact contribution to the FRD force field after writing the DAT
output; using the uncorrected DAT set sum at supported contact nodes can give
an apparent imbalance. The report preserves that DAT sum but uses corrected
FRD reactions for equilibrium and clamp loads. See the
[CalculiX manual](https://www.dhondt.de/ccx_2.23.pdf) and the upstream
[mortar output correction](https://github.com/Dhondtguido/CalculiX/blob/00fc77776204f919f81b86a80b42fbc54af1d314/src/mortar_prefrd.c).

Force balance tolerance is max(0.0001 N, 0.5% of the external load). Integration
point stresses are reported without nodal smoothing. A separate solid-cantilever
benchmark checks the common solver pipeline against elementary beam theory.
Its reaction is 0.006996 N versus 0.006950 N from the beam calculation, a 0.66%
difference; the computed resultant imbalance is below 2 × 10⁻¹⁵ N.

## Inspect and reproduce

- [Numerical results and mesh comparisons](results.json)
- [Force plots](force-summary.png)
- [Native FreeCAD FEM import/reopen checks](freecad-results.json)

```sh
python -m pip install -r cad/requirements-fem.txt
python -m cad.negative_carrier_b2.suite --native --package
```

`suite.py` names the accepted study matrix explicitly; abandoned development
folders are never swept into the report. Each result carries input-deck, FRD,
CAD-source and mesh hashes. The ZIP contains compact/full STEP and oriented STL
parts, native assemblies, actual input decks and solved fields. Five refined
representative studies are also imported into FreeCAD FEM, saved and reopened.

Before printing a complete set, check a wedge/rail and screw/nut coupon in the
specified orientations. Then measure real-machine clearance, film retention,
repeated frame positioning and preload loss at approximately 35 °C. Those are
the remaining physical acceptance steps; they are not substituted by CAD motion.
