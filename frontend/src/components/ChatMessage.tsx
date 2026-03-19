import { motion } from "framer-motion";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  assistantName: string;
}

const ChatMessage = ({ role, content, assistantName }: ChatMessageProps) => {
  const isUser = role === "user";

  return (
    <motion.div
      className="flex flex-col items-center w-full"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <p className="text-[10px] font-medium mb-1.5 tracking-wider uppercase text-muted-foreground">
        {isUser ? "你" : assistantName}
      </p>
      <div
        className={`w-full rounded-2xl px-5 py-3.5 text-sm leading-relaxed backdrop-blur-md ${
          isUser
            ? "bg-secondary/30 border border-border/30 text-foreground"
            : "bg-primary/5 border border-primary/10 text-foreground"
        }`}
      >
        {content}
      </div>
    </motion.div>
  );
};

export default ChatMessage;
