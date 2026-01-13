const API_BASE_URL = window.API_BASE_URL ?? "http://localhost:8000";

const chatWindow = document.getElementById("chat");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const micButton = document.getElementById("mic-button");
const micLabel = document.getElementById("mic-label");
const resetButton = document.getElementById("reset-session");

let sessionId = null;
let typingNode = null;
let mediaRecorder = null;
let mediaStream = null;
let recordedChunks = [];
let isRecording = false;
let recordIntent = false;
let activeAudio = null;

init();
setupVoiceControls();

async function init() {
  sessionId = sessionStorage.getItem("rr-session");
  if (!sessionId) {
    sessionId = await createSession();
    sessionStorage.setItem("rr-session", sessionId);
  }
  appendBotBubble(
    "Hi! What would you like to talk about today when it comes to physical activity?"
  );
}

async function createSession() {
  const res = await fetch(`${API_BASE_URL}/sessions`, { method: "POST" });
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
    await fetch(`${API_BASE_URL}/sessions/${sessionId}`, { method: "DELETE" });
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

  micButton.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    micButton.setPointerCapture(event.pointerId);
    recordIntent = true;
    startRecording();
  });
  micButton.addEventListener("pointerup", () => {
    recordIntent = false;
    stopRecording();
  });
  micButton.addEventListener("pointerleave", () => {
    recordIntent = false;
    stopRecording();
  });
  micButton.addEventListener("pointercancel", () => {
    recordIntent = false;
    stopRecording();
  });
  micButton.addEventListener("keydown", (event) => {
    if (event.code === "Space" || event.code === "Enter") {
      event.preventDefault();
      recordIntent = true;
      startRecording();
    }
  });
  micButton.addEventListener("keyup", (event) => {
    if (event.code === "Space" || event.code === "Enter") {
      event.preventDefault();
      recordIntent = false;
      stopRecording();
    }
  });

  window.addEventListener("blur", () => {
    recordIntent = false;
    stopRecording();
  });
}

async function startRecording() {
  if (isRecording) {
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    appendBotBubble("Something went wrong. Please try again.");
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

  if (!recordIntent) {
    stopRecording();
  }
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
  setMicButtonLabel(recording ? "Release to send" : "Hold to talk");
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
    formData.append("audio", audioBlob, `voice-input.${extension}`);

    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/voice-chat`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("The coach is unavailable right now.");
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
      headers: { "Content-Type": "application/json" },
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
