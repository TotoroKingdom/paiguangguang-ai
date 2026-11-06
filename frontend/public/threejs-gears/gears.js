import * as THREE from '../threejs-lab/vendor/three.module.js';

const miniMode = document.documentElement.dataset.variant === 'mini';
const mount = document.getElementById('viewport');
const fallback = document.getElementById('fallback');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:miniMode?'low-power':'high-performance'});
} catch (error) {
  fallback.style.display = 'grid';
  if(miniMode)window.parent.postMessage({type:'mini-scene-error'},window.location.origin);
  throw error;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, miniMode?1.2:1.8));
renderer.setClearColor(0x000000,0);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.45;
mount.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42,1,0.1,100);
const target = new THREE.Vector3(0,0,0);
let azimuth = 0.2, elevation = 0.12, distance = 9.9;
const isNarrow = () => window.innerWidth < 680;
function resetCamera() {
  azimuth = 0.2;
  elevation = 0.12;
  distance = miniMode ? 10.3 : isNarrow() ? 12.7 : 9.9;
  updateCamera();
}
function updateCamera() {
  camera.position.set(
    target.x + distance*Math.sin(azimuth)*Math.cos(elevation),
    target.y + distance*Math.sin(elevation),
    target.z + distance*Math.cos(azimuth)*Math.cos(elevation)
  );
  camera.lookAt(target);
}
resetCamera();

scene.add(new THREE.HemisphereLight(0xc6d6e5,0x222029,2.9));
const warmKey = new THREE.PointLight(0xffd3a0,140,24);
warmKey.position.set(-4,5,5);
scene.add(warmKey);
const coolRim = new THREE.PointLight(0x78b9ff,125,22);
coolRim.position.set(4,-2,-1);
scene.add(coolRim);
const frontFill = new THREE.PointLight(0xffffff,55,18);
frontFill.position.set(2,0,7);
scene.add(frontFill);

const backdrop = new THREE.GridHelper(16,32,0x476077,0x304258);
backdrop.rotation.x = Math.PI/2;
backdrop.position.z = -1.36;
backdrop.material.transparent = true;
backdrop.material.opacity = 0.16;
scene.add(backdrop);
const frameRing = new THREE.Mesh(
  new THREE.TorusGeometry(3.75,0.008,8,144),
  new THREE.MeshBasicMaterial({color:0x708c9e,transparent:true,opacity:0.14,depthWrite:false})
);
frameRing.position.z = -1.28;
scene.add(frameRing);

const starCount = miniMode?75:260;
const stars = new Float32Array(starCount*3);
function seeded(i) { const n=Math.sin(i*127.1+78.233)*43758.5453; return n-Math.floor(n); }
for(let i=0;i<starCount;i++) {
  stars[i*3] = (seeded(i+3)-.5)*24;
  stars[i*3+1] = (seeded(i+150)-.5)*16;
  stars[i*3+2] = -2.4+(seeded(i+570)-.5)*3;
}
const starGeo = new THREE.BufferGeometry();
starGeo.setAttribute('position',new THREE.BufferAttribute(stars,3));
scene.add(new THREE.Points(starGeo,new THREE.PointsMaterial({color:0x97b0c7,size:0.019,transparent:true,opacity:0.36,depthWrite:false})));

const assembly = new THREE.Group();
assembly.rotation.x = -0.14;
assembly.rotation.y = -0.12;
scene.add(assembly);
const gearbox = new THREE.Group();
assembly.add(gearbox);

const MODULE = 0.145;
const THICKNESS = 0.34;
let teethA = 14, teethB = 24;
let speedRPM = 60, direction = 1, angle = 0;
let isRunning = true, wireframe = false, showContact = true;
let driver = null, follower = null, contactGlow = null, contactHalo = null;
let meshMaterials = [];

