const API_BASE_URL = window.API_BASE_URL ?? "";

const chatWindow = document.getElementById("chat");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const micButton = document.getElementById("mic-button");
const micLabel = document.getElementById("mic-label");
const resetButton = document.getElementById("reset-session");

let sessionId = null;
let apiKey = null;
let typingNode = null;
let mediaRecorder = null;
let mediaStream = null;
let recordedChunks = [];
let isRecording = false;
let activeAudio = null;
let silenceTimeout = null;
let audioContext = null;
let analyser = null;
let silenceStart = null;
const SILENCE_THRESHOLD = 0.01; // Adjust based on testing
const SILENCE_DURATION = 3000; // 3 seconds of silence

init();
setupVoiceControls();

async function init() {
  // Check for stored API key or prompt for one
  apiKey = sessionStorage.getItem("rr-api-key");
  if (!apiKey) {
    apiKey = await promptForApiKey();
    if (!apiKey) {
      appendBotBubble("An access key is required to use the coach. Please refresh the page and enter your key.");
      disableInput();
      return;
    }
    sessionStorage.setItem("rr-api-key", apiKey);
  }

  sessionId = sessionStorage.getItem("rr-session");
  if (!sessionId) {
    try {
      sessionId = await createSession();
      sessionStorage.setItem("rr-session", sessionId);
    } catch (err) {
      // Invalid API key - clear it and prompt again
      sessionStorage.removeItem("rr-api-key");
      appendBotBubble("Invalid access key. Please refresh the page and try again.");
      disableInput();
      return;
    }
  }
  appendBotBubble(
    "Hi! What would you like to talk about today when it comes to physical activity?"
  );
}

function promptForApiKey() {
  return new Promise((resolve) => {
    const key = prompt("Please enter your access key to use the Reframing Retirement Coach:");
    resolve(key ? key.trim() : null);
  });
}

function disableInput() {
  if (messageInput) messageInput.disabled = true;
  if (micButton) micButton.disabled = true;
  if (form) form.style.opacity = "0.5";
}

async function createSession() {
  const res = await fetch(`${API_BASE_URL}/sessions`, {
    method: "POST",
    headers: { "X-API-Key": apiKey }
  });
  if (!res.ok) {
    throw new Error("Unable to start a session.");
  }
  const data = await res.json();
  return data.session_id;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }
  messageInput.value = "";
  appendUserBubble(text);
  await streamAssistantResponse(text);
});

resetButton.addEventListener("click", async () => {
  if (sessionId) {
    await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: "DELETE",
      headers: { "X-API-Key": apiKey }
    });
  }
  sessionStorage.removeItem("rr-session");
  clearChat();
  await init();
});

function setupVoiceControls() {
  if (!micButton) {
    return;
  }
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    micButton.disabled = true;
    setMicButtonLabel("Voice unavailable");
    return;
  }

  // Click to toggle recording (start/stop)
  micButton.addEventListener("click", (event) => {
    event.preventDefault();
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  // Also support keyboard
  micButton.addEventListener("keydown", (event) => {
    if (event.code === "Space" || event.code === "Enter") {
      event.preventDefault();
      if (isRecording) {
        stopRecording();
      } else {
        startRecording();
      }
    }
  });

  // Stop recording if window loses focus
  window.addEventListener("blur", () => {
    if (isRecording) {
      stopRecording();
    }
  });
}

async function startRecording() {
  if (isRecording) {
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    appendBotBubble("Microphone access denied. Please allow microphone access and try again.");
    return;
  }

  const mimeType = pickSupportedMimeType();
  recordedChunks = [];

  try {
    mediaRecorder = mimeType
      ? new MediaRecorder(mediaStream, { mimeType })
      : new MediaRecorder(mediaStream);
  } catch (err) {
    stopMediaTracks();
    appendBotBubble("Something went wrong. Please try again.");
    return;
  }

  mediaRecorder.addEventListener("dataavailable", (event) => {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data);
    }
  });

  mediaRecorder.addEventListener("stop", async () => {
    stopMediaTracks();
    stopSilenceDetection();
    isRecording = false;
    setMicButtonState(false);

    if (!recordedChunks.length) {
      return;
    }

    const blobType = mediaRecorder.mimeType || mimeType || "audio/webm";
    const audioBlob = new Blob(recordedChunks, { type: blobType });
    await sendVoiceMessage(audioBlob);
  });

  mediaRecorder.start();
  isRecording = true;
  setMicButtonState(true);

  // Start silence detection
  startSilenceDetection();
}

