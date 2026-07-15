// Cyber Casino - Blackjack Engine
const suits = ["♠", "♥", "♦", "♣"];
const values = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"];

let deck = [];
let dealerHand = [];
let playerHand = [];
let gameOver = false;
let activeBet = 0;

function setBjBet(val) {
    const betInput = document.getElementById("bj-bet-input");
    if (betInput) {
        betInput.value = val;
    }
}

function setBjBetMax() {
    const betInput = document.getElementById("bj-bet-input");
    if (betInput && typeof cyberCredits !== 'undefined') {
        betInput.value = cyberCredits;
    }
}

function toggleBetInputs(disable) {
    const betInput = document.getElementById("bj-bet-input");
    if (betInput) betInput.disabled = disable;
    const betButtons = document.querySelectorAll("#bj-betting-controls button");
    betButtons.forEach(btn => {
        btn.disabled = disable;
    });
}

function payoutBlackjack() {
    if (activeBet <= 0) return;
    
    let pScore = calculateScore(playerHand);
    let dScore = calculateScore(dealerHand);
    let payout = 0;

    if (pScore > 21) {
        payout = 0;
    } else if (dScore > 21) {
        payout = Math.floor(activeBet * 2);
    } else if (pScore > dScore) {
        if (pScore === 21 && playerHand.length === 2) {
            payout = Math.floor(activeBet * 2.5); // 3:2 payout
            if (typeof showToast === 'function') {
                showToast(`🔥 BLACKJACK! Won ${payout} ₡!`, "success");
            }
        } else {
            payout = Math.floor(activeBet * 2); // 1:1 payout
        }
    } else if (pScore < dScore) {
        payout = 0;
    } else {
        payout = activeBet; // Tie / Push
    }

    if (payout > 0 && typeof window.addCredits === 'function') {
        window.addCredits(payout);
    }
    
    activeBet = 0;
}

function buildDeck() {
    deck = [];
    for (let s of suits) {
        for (let v of values) {
            let weight = parseInt(v);
            if (v === "J" || v === "Q" || v === "K") weight = 10;
            if (v === "A") weight = 11;
            
            let color = (s === "♥" || s === "♦") ? "var(--red)" : "var(--cyan)";
            deck.push({ suit: s, value: v, weight: weight, color: color });
        }
    }
}

function shuffleDeck() {
    for (let i = deck.length - 1; i > 0; i--) {
        let j = Math.floor(Math.random() * i);
        let temp = deck[i];
        deck[i] = deck[j];
        deck[j] = temp;
    }
}

function isSoft(hand) {
    let score = 0;
    let aces = 0;
    for (let card of hand) {
        score += card.weight;
        if (card.value === "A") aces += 1;
    }
    // If the hand is 17 or less WITH an active Ace counting as 11, it is "soft"
    return (aces > 0 && score <= 21);
}

function calculateScore(hand) {
    let score = 0;
    let aces = 0;
    for (let card of hand) {
        score += card.weight;
        if (card.value === "A") aces += 1;
    }
    while (score > 21 && aces > 0) {
        score -= 10;
        aces -= 1;
    }
    return score;
}

