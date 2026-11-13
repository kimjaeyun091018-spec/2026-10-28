// HD-2D 배경: 1구역(이끼 덮인 지하철)과 환기구를 Three.js 3D로 그린다. 캐릭터·적·이펙트는 index.html의 2D 캔버스가 위에 그림.
// 좌표: 게임 좌표 그대로 (x 오른쪽, y 아래 → Three에서는 y를 뒤집음), 1단위 = 게임 1px.
// 카메라는 정면 옆에서 보는 원근 카메라. 깊이 z=0 평면이 2D 화면과 정확히 겹치도록 거리(D)와 화각을 맞춤
// → 블록 앞면(z=0)은 2D 충돌 칸과 픽셀 단위로 일치하고, 뒤로 갈수록 작아져 깊이감이 생김.
import * as THREE from './lib/three.module.min.js';   // Three.js 0.160.0 (MIT, lib/three.LICENSE). 저장소에 포함해 외부 CDN 없이 동작

const D = 260;                 // 카메라와 z=0 평면 사이 거리
const DEPTH = 64;              // 블록 깊이 (앞면 z=0 → 뒷면 z=-64)

function hash(x, y) {
  let n = (x * 374761393 + y * 668265263) | 0;
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
}

// 도트 텍스처: 작은 캔버스에 그려 픽셀 그대로 확대 (Nearest)
function tex(w, h, draw, repeat) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d');
  g.imageSmoothingEnabled = false;
  draw(g, w, h);
  const t = new THREE.CanvasTexture(c);
  t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
  t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
  return t;
}
const px = (g, x, y, w, h, c) => { g.fillStyle = c; g.fillRect(x, y, w, h); };
function noise(g, w, h, colors, n, seed = 1) {
  for (let i = 0; i < n; i++) px(g, Math.floor(hash(i, seed) * w), Math.floor(hash(seed, i) * h), 1, 1, colors[i % colors.length]);
}

// tiles.png(32x32 칸)의 한 칸을 텍스처로
function atlasTex(img, col, row, opts = {}) {
  return tex(32, 32, g => {
    g.drawImage(img, col * 32, row * 32, 32, 32, 0, 0, 32, 32);
    if (opts.dark) { g.fillStyle = `rgba(0,0,0,${opts.dark})`; g.fillRect(0, 0, 32, 32); }
  });
}

