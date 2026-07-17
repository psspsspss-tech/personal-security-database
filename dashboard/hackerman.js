// Hackerman: Fallout-Style Terminal Password Decipher minigame
// Built for the Cyber Gaming Hub on D: drive

let hmPasswords = [];
let hmSecret = "";
let hmAttempts = 4;
let hmMaxAttempts = 4;
let hmWager = 10;
let hmActive = false;
let hmGridLines = [];
let hmConsoleHistory = [];

const HM_WORDS_POOL = [
    "ROUTERS", "STEALTH", "MALWARE", "BOTNETS", "DECRYPT", "ROOTKIT", "WIRETAP", 
    "EXPLOIT", "PAYLOAD", "SANDBOX", "SPYWARE", "SPAMMER", "PHISHES", "DECOYED", 
    "DEFENSE", "FIREWAL", "BACKDOR", "KEYLOGS", "SPAMBOT", "PHREAKS", "BOTNETS"
];

const HM_SYMBOLS = "!@#$%^&*()_+-=[]{}|;:,./<>?";

function initHackermanGame() {
    hmConsoleHistory = [];
    addHmLog("SYSTEM INITIALIZED. STANDBY...");
    addHmLog("CLICK 'ESTABLISH LINK' TO BEGIN DECIPHER.");
    updateHackermanUI();
}

function startHackermanGame() {
    const wagerSelect = document.getElementById("hackerman-wager");
    if (wagerSelect) {
        hmWager = parseInt(wagerSelect.value) || 10;
    }

    if (typeof cyberCredits !== 'undefined') {
        if (cyberCredits < hmWager) {
            showToast("Insufficient Cyber Credits balance!", "error");
            return;
        }
    }

    // Deduct wager
    if (typeof window.deductCredits === 'function') {
        window.deductCredits(hmWager);
    }

    hmActive = true;
    hmAttempts = hmMaxAttempts;
    hmConsoleHistory = [];

    // Select 8 random words
    let shuffled = [...HM_WORDS_POOL].sort(() => 0.5 - Math.random());
    hmPasswords = shuffled.slice(0, 8);
    hmSecret = hmPasswords[Math.floor(Math.random() * hmPasswords.length)];

    addHmLog("--- PASSCODE RECOVERY ATTEMPT ---");
    addHmLog(`[WAGER] ${hmWager} CC entered.`);
    addHmLog("LOCKOUT SYSTEM ACTIVE. 4 ATTEMPTS REMAINING.");

    generateTerminalGrid();
    updateHackermanUI();
}

function generateTerminalGrid() {
    hmGridLines = [];
    const hexStart = 0xF3C0;
    
    // Create 12 lines of text
    for (let i = 0; i < 12; i++) {
        let address = "0x" + (hexStart + i * 12).toString(16).toUpperCase();
        let contentTokens = [];
        let wordInjected = false;
        
        // Each line has 12 symbols/characters
        let lineLen = 0;
        while (lineLen < 12) {
            // Chance to inject a password if we haven't injected one in this line
            if (!wordInjected && Math.random() < 0.4 && hmPasswords.length > 0) {
                let word = hmPasswords.pop();
                // Add characters of the word
                for (let char of word) {
                    contentTokens.push({ type: "word", val: char, word: word });
                }
                lineLen += word.length;
                wordInjected = true;
            } else {
                // Add a random symbol
                let sym = HM_SYMBOLS[Math.floor(Math.random() * HM_SYMBOLS.length)];
                contentTokens.push({ type: "symbol", val: sym });
                lineLen++;
            }
        }
        hmGridLines.push({ address: address, tokens: contentTokens });
    }

    // Inject bracket tricks (at least two bracket groups)
    // For simplicity, we search for matching brackets in lines and tag them.
    // Let's do a simple bracket injection in 2 random lines
    let bracketPairs = [["[", "]"], ["{", "}"], ["<", ">"], ["(", ")"]];
    let trickLines = [2, 7];
    for (let lineIndex of trickLines) {
        if (lineIndex < hmGridLines.length) {
            let line = hmGridLines[lineIndex];
            let pair = bracketPairs[Math.floor(Math.random() * bracketPairs.length)];
            // Replace token 1 and token 8 with matching brackets
            line.tokens[1] = { type: "bracket", val: pair[0], id: `b_${lineIndex}` };
            line.tokens[8] = { type: "bracket", val: pair[1], id: `b_${lineIndex}` };
        }
    }
}

function guessHackermanWord(word) {
    if (!hmActive) return;

    if (word === hmSecret) {
        endHackermanGame(true);
    } else {
        hmAttempts--;
        let likeness = calculateLikeness(word, hmSecret);
        addHmLog(`> Guess: '${word}'`);
        addHmLog(`> ACCESS DENIED. Likeness: ${likeness}/7`);
        addHmLog(`> Attempts remaining: ${hmAttempts}`);

        if (hmAttempts <= 0) {
            endHackermanGame(false);
        }
    }
    updateHackermanUI();
}