// A flat tooth outline is extruded into a fully 3D gear, with holes cut into it.
// It uses a stylized trapezoidal tooth profile, not a precision involute profile.
function makeGearShape(count) {
  const pitch = MODULE*count/2;
  const root = pitch-MODULE*1.12;
  const tip = pitch+MODULE*0.9;
  const step = 2*Math.PI/count;
  const shape = new THREE.Shape();
  const profile = [[0,root],[0.12,root],[0.28,tip],[0.72,tip],[0.88,root]];
  let first = true;
  for(let tooth=0;tooth<count;tooth++) {
    for(const [fraction,radius] of profile) {
      const a = (tooth+fraction)*step;
      const x = Math.cos(a)*radius, y = Math.sin(a)*radius;
      if(first) {shape.moveTo(x,y);first=false;}
      else shape.lineTo(x,y);
    }
  }
  shape.closePath();

  const shaft = new THREE.Path();
  shaft.absarc(0,0,0.205,0,Math.PI*2,true);
  shape.holes.push(shaft);

  const spokes = count < 16 ? 5 : 6;
  const innerR = Math.max(0.36,pitch*0.33);
  const outerR = root*0.79;
  if(outerR>innerR+0.1) {
    for(let n=0;n<spokes;n++) {
      const center = n*2*Math.PI/spokes + 0.16;
      const half = Math.PI/spokes*0.36;
      const hole = new THREE.Path();
      for(let j=0;j<=7;j++) {
        const a = center+half-(j/7)*2*half;
        const x = Math.cos(a)*outerR,y = Math.sin(a)*outerR;
        if(j===0)hole.moveTo(x,y);else hole.lineTo(x,y);
      }
      for(let j=0;j<=7;j++) {
        const a = center-half+(j/7)*2*half;
        hole.lineTo(Math.cos(a)*innerR,Math.sin(a)*innerR);
      }
      hole.closePath();
      shape.holes.push(hole);
    }
  }
  return {shape,pitch,root,tip};
}

function ring(radius,tube,material,z=0) {
  const mesh = new THREE.Mesh(new THREE.TorusGeometry(radius,tube,10,90),material);
  mesh.position.z = z;
  return mesh;
}
function cylinderZ(radius,height,material) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,height,40),material);
  m.rotation.x = Math.PI/2;
  return m;
}

function makeGear(count,primary) {
  const {shape,pitch,root,tip} = makeGearShape(count);
  const frontMat = new THREE.MeshPhysicalMaterial({
    color:primary?0xdab37b:0xadc2d2,
    metalness:0.66,roughness:0.27,clearcoat:0.63,clearcoatRoughness:0.18,
    wireframe
  });
  const sideMat = new THREE.MeshStandardMaterial({
    color:primary?0x916642:0x526c80,
    metalness:0.68,roughness:0.31,wireframe
  });
  meshMaterials.push(frontMat,sideMat);

  const geometry = new THREE.ExtrudeGeometry(shape,{
    depth:THICKNESS-0.08,bevelEnabled:true,bevelThickness:0.04,
    bevelSize:0.027,bevelSegments:3,curveSegments:9,steps:1,
    material:0,extrudeMaterial:1
  });
  geometry.translate(0,0,-(THICKNESS-0.08)/2);
  const group = new THREE.Group();
  group.add(new THREE.Mesh(geometry,[frontMat,sideMat]));

  const darkMetal = new THREE.MeshStandardMaterial({color:primary?0x493c32:0x253b50,metalness:0.57,roughness:0.36});
  const brightMetal = new THREE.MeshStandardMaterial({color:primary?0xffdfa7:0xd9efff,metalness:0.55,roughness:0.25});
  const hubMetal = new THREE.MeshStandardMaterial({color:primary?0xb38959:0x7697ad,metalness:0.74,roughness:0.26});
  const boltMat = new THREE.MeshStandardMaterial({color:0xe6eaf1,metalness:0.72,roughness:0.23});
  const mats = [darkMetal,brightMetal,hubMetal,boltMat];

  const hubBase = cylinderZ(0.38,0.09,hubMetal);
  hubBase.position.z = THICKNESS/2+0.055;
  group.add(hubBase);
  const hubInner = cylinderZ(0.265,0.11,darkMetal);
  hubInner.position.z = THICKNESS/2+0.12;
  group.add(hubInner);
  group.add(ring(0.245,0.024,brightMetal,THICKNESS/2+0.18));
  const hubPin = cylinderZ(0.105,0.16,boltMat);
  hubPin.position.z = THICKNESS/2+0.15;
  group.add(hubPin);
  group.add(ring(root*0.87,0.014,darkMetal,THICKNESS/2+0.068));

  // Surface rivets and a rotational reference marker are children of the gear.
  for(let i=0;i<Math.min(count,12);i++) {
    const a = i*2*Math.PI/Math.min(count,12);
    const r = root*0.89;
    const bolt = new THREE.Mesh(new THREE.SphereGeometry(0.032,12,9),boltMat);
    bolt.scale.z = 0.47;
    bolt.position.set(Math.cos(a)*r,Math.sin(a)*r,THICKNESS/2+0.078);
    group.add(bolt);
  }
  const indexMark = new THREE.Mesh(new THREE.BoxGeometry(0.055,0.21,0.025),brightMetal);
  indexMark.position.set(0,root*0.69,THICKNESS/2+0.082);
  group.add(indexMark);

  // Shafts are shown behind each wheel, reinforcing the physical depth.
  const rearShaft = cylinderZ(0.175,0.52,darkMetal);
  rearShaft.position.z = -0.35;
  group.add(rearShaft);
  const rearCollar = cylinderZ(0.34,0.08,hubMetal);
  rearCollar.position.z = -0.26;
  group.add(rearCollar);

  return {group,count,pitch,tip,materials:[frontMat,sideMat,...mats]};
}

