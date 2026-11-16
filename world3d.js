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

// --- 2구역(가시덤불 도심) 텍스처 ---
function facadeTex(seed, w = 64, h = 128) {
  // 폐빌딩 벽: 콘크리트에 어두운 창, 깨진 창, 녹물, 이끼
  return tex(w, h, g => {
    const base = ['#5a4e4a', '#4e4846', '#62574e'][seed % 3];
    px(g, 0, 0, w, h, base);
    noise(g, w, h, ['#4a403c', '#6a5e56', '#3e3633'], w * h / 6, seed + 3);
    for (let y = 6; y < h - 4; y += 14) for (let x = 4; x < w - 6; x += 12) {
      const broken = hash(x + seed, y) < 0.25, lit = hash(y, x + seed) < 0.04;
      px(g, x, y, 8, 9, lit ? '#d98a50' : (broken ? '#1a1414' : '#2a2626'));
      if (!broken && !lit) { px(g, x + 1, y + 1, 3, 2, '#4a4a48'); }
      px(g, x, y + 9, 8, 1, '#3a3330');
    }
    for (let i = 0; i < 14; i++) { const x = Math.floor(hash(i, seed + 9) * w); px(g, x, 0, 1, 10 + Math.floor(hash(seed, i) * 40), '#5e3a2a'); }
    for (let x = 0; x < w; x++) { const m = Math.floor(hash(x >> 2, seed + 21) * 6); px(g, x, 0, 1, m, '#3e4a2c'); }
  });
}
function asphaltTex() {
  return tex(64, 64, g => {
    px(g, 0, 0, 64, 64, '#2e2a28'); noise(g, 64, 64, ['#3a3532', '#26221f', '#4a3a2c'], 700, 4);
    px(g, 0, 30, 64, 2, '#6a5a3a');                          // 차선 (빛바램)
    for (let i = 0; i < 6; i++) { let x = Math.floor(hash(i, 3) * 64), y = Math.floor(hash(3, i) * 64); for (let k = 0; k < 18; k++) { px(g, x, y, 1, 1, '#151210'); x += hash(k, i) < 0.5 ? 1 : 0; y += 1; } }
  }, [1, 1]);
}
function carTex(seed) {
  return tex(48, 24, g => {
    const body = ['#6a3a2c', '#3a4a48', '#5a5040'][seed % 3];
    px(g, 0, 8, 48, 12, body); px(g, 8, 0, 28, 9, body);
    px(g, 11, 2, 10, 6, '#1d2322'); px(g, 23, 2, 10, 6, '#1d2322');
    px(g, 4, 18, 9, 6, '#141210'); px(g, 34, 18, 9, 6, '#141210');
    noise(g, 48, 24, ['#7a4a30', '#4a2a20', '#2a1a14'], 160, seed + 5);
  });
}
function brambleTex() {
  return tex(8, 32, g => { px(g, 0, 0, 8, 32, '#4a2620'); px(g, 0, 0, 2, 32, '#6e3a2e'); px(g, 6, 0, 2, 32, '#2e1814'); noise(g, 8, 32, ['#3a1c18', '#5a3024'], 30, 7); }, [1, 6]);
}
// --- 3구역(식충식물 온실) 텍스처 ---
function glassTex() {
  // 철골 유리벽: 칸마다 반투명 청록 유리, 몇 칸은 깨져서 비어 있음
  return tex(64, 64, g => {
    for (let y = 0; y < 64; y += 32) for (let x = 0; x < 64; x += 32) {
      const broken = hash(x, y + 5) < 0.2;
      if (!broken) { g.fillStyle = 'rgba(150,200,190,0.28)'; g.fillRect(x, y, 32, 32); g.fillStyle = 'rgba(220,245,235,0.35)'; g.fillRect(x + 4, y + 3, 2, 10); }
      px(g, x, y, 32, 2, '#2e3a36'); px(g, x, y, 2, 32, '#2e3a36');
    }
    noise(g, 64, 64, ['#3f6a30'], 40, 9);
  }, [1, 1]);
}
function flytrapTex(seed) {
  // 파리지옥: 줄기 + 벌어진 두 잎(이빨) + 붉은 속
  return tex(48, 64, g => {
    for (let y = 30; y < 64; y++) px(g, 22 + Math.round(Math.sin(y * 0.15 + seed) * 2), y, 3, 1, '#3f6a30');
    px(g, 14, 46, 8, 3, '#5d8f3e'); px(g, 26, 52, 9, 3, '#5d8f3e');
    const open = 4 + seed % 3 * 2;
    for (let i = 0; i < 26; i++) {
      const x = 10 + i, cu = Math.round(Math.sin(i / 26 * Math.PI) * 9);
      px(g, x, 22 - cu - open, 1, cu + 2, '#5d8f3e'); px(g, x, 24 + open, 1, cu + 2, '#4f7a34');   // 위·아래 잎
      if (i % 3 === 0) { px(g, x, 23 - open, 1, 2, '#e8dcb0'); px(g, x, 23 + open, 1, 2, '#e8dcb0'); }  // 이빨
      px(g, x, 23 - open + 2, 1, Math.max(0, open * 2 - 3), '#a8323a');                               // 붉은 속
    }
  });
}
function pitcherTex() {
  return tex(32, 64, g => {
    for (let y = 14; y < 62; y++) { const w = Math.round(6 + Math.sin((y - 14) / 48 * Math.PI) * 7); px(g, 16 - w, y, w * 2, 1, y % 6 < 3 ? '#5d8f3e' : '#4f7a34'); px(g, 16 - w, y, 2, 1, '#2e4a24'); }
    px(g, 8, 12, 16, 3, '#a8323a'); px(g, 10, 4, 14, 6, '#6fa848'); px(g, 15, 62, 3, 2, '#3f6a30');
    noise(g, 32, 64, ['#8a2a30'], 20, 4);
  });
}
function bigLeafTex(seed) {
  return tex(64, 64, g => {
    for (let y = 0; y < 64; y++) for (let x = 0; x < 64; x++) {
      const u = (x - 32) / 30, v = (y - 34) / 28;
      if (u * u + v * v < 1 && !(Math.abs(v) < 0.6 && hash(Math.floor(x / 6), Math.floor(y / 5) + seed) < 0.12)) {
        const vein = Math.abs(x - 32) < 1 || (Math.abs((y - 34) - Math.abs(x - 32) * 0.6) < 0.8 && (x + y) % 2 === 0);
        const edge = u * u + v * v > 0.8;
        px(g, x, y, 1, 1, vein ? '#5f8f44' : edge ? '#2c4a24' : (hash(x >> 2, y >> 2) < 0.5 ? '#36602c' : '#3c6a30'));
      }
    }
    for (let y = 34; y < 64; y++) px(g, 31, y, 2, 1, '#3f6a30');
  });
}

