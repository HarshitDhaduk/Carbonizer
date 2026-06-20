"use client";

import { useEffect, useMemo, useRef } from "react";
import { type ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { useBiomeStore } from "@/store/biome-store";
import {
  PLANET_RADIUS,
  atmosphereColor,
  fibonacciSphere,
  foliageColor,
  surfaceColor,
  treeTransform,
} from "./biome-helpers";
import { Forest } from "./Forest";
import { Turbines } from "./Turbines";

const BASE_TREES = 170;

/**
 * The Living Planet (docs/UI-UX-DESIGN.md §4). Health drives surface color,
 * atmosphere clarity and tree density; energy intensity drives the wind farm.
 * Tap the planet to plant a tree. Lerps smoothly toward targets — never cuts.
 */
export function Planet({
  healthOverride,
  autoRotate = false,
}: {
  healthOverride?: number;
  autoRotate?: boolean;
}) {
  const storeHealth = useBiomeStore((s) => s.health);
  const targetHealth = healthOverride ?? storeHealth;
  const energy = useBiomeStore((s) => s.categoryIntensity.energy);
  const plantedPoints = useBiomeStore((s) => s.plantedPoints);
  const plantTree = useBiomeStore((s) => s.plantTree);
  const celebrating = useBiomeStore((s) => s.celebrating);
  const endCelebration = useBiomeStore((s) => s.endCelebration);
  const invalidate = useThree((s) => s.invalidate);

  const groupRef = useRef<THREE.Group>(null);
  const planetMat = useRef<THREE.MeshStandardMaterial>(null);
  const atmoMat = useRef<THREE.MeshBasicMaterial>(null);
  const trunkRef = useRef<THREE.InstancedMesh>(null);
  const foliageRef = useRef<THREE.InstancedMesh>(null);

  const current = useRef(targetHealth);
  const celebrateT = useRef(0);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const basePoints = useMemo(() => fibonacciSphere(BASE_TREES), []);
  const plantedVecs = useMemo(
    () => plantedPoints.map((p) => new THREE.Vector3(p[0], p[1], p[2])),
    [plantedPoints],
  );

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

  const writeBaseForest = (health: number) => {
    const trunk = trunkRef.current;
    const foliage = foliageRef.current;
    if (!trunk || !foliage) return;
    const visible = Math.floor(
      BASE_TREES * THREE.MathUtils.clamp(health, 0.04, 1),
    );
    for (let i = 0; i < visible; i++) {
      const dir = basePoints[i]!;
      treeTransform(dummy, dir, i + dir.x, 0.16);
      trunk.setMatrixAt(i, dummy.matrix);
      foliage.setMatrixAt(i, dummy.matrix);
      foliage.setColorAt(i, foliageColor(i + dir.y));
    }
    trunk.count = visible;
    foliage.count = visible;
    trunk.instanceMatrix.needsUpdate = true;
    foliage.instanceMatrix.needsUpdate = true;
    if (foliage.instanceColor) foliage.instanceColor.needsUpdate = true;
  };

  // paint the initial forest once the instanced meshes exist
  useEffect(() => {
    writeBaseForest(current.current);
    invalidate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useFrame((_, delta) => {
    let dirty = false;

    // ease health → surface color, atmosphere, base forest density
    if (Math.abs(current.current - targetHealth) > 0.002) {
      current.current = THREE.MathUtils.damp(
        current.current,
        targetHealth,
        3,
        delta,
      );
      planetMat.current?.color.copy(surfaceColor(current.current));
      if (atmoMat.current) {
        atmoMat.current.color.copy(atmosphereColor(current.current));
        atmoMat.current.opacity = 0.12 + current.current * 0.22;
      }
      writeBaseForest(current.current);
      dirty = true;
    }

    // idle spin for the hero variant
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.12;
      dirty = true;
    }

    // celebration: a brief speed-up spin that settles back
    if (celebrating) {
      celebrateT.current += delta;
      if (groupRef.current) groupRef.current.rotation.y += delta * 1.4;
      dirty = true;
      if (celebrateT.current > 1.1) {
        celebrateT.current = 0;
        endCelebration();
      }
    }

    if (dirty) invalidate();
  });

  const onPlant = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    // local-space point (group may be rotated) → unit direction on the sphere
    const local = groupRef.current
      ? groupRef.current.worldToLocal(e.point.clone())
      : e.point.clone();
    const dir = local.normalize();
    plantTree([dir.x, dir.y, dir.z]);
    invalidate();
  };

  return (
    <group ref={groupRef}>
      {/* planet body */}
      <mesh
        onPointerDown={onPlant}
        onPointerOver={() => (document.body.style.cursor = "pointer")}
        onPointerOut={() => (document.body.style.cursor = "auto")}
      >
        <icosahedronGeometry args={[PLANET_RADIUS, 5]} />
        <meshStandardMaterial
          ref={planetMat}
          color={surfaceColor(targetHealth)}
          flatShading
          roughness={0.92}
          metalness={0}
        />
      </mesh>

      {/* atmosphere glow (inverted shell) */}
      <mesh scale={1.18}>
        <sphereGeometry args={[PLANET_RADIUS, 32, 32]} />
        <meshBasicMaterial
          ref={atmoMat}
          color={atmosphereColor(targetHealth)}
          transparent
          opacity={0.12 + targetHealth * 0.22}
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>

      {/* base forest (instanced trunk + foliage) */}
      <instancedMesh ref={trunkRef} args={[trunkGeo, undefined, BASE_TREES]}>
        <meshStandardMaterial color="#5b3f2a" roughness={0.9} flatShading />
      </instancedMesh>
      <instancedMesh
        ref={foliageRef}
        args={[foliageGeo, undefined, BASE_TREES]}
      >
        <meshStandardMaterial roughness={0.7} flatShading />
      </instancedMesh>

      {/* user-planted trees (pop in when added) */}
      <Forest points={plantedVecs} maxCount={140} scale={0.2} popNewest />

      {/* wind farm — density follows the energy category */}
      <Turbines intensity={energy} autoRotate={autoRotate || celebrating} />

      {/* orbital ring (brand motif) */}
      <mesh rotation={[Math.PI / 2.4, 0, 0]}>
        <torusGeometry args={[2.5, 0.01, 8, 96]} />
        <meshBasicMaterial color="#4fe08c" transparent opacity={0.3} />
      </mesh>
    </group>
  );
}