// ---------- 텍스처들 ----------
function mossTopTex() {
  return tex(32, 32, g => {
    px(g, 0, 0, 32, 32, '#4f6b34');
    noise(g, 32, 32, ['#5f7f3c', '#3f5a2c', '#6c8f44', '#36502a'], 260, 3);
    noise(g, 32, 32, ['#9fbf6a'], 18, 7);
  });
}
function trainTex() {
  return tex(360, 80, g => {
    px(g, 0, 0, 360, 80, '#7c7d72');                       // 차체
    px(g, 0, 0, 360, 6, '#5d5f58');                        // 지붕 가장자리
    px(g, 0, 50, 360, 6, '#8a3a30'); px(g, 0, 56, 360, 2, '#5a2a24');   // 붉은 띠
    px(g, 0, 62, 360, 18, '#55574f');                      // 아래쪽 (그늘)
    for (let i = 0; i < 6; i++) {                          // 창문
      const x = 18 + i * 56;
      if (i === 2) { px(g, x, 10, 30, 52, '#3a3d38'); px(g, x + 2, 12, 12, 26, '#1d2d30'); px(g, x + 16, 12, 12, 26, '#1d2d30'); continue; }   // 문
      px(g, x, 14, 40, 26, '#202f33'); px(g, x + 2, 16, 36, 22, '#2a3f44');
      px(g, x + 4, 18, 10, 2, '#5d7b7c'); px(g, x + 6, 22, 4, 2, '#4a6466');                   // 반사
      px(g, x, 40, 40, 2, '#5d5f58');
    }
    px(g, 170, 4, 14, 8, '#2c2e2a'); g.fillStyle = '#d8d4b8'; g.font = 'bold 8px monospace'; g.fillText('1', 174, 11);
    noise(g, 360, 80, ['#6a6b61', '#8e8f83', '#5f604f'], 900, 5);
    for (let i = 0; i < 40; i++) {                         // 녹물 자국
      const x = Math.floor(hash(i, 11) * 360), l = 4 + Math.floor(hash(i, 12) * 14);
      px(g, x, 42 + Math.floor(hash(i, 13) * 8), 1, l, '#6b4a34');
    }
    for (let x = 0; x < 360; x++) {                        // 지붕 이끼와 늘어진 덩굴
      const m = Math.floor(hash(x >> 2, 21) * 5);
      px(g, x, 0, 1, m, '#4f7a34');
      if (hash(x, 22) < 0.06) { const l = 6 + Math.floor(hash(x, 23) * 30); px(g, x, m, 1, l, '#3f6a30'); if (l > 10) px(g, x - 1, m + 6, 3, 2, '#5d8f3e'); }
    }
  });
}
function wallTex() {
  // 뒷벽: 때 묻은 흰 타일 + 아치 창(투명) + 이끼
  return tex(128, 128, g => {
    px(g, 0, 0, 128, 128, '#6b6d62');
    for (let y = 0; y < 128; y += 8) for (let x = 0; x < 128; x += 8) {
      const c = hash(x, y) < 0.15 ? '#5c5e54' : (hash(x + 1, y) < 0.1 ? '#7a7c70' : '#6b6d62');
      px(g, x, y, 7, 7, c); px(g, x, y + 7, 8, 1, '#4c4e46'); px(g, x + 7, y, 1, 8, '#4c4e46');
    }
    noise(g, 128, 128, ['#5a5c52', '#4f6b34'], 300, 9);
    for (let x = 0; x < 128; x++) { const m = Math.floor(hash(x >> 1, 31) * 10); px(g, x, 128 - m, 1, m, '#40592c'); }
  }, [1, 1]);
}
function archWindowTex() {
  // 아치 창: 테두리만 그리고 안쪽은 투명 → 뒤의 먼 정글이 보임
  return tex(64, 96, g => {
    px(g, 0, 0, 64, 96, '#5c5e54');
    g.clearRect(8, 28, 48, 68);
    for (let y = 8; y < 28; y++) {
      const half = Math.sqrt(Math.max(0, 24 * 24 - (28 - y) ** 2));
      g.clearRect(32 - half, y, half * 2, 1);
    }
    for (let i = 0; i < 6; i++) px(g, 8 + i * 9, 28, 2, 68, '#3c3e38');   // 창살
    px(g, 8, 60, 48, 2, '#3c3e38');
    noise(g, 64, 96, ['#4f6b34', '#3f5a2c'], 60, 4);
  });
}
function pillarTex() {
  return tex(24, 64, g => {
    px(g, 0, 0, 24, 64, '#77786d'); px(g, 0, 0, 3, 64, '#8a8b80'); px(g, 20, 0, 4, 64, '#5e5f56');
    noise(g, 24, 64, ['#6a6b61', '#5f604f', '#4f6b34'], 160, 2);
    for (let y = 0; y < 64; y += 16) px(g, 0, y, 24, 1, '#5a5b52');
  }, [1, 4]);
}
function signTex() {
  return tex(32, 24, g => {
    px(g, 0, 0, 32, 24, '#2a2d2a'); px(g, 1, 1, 30, 22, '#3a3e3a');
    g.fillStyle = '#d8d4b8'; g.font = 'bold 16px monospace'; g.fillText('1', 11, 18);
    px(g, 0, 0, 32, 2, '#4f7a34');
  });
}
function fernTex(seed) {
  return tex(32, 32, g => {
    for (let k = 0; k < 7; k++) {
      const a = -Math.PI / 2 + (k - 3) * 0.32 + (hash(k, seed) - 0.5) * 0.2;
      const l = 12 + hash(seed, k) * 14;
      for (let i = 0; i < l; i++) {
        const x = 16 + Math.cos(a) * i, y = 31 + Math.sin(a) * i + (i * i) * 0.012 * Math.abs(k - 3);
        px(g, Math.round(x), Math.round(y), 1, 1, '#3f6a30');
        if (i % 3 === 1 && i > 3) { px(g, Math.round(x - 1), Math.round(y), 1, 1, '#5d8f3e'); px(g, Math.round(x + 1), Math.round(y - 1), 1, 1, '#6fa848'); }
      }
    }
  });
}
function vineTex(seed) {
  return tex(16, 64, g => {
    for (let k = 0; k < 2; k++) {
      const x0 = 3 + k * 8 + Math.floor(hash(k, seed) * 3), l = 30 + Math.floor(hash(seed, k) * 34);
      for (let y = 0; y < l; y++) {
        const x = x0 + Math.round(Math.sin(y * 0.3 + k) * 1.2);
        px(g, x, y, 1, 1, '#3f6a30');
        if (y % 5 === 2) px(g, x + ((y >> 2) % 2 ? 1 : -2), y, 2, 1, '#5d8f3e');
      }
    }
  });
}
function benchTex() {
  return tex(32, 16, g => {
    px(g, 0, 0, 32, 16, '#6e3a30'); for (let x = 0; x < 32; x += 10) px(g, x, 0, 1, 16, '#4a2620');
    px(g, 0, 0, 32, 2, '#8a4c3e'); noise(g, 32, 16, ['#5a3028'], 30, 6);
  });
}
function panelTex() {
  // 환기구 벽: 리벳 박힌 금속 패널, 녹, 이끼
  return tex(64, 64, g => {
    px(g, 0, 0, 64, 64, '#4a5250');
    for (let y = 0; y < 64; y += 32) for (let x = 0; x < 64; x += 32) {
      px(g, x, y, 32, 1, '#2e3433'); px(g, x, y, 1, 32, '#2e3433'); px(g, x + 1, y + 1, 30, 1, '#5d6664');
      for (const [rx, ry] of [[3, 3], [28, 3], [3, 28], [28, 28]]) { px(g, x + rx, y + ry, 1, 1, '#757e7b'); px(g, x + rx + 1, y + ry + 1, 1, 1, '#2e3433'); }
      for (let i = 0; i < 6; i++) px(g, x + 2 + i * 5, y + 10, 3, 1, '#3a4240');   // 통풍 홈
    }
    noise(g, 64, 64, ['#6b4a34', '#5a3d2c', '#42504c'], 160, 8);
    for (let i = 0; i < 10; i++) { const x = Math.floor(hash(i, 41) * 64); px(g, x, 0, 1, 6 + Math.floor(hash(i, 42) * 20), '#6b4a34'); }
    noise(g, 64, 64, ['#4f6b34', '#3f5a2c'], 50, 12);
  }, [1, 1]);
}
function fanTex() {
  return tex(64, 64, g => {
    g.clearRect(0, 0, 64, 64);
    for (let b = 0; b < 4; b++) {
      const a0 = b * Math.PI / 2;
      for (let r = 6; r < 30; r++) for (let t = -0.32; t < 0.32; t += 0.02) {
        const a = a0 + t + r * 0.012;
        px(g, Math.round(32 + Math.cos(a) * r), Math.round(32 + Math.sin(a) * r), 1, 1, t < -0.2 ? '#7a8380' : '#596260');
      }
    }
    for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) { const d = Math.hypot(x - 32, y - 32); if (d < 7) px(g, x, y, 1, 1, d < 3 ? '#9aa39f' : '#3e4644'); }
  });
}
function shaftTex() {
  // 빛줄기: 위가 밝고 아래로 사라지는 세로 그라데이션 (더해서 그림)
  return tex(8, 64, g => {
    for (let y = 0; y < 64; y++) { g.fillStyle = `rgba(220,235,190,${(1 - y / 64) * 0.55})`; g.fillRect(0, y, 8, 1); }
    g.clearRect(0, 0, 1, 64); g.clearRect(7, 0, 1, 64);
  });
}

