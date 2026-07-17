// Radio & Communications Engine (Walkie-Talkie & FM Synth Radio)

// --- GLOBALS & STATE ---
const wtSenderId = 'Operator-' + Math.floor(Math.random() * 1000);
let currentWtFreq = 446.00625;
let lastWtMessageId = 0;
let wtIsTransmitting = false;
let wtMediaRecorder = null;
let wtAudioStream = null;
let wtPollInterval = null;

let wtPowerOn = false;
let wtAudioCtx = null;

// Audio queues for Walkie-Talkie
let wtAudioQueue = [];
let wtIsPlayingQueue = false;

// Chat state
let chatLastId = 0;
let chatPollInterval = null;
const chatMyName = () => (document.getElementById('wt-chat-name')?.value.trim() || wtSenderId);

// FM Synth Radio state
let fmTunedFreq = 92.4;
let fmMuted = true;
let fmVolume = 0.5;
let fmAudioCtx = null;
let fmStreamAudio = null;
let fmStreamSourceNode = null;
let fmUseProceduralFallback = false;
let fmStreamTimer = null;

// Sound synthesis nodes
let fmStaticGain = null;
let fmMusicGain = null;
let fmMasterGain = null;
let fmNoiseSource = null;

// Sequencer parameters
let fmSeqTimer = null;
let fmStep = 0;

// Morse Station Morse code sequence: "4 8 1 5 1 6 2 3 4 2"
const morseCode = [
    'dot', 'dot', 'dot', 'dot', 'dash', 'space',
    'dash', 'dash', 'dash', 'dot', 'dot', 'space',
    'dot', 'dash', 'dash', 'dash', 'dash', 'space',
    'dot', 'dot', 'dot', 'dot', 'dot', 'space',
    'dot', 'dash', 'dash', 'dash', 'dash', 'space',
    'dash', 'dot', 'dot', 'dot', 'dot', 'space',
    'dot', 'dot', 'dash', 'dash', 'dash', 'space',
    'dot', 'dot', 'dot', 'dash', 'dash', 'space',
    'dot', 'dot', 'dot', 'dot', 'dash', 'space',
    'dot', 'dot', 'dash', 'dash', 'dash', 'word_space'
];
let morseIndex = 0;

// Presets frequencies (using local CORS-bypassing proxy for live streams)
const fmStations = [
    { 
        freq: 92.4, 
        name: "ALPHA - DEF CON CYBER RADIO", 
        genre: "rap", 
        streamUrl: "/api/radio/proxy?url=" + encodeURIComponent("http://ice1.somafm.com/defcon-128-mp3") 
    },
    { 
        freq: 98.5, 
        name: "BETA - GROOVE SALAD AMBIENT", 
        genre: "pop", 
        streamUrl: "/api/radio/proxy?url=" + encodeURIComponent("http://ice1.somafm.com/groovesalad-128-mp3") 
    },
    { 
        freq: 104.2, 
        name: "GAMMA - INDIE POP ROCKS", 
        genre: "rock", 
        streamUrl: "/api/radio/proxy?url=" + encodeURIComponent("http://ice1.somafm.com/indiepop-128-mp3") 
    },
    { 
        freq: 107.9, 
        name: "DELTA - MORSE NUMBERS STATION", 
        genre: "morse" 
    }
];

// --- INITIALIZE WALKIE TALKIE ---
function initWalkieTalkie() {
    const pttBtn = document.getElementById('btn-ptt');
    if (pttBtn) {
        pttBtn.style.opacity = '0.4';
        pttBtn.style.pointerEvents = 'none';
        
        pttBtn.addEventListener('mousedown', startTransmission);
        pttBtn.addEventListener('mouseup', stopTransmission);
        pttBtn.addEventListener('mouseleave', stopTransmission);
        
        pttBtn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            startTransmission();
        });
        pttBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            stopTransmission();
        });
    }
    
    // Set initial LCD screen state to powered off
    setWtState('OFF', 'SYSTEM STANDBY - POWER OFF');
}

