# Numerical force-study summary

These are elastic model results, not measured holding capacities. Read the material, fixture and strength limits in [the study report](README.md).

## Contact cases

Normal is the mean absolute vertical reaction of the two jaws. Pull is the reaction at 0.15 mm outward movement, not a demonstrated steady sliding limit. Peak jaw stresses exclude elements whose corner centroid is at Y >= 24.5 mm, avoiding the concentrated back-support singularities.

| Case | Seated normal N/jaw | Pull at 0.15 mm N | Seated jaw XY tension MPa | Seated jaw Z tension MPa | Max penetration at final step mm |
|---|---:|---:|---:|---:|---:|
| contact-0.55-0.3-side1 | 24.06 | 8.845 | 83.8 | 53.54 | 0.007629 |
| contact-0.4-0.3-side1 | 23.41 | 8.286 | 85.49 | 74.72 | 0.007027 |
| contact-0.55-0.3-side-1 | 135.3 | 13.78 | 85.16 | 71.72 | 0.007626 |
| contact-0.4-0.3-side-1 | 131.7 | 12.35 | 92.32 | 109 | 0.007223 |
| contact-0.55-0-side1 | 19.39 | 1.385e-16 | 81.31 | 45.41 | 0.0022 |
| contact-0.55-0.6-side1 | 24.09 | 10.63 | 83.82 | 53.59 | 0.007903 |
| contact-0.55-0.3-side1-K200000 | 24.79 | 9.421 | 83.99 | 54.58 | 0.005727 |
| contact-0.55-0.3-side1-E0.7 | 17.13 | 6.4 | 58.7 | 37.88 | 0.006604 |
| contact-0.55-0.3-side-1-E0.7 | 96.76 | 10.22 | 60.48 | 51.07 | 0.00643 |
| contact-0.55-0.3-side1-mates20-mortar | 4.885 | 2.411 | 23.36 | 13.27 | 4.832e-06 |
| contact-0.4-0.3-side1-mates20-mortar | 4.797 | 2.372 | 24.1 | 19.06 | 2.415e-06 |
| contact-0.55-0.3-side-1-mates20-mortar | 5.031 | 2.544 | 18.65 | 10.09 | 2.211e-06 |
| contact-0.55-0.3-side1-E0.7-mates20-mortar | 3.422 | 1.688 | 16.28 | 9.277 | 3.386e-06 |

The 51 MPa XY and 35 MPa Z reference values are ultimate tensile strengths, not permissible service stresses. Rigid-frame contact cases exceed those references; their forces are elastic demand only. Numerical friction and pressure parameters are uncalibrated.

## Refinement

| Coarse → fine | Quantity | Step | Relative change |
|---|---|---:|---:|
| index-0.55 → index-0.4 | actuation force | 4 | 0.0659% |
| index-tip-0.12 → index-tip-0.085 | actuation force | 4 | 1.19% |
| guide-0.3 → guide-0.2 | actuation force | 4 | 0.0118% |
| roof-0.3 → roof-0.2 | actuation force | 4 | 0.177% |
| clip-catch-0.3 → clip-catch-0.22 | actuation force | 4 | 0.716% |
| contact-0.55-0.3-side1 → contact-0.4-0.3-side1 | normal_force_per_jaw_n | 1 | 2.73% |
| contact-0.55-0.3-side1 → contact-0.4-0.3-side1 | normal_force_per_jaw_n | 3 | 1.17% |
| contact-0.55-0.3-side1 → contact-0.4-0.3-side1 | pull_force_n | 3 | 6.32% |
| contact-0.55-0.3-side-1 → contact-0.4-0.3-side-1 | normal_force_per_jaw_n | 1 | 2.67% |
| contact-0.55-0.3-side-1 → contact-0.4-0.3-side-1 | normal_force_per_jaw_n | 3 | 1.81% |
| contact-0.55-0.3-side-1 → contact-0.4-0.3-side-1 | pull_force_n | 3 | 10.4% |
| contact-0.55-0.3-side1-mates20-mortar → contact-0.4-0.3-side1-mates20-mortar | normal_force_per_jaw_n | 1 | 1.8% |
| contact-0.55-0.3-side1-mates20-mortar → contact-0.4-0.3-side1-mates20-mortar | normal_force_per_jaw_n | 3 | 1.56% |
| contact-0.55-0.3-side1-mates20-mortar → contact-0.4-0.3-side1-mates20-mortar | pull_force_n | 3 | 1.6% |

Force refinement does not establish peak-stress convergence at sharp roots, edges or point supports. Contact pull reactions retain greater mesh/penalty sensitivity than spring reactions, so no precise holding-force rating is assigned.

## Run integrity

30 accepted studies. Every listed run completed every requested step and passed the reaction-balance check. Input, FRD, DAT, log and mesh hashes are retained in results.json. Failed development runs are excluded.
