import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { Revision, restoreParameters } from './state.js';

const $ = id => document.getElementById(id);
const revision = new Revision();
const fmt = (v, digits = 1) => Number(v).toLocaleString(undefined, { maximumFractionDigits: digits });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let config, parameters, model = 'assembly', timer, currentMesh, liquidMesh, loadedMesh, paperMesh, lastMeshJob, changed = true;
let cutaway = false, bedVisible = true, fillVisible = false, paperVisible = false;
const storageKey = 'processor-modular-v2-parameters'; // Separate from the legacy monolithic processor.

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 3000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;
renderer.setClearColor(0x000000, 0);
$('canvas').appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.minDistance = 15;
controls.maxDistance = 1800;
controls.addEventListener('change', () => { changed = true; });
scene.add(new THREE.HemisphereLight(0xffffff, 0x566563, 2.8));
const light = new THREE.DirectionalLight(0xffffff, 3.5);
light.position.set(100, 240, 160);
light.castShadow = true;
light.shadow.mapSize.set(2048, 2048);
Object.assign(light.shadow.camera, { left: -150, right: 150, top: 160, bottom: -160, near: 1, far: 700 });
light.shadow.bias = -0.0005;
scene.add(light);
const rim = new THREE.DirectionalLight(0xd6f4ef, 2);
rim.position.set(-150, 100, -150);
scene.add(rim);
const bedGroup = new THREE.Group();
const floor = new THREE.Mesh(new THREE.PlaneGeometry(180, 180), new THREE.ShadowMaterial({ opacity: 0.13 }));
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.15;
floor.receiveShadow = true;
bedGroup.add(floor);
const grid = new THREE.GridHelper(180, 18, 0xbdc8c1, 0xd4dcd5);
grid.position.y = -0.1;
grid.material.transparent = true;
grid.material.opacity = 0.55;
bedGroup.add(grid);
scene.add(bedGroup);
const clip = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);

function resize() {
  const { width, height } = $('canvas').getBoundingClientRect();
  renderer.setSize(width, height);
  camera.aspect = width / Math.max(height, 1);
  camera.updateProjectionMatrix();
  changed = true;
}
new ResizeObserver(resize).observe($('canvas'));
renderer.setAnimationLoop(() => {
  if (document.hidden) return;
  controls.update();
  if (changed) { renderer.render(scene, camera); changed = false; }
});

function setView(view = 'perspective') {
  const size = currentMesh ? new THREE.Box3().setFromObject(currentMesh).getSize(new THREE.Vector3()) : new THREE.Vector3(144, 145, 132);
  const target = new THREE.Vector3(0, size.y * 0.43, 0);
  const distance = Math.max(size.x, size.y, size.z, 75) * 2.6;
  const direction = view === 'top' ? new THREE.Vector3(0, 1, 0.001) : view === 'front' ? new THREE.Vector3(0, 0.05, 1) : new THREE.Vector3(0.85, 0.7, 1.2);
  controls.target.copy(target);
  camera.position.copy(target).add(direction.normalize().multiplyScalar(distance));
  controls.update();
  changed = true;
}
setView();
$('home-view').onclick = () => setView();
$('top-view').onclick = () => setView('top');
$('front-view').onclick = () => setView('front');
$('cutaway').onclick = () => {
  cutaway = !cutaway;
  $('cutaway').setAttribute('aria-pressed', String(cutaway));
  if (currentMesh) currentMesh.traverse(node => { if (node.isMesh) node.material.clippingPlanes = cutaway ? [clip] : []; });
  for (const node of [liquidMesh, loadedMesh, paperMesh]) if (node) node.material.clippingPlanes = cutaway ? [clip] : [];
  changed = true;
};
$('fill-level').onclick = () => {
  fillVisible = !fillVisible;
  $('fill-level').setAttribute('aria-pressed', String(fillVisible));
  updateOverlays();
  changed = true;
};
function updateOverlays() {
  if (liquidMesh) liquidMesh.visible = fillVisible && !paperVisible;
  if (loadedMesh) loadedMesh.visible = fillVisible && paperVisible;
  if (paperMesh) paperMesh.visible = paperVisible;
  changed = true;
}
$('paper-view').onclick = () => {
  paperVisible = !paperVisible;
  $('paper-view').setAttribute('aria-pressed', String(paperVisible));
  updateOverlays();
};
$('bed').onclick = () => {
  bedVisible = !bedVisible;
  bedGroup.visible = bedVisible;
  $('bed').setAttribute('aria-pressed', String(bedVisible));
  changed = true;
};

