class VisionCompanionApp {
  constructor() {
    this.active = false;
    this.listening = false;
    this.recognition = null;
    this.mediaStream = null;
    this.geoWatchId = null;
    this.frameTimer = null;
    this.audioQueue = [];
    this.speaking = false;
    this.lastInstruction = "";
    this.currentCoords = null;

    this.apiKey = localStorage.getItem("GEMINI_API_KEY") || "";
    this.model = "gemini-2.0-flash";

    this.app = document.getElementById("app");
    this.tapHint = document.getElementById("tapHint");
    this.centerRing = document.getElementById("centerRing");
    this.centerIcon = document.getElementById("centerIcon");
    this.centerState = document.getElementById("centerState");
    this.statusText = document.getElementById("statusText");
    this.permissionText = document.getElementById("permissionText");
    this.gpsState = document.getElementById("gpsState");
    this.visionState = document.getElementById("visionState");
    this.liveRegion = document.getElementById("liveRegion");
    this.video = document.getElementById("cameraPreview");
    this.canvas = document.getElementById("frameCanvas");

    document.body.addEventListener("click", () => this.toggleAssistant());
    this.setupSpeechRecognition();
    this.updateUi();
  }

  announce(text, priority = "normal") {
    this.liveRegion.textContent = text;
    this.lastInstruction = text;
    if (priority === "danger") this.setDangerVisual(true);
    this.enqueueSpeech(text);
    this.statusText.textContent = text;
    if (priority === "danger") setTimeout(() => this.setDangerVisual(false), 2000);
  }

  enqueueSpeech(text) {
    this.audioQueue.push(text);
    if (!this.speaking) this.flushSpeechQueue();
  }

  flushSpeechQueue() {
    if (!this.audioQueue.length) {
      this.speaking = false;
      return;
    }

    this.speaking = true;
    const text = this.audioQueue.shift();
    if (!window.speechSynthesis) {
      this.speaking = false;
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.onend = () => this.flushSpeechQueue();
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  setDangerVisual(enabled) {
    this.centerRing.classList.toggle("danger", enabled);
    this.centerIcon.textContent = enabled ? "⚠️" : this.active ? "🎤" : "🎙️";
  }

  updateUi() {
    this.centerRing.classList.toggle("active", this.active);
    this.centerRing.classList.toggle("stopped", !this.active);
    this.centerIcon.textContent = this.active ? "🎤" : "🎙️";
    this.centerState.textContent = this.active ? "Listening" : "Stopped";
    this.tapHint.textContent = this.active ? "● Tap anywhere to stop" : "● Tap anywhere to start";
  }

  async toggleAssistant() {
    if (!this.active) {
      const ok = await this.acquirePermissions();
      if (!ok) return;
      this.active = true;
      this.updateUi();
      this.startVoiceInput();
      this.startGpsWatch();
      this.startVisionLoop();
      this.announce("Assistant started. Say start navigation.");
    } else {
      this.stopAll();
      this.announce("Assistant stopped.");
    }
  }

  async acquirePermissions() {
    const checks = [];

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
        video: {
          facingMode: "environment",
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
      });
      this.video.srcObject = this.mediaStream;
      checks.push("mic+camera granted");
      this.visionState.textContent = "Ready";
    } catch {
      checks.push("mic+camera denied");
      this.visionState.textContent = "Denied";
      this.announce("Microphone and camera permission required.", "danger");
      this.permissionText.textContent = `Permissions: ${checks.join(", ")}`;
      return false;
    }

    if (!navigator.geolocation) {
      checks.push("gps unsupported");
      this.gpsState.textContent = "Unsupported";
    } else {
      checks.push("gps pending");
      this.gpsState.textContent = "Pending";
    }

    this.permissionText.textContent = `Permissions: ${checks.join(", ")}`;
    return true;
  }

  releasePermissions() {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
      this.video.srcObject = null;
    }

    if (this.geoWatchId !== null) {
      navigator.geolocation.clearWatch(this.geoWatchId);
      this.geoWatchId = null;
    }