function disposeGroup(group) {
  if(!group)return;
  const geometries=new Set(),materials=new Set();
  group.traverse(object=>{
    if(object.geometry)geometries.add(object.geometry);
    if(object.material) {
      const groupMats=Array.isArray(object.material)?object.material:[object.material];
      groupMats.forEach(m=>materials.add(m));
    }
  });
  group.removeFromParent();
  geometries.forEach(g=>g.dispose());
  materials.forEach(m=>m.dispose());
}

const contactMaterial = new THREE.MeshBasicMaterial({color:0xffdaa0,transparent:true,opacity:0.95,depthWrite:false});
const contactHaloMaterial = new THREE.MeshBasicMaterial({color:0xf3b867,transparent:true,opacity:0.24,depthWrite:false});
contactGlow = new THREE.Mesh(new THREE.SphereGeometry(0.075,20,14),contactMaterial);
contactHalo = new THREE.Mesh(new THREE.SphereGeometry(0.18,20,14),contactHaloMaterial);
gearbox.add(contactGlow,contactHalo);

function rebuild(teeth1,teeth2) {
  disposeGroup(driver?.group);
  disposeGroup(follower?.group);
  meshMaterials=[];
  teethA=teeth1;teethB=teeth2;
  driver=makeGear(teethA,true);
  follower=makeGear(teethB,false);
  const distanceBetweenCenters=driver.pitch+follower.pitch;
  const xA=-distanceBetweenCenters*0.57,xB=distanceBetweenCenters*0.43;
  driver.group.position.x=xA;
  follower.group.position.x=xB;
  gearbox.add(driver.group,follower.group);
  contactGlow.position.set(xA+driver.pitch,0,THICKNESS/2+0.24);
  contactHalo.position.copy(contactGlow.position);
  contactGlow.visible=showContact;
  contactHalo.visible=showContact;
  updateRatios();
  updateAngles();
}
function updateAngles() {
  if(!driver||!follower)return;
  // A positive input is shown clockwise, while the follower rotates oppositely.
  driver.group.rotation.z=-direction*angle;
  follower.group.rotation.z=direction*angle*teethA/teethB+Math.PI/teethB;
}
function updateRatios() {
  if(miniMode)return;
  document.getElementById('ratioLabel').textContent=`1 : ${(teethB/teethA).toFixed(2)}`;
  document.getElementById('outputSpeed').textContent=(speedRPM*teethA/teethB).toFixed(1);
  document.getElementById('outputBar').style.width=`${Math.min(100,speedRPM*teethA/teethB/120*100)}%`;
  document.getElementById('speedValue').textContent=`${speedRPM} RPM`;
}