function link(id, job, filename, enabled) {
  const node = $(id);
  node.classList.toggle('disabled', !enabled);
  node.setAttribute('aria-disabled', String(!enabled));
  if (enabled) { node.href = `/artifacts/${job.id}/${filename}`; node.download = filename; }
  else node.removeAttribute('href');
}
function status(text, kind = '') {
  $('status').textContent = text;
  $('status').className = kind;
}
function clearResults() {
  for (const id of ['print-time', 'print-weight', 'print-volume']) $(id).textContent = '—';
  for (const id of ['solid-volume', 'bath-volume', 'slit-info', 'indicator-info', 'paper-info', 'agitation-info', 'capacity-info', 'plate-note']) $(id).textContent = '';
  for (const id of ['download-stl', 'download-3mf', 'download-settings']) link(id, null, '', false);
  $('error').hidden = true;
  $('viewport').classList.add('stale');
  $('dimensions').textContent = currentMesh ? 'Previous preview · updating…' : 'Loading model…';
  $('loading').hidden = false;
  $('loading-text').textContent = 'Updating the model';
}
function error(message) {
  $('error').textContent = message;
  $('error').hidden = false;
  $('loading').hidden = true;
  if ($('viewport').classList.contains('stale')) $('dimensions').textContent = currentMesh ? 'Previous preview · not current' : 'No preview available';
  status('Needs attention', 'failed');
}