    if (this.frameTimer) {
      clearInterval(this.frameTimer);
      this.frameTimer = null;
    }
  }

  startVoiceInput() {
    if (!this.recognition) return;
    this.listening = true;
    this.recognition.start();
  }

  setupSpeechRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    this.recognition = new SR();
    this.recognition.continuous = true;
    this.recognition.lang = "en-US";
    this.recognition.interimResults = false;

    this.recognition.onresult = (event) => {
      const command = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
      this.handleCommand(command);
    };

    this.recognition.onend = () => {
      if (this.active && this.listening) this.recognition.start();
    };
  }

  handleCommand(command) {
    if (command.includes("stop")) return this.stopAll();
    if (command.includes("start navigation")) return this.announce("Navigation active. Listening for hazards.");
    if (command.includes("what is ahead") || command.includes("describe surroundings")) return this.runImmediateVision();
    if (command.includes("repeat")) return this.announce(this.lastInstruction || "No instruction yet.");
    this.announce(`Command heard: ${command}`);
  }

  startGpsWatch() {
    if (!navigator.geolocation) return;

    this.geoWatchId = navigator.geolocation.watchPosition(
      (pos) => {
        this.currentCoords = pos.coords;
        this.gpsState.textContent = "Locked";
      },
      () => {
        this.gpsState.textContent = "Denied";
        this.announce("Location permission denied. Navigation context reduced.");
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
    );
  }

  startVisionLoop() {
    this.frameTimer = setInterval(() => this.analyzeFrame(), 1000);
  }

  async runImmediateVision() {
    await this.analyzeFrame();
  }

  async analyzeFrame() {
    if (!this.video.srcObject) return;

    const frame = this.captureDownscaledFrame();
    if (!frame) return;

    try {
      const prompt = this.buildSafetyPrompt();
      const summary = await this.callGeminiWithRetry(frame, prompt);
      this.visionState.textContent = "On";
      this.processSafetySummary(summary);
    } catch (error) {
      this.visionState.textContent = "Error";
      this.announce("Network or AI issue. Falling back to local scan.");
      await this.fallbackLocalScan();
    }
  }

  captureDownscaledFrame() {
    const w = 320;
    const h = 240;
    this.canvas.width = w;
    this.canvas.height = h;
    const ctx = this.canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    ctx.drawImage(this.video, 0, 0, w, h);
    return this.canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
  }

  buildSafetyPrompt() {
    const gps = this.currentCoords
      ? `GPS lat ${this.currentCoords.latitude.toFixed(5)}, lon ${this.currentCoords.longitude.toFixed(5)}`
      : "GPS unavailable";

    return [
      "You are Vision Companion AI for blind safety navigation.",
      "Return a SHORT response only.",
      "Priority: immediate danger > guidance > awareness.",
      "Use clock direction and distance estimates.",
      "Examples: STOP! Vehicle left. Obstacle 2m ahead. Path clear 5 meters.",
      gps,
    ].join(" ");
  }

  async callGeminiWithRetry(base64Image, prompt, attempt = 1) {
    if (!this.apiKey) {
      throw new Error("Missing Gemini API key. Set localStorage.GEMINI_API_KEY");
    }

    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${this.model}:generateContent?key=${this.apiKey}`;

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                { text: prompt },
                { inline_data: { mime_type: "image/jpeg", data: base64Image } },
              ],
            },
          ],
          generationConfig: { temperature: 0.2, maxOutputTokens: 60 },
        }),
      });

      if (!response.ok) {
        throw new Error(`Gemini error ${response.status}`);
      }

      const json = await response.json();
      return json?.candidates?.[0]?.content?.parts?.[0]?.text || "Unclear environment. Move slowly.";
    } catch (error) {
      if (attempt < 3) {
        await new Promise((r) => setTimeout(r, attempt * 700));
        return this.callGeminiWithRetry(base64Image, prompt, attempt + 1);
      }
      throw error;
    }
  }

  processSafetySummary(text) {
    const lower = text.toLowerCase();
    if (lower.includes("stop") || lower.includes("vehicle") || lower.includes("very close")) {
      this.announce(text, "danger");
      return;
    }
    this.announce(text);
  }

  async fallbackLocalScan() {
    try {
      const response = await fetch("/api/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guidance_mode: true }),
      });
      const data = await response.json();
      this.announce(data.alert || "Unclear environment. Move slowly.");
    } catch {
      this.announce("Unclear environment. Move slowly.", "danger");
    }
  }

  stopAll() {
    this.active = false;
    this.listening = false;
    this.updateUi();

    if (this.recognition) {
      try { this.recognition.stop(); } catch {}
    }

    this.releasePermissions();
    this.gpsState.textContent = "Off";
    this.visionState.textContent = "Off";
    this.permissionText.textContent = "Permissions: released";
  }
}

window.addEventListener("DOMContentLoaded", () => new VisionCompanionApp());
