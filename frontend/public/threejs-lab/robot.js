import * as THREE from './vendor/three.module.js';

// The gallery and homepage reuse the same procedural robot in a lightweight, non-interactive preview.
const miniMode = document.documentElement.dataset.variant === 'mini';
const container = document.getElementById('scene');
const errorEl = document.getElementById('sceneError');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: miniMode ? 'low-power' : 'high-performance' });
} catch (error) {
  errorEl.style.display = 'grid';
  if (miniMode) window.parent.postMessage({type: 'mini-scene-error'}, window.location.origin);
  throw error;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, miniMode ? 1.2 : 1.8));
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.22;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
const target = new THREE.Vector3(0, 0.24, 0);
let azimuth = miniMode ? 0.17 : 0.38, elevation = 0.13, distance = miniMode ? 6.7 : 8.3;
function updateCamera() {
  camera.position.set(
    target.x + distance * Math.sin(azimuth) * Math.cos(elevation),
    target.y + distance * Math.sin(elevation),
    target.z + distance * Math.cos(azimuth) * Math.cos(elevation)
  );
  camera.lookAt(target);
}
updateCamera();

scene.add(new THREE.HemisphereLight(0xcde6ff, 0x17233d, 3.1));
const keyLight = new THREE.PointLight(0x7ae5ff, 95, 18);
keyLight.position.set(3.8, 4.3, 5.5);
scene.add(keyLight);
const rimLight = new THREE.PointLight(0x8390ff, 80, 18);
rimLight.position.set(-3.8, 2.1, -3.6);
scene.add(rimLight);
const frontLight = new THREE.PointLight(0xffffff, 23, 12);
frontLight.position.set(-2, 0.4, 5);
scene.add(frontLight);

const palette = {
  cyan: { accent: 0x72eeff, secondary: 0x7594ff, light: 0x78dfff, glow: '#72eeff' },
  purple: { accent: 0xe1abff, secondary: 0xee85ca, light: 0xb99aff, glow: '#d49cff' },
  gold: { accent: 0xffd58c, secondary: 0xff986f, light: 0xffcb7b, glow: '#ffd58c' }
};
let theme = 'cyan';
let mode = 'idle';
let speed = 1;
let paused = false;
let particleVisible = true;
let elapsed = 0;
let blinkRemaining = 0;
let nextBlink = 2.6;
let pulse = 0;
let pointerX = 0;
let pointerY = 0;

const shellMat = new THREE.MeshPhysicalMaterial({
  color: 0xdce9f7, metalness: 0.18, roughness: 0.3,
  clearcoat: 0.95, clearcoatRoughness: 0.2
});
const softWhiteMat = new THREE.MeshStandardMaterial({ color: 0xf1f7ff, metalness: 0.12, roughness: 0.32 });
const graphiteMat = new THREE.MeshStandardMaterial({ color: 0x243750, metalness: 0.67, roughness: 0.31 });
const visorMat = new THREE.MeshPhysicalMaterial({
  color: 0x061b32, metalness: 0.39, roughness: 0.16,
  clearcoat: 1, clearcoatRoughness: 0.08
});
const darkJointMat = new THREE.MeshStandardMaterial({ color: 0x647991, metalness: 0.58, roughness: 0.35 });
const accentMat = new THREE.MeshBasicMaterial({ color: palette.cyan.accent, toneMapped: false });
const accentSoftMat = new THREE.MeshStandardMaterial({
  color: 0x58cde8, emissive: 0x27a4cd, emissiveIntensity: 0.8,
  metalness: 0.4, roughness: 0.26
});
const secondaryMat = new THREE.MeshBasicMaterial({ color: palette.cyan.secondary, toneMapped: false });