// ---------- 장면 ----------
export function createWorld3D({ canvas, tileAt, W, H, T, VW, VH, RS, tilesImg, backdropImg, backdrop2Img, backdrop3Img, backdrop4Img, backdrop5Img, maxTx }) {
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
  // tiles.png 줄 = index.html ZONES 순서 (56줄 아래 균류 동굴, 76줄 아래 세계수 뿌리 핵)
  const zoneOf = (tx, ty = 0) => (ty >= 76 ? 5 : ty >= 56 ? 4 : tx < 36 ? 0 : tx < 46 ? 1 : tx < 80 ? 2 : 3);

  // --- 블록: 맵의 '#' 칸을 3D 상자로 (앞면 z=0, 깊이 64). 구역·드러남·변형별로 InstancedMesh ---
  const geo = new THREE.BoxGeometry(T, T, DEPTH);
  const topMat = lam(mossTopTex());
  const groups = new Map();
  for (let ty = 0; ty < H; ty++) for (let tx = 0; tx <= maxTx; tx++) {
    if (!solid(tx, ty)) continue;
    // 사방이 막힌 칸 중 공기와 3칸 넘게 떨어진 것은 화면에 거의 안 보이므로 앞면만 어둡게 한 장으로
    const inner = solid(tx - 1, ty) && solid(tx + 1, ty) && solid(tx, ty - 1) && solid(tx, ty + 1);
    const z = zoneOf(tx, ty), v = inner ? 3 : Math.floor(hash(tx, ty) * 3);
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
  const grassMats = [0, 1, 2, 3, 4, 5].map(z => new THREE.MeshLambertMaterial({ map: atlasTex(tilesImg, 4, z), transparent: true, alphaTest: 0.5 }));
  const grassMat = grassMats[0];
  const grassGeo = new THREE.PlaneGeometry(T, T);
  const vineMats = [0, 1, 2].map(s => new THREE.MeshLambertMaterial({ map: vineTex(s), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
  const vineGeo = new THREE.PlaneGeometry(16, 64);
  const swaying = [];
  for (let ty = 1; ty < H - 1; ty++) for (let tx = 0; tx <= maxTx; tx++) {
    if (!solid(tx, ty)) continue;
    if (!solid(tx, ty - 1)) {
      for (const zz of [0.5, -20, -44]) {                    // 윗면 앞·중간·뒤에 풀잎
        const p = new THREE.Mesh(grassGeo, grassMats[zoneOf(tx, ty)]);
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

  // 가시 바닥('^' 칸): 가시덤불 판을 깊이 여러 겹으로 세워 덤불처럼
  const thornMats = [0, 1, 2, 3, 4, 5].map(z => new THREE.MeshLambertMaterial({ map: atlasTex(tilesImg, 7, z), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
  for (let ty = 0; ty < H; ty++) for (let tx = 0; tx <= maxTx; tx++) {
    if (tileAt(tx, ty) !== '^') continue;
    for (const zz of [0.6, -14, -30, -48]) {
      const p = new THREE.Mesh(grassGeo, thornMats[zoneOf(tx, ty)]);
      p.position.set(tx * T + T / 2 + (hash(tx, zz) - 0.5) * 4, Y(ty * T + T / 2), zz);
      scene.add(p);
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

  function backdrop(img, w, h, x, y, z, tint) {
    if (!img) return;
    const t = new THREE.Texture(img); t.colorSpace = THREE.SRGBColorSpace;
    if (img.complete && img.naturalWidth) t.needsUpdate = true;
    else img.addEventListener('load', () => { t.needsUpdate = true; });
    t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: t, fog: false, color: tint }));
    m.position.set(x, Y(y), z); scene.add(m);
  }
  const extraLights = [];

  // --- 2구역: 가시덤불 도심 (윗길 x 736~1280, 천장 y 160, 바닥 y 288) ---
  {
    const CX0 = 736, CX1 = 1280, FL = 288, CE = 160;
    const road = new THREE.Mesh(new THREE.PlaneGeometry(CX1 - CX0 + 300, 560), lam(asphaltTex()));
    road.material.map.repeat.set((CX1 - CX0 + 300) / 64, 560 / 64);
    road.rotation.x = -Math.PI / 2; road.position.set((CX0 + CX1) / 2, Y(FL), -DEPTH - 280); scene.add(road);
    // 무너진 고가도로: 통로 천장 블록 뒤로 이어지다 끊김
    const slabMat = lam(atlasTex(tilesImg, 0, 2, { dark: 0.2 }));
    const slab = new THREE.Mesh(new THREE.BoxGeometry(380, 20, 110), slabMat);
    slab.position.set(CX0 + 190, Y(CE - 10), -DEPTH - 55); scene.add(slab);
    const broken = new THREE.Mesh(new THREE.BoxGeometry(120, 18, 110), slabMat);
    broken.position.set(CX0 + 430, Y(CE + 30), -DEPTH - 55); broken.rotation.z = -0.35; scene.add(broken);
    for (const x of [CX0 + 60, CX0 + 250]) {
      const col = new THREE.Mesh(new THREE.BoxGeometry(18, FL - CE + 10, 18), slabMat);
      col.position.set(x, Y((FL + CE) / 2), -DEPTH - 90); scene.add(col);
    }
    // 폐빌딩 (깊이 여러 겹)
    const facades = [0, 1, 2].map(i => facadeTex(i));
    for (let i = 0; i < 14; i++) {
      const z = -230 - (i % 3) * 120 - hash(i, 71) * 40;
      const w = 70 + hash(i, 72) * 70, h = 220 + hash(i, 73) * 260;
      const x = CX0 - 120 + i * 62 + hash(i, 74) * 30;
      const tm = facades[i % 3].clone(); tm.needsUpdate = true; tm.wrapS = tm.wrapT = THREE.RepeatWrapping; tm.repeat.set(w / 64, h / 128);
      const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, 60), lam(tm));
      b.position.set(x, Y(FL - h / 2), z); b.rotation.z = (hash(i, 75) - 0.5) * 0.06; scene.add(b);
    }
    // 녹슨 차
    const carMats = [0, 1, 2].map(i => lam(carTex(i), { transparent: true, alphaTest: 0.5 }));
    for (let i = 0; i < 6; i++) {
      const c = new THREE.Mesh(new THREE.BoxGeometry(48, 24, 22), [carMats[i % 3], carMats[i % 3], lam(atlasTex(tilesImg, 3, 2)), lam(atlasTex(tilesImg, 3, 2)), carMats[i % 3], carMats[i % 3]]);
      c.position.set(CX0 + 30 + i * 95 + hash(i, 81) * 30, Y(FL - 12), -DEPTH - 70 - hash(i, 82) * 120);
      c.rotation.y = (hash(i, 83) - 0.5) * 0.8; c.rotation.z = (hash(i, 84) - 0.5) * 0.15; scene.add(c);
    }
    // 가시덤불 덩굴: 빌딩 사이를 굽이치는 검붉은 줄기 + 가시
    const bMat = lam(brambleTex());
    const thornMat = lam(tex(4, 4, g => px(g, 0, 0, 4, 4, '#8a4a36')));
    const thornGeo = new THREE.ConeGeometry(1.6, 7, 4);
    for (let k = 0; k < 9; k++) {
      const pts = [];
      let x = CX0 - 60 + k * 70, y = FL + 5, z = -DEPTH - 20 - hash(k, 91) * 200;
      for (let j = 0; j < 6; j++) {
        pts.push(new THREE.Vector3(x, Y(y), z));
        x += 30 + hash(k, j) * 60; y -= 20 + hash(j, k) * 50; z -= (hash(k + j, 3) - 0.3) * 40;
      }
      const curve = new THREE.CatmullRomCurve3(pts);
      const r = 2 + hash(k, 92) * 3;
      scene.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 40, r, 5), bMat));
      for (let j = 0; j < 22; j++) {
        const u = j / 22, p0 = curve.getPointAt(u), tg = curve.getTangentAt(u);
        const th = new THREE.Mesh(thornGeo, thornMat);
        th.position.copy(p0); th.lookAt(p0.clone().add(new THREE.Vector3(-tg.y, tg.x, (hash(j, k) - 0.5)).normalize()));
        th.rotateX(Math.PI / 2); th.translateY(r + 2); scene.add(th);
      }
    }
    // 가로등 (붉게 깜빡이는 등)
    for (const x of [CX0 + 160, CX0 + 420]) {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 2, 110, 6), lam(tex(4, 4, g => px(g, 0, 0, 4, 4, '#3a3532'))));
      pole.position.set(x, Y(FL - 55), -DEPTH - 30); scene.add(pole);
      const head = new THREE.Mesh(new THREE.BoxGeometry(12, 4, 6), new THREE.MeshBasicMaterial({ color: '#ffb070' }));
      head.position.set(x + 5, Y(FL - 110), -DEPTH - 30); scene.add(head);
      const L = new THREE.PointLight('#ff9a60', 700, 220, 1.4); L.position.set(x + 5, Y(FL - 100), -DEPTH - 10); scene.add(L);
      extraLights.push({ L, base: 700, kind: 'flicker' });
    }
    const dusk = new THREE.PointLight('#ff7a50', 2600, 900, 1.0); dusk.position.set((CX0 + CX1) / 2, Y(CE - 220), -360); scene.add(dusk);
    extraLights.push({ L: dusk, base: 2600, kind: 'steady' });
    backdrop(backdrop2Img, 1600, 900, (CX0 + CX1) / 2, FL - 300, -900, '#c8a898');
  }

  // --- 3구역: 식충식물 온실 (세로 갱도 x 1280~1504, y 160~800) ---
  const traps = [];
  {
    const GX0 = 1280, GX1 = 1504, GY0 = 160, GY1 = 800;
    backdrop(backdrop3Img, 1000, 1200, (GX0 + GX1) / 2, (GY0 + GY1) / 2, -520, '#a8c8b8');
    const gm = new THREE.MeshLambertMaterial({ map: glassTex(), transparent: true, depthWrite: false, side: THREE.DoubleSide });
    gm.map.repeat.set((GX1 - GX0 + 260) / 64, (GY1 - GY0 + 200) / 64);
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(GX1 - GX0 + 260, GY1 - GY0 + 200), gm);
    glass.position.set((GX0 + GX1) / 2, Y((GY0 + GY1) / 2), -230); scene.add(glass);
    const steel = lam(tex(8, 32, g => { px(g, 0, 0, 8, 32, '#3a4642'); px(g, 0, 0, 2, 32, '#56625c'); px(g, 6, 0, 2, 32, '#26302c'); noise(g, 8, 32, ['#5e3a2a', '#3f6a30'], 16, 5); }, [1, 10]));
    for (let x = GX0 - 120; x <= GX1 + 120; x += 64) {        // 세로 철골
      const b = new THREE.Mesh(new THREE.BoxGeometry(6, GY1 - GY0 + 200, 6), steel);
      b.position.set(x, Y((GY0 + GY1) / 2), -226); scene.add(b);
    }
    for (let y = GY0 - 40; y <= GY1 + 60; y += 96) {          // 가로 들보 (앞쪽에도 몇 개)
      const b = new THREE.Mesh(new THREE.BoxGeometry(GX1 - GX0 + 260, 6, 6), steel);
      b.position.set((GX0 + GX1) / 2, Y(y), -226); scene.add(b);
      if ((y / 96) % 2 < 1) { const f = new THREE.Mesh(new THREE.BoxGeometry(GX1 - GX0, 5, 5), steel); f.position.set((GX0 + GX1) / 2, Y(y + 20), -DEPTH - 30); scene.add(f); }
    }
    // 식충식물: 파리지옥·벌레잡이통풀·큰 잎 (판을 엇갈려 세움)
    const trapMats = [0, 1, 2].map(i => new THREE.MeshLambertMaterial({ map: flytrapTex(i), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
    const pitcherMat = new THREE.MeshLambertMaterial({ map: pitcherTex(), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide });
    const leafMats = [0, 1].map(i => new THREE.MeshLambertMaterial({ map: bigLeafTex(i), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
    for (let i = 0; i < 26; i++) {
      const x = GX0 - 60 + hash(i, 101) * (GX1 - GX0 + 120), y = GY0 + 40 + hash(i, 102) * (GY1 - GY0 - 20);
      const kind = i % 3, z = -DEPTH - 20 - hash(i, 103) * 140 - (kind === 2 ? 40 : 0), s = (0.8 + hash(i, 104) * 1.2) * (kind === 2 ? 0.6 : 1);
      const [mat, w, h] = kind === 0 ? [trapMats[i % 3], 48, 64] : kind === 1 ? [pitcherMat, 32, 64] : [leafMats[i % 2], 64, 64];
      for (const r of kind === 2 ? [0] : [0, Math.PI / 2]) {
        const m = new THREE.Mesh(new THREE.PlaneGeometry(w * s, h * s), mat);
        m.position.set(x, Y(y - h * s / 2), z); m.rotation.y = r + hash(i, 105) * 0.6;
        if (kind === 2) m.rotation.z = (hash(i, 106) - 0.5) * 1.2;
        scene.add(m); (kind === 0 ? traps : swaying).push(m);
      }
    }
    // 바닥의 큰 식물 덤불
    for (let i = 0; i < 8; i++) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(44, 44), leafMats[i % 2]);
      m.position.set(GX0 + i * 32, Y(GY1 - 20), -DEPTH - 20 - hash(i, 111) * 60); m.rotation.z = (hash(i, 112) - 0.5) * 0.8; scene.add(m); swaying.push(m);
    }
    for (const [x, w] of [[1330, 50], [1420, 80], [1480, 40]]) {   // 유리 지붕 빛줄기
      const sh = new THREE.Mesh(new THREE.PlaneGeometry(w, 700), shaftMat);
      sh.position.set(x, Y(GY0 + 330), -150); sh.rotation.z = -0.18; scene.add(sh); shafts.push(sh);
    }
    for (const [x, y] of [[1330, 300], [1450, 560]]) {
      const L = new THREE.PointLight('#9fe0a0', 600, 260, 1.4); L.position.set(x, Y(y), -60); scene.add(L);
      extraLights.push({ L, base: 600, kind: 'pulse' });
    }
  }

  // --- 4구역: 균류 동굴 (x 320~1504, 천장 y 928, 바닥 y 1088) ---
  const shroomCaps = [];
  {
    const FX0 = 320, FX1 = 1504, CE = 928, FL = 1088;
    backdrop(backdrop4Img, 1700, 960, (FX0 + FX1) / 2, FL - 260, -760, '#9a90c0');
    const rock = lam(atlasTex(tilesImg, 0, 4, { dark: 0.25 }));
    const backWall = new THREE.Mesh(new THREE.PlaneGeometry(FX1 - FX0 + 300, 420), rock);
    backWall.material.map = backWall.material.map.clone(); backWall.material.map.needsUpdate = true;
    backWall.material.map.wrapS = backWall.material.map.wrapT = THREE.RepeatWrapping; backWall.material.map.repeat.set((FX1 - FX0 + 300) / 32, 420 / 32);
    backWall.position.set((FX0 + FX1) / 2, Y(FL - 150), -420); scene.add(backWall);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(FX1 - FX0 + 300, 360), lam(mossTopTex()));
    floor.rotation.x = -Math.PI / 2; floor.position.set((FX0 + FX1) / 2, Y(FL), -DEPTH - 180); scene.add(floor);
    // 거대 버섯: 줄기(원기둥) + 빛나는 반구 갓 + 갓 아래 주름판
    const stemMat = lam(tex(8, 32, g => { px(g, 0, 0, 8, 32, '#c8c0a8'); px(g, 0, 0, 2, 32, '#e0dac4'); px(g, 6, 0, 2, 32, '#9a9280'); noise(g, 8, 32, ['#b0a890'], 20, 3); }, [1, 3]));
    const capTex = tex(32, 16, g => { px(g, 0, 0, 32, 16, '#6a4a9a'); for (let i = 0; i < 14; i++) px(g, Math.floor(hash(i, 5) * 30), Math.floor(hash(5, i) * 14), 2, 2, '#7ff0e0'); px(g, 0, 0, 32, 3, '#8a6ac0'); });
    const gillMat = new THREE.MeshLambertMaterial({ color: '#3a2a50', side: THREE.DoubleSide });
    for (let i = 0; i < 16; i++) {
      const x = FX0 + 30 + i * 74 + hash(i, 121) * 40, z = -DEPTH - 40 - (i % 3) * 90 - hash(i, 122) * 40;
      const h = 60 + hash(i, 123) * 110, r = 22 + hash(i, 124) * 30;
      const stem = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.18, r * 0.26, h, 8), stemMat);
      stem.position.set(x, Y(FL - h / 2), z); stem.rotation.z = (hash(i, 125) - 0.5) * 0.25; scene.add(stem);
      const capMat = new THREE.MeshLambertMaterial({ map: capTex, emissive: '#3a1a6a', emissiveIntensity: 0.6 });
      const cap = new THREE.Mesh(new THREE.SphereGeometry(r, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), capMat);
      cap.position.set(x + Math.sin(stem.rotation.z) * -h / 2, Y(FL - h), z); cap.scale.y = 0.55; scene.add(cap); shroomCaps.push(cap);
      const gill = new THREE.Mesh(new THREE.CircleGeometry(r * 0.95, 14), gillMat);
      gill.rotation.x = Math.PI / 2; gill.position.copy(cap.position); scene.add(gill);
    }
    // 작은 버섯 무리 (판을 엇갈려 세움)
    const smallShroom = new THREE.MeshLambertMaterial({ map: tex(16, 16, g => { px(g, 6, 8, 3, 8, '#cfc8b0'); px(g, 2, 4, 12, 4, '#6a4a9a'); px(g, 3, 3, 10, 1, '#8a6ac0'); px(g, 5, 5, 1, 1, '#7ff0e0'); px(g, 10, 5, 1, 1, '#7ff0e0'); }), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide, emissive: '#201040' });
    for (let i = 0; i < 40; i++) {
      const sz = 8 + hash(i, 131) * 10;
      for (const r of [0, Math.PI / 2]) {
        const m = new THREE.Mesh(new THREE.PlaneGeometry(sz, sz), smallShroom);
        m.position.set(FX0 + hash(i, 132) * (FX1 - FX0), Y(FL - sz / 2), -6 - hash(i, 133) * 70); m.rotation.y = r + hash(i, 134); scene.add(m);
      }
    }
    // 버려진 광산: 레일, 광차, 나무 받침
    const wood = lam(tex(8, 32, g => { px(g, 0, 0, 8, 32, '#5a4028'); px(g, 0, 0, 2, 32, '#7a5838'); noise(g, 8, 32, ['#4a3020', '#3a2818'], 30, 6); }, [1, 4]));
    for (const rz of [-110, -126]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(FX1 - FX0, 2, 2), railMat); rail.position.set((FX0 + FX1) / 2, Y(FL - 1), rz); scene.add(rail);
    }
    const cart = new THREE.Mesh(new THREE.BoxGeometry(34, 20, 22), [wood, wood, lam(tex(4, 4, g => px(g, 0, 0, 4, 4, '#3a3a40'))), wood, wood, wood]);
    cart.position.set(FX0 + 520, Y(FL - 14), -118); cart.rotation.z = 0.12; scene.add(cart);
    for (let x = FX0 + 60; x < FX1; x += 220) {
      for (const dx of [-30, 30]) { const post = new THREE.Mesh(new THREE.BoxGeometry(8, FL - CE + 40, 8), wood); post.position.set(x + dx, Y((FL + CE) / 2 - 10), -DEPTH - 50); scene.add(post); }
      const beam = new THREE.Mesh(new THREE.BoxGeometry(76, 8, 8), wood); beam.position.set(x, Y(CE - 20), -DEPTH - 50); scene.add(beam);
    }
    for (const [x, c] of [[560, '#7ff0e0'], [900, '#b080ff'], [1250, '#7ff0e0']]) {
      const L = new THREE.PointLight(c, 800, 320, 1.3); L.position.set(x, Y(FL - 70), -80); scene.add(L);
      extraLights.push({ L, base: 800, kind: 'pulse' });
    }
  }

  // --- 5구역: 세계수 뿌리 핵 (x 128~832, 천장 y 1216, 바닥 y 1408), 세계수는 x 744 ---
  let core = null;
  {
    const RX0 = 128, RX1 = 832, CE = 1216, FL = 1408, TX = 744;
    backdrop(backdrop5Img, 1500, 850, (RX0 + RX1) / 2, FL - 300, -700, '#c8c098');
    const bark = lam(tex(8, 32, g => { px(g, 0, 0, 8, 32, '#4a3a2a'); px(g, 0, 0, 2, 32, '#6a5238'); px(g, 6, 0, 2, 32, '#2e2418'); for (let y = 0; y < 32; y += 5) px(g, 2, y, 4, 1, '#3a2c1e'); noise(g, 8, 32, ['#5a7a2a'], 10, 8); }, [1, 8]));
    // 굵은 뿌리: 천장에서 바닥으로 굽이침 (깊이 여러 겹)
    for (let k = 0; k < 14; k++) {
      const x0 = RX0 - 40 + k * 60 + hash(k, 141) * 30, z0 = -DEPTH - 20 - hash(k, 142) * 220;
      const pts = [];
      for (let j = 0; j <= 5; j++) {
        const t = j / 5;
        pts.push(new THREE.Vector3(x0 + Math.sin(t * 3 + k) * 40 + (TX - x0) * t * 0.35, Y(CE - 120 + t * (FL - CE + 140)), z0 + Math.cos(t * 2 + k) * 30));
      }
      const r = 6 + hash(k, 143) * 12;
      scene.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 40, r, 7), bark));
    }
    // 세계수 줄기와 핵
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(70, 110, 600, 12), bark);
    trunk.position.set(TX + 40, Y(FL - 300), -230); scene.add(trunk);
    const coreMat = new THREE.MeshBasicMaterial({ color: '#d8f080', fog: false });
    core = new THREE.Mesh(new THREE.SphereGeometry(26, 16, 12), coreMat);
    core.position.set(TX + 10, Y(FL - 70), -140); scene.add(core);
    const halo = new THREE.Mesh(new THREE.PlaneGeometry(160, 160), new THREE.MeshBasicMaterial({ map: tex(32, 32, g => { for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) { const d = Math.hypot(x - 16, y - 16) / 16; if (d < 1) { g.fillStyle = `rgba(230,250,150,${(1 - d) ** 2 * 0.6})`; g.fillRect(x, y, 1, 1); } } }), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
    halo.position.copy(core.position); halo.position.z += 2; scene.add(halo); core.userData.halo = halo;
    const coreLight = new THREE.PointLight('#e8f070', 2400, 520, 1.1); coreLight.position.set(TX, Y(FL - 80), -80); scene.add(coreLight);
    extraLights.push({ L: coreLight, base: 2400, kind: 'pulse' });
    // 뿌리에 삼켜진 도시 조각: 빌딩 덩어리, 차, 지하철 표지판
    const fac = facadeTex(1); fac.wrapS = fac.wrapT = THREE.RepeatWrapping;
    for (const [x, y, w, h, z, rot] of [[230, FL - 60, 70, 120, -200, 0.4], [470, CE + 40, 90, 70, -260, -0.6], [600, FL - 30, 60, 60, -150, 0.2]]) {
      const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, 40), lam(fac)); b.position.set(x, Y(y), z); b.rotation.z = rot; scene.add(b);
    }
    const car = new THREE.Mesh(new THREE.BoxGeometry(48, 24, 22), lam(carTex(1), { transparent: true, alphaTest: 0.5 }));
    car.position.set(360, Y(FL - 90), -170); car.rotation.z = -0.9; scene.add(car);
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(26, 20), lam(signTex())); sign.position.set(180, Y(CE + 60), -120); sign.rotation.z = 0.3; scene.add(sign);
    // 떠다니는 금빛 포자는 아래 포자 무리에서 함께 처리
  }

  // --- 조명 ---
  scene.add(new THREE.HemisphereLight('#a8cfc8', '#3a3628', 1.6));
  const sun = new THREE.DirectionalLight('#f6e2b4', 2.4);
  sun.position.set(220, 400, 300); scene.add(sun);
  const fill = new THREE.DirectionalLight('#7fb0a8', 0.5);
  fill.position.set(-200, 50, 400); scene.add(fill);

  // --- 떠다니는 포자 ---
  const N = 520, pos = new Float32Array(N * 3), base = [];
  for (let i = 0; i < N; i++) {
    // 앞 절반은 지하철·환기구, 나머지는 균류 동굴·뿌리 핵 (아래쪽)
    const x = i < 260 ? X0 + hash(i, 61) * (VX1 - X0) : 128 + hash(i, 61) * 1376;
    const y = i < 260 ? 160 + hash(i, 62) * 700 : 930 + hash(i, 62) * 480, z = -10 - hash(i, 63) * 200;
    base.push([x, y, z]); pos.set([x, Y(y), z], i * 3);
  }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const spores = new THREE.Points(pg, new THREE.PointsMaterial({ color: '#d8e8a0', size: 2, sizeAttenuation: false, transparent: true, opacity: 0.7 }));
  scene.add(spores);

  // 카메라 가운데가 어느 구역인지에 따라 안개·하늘·햇빛 색을 섞음 (지하철·환기구 → 도심 → 온실)
  const MOOD = [
    { x: -1e9, fog: '#16262a', bg: '#0e1a1c', sun: '#f6e2b4', hemi: 1.6 },
    { x: 46 * T, fog: '#3a2622', bg: '#2a1a18', sun: '#ffb48a', hemi: 1.2 },
    { x: 80 * T, fog: '#163028', bg: '#0e201c', sun: '#d8f0d8', hemi: 1.5 },
  ].map(m => ({ ...m, fogC: new THREE.Color(m.fog), bgC: new THREE.Color(m.bg), sunC: new THREE.Color(m.sun) }));
  const hemi = scene.children.find(o => o.isHemisphereLight);
  // 아래쪽 구역(균류 동굴 → 뿌리 핵)은 카메라 세로 위치로
  const DEEP = [
    { y: 56 * T, fog: '#1a1430', bg: '#0b0916', sun: '#a8a0ff', hemi: 0.9 },
    { y: 76 * T, fog: '#2a2210', bg: '#120d06', sun: '#ffe08a', hemi: 1.2 },
  ].map(m => ({ ...m, fogC: new THREE.Color(m.fog), bgC: new THREE.Color(m.bg), sunC: new THREE.Color(m.sun) }));
  function mood(cxw, cyw) {
    let a = MOOD[0], b = MOOD[0], k = 0;
    for (let i = 1; i < MOOD.length; i++) if (cxw > MOOD[i].x - 80) { a = MOOD[i - 1]; b = MOOD[i]; k = Math.min(1, (cxw - (MOOD[i].x - 80)) / 160); }
    scene.fog.color.copy(a.fogC).lerp(b.fogC, k);
    scene.background.copy(a.bgC).lerp(b.bgC, k);
    sun.color.copy(a.sunC).lerp(b.sunC, k);
    let hi = a.hemi + (b.hemi - a.hemi) * k;
    for (const d of DEEP) {
      const kd = Math.max(0, Math.min(1, (cyw - (d.y - 60)) / 120));
      if (kd <= 0) continue;
      scene.fog.color.lerp(d.fogC, kd); scene.background.lerp(d.bgC, kd); sun.color.lerp(d.sunC, kd); hi += (d.hemi - hi) * kd;
    }
    if (hemi) hemi.intensity = hi;
  }

  function render(cx, cy, t) {
    mood(cx + VW / 2, cy + VH / 2);
    extraLights.forEach(({ L, base, kind }, i) => {
      L.intensity = kind === 'flicker' ? base * (hash(Math.floor(t * 10), i) < 0.12 ? 0.25 : 1) : kind === 'pulse' ? base * (0.8 + 0.2 * Math.sin(t * 1.7 + i)) : base;
    });
    shroomCaps.forEach((c, i) => { c.material.emissiveIntensity = 0.45 + 0.3 * Math.sin(t * 1.5 + i); });
    if (core) { const k = 1 + 0.08 * Math.sin(t * 2.2); core.scale.setScalar(k); core.userData.halo.scale.setScalar(1 + 0.15 * Math.sin(t * 2.2)); }
    traps.forEach((m, i) => { m.rotation.z = Math.sin(t * 2 + i) * 0.06; m.scale.y = 1 + Math.sin(t * 3 + i * 1.7) * 0.03; });
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
      pos[i * 3 + 1] = i < 260 ? Y(((y - t * 6 * (0.5 + hash(i, 64))) % 700 + 700) % 700 + 160) : Y(((y - 930 - t * 5 * (0.5 + hash(i, 64))) % 480 + 480) % 480 + 930);
      pos[i * 3 + 2] = z;
    }
    pg.attributes.position.needsUpdate = true;
    renderer.render(scene, camera);
  }
  return { render, renderer };
}