function renderCard(card, hidden = false, delayIdx = 0) {
    let delayStyle = `animation-delay: ${delayIdx * 0.12}s;`;
    if (hidden) {
        return `<div class="bj-card hidden-card" style="${delayStyle}">
                  <div class="card-back-pattern"></div>
                </div>`;
    }
    
    let pipsHTML = "";
    if (card.value === "A") {
        pipsHTML = `<div class="pip center-large">${card.suit}</div>`;
    } else if (card.value === "J" || card.value === "Q" || card.value === "K") {
        let icon = card.value === "J" ? "⚔️" : (card.value === "Q" ? "👑" : "♚");
        pipsHTML = `<div class="pip center-large">${icon}</div>`;
    } else {
        let num = parseInt(card.value);
        let pipLayout = {
            2: ["top-center", "bot-center"],
            3: ["top-center", "center", "bot-center"],
            4: ["top-left", "top-right", "bot-left", "bot-right"],
            5: ["top-left", "top-right", "center", "bot-left", "bot-right"],
            6: ["top-left", "top-right", "mid-left", "mid-right", "bot-left", "bot-right"],
            7: ["top-left", "top-right", "mid-top", "mid-left", "mid-right", "bot-left", "bot-right"],
            8: ["top-left", "top-right", "mid-top", "mid-bot", "mid-left", "mid-right", "bot-left", "bot-right"],
            9: ["top-left", "top-right", "mid-left-up", "mid-right-up", "center", "mid-left-down", "mid-right-down", "bot-left", "bot-right"],
            10: ["top-left", "top-right", "mid-top", "mid-left-up", "mid-right-up", "mid-bot", "mid-left-down", "mid-right-down", "bot-left", "bot-right"]
        };
        
        if (pipLayout[num]) {
            pipLayout[num].forEach(pos => {
                pipsHTML += `<div class="pip ${pos}">${card.suit}</div>`;
            });
        }
    }

    return `<div class="bj-card" style="color: ${card.color}; border-color: ${card.color}; ${delayStyle}">
              <div class="card-val top">${card.value} <span style="font-size:10px">${card.suit}</span></div>
              <div class="card-pips">${pipsHTML}</div>
              <div class="card-val bot">${card.value} <span style="font-size:10px">${card.suit}</span></div>
            </div>`;
}

function updateUI() {
    const dealerCardsEl = document.getElementById("bj-dealer-cards");
    const playerCardsEl = document.getElementById("bj-player-cards");
    const dealerScoreEl = document.getElementById("bj-dealer-score");
    const playerScoreEl = document.getElementById("bj-player-score");
    const msgEl = document.getElementById("bj-msg");

    // Render Dealer
    dealerCardsEl.innerHTML = "";
    dealerHand.forEach((card, index) => {
        // Hide second card if game is not over
        if (index === 1 && !gameOver) {
            dealerCardsEl.innerHTML += renderCard(card, true, index);
        } else {
            dealerCardsEl.innerHTML += renderCard(card, false, index);
        }
    });

    // Render Player
    playerCardsEl.innerHTML = "";
    playerHand.forEach((card, index) => {
        playerCardsEl.innerHTML += renderCard(card, false, index);
    });

    // Update Scores
    let pScore = calculateScore(playerHand);
    playerScoreEl.innerText = pScore;

    // Update Shoe Status UI if it exists
    const shoeStatusEl = document.getElementById("shoe-status");
    if (shoeStatusEl) {
        shoeStatusEl.innerText = deck.length;
    }

    if (!gameOver) {
        toggleBetInputs(true);
        dealerScoreEl.innerText = "?";
        msgEl.innerText = "Hit or Stand?";
        msgEl.style.color = "var(--cyan)";
        msgEl.classList.remove("win-animate");
        document.getElementById("btn-bj-hit").disabled = false;
        document.getElementById("btn-bj-stand").disabled = false;
        document.getElementById("btn-bj-deal").style.display = "none";
        document.getElementById("bj-gameplay-controls").style.display = "flex";
    } else {
        let dScore = calculateScore(dealerHand);
        dealerScoreEl.innerText = dScore;
        document.getElementById("btn-bj-hit").disabled = true;
        document.getElementById("btn-bj-stand").disabled = true;
        document.getElementById("btn-bj-deal").style.display = "inline-block";
        document.getElementById("bj-gameplay-controls").style.display = "none";
        toggleBetInputs(false);

        if (pScore > 21) {
            msgEl.innerText = "BUST! You lose.";
            msgEl.style.color = "var(--red)";
            msgEl.classList.remove("win-animate");
        } else if (dScore > 21) {
            msgEl.innerText = "DEALER BUSTS! You win!";
            msgEl.style.color = "var(--green)";
            msgEl.classList.add("win-animate");
        } else if (pScore > dScore) {
            if (pScore === 21 && playerHand.length === 2) {
                msgEl.innerText = "BLACKJACK! You win!";
                msgEl.style.color = "var(--purple)";
            } else {
                msgEl.innerText = "YOU WIN!";
                msgEl.style.color = "var(--green)";
            }
            msgEl.classList.add("win-animate");
        } else if (pScore < dScore) {
            msgEl.innerText = "DEALER WINS.";
            msgEl.style.color = "var(--red)";
            msgEl.classList.remove("win-animate");
        } else {
            // Push
            if (pScore === 21 && playerHand.length === 2 && dealerHand.length === 2) {
                msgEl.innerText = "Double Blackjack! Push.";
            } else {
                msgEl.innerText = "PUSH (Tie).";
            }
            msgEl.style.color = "var(--orange)";
            msgEl.classList.remove("win-animate");
        }
        payoutBlackjack();
    }
}