function roundedBox(width, height, depth, radius, material) {
  const r = Math.min(radius, width / 2 - 0.01, height / 2 - 0.01);
  const x = -width / 2, y = -height / 2;
  const s = new THREE.Shape();
  s.moveTo(x + r, y);
  s.lineTo(x + width - r, y);
  s.quadraticCurveTo(x + width, y, x + width, y + r);
  s.lineTo(x + width, y + height - r);
  s.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  s.lineTo(x + r, y + height);
  s.quadraticCurveTo(x, y + height, x, y + height - r);
  s.lineTo(x, y + r);
  s.quadraticCurveTo(x, y, x + r, y);
  const bevel = Math.min(0.075, depth * 0.13, r * 0.42);
  const geometry = new THREE.ExtrudeGeometry(s, {
    depth: depth - bevel * 2, bevelEnabled: true,
    bevelThickness: bevel, bevelSize: bevel,
    bevelSegments: 3, curveSegments: 9, steps: 1
  });
  geometry.center();
  return new THREE.Mesh(geometry, material);
}
function sphere(radius, material, widthSegments = 24, heightSegments = 16) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius, widthSegments, heightSegments), material);
}
function cylinder(r1, r2, height, material) {
  return new THREE.Mesh(new THREE.CylinderGeometry(r1, r2, height, 24), material);
}

const robot = new THREE.Group();
scene.add(robot);

// Body and chest: all assembled from primitive geometries.
const torso = roundedBox(1.36, 1.16, 0.88, 0.29, shellMat);
torso.position.y = -0.39;
robot.add(torso);
const chestInset = roundedBox(0.79, 0.56, 0.07, 0.18, graphiteMat);
chestInset.position.set(0, -0.37, 0.48);
robot.add(chestInset);
const chestDisc = new THREE.Mesh(new THREE.CircleGeometry(0.17, 48), accentSoftMat);
chestDisc.position.set(0, -0.36, 0.535);
robot.add(chestDisc);
const chestRing = new THREE.Mesh(new THREE.TorusGeometry(0.255, 0.022, 10, 70), accentMat);
chestRing.position.set(0, -0.36, 0.545);
robot.add(chestRing);
const chestDot = sphere(0.047, softWhiteMat);
chestDot.position.set(0, -0.36, 0.567);
robot.add(chestDot);

const neck = cylinder(0.23, 0.26, 0.46, darkJointMat);
neck.position.set(0, 0.36, 0);
robot.add(neck);
const neckCollar = cylinder(0.32, 0.31, 0.12, accentSoftMat);
neckCollar.position.set(0, 0.22, 0);
robot.add(neckCollar);

// Head pivots independently from the body and tracks pointer position.
const headPivot = new THREE.Group();
headPivot.position.set(0, 0.69, 0);
robot.add(headPivot);
const head = roundedBox(2.12, 1.47, 0.97, 0.36, softWhiteMat);
head.position.set(0, 0.56, 0);
headPivot.add(head);
const sideBand = roundedBox(2.20, 1.17, 0.7, 0.37, shellMat);
sideBand.position.set(0, 0.56, -0.10);
headPivot.add(sideBand);
// The screen is placed on top of the frame, with bright expressive eyes.
const face = roundedBox(1.79, 0.98, 0.13, 0.28, visorMat);
face.position.set(0, 0.57, 0.55);
headPivot.add(face);
const eyes = [];
for (const x of [-0.46, 0.46]) {
  const glow = sphere(0.235, accentMat);
  glow.scale.set(0.96, 1.05, 0.37);
  glow.position.set(x, 0.66, 0.66);
  headPivot.add(glow);
  eyes.push(glow);
  const highlight = sphere(0.047, softWhiteMat, 12, 10);
  highlight.position.set(x - 0.075, 0.76, 0.744);
  headPivot.add(highlight);
}
const smileCurve = new THREE.CatmullRomCurve3([
  new THREE.Vector3(-0.23, 0.29, 0.647),
  new THREE.Vector3(0, 0.235, 0.667),
  new THREE.Vector3(0.23, 0.29, 0.647)
]);
const smile = new THREE.Mesh(new THREE.TubeGeometry(smileCurve, 24, 0.021, 8, false), accentMat);
headPivot.add(smile);
const thoughtMouth = new THREE.Mesh(new THREE.TorusGeometry(0.074, 0.018, 8, 30), accentMat);
thoughtMouth.position.set(0, 0.27, 0.67);
thoughtMouth.visible = false;
headPivot.add(thoughtMouth);
const cheeks = [];
for (const x of [-0.75, 0.75]) {
  const cheek = sphere(0.055, secondaryMat, 12, 8);
  cheek.scale.z = 0.3;
  cheek.position.set(x, 0.29, 0.63);
  headPivot.add(cheek);
  cheeks.push(cheek);
}

