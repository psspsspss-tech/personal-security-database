// Cyber Casino - Points Engine
let cyberCredits = 1000;

function initCasinoEngine() {
    let saved = localStorage.getItem("cyberCredits");
    if (saved !== null) {
        cyberCredits = parseInt(saved);
    } else {
        localStorage.setItem("cyberCredits", cyberCredits);
    }
    updateCreditsUI();
    syncPointsWithServer();
}

function updateCreditsUI() {
    const els = document.querySelectorAll(".cyber-credits-display");
    els.forEach(el => {
        el.innerText = cyberCredits + " ₡";
    });
    const headerEl = document.getElementById("cyber-credits-display");
    if (headerEl) headerEl.innerText = cyberCredits;
}

function addCredits(amount) {
    cyberCredits += amount;
    localStorage.setItem("cyberCredits", cyberCredits);
    updateCreditsUI();
    syncPointsWithServer(amount);
}

function deductCredits(amount) {
    if (cyberCredits >= amount) {
        cyberCredits -= amount;
        localStorage.setItem("cyberCredits", cyberCredits);
        updateCreditsUI();
        syncPointsWithServer(-amount);
        return true;
    }
    return false;
}

async function syncPointsWithServer(delta = 0) {
    try {
        if (delta !== 0) {
            const res = await fetch("/api/credits/update", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({delta})
            });
            const data = await res.json();
            if (data.ok) {
                cyberCredits = data.credits;
                localStorage.setItem("cyberCredits", cyberCredits);
                updateCreditsUI();
            }
        } else {
            const res = await fetch("/api/credits");
            const data = await res.json();
            if (data.ok) {
                cyberCredits = data.credits;
                localStorage.setItem("cyberCredits", cyberCredits);
                updateCreditsUI();
            }
        }
    } catch (e) {
        console.warn("[Casino] Offline mode - points saved locally.");
    }
}

// Expose globally so app.js passive income loop can call it
window.addCredits = addCredits;
window.deductCredits = deductCredits;

function switchCasinoGame(gameId) {
    // Hide all game card containers dynamically
    document.querySelectorAll("[id^='casino-card-']").forEach(el => {
        el.style.display = "none";
    });
    
    // Auto-pause or quit minigames if user switches to a different game
    if (gameId !== 'tetris' && typeof window.quitTetrisGame === 'function') {
        window.quitTetrisGame();
    }
    if (gameId !== 'crash' && typeof window.quitCrashGame === 'function') {
        window.quitCrashGame();
    }
    if (gameId !== 'gamba' && typeof window.quitGambaGame === 'function') {
        window.quitGambaGame();
    }
    
    // Remove active styling from all tabs
    document.querySelectorAll(".casino-tab-btn").forEach(btn => {
        btn.style.background = "var(--bg-card)";
        btn.style.color = "var(--text-primary)";
        btn.style.boxShadow = "4px 4px 0px #111";
        btn.style.transform = "none";
    });
    
    // Show selected card
    const activeCard = document.getElementById("casino-card-" + gameId);
    if (activeCard) {
        activeCard.style.display = "block";
    }
    
    // Style active tab
    const activeBtn = document.getElementById("casino-tab-btn-" + gameId);
    if (activeBtn) {
        activeBtn.style.background = "var(--purple)";
        activeBtn.style.color = "#fff";
        activeBtn.style.boxShadow = "2px 2px 0px #111";
        activeBtn.style.transform = "translate(2px, 2px)";
    }
    
    // Trigger canvas resizing
    if (gameId === 'crash' && typeof window.resizeCanvas === 'function') {
        setTimeout(window.resizeCanvas, 100);
    }
    if (gameId === 'gamba' && typeof window.resizeGambaCanvas === 'function') {
        setTimeout(window.resizeGambaCanvas, 100);
    }
    if (gameId === 'hangman' && typeof window.initHangmanGame === 'function') {
        window.initHangmanGame();
    }
    if (gameId === 'hackerman' && typeof window.initHackermanGame === 'function') {
        window.initHackermanGame();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    initCasinoEngine();
    const urlParams = new URLSearchParams(window.location.search);
    const targetGame = urlParams.get('game') || 'crash';
    switchCasinoGame(targetGame);
});

window.switchCasinoGame = switchCasinoGame;

