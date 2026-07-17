// Cyber Casino - Animated Crash Game (Graphically Enhanced Overhaul)
let crashMultiplier = 1.00;
let crashInterval;
let inCrashGame = false;
let crashed = false;
let currentBetCrash = 0;
let graphData = [];
let animFrame;
let startTime = 0;

// Graphics Engine variables
let stars = [];
let particles = [];
let explosionParticles = [];
let explosionActive = false;
let explosionTimer = 0;
let explosionX = 0;
let explosionY = 0;
let gridOffsetX = 0;
let gridOffsetY = 0;

const canvas = document.getElementById('crash-canvas');
const ctx = canvas ? canvas.getContext('2d') : null;

// Initialize stars once
function initStars() {
    stars = [];
    if (!canvas) return;
    for (let i = 0; i < 40; i++) {
        stars.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: Math.random() * 2 + 0.5,
            speed: Math.random() * 1.5 + 0.5
        });
    }
}

function resizeCanvas() {
    if (!canvas) return;
    const parent = canvas.parentElement;
    canvas.width = parent.clientWidth;
    canvas.height = parent.clientHeight;
    if (stars.length === 0) initStars();
    drawGraph();
}
window.addEventListener('resize', resizeCanvas);

function startCrashGame() {
    const betInput = document.getElementById("crash-bet");
    const bet = parseInt(betInput.value);
    
    if (isNaN(bet) || bet <= 0) {
        alert("Enter a valid bet!");
        return;
    }
    
    if (!deductCredits(bet)) {
        alert("Not enough Cyber Credits!");
        return;
    }
    
    if (canvas) {
        canvas.style.transform = "none";
        canvas.style.filter = "none";
    }
    
    currentBetCrash = bet;
    inCrashGame = true;
    crashed = false;
    crashMultiplier = 1.00;
    graphData = [];
    particles = [];
    explosionActive = false;
    startTime = Date.now();
    
    document.getElementById("btn-crash-bet").style.display = "none";
    document.getElementById("btn-crash-cashout").style.display = "inline-block";
    const multEl = document.getElementById("crash-multiplier");
    multEl.style.color = "var(--cyan)";
    multEl.style.textShadow = "0 0 15px var(--cyan)";
    multEl.innerText = "1.00x";
    document.getElementById("crash-msg").innerText = "Game started! Cash out before the crash!";
    
    // Determine the crash point randomly (heavy bias towards low multipliers)
    const crashPoint = (Math.random() < 0.05) ? 1.00 : Math.max(1.00, (1.00 / Math.random()) * 0.99);
    
    if (canvas) resizeCanvas();
    
    clearInterval(crashInterval);
    cancelAnimationFrame(animFrame);
    
    crashInterval = setInterval(() => {
        if (crashMultiplier >= crashPoint) {
            handleCrash();
            return;
        }
        
        // Non-linear growth formula
        const elapsedSeconds = (Date.now() - startTime) / 1000;
        crashMultiplier = Math.pow(Math.E, 0.08 * elapsedSeconds);
        
        graphData.push({ t: elapsedSeconds, y: crashMultiplier });
        multEl.innerText = crashMultiplier.toFixed(2) + "x";
    }, 50);
    
    animateGraph();
}

function animateGraph() {
    if (!inCrashGame && !explosionActive) return;
    drawGraph();
    animFrame = requestAnimationFrame(animateGraph);
}

