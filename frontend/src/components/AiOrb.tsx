import { motion } from "framer-motion";

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
  const cx = config.outer / 2;
  const cy = config.outer / 2;
  const oR = config.outerR;
  const iR = config.innerR;
  const midR = (oR + iR) / 2;
  const ringWidth = oR - iR;
  const dotOrbitR = oR + config.dot + 4;

  return (
    <div className="relative flex items-center justify-center" style={{ width: config.outer, height: config.outer }}>
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

      <svg
        width={config.outer}
        height={config.outer}
        viewBox={`0 0 ${config.outer} ${config.outer}`}
        className="absolute"
        style={{ filter: `drop-shadow(0 0 15px hsl(var(--primary) / 0.5))` }}
      >
        <defs>
          <radialGradient id={`ring-fill-${size}`} cx="40%" cy="35%" r="65%">
            <stop offset="0%" stopColor="hsl(195 90% 65%)" stopOpacity="1" />
            <stop offset="50%" stopColor="hsl(var(--primary))" stopOpacity="0.9" />
            <stop offset="100%" stopColor="hsl(210 80% 40%)" stopOpacity="0.8" />
          </radialGradient>
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

        {/* Robot face definition is retained intentionally, but not rendered in the live UI. */}
        <g display="none" aria-hidden="true">
          <ellipse
            cx={cx}
            cy={cy}
            rx={oR * 0.72}
            ry={oR * 0.58}
            fill={`url(#inner-fill-${size})`}
            stroke="hsl(var(--primary))"
            strokeWidth={ringWidth * 0.35}
            filter={`url(#glow-${size})`}
          />
          <ellipse
            cx={cx - oR * 0.25}
            cy={cy - oR * 0.08}
            rx={oR * 0.1}
            ry={oR * 0.12}
            fill="hsl(var(--primary))"
          />
          <ellipse
            cx={cx + oR * 0.25}
            cy={cy - oR * 0.08}
            rx={oR * 0.1}
            ry={oR * 0.12}
            fill="hsl(var(--primary))"
          />
          <ellipse
            cx={cx}
            cy={cy + oR * 0.22}
            rx={oR * 0.12}
            ry={oR * 0.06}
            fill="hsl(var(--primary) / 0.8)"
          />
          <circle
            cx={cx - oR * 0.32}
            cy={cy - oR * 0.5}
            r={oR * 0.05}
            fill="hsl(var(--primary) / 0.9)"
          />
          <circle
            cx={cx + oR * 0.32}
            cy={cy - oR * 0.5}
            r={oR * 0.05}
            fill="hsl(var(--primary) / 0.9)"
          />
        </g>

        <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
          <motion.path
            d={annulusPath(cx, cy, oR, iR)}
            fill={`url(#ring-fill-${size})`}
            filter={`url(#glow-${size})`}
            animate={
              isSpeaking
                ? {
                    opacity: [0.82, 1, 0.86, 1, 0.82],
                    scale: [1, 1.025, 0.992, 1.02, 1],
                  }
                : active
                  ? {
                      opacity: [0.85, 1, 0.85],
                      scale: [1, 1.01, 1],
                    }
                  : {
                      opacity: [0.75, 0.9, 0.75],
                      scale: [1, 1.003, 1],
                    }
            }
            transition={{
              duration: isSpeaking ? 0.55 : active ? 1.2 : 3,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={{ transformOrigin: "50% 50%" }}
          />

          <motion.circle
            cx={cx}
            cy={cy}
            r={iR + ringWidth * 0.15}
            fill="none"
            stroke="hsl(200 85% 60% / 0.4)"
            strokeWidth={ringWidth * 0.2}
            animate={
              isSpeaking
                ? {
                    r: [
                      iR + ringWidth * 0.16,
                      iR + ringWidth * 0.34,
                      iR + ringWidth * 0.12,
                      iR + ringWidth * 0.28,
                      iR + ringWidth * 0.16,
                    ],
                    opacity: [0.35, 0.85, 0.25, 0.72, 0.35],
                  }
                : active
                  ? {
                      r: [iR + ringWidth * 0.15, iR + ringWidth * 0.25, iR + ringWidth * 0.15],
                      opacity: [0.4, 0.7, 0.4],
                    }
                  : {
                      opacity: [0.3, 0.5, 0.3],
                    }
            }
            transition={{
              duration: isSpeaking ? 0.6 : active ? 1 : 3,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />

          <motion.circle
            cx={cx}
            cy={cy}
            r={midR + ringWidth * 0.1}
            fill="none"
            stroke="hsl(190 90% 70% / 0.25)"
            strokeWidth={ringWidth * 0.12}
            animate={
              isSpeaking
                ? {
                    opacity: [0.2, 0.65, 0.18, 0.55, 0.2],
                    strokeWidth: [ringWidth * 0.1, ringWidth * 0.26, ringWidth * 0.1],
                  }
                : active
                  ? {
                      opacity: [0.2, 0.5, 0.2],
                      strokeWidth: [ringWidth * 0.12, ringWidth * 0.2, ringWidth * 0.12],
                    }
                  : {
                      opacity: [0.15, 0.3, 0.15],
                    }
            }
            transition={{
              duration: isSpeaking ? 0.48 : active ? 0.8 : 4,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.3,
            }}
          />

          <motion.circle
            cx={cx}
            cy={cy}
            r={iR * 0.15}
            fill="hsl(var(--primary) / 0.5)"
            animate={
              isSpeaking
                ? {
                    r: [iR * 0.14, iR * 0.34, iR * 0.09, iR * 0.3, iR * 0.14],
                    opacity: [0.45, 1, 0.28, 0.88, 0.45],
                  }
                : active
                  ? {
                      r: [iR * 0.15, iR * 0.3, iR * 0.1, iR * 0.25, iR * 0.15],
                      opacity: [0.5, 1, 0.3, 0.8, 0.5],
                    }
                  : {
                      r: [iR * 0.15, iR * 0.2, iR * 0.15],
                      opacity: [0.3, 0.6, 0.3],
                    }
            }
            transition={{ duration: isSpeaking ? 0.45 : active ? 0.7 : 3, repeat: Infinity }}
          />

          <motion.circle
            cx={cx}
            cy={cy}
            r={iR * 0.6}
            fill="none"
            stroke="hsl(var(--primary) / 0.22)"
            strokeWidth={ringWidth * 0.08}
            animate={
              isSpeaking
                ? {
                    r: [iR * 0.45, iR * 0.95, iR * 1.15],
                    opacity: [0, 0.6, 0],
                  }
                : {
                    opacity: [0, 0, 0],
                  }
            }
            transition={{ duration: 0.8, repeat: Infinity, ease: "easeOut" }}
          />

          <motion.circle
            cx={cx}
            cy={cy}
            r={iR * 0.75}
            fill="none"
            stroke="hsl(195 90% 70% / 0.18)"
            strokeWidth={ringWidth * 0.06}
            animate={
              isSpeaking
                ? {
                    r: [iR * 0.55, iR * 1.08, iR * 1.28],
                    opacity: [0, 0.45, 0],
                  }
                : {
                    opacity: [0, 0, 0],
                  }
            }
            transition={{ duration: 0.8, repeat: Infinity, ease: "easeOut", delay: 0.18 }}
          />
        </motion.g>
      </svg>
    </div>
  );
};

function annulusPath(cx: number, cy: number, outerR: number, innerR: number): string {
  return [
    `M ${cx - outerR} ${cy}`,
    `A ${outerR} ${outerR} 0 1 1 ${cx + outerR} ${cy}`,
    `A ${outerR} ${outerR} 0 1 1 ${cx - outerR} ${cy}`,
    `Z`,
    `M ${cx - innerR} ${cy}`,
    `A ${innerR} ${innerR} 0 1 0 ${cx + innerR} ${cy}`,
    `A ${innerR} ${innerR} 0 1 0 ${cx - innerR} ${cy}`,
    `Z`,
  ].join(" ");
}

export default AiOrb;
