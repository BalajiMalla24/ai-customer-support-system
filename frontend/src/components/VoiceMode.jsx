import { useEffect, useMemo, useRef, useState } from "react";

const getOrCreateSessionId = () => {
  let sid = localStorage.getItem("chat_session_id");
  if (!sid) {
    sid = Math.random().toString(36).slice(2, 10);
    localStorage.setItem("chat_session_id", sid);
  }
  return sid;
};

const VoiceMode = ({ forcedSessionId, orderId }) => {
  const sessionId = forcedSessionId || getOrCreateSessionId();
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [continuousMode, setContinuousMode] = useState(true);
  const [accuracyProfile, setAccuracyProfile] = useState("balanced");
  const [level, setLevel] = useState(0);
  const [turnReason, setTurnReason] = useState("idle");
  const [partialTranscript, setPartialTranscript] = useState("");
  const [earlyReply, setEarlyReply] = useState("");
  const [lastTranscript, setLastTranscript] = useState("");
  const [lastReply, setLastReply] = useState("");
  const [history, setHistory] = useState([]);

  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const rafRef = useRef(null);

  const silenceMsRef = useRef(0);
  const speechMsRef = useRef(0);
  const hasSpeechRef = useRef(false);
  const noiseFloorRef = useRef(0.008);

  const currentAudioRef = useRef(null);
  const voiceWsRef = useRef(null);
  const manualStopRef = useRef(false);

  const bars = useMemo(() => {
    const base = Math.max(6, Math.round(level * 28));
    return [0.45, 0.8, 1, 0.7, 0.5].map((m, idx) => ({
      id: idx,
      h: Math.max(8, Math.round(base * m)),
    }));
  }, [level]);

  const profileSettings = useMemo(() => {
    if (accuracyProfile === "strict") {
      return {
        label: "Strict Accuracy",
        thresholdScale: 2.8,
        minSpeechMs: 900,
        silenceEndMs: 900,
        noSpeechTimeoutMs: 3200,
      };
    }
    if (accuracyProfile === "quick") {
      return {
        label: "Quick Response",
        thresholdScale: 1.95,
        minSpeechMs: 450,
        silenceEndMs: 520,
        noSpeechTimeoutMs: 2200,
      };
    }
    return {
      label: "Balanced",
      thresholdScale: 2.2,
      minSpeechMs: 650,
      silenceEndMs: 700,
      noSpeechTimeoutMs: 2600,
    };
  }, [accuracyProfile]);

  const cleanupAnalyzer = () => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    try {
      sourceRef.current?.disconnect();
    } catch {
      // noop
    }
    sourceRef.current = null;
    analyserRef.current = null;

    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => undefined);
      audioCtxRef.current = null;
    }
  };

  const cleanupStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    cleanupAnalyzer();
  };

  const startMonitoring = () => {
    if (!analyserRef.current) return;
    const analyser = analyserRef.current;
    const data = new Uint8Array(analyser.fftSize);
    const frameMs = 45;

    const tick = () => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i += 1) {
        const n = (data[i] - 128) / 128;
        sum += n * n;
      }
      const rms = Math.sqrt(sum / data.length);
      setLevel(rms);

      // Adaptive VAD + semantic timing: fully auto end-of-turn on silence.
      if (isListening) {
        const speechThreshold = Math.max(
          noiseFloorRef.current * profileSettings.thresholdScale,
          0.015,
        );
        const isSpeechFrame = rms > speechThreshold;

        if (isSpeechFrame) {
          hasSpeechRef.current = true;
          speechMsRef.current += frameMs;
          silenceMsRef.current = 0;
          setTurnReason("speech-detected");
        } else {
          silenceMsRef.current += frameMs;
          noiseFloorRef.current = Math.min(
            0.02,
            noiseFloorRef.current * 0.94 + rms * 0.06,
          );
        }

        const shouldStopBySilence =
          hasSpeechRef.current &&
          speechMsRef.current > profileSettings.minSpeechMs &&
          silenceMsRef.current > profileSettings.silenceEndMs;
        const shouldStopByCap = speechMsRef.current > 15000;
        const shouldStopNoSpeech =
          !hasSpeechRef.current &&
          silenceMsRef.current > profileSettings.noSpeechTimeoutMs;

        if (shouldStopBySilence || shouldStopByCap || shouldStopNoSpeech) {
          stopCapture(
            shouldStopByCap
              ? "max-duration"
              : shouldStopNoSpeech
                ? "no-speech-timeout"
                : "silence-end-of-turn",
          );
          return;
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
  };

  const playReplyAudio = async (audioUrl) => {
    if (!audioUrl) return;
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }

    const audio = new Audio(`http://localhost:8000${audioUrl}`);
    currentAudioRef.current = audio;
    setIsSpeaking(true);

    audio.onended = () => {
      setIsSpeaking(false);
      if (continuousMode && !manualStopRef.current) {
        setTimeout(() => {
          if (!isListening && !isProcessing) {
            beginCapture();
          }
        }, 250);
      }
    };
    audio.onerror = () => setIsSpeaking(false);

    try {
      await audio.play();
    } catch {
      setIsSpeaking(false);
    }
  };

  const connectVoiceSocket = () =>
    new Promise((resolve, reject) => {
      const existing = voiceWsRef.current;
      if (existing && existing.readyState === WebSocket.OPEN) {
        resolve(existing);
        return;
      }

      const ws = new WebSocket(
        `ws://localhost:8000/ws/voice-stream/${sessionId}`,
      );
      voiceWsRef.current = ws;

      ws.onopen = () => resolve(ws);
      ws.onerror = () => reject(new Error("Voice stream socket failed"));
      ws.onclose = () => {
        if (voiceWsRef.current === ws) {
          voiceWsRef.current = null;
        }
      };

      ws.onmessage = async (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "processing") {
            setIsProcessing(true);
            return;
          }
          if (msg.type === "partial_transcript") {
            setPartialTranscript(msg.text || "");
            return;
          }
          if (msg.type === "early_reply") {
            setEarlyReply(msg.text || "");
            return;
          }
          if (msg.type === "turn_error") {
            setIsProcessing(false);
            setTurnReason(msg.trigger || "turn-error");
            setHistory((prev) =>
              [
                { role: "system", text: msg.error || "Voice turn failed." },
                ...prev,
              ].slice(0, 12),
            );
            return;
          }
          if (msg.type !== "turn_result") return;

          const data = msg.payload || {};
          setTurnReason(msg.trigger || "turn-complete");
          if (data.error) {
            setHistory((prev) =>
              [{ role: "system", text: data.error }, ...prev].slice(0, 12),
            );
            setIsProcessing(false);
            setLevel(0);
            if (continuousMode && !isListening && !manualStopRef.current) {
              setTimeout(() => beginCapture(), 200);
            }
            return;
          }

          setLastTranscript(data.transcribed_text || "");
          setLastReply(data.response_text || "");
          setPartialTranscript("");
          setEarlyReply("");
          setHistory((prev) =>
            [
              { role: "assistant", text: data.response_text || "" },
              { role: "user", text: data.transcribed_text || "" },
              ...prev,
            ].slice(0, 12),
          );

          setIsProcessing(false);
          setLevel(0);
          if (data.audio_url) {
            await playReplyAudio(data.audio_url);
          }
        } catch {
          // ignore malformed frames
        }
      };
    });

  const sendControl = (type) => {
    const ws = voiceWsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(
      JSON.stringify({
        type,
        order_id: orderId || null,
        accuracy_profile: accuracyProfile,
      }),
    );
  };

  const stopCapture = (reason = "manual") => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state === "recording") {
      setTurnReason(reason);
      rec.stop();
    }
  };

  const beginCapture = async () => {
    if (isListening || isProcessing) return;
    if (mediaRecorderRef.current?.state === "recording") return;
    manualStopRef.current = false;

    try {
      const ws = await connectVoiceSocket();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioCtx = new window.AudioContext();
      audioCtxRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 1024;
      analyserRef.current = analyser;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);
      sourceRef.current = source;

      const rec = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = rec;
      audioChunksRef.current = [];

      silenceMsRef.current = 0;
      speechMsRef.current = 0;
      hasSpeechRef.current = false;
      noiseFloorRef.current = 0.008;
      setPartialTranscript("");
      setEarlyReply("");

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);
          }
        }
      };

      rec.onstop = async () => {
        setIsListening(false);
        cleanupStream();

        const chunk = new Blob(audioChunksRef.current, { type: "audio/webm" });
        if (chunk.size < 3000) {
          if (continuousMode && !isProcessing && !manualStopRef.current) {
            setTimeout(() => beginCapture(), 200);
          }
          return;
        }

        if (manualStopRef.current) {
          setIsProcessing(false);
          return;
        }

        setIsProcessing(true);
        sendControl("end_turn");
      };

      sendControl("start_turn");
      rec.start(200);
      setIsListening(true);
      setTurnReason("listening");
      startMonitoring();
    } catch {
      setHistory((prev) => [
        {
          role: "system",
          text: "Microphone permission is required for Voice Mode.",
        },
        ...prev,
      ]);
    }
  };

  const stopVoiceMode = () => {
    manualStopRef.current = true;
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    } else {
      cleanupStream();
      setIsListening(false);
    }

    setIsListening(false);
    setIsProcessing(false);
    setTurnReason("manual-stop");

    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    if (voiceWsRef.current) {
      voiceWsRef.current.close();
      voiceWsRef.current = null;
    }
    setIsSpeaking(false);
  };

  useEffect(() => {
    return () => {
      stopVoiceMode();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="w-full h-full bg-white text-zinc-900 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-4 md:px-8 py-8 md:py-10 space-y-6">
        <div className="border border-zinc-200 rounded-2xl p-5 md:p-7">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">
                Voice Mode
              </h1>
              <p className="text-sm text-zinc-500 mt-1">
                VAD + turn detection + STT + agent + TTS (Kitten preferred)
              </p>
              {orderId && (
                <p className="text-xs text-blue-700 mt-2">
                  Order context active: {orderId}
                </p>
              )}
            </div>
            <div className="flex items-center gap-3">
              <label className="text-sm text-zinc-600">
                Accuracy
                <select
                  value={accuracyProfile}
                  onChange={(e) => setAccuracyProfile(e.target.value)}
                  className="ml-2 rounded-md border border-zinc-300 px-2 py-1 text-sm"
                >
                  <option value="strict">Strict</option>
                  <option value="balanced">Balanced</option>
                  <option value="quick">Quick</option>
                </select>
              </label>
              <label className="text-sm text-zinc-600 flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={continuousMode}
                  onChange={(e) => setContinuousMode(e.target.checked)}
                />
                Continuous
              </label>
              {!isListening ? (
                <button
                  onClick={beginCapture}
                  disabled={isProcessing}
                  className="px-4 py-2 rounded-lg bg-[#2563EB] text-white text-sm font-medium disabled:opacity-50"
                >
                  Start Auto Voice
                </button>
              ) : (
                <button
                  onClick={stopVoiceMode}
                  className="px-4 py-2 rounded-lg border border-zinc-300 text-sm font-medium"
                >
                  End Voice Mode
                </button>
              )}
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="border border-zinc-200 rounded-xl p-4">
              <p className="text-xs uppercase tracking-wide text-zinc-500">
                Live State
              </p>
              <div className="mt-3 flex items-center gap-2 text-sm">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${isListening ? "bg-emerald-500" : "bg-zinc-400"}`}
                />
                <span>{isListening ? "Listening" : "Idle"}</span>
              </div>
              <div className="mt-2 flex items-center gap-2 text-sm">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${isProcessing ? "bg-amber-500" : "bg-zinc-400"}`}
                />
                <span>{isProcessing ? "Processing" : "Ready"}</span>
              </div>
              <div className="mt-2 flex items-center gap-2 text-sm">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${isSpeaking ? "bg-[#2563EB]" : "bg-zinc-400"}`}
                />
                <span>{isSpeaking ? "Agent Speaking" : "Silent"}</span>
              </div>
              <p className="mt-3 text-xs text-zinc-500">
                Turn reason: {turnReason} (automatic stop enabled)
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                Mode: {profileSettings.label}
              </p>
            </div>

            <div className="border border-zinc-200 rounded-xl p-4">
              <p className="text-xs uppercase tracking-wide text-zinc-500">
                Voice Activity
              </p>
              <div className="mt-4 h-16 flex items-end gap-2">
                {bars.map((b) => (
                  <div
                    key={b.id}
                    className="w-3 rounded-t bg-[#2563EB] transition-all duration-100"
                    style={{ height: `${b.h}px`, opacity: 0.45 + level * 2 }}
                  />
                ))}
              </div>
              <p className="mt-3 text-xs text-zinc-500">
                Level: {(level * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="border border-zinc-200 rounded-xl p-4 min-h-[120px]">
            <p className="text-xs uppercase tracking-wide text-zinc-500">
              Streaming Partial Transcript
            </p>
            <p className="mt-3 text-sm leading-relaxed text-zinc-800 whitespace-pre-wrap">
              {partialTranscript || "Listening for speech..."}
            </p>
          </div>

          <div className="border border-zinc-200 rounded-xl p-4 min-h-[120px]">
            <p className="text-xs uppercase tracking-wide text-zinc-500">
              Early Agent Preview
            </p>
            <p className="mt-3 text-sm leading-relaxed text-zinc-800 whitespace-pre-wrap">
              {earlyReply || "Preview will appear while you speak."}
            </p>
          </div>

          <div className="border border-zinc-200 rounded-xl p-4 min-h-[160px]">
            <p className="text-xs uppercase tracking-wide text-zinc-500">
              Last Transcript
            </p>
            <p className="mt-3 text-sm leading-relaxed text-zinc-800 whitespace-pre-wrap">
              {lastTranscript || "No transcript yet."}
            </p>
          </div>

          <div className="border border-zinc-200 rounded-xl p-4 min-h-[160px]">
            <p className="text-xs uppercase tracking-wide text-zinc-500">
              Last Agent Reply
            </p>
            <p className="mt-3 text-sm leading-relaxed text-zinc-800 whitespace-pre-wrap">
              {lastReply || "No reply yet."}
            </p>
          </div>
        </div>

        <div className="border border-zinc-200 rounded-xl p-4">
          <p className="text-xs uppercase tracking-wide text-zinc-500">
            Recent Voice Turns
          </p>
          <div className="mt-3 space-y-2 max-h-[260px] overflow-y-auto pr-1">
            {history.length === 0 ? (
              <p className="text-sm text-zinc-500">No turns yet.</p>
            ) : (
              history.map((h, i) => (
                <div
                  key={i}
                  className={`text-sm rounded-lg px-3 py-2 ${h.role === "assistant" ? "bg-zinc-100" : h.role === "user" ? "bg-blue-50" : "bg-amber-50"}`}
                >
                  <span className="font-semibold mr-2 capitalize">
                    {h.role}:
                  </span>
                  <span>{h.text}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceMode;
