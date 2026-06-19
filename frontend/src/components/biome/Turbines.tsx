"use client";

import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { PLANET_RADIUS } from "./biome-helpers";

/**
 * A small wind farm near the planet's pole. The number of turbines tracks the
 * energy category intensity (more clean infrastructure as energy improves);
 * blades spin only while the scene is already animating (Green-AI budget §4.4).
 */
export function Turbines({
  intensity,
  autoRotate,
}: {
  intensity: number;
  autoRotate: boolean;
}) {
  const bladesRef = useRef<(THREE.Group | null)[]>([]);
  const invalidate = useThree((s) => s.invalidate);

  // up to 4 turbines, placed on the upper hemisphere
  const turbines = useMemo(() => {
    const count = 1 + Math.round(intensity * 3);
    const out: { pos: THREE.Vector3; quat: THREE.Quaternion }[] = [];
    for (let i = 0; i < count; i++) {
      const theta = (i / 4) * Math.PI * 0.8 - 0.3;
      const phi = 0.6 + (i % 2) * 0.25;
      const dir = new THREE.Vector3(
        Math.sin(phi) * Math.cos(theta),
        Math.cos(phi),
        Math.sin(phi) * Math.sin(theta),
      ).normalize();
      const quat = new THREE.Quaternion().setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        dir,
      );
      out.push({ pos: dir.multiplyScalar(PLANET_RADIUS * 0.99), quat });
    }
    return out;
  }, [intensity]);

  useFrame((_, delta) => {
    if (!autoRotate) return;
    for (const g of bladesRef.current) {
      if (g) g.rotation.y += delta * 2.2;
    }
    invalidate();
  });

  return (
    <>
      {turbines.map((t, i) => (
        <group key={i} position={t.pos} quaternion={t.quat} scale={0.16}>
          {/* mast */}
          <mesh position={[0, 0.6, 0]}>
            <cylinderGeometry args={[0.05, 0.08, 1.2, 6]} />
            <meshStandardMaterial color="#dfe9e3" roughness={0.6} />
          </mesh>
          {/* nacelle + blades spin around the local Y, tilted to face out */}
          <group
            position={[0, 1.2, 0]}
            rotation={[Math.PI / 2, 0, 0]}
            ref={(el) => {
              bladesRef.current[i] = el;
            }}
          >
            {[0, 1, 2].map((b) => (
              <mesh key={b} rotation={[0, 0, (b * Math.PI * 2) / 3]}>
                <boxGeometry args={[0.06, 0.7, 0.02]} />
                <meshStandardMaterial color="#ffffff" roughness={0.5} />
              </mesh>
            ))}
          </group>
        </group>
      ))}
    </>
  );
}
