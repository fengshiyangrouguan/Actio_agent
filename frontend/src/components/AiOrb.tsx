import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

interface AiOrbProps {
  isListening?: boolean;
  isSpeaking?: boolean;
  isTyping?: boolean;
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: { outer: 48, outerR: 20, innerR: 10, dot: 4, face: false },
  md: { outer: 140, outerR: 55, innerR: 28, dot: 6, face: true },
  lg: { outer: 200, outerR: 80, innerR: 40, dot: 7, face: true },
};

const AiOrb = ({ isListening = false, isSpeaking = false, isTyping = false, size = "md" }: AiOrbProps) => {
  const config = sizeMap[size];
  const active = isListening || isSpeaking || isTyping;
  const [showFace, setShowFace] = useState(false);

  // Periodically morph into robot face
  useEffect(() => {
    if (!config.face) return;

    // Show face on mount briefly
    const showForDuration = () => {
      setShowFace(true);
      return setTimeout(() => setShowFace(false), 2800);
    };

    // When active, show face more often
    if (active) {
      const t1 = showForDuration();
      const interval = setInterval(() => {
        showForDuration();
      }, 5000);
      return () => { clearTimeout(t1); clearInterval(interval); setShowFace(false); };
    } else {
      // When idle, show occasionally
      const interval = setInterval(() => {
        showForDuration();
      }, 10000);
      return () => { clearInterval(interval); setShowFace(false); };
    }
  }, [active, config.face]);

  const cx = config.outer / 2;
  const cy = config.outer / 2;
  const oR = config.outerR; // outer radius of ring
  const iR = config.innerR; // inner radius of ring
  const midR = (oR + iR) / 2;
  const ringWidth = oR - iR;
  // Dot orbits outside the ring
  const dotOrbitR = oR + config.dot + 4;

  return (
    <div className="relative flex items-center justify-center" style={{ width: config.outer, height: config.outer }}>
      {/* Orbiting dot 1 - outside the ring */}
      <motion.div
        className="absolute inset-0"
        animate={{ rotate: 360 }}
        transition={{ duration: active ? 2.5 : 7, repeat: Infinity, ease: "linear" }}
      >
        <motion.div
          className="absolute rounded-full bg-primary"
          style={{
            width: config.dot,
            height: config.dot,
            top: cy - dotOrbitR - config.dot / 2,
            left: cx - config.dot / 2,
            boxShadow: `0 0 10px hsl(var(--primary) / 0.9), 0 0 20px hsl(var(--primary) / 0.4)`,
          }}
          animate={active ? { scale: [1, 1.6, 1], opacity: [0.8, 1, 0.8] } : {}}
          transition={{ duration: 0.6, repeat: Infinity }}
        />
      </motion.div>

      {/* Orbiting dot 2 - opposite, only when active or lg */}
      {(active || size === "lg") && (
        <motion.div
          className="absolute inset-0"
          animate={{ rotate: -360 }}
          transition={{ duration: active ? 3.2 : 9, repeat: Infinity, ease: "linear" }}
        >
          <motion.div
            className="absolute rounded-full"
            style={{
              width: config.dot * 0.7,
              height: config.dot * 0.7,
              bottom: cy - dotOrbitR - config.dot * 0.35,
              left: cx - config.dot * 0.35,
              background: `hsl(var(--primary) / 0.7)`,
              boxShadow: `0 0 8px hsl(var(--primary) / 0.6)`,
            }}
            animate={{ opacity: [0.3, 0.9, 0.3] }}
            transition={{ duration: 1.8, repeat: Infinity }}
          />
        </motion.div>
      )}

      {/* Main SVG: flat ring + face */}
      <svg
        width={config.outer}
        height={config.outer}
        viewBox={`0 0 ${config.outer} ${config.outer}`}
        className="absolute"
        style={{ filter: `drop-shadow(0 0 15px hsl(var(--primary) / 0.5))` }}
      >
        <defs>
          {/* Outer ring gradient - radial for flat look */}
          <radialGradient id={`ring-fill-${size}`} cx="40%" cy="35%" r="65%">
            <stop offset="0%" stopColor="hsl(195 90% 65%)" stopOpacity="1" />
            <stop offset="50%" stopColor="hsl(var(--primary))" stopOpacity="0.9" />
            <stop offset="100%" stopColor="hsl(210 80% 40%)" stopOpacity="0.8" />
          </radialGradient>
          {/* Inner layer gradient */}
          <radialGradient id={`inner-fill-${size}`} cx="45%" cy="40%" r="60%">
            <stop offset="0%" stopColor="hsl(200 85% 55%)" stopOpacity="0.6" />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.3" />
          </radialGradient>
          <filter id={`glow-${size}`}>
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <AnimatePresence mode="wait">
          {showFace && config.face ? (
            /* ===== ROBOT FACE MODE ===== */
            <g key="face">
              <motion.g
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5 }}
              >
                {/* Robot head blob */}
                <motion.ellipse
                  cx={cx}
                  cy={cy}
                  rx={oR * 0.72}
                  ry={oR * 0.58}
                  fill={`url(#inner-fill-${size})`}
                  stroke="hsl(var(--primary))"
                  strokeWidth={ringWidth * 0.35}
                  filter={`url(#glow-${size})`}
                  animate={isSpeaking ? {
                    ry: [oR * 0.58, oR * 0.63, oR * 0.55, oR * 0.6, oR * 0.58],
                  } : {
                    ry: [oR * 0.58, oR * 0.6, oR * 0.58],
                  }}
                  transition={{ duration: isSpeaking ? 0.5 : 2.5, repeat: Infinity }}
                />

                {/* Left eye */}
                <motion.ellipse
                  cx={cx - oR * 0.25}
                  cy={cy - oR * 0.08}
                  rx={oR * 0.1}
                  ry={oR * 0.12}
                  fill="hsl(var(--primary))"
                  animate={{
                    ry: [oR * 0.12, oR * 0.12, oR * 0.03, oR * 0.12],
                  }}
                  transition={{ duration: 0.35, repeat: Infinity, repeatDelay: 3 }}
                />
                {/* Right eye */}
                <motion.ellipse
                  cx={cx + oR * 0.25}
                  cy={cy - oR * 0.08}
                  rx={oR * 0.1}
                  ry={oR * 0.12}
                  fill="hsl(var(--primary))"
                  animate={{
                    ry: [oR * 0.12, oR * 0.12, oR * 0.03, oR * 0.12],
                  }}
                  transition={{ duration: 0.35, repeat: Infinity, repeatDelay: 3, delay: 0.05 }}
                />

                {/* Mouth */}
                <motion.ellipse
                  cx={cx}
                  cy={cy + oR * 0.22}
                  rx={oR * 0.12}
                  ry={oR * 0.06}
                  fill="hsl(var(--primary) / 0.8)"
                  animate={isSpeaking ? {
                    ry: [oR * 0.06, oR * 0.14, oR * 0.04, oR * 0.11, oR * 0.06],
                    rx: [oR * 0.12, oR * 0.09, oR * 0.14, oR * 0.1, oR * 0.12],
                  } : isListening ? {
                    ry: [oR * 0.06, oR * 0.03, oR * 0.06],
                  } : {
                    ry: [oR * 0.06, oR * 0.05, oR * 0.06],
                  }}
                  transition={{ duration: isSpeaking ? 0.4 : 2, repeat: Infinity }}
                />

                {/* Antenna nubs */}
                <motion.circle
                  cx={cx - oR * 0.32}
                  cy={cy - oR * 0.5}
                  r={oR * 0.05}
                  fill="hsl(var(--primary) / 0.9)"
                  animate={{ scale: [1, 1.4, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
                <motion.circle
                  cx={cx + oR * 0.32}
                  cy={cy - oR * 0.5}
                  r={oR * 0.05}
                  fill="hsl(var(--primary) / 0.9)"
                  animate={{ scale: [1, 1.4, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 1, repeat: Infinity, delay: 0.5 }}
                />
              </motion.g>
            </g>
          ) : (
            /* ===== FLAT RING MODE ===== */
            <g key="ring">
              <motion.g
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5 }}
              >
                {/* Flat donut ring - outer filled annulus using path */}
                <motion.path
                  d={annulusPath(cx, cy, oR, iR)}
                  fill={`url(#ring-fill-${size})`}
                  filter={`url(#glow-${size})`}
                  animate={active ? {
                    opacity: [0.85, 1, 0.85],
                  } : {
                    opacity: [0.75, 0.9, 0.75],
                  }}
                  transition={{ duration: active ? 1.2 : 3, repeat: Infinity, ease: "easeInOut" }}
                />

                {/* Inner color layer 1 - slightly inside */}
                <motion.circle
                  cx={cx}
                  cy={cy}
                  r={iR + ringWidth * 0.15}
                  fill="none"
                  stroke="hsl(200 85% 60% / 0.4)"
                  strokeWidth={ringWidth * 0.2}
                  animate={active ? {
                    r: [iR + ringWidth * 0.15, iR + ringWidth * 0.25, iR + ringWidth * 0.15],
                    opacity: [0.4, 0.7, 0.4],
                  } : {
                    opacity: [0.3, 0.5, 0.3],
                  }}
                  transition={{ duration: active ? 1 : 3, repeat: Infinity, ease: "easeInOut" }}
                />

                {/* Inner color layer 2 - highlight ring */}
                <motion.circle
                  cx={cx}
                  cy={cy}
                  r={midR + ringWidth * 0.1}
                  fill="none"
                  stroke="hsl(190 90% 70% / 0.25)"
                  strokeWidth={ringWidth * 0.12}
                  animate={active ? {
                    opacity: [0.2, 0.5, 0.2],
                    strokeWidth: [ringWidth * 0.12, ringWidth * 0.2, ringWidth * 0.12],
                  } : {
                    opacity: [0.15, 0.3, 0.15],
                  }}
                  transition={{ duration: active ? 0.8 : 4, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
                />

                {/* Center breathing dot */}
                <motion.circle
                  cx={cx}
                  cy={cy}
                  r={iR * 0.15}
                  fill="hsl(var(--primary) / 0.5)"
                  animate={active ? {
                    r: [iR * 0.15, iR * 0.3, iR * 0.1, iR * 0.25, iR * 0.15],
                    opacity: [0.5, 1, 0.3, 0.8, 0.5],
                  } : {
                    r: [iR * 0.15, iR * 0.2, iR * 0.15],
                    opacity: [0.3, 0.6, 0.3],
                  }}
                  transition={{ duration: active ? 0.7 : 3, repeat: Infinity }}
                />
              </motion.g>
            </g>
          )}
        </AnimatePresence>
      </svg>
    </div>
  );
};

/** SVG path for a flat donut (annulus) shape */
function annulusPath(cx: number, cy: number, outerR: number, innerR: number): string {
  return [
    // Outer circle clockwise
    `M ${cx - outerR} ${cy}`,
    `A ${outerR} ${outerR} 0 1 1 ${cx + outerR} ${cy}`,
    `A ${outerR} ${outerR} 0 1 1 ${cx - outerR} ${cy}`,
    `Z`,
    // Inner circle counter-clockwise (hole)
    `M ${cx - innerR} ${cy}`,
    `A ${innerR} ${innerR} 0 1 0 ${cx + innerR} ${cy}`,
    `A ${innerR} ${innerR} 0 1 0 ${cx - innerR} ${cy}`,
    `Z`,
  ].join(" ");
}

export default AiOrb;
