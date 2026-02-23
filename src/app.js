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
    this.startPhrase = "start safe navigation";
    this.stopPhrase = "stop safe navigation";

    // Controlled feedback state
    this.lastAutoSummary = "";
    this.lastHazardLevel = 0;
    this.lastCriticalCondition = "";
    this.speakingPriority = null;
    this.pendingNormalAnnouncement = "";

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
    this.announce("Voice control ready. Say start safe navigation.");
  }

  announce(text, priority = "normal") {
    this.lastInstruction = text;
    this.liveRegion.textContent = text;
    this.statusText.textContent = text;

    if (priority === "danger") {
      this.centerRing.classList.add("danger");
      setTimeout(() => this.centerRing.classList.remove("danger"), 1800);
    }

    if (!window.speechSynthesis) return;

    if (priority === "normal" && this.speakingPriority === "danger") {
      this.pendingNormalAnnouncement = text;
      return;
    }

    if (priority === "danger") {
      window.speechSynthesis.cancel();
    }

    this.speakingPriority = priority;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.onend = () => {
      const queued = this.pendingNormalAnnouncement;
      this.pendingNormalAnnouncement = "";
      this.speakingPriority = null;
      if (queued) {
        this.announce(queued, "normal");
      }
    };
    window.speechSynthesis.speak(utterance);
  }

  updateUi() {
    this.centerRing.classList.toggle("active", this.active);
    this.centerRing.classList.toggle("stopped", !this.active);
    this.centerIcon.textContent = this.active ? "🟢" : "🎙️";
    this.centerState.textContent = this.active ? "Active" : "Stopped";
    this.visionState.textContent = this.active ? this.visionState.textContent : "Off";
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

  normalizeCommand(command) {
    return command
      .toLowerCase()
      .replace(/[^a-z\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  matchesPhrase(command, phrase) {
    if (command === phrase) return true;
    return command.startsWith(`${phrase} `) || command.endsWith(` ${phrase}`) || command.includes(` ${phrase} `);
  }

  handleCommand(command) {
    const normalized = this.normalizeCommand(command);

    if (this.matchesPhrase(normalized, this.startPhrase)) {
      return this.startNavigation();
    }

    if (this.matchesPhrase(normalized, this.stopPhrase)) {
      return this.stopNavigation();
    }

    if (normalized.includes("help") || normalized.includes("what can you do")) {
      return this.speakContextHelp();
    }

    if (!this.active) return;

    if (
      normalized.includes("what is ahead") ||
      normalized.includes("describe surroundings") ||
      normalized.includes("describe scene")
    ) {
      return this.runImmediateVision(true);
    }

    if (normalized.includes("repeat")) {
      return this.announce(this.lastInstruction || "No instruction available.");
    }
  }

  speakContextHelp() {
    const helpText =
      "Available voice commands: Start safe navigation, Stop safe navigation, What is ahead, Describe surroundings, Help, and Repeat.";

    return this.announce(helpText, "normal");
  }

  startNavigation() {
    if (this.active) return;
    this.active = true;
    this.lastHazardLevel = 0;
    this.lastAutoSummary = "";
    this.lastCriticalCondition = "";
    this.speakingPriority = null;
    this.pendingNormalAnnouncement = "";
    this.updateUi();
    this.startGpsWatch();
    this.startVisionLoop();
    this.announce("Safe navigation started.");
  }

  stopNavigation() {
    if (!this.active) return;
    this.active = false;
    this.updateUi();
    this.stopVisionLoop();
    this.stopGpsWatch();
    this.announce("Safe navigation stopped.");
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
    this.frameTimer = setInterval(() => this.analyzeFrame(false), 1000);
  }

  stopVisionLoop() {
    if (this.frameTimer) {
      clearInterval(this.frameTimer);
      this.frameTimer = null;
    }
    this.visionState.textContent = "Off";
  }

  async runImmediateVision(userRequested = false) {
    await this.analyzeFrame(userRequested);
  }

  assessSystemConditions(detections) {
    if (!this.mediaStream || !this.video.srcObject) {
      return "camera blocked";
    }

    if (!detections.length) {
      return "low visibility";
    }

    return "ok";
  }

  hazardLevelFromDescription(text) {
    const lower = text.toLowerCase();
    if (lower.includes("vehicle") || lower.includes("dropoff") || lower.includes("very close") || lower.includes("stairs down")) return 3;
    if (lower.includes("near") || lower.includes("obstacle")) return 2;
    if (lower.includes("person") || lower.includes("medium")) return 1;
    return 0;
  }

  async analyzeFrame(userRequested = false) {
    if (!this.active) return;

    try {
      const response = await fetch("/api/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guidance_mode: true }),
      });

      if (!response.ok) throw new Error("detect failed");

      const data = await response.json();
      const detections = data.detections || [];
      this.visionState.textContent = data.engine || "On";

      const condition = this.assessSystemConditions(detections);
      if (condition !== "ok") {
        if (condition !== this.lastCriticalCondition) {
          this.lastCriticalCondition = condition;
          const msg = condition === "camera blocked" ? "Camera blocked. Stop and reposition phone." : "Low visibility. Move slowly.";
          this.announce(msg, "danger");
        }
        return;
      }
      this.lastCriticalCondition = "";

      const description = this.composeEnvironmentalDescription(detections);
      const hazardLevel = this.hazardLevelFromDescription(description);

      if (userRequested) {
        this.lastHazardLevel = hazardLevel;
        this.lastAutoSummary = description;
        this.processSafetySummary(description);
        return;
      }

      // Controlled feedback: announce only when danger is new/increasing.
      if (hazardLevel > this.lastHazardLevel) {
        this.lastHazardLevel = hazardLevel;
        this.lastAutoSummary = description;
        this.processSafetySummary(description);
        return;
      }

      // If unchanged or lower risk, do not repeat routine info.
      if (hazardLevel < this.lastHazardLevel) {
        this.lastHazardLevel = hazardLevel;
      }
    } catch {
      this.visionState.textContent = "Error";
      if (this.lastCriticalCondition !== "vision-failure") {
        this.lastCriticalCondition = "vision-failure";
        this.processSafetySummary("Unclear environment. Move slowly.");
      }
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