function toggleWtPower() {
    const pttBtn = document.getElementById('btn-ptt');
    const powerBtn = document.getElementById('btn-wt-power');
    
    if (!wtPowerOn) {
        wtPowerOn = true;
        lastWtMessageId = 0; // Reset so server restarts don't cause stale-ID freeze
        
        // Unlock Web Audio Context for Safari
        try {
            wtAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const buffer = wtAudioCtx.createBuffer(1, 1, 22050);
            const source = wtAudioCtx.createBufferSource();
            source.buffer = buffer;
            source.connect(wtAudioCtx.destination);
            source.start(0);
        } catch(e) {
            console.warn("Could not init audio context:", e);
        }
        
        if (pttBtn) {
            pttBtn.style.opacity = '1';
            pttBtn.style.pointerEvents = 'auto';
        }
        
        if (powerBtn) {
            powerBtn.textContent = '🔌 TURN RADIO OFF';
            powerBtn.style.background = 'var(--cyan)';
            powerBtn.style.color = '#000';
        }
        
        setWtState('STANDBY', 'REQUESTING MIC ACCESS...');
        playWtBeep(880, 0.15); // Startup chime
        
        // Pre-request microphone permission and show result on LCD
        (async () => {
            try {
                const testStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                testStream.getTracks().forEach(t => t.stop()); // release immediately
                setWtState('STANDBY', 'MIC OK — ONLINE DUAL-BAND TRANSCEIVER');
            } catch (e) {
                setWtState('STANDBY', 'MIC DENIED: ' + (e.name || e.message));
                showToast('Microphone blocked: ' + (e.name || e.message), 'error', 6000);
            }
        })();
        
        startWtReceiver();
        
        // Show chat panel and start polling
        const chatPanel = document.getElementById('wt-chat-panel');
        if (chatPanel) chatPanel.style.display = 'block';
        startChatPoller();
    } else {
        wtPowerOn = false;
        
        if (pttBtn) {
            pttBtn.style.opacity = '0.4';
            pttBtn.style.pointerEvents = 'none';
        }
        
        if (powerBtn) {
            powerBtn.textContent = '🔌 TURN RADIO ON';
            powerBtn.style.background = '#333';
            powerBtn.style.color = '#fff';
        }
        
        if (wtPollInterval) {
            clearInterval(wtPollInterval);
            wtPollInterval = null;
        }
        
        // Stop chat poll and hide panel
        if (chatPollInterval) {
            clearInterval(chatPollInterval);
            chatPollInterval = null;
        }
        const chatPanel = document.getElementById('wt-chat-panel');
        if (chatPanel) chatPanel.style.display = 'none';
        
        setWtState('OFF', 'SYSTEM STANDBY - POWER OFF');
        playWtBeep(440, 0.2); // Shutdown chime
    }
}
window.toggleWtPower = toggleWtPower;

function updateWtFrequency(val) {
    currentWtFreq = parseFloat(val);
    const lcdFreq = document.getElementById('wt-lcd-freq');
    if (lcdFreq) {
        let chNum = 1;
        if (currentWtFreq === 446.01875) chNum = 2;
        else if (currentWtFreq === 446.03125) chNum = 3;
        else if (currentWtFreq === 446.04375) chNum = 4;
        lcdFreq.innerHTML = `CH ${chNum} <span style="font-size:14px;">${currentWtFreq.toFixed(3)} MHz</span>`;
    }
    
    wtAudioQueue = [];
    chatLastId = 0;
    const log = document.getElementById('wt-chat-log');
    if (log) log.innerHTML = '<div style="color:#333; text-align:center; margin:auto;">No messages yet on this channel</div>';
    playFmStaticClick();
}

function setWtState(state, info = "") {
    const led = document.getElementById('wt-status-led');
    const stateEl = document.getElementById('wt-lcd-state');
    const infoEl = document.getElementById('wt-lcd-info');
    
    if (!led || !stateEl) return;
    
    stateEl.textContent = state;
    if (info) infoEl.textContent = info;
    
    if (state === 'TRANSMITTING') {
        led.style.background = '#ff0033';
        led.style.boxShadow = '0 0 10px #ff0033';
        stateEl.style.background = '#5c0c16';
        stateEl.style.color = '#fff';
    } else if (state === 'RECEIVING') {
        led.style.background = '#39ff14';
        led.style.boxShadow = '0 0 10px #39ff14';
        stateEl.style.background = '#113a1a';
        stateEl.style.color = '#39ff14';
    } else {
        led.style.background = '#444';
        led.style.boxShadow = 'none';
        stateEl.style.background = '#113a1a';
        stateEl.style.color = '#39ff14';
        infoEl.textContent = 'ONLINE DUAL-BAND TRANSCEIVER';
    }
}

let wtChunks = [];

