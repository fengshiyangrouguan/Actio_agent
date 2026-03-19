import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { PhoneOff } from "lucide-react";

interface CallModeProps {
  isListening: boolean;
  level: number;
  onHangUp: () => void;
}

const barCount = 12;

const getLiveWaveHeight = (frameSeed: number, index: number, level: number, barCount: number) => {
  const archWeight = 0.45 + Math.sin((index / barCount) * Math.PI) * 0.9;
  const pulse = 0.75 + ((Math.cos(frameSeed * 0.18 + index * 0.85) + 1) / 2) * 1.1;
  const jitter = 0.7 + Math.random() * 1.1;

  return 6 + archWeight * pulse * jitter * level * 34;
};

const CallMode = ({ isListening, level, onHangUp }: CallModeProps) => {
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
    <motion.div
      className="flex w-full flex-col items-center justify-center py-2"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.28, ease: "easeOut" }}
    >
      {/* Waveform visualizer */}
      <div className="mb-8 flex h-16 w-full items-center justify-center gap-[3px]">
        {Array.from({ length: barCount }).map((_, i) => (
          <motion.div
            key={i}
            className="w-[3px] rounded-full bg-primary/70"
            animate={{ height: isListening ? getLiveWaveHeight(frameSeed, i, level, barCount) : 6 }}
            transition={{ duration: 0.08, ease: "linear" }}
            style={{ height: 6 }}
          />
        ))}
      </div>

      {/* Hang up button */}
      <motion.button
        onClick={onHangUp}
        className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive shadow-lg"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        initial={{ scale: 0.92 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 220, damping: 18, delay: 0.05 }}
      >
        <PhoneOff className="w-6 h-6 text-destructive-foreground" />
      </motion.button>
    </motion.div>
  );
};

export default CallMode;