// Side speakers and antenna.
for (const side of [-1, 1]) {
  const ear = cylinder(0.24, 0.24, 0.16, graphiteMat);
  ear.rotation.z = Math.PI / 2;
  ear.position.set(side * 1.105, 0.57, 0);
  headPivot.add(ear);
  const earLight = cylinder(0.14, 0.14, 0.018, accentSoftMat);
  earLight.rotation.z = Math.PI / 2;
  earLight.position.set(side * 1.205, 0.57, 0);
  headPivot.add(earLight);
}
const antenna = cylinder(0.055, 0.07, 0.37, darkJointMat);
antenna.position.set(0, 1.50, 0);
headPivot.add(antenna);
const antennaOrb = sphere(0.14, accentMat);
antennaOrb.position.set(0, 1.75, 0);
headPivot.add(antennaOrb);

// Two simple articulated arms: their parent groups are the shoulder joints.
function makeArm(side) {
  const pivot = new THREE.Group();
  pivot.position.set(side * 0.84, -0.05, 0);
  robot.add(pivot);
  const shoulder = sphere(0.245, graphiteMat);
  pivot.add(shoulder);
  const upper = roundedBox(0.37, 0.67, 0.39, 0.15, shellMat);
  upper.position.y = -0.4;
  pivot.add(upper);
  const elbow = sphere(0.18, darkJointMat);
  elbow.position.y = -0.76;
  pivot.add(elbow);
  const cuff = roundedBox(0.31, 0.12, 0.33, 0.06, accentSoftMat);
  cuff.position.y = -0.92;
  pivot.add(cuff);
  const hand = sphere(0.205, softWhiteMat);
  hand.position.y = -1.10;
  hand.scale.set(1.1, 1.05, 0.9);
  pivot.add(hand);
  return pivot;
}
const leftArm = makeArm(-1);
const rightArm = makeArm(1);

// Short legs and oversized rounded feet make the silhouette recognizable.
for (const side of [-1, 1]) {
  const leg = cylinder(0.17, 0.19, 0.46, graphiteMat);
  leg.position.set(side * 0.38, -1.1, 0);
  robot.add(leg);
  const boot = roundedBox(0.5, 0.24, 0.7, 0.115, shellMat);
  boot.position.set(side * 0.38, -1.46, 0.15);
  robot.add(boot);
  const bootTip = roundedBox(0.32, 0.052, 0.05, 0.02, accentSoftMat);
  bootTip.position.set(side * 0.38, -1.48, 0.53);
  robot.add(bootTip);
}

// Thinking indicator: three luminous bubbles above one side of the head.
const thoughtDots = [];
for (let i = 0; i < 3; i++) {
  const dot = sphere(0.045 + i * 0.027, accentMat, 16, 12);
  dot.position.set(1.19 + i * 0.2, 1.12 + i * 0.25, 0.18);
  dot.visible = false;
  headPivot.add(dot);
  thoughtDots.push(dot);
}

// A holographic landing ring under the floating robot.
const haloGroup = new THREE.Group();
haloGroup.position.y = -1.91;
scene.add(haloGroup);
const haloMaterials = [];
for (const [radius, tube, opacity] of [[1.18, 0.018, 0.7], [1.58, 0.012, 0.35], [1.88, 0.007, 0.16]]) {
  const material = new THREE.MeshBasicMaterial({color: palette.cyan.accent, transparent: true, opacity, depthWrite: false});
  const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, tube, 8, 120), material);
  ring.rotation.x = Math.PI / 2;
  haloGroup.add(ring);
  haloMaterials.push(material);
}
const groundDiscMaterial = new THREE.MeshBasicMaterial({color: 0x4ccaff, transparent: true, opacity: 0.035, side: THREE.DoubleSide, depthWrite: false});
const groundDisc = new THREE.Mesh(new THREE.CircleGeometry(1.86, 80), groundDiscMaterial);
groundDisc.rotation.x = -Math.PI / 2;
groundDisc.position.y = -0.012;
haloGroup.add(groundDisc);

// The faint bloom is itself generated at runtime from a tiny canvas texture.
const glowCanvas = document.createElement('canvas');
glowCanvas.width = glowCanvas.height = 128;
const gc = glowCanvas.getContext('2d');
const gradient = gc.createRadialGradient(64, 64, 4, 64, 64, 64);
gradient.addColorStop(0, 'rgba(109,220,255,.43)');
gradient.addColorStop(0.36, 'rgba(83,161,255,.14)');
gradient.addColorStop(1, 'rgba(57,116,230,0)');
gc.fillStyle = gradient;
gc.fillRect(0, 0, 128, 128);
const auraMaterial = new THREE.SpriteMaterial({map: new THREE.CanvasTexture(glowCanvas), transparent: true, depthWrite: false, opacity: 0.65});
const aura = new THREE.Sprite(auraMaterial);
aura.position.set(0, 0.2, -1.35);
aura.scale.set(7.5, 7.5, 1);
scene.add(aura);

