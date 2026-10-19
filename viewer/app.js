import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { Revision, restoreParameters } from './state.js';

const $ = id => document.getElementById(id);
const revision = new Revision();
const fmt = (v, digits = 1) => Number(v).toLocaleString(undefined, { maximumFractionDigits: digits });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let config, parameters, model = 'tank', timer, currentMesh, liquidMesh, lastMeshJob, changed = true;
let cutaway = false, bedVisible = true, fillVisible = false;
const storageKey = 'processor-parameters-v2'; // Fill calibration changed to the empty tank.

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
controls.maxDistance = 900;
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
  if (currentMesh) currentMesh.material.clippingPlanes = cutaway ? [clip] : [];
  if (liquidMesh) liquidMesh.material.clippingPlanes = cutaway ? [clip] : [];
  changed = true;
};
$('fill-level').onclick = () => {
  fillVisible = !fillVisible;
  $('fill-level').setAttribute('aria-pressed', String(fillVisible));
  if (liquidMesh) liquidMesh.visible = fillVisible;
  changed = true;
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
  for (const id of ['solid-volume', 'bath-volume', 'slit-info', 'indicator-info']) $(id).textContent = '';
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
  if (job.mesh && lastMeshJob !== job.id) {
    const response = await fetch(`/artifacts/${job.id}/model.stl`);
    if (!response.ok) throw new Error('Could not load the model. Update the preview again.');
    const buffer = await response.arrayBuffer();
    if (!revision.current(version)) return;
    const geometry = new STLLoader().parse(buffer);
    geometry.rotateX(-Math.PI / 2);
    geometry.computeBoundingBox();
    const center = geometry.boundingBox.getCenter(new THREE.Vector3());
    const offset = new THREE.Vector3(-center.x, -geometry.boundingBox.min.y, -center.z);
    geometry.translate(offset.x, offset.y, offset.z);
    let liquidGeometry;
    if (job.liquid) {
      const waterResponse = await fetch(`/artifacts/${job.id}/liquid.stl`);
      if (!waterResponse.ok) throw new Error('Could not load the fill-level preview.');
      const waterBuffer = await waterResponse.arrayBuffer();
      if (!revision.current(version)) { geometry.dispose(); return; }
      liquidGeometry = new STLLoader().parse(waterBuffer);
      liquidGeometry.rotateX(-Math.PI / 2);
      liquidGeometry.translate(offset.x, offset.y, offset.z);
    }
    const first = !currentMesh;
    const plateChanged = currentMesh?.userData.plate !== model;
    if (currentMesh) { scene.remove(currentMesh); currentMesh.geometry.dispose(); currentMesh.material.dispose(); }
    if (liquidMesh) { scene.remove(liquidMesh); liquidMesh.geometry.dispose(); liquidMesh.material.dispose(); liquidMesh = null; }
    currentMesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0x367e78, metalness: 0.08, roughness: 0.58, clippingPlanes: cutaway ? [clip] : [], clipShadows: true, side: THREE.DoubleSide }));
    currentMesh.castShadow = true;
    currentMesh.receiveShadow = true;
    scene.add(currentMesh);
    if (liquidGeometry) {
      liquidMesh = new THREE.Mesh(liquidGeometry, new THREE.MeshStandardMaterial({ color: 0x5aaee0, roughness: 0.2, transparent: true, opacity: 0.8, depthWrite: false, clippingPlanes: cutaway ? [clip] : [], side: THREE.DoubleSide }));
      liquidMesh.visible = fillVisible;
      scene.add(liquidMesh);
    }
    $('fill-level').disabled = !liquidGeometry;
    lastMeshJob = job.id;
    if (first || plateChanged) setView();
    currentMesh.userData.plate = model;
    changed = true;
  }
  if (!revision.current(version)) return;
  if (job.mesh) {
    $('viewport').classList.remove('stale');
    $('loading').hidden = true;
    $('dimensions').textContent = `${job.mesh.extents_mm.map(v => fmt(v)).join(' × ')} mm`;
    $('solid-volume').textContent = `Solid model ${fmt(job.mesh.volume_mm3 / 1000)} cm³`;
    $('bath-volume').textContent = `Working bath ${fmt(job.model_info.bath_ml)} ml · ${fmt(job.model_info.mix_first_ml)}:${fmt(job.model_info.mix_second_ml)}`;
    $('slit-info').textContent = `Slit ${fmt(job.model_info.slit_mm, 2)} mm · dry border ${fmt(job.model_info.dry_border_mm)} mm`;
    $('indicator-info').textContent = job.parameters.inlets_enabled ? `Fill cue ${fmt(job.model_info.indicator_depth_mm)} mm · ${fmt(job.model_info.indicator_ml, 2)} ml visible` : '';
    link('download-stl', job, 'model.stl', true);
    link('download-settings', job, 'settings.json', true);
  }
  if (job.stats && job.state === 'ready') {
    $('print-time').textContent = job.stats.total_estimated_time || job.stats.model_printing_time || 'Unavailable';
    $('print-weight').textContent = job.stats.estimated_filament_g == null ? 'Unavailable' : `${fmt(job.stats.estimated_filament_g)} g`;
    $('print-volume').textContent = job.stats.estimated_filament_cm3 == null ? 'Unavailable' : `${fmt(job.stats.estimated_filament_cm3)} cm³`;
    link('download-3mf', job, 'plate.3mf', true);
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

function form() {
  $('parameters').replaceChildren();
  for (const group of ['Paper', 'Tank', 'Advanced']) {
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
      else { input.type = 'number'; input.min = field.min; input.max = field.max; input.step = field.step; input.value = parameters[field.id]; }
      input.addEventListener('input', () => {
        $('preset').value = 'custom';
        if (!$('parameters').checkValidity() || input.value === '') {
          revision.next(); clearTimeout(timer); clearResults(); error(`Enter a valid ${field.label.toLowerCase()}.`); return;
        }
        for (const f of config.fields) parameters[f.id] = f.type === 'boolean' ? $(f.id).checked : Number($(f.id).value);
        schedule();
      });
      wrap.append(input);
      if (field.unit) { const unit = document.createElement('small'); unit.textContent = field.unit; wrap.append(unit); }
      row.append(title, wrap); details.append(row);
    }
    $('parameters').append(details);
  }
}