function drawGraph() {
    if (!ctx || !canvas) return;
    
    // Apply screen shake directly on canvas context
    ctx.save();
    let shakeAmt = 0;
    if (inCrashGame) {
        shakeAmt = Math.max(0, (crashMultiplier - 1.2) * 1.5);
        if (shakeAmt > 8) shakeAmt = 8;
    }
    const dx = (Math.random() - 0.5) * shakeAmt;
    const dy = (Math.random() - 0.5) * shakeAmt;
    ctx.translate(dx, dy);
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 1. Draw Space background & stars
    ctx.fillStyle = "#020208";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Update and draw stars
    const speedMult = inCrashGame ? (crashMultiplier - 0.9) * 3 + 1 : 1;
    ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
    stars.forEach(star => {
        if (inCrashGame) {
            star.x -= star.speed * speedMult * 0.4;
            star.y += star.speed * speedMult * 0.2;
            if (star.x < 0) {
                star.x = canvas.width;
                star.y = Math.random() * canvas.height;
            }
            if (star.y > canvas.height) {
                star.y = 0;
                star.x = Math.random() * canvas.width;
            }
        }
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
    });
    
    // 2. Draw Scrolling Grid
    if (inCrashGame) {
        gridOffsetX -= speedMult * 0.8;
        gridOffsetY += speedMult * 0.4;
    }
    ctx.strokeStyle = "rgba(0, 255, 204, 0.08)";
    ctx.lineWidth = 1;
    const spacing = 40;
    for (let x = (gridOffsetX % spacing); x < canvas.width; x += spacing) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
    }
    for (let y = (gridOffsetY % spacing); y < canvas.height; y += spacing) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
    }
    
    // 3. Draw Crash Curve & Rocket
    const padding = 30;
    const w = canvas.width - padding * 2;
    const h = canvas.height - padding * 2;
    
    const maxT = Math.max(10, graphData.length > 0 ? graphData[graphData.length - 1].t : 10);
    const maxY = Math.max(2, crashMultiplier);
    
    let rocketX = padding;
    let rocketY = canvas.height - padding;
    
    if (graphData.length > 0) {
        // Draw glow effect for the line
        ctx.shadowColor = "var(--cyan)";
        ctx.shadowBlur = 15;
        ctx.strokeStyle = "var(--cyan)";
        ctx.lineWidth = 4;
        
        ctx.beginPath();
        ctx.moveTo(padding, canvas.height - padding);
        
        for (let i = 0; i < graphData.length; i++) {
            const pt = graphData[i];
            const x = padding + (pt.t / maxT) * w;
            const y = canvas.height - padding - ((pt.y - 1) / (maxY - 1)) * h;
            ctx.lineTo(x, y);
            
            if (i === graphData.length - 1) {
                rocketX = x;
                rocketY = y;
            }
        }
        ctx.stroke();
        ctx.shadowBlur = 0; // reset
        
        // Fill gradient under curve
        ctx.lineTo(rocketX, canvas.height - padding);
        ctx.lineTo(padding, canvas.height - padding);
        const grad = ctx.createLinearGradient(0, rocketY, 0, canvas.height - padding);
        grad.addColorStop(0, "rgba(0, 255, 204, 0.2)");
        grad.addColorStop(1, "rgba(0, 255, 204, 0.0)");
        ctx.fillStyle = grad;
        ctx.fill();
        
        // Emit smoke/fire particles from rocket exhaust
        if (inCrashGame) {
            emitExhaustParticles(rocketX, rocketY);
        }
    }
    
    // Update and draw trail particles
    updateAndDrawParticles();
    
    // Draw explosion if active
    updateAndDrawExplosion();
    
    // Draw rocket ship on top
    if (inCrashGame && graphData.length > 0) {
        ctx.save();
        ctx.font = "32px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.translate(rocketX, rocketY);
        // Tilt the rocket upward to match path angle
        ctx.rotate(-Math.PI / 4 + Math.sin(Date.now() / 80) * 0.03); 
        ctx.fillText("🚀", 0, 0);
        ctx.restore();
    }
    
    ctx.restore(); // Restore context from shake translate
}

function emitExhaustParticles(x, y) {
    for (let i = 0; i < 2; i++) {
        particles.push({
            x: x - 10,
            y: y + 10,
            vx: -Math.random() * 2 - 1.5,
            vy: Math.random() * 1.5 - 0.75,
            size: Math.random() * 4 + 2,
            alpha: 1.0,
            decay: Math.random() * 0.04 + 0.02,
            color: Math.random() < 0.6 ? "rgba(255, 68, 85, 0.8)" : "rgba(255, 170, 0, 0.8)" // Red/orange fire
        });
    }
}

function updateAndDrawParticles() {
    for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.alpha -= p.decay;
        if (p.alpha <= 0) {
            particles.splice(i, 1);
            continue;
        }
        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }
}

function triggerExplosion(x, y) {
    explosionActive = true;
    explosionTimer = 35;
    explosionX = x;
    explosionY = y;
    explosionParticles = [];
    
    for (let i = 0; i < 45; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = Math.random() * 7 + 3;
        explosionParticles.push({
            x: x,
            y: y,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            size: Math.random() * 6 + 3,
            color: Math.random() < 0.4 ? "#ff3366" : (Math.random() < 0.75 ? "#ffaa00" : "#ffff33"),
            alpha: 1.0,
            decay: Math.random() * 0.03 + 0.015
        });
    }
}

