// Cyber Casino - Gamba+ Cyber Slots Engine
const gCanvas = document.getElementById("gamba-canvas");
const gCtx = gCanvas ? gCanvas.getContext("2d") : null;

// Symbols config
const slotSymbols = [
    { char: "🎰", label: "SEVEN", mult: 20, color: "#ffcc00" },
    { char: "💀", label: "SKULL", mult: 50, color: "#ff3366" },
    { char: "🚀", label: "ROCKET", mult: 10, color: "#33ccff" },
    { char: "💎", label: "DIAMOND", mult: 15, color: "#00ffcc" },
    { char: "🛡️", label: "SHIELD", mult: 5, color: "#bb86fc" },
    { char: "🔋", label: "BATTERY", mult: 3, color: "#00e699" },
    { char: "🍒", label: "CHERRY", mult: 2, color: "#ff4444" }
];

// Reels state
let reels = [
    { y: 0, targetY: 0, speed: 0, symbols: [], spinning: false, decelerating: false },
    { y: 0, targetY: 0, speed: 0, symbols: [], spinning: false, decelerating: false },
    { y: 0, targetY: 0, speed: 0, symbols: [], spinning: false, decelerating: false }
];

let isGambaSpinning = false;
let gambaWinParticles = [];
let animGambaFrame;
let gambaTimeouts = [];

const SYMBOL_HEIGHT = 80;
const REEL_WIDTH = 120;
const REEL_GAP = 20;
const VISIBLE_ROWS = 3;

function initGamba() {
    if (!gCanvas) return;
    
    // Set fixed logical size for drawing
    gCanvas.width = 450;
    gCanvas.height = 280;
    
    // Populate reels with random symbols initially
    for (let r = 0; r < 3; r++) {
        reels[r].symbols = [];
        for (let i = 0; i < 20; i++) {
            reels[r].symbols.push(Math.floor(Math.random() * slotSymbols.length));
        }
        reels[r].y = 0;
    }
    
    drawGamba();
}

function resizeGambaCanvas() {
    // Keep it responsive via CSS max-width, internal resolution stays at 450x280
    drawGamba();
}
window.resizeGambaCanvas = resizeGambaCanvas;

// Web Audio API Sound Synthesizer (No assets needed!)
let audioCtx = null;
function playGambaSound(type) {
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        
        if (type === 'spin') {
            // Whoosh sweep sound
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(100, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(800, audioCtx.currentTime + 0.5);
            gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.5);
        } else if (type === 'stop') {
            // Clunk bump sound
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(150, audioCtx.currentTime);
            osc.frequency.setValueAtTime(80, audioCtx.currentTime + 0.05);
            gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.12);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.12);
        } else if (type === 'win') {
            // Upward melody beeps
            const now = audioCtx.currentTime;
            osc.type = 'square';
            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
            
            osc.frequency.setValueAtTime(261.6, now); // C4
            osc.frequency.setValueAtTime(329.6, now + 0.1); // E4
            osc.frequency.setValueAtTime(392.0, now + 0.2); // G4
            osc.frequency.setValueAtTime(523.3, now + 0.3); // C5
            
            osc.start();
            osc.stop(now + 0.45);
        } else if (type === 'jackpot') {
            // Crazy synth alarm
            const now = audioCtx.currentTime;
            osc.type = 'sawtooth';
            gain.gain.setValueAtTime(0.2, now);
            
            for (let i = 0; i < 8; i++) {
                osc.frequency.setValueAtTime(400, now + i * 0.1);
                osc.frequency.setValueAtTime(800, now + i * 0.1 + 0.05);
            }
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.8);
            osc.start();
            osc.stop(now + 0.85);
        }
    } catch(e) {
        console.warn("Audio Context blocked/failed", e);
    }
}