function triggerBracketTrick(id) {
    if (!hmActive) return;

    // Disarm bracket group (can only trigger once)
    const bracketTokens = document.querySelectorAll(`[data-bracket-id='${id}']`);
    bracketTokens.forEach(el => {
        el.style.opacity = "0.3";
        el.style.pointerEvents = "none";
    });

    addHmLog("> Executing bracket trick...");

    if (Math.random() < 0.5) {
        // Reset attempts
        hmAttempts = hmMaxAttempts;
        addHmLog("> ATTEMPTS RESET TO 4.");
    } else {
        // Remove a dud (a wrong password)
        let wrongWords = hmPasswords.filter(w => w !== hmSecret);
        if (wrongWords.length > 0) {
            let dud = wrongWords[Math.floor(Math.random() * wrongWords.length)];
            // Remove dud from passwords list
            hmPasswords = hmPasswords.filter(w => w !== dud);
            addHmLog(`> Dud removed: '${dud}'`);
            
            // Blank out the dud in the UI
            document.querySelectorAll(`[data-word='${dud}']`).forEach(el => {
                el.textContent = ".";
                el.className = "tm-char";
                el.removeAttribute("onclick");
            });
        } else {
            // Fallback to resetting attempts
            hmAttempts = hmMaxAttempts;
            addHmLog("> ATTEMPTS RESET TO 4.");
        }
    }
    updateHackermanUI();
}

function calculateLikeness(w1, w2) {
    let likeness = 0;
    for (let i = 0; i < w1.length; i++) {
        if (w1[i] === w2[i]) likeness++;
    }
    return likeness;
}

function endHackermanGame(won) {
    hmActive = false;
    const statusText = document.getElementById("hackerman-game-status");

    if (won) {
        const reward = hmWager * 3; // 3x payout because it requires deduction!
        if (typeof window.addCredits === 'function') {
            window.addCredits(reward);
        }
        if (statusText) {
            statusText.textContent = `DECRYPTED! +${reward} CC`;
            statusText.style.color = "var(--green)";
        }
        addHmLog(`[ACCESS GRANTED] Mainframe decrypted. Reward: +${reward} CC`);
        showToast("Access Granted! Mainframe unlocked.", "success");
    } else {
        if (statusText) {
            statusText.textContent = `LOCKED OUT! -${hmWager} CC`;
            statusText.style.color = "var(--red)";
        }
        addHmLog(`[LOCKOUT] Maximum attempts reached. Target: ${hmSecret}`);
        showToast(`Terminal Lockout! Lost ${hmWager} CC.`, "error");
    }
}

function addHmLog(msg) {
    hmConsoleHistory.push(msg);
    if (hmConsoleHistory.length > 10) hmConsoleHistory.shift();
}

function updateHackermanUI() {
    // Render Terminal Grid
    const gridContainer = document.getElementById("hackerman-terminal-grid");
    if (gridContainer) {
        if (!hmActive) {
            gridContainer.innerHTML = `<div style="color:var(--text-muted); font-size:13px; text-align:center; padding-top:40px;">TERMINAL STANDBY.<br>CLICK ESTABLISH LINK TO CONNECT.</div>`;
        } else {
            let html = "";
            for (let line of hmGridLines) {
                let tokensHtml = line.tokens.map(tok => {
                    if (tok.type === "word") {
                        return `<span class="tm-word" data-word="${tok.word}" onclick="guessHackermanWord('${tok.word}')">${tok.val}</span>`;
                    } else if (tok.type === "bracket") {
                        return `<span class="tm-bracket" data-bracket-id="${tok.id}" onclick="triggerBracketTrick('${tok.id}')">${tok.val}</span>`;
                    } else {
                        return `<span class="tm-char">${tok.val}</span>`;
                    }
                }).join("");
                html += `<div style="margin-bottom:4px;"><span style="color:#666; margin-right:12px;">${line.address}</span>${tokensHtml}</div>`;
            }
            gridContainer.innerHTML = html;
        }
    }

    // Update Console Log panel
    const consoleLogs = document.getElementById("hackerman-console-log");
    if (consoleLogs) {
        consoleLogs.innerHTML = hmConsoleHistory.map(line => `<div>${line}</div>`).join("");
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Update Attempts / Lockout indicators
    const attemptsContainer = document.getElementById("hackerman-attempts-indicator");
    if (attemptsContainer) {
        if (!hmActive) {
            attemptsContainer.innerHTML = "";
        } else {
            attemptsContainer.innerHTML = "LOCKOUT SAFEGUARDS: " + Array(hmAttempts).fill("■").join(" ") + Array(hmMaxAttempts - hmAttempts).fill("□").join(" ");
        }
    }
}

// Expose functions globally
window.initHackermanGame = initHackermanGame;
window.startHackermanGame = startHackermanGame;
window.guessHackermanWord = guessHackermanWord;
window.triggerBracketTrick = triggerBracketTrick;
