#!/usr/bin/env python3
"""Check sampled deposited paths for bed bounds and support inside the wet cavity.

Samples linear and XY circular moves at <=0.25 mm spacing. This is a geometric
check of centre lines, not proof of clean support removal or print quality.
"""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import numpy as np
import build_openscad as build
ROOT=Path(__file__).resolve().parents[1]

def config(aspect):
    path=ROOT/'build/v2-toolpath-config.scad'
    path.write_text('include <../v2/parameters.scad>\necho(cfg=[body_width,body_depth,body_height,wall,floor,inside_radius,vessel_xmax,rim_overhang,print_tilt,vessel_print_bounds,well_stations]); cube(.1);\n')
    result=subprocess.run([build.OPENSCAD,'-D',f'image_aspect={aspect}','-o',str(path.with_suffix('.csg')),str(path)],capture_output=True,text=True,check=True)
    return json.loads(re.search(r'cfg = (\[.*\])',result.stderr)[1])

def check(path,aspect,chamber):
    w,d,h,wall,floor,r,xmax,rim,tilt,bounds,stations=config(aspect)
    angle=math.radians(tilt); co,si=math.cos(angle),math.sin(angle)
    offset=np.array([(180-bounds[0])/2+(xmax-w if chamber==0 else rim),
                     (180-bounds[1])/2+h*si+rim*co,0])
    stations=np.array(stations)
    p=np.zeros(3); e=0.; relative_e=True; feature='Custom'
    count=0; minimum=np.full(3,float('inf')); maximum=np.full(3,-float('inf')); support=[]
    for line in path.read_text().splitlines():
        if line.startswith('; FEATURE:'): feature=line.split(':',1)[1].strip()
        code=line.split(';',1)[0].strip()
        if code=='M83': relative_e=True
        if code=='M82': relative_e=False
        if code.startswith('G92 E'): e=float(code.split('E')[1])
        match=re.match(r'^(G[0123])\s',code)
        if not match: continue
        data={k:float(v) for k,v in re.findall(r'([XYZEFIJ])(-?[\d.]+)',code.replace('  ',' ')) if k.strip()}
        q=np.array([data.get(k,p[i]) for i,k in enumerate('XYZ')])
        deposited=data.get('E',0) if relative_e else data.get('E',e)-e
        if 'E' in data: e=data['E'] if not relative_e else e+data['E']
        if deposited>0 and ('X' in data or 'Y' in data) and feature!='Custom':
            if match[1] in ('G2','G3') and ('I' in data or 'J' in data):
                center=p[:2]+np.array([data.get('I',0),data.get('J',0)])
                radius=np.linalg.norm(p[:2]-center)
                a=math.atan2(p[1]-center[1],p[0]-center[0]); b=math.atan2(q[1]-center[1],q[0]-center[0])
                sweep=(b-a)%(2*math.pi) if match[1]=='G3' else -((a-b)%(2*math.pi))
                n=max(2,math.ceil(abs(sweep)*radius/.25)+1)
                theta=np.linspace(a,a+sweep,n)
                samples=np.column_stack([center[0]+radius*np.cos(theta),center[1]+radius*np.sin(theta),np.linspace(p[2],q[2],n)])
            else:
                samples=np.linspace(p,q,max(2,math.ceil(np.linalg.norm(q-p)/.25)+1))
            count += len(samples); minimum=np.minimum(minimum,samples.min(0)); maximum=np.maximum(maximum,samples.max(0))
            if feature.startswith('Support'): support.extend(samples)
        p=q
    support=np.array(support)
    assert count and len(support), 'No deposited/support paths found'
    assert minimum[:2].min()>=0.25 and maximum[:2].max()<=179.75, f'Bed extrusion bounds: {minimum}, {maximum}'
    assert maximum[2]<=178.2, 'Height margin lost'
    local=support-offset
    local[:,[1,2]]=local[:,[1,2]] @ np.array([[co,-si],[si,co]])
    low=np.array([wall+r,wall+r,floor+r]); high=np.array([w-wall-r,d-wall-r,h+10])
    bath=np.linalg.norm(np.maximum(np.maximum(low-local,local-high),0),axis=1)<r-.25
    z=local[:,2]; x=w-local[:,0] if chamber==0 else local[:,0]
    cx=np.interp(z,stations[:,0],stations[:,1]); rad=np.interp(z,stations[:,0],stations[:,2])
    well=(z>stations[0,0]+.25)&(z<h-.25)&((x-cx)**2+(local[:,1]-d/2)**2 < (rad-.25)**2)
    bad=local[bath|well]
    assert not len(bad), f'{len(bad)} support samples enter wet cavity, first: {bad[:5]}'
    return dict(path=str(path),aspect=aspect,chamber=chamber,samples=count,support_samples=len(support),
                deposited_bounds_mm=[minimum.tolist(),maximum.tolist()],wet_cavity_support_samples=0,
                sampling_mm=.25,interior_margin_mm=.25)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gcode',type=Path); parser.add_argument('--aspect',type=float,default=16/9)
    parser.add_argument('--chamber',type=int,choices=[0,1],default=0)
    args=parser.parse_args(); print(json.dumps(check(args.gcode,args.aspect,args.chamber),indent=2))
if __name__=='__main__': main()