function updateAndDrawExplosion() {
    if (!explosionActive) return;
    explosionTimer--;
    if (explosionTimer <= 0) {
        explosionActive = false;
        return;
    }
    
    for (let i = explosionParticles.length - 1; i >= 0; i--) {
        const p = explosionParticles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.alpha -= p.decay;
        if (p.alpha <= 0) {
            continue;
        }
        ctx.save();
        ctx.globalAlpha = p.alpha;
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }
}

function handleCrash() {
    clearInterval(crashInterval);
    
    crashed = true;
    inCrashGame = false;
    
    // Find final point of path
    let lastX = canvas.width / 2;
    let lastY = canvas.height / 2;
    if (graphData.length > 0) {
        const padding = 30;
        const w = canvas.width - padding * 2;
        const h = canvas.height - padding * 2;
        const maxT = Math.max(10, graphData[graphData.length - 1].t);
        const maxY = Math.max(2, crashMultiplier);
        const lastPt = graphData[graphData.length - 1];
        lastX = padding + (lastPt.t / maxT) * w;
        lastY = canvas.height - padding - ((lastPt.y - 1) / (maxY - 1)) * h;
    }
    
    // Trigger canvas explosion animation
    triggerExplosion(lastX, lastY);
    
    const multEl = document.getElementById("crash-multiplier");
    multEl.style.color = "var(--red)";
    multEl.style.textShadow = "0 0 15px var(--red)";
    multEl.innerText = "💥 CRASHED @ " + crashMultiplier.toFixed(2) + "x";
    document.getElementById("crash-msg").innerText = "You lost " + currentBetCrash + " CC.";
    
    if (canvas) {
        // Red flash shake via CSS
        canvas.style.animation = "shake 0.5s cubic-bezier(.36,.07,.19,.97) both";
        canvas.style.filter = "sepia(1) hue-rotate(-50deg) saturate(3) brightness(1.2)";
        setTimeout(() => {
            if (canvas) canvas.style.filter = "none";
        }, 500);
    }
    
    resetCrashUI();
}

function cashOutCrash() {
    if (!inCrashGame || crashed) return;
    
    clearInterval(crashInterval);
    inCrashGame = false;
    cancelAnimationFrame(animFrame);
    
    const winAmount = Math.floor(currentBetCrash * crashMultiplier);
    addCredits(winAmount);
    
    const multEl = document.getElementById("crash-multiplier");
    multEl.style.color = "var(--green)";
    multEl.style.textShadow = "0 0 15px var(--green)";
    document.getElementById("crash-msg").innerText = "💰 Cashed out! Won " + winAmount + " CC!";
    
    resetCrashUI();
}

function resetCrashUI() {
    document.getElementById("btn-crash-bet").style.display = "inline-block";
    document.getElementById("btn-crash-cashout").style.display = "none";
    currentBetCrash = 0;
}

function setCrashBetMultiplier(mult) {
    const betInput = document.getElementById("crash-bet");
    if (!betInput) return;
    
    // Retrieve latest balance
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

// Inject stylesheet for shake & pulse animation
const style = document.createElement('style');
style.innerHTML = `
@keyframes shake {
  10%, 90% { transform: translate3d(-2px, 0, 0); }
  20%, 80% { transform: translate3d(4px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-8px, -4px, 0); }
  40%, 60% { transform: translate3d(8px, 4px, 0); }
}
@keyframes pulse-green {
  0% { box-shadow: 4px 4px 0px #111, 0 0 0 0px rgba(0,230,153,0.6); }
  70% { box-shadow: 4px 4px 0px #111, 0 0 0 12px rgba(0,230,153,0); }
  100% { box-shadow: 4px 4px 0px #111, 0 0 0 0px rgba(0,230,153,0); }
}`;
document.head.appendChild(style);

function quitCrashGame() {
    if (inCrashGame) {
        clearInterval(crashInterval);
        inCrashGame = false;
        crashed = false;
        explosionActive = false;
        cancelAnimationFrame(animFrame);
        resetCrashUI();
        const multEl = document.getElementById("crash-multiplier");
        if (multEl) {
            multEl.style.color = "var(--text-muted)";
            multEl.style.textShadow = "none";
            multEl.innerText = "1.00x";
        }
        const msgEl = document.getElementById("crash-msg");
        if (msgEl) {
            msgEl.innerText = "Game closed.";
        }
    }
}

window.quitCrashGame = quitCrashGame;
window.setCrashBetMultiplier = setCrashBetMultiplier;
window.resizeCanvas = resizeCanvas;