function drawGamba() {
    if (!gCtx || !gCanvas) return;
    
    gCtx.clearRect(0, 0, gCanvas.width, gCanvas.height);
    
    // Draw background
    gCtx.fillStyle = "#03030d";
    gCtx.fillRect(0, 0, gCanvas.width, gCanvas.height);
    
    const startX = 35;
    const startY = 20;
    const slotH = SYMBOL_HEIGHT * VISIBLE_ROWS;
    
    // Draw reel windows backdrops
    for (let r = 0; r < 3; r++) {
        const x = startX + r * (REEL_WIDTH + REEL_GAP);
        gCtx.fillStyle = "#060617";
        gCtx.fillRect(x, startY, REEL_WIDTH, slotH);
        
        // Draw grid boundaries inside reels
        gCtx.strokeStyle = "rgba(255, 102, 0, 0.15)";
        gCtx.lineWidth = 2;
        gCtx.strokeRect(x, startY, REEL_WIDTH, slotH);
        
        // Render slots symbols with clip mask to stay in bounds
        gCtx.save();
        
        // Create clipping region
        gCtx.beginPath();
        gCtx.rect(x, startY, REEL_WIDTH, slotH);
        gCtx.clip();
        
        // Draw symbols
        const reel = reels[r];
        const offset = reel.y % SYMBOL_HEIGHT;
        const baseIdx = Math.floor(reel.y / SYMBOL_HEIGHT);
        
        for (let row = -1; row <= VISIBLE_ROWS; row++) {
            const symbolIdx = reel.symbols[(baseIdx + row + reel.symbols.length * 10) % reel.symbols.length];
            const sym = slotSymbols[symbolIdx];
            
            const symY = startY + row * SYMBOL_HEIGHT + offset;
            
            // Draw symbol text
            gCtx.font = "40px Arial";
            gCtx.textAlign = "center";
            gCtx.textBaseline = "middle";
            
            gCtx.fillText(sym.char, x + REEL_WIDTH / 2, symY + SYMBOL_HEIGHT / 2);
            gCtx.restore();
        }
        gCtx.restore();
    }
    
    // Draw horizontal payline markers on sides
    gCtx.strokeStyle = "var(--orange)";
    gCtx.lineWidth = 3;
    
    gCtx.beginPath();
    gCtx.moveTo(10, startY + slotH / 2);
    gCtx.lineTo(startX - 5, startY + slotH / 2);
    gCtx.stroke();
    
    gCtx.beginPath();
    gCtx.moveTo(gCanvas.width - 10, startY + slotH / 2);
    gCtx.lineTo(startX + 3 * REEL_WIDTH + 2 * REEL_GAP + 5, startY + slotH / 2);
    gCtx.stroke();
    
    // Draw winning particles on top
    updateAndDrawGambaParticles();
}

function spinGamba() {
    if (isGambaSpinning) return;
    
    const betInput = document.getElementById("gamba-bet");
    const bet = parseInt(betInput.value);
    
    if (isNaN(bet) || bet <= 0) {
        alert("Enter a valid bet!");
        return;
    }
    
    if (!deductCredits(bet)) {
        alert("Not enough Cyber Credits!");
        return;
    }
    
    isGambaSpinning = true;
    gambaWinParticles = [];
    document.getElementById("btn-gamba-spin").disabled = true;
    document.getElementById("gamba-msg").innerText = "🎰 Spin reels rolling... Good Luck!";
    document.getElementById("gamba-msg").style.color = "var(--orange)";
    
    playGambaSound('spin');
    
    // Set random results
    const results = [
        Math.floor(Math.random() * slotSymbols.length),
        Math.floor(Math.random() * slotSymbols.length),
        Math.floor(Math.random() * slotSymbols.length)
    ];
    
    // Let's configure stop sequence
    const stopTimes = [1500, 2200, 2900];
    
    gambaTimeouts = [];
    for (let r = 0; r < 3; r++) {
        const reel = reels[r];
        reel.spinning = true;
        reel.decelerating = false;
        reel.speed = 25 + Math.random() * 8;
        
        // Find how many scrolls we need to stop at the result symbol in middle row
        const targetSymIdx = results[r];
        
        // Find matching symbol offset in symbols array
        const currentBaseIdx = Math.floor(reel.y / SYMBOL_HEIGHT);
        
        // Force a large number of rotations
        const minRotations = 30 + r * 15;
        let finalIndex = currentBaseIdx + minRotations;
        
        while ((reel.symbols[(finalIndex + 1) % reel.symbols.length]) !== targetSymIdx) {
            finalIndex++;
        }
        
        reel.targetY = finalIndex * SYMBOL_HEIGHT;
        
        // Set stop timers and track them
        const timeoutId = setTimeout(((index) => {
            return () => {
                stopReel(index);
            };
        })(r), stopTimes[r]);
        gambaTimeouts.push(timeoutId);
    }
    
    if (animGambaFrame) cancelAnimationFrame(animGambaFrame);
    animGambaFrame = requestAnimationFrame(animateGambaRoll);
}

function stopReel(r) {
    if (reels[r]) {
        reels[r].decelerating = true;
    }
}

function animateGambaRoll() {
    if (!isGambaSpinning && gambaWinParticles.length === 0) {
        if (animGambaFrame) cancelAnimationFrame(animGambaFrame);
        animGambaFrame = null;
        drawGamba();
        return;
    }
    
    let allStopped = true;
    
    for (let r = 0; r < 3; r++) {
        const reel = reels[r];
        if (reel.spinning) {
            allStopped = false;
            
            if (reel.decelerating) {
                if (reel.y >= reel.targetY) {
                    reel.y = reel.targetY;
                    reel.speed = 0;
                    reel.spinning = false;
                    reel.decelerating = false;
                    playGambaSound('stop');
                } else {
                    // Decelerate smoothly
                    reel.speed = Math.max(1, (reel.targetY - reel.y) * 0.08);
                    reel.y += reel.speed;
                }
            } else {
                // Constant spin speed
                reel.y += reel.speed;
            }
        }
    }
    
    if (isGambaSpinning && allStopped) {
        isGambaSpinning = false;
        const spinBtn = document.getElementById("btn-gamba-spin");
        if (spinBtn) spinBtn.disabled = false;
        evaluateGambaResult();
    }
    
    drawGamba();
    animGambaFrame = requestAnimationFrame(animateGambaRoll);
}

