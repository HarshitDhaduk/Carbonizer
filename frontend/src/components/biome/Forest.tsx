"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { foliageColor, treeTransform } from "./biome-helpers";

/**
 * Instanced low-poly trees (trunk + foliage) growing out of the planet.
 * Geometry is pre-translated along +Y so a single per-instance matrix drives
 * both meshes. `popNewest` scales the most recently added tree in for a
 * satisfying "plant" beat (docs/UI-UX-DESIGN.md §4 — earned, not decorative).
 */
export function Forest({
  points,
  maxCount,
  scale = 0.18,
  popNewest = false,
}: {
  points: THREE.Vector3[];
  maxCount: number;
  scale?: number;
  popNewest?: boolean;
}) {
  const trunkRef = useRef<THREE.InstancedMesh>(null);
  const foliageRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const invalidate = useThree((s) => s.invalidate);

  // pop-in bookkeeping for the newest tree
  const grown = useRef(0);
  const popT = useRef(1);

  const trunkGeo = useMemo(() => {
    const g = new THREE.CylinderGeometry(0.05, 0.07, 0.45, 5);
    g.translate(0, 0.22, 0);
    return g;
  }, []);
  const foliageGeo = useMemo(() => {
    const g = new THREE.ConeGeometry(0.26, 0.62, 6);
    g.translate(0, 0.68, 0);
    return g;
  }, []);

  const write = (popScale: number) => {
    const trunk = trunkRef.current;
    const foliage = foliageRef.current;
    if (!trunk || !foliage) return;
    const n = Math.min(points.length, maxCount);
    for (let i = 0; i < n; i++) {
      const dir = points[i]!;
      const isNewest = popNewest && i === n - 1;
      treeTransform(dummy, dir, i + dir.x, scale * (isNewest ? popScale : 1));
      trunk.setMatrixAt(i, dummy.matrix);
      foliage.setMatrixAt(i, dummy.matrix);
      foliage.setColorAt(i, foliageColor(i + dir.y));
    }
    trunk.count = n;
    foliage.count = n;
    trunk.instanceMatrix.needsUpdate = true;
    foliage.instanceMatrix.needsUpdate = true;
    if (foliage.instanceColor) foliage.instanceColor.needsUpdate = true;
  };

  useFrame((_, delta) => {
    // a new tree appeared → animate it popping in
    if (popNewest && points.length > grown.current) {
      popT.current = Math.min(1, popT.current + delta / 0.4);
      // overshoot easing for a springy pop
      const e = 1 - Math.pow(1 - popT.current, 3);
      write(e * 1.08);
      invalidate();
      if (popT.current >= 1) {
        grown.current = points.length;
        popT.current = 1;
        write(1);
      }
    }
  });

  // (re)write whenever the point set changes (also covers first mount)
  useEffect(() => {
    if (popNewest && points.length > grown.current) {
      popT.current = 0; // trigger pop animation on next frame
      write(0.01);
      invalidate();
    } else {
      grown.current = points.length;
      write(1);
      invalidate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, scale, maxCount]);

  return (
    <group>
      <instancedMesh ref={trunkRef} args={[trunkGeo, undefined, maxCount]}>
        <meshStandardMaterial color="#5b3f2a" roughness={0.9} flatShading />
      </instancedMesh>
      <instancedMesh ref={foliageRef} args={[foliageGeo, undefined, maxCount]}>
        <meshStandardMaterial roughness={0.7} flatShading />
      </instancedMesh>
    </group>
  );
}
