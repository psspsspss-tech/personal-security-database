// 8-Bit Offline TV Main Controller
const tvChannels = [
    { type: 'matrix', title: 'Matrix Rain' },
    { type: 'snake', title: 'Snake Game' },
    { type: 'hacker', title: 'Hacker Terminal' },
    { type: 'procedural', title: '8-Bit Cyber TV' }
];

var isOfflineMode = false;
var tvDismissed = false;

// --- WEB AUDIO SYNTHESIZER ---
let audioCtx = null;
let humOsc = null;
let humGain = null;
let staticNode = null;
let staticGain = null;

function initAudio() {
    if (audioCtx) return;
    try {
        audioCtx = new AudioContext();
        
        // 1. Low ambient hum
        humOsc = audioCtx.createOscillator();
        humGain = audioCtx.createGain();
        humOsc.type = 'sawtooth';
        humOsc.frequency.setValueAtTime(55, audioCtx.currentTime); // Low A
        humGain.gain.setValueAtTime(0.015, audioCtx.currentTime);
        
        // Filter out high harsh frequencies from the hum
        const filter = audioCtx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(100, audioCtx.currentTime);

        humOsc.connect(filter);
        filter.connect(humGain);
        humGain.connect(audioCtx.destination);
        humOsc.start();
        
        // 2. White noise generator for static effect
        const bufferSize = 2 * audioCtx.sampleRate;
        const noiseBuffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
        const output = noiseBuffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            output[i] = Math.random() * 2 - 1;
        }
        
        staticNode = audioCtx.createBufferSource();
        staticNode.buffer = noiseBuffer;
        staticNode.loop = true;
        
        staticGain = audioCtx.createGain();
        staticGain.gain.setValueAtTime(0.008, audioCtx.currentTime);
        
        const staticFilter = audioCtx.createBiquadFilter();
        staticFilter.type = 'bandpass';
        staticFilter.frequency.setValueAtTime(800, audioCtx.currentTime);
        staticFilter.Q.setValueAtTime(1.0, audioCtx.currentTime);
        
        staticNode.connect(staticFilter);
        staticFilter.connect(staticGain);
        staticGain.connect(audioCtx.destination);
        staticNode.start();
    } catch (err) {
        console.warn('Web Audio API not supported or blocked:', err);
    }
}