async function init() {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error('Could not connect to the local viewer.');
  config = await response.json();
  $('preset').options[0].textContent = `${fmt(config.defaults.paper_width)} × ${fmt(config.defaults.paper_height)} mm`;
  let saved;
  try { saved = JSON.parse(localStorage.getItem(storageKey)); } catch { /* Start with source defaults. */ }
  parameters = restoreParameters(saved, config);
  if (JSON.stringify(parameters) !== JSON.stringify(config.defaults)) $('preset').value = 'custom';
  form();
  for (const plate of config.models) {
    const button = document.createElement('button');
    button.textContent = plate.label; button.setAttribute('role', 'tab'); button.setAttribute('aria-selected', String(plate.id === model));
    button.onclick = () => {
      model = plate.id;
      for (const node of $('plates').children) node.setAttribute('aria-selected', String(node === button));
      $('part-caption').textContent = plate.label.toUpperCase();
      $('result-title').textContent = `${plate.label} estimates`;
      schedule(true);
    };
    $('plates').append(button);
  }
  const p = config.profile;
  $('profile').textContent = `${p.filament} · ${p.layer_height || '?'} mm layers · ${p.walls || '?'} walls · ${p.infill || '?'} infill`;
  $('result-title').textContent = 'Tank estimates';
  $('reset').onclick = () => { parameters = { ...config.defaults }; $('preset').value = 'default'; form(); schedule(true); };
  $('preset').onchange = () => {
    parameters = { ...config.defaults };
    if ($('preset').value === 'square') parameters.paper_width = parameters.paper_height = Math.floor(Math.min(config.limits.max_width_mm, config.limits.max_height_mm) * 10) / 10;
    if ($('preset').value === 'rectangle') { parameters.paper_width = config.limits.max_width_mm; parameters.paper_height = config.limits.max_height_mm; }
    form(); schedule(true);
  };
  schedule(true);
}
init().catch(e => error(e.message));