async function startTransmission() {
    if (!wtPowerOn) return;
    if (wtIsTransmitting) return;
    wtIsTransmitting = true;
    
    if (wtAudioCtx && wtAudioCtx.state === 'suspended') {
        wtAudioCtx.resume().catch(() => {});
    }
    
    playWtBeep(1200, 0.08);
    setWtState('TRANSMITTING', 'CAPTURING MICROPHONE...');
    
    try {
        wtAudioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        let mimeType = 'audio/webm;codecs=opus';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'audio/webm';
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'audio/ogg';
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'audio/mp4';
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = '';
        }
        
        wtMediaRecorder = new MediaRecorder(wtAudioStream, mimeType ? { mimeType } : undefined);
        
        wtChunks = [];
        wtMediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
                wtChunks.push(e.data);
            }
        };
        
        wtMediaRecorder.onstop = async () => {
            if (wtChunks.length > 0) {
                const recordedMimeType = wtMediaRecorder.mimeType || mimeType || 'audio/webm';
                const blob = new Blob(wtChunks, { type: recordedMimeType });
                const reader = new FileReader();
                reader.readAsDataURL(blob);
                reader.onloadend = async () => {
                    const base64Audio = reader.result.split(',')[1];
                    broadcastWtChunk(base64Audio, recordedMimeType);
                };
            }
        };
        
        if (mimeType && mimeType.includes('mp4')) {
            wtMediaRecorder.start();
        } else {
            wtMediaRecorder.start(100);
        }
        
    } catch (err) {
        console.error("PTT capture failed", err);
        const errDetail = err.name ? `${err.name}: ${err.message}` : String(err);
        setWtState('STANDBY', 'MIC ERR: ' + errDetail.substring(0, 40));
        wtIsTransmitting = false;
        showToast('PTT failed: ' + errDetail, 'error', 6000);
    }
}

function stopTransmission() {
    if (!wtIsTransmitting) return;
    wtIsTransmitting = false;
    
    setWtState('STANDBY', 'TRANSMISSION ENDED');
    
    if (wtMediaRecorder && wtMediaRecorder.state !== 'inactive') {
        try {
            wtMediaRecorder.stop();
        } catch(e){}
    }
    
    if (wtAudioStream) {
        wtAudioStream.getTracks().forEach(track => track.stop());
        wtAudioStream = null;
    }
    
    playWtSquelch();
}

async function broadcastWtChunk(base64Audio, mimeType) {
    try {
        await fetch('/api/walkie-talkie/broadcast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                frequency: currentWtFreq,
                audio: base64Audio,
                mime_type: mimeType,
                sender: wtSenderId
            })
        });
    } catch (e) {
        console.warn("Broadcast chunk failed", e);
    }
}

function startWtReceiver() {
    if (wtPollInterval) clearInterval(wtPollInterval);
    
    wtPollInterval = setInterval(async () => {
        if (wtIsTransmitting) return;
        
        try {
            const res = await fetch(`/api/walkie-talkie/receive?last_id=${lastWtMessageId}&frequency=${currentWtFreq}`);
            const data = await res.json();
            
            // If server counter reset (restart), reset our local ID too
            if (data.counter !== undefined && lastWtMessageId > data.counter) {
                lastWtMessageId = 0;
            }
            
            if (data.ok && data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    if (msg.id > lastWtMessageId) {
                        lastWtMessageId = msg.id;
                    }
                    if (msg.sender !== wtSenderId) {
                        wtAudioQueue.push({
                            audio: msg.audio,
                            mimeType: msg.mime_type || 'audio/webm'
                        });
                    }
                });
                
                if (wtAudioQueue.length > 0 && !wtIsPlayingQueue) {
                    playNextWtChunk();
                }
            }
        } catch (e) {
        }
    }, 400);
}

function playNextWtChunk() {
    if (wtAudioQueue.length === 0) {
        wtIsPlayingQueue = false;
        setWtState('STANDBY');
        return;
    }
    wtIsPlayingQueue = true;
    setWtState('RECEIVING', 'DECODING VOICE INCOMING...');
    const chunk = wtAudioQueue.shift();
    const base64Data = chunk.audio;
    const mimeType = chunk.mimeType;
    
    try {
        const binaryString = atob(base64Data);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        
        // Use a copy of the buffer because decodeAudioData neuters/consumes the ArrayBuffer
        const bufferCopy = bytes.buffer.slice(0);
        
        if (wtAudioCtx && typeof wtAudioCtx.decodeAudioData === 'function') {
            wtAudioCtx.decodeAudioData(bufferCopy, (audioBuffer) => {
                const source = wtAudioCtx.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(wtAudioCtx.destination);
                source.onended = () => {
                    playNextWtChunk();
                };
                source.start(0);
            }, (err) => {
                console.warn("decodeAudioData failed, falling back to legacy Audio element:", err);
                playHtml5AudioFallback(bytes.buffer, mimeType);
            });
        } else {
            playHtml5AudioFallback(bytes.buffer, mimeType);
        }
    } catch(e) {
        console.error("WT playback error:", e);
        playNextWtChunk();
    }
}

