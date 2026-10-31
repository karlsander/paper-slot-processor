#!/usr/bin/env python3
"""Per-chamber heat-loss sensitivity, not a measured temperature prediction."""
import argparse
import json
from pathlib import Path

SIGMA = 5.670374419e-8


def estimate(meta, room=22, convection=5, bath=35):
    width, depth, height = [v/1000 for v in meta['vessel_mm']]
    pw, ph, _ = [v/1000 for v in meta['plate_mm']]
    mw, mh, _ = [v/1000 for v in meta['mat_mm']]
    cw, ch, pad = [v/1000 for v in meta['pad_mm']]
    contact = cw*ch
    # Exclude the pad-covered rear wall; all other tank surfaces lose heat to air.
    exposed = 2*(width+depth)*height+2*width*depth-contact
    delta = bath-room
    def radiation(area, emissivity, temperature):
        return area*emissivity*SIGMA*((temperature+273.15)**4-(room+273.15)**4)
    # 0.25 W per chamber is an assumed slit/well evaporation and base allowance.
    bath_loss = exposed*convection*delta+radiation(exposed,.9,bath)+.25
    # Uniform mixed bath, PETG k=.20, pad k=1, liquid film h=150 (all assumptions).
    conductance = contact/(meta.get('wall_mm',3)/1000/.20+pad+1/150)
    plate = bath+bath_loss/conductance
    mat_back = mw*mh
    metal = max(0,pw*ph-mat_back)+max(0,pw*ph-contact)
    plate_loss = (mat_back+metal)*convection*(plate-room)
    plate_loss += radiation(mat_back,.9,plate)+radiation(metal,.15,plate)
    return dict(room_c=room, convection_w_m2k=convection, bath_c=bath,
                bath_loss_w=bath_loss, plate_c=plate, required_w=bath_loss+plate_loss)


def equilibrium(meta, power, room, convection):
    low, high = room, room+80
    for _ in range(60):
        mid = (low+high)/2
        if estimate(meta,room,convection,mid)['required_w'] < power:
            low = mid
        else:
            high = mid
    return (low+high)/2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('settings',type=Path)
    parser.add_argument('--power',type=float,default=5,help='Electrical watts per chamber')
    parser.add_argument('--output',type=Path,default=Path('build/v2-thermal.json'))
    args = parser.parse_args()
    if args.power <= 0:
        parser.error('--power must be positive')
    meta = json.loads(args.settings.read_text())['model_info']
    scenarios = []
    for room, convection in [(23,3),(22,5),(18,8)]:
        row = estimate(meta,room,convection)
        row['estimated_equilibrium_c'] = equilibrium(meta,args.power,room,convection)
        scenarios.append({k:round(v,2) for k,v in row.items()})
    result = dict(power_per_chamber_w=args.power, mat_mm=meta['mat_mm'],
        ideal_water_warming_c_per_minute=round(args.power*60/(meta['bath_ml']/1000*4180),3),
        assumptions={'target_c':35,'water_cp_j_kgk':4180,'petg_k_w_mk':.20,
            'pad_k_w_mk':1,'liquid_film_h_w_m2k':150,'mat_emissivity':.9,
            'vessel_emissivity':.9,'bare_metal_emissivity':.15,'additional_loss_w':.25},
        scenarios=scenarios,
        limitations=['Uncalibrated steady-state calculation; no measured contact resistance or vertical gradients.',
            'Uniform plate and mixed-liquid temperatures are assumed. Wider overhang adds heat loss and spreading resistance is not modeled.',
            'Adjacent modules exchange heat through their surroundings; this isolated-module estimate does not model that coupling.',
            'No heater product compatibility or achievable temperature is certified. Prewarm and measure the actual bath.'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