function stopRecording() {
  if (!isRecording || !mediaRecorder) {
    return;
  }
  if (mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

function stopMediaTracks() {
  if (!mediaStream) {
    return;
  }
  mediaStream.getTracks().forEach((track) => track.stop());
  mediaStream = null;
}

function startSilenceDetection() {
  if (!mediaStream) {
    return;
  }

  try {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(mediaStream);
    source.connect(analyser);
    analyser.fftSize = 2048;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function checkAudioLevel() {
      if (!isRecording) {
        return;
      }

      analyser.getByteTimeDomainData(dataArray);

      // Calculate RMS (root mean square) to detect audio level
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        const normalized = (dataArray[i] - 128) / 128;
        sum += normalized * normalized;
      }
      const rms = Math.sqrt(sum / bufferLength);

      if (rms < SILENCE_THRESHOLD) {
        // Silence detected
        if (silenceStart === null) {
          silenceStart = Date.now();
        } else if (Date.now() - silenceStart >= SILENCE_DURATION) {
          // 3 seconds of silence, stop recording
          stopRecording();
          return;
        }
      } else {
        // Sound detected, reset silence timer
        silenceStart = null;
      }

      // Check again in 100ms
      silenceTimeout = setTimeout(checkAudioLevel, 100);
    }

    checkAudioLevel();
  } catch (err) {
    console.error("Failed to start silence detection:", err);
  }
}

function stopSilenceDetection() {
  if (silenceTimeout) {
    clearTimeout(silenceTimeout);
    silenceTimeout = null;
  }
  silenceStart = null;

  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  analyser = null;
}

function pickSupportedMimeType() {
  if (!window.MediaRecorder) {
    return "";
  }
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function setMicButtonState(recording) {
  if (!micButton) {
    return;
  }
  micButton.classList.toggle("recording", recording);
  micButton.setAttribute("aria-pressed", recording ? "true" : "false");
  setMicButtonLabel(recording ? "Click to stop" : "Click to talk");
}

function setMicButtonLabel(text) {
  if (micLabel) {
    micLabel.textContent = text;
  }
  if (micButton) {
    micButton.title = text;
  }
}

async function sendVoiceMessage(audioBlob) {
  showTyping();
  try {
    if (!sessionId) {
      sessionId = await createSession();
      sessionStorage.setItem("rr-session", sessionId);
    }

    const formData = new FormData();
    const extension = guessExtension(audioBlob.type);
    const filename = `voice-input.${extension}`;

    // Normalize MIME type to match backend validation
    let normalizedMimeType = audioBlob.type;
    if (normalizedMimeType && normalizedMimeType.includes(";")) {
      // Remove codec info (e.g., "audio/webm;codecs=opus" -> "audio/webm")
      normalizedMimeType = normalizedMimeType.split(";")[0];
    }
    if (!normalizedMimeType) {
      normalizedMimeType = "audio/webm"; // Default
    }

    console.log("Sending voice message:", {
      blobSize: audioBlob.size,
      originalBlobType: audioBlob.type,
      normalizedMimeType: normalizedMimeType,
      filename: filename
    });

    // Create a new blob with normalized MIME type
    const normalizedBlob = new Blob([audioBlob], { type: normalizedMimeType });
    formData.append("audio", normalizedBlob, filename);

    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/voice-chat`, {
      method: "POST",
      headers: { "X-API-Key": apiKey },
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Voice chat error:", response.status, errorText);
      throw new Error(`Voice chat failed: ${errorText || "The coach is unavailable right now."}`);
    }

    const data = await response.json();
    if (data.transcript) {
      appendUserBubble(data.transcript);
    }

    appendBotBubble(data.reply_text || "Something went wrong.");
    playReplyAudio(data.reply_audio, data.reply_audio_mime);
  } catch (err) {
    appendBotBubble(err.message || "Something went wrong.");
  } finally {
    hideTyping();
  }
}

function guessExtension(mimeType) {
  if (!mimeType) {
    return "webm";
  }
  if (mimeType.includes("ogg")) {
    return "ogg";
  }
  if (mimeType.includes("mp4")) {
    return "mp4";
  }
  if (mimeType.includes("wav")) {
    return "wav";
  }
  return "webm";
}

function playReplyAudio(base64Audio, mimeType) {
  if (!base64Audio) {
    return;
  }
  if (activeAudio) {
    activeAudio.pause();
    activeAudio = null;
  }
  const source = `data:${mimeType || "audio/mpeg"};base64,${base64Audio}`;
  const audio = new Audio(source);
  activeAudio = audio;
  audio.play().catch(() => {});
}

async function streamAssistantResponse(text) {
  showTyping();
  const botBubble = appendBotBubble("");
  try {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey
      },
      body: JSON.stringify({ text }),
    });
    if (!response.ok || !response.body) {
      throw new Error("The coach is unavailable right now.");
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalState = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.trim()) {
          continue;
        }
        const event = JSON.parse(line);
        if (event.type === "token") {
          botBubble.textContent += event.text;
        } else if (event.type === "done") {
          finalState = event.state;
        } else if (event.type === "error") {
          throw new Error(event.error || "Unknown error");
        }
      }
    }
    if (finalState) {
      botBubble.dataset.state = JSON.stringify(finalState);
    }
  } catch (err) {
    botBubble.textContent = err.message || "Something went wrong.";
  } finally {
    hideTyping();
  }
}

function appendUserBubble(text) {
  const bubble = document.createElement("div");
  bubble.className = "bubble user";
  bubble.textContent = text;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function appendBotBubble(text) {
  const bubble = document.createElement("div");
  bubble.className = "bubble bot";
  bubble.textContent = text;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return bubble;
}

function showTyping() {
  if (typingNode) {
    return;
  }
  typingNode = document.createElement("div");
  typingNode.className = "typing";
  typingNode.textContent = "Coach is thinking...";
  chatWindow.appendChild(typingNode);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function hideTyping() {
  if (!typingNode) {
    return;
  }
  chatWindow.removeChild(typingNode);
  typingNode = null;
}

function clearChat() {
  chatWindow.innerHTML = "";
}