function playHtml5AudioFallback(arrayBuffer, mimeType) {
    try {
        const blob = new Blob([arrayBuffer], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => {
            URL.revokeObjectURL(url);
            playNextWtChunk();
        };
        audio.onerror = () => {
            URL.revokeObjectURL(url);
            playNextWtChunk();
        };
        audio.play().catch(e => {
            URL.revokeObjectURL(url);
            playNextWtChunk();
        });
    } catch(e) {
        playNextWtChunk();
    }
}

function playWtBeep(freq, dur) {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + dur);
    
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + dur);
}

function playWtSquelch() {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const bufferSize = audioCtx.sampleRate * 0.15;
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
    }
    
    const noise = audioCtx.createBufferSource();
    noise.buffer = buffer;
    
    const filter = audioCtx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(1000, audioCtx.currentTime);
    
    const gain = audioCtx.createGain();
    gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);
    
    noise.connect(filter);
    filter.connect(gain);
    gain.connect(audioCtx.destination);
    
    noise.start();
    noise.stop(audioCtx.currentTime + 0.15);
}


// --- FM RADIO SYNTHESIS ENGINE ---
function initFmAudio() {
    if (fmAudioCtx) {
        if (fmAudioCtx.state === 'suspended') {
            fmAudioCtx.resume().catch(e => {});
        }
        return;
    }
    
    fmAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    fmMasterGain = fmAudioCtx.createGain();
    fmMasterGain.gain.setValueAtTime(fmVolume, fmAudioCtx.currentTime);
    fmMasterGain.connect(fmAudioCtx.destination);
    
    fmStaticGain = fmAudioCtx.createGain();
    fmStaticGain.connect(fmMasterGain);
    
    fmMusicGain = fmAudioCtx.createGain();
    fmMusicGain.connect(fmMasterGain);
    
    const bufferSize = fmAudioCtx.sampleRate * 2;
    const buffer = fmAudioCtx.createBuffer(1, bufferSize, fmAudioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
    }
    
    fmNoiseSource = fmAudioCtx.createBufferSource();
    fmNoiseSource.buffer = buffer;
    fmNoiseSource.loop = true;
    
    const filter = fmAudioCtx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(1200, fmAudioCtx.currentTime);
    filter.Q.setValueAtTime(1.0, fmAudioCtx.currentTime);
    
    fmNoiseSource.connect(filter);
    filter.connect(fmStaticGain);
    fmNoiseSource.start();

    // Create a hidden HTML5 audio element and route it into the Web Audio graph
    if (!fmStreamAudio) {
        fmStreamAudio = new Audio();
        fmStreamAudio.crossOrigin = "anonymous";
        fmStreamAudio.addEventListener('error', (e) => {
            console.warn("FM Audio Stream failed to load, falling back to 8-bit synth.", e);
            fmUseProceduralFallback = true;
            updateFmVolumeLevels();
        });
        fmStreamSourceNode = fmAudioCtx.createMediaElementSource(fmStreamAudio);
        fmStreamSourceNode.connect(fmMusicGain);
    }
    
    updateFmVolumeLevels();
    startFmSequencer();
}

