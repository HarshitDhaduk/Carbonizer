"use client";

import { Canvas } from "@react-three/fiber";
import {
  AdaptiveDpr,
  OrbitControls,
  PerformanceMonitor,
  Sparkles,
  Stars,
} from "@react-three/drei";
import { useState } from "react";
import { Planet } from "./Planet";

/**
 * R3F canvas host for the biome.
 *
 * - "dashboard": frameloop="demand" — the GPU is idle unless something is
 *   animating or the user interacts (docs/UI-UX-DESIGN.md §4.4 Green-AI budget).
 * - "hero": frameloop="always" + idle auto-rotate for the landing showpiece;
 *   the wrapper unmounts it when scrolled offscreen so it never burns cycles.
 */
export default function BiomeScene({
  variant = "dashboard",
  healthOverride,
}: {
  variant?: "dashboard" | "hero";
  healthOverride?: number;
}) {
  const hero = variant === "hero";
  const [dpr, setDpr] = useState(hero ? 1.75 : 1.5);

  return (
    <Canvas
      frameloop={hero ? "always" : "demand"}
      dpr={dpr}
      shadows={false}
      gl={{ antialias: true, powerPreference: "high-performance", alpha: true }}
      camera={{ position: [0, 1.1, hero ? 5.6 : 5.2], fov: 42 }}
      style={{ touchAction: "pan-y" }}
    >
      <PerformanceMonitor
        onDecline={() => setDpr(1)}
        onIncline={() => setDpr(hero ? 1.75 : 1.5)}
      />
      <AdaptiveDpr pixelated={false} />

      <ambientLight intensity={0.5} />
      <directionalLight position={[4, 6, 3]} intensity={1.5} color="#eafff2" />
      <directionalLight
        position={[-5, -2, -4]}
        intensity={0.35}
        color="#2bd576"
      />

      {/* deep-space backdrop + ambient fireflies that read as life */}
      <Stars
        radius={60}
        depth={40}
        count={hero ? 1800 : 900}
        factor={3}
        saturation={0}
        fade
        speed={0}
      />
      <Sparkles
        count={hero ? 60 : 36}
        scale={6}
        size={2.4}
        speed={hero ? 0.4 : 0}
        opacity={0.5}
        color="#9bf6c4"
      />

      <Planet
        autoRotate={hero}
        {...(healthOverride !== undefined ? { healthOverride } : {})}
      />

      {/* the planet spins itself (Planet autoRotate); controls only orbit camera */}
      <OrbitControls
        makeDefault
        enableDamping
        enablePan={false}
        enableZoom={!hero}
        minDistance={3.6}
        maxDistance={7}
        minPolarAngle={Math.PI / 4}
        maxPolarAngle={Math.PI / 1.6}
        rotateSpeed={0.6}
      />
    </Canvas>
  );
}
