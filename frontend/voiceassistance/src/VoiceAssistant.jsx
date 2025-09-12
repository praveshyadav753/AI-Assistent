// VoiceAssistant.js - Simplified React Frontend (No Start/Stop)
import React, { useState, useEffect, useRef, useCallback } from "react";
import { Mic, Volume2, Wifi, WifiOff } from "lucide-react";

const VoiceAssistant = () => {
  // State management (removed start/stop related states)
  const [isAwake, setIsAwake] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showWakeupPopup, setShowWakeupPopup] = useState(false);
  const [userQuery, setUserQuery] = useState("");
  const [response, setResponse] = useState("");
  const [wavePhase, setWavePhase] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [systemMessage, setSystemMessage] = useState("Voice Assistant Ready");
  const [error, setError] = useState("");

  // WebSocket connection
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  // API base URL
  const API_BASE_URL = "http://localhost:8000";
  const WS_URL = "ws://localhost:8000/ws";

  const soundMap = {
    wake_word_detected: "/sounds/wakeup.mp3",
    listening_started: "/sounds/listening.mp3",
  };

  // Continuous wave animation
  useEffect(() => {
    const interval = setInterval(() => {
      setWavePhase((prev) => prev + 0.05);
    }, 30);
    return () => clearInterval(interval);
  }, []);

  // WebSocket connection and message handling
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    console.log("Attempting to connect to WebSocket...");
    setConnectionStatus("connecting");

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected successfully");
      setConnectionStatus("connected");
      setError("");
      reconnectAttemptsRef.current = 0;

      // Send ping to test connection
      ws.send(JSON.stringify({ type: "ping" }));
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log("Received message:", message);

        // Handle existing assistant state updates
        handleWebSocketMessage(message);

        // Map backend events to sound files
        const soundMap = {
          direct_wakeup: "../public/wakeup2.mp3",
          listening_started: "/wakeup2.mp3",
          response_generated: "/response.mp3",
          // Add more events as needed
        };

        // Play sound if this event has a mapping
        const soundFile = soundMap[message.type];
        if (soundFile) {
          const audio = new Audio(soundFile);
          audio.play().catch((err) => console.error("Audio play failed:", err));
        }
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };

    ws.onclose = (event) => {
      console.log("WebSocket disconnected:", event.code, event.reason);
      setConnectionStatus("disconnected");

      // Attempt to reconnect if not intentionally closed
      if (
        event.code !== 1000 &&
        reconnectAttemptsRef.current < maxReconnectAttempts
      ) {
        const delay = Math.min(
          1000 * Math.pow(2, reconnectAttemptsRef.current),
          10000
        );
        console.log(
          `Reconnecting in ${delay}ms (attempt ${
            reconnectAttemptsRef.current + 1
          })`
        );

        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current++;
          connectWebSocket();
        }, delay);
      } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
        setError(
          "Failed to connect to voice assistant backend. Please check if the server is running."
        );
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setConnectionStatus("error");
      setError("WebSocket connection error");
    };
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = (message) => {
    const { type, data, assistant_state } = message;

    // Update assistant state from backend
    if (assistant_state) {
      setIsAwake(assistant_state.is_awake || false);
      setIsListening(assistant_state.is_listening || false);
      setIsSpeaking(assistant_state.is_speaking || false);
      setUserQuery(assistant_state.current_command || "");
      setResponse(assistant_state.current_response || "");
      setSystemMessage(assistant_state.message || "Voice Assistant Ready");
    }

    // Handle specific message types
    switch (type) {
      case "initial_state":
        console.log("Received initial state from backend");
        break;

      case "wake_word_detected":
        setShowWakeupPopup(true);
        setTimeout(() => {
          setShowWakeupPopup(false);
        }, 2000);
        break;

      case "command_received":
        setShowWakeupPopup(false);
        break;

      case "response_generated":
        // Response will be handled by assistant_state
        break;

      case "status_update":
        // Status updates handled by assistant_state
        break;

      case "error":
        setError(data?.message || "An error occurred");
        break;

      case "pong":
        // Ping response received
        break;

      default:
        console.log("Unknown message type:", type);
    }
  };

  // Initialize WebSocket connection
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounting");
      }
    };
  }, [connectWebSocket]);

  // Simulate wake word
  onclick; // Trigger direct wakeup via backend
  const simulateWakeWord = async () => {
    if (connectionStatus !== "connected") {
      setError(
        "Voice assistant is not connected. Please check if the server is running."
      );
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/start-wakeup/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const data = await response.json();
      if (data.status === "success") {
        console.log("Direct wakeup triggered via backend");
        setShowWakeupPopup(true);
        setTimeout(() => setShowWakeupPopup(false), 2000);
      } else {
        setError(data.message || "Failed to trigger wakeup");
      }
    } catch (err) {
      console.error("Error triggering direct wakeup:", err);
      setError("Failed to trigger wakeup");
    }
  };

  // Generate circular waveform
  const generateCircularWaveform = () => {
    const waves = [];
    const numberOfWaves = 150;
    const radius = 120;
    const centerX = 150;
    const centerY = 150;

    for (let i = 0; i < numberOfWaves; i++) {
      const angle = (i / numberOfWaves) * Math.PI * 2;

      // Create dynamic wave effect based on state
      let baseIntensity = 0.4; // Default intensity when connected
      if (isAwake) baseIntensity = 0.8;
      else if (isListening) baseIntensity = 0.6;
      else if (isSpeaking) baseIntensity = 1.0;
      else if (connectionStatus !== "connected") baseIntensity = 0.2;

      const waveIntensity =
        baseIntensity + Math.sin(wavePhase * 3 + angle * 8) * 0.4;
      const waveRadius = radius + waveIntensity * 30;

      const x = centerX + Math.cos(angle) * waveRadius;
      const y = centerY + Math.sin(angle) * waveRadius;

      // Dynamic colors based on state
      let hue = 200; // Default light blue
      if (isAwake) hue = 180; // Cyan
      else if (isSpeaking) hue = 280; // Purple
      else if (connectionStatus !== "connected") hue = 0; // Red

      hue += angle * 30;
      const opacity = 0.6 + waveIntensity * 0.4;

      waves.push(
        <circle
          key={i}
          cx={x}
          cy={y}
          r="2"
          fill={`hsla(${hue}, 70%, 60%, ${opacity})`}
          className="transition-all duration-75"
        />
      );
    }
    return waves;
  };

  // Generate inner particles
  const generateInnerParticles = () => {
    const particles = [];
    const numberOfParticles = 30;
    const centerX = 150;
    const centerY = 150;

    for (let i = 0; i < numberOfParticles; i++) {
      const angle = (i / numberOfParticles) * Math.PI * 2;
      const baseRadius = 40 + Math.sin(wavePhase + angle * 2) * 15;
      const x = centerX + Math.cos(angle + wavePhase * 0.5) * baseRadius;
      const y = centerY + Math.sin(angle + wavePhase * 0.5) * baseRadius;

      let opacity = 0.5; // Default when connected
      if (isAwake) opacity = 0.8;
      else if (isListening) opacity = 0.6;
      else if (isSpeaking) opacity = 0.9;
      else if (connectionStatus !== "connected") opacity = 0.2;

      particles.push(
        <circle
          key={i}
          cx={x}
          cy={y}
          r="1.5"
          fill={`rgba(255, 255, 255, ${opacity})`}
          className="transition-all duration-100"
        />
      );
    }
    return particles;
  };

  // Get status text and colors
  const getStatusInfo = () => {
    if (connectionStatus === "disconnected") {
      return {
        title: "Voice Assistant",
        subtitle: "Connecting to backend...",
        titleClass: "text-red-300",
        subtitleClass: "text-red-200/80",
      };
    }

    if (connectionStatus === "error") {
      return {
        title: "Connection Error",
        subtitle: "Failed to connect to backend",
        titleClass: "text-red-300",
        subtitleClass: "text-red-200/80",
      };
    }

    if (isAwake && isListening) {
      return {
        title: "How can I help you?",
        subtitle: "Listening for your command...",
        titleClass: "text-cyan-300 scale-105",
        subtitleClass: "text-cyan-200",
      };
    }

    if (isSpeaking) {
      return {
        title: "Nesty",
        subtitle: "Speaking...",
        titleClass: "text-purple-300",
        subtitleClass: "text-purple-200",
      };
    }

    return {
      title: "Hey Nesty",
      subtitle: 'Say "Hey Nesty" or click to simulate',
      titleClass: "text-blue-300",
      subtitleClass: "text-blue-200/80",
    };
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-950 via-purple-900 to-blue-950 flex flex-col items-center justify-center p-8 relative overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 opacity-20">
        <div
          className="absolute inset-0 bg-gradient-to-r from-cyan-600/30 via-purple-600/30 to-pink-600/30"
          style={{
            transform: `rotate(${wavePhase * 10}deg) scale(1.2)`,
            filter: "blur(80px)",
          }}
        />
      </div>

      {/* Status Bar */}
      <div className="absolute top-6 left-0 right-0 flex justify-between items-center px-8 z-10">
        <div className="flex items-center gap-4">
          {/* Connection Status */}
          <div className="flex items-center gap-2 text-white/90 text-sm font-medium">
            {connectionStatus === "connected" ? (
              <Wifi className="w-4 h-4 text-emerald-400" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-400" />
            )}
            <span
              className={`${
                connectionStatus === "connected"
                  ? "text-emerald-400"
                  : "text-red-400"
              }`}
            >
              {connectionStatus === "connected" ? "Connected" : "Disconnected"}
            </span>
          </div>

          {/* Assistant Status */}
          <div className="text-white/90 text-sm font-medium">
            <span className="flex items-center gap-3">
              <div
                className={`w-3 h-3 rounded-full ${
                  connectionStatus === "connected"
                    ? "bg-emerald-400 animate-pulse shadow-lg shadow-emerald-400/50"
                    : "bg-red-400 shadow-lg shadow-red-400/50"
                }`}
              />
              {connectionStatus === "connected"
                ? "Voice Assistant Active"
                : "Voice Assistant Offline"}
            </span>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-20">
          <div className="bg-red-500/20 backdrop-blur-xl border border-red-500/30 rounded-lg px-4 py-2 text-red-200 text-sm max-w-md text-center">
            {error}
            <button
              onClick={() => setError("")}
              className="ml-2 text-red-300 hover:text-red-100"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Main Circular Waveform Visualization */}
      <div className="relative z-10" onClick={simulateWakeWord}>
        <svg width="300" height="300" className="cursor-pointer">
          {/* Background circle */}
          <circle
            cx="150"
            cy="150"
            r="140"
            fill="none"
            stroke="rgba(255, 255, 255, 0.1)"
            strokeWidth="1"
          />

          {/* Circular waveform */}
          {generateCircularWaveform()}

          {/* Inner particles */}
          {generateInnerParticles()}

          {/* Center circle */}
          <circle
            cx="150"
            cy="150"
            r="35"
            fill="url(#centerGradient)"
            className="drop-shadow-2xl"
          />

          {/* Gradient definitions */}
          <defs>
            <radialGradient id="centerGradient" cx="0.3" cy="0.3">
              <stop
                offset="0%"
                stopColor={
                  isAwake
                    ? "rgba(34, 211, 238, 0.9)"
                    : isSpeaking
                    ? "rgba(168, 85, 247, 0.9)"
                    : connectionStatus === "connected"
                    ? "rgba(59, 130, 246, 0.8)"
                    : "rgba(239, 68, 68, 0.8)"
                }
              />
              <stop
                offset="100%"
                stopColor={
                  isAwake
                    ? "rgba(59, 130, 246, 0.7)"
                    : isSpeaking
                    ? "rgba(236, 72, 153, 0.7)"
                    : connectionStatus === "connected"
                    ? "rgba(30, 41, 59, 0.9)"
                    : "rgba(127, 29, 29, 0.9)"
                }
              />
            </radialGradient>
          </defs>
        </svg>

        {/* Icon in center */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {isSpeaking ? (
            <Volume2 className="w-8 h-8 text-white drop-shadow-lg" />
          ) : (
            <Mic className="w-8 h-8 text-white drop-shadow-lg" />
          )}
        </div>
      </div>

      {/* Status Text */}
      <div className="mt-12 text-center z-10">
        <h1
          className={`text-3xl font-light text-white mb-3 transition-all duration-500 ${statusInfo.titleClass}`}
          style={{ textShadow: "0 0 20px rgba(255, 255, 255, 0.5)" }}
        >
          {statusInfo.title}
        </h1>

        <p
          className={`text-sm font-medium transition-all duration-500 ${statusInfo.subtitleClass}`}
        >
          {systemMessage || statusInfo.subtitle}
        </p>
      </div>

      {/* Query and Response Display */}
      {userQuery && (
        <div className="mt-8 p-6 bg-white/10 backdrop-blur-xl rounded-3xl max-w-md border border-white/20 shadow-xl animate-fade-in">
          <p className="text-cyan-300 text-sm mb-2 font-medium">You asked:</p>
          <p className="text-white text-center">"{userQuery}"</p>
        </div>
      )}

      {response && (
        <div className="mt-4 p-6 bg-white/10 backdrop-blur-xl rounded-3xl max-w-lg border border-white/20 shadow-xl animate-fade-in">
          <p className="text-cyan-300 text-sm mb-3 font-medium">Nesty:</p>
          <p className="text-white">{response}</p>
        </div>
      )}

      {/* Demo Button */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-10">
        <button
          onClick={simulateWakeWord}
          disabled={connectionStatus !== "connected"}
          className="px-8 py-4 bg-gradient-to-r from-cyan-500/20 to-purple-500/20 backdrop-blur-xl rounded-full text-white font-medium hover:from-cyan-500/30 hover:to-purple-500/30 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed border border-white/20 shadow-lg"
        >
          {connectionStatus === "connected"
            ? 'Simulate "Hey Nesty"'
            : "Backend Disconnected"}
        </button>
      </div>

      {/* Wake-up Popup */}
      {showWakeupPopup && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gradient-to-br from-cyan-500/20 to-purple-600/20 backdrop-blur-xl rounded-3xl p-8 border border-white/20 shadow-2xl max-w-sm mx-4 animate-scale-in">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center animate-pulse">
                <Mic className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Wake word detected!
              </h3>
              <p className="text-cyan-200">Activating Nesty...</p>
              <div className="mt-4 flex justify-center space-x-2">
                {[...Array(3)].map((_, i) => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Custom Styles */}
      <style>{`
        @keyframes scale-in {
          from { opacity: 0; transform: scale(0.8); }
          to { opacity: 1; transform: scale(1); }
        }
        
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        .animate-scale-in {
          animation: scale-in 0.3s ease-out;
        }
        
        .animate-fade-in {
          animation: fade-in 0.5s ease-out;
        }
      `}</style>
    </div>
  );
};

export default VoiceAssistant;
