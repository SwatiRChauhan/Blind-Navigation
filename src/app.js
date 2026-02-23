class VisionCompanionApp {
  constructor() {
    this.active = false;
    this.listening = false;
    this.recognition = null;
    this.mediaStream = null;
    this.geoWatchId = null;
    this.frameTimer = null;
    this.lastInstruction = "";
    this.currentCoords = null;
    this.permissionState = { micCam: false, gps: false };

    this.centerRing = document.getElementById("centerRing");
    this.centerIcon = document.getElementById("centerIcon");
    this.centerState = document.getElementById("centerState");
    this.statusText = document.getElementById("statusText");
    this.permissionText = document.getElementById("permissionText");
    this.gpsState = document.getElementById("gpsState");
    this.visionState = document.getElementById("visionState");
    this.liveRegion = document.getElementById("liveRegion");
    this.video = document.getElementById("cameraPreview");

    this.setupSpeechRecognition();
    this.bootstrap();
  }

  async bootstrap() {
    const granted = await this.acquirePermissions();
    if (!granted) {
      this.announce("Permissions blocked. Allow microphone, camera, and location to run hands-free.", "danger");
      return;
    }

    this.startVoiceInput();
    this.announce("Voice control ready. Say start navigation.");
  }

  announce(text, priority = "normal") {
    this.lastInstruction = text;
    this.liveRegion.textContent = text;
    this.statusText.textContent = text;

    if (priority === "danger") {
      this.centerRing.classList.add("danger");
      setTimeout(() => this.centerRing.classList.remove("danger"), 1800);
    }

    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1;
      window.speechSynthesis.speak(utterance);
    }
  }

  updateUi() {
    this.centerRing.classList.toggle("active", this.active);
    this.centerRing.classList.toggle("stopped", !this.active);
    this.centerIcon.textContent = this.active ? "🟢" : "🎙️";
    this.centerState.textContent = this.active ? "Active" : "Stopped";
    this.visionState.textContent = this.active ? "On" : "Off";
  }

  async acquirePermissions() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.permissionText.textContent = "Permissions: unsupported browser";
      return false;
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true },
        video: { facingMode: "environment", width: { ideal: 640 }, height: { ideal: 480 } },
      });
      this.video.srcObject = this.mediaStream;
      this.permissionState.micCam = true;
    } catch {
      this.permissionState.micCam = false;
    }

    if (navigator.geolocation) {
      try {
        await new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0,
          });
        });
        this.permissionState.gps = true;
      } catch {
        this.permissionState.gps = false;
      }
    }

    this.permissionText.textContent = `Permissions: mic/camera ${this.permissionState.micCam ? "granted" : "denied"}, location ${this.permissionState.gps ? "granted" : "denied"}`;
    this.gpsState.textContent = this.permissionState.gps ? "Locked" : "Denied";

    return this.permissionState.micCam;
  }

  startVoiceInput() {
    if (!this.recognition || this.listening) return;
    this.listening = true;
    this.recognition.start();
  }

  stopVoiceInput() {
    if (!this.recognition || !this.listening) return;
    this.listening = false;
    try {
      this.recognition.stop();
    } catch {
      // no-op
    }
  }

  setupSpeechRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      this.announce("Offline speech recognition unavailable on this browser.", "danger");
      return;
    }

    this.recognition = new SR();
    this.recognition.continuous = true;
    this.recognition.lang = "en-US";
    this.recognition.interimResults = false;

    this.recognition.onresult = (event) => {
      const command = event.results[event.results.length - 1][0].transcript.toLowerCase().trim();
      this.handleCommand(command);
    };

    this.recognition.onend = () => {
      if (this.listening) {
        try {
          this.recognition.start();
        } catch {
          // browser throttle
        }
      }
    };

    this.recognition.onerror = () => {
      this.announce("Voice input error. Listening resumed.");
    };
  }

  handleCommand(command) {
    if (command.includes("start navigation")) {
      return this.startNavigation();
    }

    if (command.includes("stop navigation") || command === "stop") {
      return this.stopNavigation();
    }

    if (!this.active) {
      return;
    }

    if (command.includes("what is ahead") || command.includes("describe surroundings")) {
      return this.runImmediateVision();
    }

    if (command.includes("repeat")) {
      return this.announce(this.lastInstruction || "No instruction available.");
    }
  }

  startNavigation() {
    if (this.active) return;
    this.active = true;
    this.updateUi();
    this.startGpsWatch();
    this.startVisionLoop();
    this.announce("Navigation started.");
  }

  stopNavigation() {
    if (!this.active) return;
    this.active = false;
    this.updateUi();
    this.stopVisionLoop();
    this.stopGpsWatch();
    this.announce("Navigation stopped.");
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
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 12000 }
    );
  }

  stopGpsWatch() {
    if (this.geoWatchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(this.geoWatchId);
      this.geoWatchId = null;
    }
  }

  startVisionLoop() {
    if (this.frameTimer) return;
    this.frameTimer = setInterval(() => this.analyzeFrame(), 1000);
  }

  stopVisionLoop() {
    if (this.frameTimer) {
      clearInterval(this.frameTimer);
      this.frameTimer = null;
    }
    this.visionState.textContent = "Off";
  }

  async runImmediateVision() {
    await this.analyzeFrame();
  }

  async analyzeFrame() {
    if (!this.active) return;

    try {
      const response = await fetch("/api/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guidance_mode: true }),
      });

      if (!response.ok) throw new Error("detect failed");

      const data = await response.json();
      this.visionState.textContent = data.engine || "On";
      const description = this.composeEnvironmentalDescription(data.detections || []);
      this.processSafetySummary(description || data.alert || "Unclear environment. Move slowly.");
    } catch {
      this.visionState.textContent = "Error";
      this.processSafetySummary("Unclear environment. Move slowly.");
    }
  }

  composeEnvironmentalDescription(detections) {
    if (!detections.length) return "Path unclear. Move slowly.";

    const ordered = detections
      .slice(0, 3)
      .map((d) => {
        const label = (d.label || "object").toLowerCase();
        const direction = d.direction || "ahead";
        const proximity = d.proximity || this.proximityFromDistance(d.distance_hint_m);
        const movement = d.movement && d.movement !== "unknown" ? ` moving ${d.movement}` : "";

        if (label === "person") {
          return `person ${direction} ${proximity}${movement}`;
        }

        return `${label} ${direction} ${proximity}${movement}`;
      });

    return ordered.join(". ");
  }

  proximityFromDistance(distanceHint) {
    const d = Number(distanceHint);
    if (!Number.isFinite(d)) return "near";
    if (d <= 0.8) return "very close";
    if (d <= 1.6) return "near";
    if (d <= 3) return "medium";
    return "far";
  }

  processSafetySummary(text) {
    const lower = text.toLowerCase();
    if (
      lower.includes("vehicle") ||
      lower.includes("very close") ||
      lower.includes("dropoff") ||
      lower.includes("stairs down")
    ) {
      return this.announce(`Stop. ${text}`, "danger");
    }

    this.announce(text);
  }
}

window.addEventListener("DOMContentLoaded", () => new VisionCompanionApp());