const pseudoRandom = n => {
  const value = Math.sin(n * 127.1 + 78.233) * 43758.5453;
  return value - Math.floor(value);
};
const particleCount = miniMode ? 120 : 450;
const positions = new Float32Array(particleCount * 3);
for (let i = 0; i < particleCount; i++) {
  const a = pseudoRandom(i + 1) * Math.PI * 2;
  const r = 2.8 + pseudoRandom(i + 130) * 1.9;
  positions[i * 3] = Math.cos(a) * r;
  positions[i * 3 + 1] = (pseudoRandom(i + 390) - 0.5) * 4.4;
  positions[i * 3 + 2] = Math.sin(a) * r;
}
const particleGeometry = new THREE.BufferGeometry();
particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
const particleMaterial = new THREE.PointsMaterial({
  color: palette.cyan.accent, size: 0.027, transparent: true,
  opacity: 0.58, blending: THREE.AdditiveBlending,
  depthWrite: false, sizeAttenuation: true
});
const particles = new THREE.Points(particleGeometry, particleMaterial);
scene.add(particles);

const starCount = miniMode ? 60 : 180;
const starPositions = new Float32Array(starCount * 3);
for (let i = 0; i < starCount; i++) {
  starPositions[i * 3] = (pseudoRandom(i + 300) - 0.5) * 35;
  starPositions[i * 3 + 1] = (pseudoRandom(i + 700) - 0.5) * 22;
  starPositions[i * 3 + 2] = (pseudoRandom(i + 1100) - 0.5) * 20 - 5;
}
const starsGeometry = new THREE.BufferGeometry();
starsGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
scene.add(new THREE.Points(starsGeometry, new THREE.PointsMaterial({color: 0x7a9dcc, size: 0.023, transparent: true, opacity: 0.4, depthWrite: false})));

function setTheme(name) {
  theme = name;
  const p = palette[name];
  accentMat.color.setHex(p.accent);
  accentSoftMat.color.setHex(p.accent);
  accentSoftMat.emissive.setHex(p.accent);
  secondaryMat.color.setHex(p.secondary);
  keyLight.color.setHex(p.light);
  rimLight.color.setHex(p.secondary);
  particleMaterial.color.setHex(p.accent);
  groundDiscMaterial.color.setHex(p.accent);
  haloMaterials.forEach(m => m.color.setHex(p.accent));
  document.documentElement.style.setProperty('--accent', p.glow);
}

const codeExamples = {
  geometry: `// 头、身体、手臂都由代码构建\nconst head = roundedBox(2.1, 1.5, 1);\nconst eyes = new THREE.Mesh(\n  new THREE.SphereGeometry(.23),\n  glowMaterial\n);\nrobot.add(head, eyes);`,
  material: `// 陶瓷外壳 + 发光眼睛\nconst shell = new THREE.\n  MeshPhysicalMaterial({\n    color: 0xdce9f7, clearcoat: .95\n  });\nconst eyes = new THREE.\n  MeshBasicMaterial({ color: 0x72eeff });`,
  animate: `// 动画无需现成模型骨骼\nrobot.position.y =\n  Math.sin(time * 1.4) * .08;\nhead.rotation.y = pointerX * .15;\nrightArm.rotation.z = 2.3;\nrenderer.render(scene, camera);`,
  interact: `// 点击机器人，切换挥手状态\nraycaster.setFromCamera(\n  pointer, camera\n);\nif (raycaster.intersectObjects(\n  robot.children, true\n).length) setMode('wave');`
};
let activeTab = 'geometry';
function updateCode() {
  document.getElementById('codeSample').textContent = codeExamples[activeTab];
}
if (!miniMode) updateCode();

