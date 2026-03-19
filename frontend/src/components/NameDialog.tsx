import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import AiOrb from "./AiOrb";

interface NameDialogProps {
  open: boolean;
  onSubmit: (name: string) => void;
}

const NameDialog = ({ open, onSubmit }: NameDialogProps) => {
  const [name, setName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) onSubmit(name.trim());
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/90 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="flex flex-col items-center gap-8 p-10"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          >
            <AiOrb size="lg" />
            <div className="text-center space-y-2">
              <h1 className="text-2xl font-light tracking-wider text-foreground">
                为你的 AI 助手<span className="glow-text text-primary font-medium">命名</span>
              </h1>
              <p className="text-sm text-muted-foreground">给你的语音助手一个独特的名字</p>
            </div>
            <form onSubmit={handleSubmit} className="flex flex-col items-center gap-4 w-72">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：Jarvis, Nova, Atlas..."
                className="w-full bg-secondary/50 border border-border rounded-lg px-4 py-3 text-center text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/60 focus:glow-border transition-all font-mono-code text-sm"
                autoFocus
              />
              <motion.button
                type="submit"
                disabled={!name.trim()}
                className="px-8 py-2.5 rounded-lg bg-primary/20 border border-primary/40 text-primary font-medium text-sm tracking-wider uppercase hover:bg-primary/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all glow-border"
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
              >
                激活
              </motion.button>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default NameDialog;