function updateFmVolumeLevels() {
    if (!fmAudioCtx) return;
    
    if (fmMuted) {
        fmMasterGain.gain.setValueAtTime(0, fmAudioCtx.currentTime);
        if (fmStreamAudio && !fmStreamAudio.paused) {
            fmStreamAudio.pause();
        }
        return;
    }
    
    fmMasterGain.gain.setValueAtTime(fmVolume, fmAudioCtx.currentTime);
    
    let minDistance = 999.0;
    let nearestStation = null;
    
    fmStations.forEach(st => {
        const dist = Math.abs(fmTunedFreq - st.freq);
        if (dist < minDistance) {
            minDistance = dist;
            nearestStation = st;
        }
    });
    
    let staticVol = 0.3;
    let musicVol = 0.0;
    
    if (minDistance < 0.5) {
        const ratio = minDistance / 0.5;
        staticVol = ratio * 0.3;
        musicVol = 1.0 - ratio;
    }
    
    fmStaticGain.gain.setTargetAtTime(staticVol, fmAudioCtx.currentTime, 0.1);
    fmMusicGain.gain.setTargetAtTime(musicVol * 0.25, fmAudioCtx.currentTime, 0.1);
    
    const stationLabel = document.getElementById('fm-lcd-station');
    
    if (minDistance < 0.2 && nearestStation) {
        if (nearestStation.streamUrl) {
            if (!navigator.onLine) {
                fmUseProceduralFallback = true;
            }
            if (!fmUseProceduralFallback) {
                if (fmStreamAudio && fmStreamAudio.src !== nearestStation.streamUrl) {
                    if (fmStreamTimer) clearTimeout(fmStreamTimer);
                    fmStreamAudio.src = nearestStation.streamUrl;
                    fmStreamAudio.load();
                    if (stationLabel) {
                        stationLabel.textContent = "BUFFERING LIVE FEED...";
                        stationLabel.style.color = '#ffcc00';
                    }
                    fmStreamAudio.play().then(() => {
                        const lbl = document.getElementById('fm-lcd-station');
                        if (lbl && fmStreamAudio.src === nearestStation.streamUrl) {
                            lbl.textContent = nearestStation.name + " (LIVE)";
                            lbl.style.color = 'var(--cyan)';
                        }
                    }).catch(err => {
                        console.log("Stream play blocked or failed:", err);
                    });
                    fmStreamTimer = setTimeout(() => {
                        if (fmStreamAudio.paused || fmStreamAudio.currentTime === 0) {
                            fmUseProceduralFallback = true;
                            const lbl = document.getElementById('fm-lcd-station');
                            if (lbl) {
                                lbl.textContent = nearestStation.name + " (SYNTH BACKUP)";
                                lbl.style.color = 'var(--cyan)';
                            }
                        }
                    }, 3500);
                } else if (fmStreamAudio && fmStreamAudio.paused) {
                    fmStreamAudio.play().catch(e => {});
                    if (stationLabel) {
                        stationLabel.textContent = nearestStation.name + " (LIVE)";
                        stationLabel.style.color = 'var(--cyan)';
                    }
                } else {
                    if (stationLabel) {
                        stationLabel.textContent = nearestStation.name + " (LIVE)";
                        stationLabel.style.color = 'var(--cyan)';
                    }
                }
            } else {
                if (stationLabel) {
                    stationLabel.textContent = nearestStation.name + " (SYNTH BACKUP)";
                    stationLabel.style.color = 'var(--cyan)';
                }
            }
        } else {
            // Morse numbers station
            if (fmStreamAudio && !fmStreamAudio.paused) {
                fmStreamAudio.pause();
                fmStreamAudio.src = "";
            }
            if (stationLabel) {
                stationLabel.textContent = nearestStation.name;
                stationLabel.style.color = 'var(--cyan)';
            }
        }
    } else {
        // Tuned to static noise
        if (fmStreamAudio && !fmStreamAudio.paused) {
            fmStreamAudio.pause();
            fmStreamAudio.src = "";
        }
        if (fmStreamTimer) {
            clearTimeout(fmStreamTimer);
            fmStreamTimer = null;
        }
        fmUseProceduralFallback = false;
        if (stationLabel) {
            stationLabel.textContent = "TUNING - STATIC STATS";
            stationLabel.style.color = '#555';
        }
    }
}

function tuneFmRadio(val) {
    fmTunedFreq = parseFloat(val);
    
    const lcdFreq = document.getElementById('fm-lcd-freq');
    const needle = document.getElementById('fm-needle');
    
    if (lcdFreq) lcdFreq.textContent = `${fmTunedFreq.toFixed(1)} MHz`;
    
    if (needle) {
        const percent = ((fmTunedFreq - 88.0) / (108.0 - 88.0)) * 90 + 5;
        needle.style.left = `${percent}%`;
    }
    
    initFmAudio();
    if (fmAudioCtx && fmAudioCtx.state === 'suspended') {
        fmAudioCtx.resume().catch(e => {});
    }
    updateFmVolumeLevels();
}

