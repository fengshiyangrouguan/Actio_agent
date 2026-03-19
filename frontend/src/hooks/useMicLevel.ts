import { useCallback, useRef, useState } from "react";

declare global {
  interface Window {
    webkitAudioContext?: typeof AudioContext;
  }
}

interface UseMicLevelReturn {
  level: number;
  startMeter: () => Promise<void>;
  stopMeter: () => void;
}

export function useMicLevel(): UseMicLevelReturn {
  const [level, setLevel] = useState(0);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const frameRef = useRef<number | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);

  const stopMeter = useCallback(() => {
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }

    sourceRef.current?.disconnect();
    analyserRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    audioContextRef.current?.close().catch(() => undefined);

    sourceRef.current = null;
    analyserRef.current = null;
    streamRef.current = null;
    audioContextRef.current = null;
    dataArrayRef.current = null;
    setLevel(0);
  }, []);

  const startMeter = useCallback(async () => {
    if (streamRef.current) {
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContextCtor();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);

      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.85;

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      source.connect(analyser);

      streamRef.current = stream;
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      sourceRef.current = source;
      dataArrayRef.current = dataArray;

      const updateLevel = () => {
        if (!analyserRef.current || !dataArrayRef.current) {
          return;
        }

        analyserRef.current.getByteTimeDomainData(dataArrayRef.current);

        let sum = 0;
        for (const value of dataArrayRef.current) {
          const normalized = (value - 128) / 128;
          sum += normalized * normalized;
        }

        const rms = Math.sqrt(sum / dataArrayRef.current.length);
        const boosted = Math.min(1, rms * 4.5);
        setLevel((prev) => prev * 0.35 + boosted * 0.65);
        frameRef.current = requestAnimationFrame(updateLevel);
      };

      updateLevel();
    } catch {
      stopMeter();
    }
  }, [stopMeter]);

  return { level, startMeter, stopMeter };
}
