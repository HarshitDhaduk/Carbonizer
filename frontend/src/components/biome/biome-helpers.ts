import * as THREE from "three";

export const PLANET_RADIUS = 1.6;

/** Evenly distribute N points on a unit sphere (Fibonacci sphere). */
export function fibonacciSphere(count: number): THREE.Vector3[] {
  const points: THREE.Vector3[] = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const radius = Math.sqrt(1 - y * y);
    const theta = golden * i;
    points.push(
      new THREE.Vector3(Math.cos(theta) * radius, y, Math.sin(theta) * radius),
    );
  }
  return points;
}

/** Lerp planet surface color from arid (poor health) → lush green (good). */
export function surfaceColor(health: number): THREE.Color {
  const arid = new THREE.Color("#6b6149");
  const lush = new THREE.Color("#2f8a52");
  return arid.clone().lerp(lush, THREE.MathUtils.clamp(health, 0, 1));
}

/** Atmosphere rim color from smoggy brown → clean teal as health rises. */
export function atmosphereColor(health: number): THREE.Color {
  const smog = new THREE.Color("#b08d57");
  const clean = new THREE.Color("#2bd576");
  return smog.clone().lerp(clean, THREE.MathUtils.clamp(health, 0, 1));
}

/** Foliage color with slight per-tree variation for a natural look. */
export function foliageColor(seed: number): THREE.Color {
  const base = new THREE.Color("#2bd576");
  const alt = new THREE.Color("#1f9d57");
  return base.clone().lerp(alt, (Math.sin(seed * 12.9898) * 0.5 + 0.5) * 0.6);
}

/**
 * Build a transform for a tree sitting on the planet surface at `dir`
 * (a unit vector), oriented outward, with a deterministic scale jitter.
 */
export function treeTransform(
  dummy: THREE.Object3D,
  dir: THREE.Vector3,
  seed: number,
  scale: number,
): void {
  dummy.position.copy(dir).multiplyScalar(PLANET_RADIUS * 0.99);
  dummy.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  const jitter = 0.85 + (Math.sin(seed * 78.233) * 0.5 + 0.5) * 0.4;
  dummy.scale.setScalar(scale * jitter);
  dummy.updateMatrix();
}