function setMode(next) {
  mode = next;
  document.querySelectorAll('[data-mode]').forEach(btn => {
    const isActive = btn.dataset.mode === next;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-pressed', String(isActive));
  });
  thoughtDots.forEach(dot => dot.visible = next === 'thinking');
  thoughtMouth.visible = next === 'thinking';
  smile.visible = next !== 'thinking';
  blinkRemaining = 0.17;
}
if (!miniMode) {
document.getElementById('shapeGrid').addEventListener('click', event => {
  const btn = event.target.closest('[data-mode]');
  if (!btn) return;
  setMode(btn.dataset.mode);
});
document.getElementById('speed').addEventListener('input', event => {
  speed = Number(event.target.value);
  document.getElementById('speedValue').textContent = speed.toFixed(1) + '×';
});
document.getElementById('particlesToggle').addEventListener('click', event => {
  particleVisible = !particleVisible;
  particles.visible = particleVisible;
  event.currentTarget.classList.toggle('off', !particleVisible);
  event.currentTarget.setAttribute('aria-pressed', String(particleVisible));
});
document.getElementById('swatches').addEventListener('click', event => {
  const btn = event.target.closest('[data-color]');
  if (!btn) return;
  setTheme(btn.dataset.color);
  document.querySelectorAll('.swatch').forEach(b => {
    const active = b === btn;
    b.classList.toggle('active', active);
    b.setAttribute('aria-pressed', String(active));
  });
});
document.querySelector('.code-tabs').addEventListener('click', event => {
  const btn = event.target.closest('[data-tab]');
  if (!btn) return;
  activeTab = btn.dataset.tab;
  document.querySelectorAll('.code-tabs button').forEach(b => b.classList.toggle('active', b === btn));
  updateCode();
});
document.getElementById('pause').addEventListener('click', event => {
  paused = !paused;
  event.currentTarget.textContent = paused ? '▶ 继续动画' : 'Ⅱ 暂停动画';
  event.currentTarget.classList.toggle('primary', !paused);
});
document.getElementById('reset').addEventListener('click', () => {
  azimuth = 0.38;
  elevation = 0.13;
  distance = 8.3;
  updateCamera();
});
let toastTimeout;
function greet() {
  setMode('wave');
  pulse = 1.1;
  const toast = document.getElementById('toast');
  toast.classList.add('visible');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('visible'), 1400);
}
document.getElementById('pulse').addEventListener('click', greet);

let dragging = false, moved = false, lastX = 0, lastY = 0;
renderer.domElement.addEventListener('pointerdown', event => {
  dragging = true;
  moved = false;
  lastX = event.clientX;
  lastY = event.clientY;
  renderer.domElement.setPointerCapture(event.pointerId);
});
renderer.domElement.addEventListener('pointermove', event => {
  const bounds = renderer.domElement.getBoundingClientRect();
  pointerX = ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;
  pointerY = ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;
  if (!dragging) return;
  const dx = event.clientX - lastX;
  const dy = event.clientY - lastY;
  if (Math.abs(dx) + Math.abs(dy) > 1) moved = true;
  azimuth -= dx * 0.006;
  elevation = Math.max(-1.1, Math.min(1.1, elevation + dy * 0.005));
  lastX = event.clientX;
  lastY = event.clientY;
  updateCamera();
});
renderer.domElement.addEventListener('pointerup', event => {
  dragging = false;
  if (moved) return;
  const rect = renderer.domElement.getBoundingClientRect();
  const pointer = new THREE.Vector2(
    (event.clientX - rect.left) / rect.width * 2 - 1,
    -(event.clientY - rect.top) / rect.height * 2 + 1
  );
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(pointer, camera);
  if (raycaster.intersectObjects(robot.children, true).length) greet();
});
renderer.domElement.addEventListener('pointercancel', () => { dragging = false; });
renderer.domElement.addEventListener('pointerleave', () => { if (!dragging) { pointerX = 0; pointerY = 0; } });
renderer.domElement.addEventListener('wheel', event => {
  event.preventDefault();
  distance = Math.max(5.5, Math.min(14, distance + event.deltaY * 0.006));
  updateCamera();
}, { passive: false });
}

