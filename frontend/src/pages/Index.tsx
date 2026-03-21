import { useState, useEffect, useRef, useCallback } from "react";
import AiOrb from "@/components/AiOrb";
import MicButton from "@/components/MicButton";
import { useMicLevel } from "@/hooks/useMicLevel";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { Send, Phone } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import CallMode from "@/components/CallMode";

interface Exchange {
  id: string;
  user: string;
  assistant: string;
  assistantRevision: number;
}

interface BotProfile {
  bot_name: string;
  bot_personality: string;
}

const CALL_START_THRESHOLD = 0.075;
const CALL_START_HOLD_MS = 20;
const CALL_STOP_THRESHOLD = 0.045;
const CALL_STOP_SILENCE_MS = 850;
const TYPEWRITER_SPEED_MS = 28;
const SESSION_STORAGE_KEY = "ai-session-id";

const createSessionId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const getStoredSessionId = () => {
  const existing = localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;

  const created = createSessionId();
  localStorage.setItem(SESSION_STORAGE_KEY, created);
  return created;
};

const Index = () => {
  const [assistantName, setAssistantName] = useState<string | null>(null);
  const [typedAssistantName, setTypedAssistantName] = useState("");
  const [activeExchange, setActiveExchange] = useState<Exchange | null>(null);
  const [typedAssistantText, setTypedAssistantText] = useState("");
  const [textInput, setTextInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTypingReply, setIsTypingReply] = useState(false);
  const [isCallMode, setIsCallMode] = useState(false);
  const [isBootstrappingProfile, setIsBootstrappingProfile] = useState(true);
  const sessionIdRef = useRef<string>(getStoredSessionId());
  const callStartTimerRef = useRef<number | null>(null);
  const callSilenceTimerRef = useRef<number | null>(null);
  const {
    isListening,
    transcript,
    startListening,
    stopListening,
    clearTranscript,
    error,
  } = useSpeechRecognition();
  const { level, startMeter, stopMeter } = useMicLevel();
  const previousAssistantNameRef = useRef<string | null>(null);

  const updateAssistantExchange = useCallback((exchangeId: string, message: string) => {
    setActiveExchange((prev) =>
      prev && prev.id === exchangeId
        ? {
            ...prev,
            assistant: message,
            assistantRevision: prev.assistantRevision + 1,
          }
        : prev
    );
  }, []);

  const clearCallTimers = useCallback(() => {
    if (callStartTimerRef.current !== null) {
      window.clearTimeout(callStartTimerRef.current);
      callStartTimerRef.current = null;
    }

    if (callSilenceTimerRef.current !== null) {
      window.clearTimeout(callSilenceTimerRef.current);
      callSilenceTimerRef.current = null;
    }
  }, []);

  const syncAssistantProfile = useCallback((profile?: Partial<BotProfile>) => {
    const botName = profile?.bot_name?.trim();
    if (!botName) {
      return;
    }

    localStorage.setItem("ai-assistant-name", botName);
    setAssistantName(botName);
  }, []);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await fetch("/api/profile");
        if (!response.ok) {
          throw new Error("profile request failed");
        }

        const data: { mode: "setup" | "main"; bot_profile: BotProfile } = await response.json();
        syncAssistantProfile(data.bot_profile);
      } catch {
      } finally {
        setIsBootstrappingProfile(false);
      }
    };

    void loadProfile();
  }, [syncAssistantProfile]);

  useEffect(() => {
    if (!assistantName) {
      setTypedAssistantName("");
      previousAssistantNameRef.current = null;
      return;
    }

    if (previousAssistantNameRef.current === assistantName) {
      setTypedAssistantName(assistantName);
      return;
    }

    previousAssistantNameRef.current = assistantName;
    setTypedAssistantName("");

    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setTypedAssistantName(assistantName.slice(0, index));
      if (index >= assistantName.length) {
        window.clearInterval(timer);
      }
    }, 60);

    return () => {
      window.clearInterval(timer);
    };
  }, [assistantName]);

  useEffect(() => {
    if (!activeExchange?.assistant) {
      setTypedAssistantText("");
      setIsTypingReply(false);
      return;
    }

    setTypedAssistantText("");
    setIsTypingReply(true);
    let index = 0;
    const assistantText = activeExchange.assistant;
    const timer = window.setInterval(() => {
      index += 1;
      setTypedAssistantText(assistantText.slice(0, index));
      if (index >= assistantText.length) {
        window.clearInterval(timer);
        setIsTypingReply(false);
      }
    }, TYPEWRITER_SPEED_MS);

    return () => {
      window.clearInterval(timer);
      setIsTypingReply(false);
    };
  }, [activeExchange?.assistant, activeExchange?.assistantRevision, activeExchange?.id]);

  const isAssistantBusy = isProcessing || isTypingReply;

  useEffect(() => {
    if (transcript && !isListening) {
      sendMessage(transcript);
      clearTranscript();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transcript, isListening]);

  useEffect(() => {
    if (!isCallMode || isAssistantBusy) {
      clearCallTimers();
      return;
    }

    if (!isListening) {
      if (callSilenceTimerRef.current !== null) {
        window.clearTimeout(callSilenceTimerRef.current);
        callSilenceTimerRef.current = null;
      }

      if (level >= CALL_START_THRESHOLD) {
        if (callStartTimerRef.current === null) {
          callStartTimerRef.current = window.setTimeout(() => {
            callStartTimerRef.current = null;
            clearTranscript();
            startListening();
          }, CALL_START_HOLD_MS);
        }
      } else if (callStartTimerRef.current !== null) {
        window.clearTimeout(callStartTimerRef.current);
        callStartTimerRef.current = null;
      }

      return;
    }

    if (callStartTimerRef.current !== null) {
      window.clearTimeout(callStartTimerRef.current);
      callStartTimerRef.current = null;
    }

    if (level <= CALL_STOP_THRESHOLD) {
      if (callSilenceTimerRef.current === null) {
        callSilenceTimerRef.current = window.setTimeout(() => {
          callSilenceTimerRef.current = null;
          stopListening();
        }, CALL_STOP_SILENCE_MS);
      }
    } else if (callSilenceTimerRef.current !== null) {
      window.clearTimeout(callSilenceTimerRef.current);
      callSilenceTimerRef.current = null;
    }
  }, [
    clearCallTimers,
    clearTranscript,
    isAssistantBusy,
    isCallMode,
    isListening,
    level,
    startListening,
    stopListening,
  ]);

  useEffect(() => {
    if (isCallMode || isListening) {
      void startMeter();
      return;
    }

    stopMeter();
  }, [isCallMode, isListening, startMeter, stopMeter]);

  useEffect(() => {
    return () => {
      clearCallTimers();
      stopMeter();
    };
  }, [clearCallTimers, stopMeter]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isAssistantBusy) return;

    const exchangeId = Date.now().toString();
    setActiveExchange({
      id: exchangeId,
      user: content,
      assistant: "",
      assistantRevision: 0,
    });
    setTypedAssistantText("");
    setTextInput("");
    setIsProcessing(true);
    setIsTypingReply(false);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: content,
          session_id: sessionIdRef.current,
        }),
      });

      if (!response.ok) {
        throw new Error("request failed");
      }

      const data: {
        task_id: string;
        session_id: string;
        reply: string;
        mode: "setup" | "main";
        bot_profile: BotProfile;
      } = await response.json();
      sessionIdRef.current = data.session_id;
      localStorage.setItem(SESSION_STORAGE_KEY, data.session_id);
      syncAssistantProfile(data.bot_profile);

      updateAssistantExchange(exchangeId, data.reply);

      const eventSource = new EventSource(`/api/chat/${data.task_id}/events`);
      eventSource.onmessage = (event) => {
        const payload = JSON.parse(event.data) as {
          kind: "ack" | "plan" | "tool" | "done" | "error";
          message: string;
          metadata?: {
            mode?: "setup" | "main";
            bot_profile?: BotProfile;
          };
        };

        syncAssistantProfile(payload.metadata?.bot_profile);

        if (payload.kind === "ack" || payload.kind === "plan" || payload.kind === "tool") {
          updateAssistantExchange(exchangeId, payload.message);
        }

        if (payload.kind === "done") {
          updateAssistantExchange(exchangeId, payload.message);
          eventSource.close();
          setIsProcessing(false);
        }

        if (payload.kind === "error") {
          updateAssistantExchange(exchangeId, payload.message);
          eventSource.close();
          setIsProcessing(false);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setIsProcessing(false);
      };
    } catch {
      setActiveExchange((prev) =>
        prev && prev.id === exchangeId
          ? {
              ...prev,
              assistant: "连接后端失败，请检查 FastAPI 服务是否已启动。",
            }
          : prev
      );
      setIsProcessing(false);
    }
  }, [isAssistantBusy, syncAssistantProfile, updateAssistantExchange]);

  const handleMicClick = () => {
    if (isAssistantBusy) return;
    if (isListening) stopListening();
    else startListening();
  };

  const handleStartCall = () => {
    if (isAssistantBusy) return;
    clearTranscript();
    setIsCallMode(true);
  };

  const handleHangUp = () => {
    clearCallTimers();
    if (isListening) stopListening();
    setIsCallMode(false);
    clearTranscript();
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (textInput.trim()) sendMessage(textInput.trim());
  };

  const hasExchange = Boolean(activeExchange);
  const hasAssistantReply = Boolean(activeExchange?.assistant);
  const setupHint = assistantName ? `对 ${assistantName} 说点什么...` : "先告诉我你希望我叫什么，以及我的性格倾向";

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-background">
      {!isBootstrappingProfile && (
        <div className="flex h-full flex-col items-center">
          <motion.div
            className="z-10 flex flex-col items-center"
            animate={{
              paddingTop: hasExchange ? "13vh" : "18vh",
              paddingBottom: hasExchange ? 20 : 0,
            }}
            transition={{ type: "spring", stiffness: 120, damping: 20 }}
          >
            <AiOrb
              size="lg"
              isListening={isListening}
              isSpeaking={isTypingReply}
              isTyping={textInput.length > 0}
            />
            <motion.div className="mt-3 text-center" animate={{ opacity: 1 }}>
              {assistantName ? (
                <h1 className="terminal-ai-text text-sm font-semibold uppercase tracking-[0.35em] text-primary">
                  {typedAssistantName}
                  {typedAssistantName.length < assistantName.length ? (
                    <span className="terminal-caret">_</span>
                  ) : null}
                </h1>
              ) : null}
              <p className="mt-1 text-xs text-muted-foreground">
                {isCallMode
                  ? isListening
                    ? "正在聆听..."
                    : isAssistantBusy
                      ? "思考中..."
                      : "等待语音..."
                  : isListening
                    ? "正在聆听..."
                    : isAssistantBusy
                      ? "思考中..."
                      : assistantName
                        ? "在线"
                        : "等待初始化"}
              </p>
            </motion.div>
          </motion.div>

          <div className="relative flex w-full flex-1 items-center justify-center overflow-hidden px-6">
            {hasExchange && (
              <div className="pointer-events-none absolute left-0 right-0 top-0 z-10 h-28 bg-gradient-to-b from-background via-background/92 to-transparent" />
            )}
            <AnimatePresence mode="wait">
              {!activeExchange ? (
                <motion.p
                  key="empty-state"
                  className="max-w-xl text-center text-sm text-muted-foreground"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.6 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.24 }}
                >
                  {assistantName
                    ? "点击麦克风或输入文字开始对话"
                    : "先完成初始化，告诉我名字和你希望的性格风格"}
                </motion.p>
              ) : (
                <motion.div
                  key={activeExchange.id}
                  className="relative flex h-full w-full max-w-4xl items-center justify-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <motion.div
                    className="flex w-full max-w-3xl flex-col items-center gap-8 px-6"
                    animate={{
                      y: hasAssistantReply ? -56 : 0,
                    }}
                    transition={{ duration: 0.22, ease: "easeOut" }}
                  >
                    <motion.p
                      className="terminal-user-text text-center"
                      animate={{
                        opacity: hasAssistantReply ? 0.6 : 1,
                        scale: hasAssistantReply ? 0.88 : 1,
                      }}
                      transition={{ duration: 0.22, ease: "easeOut" }}
                    >
                      {activeExchange.user}
                    </motion.p>

                    <AnimatePresence>
                      {hasAssistantReply ? (
                          <motion.div
                            key={`${activeExchange.id}-assistant-${activeExchange.assistantRevision}`}
                            className="flex w-full justify-center"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8, filter: "blur(4px)" }}
                            transition={{ duration: 0.22, ease: "easeOut" }}
                          >
                          <p className="terminal-ai-text text-center">
                            {typedAssistantText}
                            {typedAssistantText.length < activeExchange.assistant.length && (
                              <span className="terminal-caret">_</span>
                            )}
                          </p>
                        </motion.div>
                      ) : (
                        isProcessing && (
                          <motion.div
                            key={`${activeExchange.id}-thinking`}
                            className="flex items-center justify-center gap-2"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                          >
                            {[0, 1, 2].map((i) => (
                              <motion.div
                                key={i}
                                className="h-1.5 w-1.5 rounded-full bg-primary"
                                animate={{ opacity: [0.2, 1, 0.2] }}
                                transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
                              />
                            ))}
                          </motion.div>
                        )
                      )}
                    </AnimatePresence>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {error && (
            <div className="px-6 py-2 text-center text-xs text-destructive">{error}</div>
          )}

          <div className="w-full overflow-hidden border-t border-border/30 px-4 py-4">
            <div className="mx-auto min-h-[96px] max-w-xl">
              <AnimatePresence mode="wait" initial={false}>
                {!isCallMode ? (
                  <motion.div
                    key="chat-input"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 24 }}
                    transition={{ duration: 0.28, ease: "easeOut" }}
                  >
                    <div className="flex items-center gap-2 sm:gap-3">
                      <div className="flex-shrink-0">
                        <MicButton
                          isListening={isListening}
                          isProcessing={isAssistantBusy}
                          level={level}
                          onClick={handleMicClick}
                        />
                      </div>
                      <form onSubmit={handleTextSubmit} className="flex min-w-0 flex-1 gap-2">
                        <input
                          type="text"
                          value={textInput}
                          onChange={(e) => setTextInput(e.target.value)}
                          placeholder={setupHint}
                          className="min-w-0 flex-1 rounded-full border border-border/50 bg-secondary/30 px-4 py-2.5 text-sm text-foreground backdrop-blur-sm transition-all placeholder:text-muted-foreground focus:border-primary/40 focus:outline-none sm:px-5 sm:py-3"
                          disabled={isAssistantBusy}
                        />
                        <motion.button
                          type="submit"
                          disabled={!textInput.trim() || isAssistantBusy}
                          className="flex-shrink-0 rounded-full border border-primary/25 bg-primary/15 p-2.5 text-primary transition-all hover:bg-primary/25 disabled:cursor-not-allowed disabled:opacity-30 sm:p-3"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <Send className="h-4 w-4" />
                        </motion.button>
                      </form>
                      <motion.button
                        onClick={handleStartCall}
                        disabled={isAssistantBusy}
                        className="flex-shrink-0 rounded-full border border-green-500/25 bg-green-500/15 p-2.5 text-green-400 transition-all hover:bg-green-500/25 disabled:cursor-not-allowed disabled:opacity-30 sm:p-3"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        <Phone className="h-4 w-4" />
                      </motion.button>
                    </div>
                  </motion.div>
                ) : (
                  <CallMode key="call-mode" isListening={isListening} level={level} onHangUp={handleHangUp} />
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Index;