function resumeAudio() {
    if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playBeep(freq, type, duration, volume = 0.1) {
    if (!audioCtx) return;
    resumeAudio();
    try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        gain.gain.setValueAtTime(volume, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch (e) {}
}

function playNoise(duration, volume = 0.1) {
    if (!audioCtx) return;
    resumeAudio();
    try {
        const bufferSize = audioCtx.sampleRate * duration;
        const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }
        const source = audioCtx.createBufferSource();
        source.buffer = buffer;
        
        const gain = audioCtx.createGain();
        gain.gain.setValueAtTime(volume, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        
        source.connect(gain);
        gain.connect(audioCtx.destination);
        source.start();
    } catch (e) {}
}

function playKeyClick() {
    // Simulate mechanical keyboard click
    const pitch = 800 + Math.random() * 600;
    playBeep(pitch, 'triangle', 0.05, 0.05);
    playNoise(0.03, 0.02);
}

function playChannelSwitchSound() {
    // Static snap + pop
    playNoise(0.12, 0.15);
    playBeep(120, 'square', 0.1, 0.2);
}

window.playBeep = playBeep;
window.playKeyClick = playKeyClick;
window.playChannelSwitchSound = playChannelSwitchSound;

function triggerOffline() {
    if (!isOfflineMode && !tvDismissed) {
        isOfflineMode = true;
        const tvEl = document.getElementById("offline-tv");
        if (tvEl) tvEl.style.display = "flex";
        document.body.style.overflow = "hidden"; // Prevent scrolling while TV is on
        if (typeof resetChannels === 'function') {
            resetChannels();
        }
        if (typeof window.startTvLoop === 'function') {
            window.startTvLoop();
        }
    }
}

function initOfflineTV() {
    // Listen for browser offline events
    window.addEventListener('offline', () => {
        triggerOffline();
    });
    window.addEventListener('online', () => {
        checkConnection();
    });

    // Check immediately on script load
    if (typeof navigator.onLine !== 'undefined' && !navigator.onLine) {
        triggerOffline();
    }

    // Ping the backend every 2 seconds to check if we are online
    setInterval(checkConnection, 2000);
}

async function checkConnection() {
    // If the browser reports offline, trigger immediately
    if (typeof navigator.onLine !== 'undefined' && !navigator.onLine) {
        triggerOffline();
        return;
    }

    try {
        const res = await fetch("/api/status");
        if (res.ok) {
            tvDismissed = false; // Reset dismissal when back online
            if (isOfflineMode) {
                isOfflineMode = false;
                const tvEl = document.getElementById("offline-tv");
                if (tvEl) tvEl.style.display = "none";
                document.body.style.overflow = "auto";
                const tvVideo = document.getElementById("tv-video");
                if (tvVideo) tvVideo.pause();
                clearTimeout(tvControlsTimeout);
            }
        } else {
            throw new Error("Server returned non-200");
        }
    } catch (e) {
        triggerOffline();
    }
}

let tvControlsTimeout = null;
let tvControlsHidden = false;

function showTvControls() {
    const ui = document.getElementById("tv-overlay-ui");
    if (ui) {
        ui.style.opacity = "1";
        ui.style.pointerEvents = "auto";
    }
    tvControlsHidden = false;
    resetTvControlsTimer();
}

function hideTvControls() {
    if (!isOfflineMode) return;
    const ui = document.getElementById("tv-overlay-ui");
    if (ui) {
        ui.style.opacity = "0";
        ui.style.pointerEvents = "none";
    }
    tvControlsHidden = true;
}

function resetTvControlsTimer() {
    clearTimeout(tvControlsTimeout);
    if (isOfflineMode && !tvControlsHidden) {
        tvControlsTimeout = setTimeout(hideTvControls, 3000);
    }
}

function areTvControlsHidden() {
    return tvControlsHidden;
}

window.showTvControls = showTvControls;
window.areTvControlsHidden = areTvControlsHidden;
window.resetTvControlsTimer = resetTvControlsTimer;

function dismissTv() {
    tvDismissed = true;
    isOfflineMode = false;
    document.getElementById("offline-tv").style.display = "none";
    document.body.style.overflow = "auto";
    const tvVideo = document.getElementById("tv-video");
    if (tvVideo) tvVideo.pause();
    
    clearTimeout(tvControlsTimeout);
    const ui = document.getElementById("tv-overlay-ui");
    if (ui) {
        ui.style.opacity = "1";
        ui.style.pointerEvents = "auto";
    }
    tvControlsHidden = false;
}

function watchTV() {
    // Manually open the TV overlay regardless of connectivity
    tvDismissed = false;
    isOfflineMode = true;
    document.getElementById("offline-tv").style.display = "flex";
    document.body.style.overflow = "hidden";
    if (typeof resetChannels === 'function') {
        resetChannels();
    }
    if (typeof window.startTvLoop === 'function') {
        window.startTvLoop();
    }
    showTvControls();
}

window.dismissTv = dismissTv;
window.watchTV = watchTV;

function nextChannel() {
    if (typeof tvChannel !== 'undefined' && typeof resetChannels === 'function') {
        tvChannel = (tvChannel + 1) % tvChannels.length;
        resetChannels();
    }
}

document.addEventListener("DOMContentLoaded", initOfflineTV);

// Listen for keyboard or clicks to change channel
document.addEventListener('keydown', (e) => {
    if (isOfflineMode) {
        showTvControls();
        if (e.key === 'c' || e.key === 'C') {
            nextChannel();
        }
    }
});

// For mobile taps on TV
window.addEventListener('load', () => {
    const tvContainer = document.getElementById('offline-tv');
    if (tvContainer) {
        const handleInteraction = (e) => {
            if (tvControlsHidden) {
                e.stopImmediatePropagation();
                e.preventDefault();
                showTvControls();
            } else {
                resetTvControlsTimer();
            }
        };

        // Capture phase listeners to intercept clicks/touches when controls are hidden
        tvContainer.addEventListener('click', handleInteraction, true);
        tvContainer.addEventListener('touchstart', handleInteraction, true);

        tvContainer.addEventListener('click', () => {
            if (isOfflineMode) {
                nextChannel();
            }
        });
        
        tvContainer.addEventListener('mousemove', () => {
            if (tvControlsHidden) {
                showTvControls();
            } else {
                resetTvControlsTimer();
            }
        });
    }
});
