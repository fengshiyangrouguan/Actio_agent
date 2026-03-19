import { useState, useRef, useCallback } from "react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

interface UseSpeechRecognitionReturn {
  isListening: boolean;
  transcript: string;
  startListening: () => void;
  stopListening: () => void;
  clearTranscript: () => void;
  error: string | null;
}

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  const startListening = useCallback(() => {
    setError(null);
    setTranscript("")
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError("你的浏览器不支持语音识别");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "zh-CN";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (event) => {
      const result = event.results[0][0].transcript;
      setTranscript(result);
    };

    recognition.onerror = (event) => {
      setError(`语音识别错误: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, []);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const clearTranscript = useCallback(() => {
    setTranscript("");
  }, []);

  return { isListening, transcript, startListening, stopListening, clearTranscript, error };
}
