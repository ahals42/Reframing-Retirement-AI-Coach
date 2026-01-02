const API_BASE_URL = window.API_BASE_URL ?? "http://localhost:8000";

const chatWindow = document.getElementById("chat");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const resetButton = document.getElementById("reset-session");

let sessionId = null;
let typingNode = null;

init();

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
