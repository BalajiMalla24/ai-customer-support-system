import { useEffect, useRef, useState } from "react";

const getOrCreateSessionId = () => {
  let sid = localStorage.getItem("chat_session_id");
  if (!sid) {
    sid = Math.random().toString(36).substring(7);
    localStorage.setItem("chat_session_id", sid);
  }
  return sid;
};

const ChatWindow = ({
  embedded = false,
  forcedSessionId,
  orderId,
  onClearOrderContext,
}) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const sessionId = forcedSessionId || getOrCreateSessionId();
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimeoutRef = useRef(null);
  const ws = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetch(`http://localhost:8000/api/history/${sessionId}`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.history && data.history.length > 0) {
          const loadedMsgs = data.history.map((m) => ({
            role: m.role === "user" ? "user" : "assistant",
            text: m.content,
          }));
          setMessages(loadedMsgs);
        } else {
          setMessages([
            {
              role: "assistant",
              text: orderId
                ? `Hello! I am your ShopEasy AI Assistant. I am now focused on order ${orderId}. How can I help?`
                : "Hello! I am your ShopEasy AI Assistant. How can I help you with your order today?",
            },
          ]);
        }
      })
      .catch((err) => {
        console.error("Failed to load history:", err);
        setMessages([
          {
            role: "assistant",
            text: orderId
              ? `Hello! I am your ShopEasy AI Assistant. I am now focused on order ${orderId}. How can I help?`
              : "Hello! I am your ShopEasy AI Assistant. How can I help you today?",
          },
        ]);
      });

    ws.current = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}`);
    ws.current.onopen = () => setIsConnected(true);
    ws.current.onclose = () => setIsConnected(false);
    ws.current.onerror = () => setIsConnected(false);
    ws.current.onmessage = (event) => {
      setIsThinking(false);
      setMessages((prev) => [...prev, { role: "assistant", text: event.data }]);
    };

    return () => {
      if (ws.current) ws.current.close();
    };
  }, [sessionId, orderId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTranscribing]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || !isConnected) return;
    setMessages((prev) => [...prev, { role: "user", text: input }]);
    if (orderId) {
      ws.current.send(
        JSON.stringify({
          type: "chat_message",
          text: input,
          order_id: orderId,
        }),
      );
    } else {
      ws.current.send(input);
    }
    setIsThinking(true);
    setInput("");
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm",
      });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      mediaRecorder.onstop = async () => {
        setIsRecording(false);
        setIsTranscribing(true);
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });
        const formData = new FormData();
        formData.append("audio", audioBlob, "voice.webm");
        formData.append("session_id", sessionId);
        if (orderId) {
          formData.append("order_id", orderId);
        }
        try {
          const res = await fetch(
            "http://localhost:8000/api/voice/transcribe",
            {
              method: "POST",
              body: formData,
            },
          );
          const data = await res.json();
          setIsTranscribing(false);
          if (data.transcribed_text) {
            setMessages((prev) => [
              ...prev,
              { role: "user", text: data.transcribed_text },
            ]);
            setMessages((prev) => [
              ...prev,
              { role: "assistant", text: data.response_text },
            ]);
            if (data.audio_url) {
              const bgAudio = new Audio(
                `http://localhost:8000${data.audio_url}`,
              );
              bgAudio
                .play()
                .catch((e) => console.error("Audio autoplay block:", e));
            }
          }
        } catch {
          setIsTranscribing(false);
          alert("Voice service currently unavailable.");
        }
        stream.getTracks().forEach((track) => track.stop());
      };
      mediaRecorder.start();
      setIsRecording(true);
      recordingTimeoutRef.current = setTimeout(() => {
        if (mediaRecorderRef.current?.state === "recording") stopRecording();
      }, 15000);
    } catch {
      alert("Microphone access is required.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
      clearTimeout(recordingTimeoutRef.current);
    }
  };

  const renderAssistantContent = (text) => {
    const lines = (text || "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (lines.length === 0) return text;

    const items = [];
    let listBuffer = [];
    let listType = null;

    const flushList = (keyBase) => {
      if (listBuffer.length === 0) return;
      if (listType === "ul") {
        items.push(
          <ul key={`${keyBase}-ul`} className="list-disc pl-5 space-y-1">
            {listBuffer.map((li, i) => (
              <li key={i}>{li}</li>
            ))}
          </ul>,
        );
      } else {
        items.push(
          <ol key={`${keyBase}-ol`} className="list-decimal pl-5 space-y-1">
            {listBuffer.map((li, i) => (
              <li key={i}>{li}</li>
            ))}
          </ol>,
        );
      }
      listBuffer = [];
      listType = null;
    };

    lines.forEach((line, idx) => {
      if (line.startsWith("- ")) {
        if (listType && listType !== "ul") flushList(`line-${idx}`);
        listType = "ul";
        listBuffer.push(line.slice(2));
        return;
      }

      if (/^\d+\.\s/.test(line)) {
        if (listType && listType !== "ol") flushList(`line-${idx}`);
        listType = "ol";
        listBuffer.push(line.replace(/^\d+\.\s/, ""));
        return;
      }

      flushList(`line-${idx}`);
      if (line.endsWith(":")) {
        items.push(
          <p key={`h-${idx}`} className="font-semibold text-zinc-800">
            {line}
          </p>,
        );
      } else {
        items.push(<p key={`p-${idx}`}>{line}</p>);
      }
    });

    flushList("last");
    return <div className="space-y-2">{items}</div>;
  };

  return (
    <div
      className={`w-full ${embedded ? "h-full" : "h-screen"} flex flex-col bg-white overflow-hidden`}
    >
      <div className="px-6 py-4 flex justify-between items-center border-b border-zinc-100 bg-white z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-zinc-900 flex items-center justify-center text-white">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" x2="12" y1="19" y2="22" />
            </svg>
          </div>
          <h2 className="text-[16px] font-semibold text-zinc-800 tracking-tight flex items-center gap-2">
            ShopEasy Agent
            <span
              className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-500" : "bg-rose-500"}`}
            ></span>
          </h2>
        </div>
        {orderId && (
          <button
            type="button"
            onClick={onClearOrderContext}
            className="text-xs px-3 py-1.5 rounded-full border border-blue-200 text-blue-700 bg-blue-50 hover:bg-blue-100"
          >
            Order: {orderId}
          </button>
        )}
      </div>

      <div
        className={`flex-1 overflow-y-auto ${embedded ? "px-3 py-4" : "px-4 md:px-0 py-8"} scroll-smooth`}
      >
        <div
          className={`${embedded ? "max-w-full" : "max-w-3xl"} mx-auto space-y-6`}
        >
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} w-full`}
            >
              <div className="flex gap-4 w-full">
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center shrink-0 border border-zinc-200">
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                      <line x1="12" x2="12" y1="19" y2="22" />
                    </svg>
                  </div>
                )}
                <div
                  className={`flex ${msg.role === "user" ? "justify-end w-full" : "justify-start w-full"}`}
                >
                  <div
                    className={
                      msg.role === "user"
                        ? "chat-bubble-user max-w-[80%] md:max-w-[70%]"
                        : "chat-bubble-ai max-w-full md:max-w-[85%]"
                    }
                  >
                    {msg.role === "assistant"
                      ? renderAssistantContent(msg.text)
                      : msg.text}
                  </div>
                </div>
              </div>
            </div>
          ))}
          {(isTranscribing || isThinking) && (
            <div className="flex justify-start w-full">
              <div className="flex gap-4 w-full">
                <div className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center shrink-0 border border-zinc-200">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
                  </svg>
                </div>
                <div className="chat-bubble-ai flex gap-2 items-center">
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div
        className={`px-4 ${embedded ? "py-3" : "py-4 md:py-6"} bg-white shrink-0`}
      >
        <div className={`${embedded ? "max-w-full" : "max-w-3xl"} mx-auto`}>
          <form
            onSubmit={handleSend}
            className="flex items-center gap-2 bg-zinc-100 p-1.5 md:p-2 rounded-3xl border border-zinc-200 focus-within:bg-white focus-within:ring-1 focus-within:ring-zinc-300 focus-within:border-zinc-300 transition-all"
          >
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              className={`w-10 h-10 md:w-11 md:h-11 rounded-full flex items-center justify-center transition-all ${
                isRecording
                  ? "bg-rose-500 text-white"
                  : "bg-transparent text-zinc-500 hover:bg-zinc-200"
              }`}
            >
              {isRecording ? (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
              ) : (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" x2="12" y1="19" y2="22" />
                </svg>
              )}
            </button>

            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isRecording}
              placeholder={
                isRecording
                  ? "Recording your voice..."
                  : "Message ShopEasy Agent..."
              }
              className="flex-1 px-3 bg-transparent border-none focus:outline-none focus:ring-0 text-[15px] sm:text-[16px] text-zinc-900 placeholder-zinc-500 font-normal"
            />

            <button
              type="submit"
              disabled={!isConnected || !input.trim() || isRecording}
              className="w-10 h-10 md:w-11 md:h-11 rounded-full bg-black text-white flex items-center justify-center hover:bg-zinc-800 transition-all disabled:opacity-30 disabled:hover:bg-black"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
          <div className="text-center mt-3 text-[12px] text-zinc-400 font-medium">
            ShopEasy AI Agent can make mistakes. Please verify important
            information.
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatWindow;