async function display(job, version) {
  if (!revision.current(version)) return;
  const labels = { queued: 'Queued', rendering: 'Building preview', slicing: 'Calculating print estimates', ready: 'Up to date', preview_only: 'Preview ready', superseded: 'Build superseded' };
  status(labels[job.state] || 'Build failed', job.state === 'ready' ? 'ready' : '');
  if (job.stage_detail && job.state === 'slicing') status(job.stage_detail);
  if (job.mesh && lastMeshJob !== job.id) {
    const loader = new STLLoader();
    const files = [{file:'model.stl',color:'#367e78'}, ...(job.layers || [])];
    if (job.liquid) files.push({file:'liquid.stl',color:'#5aaee0',overlay:'liquid'}, {file:'loaded.stl',color:'#5aaee0',overlay:'loaded'});
    if (job.paper) files.push({file:'paper.stl',color:'#eee8cf',overlay:'paper'});
    const geometries = await Promise.all(files.map(async item => {
      const response = await fetch(`/artifacts/${job.id}/${item.file}`);
      if (!response.ok) throw new Error('Could not load the preview. Update again.');
      const geometry = loader.parse(await response.arrayBuffer());
      geometry.rotateX(-Math.PI / 2);
      return {...item, geometry};
    }));
    if (!revision.current(version)) { geometries.forEach(g => g.geometry.dispose()); return; }
    const group = new THREE.Group();
    const overlays = {};
    for (const item of geometries) {
      const water = item.overlay === 'liquid' || item.overlay === 'loaded';
      const node = new THREE.Mesh(item.geometry, new THREE.MeshStandardMaterial({
        color:item.color, metalness:item.file === 'hardware.stl' ? 0.5 : 0.08, roughness:water ? 0.2 : 0.58,
        transparent:water, opacity:water ? 0.65 : 1, depthWrite:!water,
        clippingPlanes:cutaway ? [clip] : [], clipShadows:true, side:THREE.DoubleSide
      }));
      node.castShadow = !water; node.receiveShadow = !water;
      if (item.overlay) overlays[item.overlay] = node; else group.add(node);
    }
    const bounds = new THREE.Box3().setFromObject(group);
    const center = bounds.getCenter(new THREE.Vector3());
    const offset = new THREE.Vector3(-center.x,-bounds.min.y,-center.z);
    group.position.copy(offset);
    for (const node of Object.values(overlays)) node.position.copy(offset);
    const first = !currentMesh;
    const plateChanged = currentMesh?.userData.plate !== model;
    for (const old of [currentMesh,liquidMesh,loadedMesh,paperMesh]) if (old) {
      scene.remove(old); old.traverse(node => { if (node.isMesh) { node.geometry.dispose(); node.material.dispose(); } });
    }
    currentMesh = group; liquidMesh = overlays.liquid; loadedMesh = overlays.loaded; paperMesh = overlays.paper;
    scene.add(group); Object.values(overlays).forEach(node => scene.add(node));
    $('fill-level').disabled = !liquidMesh; $('paper-view').disabled = !paperMesh;
    updateOverlays();
    lastMeshJob = job.id;
    if (first || plateChanged) setView();
    currentMesh.userData.plate = model;
    changed = true;
  }
  if (!revision.current(version)) return;
  if (job.mesh) {
    $('viewport').classList.remove('stale');
    bedGroup.visible = bedVisible && !job.view_only;
    $('bed').disabled = job.view_only;
    $('loading').hidden = true;
    $('dimensions').textContent = `${(job.preview_bounds_mm || job.mesh.extents_mm).map(v => fmt(v)).join(' × ')} mm`;
    const info = job.model_info;
    $('solid-volume').textContent = `Printed solid ${fmt((job.solid_volume_mm3 || job.mesh.volume_mm3) / 1000)} cm³`;
    $('bath-volume').textContent = `Each bath ${fmt(info.bath_ml)} ml · A ${info.recipe_a_ml.join(':')} · B ${info.recipe_b_ml.join(':')}`;
    $('capacity-info').textContent = info.adox_recipe ? `ADOX RA-4 · about ${info.adox_prints_per_fill} prints per fill (whole cut counted)` : 'ADOX capacity estimate applies at 1+4 dilution in both baths';
    $('slit-info').textContent = `Guide ${fmt(info.slit_mm,2)} mm · grip ${fmt(info.grip_mm)} mm`;
    $('indicator-info').textContent = `Empty fill cue ${fmt(info.indicator_depth_mm)} mm · ${fmt(info.indicator_ml,2)} ml`;
    $('paper-info').textContent = `Image ${info.image_mm.map(v=>fmt(v)).join(' × ')} mm · cut ${info.cut_mm.map(v=>fmt(v)).join(' × ')} mm · trim ${fmt(info.trim_mm)} mm`;
    $('agitation-info').textContent = `Agitation ↑ ${fmt(info.agitation_mm[0])} mm / ↔ ±${fmt(info.agitation_mm[1])} mm · immersion reserve ${fmt(info.immersion_mm)} mm`;
    $('plate-note').textContent = ['assembly','exploded'].includes(model) ? 'Complete set, including both covers and four guard tiles. Commercial heaters, metal plates and straps are excluded.' : model.startsWith('inspect_') ? 'Print estimates and project below are for the vessel alone, in its tilted print orientation.' : job.quantity > 1 ? `Print this plate ${job.quantity} times. Estimates below are for one copy.` : 'One copy of this plate. Vessel projects preserve the required tilt and support settings.';
    link('download-stl', job, 'model.stl', !job.view_only);
    link('download-settings', job, 'settings.json', true);
  }
  if (job.stats && job.state === 'ready') {
    $('print-time').textContent = job.stats.total_estimated_time || job.stats.model_printing_time || 'Unavailable';
    $('print-weight').textContent = job.stats.estimated_filament_g == null ? 'Unavailable' : `${fmt(job.stats.estimated_filament_g)} g`;
    $('print-volume').textContent = job.stats.estimated_filament_cm3 == null ? 'Unavailable' : `${fmt(job.stats.estimated_filament_cm3)} cm³`;
    $('download-3mf').textContent = job.bundle ? 'All print files ↓' : 'Bambu project ↗';
    link('download-3mf', job, job.bundle ? 'print-files.zip' : 'plate.3mf', true);
  }
  if (job.error || job.warnings?.length) error(job.error || job.warnings.join('\n'));
  if (job.state === 'superseded') error('Another edit superseded this build. Change a value or reset to rebuild.');
}

