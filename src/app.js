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

    this.appShell = document.querySelector(".app-shell");
    this.systemState = document.getElementById("systemState");
    this.statusText = document.getElementById("statusText");
    this.locationText = document.getElementById("locationText");
    this.visionText = document.getElementById("visionText");
    this.liveRegion = document.getElementById("liveRegion");
    this.micBtn = document.getElementById("micBtn");

    this.micBtn.addEventListener("click", () => this.toggleVoiceRecognition());
    this.setupVoiceRecognition();
    this.checkBackend();
    this.updateSystemState();
  }

  updateSystemState() {
    this.systemState.textContent = `● System Status: ${this.active ? "Active" : "Inactive"}`;
    this.appShell.classList.toggle("active", this.active);
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

  startGuidance() {
    if (this.active) return this.announce("Guidance is already active.");
    this.active = true;
    this.index = 0;
    this.updateSystemState();
    this.updateForCurrentStep("Guidance started.");
  }

  nextStep() {
    if (!this.active) return this.announce("Guidance is not active. Say assistant start navigation.");
    if (this.index < route.length - 1) {
      this.index += 1;
      return this.updateForCurrentStep("Proceeding to the next waypoint.");
    }
    this.announce("You are already at the destination.");
  }

  repeatStep() {
    if (!this.active || this.index < 0) return this.announce("No active step to repeat.");
    this.announce(`Repeating current step. ${route[this.index].instruction}`);
  }

  async scanScene() {
    this.visionText.textContent = "Vision: scanning scene with Python YOLO service...";
    try {
      const response = await fetch("/api/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guidance_mode: this.active })
      });
      if (!response.ok) throw new Error("Detection failed");
      const data = await response.json();
      this.visionText.textContent = `Vision [${data.engine}]: ${data.summary}`;
      this.announce(data.alert);
    } catch {
      this.visionText.textContent = "Vision scan failed. Ensure Python backend is running (`python server.py`).";
      this.announce("Vision scan failed. Continue cautiously.");
    }
  }

  stopGuidance() {
    if (!this.active) return this.announce("Guidance is already stopped.");
    this.active = false;
    this.index = -1;
    this.updateSystemState();
    this.statusText.textContent = "Guidance stopped. Say start command when ready.";
    this.locationText.textContent = "Location: Navigation paused";
    this.speak("Guidance stopped.");
  }

  updateForCurrentStep(prefix) {
    const step = route[this.index];
    const combined = `${prefix} ${step.instruction}`;
    this.statusText.textContent = combined;
    this.locationText.textContent = `Location: ${step.name} (${this.index + 1} of ${route.length})`;
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
    window.speechSynthesis.speak(utterance);
  }

  setupVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.micBtn.disabled = true;
      this.micBtn.textContent = "🚫";
      this.micBtn.setAttribute("aria-label", "Voice command unsupported");
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
      this.announce("Voice recognition error. Please try again.");
    };
  }

  toggleVoiceRecognition() {
    if (!this.recognition) return;
    this.listening = !this.listening;
    this.micBtn.textContent = this.listening ? "🟢" : "🎙️";
    this.micBtn.setAttribute("aria-label", `Voice command ${this.listening ? "on" : "off"}`);

    if (this.listening) {
      this.recognition.start();
      this.announce("Voice command activated.");
    } else {
      this.recognition.stop();
      this.announce("Voice command deactivated.");
    }
  }

  handleCommand(command) {
    if (command.includes("assistant start navigation") || command.includes("start")) return this.startGuidance();
    if (command.includes("next")) return this.nextStep();
    if (command.includes("repeat")) return this.repeatStep();
    if (command.includes("scan")) return this.scanScene();
    if (command.includes("stop")) return this.stopGuidance();
    if (command.includes("where am i") || command.includes("location")) return this.announce(this.locationText.textContent);
    if (command.includes("help")) {
      return this.announce("Say: assistant start navigation, next, repeat, scan scene, where am I, stop.");
    }
    this.announce(`Unknown command: ${command}`);
  }
}

window.addEventListener("DOMContentLoaded", () => new BlindNavigationApp());
