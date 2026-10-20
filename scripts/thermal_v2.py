#!/usr/bin/env python3
"""Sensitivity calculation, not a calibrated thermal simulation or heater certification."""
import argparse
import json
from pathlib import Path

SIGMA = 5.670374419e-8

def estimate(meta, room=22, convection=5, insulation_mm=0, bath=35):
    width,depth,height = [v/1000 for v in meta['vessel_mm']]
    pw,ph,pt = [v/1000 for v in meta['plate_mm']]
    mw,mh,mt = [v/1000 for v in meta['mat_mm']]
    cw,ch,pad = [v/1000 for v in meta['pad_mm']]
    contact = 2*cw*ch
    # Deliberately exposed bottom guides and upper well zones leave 30% bare.
    vessel_area = 2*((width+2*depth)*height+width*depth)
    covered = vessel_area*0.7 if insulation_mm else 0
    delta = bath-room
    rad = lambda area,emissivity,t: area*emissivity*SIGMA*((t+273.15)**4-(room+273.15)**4)
    air_h = convection + (rad(1,.9,bath)/delta if delta else 5.5)
    bare_loss = (vessel_area-covered)*air_h*delta
    jacket_loss = covered*delta/(insulation_mm/1000/.04 + 1/air_h) if covered else 0
    # 0.5 W is an assumed allowance for the small open slit/wells plus base conduction.
    bath_loss = bare_loss+jacket_loss+0.5
    # Assumed PETG k=.20 W/mK, pad k=1, water film h=150 W/m2K, 3 mm wall.
    conductance = contact/(.003/.20+pad/1+1/150)
    plate = bath+bath_loss/conductance
    # Mat back high emissivity; uncovered aluminium margins assumed emissivity .15.
    mat_back = mw*mh
    margin = max(0,pw*ph-mat_back)
    front = max(0,pw*ph-contact)
    plate_loss = (mat_back+margin+front)*convection*(plate-room)
    plate_loss += rad(mat_back,.9,plate)+rad(margin+front,.15,plate)
    power = bath_loss+plate_loss
    return dict(room_c=room,convection_w_m2k=convection,jacket_mm=insulation_mm,bath_c=bath,
                bath_loss_w=round(bath_loss,2),plate_c=round(plate,2),required_w=round(power,2),
                margin_at_20w=round(20-power,2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('settings',type=Path)
    parser.add_argument('--output',type=Path,default=Path('build/v2-thermal.json'))
    args=parser.parse_args()
    meta=json.loads(args.settings.read_text())['model_info']
    scenarios=[estimate(meta,*v) for v in [(23,3,0),(23,5,0),(23,5,12),(20,5,12),(18,8,12)]]
    water_kg=2*meta['bath_ml']/1000
    plate_mass=__import__('math').prod(meta['plate_mm'])*1e-9*2700
    # 0.4 kg of plastic participating is a lumped sensitivity assumption.
    heat_capacity=water_kg*4180+plate_mass*900+.4*1200
    result=dict(assumptions={'target_c':35,'water_cp_j_kgk':4180,'petg_k_w_mk':.20,
        'pad_k_w_mk':1,'liquid_film_h_w_m2k':150,'foam_k_w_mk':.04,'jacket_coverage':.7,
        'mat_emissivity':.9,'bare_metal_emissivity':.15,'additional_loss_w':.5,
        'plastic_heat_capacity_j_k':480,'wall_m':.003},
        ideal_warmup_20_to_35_minutes=round(heat_capacity*15/20/60,1),scenarios=scenarios,
        conclusion='20 W is a deliberately modest shared heater. Prewarm the mixing water to roughly 35-38 C and measure the actual equilibrium temperature. User chooses experimentally established development times. No fixed temperature guarantee; the foam scenarios are sensitivity comparisons, not required equipment.',
        limitations=['Steady, uniform plate and mixed liquid assumptions; no measured contact resistance or vertical gradients.',
        'Foam covers vessel fronts/ends only, clear of the heating mat and its ventilation; it must be removable.',
        'The stated 36-42 C mat surface range is not a regulated liquid temperature or a guarantee under this load.',
        'Ideal warmup ignores all losses; real warmup can be much longer or never reach target.'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
