import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Mic, Square, Loader2 } from "lucide-react";

interface MicButtonProps {
  isListening: boolean;
  isProcessing: boolean;
  level: number;
  onClick: () => void;
}

const getLiveBarHeight = (frameSeed: number, index: number, side: "left" | "right", level: number, barCount: number) => {
  const weight = side === "left" ? 0.35 + (barCount - index) * 0.12 : 0.4 + (index + 1) * 0.11;
  const pulse = 0.7 + ((Math.sin(frameSeed * 0.22 + index * 1.3 + (side === "left" ? 0.2 : 0.7)) + 1) / 2) * 0.9;
  const jitter = 0.75 + Math.random() * 0.85;

  return 4 + weight * pulse * jitter * level * 24;
};

const MicButton = ({ isListening, isProcessing, level, onClick }: MicButtonProps) => {
  const barCount = 5;
  const [frameSeed, setFrameSeed] = useState(0);

  useEffect(() => {
    if (!isListening) {
      setFrameSeed(0);
      return;
    }

    let frameId = 0;

    const updateFrame = () => {
      setFrameSeed((prev) => prev + 1);
      frameId = requestAnimationFrame(updateFrame);
    };

    frameId = requestAnimationFrame(updateFrame);

    return () => cancelAnimationFrame(frameId);
  }, [isListening]);

  return (
    <div className="relative flex items-center">
      {/* Waveform bars - left side */}
      {isListening && (
        <div className="flex items-center gap-[2px] mr-1.5">
          {Array.from({ length: barCount }).map((_, i) => (
            <motion.div
              key={`l-${i}`}
              className="w-[2px] rounded-full bg-primary/70"
              animate={{ height: getLiveBarHeight(frameSeed, i, "left", level, barCount) }}
              transition={{ duration: 0.08, ease: "linear" }}
              style={{ height: 4 }}
            />
          ))}
        </div>
      )}

      <motion.button
        onClick={onClick}
        disabled={isProcessing}
        className={`relative w-12 h-12 rounded-full flex items-center justify-center transition-all flex-shrink-0 ${
          isListening
            ? "bg-primary/20 border border-primary/50 glow-box"
            : "bg-secondary/50 border border-border/50 hover:border-primary/30"
        } disabled:opacity-50 disabled:cursor-not-allowed`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        {isProcessing ? (
          <Loader2 className="w-5 h-5 text-primary animate-spin" />
        ) : isListening ? (
          <Square className="w-4 h-4 text-primary fill-primary" />
        ) : (
          <Mic className="w-5 h-5 text-muted-foreground" />
        )}

        {isListening && (
          <motion.div
            className="absolute inset-0 rounded-full border border-primary/40"
            animate={{ scale: [1, 1.5], opacity: [0.4, 0] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          />
        )}
      </motion.button>

      {/* Waveform bars - right side */}
      {isListening && (
        <div className="flex items-center gap-[2px] ml-1.5">
          {Array.from({ length: barCount }).map((_, i) => (
            <motion.div
              key={`r-${i}`}
              className="w-[2px] rounded-full bg-primary/70"
              animate={{ height: getLiveBarHeight(frameSeed, i, "right", level, barCount) }}
              transition={{ duration: 0.08, ease: "linear" }}
              style={{ height: 4 }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default MicButton;