function quitGambaGame() {
    isGambaSpinning = false;
    
    // Clear timeouts
    gambaTimeouts.forEach(t => clearTimeout(t));
    gambaTimeouts = [];
    
    // Reset reels to non-spinning
    for (let r = 0; r < 3; r++) {
        reels[r].spinning = false;
        reels[r].decelerating = false;
        reels[r].speed = 0;
    }
    
    // Cancel anim frame
    if (animGambaFrame) {
        cancelAnimationFrame(animGambaFrame);
        animGambaFrame = null;
    }
    
    // Reset button
    const spinBtn = document.getElementById("btn-gamba-spin");
    if (spinBtn) spinBtn.disabled = false;
}

window.quitGambaGame = quitGambaGame;

function evaluateGambaResult() {
    // Get symbols in middle row
    const middleSymbols = [];
    for (let r = 0; r < 3; r++) {
        const reel = reels[r];
        const baseIdx = Math.floor(reel.y / SYMBOL_HEIGHT);
        const symIdx = reel.symbols[(baseIdx + 1) % reel.symbols.length];
        middleSymbols.push(symIdx);
    }
    
    const sym1 = slotSymbols[middleSymbols[0]];
    const sym2 = slotSymbols[middleSymbols[1]];
    const sym3 = slotSymbols[middleSymbols[2]];
    
    const betInput = document.getElementById("gamba-bet");
    const bet = parseInt(betInput.value);
    
    let winMult = 0;
    let winMsg = "";
    
    if (sym1.char === sym2.char && sym2.char === sym3.char) {
        // Three of a kind!
        winMult = sym1.mult;
        winMsg = `JACKPOT! 3x ${sym1.char} paid ${winMult}x bet!`;
        triggerGambaWinConfetti(sym1.color);
        playGambaSound(sym1.char === '💀' ? 'jackpot' : 'win');
    } else if (sym1.char === sym2.char || sym2.char === sym3.char || sym1.char === sym3.char) {
        // Two of a kind!
        const matchSym = (sym1.char === sym2.char) ? sym1 : sym3;
        winMult = Math.max(1, Math.floor(matchSym.mult * 0.4));
        winMsg = `WIN! Double ${matchSym.char} paid ${winMult}x wagers.`;
        triggerGambaWinConfetti(matchSym.color);
        playGambaSound('win');
    } else {
        // Lose
        winMsg = `No match. You lost ${bet} CC.`;
        document.getElementById("gamba-msg").style.color = "var(--text-muted)";
    }
    
    if (winMult > 0) {
        const payout = bet * winMult;
        addCredits(payout);
        document.getElementById("gamba-msg").style.color = "var(--green)";
        document.getElementById("gamba-msg").innerText = winMsg + ` (+${payout} CC)`;
    } else {
        document.getElementById("gamba-msg").innerText = winMsg;
    }
}

function triggerGambaWinConfetti(color) {
    gambaWinParticles = [];
    if (!gCanvas) return;
    for (let i = 0; i < 60; i++) {
        gambaWinParticles.push({
            x: gCanvas.width / 2,
            y: gCanvas.height / 2,
            vx: (Math.random() - 0.5) * 8,
            vy: (Math.random() - 0.7) * 7 - 2, // shoot upwards
            size: Math.random() * 5 + 3,
            color: color || "var(--orange)",
            alpha: 1.0,
            decay: Math.random() * 0.02 + 0.015
        });
    }
    // Loop animation frames if not already running
    if (!isGambaSpinning) {
        animateGambaRoll();
    }
}

function updateAndDrawGambaParticles() {
    for (let i = gambaWinParticles.length - 1; i >= 0; i--) {
        const p = gambaWinParticles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.alpha -= p.decay;
        if (p.alpha <= 0) {
            gambaWinParticles.splice(i, 1);
            continue;
        }
        gCtx.save();
        gCtx.globalAlpha = p.alpha;
        gCtx.fillStyle = p.color;
        gCtx.beginPath();
        gCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        gCtx.fill();
        gCtx.restore();
    }
}

function setGambaBetMultiplier(mult) {
    const betInput = document.getElementById("gamba-bet");
    if (!betInput) return;
    
    let balance = 1000;
    let saved = localStorage.getItem("cyberCredits");
    if (saved !== null) balance = parseInt(saved);
    
    let currentBet = parseInt(betInput.value) || 50;
    
    if (mult === 0.1) {
        betInput.value = 10;
    } else if (mult === 0.5) {
        betInput.value = Math.max(1, Math.floor(currentBet * 0.5));
    } else if (mult === 2.0) {
        betInput.value = Math.min(balance, currentBet * 2);
    } else if (mult === 999) {
        betInput.value = balance;
    }
}

// Hook slots initialization
document.addEventListener("DOMContentLoaded", initGamba);

window.spinGamba = spinGamba;
window.setGambaBetMultiplier = setGambaBetMultiplier;
