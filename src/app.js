const route = [
  { name: "Main Entrance", instruction: "Face forward and walk 15 meters to the reception desk." },
  { name: "Reception Desk", instruction: "Turn right and continue 10 meters toward the elevator." },
  { name: "Elevator", instruction: "Move slightly left and walk 8 meters to the tactile floor marker." },
  { name: "Tactile Marker", instruction: "Continue straight for 12 meters. Destination is on your right." },
  { name: "Destination", instruction: "You have arrived at your destination." }
];

class BlindNavigationApp {
  constructor() {
    this.index = -1;
    this.active = false;
    this.recognition = null;
    this.listening = false;

    this.statusText = document.getElementById("statusText");
    this.locationText = document.getElementById("locationText");
    this.visionText = document.getElementById("visionText");
    this.routeList = document.getElementById("routeList");
    this.liveRegion = document.getElementById("liveRegion");
    this.micBtn = document.getElementById("micBtn");

    this.bindEvents();
    this.renderRoute();
    this.setupVoiceRecognition();
    this.checkBackend();
  }

  bindEvents() {
    document.getElementById("startBtn").addEventListener("click", () => this.startGuidance());
    document.getElementById("nextBtn").addEventListener("click", () => this.nextStep());
    document.getElementById("repeatBtn").addEventListener("click", () => this.repeatStep());
    document.getElementById("obstacleBtn").addEventListener("click", () => this.simulateObstacle());
    document.getElementById("scanBtn").addEventListener("click", () => this.scanScene());
    document.getElementById("stopBtn").addEventListener("click", () => this.stopGuidance());
    this.micBtn.addEventListener("click", () => this.toggleVoiceRecognition());

    document.addEventListener("keydown", (event) => {
      const key = event.key.toLowerCase();
      if (key === "s") this.startGuidance();
      if (key === "n") this.nextStep();
      if (key === "r") this.repeatStep();
      if (key === "o") this.simulateObstacle();
      if (key === "v") this.scanScene();
      if (key === "x") this.stopGuidance();
    });
  }

  async checkBackend() {
    try {
      const response = await fetch("/health");
      if (!response.ok) throw new Error("health failed");
      const data = await response.json();
      this.visionText.textContent = `Vision: backend ${data.backend}, engine ready: ${data.yolo_ready ? "yes" : "fallback"}`;
    } catch {
      this.visionText.textContent = "Vision: backend unavailable. Start with `python server.py`.";
    }
  }

  renderRoute() {
    this.routeList.innerHTML = "";

    route.forEach((step, idx) => {
      const item = document.createElement("li");
      item.textContent = `${step.name}: ${step.instruction}`;
      if (idx === this.index) item.classList.add("current");
      this.routeList.appendChild(item);
    });
  }

  startGuidance() {
    if (this.active) {
      this.announce("Guidance is already active.");
      return;
    }

    this.active = true;
    this.index = 0;
    this.updateForCurrentStep("Guidance started.");
  }

  nextStep() {
    if (!this.active) {
      this.announce("Guidance is not active. Press start first.");
      return;
    }

    if (this.index < route.length - 1) {
      this.index += 1;
      this.updateForCurrentStep("Proceeding to the next waypoint.");
      return;
    }

    this.announce("You are already at the destination.");
  }

  repeatStep() {
    if (!this.active || this.index < 0) {
      this.announce("No active step to repeat.");
      return;
    }

    const step = route[this.index];
    this.announce(`Repeating current step. ${step.instruction}`);
  }

  simulateObstacle() {
    if (!this.active) {
      this.announce("Start guidance before simulating obstacles.");
      return;
    }

    const message =
      "Obstacle detected ahead. Stop. Shift one meter left, then continue forward cautiously.";
    this.announce(message);
    this.statusText.textContent = message;
  }

  async scanScene() {
    this.visionText.textContent = "Vision: scanning scene with Python YOLO service...";

    try {
      const response = await fetch("/api/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guidance_mode: this.active })
      });

      if (!response.ok) {
        throw new Error("Detection failed");
      }

      const data = await response.json();
      const detected = data.detections.length
        ? data.detections.map((d) => `${d.label} (${Math.round(d.confidence * 100)}%)`).join(", ")
        : "none";

      this.visionText.textContent = `Vision [${data.engine}]: ${data.summary} Objects: ${detected}.`;
      this.announce(data.alert);
    } catch {
      this.visionText.textContent = "Vision scan failed. Ensure Python backend is running (`python server.py`).";
      this.announce("Vision scan failed. Continue with manual navigation controls.");
    }
  }

  stopGuidance() {
    if (!this.active) {
      this.announce("Guidance is already stopped.");
      return;
    }

    this.active = false;
    this.index = -1;
    this.statusText.textContent = "Guidance stopped. Press Start Guidance when ready.";
    this.locationText.textContent = "Location: Navigation paused";
    this.renderRoute();
    this.speak("Guidance stopped.");
  }

  updateForCurrentStep(prefix) {
    const step = route[this.index];
    const combined = `${prefix} ${step.instruction}`;
    this.statusText.textContent = combined;
    this.locationText.textContent = `Location: ${step.name} (${this.index + 1} of ${route.length})`;
    this.renderRoute();
    this.announce(combined);
  }

  announce(message) {
    this.liveRegion.textContent = message;
    this.speak(message);
  }

  speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }

  setupVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.micBtn.disabled = true;
      this.micBtn.textContent = "Voice Command: Unsupported";
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.lang = "en-US";
    this.recognition.interimResults = false;

    this.recognition.onresult = (event) => {
      const transcript = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
      this.handleCommand(transcript);
    };

    this.recognition.onend = () => {
      if (this.listening) this.recognition.start();
    };

    this.recognition.onerror = () => {
      this.announce("Voice recognition error. You can continue with buttons and keyboard.");
    };
  }

  toggleVoiceRecognition() {
    if (!this.recognition) return;

    this.listening = !this.listening;
    this.micBtn.textContent = `Voice Command: ${this.listening ? "On" : "Off"}`;

    if (this.listening) {
      this.recognition.start();
      this.announce("Voice command activated.");
    } else {
      this.recognition.stop();
      this.announce("Voice command deactivated.");
    }
  }

  handleCommand(command) {
    if (command.includes("start")) return this.startGuidance();
    if (command.includes("next")) return this.nextStep();
    if (command.includes("repeat")) return this.repeatStep();
    if (command.includes("scan") || command.includes("vision")) return this.scanScene();
    if (command.includes("stop")) return this.stopGuidance();
    if (command.includes("where am i") || command.includes("location")) {
      return this.announce(this.locationText.textContent);
    }

    if (command.includes("help")) {
      return this.announce(
        "Available commands: start, next, repeat, scan, where am I, stop, and help."
      );
    }

    this.announce(`Unknown command: ${command}`);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  new BlindNavigationApp();
});
