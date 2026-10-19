"""Viewer schema; numeric defaults and derived values come from the CAD source."""
from build_v2 import PARTS, STANDARD_PARTS, QUANTITIES, preset_overrides

VIEWS = {'assembly': ('Assembly', 'assembly'), 'exploded': ('Exploded', 'exploded'),
         'inspect_a': ('Inspect vessel A', 'single_assembly'), 'inspect_b': ('Inspect vessel B', 'single_assembly')}
MODELS = {k: (v[0], 'v2/processor.scad', {'part': v[1], 'chamber': int(k == 'inspect_b')}) for k,v in VIEWS.items()}
MODELS.update({k: (v[0], 'v2/processor.scad', v[2] | {'part': v[1]}) for k,v in PARTS.items()})
FIELDS = [
    ('roll_width','Roll width','Paper','number',80,120,0.1,'mm'),
    ('image_aspect','Image aspect ratio','Paper','number',1.5,2.2,0.000001,':1'),
    ('paper_thickness','Paper thickness','Paper','number',0.1,0.6,0.05,'mm'),
    ('finger_grip','Grip above guide','Paper','number',6,20,1,'mm'),
    ('guide_gap','Guide slit','Paper','number',0.6,2,0.1,'mm'),
    ('vertical_stroke','Vertical travel','Agitation','number',0,12,0.5,'mm'),
    ('lateral_stroke','Travel each side','Agitation','number',0,6,0.5,'mm'),
    ('immersion_margin','Immersion reserve','Agitation','number',1,5,0.5,'mm'),
    ('side_clearance','Side clearance','Agitation','number',7,16,0.5,'mm'),
    ('bottom_clearance','Below paper','Agitation','number',4,10,0.5,'mm'),
    ('bath_gap','Chamber depth','Vessel','number',10,22,0.5,'mm'),
    ('freeboard','Slosh headroom','Vessel','number',7,12,0.5,'mm'),
    ('wall','Wall thickness','Vessel','number',2.4,5,0.2,'mm'),
    ('floor','Floor thickness','Vessel','number',3,8,0.2,'mm'),
    ('guide_fit','Guide fit clearance','Vessel','number',0.15,0.7,0.05,'mm'),
    ('sight_depth','Target visible pool','Vessel','number',0.5,2.5,0.1,'mm'),
    ('recipe_a_concentrate','A concentrate parts','Chemistry','integer',1,20,1,''),
    ('recipe_a_water','A water parts','Chemistry','integer',1,40,1,''),
    ('recipe_b_concentrate','B concentrate parts','Chemistry','integer',1,20,1,''),
    ('recipe_b_water','B water parts','Chemistry','integer',1,40,1,''),
    ('heater_thickness','Measured mat thickness','Heater','number',1,5,0.1,'mm'),
    ('heat_spreader_thickness','Metal plate thickness','Heater','number',1,3,0.1,'mm'),
    ('thermal_pad','Interface pad thickness','Heater','number',0,2,0.1,'mm'),
    ('guard_gap','Guard air gap','Heater','number',8,20,1,'mm'),
]
SCHEMA = [dict(zip(('id','label','group','type','min','max','step','unit'), f)) for f in FIELDS]
META = {
    'bath_ml':'working_ml', 'recipe_a_ml':'amounts_a','recipe_b_ml':'amounts_b',
    'slit_mm':'guide_gap','image_mm':'[roll_width,image_length]',
    'cut_mm':'[roll_width,paper_cut_length]','trim_mm':'trim_band',
    'grip_mm':'paper_top-guide_top','agitation_mm':'[vertical_stroke,lateral_stroke]',
    'immersion_mm':'level_for_volume(working_ml*1000,true,lift=vertical_stroke)-image_top-vertical_stroke',
    'freeboard_mm':'body_height-loaded_level','indicator_depth_mm':'actual_sight_depth',
    'indicator_ml':'visible_pool_ml','vessel_mm':'[body_width,body_depth,body_height]',
    'plate_mm':'[spreader_width,spreader_height,heat_spreader_thickness]',
    'mat_mm':'[heater_width,heater_height,heater_thickness]',
    'pad_mm':'[body_width-4,body_height-12,thermal_pad]',
}
ARTIFACTS = {'model.stl','liquid.stl','paper.stl','loaded.stl','details.stl','hardware.stl','plate.3mf','settings.json','print-files.zip'}