if(!miniMode) {
document.getElementById('presets').addEventListener('click',event=>{
  const button=event.target.closest('[data-pair]');
  if(!button)return;
  const [a,b]=button.dataset.pair.split(',').map(Number);
  rebuild(a,b);
  document.querySelectorAll('[data-pair]').forEach(item=>{
    const active=item===button;
    item.classList.toggle('active',active);
    item.setAttribute('aria-pressed',String(active));
  });
});
document.getElementById('speed').addEventListener('input',event=>{
  speedRPM=Number(event.target.value);
  updateRatios();
});
document.getElementById('directions').addEventListener('click',event=>{
  const button=event.target.closest('[data-direction]');
  if(!button)return;
  direction=Number(button.dataset.direction);
  document.querySelectorAll('[data-direction]').forEach(item=>{
    const active=item===button;
    item.classList.toggle('active',active);
    item.setAttribute('aria-pressed',String(active));
  });
  updateAngles();
});
document.getElementById('playToggle').addEventListener('click',event=>{
  isRunning=!isRunning;
  event.currentTarget.textContent=isRunning?'Ⅱ 暂停':'▶ 继续';
  event.currentTarget.classList.toggle('featured',isRunning);
});
document.getElementById('stepButton').addEventListener('click',()=>{
  angle+=Math.PI/12;
  updateAngles();
});
document.getElementById('resetCamera').addEventListener('click',resetCamera);
document.getElementById('wireToggle').addEventListener('click',event=>{
  wireframe=!wireframe;
  meshMaterials.forEach(mat=>{mat.wireframe=wireframe;mat.needsUpdate=true;});
  event.currentTarget.classList.toggle('off',!wireframe);
  event.currentTarget.setAttribute('aria-pressed',String(wireframe));
});
document.getElementById('contactToggle').addEventListener('click',event=>{
  showContact=!showContact;
  contactGlow.visible=showContact;
  contactHalo.visible=showContact;
  event.currentTarget.classList.toggle('off',!showContact);
  event.currentTarget.setAttribute('aria-pressed',String(showContact));
});

let dragging=false,lastX=0,lastY=0;
renderer.domElement.addEventListener('pointerdown',event=>{
  dragging=true;
  lastX=event.clientX;
  lastY=event.clientY;
  renderer.domElement.setPointerCapture(event.pointerId);
});
renderer.domElement.addEventListener('pointermove',event=>{
  if(!dragging)return;
  azimuth-=(event.clientX-lastX)*0.006;
  elevation=Math.max(-1.23,Math.min(1.23,elevation+(event.clientY-lastY)*0.005));
  lastX=event.clientX;
  lastY=event.clientY;
  updateCamera();
});
renderer.domElement.addEventListener('pointerup',()=>dragging=false);
renderer.domElement.addEventListener('pointercancel',()=>dragging=false);
renderer.domElement.addEventListener('wheel',event=>{
  event.preventDefault();
  distance=Math.max(5.8,Math.min(17,distance+event.deltaY*0.006));
  updateCamera();
},{passive:false});
}

let currentWidth=0,currentHeight=0;
function resize() {
  const width=mount.clientWidth,height=mount.clientHeight;
  if(!width||!height)return;
  renderer.setSize(width,height,false);
  camera.aspect=width/height;
  camera.updateProjectionMatrix();
  if(currentWidth===0)resetCamera();
  currentWidth=width;currentHeight=height;
}
new ResizeObserver(resize).observe(mount);
resize();
rebuild(teethA,teethB);

const reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if(reduceMotion) {
  isRunning=false;
  if(!miniMode) {
    const button=document.getElementById('playToggle');
    button.textContent='▶ 继续';button.classList.remove('featured');
  }
}
let previous=performance.now(),sampleTime=performance.now(),frames=0;
let lastMiniFrame=0,firstMiniRender=true;
if(miniMode)window.addEventListener('message',event=>{
  if(event.origin===window.location.origin&&event.data?.type==='mini-scene-status-request'&&!firstMiniRender) {
    window.parent.postMessage({type:'mini-scene-ready'},window.location.origin);
  }
});
function animate(now) {
  requestAnimationFrame(animate);
  if(miniMode) {
    if(document.hidden||(reduceMotion&&!firstMiniRender))return;
    if(now-lastMiniFrame<1000/24)return;
    lastMiniFrame=now;
  }
  const dt=Math.min(0.06,(now-previous)/1000);
  previous=now;
  if(isRunning) angle+=dt*speedRPM*Math.PI*2/60;
  updateAngles();
  if(showContact) {
    const shimmer=0.85+Math.sin(now*0.007)*0.15;
    contactGlow.scale.setScalar(shimmer);
    contactHalo.scale.setScalar(0.9+Math.sin(now*0.004)*0.17);
  }
  renderer.render(scene,camera);
  if(miniMode) {
    if(firstMiniRender) {
      firstMiniRender=false;
      window.parent.postMessage({type:'mini-scene-ready'},window.location.origin);
    }
    return;
  }
  frames++;
  if(now-sampleTime>1000) {
    document.getElementById('fps').textContent=Math.round(frames*1000/(now-sampleTime));
    frames=0;sampleTime=now;
  }
}
requestAnimationFrame(animate);
