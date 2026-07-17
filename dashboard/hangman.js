// Hackman (System Breach Hangman) Game Engine
// Offline & Online Hacker Duel modes with Neo-Brutalist styling

let hangmanWord = "";
let hangmanGuessed = new Set();
let hangmanAttempts = 0;
const hangmanMaxAttempts = 6;
let hangmanWager = 10;
let hangmanActive = false;
let hangmanIsOnline = false;

const HANGMAN_LOCAL_WORDS = [
    "CYBERSECURITY", "FIREWALL", "HONEYPOT", "RANSOMWARE", "PHISHING",
    "DECRYPTION", "ANTIVIRUS", "TRIPWIRE", "INTRUSION", "ENCRYPTION",
    "MALWARE", "SPYWARE", "ROOTKIT", "VULNERABILITY", "SANDBOX",
    "BACKDOOR", "EXPLOIT", "PAYLOAD", "KEYLOGGER", "SPAMMER",
    "BOTNET", "PHREAKING", "STEALTH", "SPOOFING", "WIRETAP"
];

const HACKER_LOGS_STEPS = [
    "LOG: Connection closed. Remote terminal idle.",
    "WARN: Intruder connection detected at router node.",
    "ALERT: Firewall rules bypassed on ports 80/443.",
    "CRITICAL: Exploit packet successfully uploaded to target shell.",
    "BREACH: Privilege escalation root access achieved.",
    "DATA: Decrypting secure database nodes... 68% complete.",
    "SYSTEM BREACHED! Host data fully exfiltrated."
];

function initHangmanGame() {
    // Generate keyboard keys
    const kbContainer = document.getElementById("hangman-keyboard");
    if (kbContainer) {
        kbContainer.innerHTML = "";
        const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        for (let char of letters) {
            const btn = document.createElement("button");
            btn.textContent = char;
            btn.className = "hm-key-btn";
            btn.onclick = () => guessHangmanLetter(char);
            kbContainer.appendChild(btn);
        }
    }

    // Set default display state
    updateHangmanUI();
}

async function startHangmanGame() {
    const wagerSelect = document.getElementById("hangman-wager");
    if (wagerSelect) {
        hangmanWager = parseInt(wagerSelect.value) || 10;
    }

    // Check credits availability
    if (typeof cyberCredits !== 'undefined') {
        if (cyberCredits < hangmanWager) {
            showToast("Insufficient Cyber Credits balance!", "error");
            return;
        }
    }

    hangmanGuessed.clear();
    hangmanAttempts = 0;
    hangmanActive = true;

    // Deduct wager
    if (typeof window.deductCredits === 'function') {
        window.deductCredits(hangmanWager);
    }

    // Mode check
    const modeCheckbox = document.getElementById("hangman-online-toggle");
    hangmanIsOnline = modeCheckbox ? modeCheckbox.checked : false;

    const statusText = document.getElementById("hangman-game-status");
    if (statusText) {
        statusText.textContent = "DECRYPTING SECURITY PACKET...";
        statusText.style.color = "var(--yellow)";
    }

    if (hangmanIsOnline) {
        try {
            const res = await fetch("/api/gaming/hangman");
            const data = await res.json();
            if (data.ok) {
                hangmanWord = data.word.toUpperCase();
                addHangmanConsoleLog(`[INCOMING] Hacker handshake packet: ${data.signature}`);
                addHangmanConsoleLog(`[THREAT_LEVEL] Connection Threat: ${data.hacker_threat}`);
            } else {
                throw new Error("API error");
            }
        } catch (e) {
            console.warn("Failed to fetch online word, falling back to local database.", e);
            hangmanWord = HANGMAN_LOCAL_WORDS[Math.floor(Math.random() * HANGMAN_LOCAL_WORDS.length)].toUpperCase();
            addHangmanConsoleLog("[SYSTEM] Connection failed. Emulating offline packet security vault.");
        }
    } else {
        hangmanWord = HANGMAN_LOCAL_WORDS[Math.floor(Math.random() * HANGMAN_LOCAL_WORDS.length)].toUpperCase();
        addHangmanConsoleLog("[LOCAL] Initialized offline decryption chamber. Decoy vault ready.");
    }

    // Reset keyboards
    document.querySelectorAll(".hm-key-btn").forEach(btn => {
        btn.disabled = false;
        btn.classList.remove("correct", "incorrect");
    });

    updateHangmanUI();
}