// ---------- 장면 ----------
export function createWorld3D({ canvas, tileAt, W, H, T, VW, VH, RS, tilesImg, backdropImg, maxTx }) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false });
  renderer.setPixelRatio(1);
  renderer.setSize(VW * RS, VH * RS, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#0e1a1c');
  scene.fog = new THREE.Fog('#16262a', D + 80, D + 900);
  const camera = new THREE.PerspectiveCamera(2 * Math.atan(VH / 2 / D) * 180 / Math.PI, VW / VH, 1, 4000);

  const Y = y => -y;                                       // 게임 y(아래) → Three y(위)
  const solid = (tx, ty) => tileAt(tx, ty) === '#';
  const lam = (map, extra = {}) => new THREE.MeshLambertMaterial({ map, ...extra });
  const zoneOf = tx => (tx < 36 ? 0 : tx < 46 ? 1 : tx < 80 ? 2 : 3);   // tiles.png 줄 = index.html ZONES 순서

  // --- 블록: 맵의 '#' 칸을 3D 상자로 (앞면 z=0, 깊이 64). 구역·드러남·변형별로 InstancedMesh ---
  const geo = new THREE.BoxGeometry(T, T, DEPTH);
  const topMat = lam(mossTopTex());
  const groups = new Map();
  for (let ty = 0; ty < H; ty++) for (let tx = 0; tx <= maxTx; tx++) {
    if (!solid(tx, ty)) continue;
    // 사방이 막힌 칸 중 공기와 3칸 넘게 떨어진 것은 화면에 거의 안 보이므로 앞면만 어둡게 한 장으로
    const inner = solid(tx - 1, ty) && solid(tx + 1, ty) && solid(tx, ty - 1) && solid(tx, ty + 1);
    const z = zoneOf(tx), v = inner ? 3 : Math.floor(hash(tx, ty) * 3);
    const key = z + ':' + v;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push([tx, ty]);
  }
  const m4 = new THREE.Matrix4();
  for (const [key, cells] of groups) {
    const [z, v] = key.split(':').map(Number);
    const front = lam(atlasTex(tilesImg, v, z));
    const side = lam(atlasTex(tilesImg, v === 3 ? 3 : (v + 1) % 3, z, { dark: 0.35 }));
    const bottom = lam(atlasTex(tilesImg, 3, z, { dark: 0.3 }));
    const mesh = new THREE.InstancedMesh(geo, [side, side, topMat, bottom, front, side], cells.length);
    cells.forEach(([tx, ty], i) => { m4.makeTranslation(tx * T + T / 2, Y(ty * T + T / 2), -DEPTH / 2); mesh.setMatrixAt(i, m4); });
    scene.add(mesh);
  }

  // 블록 위 풀잎 술(앞쪽)과 아래로 늘어진 덩굴
  const grassMat = new THREE.MeshLambertMaterial({ map: (() => { const t = atlasTex(tilesImg, 4, 0); return t; })(), transparent: true, alphaTest: 0.5 });
  const grassGeo = new THREE.PlaneGeometry(T, T);
  const vineMats = [0, 1, 2].map(s => new THREE.MeshLambertMaterial({ map: vineTex(s), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
  const vineGeo = new THREE.PlaneGeometry(16, 64);
  const swaying = [];
  for (let ty = 1; ty < H - 1; ty++) for (let tx = 0; tx <= maxTx; tx++) {
    if (!solid(tx, ty)) continue;
    if (!solid(tx, ty - 1)) {
      for (const zz of [0.5, -20, -44]) {                    // 윗면 앞·중간·뒤에 풀잎
        const p = new THREE.Mesh(grassGeo, grassMat);
        p.position.set(tx * T + T / 2, Y(ty * T - 5), zz);
        scene.add(p);
      }
    }
    if (!solid(tx, ty + 1) && tileAt(tx, ty + 1) !== '^' && hash(tx, ty + 99) < 0.45) {
      const p = new THREE.Mesh(vineGeo, vineMats[Math.floor(hash(tx, ty) * 3)]);
      p.position.set(tx * T + T / 2, Y((ty + 1) * T + 32), -6 - hash(ty, tx) * 40);
      scene.add(p); swaying.push(p);
    }
  }

  // --- 1구역: 이끼 덮인 지하철 승강장 (x 32~576, 천장 y 640, 바닥 y 832) ---
  const FLOOR = 832, CEIL = 640, X0 = 32, X1 = 576;
  // 승강장 바닥은 블록(깊이 64) 뒤로 조금 더 이어지고, 그 뒤는 선로가 있는 낮은 바닥
  const platform = new THREE.Mesh(new THREE.BoxGeometry(X1 - X0, 16, 30), [lam(atlasTex(tilesImg, 0, 0, { dark: 0.3 })), lam(atlasTex(tilesImg, 0, 0, { dark: 0.3 })), topMat, topMat, lam(atlasTex(tilesImg, 1, 0)), topMat]);
  platform.position.set((X0 + X1) / 2, Y(FLOOR + 8), -DEPTH - 15);
  scene.add(platform);
  const trackY = FLOOR + 18;
  const bed = new THREE.Mesh(new THREE.PlaneGeometry(X1 - X0 + 400, 200), lam(tex(32, 32, g => { px(g, 0, 0, 32, 32, '#3a3a33'); noise(g, 32, 32, ['#4a4a40', '#2c2c26', '#4f6b34'], 200, 14); }, [20, 6])));
  bed.rotation.x = -Math.PI / 2; bed.position.set((X0 + X1) / 2, Y(trackY), -DEPTH - 30 - 100);
  scene.add(bed);
  const railMat = lam(tex(4, 4, g => px(g, 0, 0, 4, 4, '#6a6258')));
  for (const rz of [-140, -170]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(X1 - X0 + 400, 3, 3), railMat);
    rail.position.set((X0 + X1) / 2, Y(trackY - 2), rz); scene.add(rail);
  }
  // 열차
  const train = new THREE.Mesh(new THREE.BoxGeometry(400, 116, 50), [lam(atlasTex(tilesImg, 0, 0, { dark: 0.4 })), lam(atlasTex(tilesImg, 0, 0, { dark: 0.4 })), topMat, topMat, lam(trainTex()), lam(trainTex())]);
  train.position.set(330, Y(trackY - 62), -150);
  scene.add(train);
  // 기둥 + 1번 표지판 + 벽등
  const pillarMat = lam(pillarTex());
  const lamps = [];
  for (const x of [130, 330, 530]) {
    const p = new THREE.Mesh(new THREE.BoxGeometry(22, FLOOR - CEIL + 60, 22), pillarMat);
    p.position.set(x, Y((FLOOR + CEIL) / 2 - 30), -100); scene.add(p);
    const s = new THREE.Mesh(new THREE.PlaneGeometry(26, 20), lam(signTex()));
    s.position.set(x, Y(CEIL + 50), -88); scene.add(s);
    const L = new THREE.PointLight('#ffb070', 900, 260, 1.4);
    L.position.set(x + 14, Y(CEIL + 80), -70); scene.add(L); lamps.push(L);
    const bulb = new THREE.Mesh(new THREE.BoxGeometry(4, 3, 3), new THREE.MeshBasicMaterial({ color: '#ffd9a0' }));
    bulb.position.copy(L.position); scene.add(bulb);
  }
  // 벤치
  const benchMat = lam(benchTex());
  for (const x of [190, 250, 410]) {
    const b = new THREE.Mesh(new THREE.BoxGeometry(34, 10, 12), benchMat);
    b.position.set(x, Y(FLOOR - 9), -52); scene.add(b);
    const back = new THREE.Mesh(new THREE.BoxGeometry(34, 16, 3), benchMat);
    back.position.set(x, Y(FLOOR - 20), -58); scene.add(back);
  }
  // 뒷벽 (선로 뒤) + 아치 창 너머 먼 정글
  const wallZ = -230, WALL_TOP = CEIL - 40, WALL_H = trackY - WALL_TOP;
  const wallMat = lam(wallTex());
  const arches = [60, 230, 400, 570], AW = 96, AH = 144, A_TOP = trackY - 192;
  function wallPanel(x0, x1, y0, y1) {
    if (x1 <= x0 || y1 <= y0) return;
    const m = wallMat.clone(); m.map = wallMat.map.clone(); m.map.needsUpdate = true;
    m.map.repeat.set((x1 - x0) / 128, (y1 - y0) / 128);
    const w = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, y1 - y0), m);
    w.position.set((x0 + x1) / 2, Y((y0 + y1) / 2), wallZ - 1); scene.add(w);
  }
  let wx = X0 - 300;
  for (const ax of arches) {
    wallPanel(wx, ax - AW / 2 + 8, WALL_TOP, trackY);        // 창 사이 벽
    wallPanel(ax - AW / 2 + 8, ax + AW / 2 - 8, WALL_TOP, A_TOP + 8);   // 창 위
    wallPanel(ax - AW / 2 + 8, ax + AW / 2 - 8, A_TOP + AH - 6, trackY); // 창 아래
    wx = ax + AW / 2 - 8;
  }
  wallPanel(wx, X1 + 300, WALL_TOP, trackY);
  const archMat = new THREE.MeshLambertMaterial({ map: archWindowTex(), transparent: true, alphaTest: 0.5 });
  for (const x of arches) {
    const fr = new THREE.Mesh(new THREE.PlaneGeometry(AW, AH), archMat);
    fr.position.set(x, Y(A_TOP + AH / 2), wallZ + 1); scene.add(fr);
  }
  // 뒤쪽 천장: 블록 천장(깊이 64) 뒤로 뒷벽까지 이어지는 판, 아래면에 이끼
  const ceil = new THREE.Mesh(new THREE.BoxGeometry(X1 - X0 + 600, 24, -wallZ - DEPTH), [lam(atlasTex(tilesImg, 3, 0)), lam(atlasTex(tilesImg, 3, 0)), lam(atlasTex(tilesImg, 3, 0)), lam(mossTopTex()), lam(atlasTex(tilesImg, 1, 0, { dark: 0.2 })), lam(atlasTex(tilesImg, 3, 0))]);
  ceil.position.set((X0 + X1) / 2, Y(WALL_TOP - 12), (wallZ - DEPTH) / 2 - 1); scene.add(ceil);
  // 먼 정글 (1구역 그림을 아치 창 너머 판으로)
  if (backdropImg) {
    const t = new THREE.Texture(backdropImg); t.colorSpace = THREE.SRGBColorSpace;
    if (backdropImg.complete && backdropImg.naturalWidth) t.needsUpdate = true;
    else backdropImg.addEventListener('load', () => { t.needsUpdate = true; });
    t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
    const far = new THREE.Mesh(new THREE.PlaneGeometry(1400, 788), new THREE.MeshBasicMaterial({ map: t, fog: false, color: '#b4c2b0' }));
    far.position.set(330, Y(trackY - 260), -520); scene.add(far);
  }
  // 고사리 (승강장 위, 여러 깊이) — 가로세로 두 장을 엇갈려 세움
  const fernMats = [0, 1, 2].map(s => new THREE.MeshLambertMaterial({ map: fernTex(s + 3), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
  for (let i = 0; i < 26; i++) {
    const x = X0 + 10 + hash(i, 51) * (X1 - X0 - 20), z = -4 - hash(i, 52) * 90, s = 18 + hash(i, 53) * 22;
    const fy = z < -DEPTH - 30 ? trackY : FLOOR;
    for (const r of [0, Math.PI / 2]) {
      const f = new THREE.Mesh(new THREE.PlaneGeometry(s, s), fernMats[i % 3]);
      f.position.set(x, Y(fy - s / 2 + 1), z); f.rotation.y = r + hash(i, 54); scene.add(f); swaying.push(f);
    }
  }
  // 천장 틈으로 들어오는 빛줄기
  const shaftMat = new THREE.MeshBasicMaterial({ map: shaftTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false });
  const shafts = [];
  for (const [x, z, w] of [[200, -120, 40], [450, -170, 60], [90, -60, 24]]) {
    const s = new THREE.Mesh(new THREE.PlaneGeometry(w, 260), shaftMat);
    s.position.set(x, Y(CEIL + 110), z); s.rotation.z = -0.35; scene.add(s); shafts.push(s);
  }

  // --- 환기구 (x 576~736, y 160~832, 세로 갱도) ---
  const VX0 = 576, VX1 = 736, VY0 = 160, VY1 = 832;
  const pmat = lam(panelTex());
  pmat.map.repeat.set((VX1 - VX0) / 64, (VY1 - VY0) / 64);
  const back = new THREE.Mesh(new THREE.PlaneGeometry(VX1 - VX0 + 64, VY1 - VY0), pmat);
  back.position.set((VX0 + VX1) / 2, Y((VY0 + VY1) / 2), -DEPTH - 30); scene.add(back);
  for (const x of [VX0 - 8, VX1 + 8]) {                       // 옆벽
    const sw = new THREE.Mesh(new THREE.PlaneGeometry(DEPTH + 30, VY1 - VY0), lam(panelTex()));
    sw.material.map.repeat.set(1.5, (VY1 - VY0) / 64);
    sw.rotation.y = x < VX0 ? Math.PI / 2 : -Math.PI / 2;
    sw.position.set(x + (x < VX0 ? 8 : -8), Y((VY0 + VY1) / 2), -(DEPTH + 30) / 2); scene.add(sw);
  }
  const pipeMat = lam(tex(8, 32, g => { px(g, 0, 0, 8, 32, '#5c6563'); px(g, 0, 0, 2, 32, '#7b8582'); px(g, 6, 0, 2, 32, '#3c4442'); for (let y = 0; y < 32; y += 16) px(g, 0, y, 8, 2, '#3c4442'); noise(g, 8, 32, ['#6b4a34'], 10, 3); }, [1, 20]));
  for (const [x, r] of [[VX0 + 12, 6], [VX0 + 26, 3], [VX1 - 14, 7]]) {
    const p = new THREE.Mesh(new THREE.CylinderGeometry(r, r, VY1 - VY0, 8), pipeMat);
    p.position.set(x, Y((VY0 + VY1) / 2), -DEPTH - 20); scene.add(p);
  }
  for (const y of [300, 520, 700]) {
    const p = new THREE.Mesh(new THREE.CylinderGeometry(4, 4, VX1 - VX0, 8), pipeMat);
    p.rotation.z = Math.PI / 2; p.position.set((VX0 + VX1) / 2, Y(y), -DEPTH - 24); scene.add(p);
  }
  // 대형 환풍기 2개 (돌아감)
  const fans = [];
  const fanMat = new THREE.MeshLambertMaterial({ map: fanTex(), transparent: true, alphaTest: 0.5 });
  const ringMat = lam(tex(8, 8, g => px(g, 0, 0, 8, 8, '#3a4240')));
  for (const [y, r] of [[420, 52], [640, 40]]) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(r, 5, 6, 24), ringMat);
    ring.position.set((VX0 + VX1) / 2, Y(y), -DEPTH - 26); scene.add(ring);
    const blades = new THREE.Mesh(new THREE.PlaneGeometry(r * 2, r * 2), fanMat);
    blades.position.set((VX0 + VX1) / 2, Y(y), -DEPTH - 27); scene.add(blades); fans.push(blades);
    const glow = new THREE.PointLight('#9fd0c0', 300, 180, 1.5);
    glow.position.set((VX0 + VX1) / 2, Y(y), -DEPTH - 60); scene.add(glow);
  }
  // 비상등 (붉게 깜빡)
  const reds = [];
  for (const [x, y] of [[VX0 + 8, 260], [VX1 - 8, 480], [VX0 + 8, 760]]) {
    const L = new THREE.PointLight('#ff5040', 500, 140, 1.5); L.position.set(x, Y(y), -30); scene.add(L); reds.push(L);
    const b = new THREE.Mesh(new THREE.BoxGeometry(5, 4, 4), new THREE.MeshBasicMaterial({ color: '#ff8070' }));
    b.position.set(x, Y(y), -DEPTH - 28); scene.add(b);
  }
  // 갱도 위에서 내려오는 빛
  for (const [x, w] of [[640, 70], [700, 40]]) {
    const s = new THREE.Mesh(new THREE.PlaneGeometry(w, 520), shaftMat);
    s.position.set(x, Y(VY0 + 260), -DEPTH - 10); s.rotation.z = 0.12; scene.add(s); shafts.push(s);
  }

  // --- 조명 ---
  scene.add(new THREE.HemisphereLight('#a8cfc8', '#3a3628', 1.6));
  const sun = new THREE.DirectionalLight('#f6e2b4', 2.4);
  sun.position.set(220, 400, 300); scene.add(sun);
  const fill = new THREE.DirectionalLight('#7fb0a8', 0.5);
  fill.position.set(-200, 50, 400); scene.add(fill);

  // --- 떠다니는 포자 ---
  const N = 260, pos = new Float32Array(N * 3), base = [];
  for (let i = 0; i < N; i++) {
    const x = X0 + hash(i, 61) * (VX1 - X0), y = 160 + hash(i, 62) * 700, z = -10 - hash(i, 63) * 200;
    base.push([x, y, z]); pos.set([x, Y(y), z], i * 3);
  }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const spores = new THREE.Points(pg, new THREE.PointsMaterial({ color: '#d8e8a0', size: 2, sizeAttenuation: false, transparent: true, opacity: 0.7 }));
  scene.add(spores);

  function render(cx, cy, t) {
    camera.position.set(cx + VW / 2, Y(cy + VH / 2), D);
    camera.lookAt(cx + VW / 2, Y(cy + VH / 2), 0);
    for (const f of fans) f.rotation.z = -t * 3;
    lamps.forEach((L, i) => { L.intensity = 900 * (0.85 + 0.15 * Math.sin(t * 7 + i * 2) * (hash(Math.floor(t * 8), i) < 0.1 ? 3 : 1)); });
    reds.forEach((L, i) => { L.intensity = Math.sin(t * 3 + i) > 0.2 ? 500 : 60; });
    swaying.forEach((m, i) => { m.rotation.z = Math.sin(t * 1.3 + i) * 0.04; });
    shafts.forEach((s, i) => { s.material.opacity = 0.75 + 0.25 * Math.sin(t * 0.8 + i); });
    for (let i = 0; i < N; i++) {
      const [x, y, z] = base[i];
      pos[i * 3] = x + Math.sin(t * 0.3 + i) * 12;
      pos[i * 3 + 1] = Y(((y - t * 6 * (0.5 + hash(i, 64))) % 700 + 700) % 700 + 160);
      pos[i * 3 + 2] = z;
    }
    pg.attributes.position.needsUpdate = true;
    renderer.render(scene, camera);
  }
  return { render, renderer };
}