function setFmPreset(freq) {
    const slider = document.getElementById('fm-tuner-slider');
    if (slider) slider.value = freq;
    tuneFmRadio(freq);
}

function toggleFmMute() {
    fmMuted = !fmMuted;
    const muteBtn = document.getElementById('btn-fm-mute');
    if (muteBtn) {
        muteBtn.textContent = fmMuted ? "🔇 UNMUTE AUDIO" : "🔊 MUTE AUDIO";
        muteBtn.style.borderColor = fmMuted ? '#ff0033' : 'var(--cyan)';
        muteBtn.style.color = fmMuted ? '#ff0033' : 'var(--cyan)';
    }
    
    initFmAudio();
    if (fmAudioCtx && fmAudioCtx.state === 'suspended') {
        fmAudioCtx.resume().catch(e => {});
    }
    updateFmVolumeLevels();
}

function setFmVolume(val) {
    fmVolume = parseFloat(val);
    updateFmVolumeLevels();
}

function playFmStaticClick() {
    if (!fmAudioCtx || fmMuted) return;
    const osc = fmAudioCtx.createOscillator();
    const gain = fmAudioCtx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(100, fmAudioCtx.currentTime);
    osc.frequency.linearRampToValueAtTime(1, fmAudioCtx.currentTime + 0.05);
    gain.gain.setValueAtTime(0.08, fmAudioCtx.currentTime);
    gain.gain.linearRampToValueAtTime(0.001, fmAudioCtx.currentTime + 0.05);
    osc.connect(gain);
    gain.connect(fmMasterGain);
    osc.start();
    osc.stop(fmAudioCtx.currentTime + 0.05);
}


// --- PROCEDURAL MUSIC SEQUENCER ---
function startFmSequencer() {
    if (fmSeqTimer) clearInterval(fmSeqTimer);
    
    fmSeqTimer = setInterval(() => {
        if (!fmAudioCtx || fmMuted) return;
        
        let minDistance = 999.0;
        let activeSt = null;
        
        fmStations.forEach(st => {
            const dist = Math.abs(fmTunedFreq - st.freq);
            if (dist < minDistance) {
                minDistance = dist;
                activeSt = st;
            }
        });
        
        if (minDistance < 0.2) {
            // Only trigger 8-bit procedural notes if it's the Morse station or if live stream failed
            if (!activeSt.streamUrl || fmUseProceduralFallback) {
                triggerFmSynthStep(activeSt.genre);
            }
            animateVisualizerBar();
        } else {
            resetVisualizerBars();
        }
        
        fmStep = (fmStep + 1) % 16;
    }, 140);
}

function animateVisualizerBar() {
    const bars = document.querySelectorAll('.vis-bar');
    bars.forEach(bar => {
        const height = 3 + Math.floor(Math.random() * 15);
        bar.style.height = `${height}px`;
    });
}

function resetVisualizerBars() {
    const bars = document.querySelectorAll('.vis-bar');
    bars.forEach(bar => {
        bar.style.height = `3px`;
    });
}