async function buildModel(version) {
  if (!revision.current(version)) return;
  const response = await fetch('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Viewer-Token': config.token }, body: JSON.stringify({ model, parameters }) });
  let job = await response.json();
  if (!revision.current(version)) return;
  if (!response.ok) throw new Error(job.error || 'Could not start the build.');
  while (revision.current(version)) {
    await display(job, version);
    if (['ready', 'error', 'preview_only', 'superseded'].includes(job.state)) break;
    await sleep(700);
    if (!revision.current(version)) return;
    const result = await fetch(`/api/jobs/${job.id}`);
    job = await result.json();
    if (!result.ok) throw new Error(job.error || 'The build is no longer available.');
  }
}
function schedule(immediate = false) {
  clearTimeout(timer);
  const version = revision.next();
  clearResults();
  status('Changes pending');
  try { localStorage.setItem(storageKey, JSON.stringify(parameters)); } catch { /* Storage is optional. */ }
  timer = setTimeout(() => buildModel(version).catch(e => { if (revision.current(version)) error(e.message); }), immediate ? 0 : 650);
}

function fixedFields() {
  const fixed = config.models.find(p => p.id === model)?.fixed_parameters || {};
  for (const field of config.fields) {
    const input = $(field.id);
    input.disabled = field.id in fixed;
    input.title = input.disabled ? 'Fixed for this optional guide. Choose Paper guide A or B to adjust it.' : '';
    if (field.type !== 'boolean') input.value = fixed[field.id] ?? parameters[field.id];
  }
}
function form() {
  $('parameters').replaceChildren();
  for (const group of [...new Set(config.fields.map(f=>f.group))]) {
    const details = document.createElement('details');
    details.open = group === 'Paper';
    const summary = document.createElement('summary'); summary.textContent = group;
    details.append(summary);
    for (const field of config.fields.filter(f => f.group === group)) {
      const row = document.createElement('label'); row.className = `field ${field.type === 'boolean' ? 'toggle-field' : ''}`;
      const title = document.createElement('span'); title.textContent = field.label;
      const wrap = document.createElement('span'); wrap.className = 'input-wrap';
      const input = document.createElement('input'); input.id = field.id; input.name = field.id;
      if (field.type === 'boolean') { input.type = 'checkbox'; input.checked = parameters[field.id]; }
      else { input.type = 'number'; input.min = field.min; input.max = field.max; input.step = field.id === 'image_aspect' ? 'any' : field.step; input.value = parameters[field.id]; }
      input.addEventListener('input', () => {
        $('preset').value = 'custom';
        if (!$('parameters').checkValidity() || input.value === '') {
          revision.next(); clearTimeout(timer); clearResults(); error(`Enter a valid ${field.label.toLowerCase()}.`); return;
        }
        for (const f of config.fields) if (!$(f.id).disabled) parameters[f.id] = f.type === 'boolean' ? $(f.id).checked : Number($(f.id).value);
        schedule();
      });
      wrap.append(input);
      if (field.unit) { const unit = document.createElement('small'); unit.textContent = field.unit; wrap.append(unit); }
      row.append(title, wrap); details.append(row);
    }
    $('parameters').append(details);
  }
  fixedFields();
}

async function init() {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error('Could not connect to the local viewer.');
  config = await response.json();
  $('preset').options[0].textContent = '102 mm roll · 16:9 image';
  let saved;
  try { saved = JSON.parse(localStorage.getItem(storageKey)); } catch { /* Start with source defaults. */ }
  parameters = restoreParameters(saved, config);
  if (JSON.stringify(parameters) !== JSON.stringify(config.defaults)) $('preset').value = 'custom';
  form();
  for (const plate of config.models) {
    const option = document.createElement('option'); option.value = plate.id; option.textContent = plate.label;
    $('plates').append(option);
  }
  $('plates').value = model;
  $('plates').onchange = () => {
    model = $('plates').value;
    fixedFields();
    const label = config.models.find(p=>p.id===model).label;
    $('part-caption').textContent = label.toUpperCase();
    $('result-title').textContent = ['assembly','exploded'].includes(model) ? 'Complete set estimates' : `${label} estimates`;
    schedule(true);
  };
  const p = config.profile;
  $('profile').textContent = `${p.filament} · ${p.layer_height || '?'} mm layers · ${p.walls || '?'} walls · ${p.infill || '?'} infill`;
  $('result-title').textContent = 'Complete set estimates';
  $('reset').onclick = () => { parameters = { ...config.defaults }; $('preset').value = 'default'; form(); schedule(true); };
  $('preset').onchange = () => {
    parameters = { ...config.defaults };
    if ($('preset').value === 'wide') parameters.image_aspect = 2;
    form(); schedule(true);
  };
  schedule(true);
}
init().catch(e => error(e.message));