function guessHangmanLetter(char) {
    if (!hangmanActive || hangmanGuessed.has(char)) return;

    hangmanGuessed.add(char);
    const btn = Array.from(document.querySelectorAll(".hm-key-btn")).find(b => b.textContent === char);

    if (hangmanWord.includes(char)) {
        if (btn) btn.classList.add("correct");
        addHangmanConsoleLog(`[SUCCESS] Matched node signature fragment: '${char}'`);
        
        // Check win condition
        const won = Array.from(hangmanWord).every(letter => hangmanGuessed.has(letter));
        if (won) {
            endHangmanGame(true);
        }
    } else {
        if (btn) btn.classList.add("incorrect");
        hangmanAttempts++;
        addHangmanConsoleLog(`[FAIL] Mismatched node signature fragment: '${char}'`);
        
        // Check lose condition
        if (hangmanAttempts >= hangmanMaxAttempts) {
            endHangmanGame(false);
        }
    }

    if (btn) btn.disabled = true;
    updateHangmanUI();
}

function endHangmanGame(won) {
    hangmanActive = false;
    const statusText = document.getElementById("hangman-game-status");

    if (won) {
        const reward = hangmanWager * 2;
        if (typeof window.addCredits === 'function') {
            window.addCredits(reward);
        }
        if (statusText) {
            statusText.textContent = `PASSCODE RESTORED! +${reward} CC`;
            statusText.style.color = "var(--green)";
        }
        addHangmanConsoleLog(`[RESOLVED] Secure key restored. Hacker trace isolated. Payout: +${reward} CC`);
        showToast("System Secured! Recouped double wager.", "success");
    } else {
        if (statusText) {
            statusText.textContent = `SYSTEM BREACHED! -${hangmanWager} CC`;
            statusText.style.color = "var(--red)";
        }
        addHangmanConsoleLog(`[EXPLOITED] System security core hijacked. Target word was: ${hangmanWord}`);
        showToast(`Security Breach! Lost ${hangmanWager} Cyber Credits.`, "error");
    }

    // Disable all keyboard keys
    document.querySelectorAll(".hm-key-btn").forEach(btn => {
        btn.disabled = true;
    });
}

function addHangmanConsoleLog(msg) {
    const consoleLog = document.getElementById("hangman-console-log");
    if (consoleLog) {
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0];
        const logLine = document.createElement("div");
        logLine.innerHTML = `<span style="color:var(--text-muted);">${timeStr}</span> ${msg}`;
        consoleLog.appendChild(logLine);
        consoleLog.scrollTop = consoleLog.scrollHeight;
    }
}

function updateHangmanUI() {
    // 1. Draw Word Blanks
    const blanksContainer = document.getElementById("hangman-word-blanks");
    if (blanksContainer) {
        if (!hangmanWord) {
            blanksContainer.innerHTML = `<span style="color:var(--text-muted); letter-spacing:1px; font-size:16px;">CONNECT SYSTEM TO START DECRYPTION</span>`;
        } else {
            blanksContainer.innerHTML = Array.from(hangmanWord).map(letter => {
                if (hangmanGuessed.has(letter)) {
                    return `<span class="hm-letter-blank">${letter}</span>`;
                } else {
                    return `<span class="hm-letter-blank">_</span>`;
                }
            }).join("");
        }
    }

    // 2. Update Console status message
    const lcdStatus = document.getElementById("hangman-lcd-status");
    if (lcdStatus) {
        lcdStatus.textContent = HACKER_LOGS_STEPS[Math.min(hangmanAttempts, hangmanMaxAttempts)];
        lcdStatus.style.color = hangmanAttempts >= 4 ? "var(--red)" : (hangmanAttempts >= 2 ? "var(--orange)" : "var(--green)");
    }

    // 3. Update SVG Graphic elements visibility
    // SVG Parts: hm-part-1, hm-part-2, ... hm-part-6
    for (let i = 1; i <= hangmanMaxAttempts; i++) {
        const part = document.getElementById(`hm-part-${i}`);
        if (part) {
            part.style.opacity = (hangmanAttempts >= i) ? "1" : "0.08";
        }
    }
}

// Expose functions globally
window.initHangmanGame = initHangmanGame;
window.startHangmanGame = startHangmanGame;
window.guessHangmanLetter = guessHangmanLetter;
window.updateHangmanUI = updateHangmanUI;