function resize() {
  const width = container.clientWidth, height = container.clientHeight;
  if (!width || !height) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(container);
resize();
setMode('idle');
setTheme('cyan');

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (reducedMotion) {
  paused = true;
  if (!miniMode) {
    document.getElementById('pause').textContent = '▶ 继续动画';
    document.getElementById('pause').classList.remove('primary');
  }
}

let previous = performance.now(), sampleTime = performance.now(), frames = 0;
let lastMiniFrame = 0;
let firstMiniRender = true;
if (miniMode) window.addEventListener('message', event => {
  if (event.origin === window.location.origin && event.data?.type === 'mini-scene-status-request' && !firstMiniRender) {
    window.parent.postMessage({type: 'mini-scene-ready'}, window.location.origin);
  }
});
const objectCount = (() => { let count = 0; scene.traverse(obj => { if (obj.isMesh || obj.isPoints || obj.isSprite || obj.isLine) count++; }); return count; })();
function animate(now) {
  requestAnimationFrame(animate);
  if (miniMode) {
    if (document.hidden || (reducedMotion && !firstMiniRender)) return;
    if (now - lastMiniFrame < 1000 / 24) return;
    lastMiniFrame = now;
  }
  const dt = Math.min(0.05, (now - previous) / 1000);
  previous = now;
  if (!paused) {
    elapsed += dt * speed;
    const t = elapsed;
    robot.position.y = Math.sin(t * 1.45) * 0.09;
    robot.rotation.z = Math.sin(t * 0.7) * 0.018;
    const desiredHeadY = pointerX * 0.13 + Math.sin(t * 0.45) * 0.035;
    const desiredHeadX = -pointerY * 0.055 + (mode === 'thinking' ? -0.08 : 0);
    headPivot.rotation.y = THREE.MathUtils.lerp(headPivot.rotation.y, desiredHeadY, Math.min(1, dt * 4));
    headPivot.rotation.x = THREE.MathUtils.lerp(headPivot.rotation.x, desiredHeadX, Math.min(1, dt * 4));
    headPivot.rotation.z = THREE.MathUtils.lerp(headPivot.rotation.z, mode === 'thinking' ? -0.1 : mode === 'wave' ? 0.08 : 0, Math.min(1, dt * 4));
    const desiredLeft = mode === 'thinking' ? 2.25 : -0.12 + Math.sin(t * 1.6) * 0.045;
    const desiredRight = mode === 'wave' ? 2.23 + Math.sin(t * 8) * 0.16 : 0.12 + Math.sin(t * 1.8) * 0.045;
    leftArm.rotation.z = THREE.MathUtils.lerp(leftArm.rotation.z, desiredLeft, Math.min(1, dt * 5));
    rightArm.rotation.z = THREE.MathUtils.lerp(rightArm.rotation.z, desiredRight, Math.min(1, dt * 6));
    if (t >= nextBlink) {
      blinkRemaining = 0.18;
      nextBlink = t + 3.6 + pseudoRandom(Math.floor(t * 10)) * 1.7;
    }
    blinkRemaining = Math.max(0, blinkRemaining - dt * Math.max(0.4, speed));
    const blink = blinkRemaining > 0 ? Math.sin(Math.PI * blinkRemaining / 0.18) : 0;
    const eyeHeight = (mode === 'thinking' ? 0.72 : 1.05) * (1 - 0.92 * blink);
    eyes.forEach(eye => { eye.scale.y = Math.max(0.05, eyeHeight); });
    haloGroup.rotation.y = t * 0.19;
    particles.rotation.y = t * 0.021;
    thoughtDots.forEach((dot, i) => { dot.position.y = 1.12 + i * 0.25 + Math.sin(t * 2 + i) * 0.06; });
  }
  pulse = Math.max(0, pulse - dt * 1.4);
  chestDisc.scale.setScalar(1 + Math.sin(elapsed * 5) * 0.09 + pulse * 0.45);
  antennaOrb.scale.setScalar(1 + Math.sin(elapsed * 2.5) * 0.1 + pulse * 0.35);
  keyLight.intensity = 95 + pulse * 45;
  renderer.render(scene, camera);
  if (miniMode) {
    if (firstMiniRender) {
      firstMiniRender = false;
      window.parent.postMessage({type: 'mini-scene-ready'}, window.location.origin);
    }
    return;
  }
  frames++;
  if (now - sampleTime >= 1000) {
    document.getElementById('fps').textContent = Math.round(frames * 1000 / (now - sampleTime));
    document.getElementById('objects').textContent = objectCount;
    document.getElementById('triangles').textContent = renderer.info.render.triangles.toLocaleString('en-US');
    frames = 0;
    sampleTime = now;
  }
}
requestAnimationFrame(animate);