function initCasino() {
    // Only rebuild and shuffle if shoe penetration is deep (< 75 cards remaining)
    if (deck.length < 75) {
        console.log("Cut card reached. Shuffling new 6-deck shoe...");
        buildDeck();
        shuffleDeck();
        const msgEl = document.getElementById("bj-msg");
        msgEl.innerText = "SHUFFLING NEW SHOE...";
        msgEl.style.color = "var(--purple)";
        msgEl.classList.remove("win-animate");
        setTimeout(dealHands, 1000); // slight delay to show shuffle message
    } else {
        dealHands();
    }
}

function dealHands() {
    const betInput = document.getElementById("bj-bet-input");
    let betAmount = 50;
    if (betInput) {
        betAmount = parseInt(betInput.value);
        if (isNaN(betAmount) || betAmount < 1) {
            if (typeof showToast === 'function') showToast("Please enter a valid bet amount.", "error");
            else alert("Please enter a valid bet amount.");
            return;
        }
        if (typeof cyberCredits !== 'undefined' && betAmount > cyberCredits) {
            if (typeof showToast === 'function') showToast("Insufficient credits!", "error");
            else alert("Insufficient credits!");
            return;
        }
    }

    if (typeof window.deductCredits === 'function') {
        if (!window.deductCredits(betAmount)) {
            return;
        }
    }
    
    activeBet = betAmount;
    toggleBetInputs(true);

    dealerHand = [];
    playerHand = [];
    gameOver = false;

    playerHand.push(deck.pop());
    dealerHand.push(deck.pop());
    playerHand.push(deck.pop());
    dealerHand.push(deck.pop());

    updateUI();
    
    if (calculateScore(playerHand) === 21) {
        gameOver = true;
        updateUI();
    }
}

function hit() {
    if (gameOver) return;
    playerHand.push(deck.pop());
    if (calculateScore(playerHand) > 21) {
        gameOver = true;
    }
    updateUI();
}

function stand() {
    if (gameOver) return;
    gameOver = true;
    let dScore = calculateScore(dealerHand);
    
    // Dealer hits on Soft 17 or any hard score < 17
    while (dScore < 17 || (dScore === 17 && isSoft(dealerHand))) {
        dealerHand.push(deck.pop());
        dScore = calculateScore(dealerHand);
    }
    updateUI();
}

// Expose to window for inline onclick attributes
window.initCasino = initCasino;
window.startBlackjack = initCasino;
window.hit = hit;
window.blackjackHit = hit;
window.stand = stand;
window.blackjackStand = stand;
window.setBjBet = setBjBet;
window.setBjBetMax = setBjBetMax;
window.setBjBetMultiplier = function(mult) {
    const betInput = document.getElementById("bj-bet-input");
    if (!betInput) return;
    if (mult === 999) {
        if (typeof cyberCredits !== 'undefined') betInput.value = cyberCredits;
    } else if (mult === 0.1) {
        betInput.value = 10;
    } else if (mult === 0.5) {
        let val = Math.floor(parseInt(betInput.value) * 0.5);
        betInput.value = Math.max(1, val);
    } else if (mult === 2.0) {
        let val = Math.floor(parseInt(betInput.value) * 2);
        if (typeof cyberCredits !== 'undefined') {
            val = Math.min(val, cyberCredits);
        }
        betInput.value = Math.max(1, val);
    }
};

console.log("Cyber Casino Engine Loaded.");