function triggerFmSynthStep(genre) {
    if (!fmAudioCtx) return;
    
    const now = fmAudioCtx.currentTime;
    
    if (genre === 'rap') {
        const bassScale = [110.0, 110.0, 130.8, 146.8, 130.8, 164.8, 146.8, 110.0];
        const synthScale = [440.0, 523.25, 587.33, 659.25, 783.99, 880.0];
        
        if (fmStep % 4 === 0) {
            playSynthKick(now);
        }
        if (fmStep % 8 === 4) {
            playSynthSnare(now);
        }
        if (fmStep % 2 !== 0) {
            playSynthHihat(now);
        }
        if (fmStep % 2 === 0) {
            const note = bassScale[(fmStep / 2) % bassScale.length];
            playSynthNote('triangle', note, 0.12, 0.08, now);
        }
        if (fmStep % 4 === 2) {
            const note = synthScale[Math.floor(Math.random() * synthScale.length)];
            playSynthNote('square', note, 0.10, 0.04, now);
        }
    } 
    else if (genre === 'pop') {
        const chords = [
            [261.63, 329.63, 392.00],
            [196.00, 246.94, 293.66],
            [220.00, 261.63, 329.63],
            [174.61, 220.00, 261.63]
        ];
        
        const popMelody = [523.25, 587.33, 659.25, 783.99, 880.0, 987.77, 1046.50];
        
        if (fmStep % 4 === 0) {
            playSynthKick(now);
        }
        if (fmStep % 8 === 4) {
            playSynthSnare(now);
        }
        const chordIdx = Math.floor(fmStep / 4) % chords.length;
        const chord = chords[chordIdx];
        const note = chord[fmStep % 3];
        playSynthNote('triangle', note, 0.12, 0.05, now);
        
        if (fmStep % 2 === 0 && Math.random() > 0.3) {
            const leadNote = popMelody[Math.floor(Math.random() * popMelody.length)];
            playSynthNote('sawtooth', leadNote, 0.15, 0.03, now);
        }
    } 
    else if (genre === 'rock') {
        const bassNotes = [146.83, 146.83, 164.81, 196.00, 196.00, 174.61, 146.83, 110.0];
        
        if (fmStep === 0 || fmStep === 2 || fmStep === 8 || fmStep === 10) {
            playSynthKick(now);
        }
        if (fmStep === 4 || fmStep === 12) {
            playSynthSnare(now);
        }
        playSynthHihat(now);
        
        if (fmStep % 4 === 0) {
            const bass = bassNotes[Math.floor(fmStep / 2) % bassNotes.length];
            playSynthNote('sawtooth', bass, 0.30, 0.10, now);
            playSynthNote('sawtooth', bass * 1.5, 0.30, 0.08, now);
        }
        
        if (fmStep % 2 !== 0) {
            const soloNotes = [587.33, 698.46, 783.99, 880.0, 1046.50, 1174.66];
            const note = soloNotes[Math.floor(Math.random() * soloNotes.length)];
            playSynthNote('square', note, 0.10, 0.05, now);
        }
    } 
    else if (genre === 'morse') {
        if (fmStep === 0) {
            playSynthNote('triangle', 55.0, 2.2, 0.1, now);
            playSynthNote('triangle', 55.6, 2.2, 0.1, now);
        }
        
        const morseVal = morseCode[morseIndex];
        
        if (morseVal === 'dot') {
            playMorseTone(0.08, now);
        } else if (morseVal === 'dash') {
            playMorseTone(0.24, now);
        }
        
        if (fmStep % 2 === 0) {
            morseIndex = (morseIndex + 1) % morseCode.length;
        }
    }
}

function playSynthNote(type, freq, duration, gainVal, time) {
    const osc = fmAudioCtx.createOscillator();
    const gain = fmAudioCtx.createGain();
    
    osc.type = type;
    osc.frequency.setValueAtTime(freq, time);
    
    gain.gain.setValueAtTime(gainVal, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + duration);
    
    osc.connect(gain);
    gain.connect(fmMusicGain);
    
    osc.start(time);
    osc.stop(time + duration);
}

function playMorseTone(dur, time) {
    const osc = fmAudioCtx.createOscillator();
    const gain = fmAudioCtx.createGain();
    
    osc.type = 'sine';
    osc.frequency.setValueAtTime(800, time);
    
    gain.gain.setValueAtTime(0.12, time);
    gain.gain.setValueAtTime(0.12, time + dur - 0.01);
    gain.gain.linearRampToValueAtTime(0, time + dur);
    
    osc.connect(gain);
    gain.connect(fmMusicGain);
    
    osc.start(time);
    osc.stop(time + dur);
}

function playSynthKick(time) {
    const osc = fmAudioCtx.createOscillator();
    const gain = fmAudioCtx.createGain();
    
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(140, time);
    osc.frequency.exponentialRampToValueAtTime(30, time + 0.12);
    
    gain.gain.setValueAtTime(0.35, time);
    gain.gain.linearRampToValueAtTime(0.001, time + 0.12);
    
    osc.connect(gain);
    gain.connect(fmMusicGain);
    
    osc.start(time);
    osc.stop(time + 0.12);
}

function playSynthSnare(time) {
    const bufferSize = fmAudioCtx.sampleRate * 0.12;
    const buffer = fmAudioCtx.createBuffer(1, bufferSize, fmAudioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
    }
    
    const noise = fmAudioCtx.createBufferSource();
    noise.buffer = buffer;
    
    const filter = fmAudioCtx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(1000, time);
    
    const gain = fmAudioCtx.createGain();
    gain.gain.setValueAtTime(0.12, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.12);
    
    noise.connect(filter);
    filter.connect(gain);
    gain.connect(fmMusicGain);
    
    noise.start(time);
    noise.stop(time + 0.12);
}

