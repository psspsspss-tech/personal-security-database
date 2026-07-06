// 8-Bit Offline TV Main Controller
const tvChannels = [
    { type: 'matrix', title: 'Matrix Rain' },
    { type: 'snake', title: 'Snake Game' },
    { type: 'hacker', title: 'Hacker Terminal' }
];

var isOfflineMode = false;
var tvDismissed = false;
var tvManualMode = false;

// --- WEB AUDIO SYNTHESIZER ---
let tvAudioCtx = null;
let humOsc = null;
let humGain = null;
let staticNode = null;
let staticGain = null;

function initAudio() {
    if (tvAudioCtx) return;
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        tvAudioCtx = new AudioCtx();
        
        // 1. Low ambient hum
        humOsc = tvAudioCtx.createOscillator();
        humGain = tvAudioCtx.createGain();
        humOsc.type = 'sawtooth';
        humOsc.frequency.setValueAtTime(55, tvAudioCtx.currentTime); // Low A
        humGain.gain.setValueAtTime(0.015, tvAudioCtx.currentTime);
        
        // Filter out high harsh frequencies from the hum
        const filter = tvAudioCtx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(100, tvAudioCtx.currentTime);

        humOsc.connect(filter);
        filter.connect(humGain);
        humGain.connect(tvAudioCtx.destination);
        humOsc.start();
        
        // 2. White noise generator for static effect
        const bufferSize = 2 * tvAudioCtx.sampleRate;
        const noiseBuffer = tvAudioCtx.createBuffer(1, bufferSize, tvAudioCtx.sampleRate);
        const output = noiseBuffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            output[i] = Math.random() * 2 - 1;
        }
        
        staticNode = tvAudioCtx.createBufferSource();
        staticNode.buffer = noiseBuffer;
        staticNode.loop = true;
        
        staticGain = tvAudioCtx.createGain();
        staticGain.gain.setValueAtTime(0.008, tvAudioCtx.currentTime);
        
        const staticFilter = tvAudioCtx.createBiquadFilter();
        staticFilter.type = 'bandpass';
        staticFilter.frequency.setValueAtTime(800, tvAudioCtx.currentTime);
        staticFilter.Q.setValueAtTime(1.0, tvAudioCtx.currentTime);
        
        staticNode.connect(staticFilter);
        staticFilter.connect(staticGain);
        staticGain.connect(tvAudioCtx.destination);
        staticNode.start();
    } catch (err) {
        console.warn('Web Audio API not supported or blocked:', err);
    }
}

function resumeAudio() {
    if (tvAudioCtx && tvAudioCtx.state === 'suspended') {
        tvAudioCtx.resume();
    }
}

function playBeep(freq, type, duration, volume = 0.1) {
    if (!tvAudioCtx) return;
    resumeAudio();
    try {
        const osc = tvAudioCtx.createOscillator();
        const gain = tvAudioCtx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, tvAudioCtx.currentTime);
        gain.gain.setValueAtTime(volume, tvAudioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, tvAudioCtx.currentTime + duration);
        
        osc.connect(gain);
        gain.connect(tvAudioCtx.destination);
        osc.start();
        osc.stop(tvAudioCtx.currentTime + duration);
    } catch (e) {}
}

function playNoise(duration, volume = 0.1) {
    if (!tvAudioCtx) return;
    resumeAudio();
    try {
        const bufferSize = tvAudioCtx.sampleRate * duration;
        const buffer = tvAudioCtx.createBuffer(1, bufferSize, tvAudioCtx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }
        const source = tvAudioCtx.createBufferSource();
        source.buffer = buffer;
        
        const gain = tvAudioCtx.createGain();
        gain.gain.setValueAtTime(volume, tvAudioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, tvAudioCtx.currentTime + duration);
        
        source.connect(gain);
        gain.connect(tvAudioCtx.destination);
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
            // Only auto-close if we are not in manual override mode
            if (isOfflineMode && !tvManualMode) {
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
    tvManualMode = false; // Reset manual override mode
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
    tvManualMode = true; // Enable manual override mode
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

function setupTvInteractions() {
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

    // Add manual trigger click listener to status indicator badge in the dashboard header
    const statusIndicator = document.getElementById('status-indicator');
    if (statusIndicator) {
        statusIndicator.style.cursor = 'pointer';
        const triggerHandler = (e) => {
            e.stopPropagation();
            e.preventDefault();
            if (typeof watchTV === 'function') {
                watchTV();
            }
        };
        statusIndicator.addEventListener('click', triggerHandler);
        statusIndicator.addEventListener('touchstart', triggerHandler, {passive: true});
    }
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initOfflineTV);
} else {
    initOfflineTV();
}

if (document.readyState === 'complete') {
    setupTvInteractions();
} else {
    window.addEventListener('load', setupTvInteractions);
}

// Listen for keyboard to change channel
document.addEventListener('keydown', (e) => {
    if (isOfflineMode) {
        showTvControls();
        if (e.key === 'c' || e.key === 'C') {
            nextChannel();
        }
    }
});