function playSynthHihat(time) {
    const osc = fmAudioCtx.createOscillator();
    const gain = fmAudioCtx.createGain();
    
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(10000, time);
    
    gain.gain.setValueAtTime(0.03, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.04);
    
    osc.connect(gain);
    gain.connect(fmMusicGain);
    
    osc.start(time);
    osc.stop(time + 0.04);
}

// ══════════════════════════════════════════════════════════════════
// CHANNEL CHAT — relay text messages over LAN (zero internet)
// ══════════════════════════════════════════════════════════════════

function getChatChannel() {
    const sel = document.getElementById('wt-frequency');
    if (!sel) return '1';
    const idx = sel.selectedIndex;
    return String(idx + 1); // ch1..ch4 mapped to frequency index
}

function appendChatMessage(msg, isSelf) {
    const log = document.getElementById('wt-chat-log');
    if (!log) return;

    // Clear placeholder
    const placeholder = log.querySelector('[data-placeholder]');
    if (placeholder) placeholder.remove();
    const noMsg = [...log.children].find(c => c.textContent === 'No messages yet on this channel');
    if (noMsg) noMsg.remove();

    const ts = new Date(msg.timestamp * 1000);
    const timeStr = ts.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

    const bubble = document.createElement('div');
    bubble.style.cssText = `
        max-width:85%; padding:7px 10px; border-radius:8px; word-break:break-word;
        line-height:1.4; position:relative;
        ${isSelf
            ? 'align-self:flex-end; background:rgba(255,0,234,0.2); border:1px solid rgba(255,0,234,0.4); color:#fff;'
            : 'align-self:flex-start; background:rgba(0,212,255,0.1); border:1px solid rgba(0,212,255,0.25); color:#e0e0e0;'}
    `;
    bubble.innerHTML = `
        <div style="font-size:10px; color:${isSelf ? '#ff88f0' : '#66d4ff'}; font-weight:700; margin-bottom:3px;">
            ${isSelf ? '📤 ' : '📥 '}${escapeHtml(msg.sender)}
            <span style="color:#555; font-weight:400; margin-left:6px;">${timeStr}</span>
        </div>
        <div style="font-size:13px;">${escapeHtml(msg.text)}</div>
    `;
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
}

function escapeHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function sendChatMessage() {
    const input = document.getElementById('wt-chat-input');
    const text = input?.value.trim();
    if (!text) return;

    const sender = chatMyName();
    const channel = getChatChannel();

    // Optimistically append own message
    appendChatMessage({ sender, text, timestamp: Date.now() / 1000 }, true);
    input.value = '';

    try {
        const res = await fetch('/api/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, sender, channel })
        });
        const data = await res.json();
        if (data.ok) {
            // advance lastId so we don't echo back our own message
            if (data.id > chatLastId) chatLastId = data.id;
        }
    } catch (e) {
        showToast('Chat send failed: ' + e.message, 'error');
    }
}
window.sendChatMessage = sendChatMessage;

function startChatPoller() {
    if (chatPollInterval) clearInterval(chatPollInterval);
    chatPollInterval = setInterval(async () => {
        if (!wtPowerOn) return;
        const channel = getChatChannel();
        try {
            const res = await fetch(`/api/chat/poll?last_id=${chatLastId}&channel=${channel}`);
            const data = await res.json();
            if (data.ok && data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    if (msg.id > chatLastId) chatLastId = msg.id;
                    // Only show messages from others (own messages shown optimistically)
                    if (msg.sender !== chatMyName()) {
                        appendChatMessage(msg, false);
                        // Quick beep to signal incoming message
                        try {
                            const ctx = wtAudioCtx || new (window.AudioContext || window.webkitAudioContext)();
                            const o = ctx.createOscillator();
                            const g = ctx.createGain();
                            o.frequency.value = 1200;
                            g.gain.setValueAtTime(0.08, ctx.currentTime);
                            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
                            o.connect(g); g.connect(ctx.destination);
                            o.start(); o.stop(ctx.currentTime + 0.12);
                        } catch(e) {}
                    }
                });
            }
        } catch(e) {
            // Silently ignore offline poll failures
        }
    }, 1500); // poll every 1.5 seconds
}

document.addEventListener('DOMContentLoaded', () => {
    initWalkieTalkie();
    const slider = document.getElementById('fm-tuner-slider');
    if (slider) {
        tuneFmRadio(slider.value);
    }
});
