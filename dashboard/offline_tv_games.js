// 8-Bit CRT TV Channels Engine
let tvChannel = 0; // 0 = Matrix Rain, 1 = Snake Game, 2 = Hacker Terminal
let tvAnimFrame;
let tvCanvas;
let tvCtx;

// --- MATRIX CONFIG ---
let matrixCols;
let matrixYPos;

// --- SNAKE CONFIG ---
let snake = [];
let snakeDir = { x: 1, y: 0 };
let snakeNextDir = { x: 1, y: 0 };
let snakeFood = { x: 15, y: 15 };
let snakeScore = 0;
let snakeGrid = 20;
let lastSnakeUpdate = 0;
let snakeGameOver = false;

// --- PROCEDURAL SHOWS CONFIG ---
let currentShowIndex = 0;

// Cosmos Cruiser state
let ccStars = [];
let ccPlanets = [];
let ccLogs = [];
let ccLastLog = 0;

// Cyber News state
let cnNews = [];
let cnNewsIdx = 0;
let cnCityIdx = 0;
let cnCities = [];
let cnLastCityChange = 0;
let cnWeatherAnim = 0;
let cnTickerX = 0;

// Sapiens Evolution state
let evoStage = 0;
let lastEvoStageChange = 0;
let evoAnimProgress = 0;
let evoGlitchTime = 0;

// Story Mode state
let storyList = [];
let activeStoryIndex = 0;
let activeChapterIndex = 0;
let storyReadingMode = false; // false = browsing, true = reading chapters
let storyTypeIndex = 0;
let storyLastTypeTime = 0;
let storyAudio = null;
let storyImage = null;
let storyIsLoading = false;
let storyTextTyped = "";
let storyImageLoaded = false;

// Fictional shows metadata (Story Mode added as 4th show)
const shows = [
    { name: "Cosmos Cruiser", init: initCosmosCruiser, render: renderCosmosCruiser },
    { name: "Cyber News Network", init: initCyberNews, render: renderCyberNews },
    { name: "Evolution of Sapiens", init: initEvolutionSapiens, render: renderEvolutionSapiens },
    { name: "Story Mode", init: initStoryMode, render: renderStoryMode, handleClick: handleStoryClick }
];

let touchStartX = 0;
let touchStartY = 0;

// FPS counter trackers
let lastFpsTime = 0;
let frameCount = 0;
let currentFps = 60;

function initTvEngine() {
    tvCanvas = document.getElementById("tv-canvas");
    if (!tvCanvas) return;
    tvCtx = tvCanvas.getContext("2d");
    
    window.addEventListener("resize", resizeTv);
    resizeTv();
    
    document.addEventListener("keydown", handleTvInput);

    // Stop propagation on top bar and control strip to prevent accidental channel switching
    const topBar = document.querySelector('.tv-top-bar');
    if (topBar) {
        topBar.addEventListener('click', (e) => e.stopPropagation());
        topBar.addEventListener('touchstart', (e) => e.stopPropagation());
    }
    const controlStrip = document.querySelector('.tv-control-strip');
    if (controlStrip) {
        controlStrip.addEventListener('click', (e) => e.stopPropagation());
        controlStrip.addEventListener('touchstart', (e) => e.stopPropagation());
    }

    // Set up channel dot clicks
    const dots = document.querySelectorAll('.tv-dot');
    dots.forEach((dot, index) => {
        const handler = (e) => {
            e.stopPropagation();
            e.preventDefault();
            if (typeof tvChannel !== 'undefined') {
                tvChannel = index;
                resetChannels();
            }
        };
        dot.addEventListener('click', handler);
        dot.addEventListener('touchstart', handler, {passive: false});
    });
    
    // Intercept clicks directly on the TV canvas to interact with games/stories
    // Calling stopPropagation stops parent offline-tv container from switching channels
    tvCanvas.addEventListener("click", (e) => {
        if (!isOfflineMode) return;
        
        // Snake Game Over click restart
        if (tvChannel === 1) {
            e.stopPropagation();
            if (snakeGameOver) {
                startSnake();
            }
            return;
        }
        
        // Hacker Terminal click/tap
        if (tvChannel === 2) {
            e.stopPropagation();
            hackerTypeKey();
            return;
        }
        
        // Cyber TV click interactions
        if (tvChannel === 3) {
            e.stopPropagation();
            if (shows[currentShowIndex].handleClick) {
                shows[currentShowIndex].handleClick();
            }
            return;
        }
    });

    // Mobile Touch Controls for Snake
    tvCanvas.addEventListener("touchstart", (e) => {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, {passive: true});
    
    tvCanvas.addEventListener("touchend", (e) => {
        if (!isOfflineMode) return;
        
        const touchEndX = e.changedTouches[0].screenX;
        const touchEndY = e.changedTouches[0].screenY;
        handleSwipe(touchStartX, touchStartY, touchEndX, touchEndY);
    }, {passive: true});
}

function handleSwipe(startX, startY, endX, endY) {
    if (tvChannel !== 1) return; // Only process swipes for Snake
    
    if (snakeGameOver) {
        startSnake();
        return;
    }
    
    const dx = endX - startX;
    const dy = endY - startY;
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);
    
    if (absDx < 30 && absDy < 30) return;
    
    if (absDx > absDy) {
        // Horizontal swipe
        if (dx > 0 && snakeDir.x === 0) snakeNextDir = { x: 1, y: 0 };
        else if (dx < 0 && snakeDir.x === 0) snakeNextDir = { x: -1, y: 0 };
    } else {
        // Vertical swipe
        if (dy > 0 && snakeDir.y === 0) snakeNextDir = { x: 0, y: 1 };
        else if (dy < 0 && snakeDir.y === 0) snakeNextDir = { x: 0, y: -1 };
    }
}

function resizeTv() {
    if (!tvCanvas) return;
    tvCanvas.width = tvCanvas.clientWidth || window.innerWidth;
    tvCanvas.height = tvCanvas.clientHeight || window.innerHeight;
    
    // Reset Matrix
    matrixCols = Math.floor(tvCanvas.width / 20) + 1;
    matrixYPos = Array(matrixCols).fill(0);
}

function handleTvInput(e) {
    if (!isOfflineMode) return;
    
    if (e.key.toLowerCase() === 'c') {
        if (typeof nextChannel === 'function') {
            nextChannel();
        } else {
            tvChannel = (tvChannel + 1) % 3;
            resetChannels();
        }
        return;
    }
    
    if (tvChannel === 1) { // Snake controls
        if (e.key === "ArrowUp" || e.key.toLowerCase() === "w") {
            if (snakeDir.y === 0) snakeNextDir = { x: 0, y: -1 };
        } else if (e.key === "ArrowDown" || e.key.toLowerCase() === "s") {
            if (snakeDir.y === 0) snakeNextDir = { x: 0, y: 1 };
        } else if (e.key === "ArrowLeft" || e.key.toLowerCase() === "a") {
            if (snakeDir.x === 0) snakeNextDir = { x: -1, y: 0 };
        } else if (e.key === "ArrowRight" || e.key.toLowerCase() === "d") {
            if (snakeDir.x === 0) snakeNextDir = { x: 1, y: 0 };
        } else if (e.key === " " && snakeGameOver) {
            startSnake();
        }
    } else if (tvChannel === 2) { // Hacker Terminal controls
        e.preventDefault();
        hackerTypeKey();
    }
}

function resetChannels() {
    if (typeof window.playChannelSwitchSound === 'function') {
        window.playChannelSwitchSound();
    }
    
    // Update the channel header title
    const channelTitleEl = document.getElementById("tv-channel-title");
    if (channelTitleEl && typeof tvChannels !== 'undefined' && tvChannels[tvChannel]) {
        channelTitleEl.textContent = `CHANNEL 0${tvChannel + 1}: ${tvChannels[tvChannel].title.toUpperCase()}`;
    }

    // Update active class on dots
    const dots = document.querySelectorAll('.tv-dot');
    dots.forEach((dot, index) => {
        if (index === tvChannel) {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    });

    if (tvChannel === 1) {
        startSnake();
    } else if (tvChannel === 2) {
        initHackerTerminal();
    }
    
    // Safety stop for any active story audio when switching channels
    stopStoryAudio();
    
    const video = document.getElementById('tv-video');
    const canvas = document.getElementById('tv-canvas');
    const movieControls = document.getElementById('tv-movie-controls');
    
    if (video && canvas) {
        video.style.display = 'none';
        video.pause();
        if (movieControls) movieControls.style.display = 'none';
        canvas.style.display = 'block';
    }
}

function changeShow(delta) {
    // Release any music playing in story mode before switching shows
    stopStoryAudio();
    
    currentShowIndex = (currentShowIndex + delta + shows.length) % shows.length;
    shows[currentShowIndex].init();
    updateShowControlsUI();
}

function updateShowControlsUI() {
    const titleSpan = document.getElementById('tv-movie-title');
    if (titleSpan) {
        if (currentShowIndex === 3) {
            if (storyReadingMode && storyList[activeStoryIndex]) {
                const story = storyList[activeStoryIndex];
                titleSpan.textContent = `${story.title} - Ch ${activeChapterIndex + 1}/${story.chapters.length}`;
            } else if (storyList[activeStoryIndex]) {
                titleSpan.textContent = `Story: ${storyList[activeStoryIndex].title} [${activeStoryIndex + 1}/${storyList.length}]`;
            } else {
                titleSpan.textContent = "CH 03 - Story Mode";
            }
        } else {
            titleSpan.textContent = `CH 03 - ${shows[currentShowIndex].name} [${currentShowIndex + 1}/${shows.length}]`;
        }
    }
}

function prevTvMovie() {
    if (currentShowIndex === 3) {
        if (storyReadingMode) {
            if (activeChapterIndex > 0) {
                activeChapterIndex--;
                startChapter();
            } else {
                storyReadingMode = false;
                stopStoryAudio();
            }
        } else {
            if (activeStoryIndex > 0) {
                activeStoryIndex--;
            } else {
                changeShow(-1);
            }
        }
        updateShowControlsUI();
    } else {
        changeShow(-1);
    }
}

function nextTvMovie() {
    if (currentShowIndex === 3) {
        if (storyReadingMode) {
            if (storyList[activeStoryIndex] && activeChapterIndex + 1 < storyList[activeStoryIndex].chapters.length) {
                activeChapterIndex++;
                startChapter();
            } else {
                storyReadingMode = false;
                stopStoryAudio();
            }
        } else {
            if (activeStoryIndex + 1 < storyList.length) {
                activeStoryIndex++;
            } else {
                changeShow(1);
            }
        }
        updateShowControlsUI();
    } else {
        changeShow(1);
    }
}

window.prevTvMovie = prevTvMovie;
window.nextTvMovie = nextTvMovie;

let tvLoopId = null;

function renderTvLoop() {
    if (!isOfflineMode) {
        tvLoopId = null;
        return;
    }
    
    // FPS computation
    const now = Date.now();
    frameCount++;
    if (now - lastFpsTime >= 1000) {
        currentFps = Math.round((frameCount * 1000) / (now - lastFpsTime));
        frameCount = 0;
        lastFpsTime = now;
        const fpsEl = document.getElementById("tv-fps-counter");
        if (fpsEl) fpsEl.textContent = `${currentFps}fps`;
    }

    if (tvCanvas && tvCtx) {
        if (tvChannel === 0) renderMatrix();
        else if (tvChannel === 1) renderSnake();
        else if (tvChannel === 2) renderHackerTerminal();
    }
    tvLoopId = requestAnimationFrame(renderTvLoop);
}

function startTvLoop() {
    if (!tvLoopId) {
        tvLoopId = requestAnimationFrame(renderTvLoop);
    }
}
window.startTvLoop = startTvLoop;

function initProceduralTv() {
    if (shows[currentShowIndex] && typeof shows[currentShowIndex].init === 'function') {
        shows[currentShowIndex].init();
    }
}

function renderProceduralTv() {
    if (shows[currentShowIndex] && typeof shows[currentShowIndex].render === 'function') {
        shows[currentShowIndex].render();
    }
}

// Global safety stop for audio playing in background
function stopStoryAudio() {
    if (storyAudio) {
        try {
            storyAudio.pause();
        } catch (e) {}
        storyAudio = null;
    }
}
window.stopStoryAudio = stopStoryAudio;

// --- RETRO SOUND SYNTHESIZER (0-Storage, Offline Clicks) ---
function playTypewriterClick() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'triangle'; // Smooth mechanical click sound
        osc.frequency.setValueAtTime(400 + Math.random() * 200, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.015, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + 0.04);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.04);
    } catch (e) {}
}

// --- TEXT WRAPPING HELPER FOR CANVAS ---
function drawWrappedText(ctx, text, x, y, maxWidth, lineHeight) {
    const paragraphs = text.split('\n');
    let currentY = y;
    
    paragraphs.forEach(para => {
        const words = para.split(' ');
        let line = '';
        for (let n = 0; n < words.length; n++) {
            let testLine = line + words[n] + ' ';
            let metrics = ctx.measureText(testLine);
            let testWidth = metrics.width;
            if (testWidth > maxWidth && n > 0) {
                ctx.fillText(line, x, currentY);
                line = words[n] + ' ';
                currentY += lineHeight;
            } else {
                line = testLine;
            }
        }
        ctx.fillText(line, x, currentY);
        currentY += lineHeight; // Margin between paragraphs
    });
}

// --- MATRIX RENDERER ---
function renderMatrix() {
    tvCtx.fillStyle = "rgba(0, 0, 0, 0.05)";
    tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
    
    tvCtx.fillStyle = "#0f0";
    tvCtx.font = "15pt monospace";
    
    for (let i = 0; i < matrixCols; i++) {
        const text = String.fromCharCode(Math.random() * 128);
        const x = i * 20;
        const y = matrixYPos[i];
        
        tvCtx.fillText(text, x, y);
        
        if (y > 100 + Math.random() * 10000) {
            matrixYPos[i] = 0;
        } else {
            matrixYPos[i] = y + 20;
        }
    }
}

// --- SNAKE RENDERER ---
function startSnake() {
    snake = [{ x: 10, y: 10 }];
    snakeDir = { x: 1, y: 0 };
    snakeNextDir = { x: 1, y: 0 };
    snakeScore = 0;
    snakeGameOver = false;
    spawnFood();
}

function spawnFood() {
    if (!tvCanvas) return;
    const maxX = Math.floor(tvCanvas.width / snakeGrid) - 1;
    const maxY = Math.floor(tvCanvas.height / snakeGrid) - 1;
    snakeFood = {
        x: Math.floor(Math.random() * maxX),
        y: Math.floor(Math.random() * maxY)
    };
}

function renderSnake() {
    const now = Date.now();
    if (now - lastSnakeUpdate > 100) { // 10fps
        lastSnakeUpdate = now;
        updateSnake();
    }
    
    tvCtx.fillStyle = "#000";
    tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
    
    if (snakeGameOver) {
        tvCtx.fillStyle = "rgba(0,0,0,0.7)";
        tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
        tvCtx.fillStyle = "#0f0";
        tvCtx.font = "40px monospace";
        tvCtx.textAlign = "center";
        tvCtx.fillText("GAME OVER", tvCanvas.width/2, tvCanvas.height/2 - 20);
        tvCtx.font = "20px monospace";
        tvCtx.fillText(`SCORE: ${snakeScore}`, tvCanvas.width/2, tvCanvas.height/2 + 20);
        tvCtx.fillText("PRESS SPACE TO RESTART", tvCanvas.width/2, tvCanvas.height/2 + 60);
        return;
    }
    
    tvCtx.fillStyle = "#f00";
    tvCtx.fillRect(snakeFood.x * snakeGrid, snakeFood.y * snakeGrid, snakeGrid - 1, snakeGrid - 1);
    
    tvCtx.fillStyle = "#0f0";
    for (let i = 0; i < snake.length; i++) {
        tvCtx.fillRect(snake[i].x * snakeGrid, snake[i].y * snakeGrid, snakeGrid - 1, snakeGrid - 1);
    }
    
    tvCtx.fillStyle = "#fff";
    tvCtx.font = "20px monospace";
    tvCtx.textAlign = "left";
    tvCtx.fillText(`SCORE: ${snakeScore}`, 20, 60);
}

function updateSnake() {
    if (snakeGameOver) return;
    
    snakeDir = snakeNextDir;
    const head = { x: snake[0].x + snakeDir.x, y: snake[0].y + snakeDir.y };
    
    const maxX = Math.floor(tvCanvas.width / snakeGrid);
    const maxY = Math.floor(tvCanvas.height / snakeGrid);
    if (head.x < 0 || head.x >= maxX || head.y < 0 || head.y >= maxY) {
        snakeGameOver = true;
        if (window.playBeep) window.playBeep(110, 'sawtooth', 0.5, 0.25);
        return;
    }
    
    for (let i = 0; i < snake.length; i++) {
        if (head.x === snake[i].x && head.y === snake[i].y) {
            snakeGameOver = true;
            if (window.playBeep) window.playBeep(110, 'sawtooth', 0.5, 0.25);
            return;
        }
    }
    
    snake.unshift(head);
    
    if (head.x === snakeFood.x && head.y === snakeFood.y) {
        snakeScore += 10;
        spawnFood();
        if (window.playBeep) window.playBeep(880, 'square', 0.1, 0.1);
    } else {
        snake.pop();
    }
}

// --- HACKER TERMINAL CONFIG ---
let hackerLines = []; // [{text, color}]
let hackerCodePos = 0;
let lastHackerAutoLog = 0;
let hackerCursorBlink = true;
let lastHackerCursorBlink = 0;

// --- COMMAND SEQUENCE STATE MACHINE ---
let hackerPhase = 'idle'; // idle | typing_cmd | pausing | showing_output
let hackerCmdTyped = '';
let hackerCmdTarget = '';
let hackerCmdOutput = [];
let hackerCmdOutputIdx = 0;
let lastHackerCmdTick = 0;
let hackerCmdPauseEnd = 0;
let hackerCmdIdx = 0;

// --- PROGRESS BAR ---
let hackerProgressBar = {active: false, label: '', progress: 0, speed: 0, lastUpdate: 0};

// --- SYSTEM STATS HUD ---
let hackerStats = {cpu: 45, mem: 52, netUp: 2.1, netDown: 5.4, packets: 8241, lastUpdate: 0};

// --- GLITCH STATE ---
let hackerGlitching = false;
let hackerGlitchEnd = 0;
let lastHackerGlitch = 0;
let hackerGlitchNextIn = 20000;

// --- RANDOM NETWORK TOPOLOGY ---
let hackerFakeNetwork = {};

// --- COLOUR MAP ---
const hackerColorMap = {
    '[SUCCESS]': '#00ffcc',
    '[WARN]':    '#ffdd00',
    '[ERROR]':   '#ff0077',
    '[OK]':      '#00ff88',
    '[INFO]':    '#33ff33',
    '[SYSTEM]':  '#cc88ff',
    '[DEBUG]':   '#668866',
    '[STATUS]':  '#ff8800',
    '[NET]':     '#44aaff',
};

function getHackerLineColor(text) {
    for (const [tag, color] of Object.entries(hackerColorMap)) {
        if (text.startsWith(tag)) return color;
    }
    if (text.startsWith('[root@')) return '#ffffff';
    if (text.match(/^\d+\/tcp/)) return '#44aaff';
    if (text.startsWith('Starting') || text.startsWith('Nmap') || text.startsWith('hashcat')) return '#668866';
    return '#33ff33';
}

function addHackerLine(text, color) {
    const c = color || getHackerLineColor(text);
    hackerLines.push({text, color: c});
    const maxVisible = tvCanvas ? Math.floor(tvCanvas.height / 16) - 8 : 30;
    while (hackerLines.length > maxVisible) hackerLines.shift();
}

function generateFakeNetwork() {
    const sub = `192.168.${Math.floor(Math.random()*5)}`;
    const randIP = () => `${sub}.${10 + Math.floor(Math.random()*240)}`;
    const hostWords = ['alpha','beta','gamma','delta','node','proxy','gate','core','edge','vault'];
    const tlds = ['.local','.int','.corp'];
    const hostname = hostWords[Math.floor(Math.random()*hostWords.length)] + '-' + Math.floor(Math.random()*99) + tlds[Math.floor(Math.random()*tlds.length)];
    const allPorts = [
        {port:22,  service:'ssh',      version:'OpenSSH 8.4p1'},
        {port:80,  service:'http',     version:'Apache 2.4.51'},
        {port:443, service:'https',    version:'nginx 1.21.6'},
        {port:3306,service:'mysql',    version:'MySQL 8.0.28'},
        {port:8080,service:'http-alt', version:'Tomcat 9.0.62'},
        {port:6379,service:'redis',    version:'Redis 6.2.6'},
        {port:5432,service:'postgres', version:'PostgreSQL 14.2'},
        {port:21,  service:'ftp',      version:'vsftpd 3.0.3'},
    ];
    const ports = [...allPorts].sort(() => Math.random()-0.5).slice(0, 3 + Math.floor(Math.random()*3));
    const users = ['admin','root','ubuntu','ec2-user','deploy'];
    const dbNames = ['users','accounts','customers','employees','vault'];
    return {
        targetIP:  randIP(),
        gatewayIP: `10.${Math.floor(Math.random()*3)}.0.1`,
        hostname,
        ports,
        user:   users[Math.floor(Math.random()*users.length)],
        dbName: dbNames[Math.floor(Math.random()*dbNames.length)] + '_db',
        pid:    1000 + Math.floor(Math.random()*60000),
        pid2:   1000 + Math.floor(Math.random()*60000),
        hash:   [...Array(32)].map(()=>Math.floor(Math.random()*16).toString(16)).join(''),
    };
}


const hackerPayloadCode = `
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>

int main(int argc, char *argv[]) {
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);
    char buffer[1024] = {0};
    char *hello = "HTTP/1.1 200 OK\\nContent-Type: text/plain\\nContent-Length: 12\\n\\nHello World";

    // Creating socket file descriptor
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }
    
    // Forcefully attaching socket to the port 8080
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt))) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons( 8080 );
    
    // Forcefully attaching socket to the port 8080
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }
    if (listen(server_fd, 3) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }
    
    printf("[*] Listening on port 8080 for incoming connections...\\n");
    while(1) {
        if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen)) < 0) {
            perror("accept");
            exit(EXIT_FAILURE);
        }
        int valread = read( new_socket , buffer, 1024);
        printf("[+] Connection received! Request headers:\\n%s\\n", buffer);
        send(new_socket , hello , strlen(hello) , 0 );
        printf("[-] Response sent. Closing socket connection.\\n");
        close(new_socket);
    }
    return 0;
}
`;

function buildHackerCommands(net) {
    return [
        {
            cmd: `nmap -sV -p- ${net.targetIP}`,
            output: [
                {text:`Starting Nmap 7.94 ( https://nmap.org )`, color:'#668866'},
                {text:`Nmap scan report for ${net.hostname} (${net.targetIP})`, color:'#33ff33'},
                {text:`Host is up (0.024s latency).`, color:'#33ff33'},
                {text:`PORT      STATE  SERVICE    VERSION`, color:'#00ffcc'},
                ...net.ports.map(p=>({text:`${(p.port+'/tcp').padEnd(10)}open   ${p.service.padEnd(11)}${p.version}`, color:'#44aaff'})),
                {text:`Nmap done: 1 IP address scanned in 8.32s`, color:'#668866'},
            ]
        },
        {
            cmd: `ssh ${net.user}@${net.targetIP}`,
            output: [
                {text:`The authenticity of host '${net.targetIP}' can't be established.`, color:'#ffdd00'},
                {text:`RSA key fingerprint: SHA256:${net.hash.slice(0,20)}.`, color:'#668866'},
                {text:`Are you sure you want to continue? yes`, color:'#ffffff'},
                {text:`[WARN] Permanently added '${net.targetIP}' to known hosts.`, color:'#ffdd00'},
                {text:`[SUCCESS] Welcome to ${net.hostname}!`, color:'#00ffcc'},
                {text:`Last login: Mon Jul 06 03:42:11 2026 from ${net.gatewayIP}`, color:'#668866'},
            ]
        },
        {
            cmd: `python3 exploit.py --target ${net.targetIP} --port ${net.ports[0]?.port||80}`,
            output: [
                {text:`[SYSTEM] Loading exploit framework v2.4.1...`, color:'#cc88ff'},
                {text:`[INFO] Target: ${net.targetIP}:${net.ports[0]?.port||80}`, color:'#33ff33'},
                {text:`[DEBUG] Sending probe packets...`, color:'#668866'},
                {text:`[WARN] Firewall detected — initiating bypass...`, color:'#ffdd00'},
                {text:`[SYSTEM] ROP chain injected into process ${net.pid2}`, color:'#cc88ff'},
                {text:`[SUCCESS] Remote code execution achieved! Shell active.`, color:'#00ffcc'},
            ]
        },
        {
            cmd: `hashcat -m 0 hashes.txt rockyou.txt`,
            output: [
                {text:`hashcat (v6.2.6) starting...`, color:'#668866'},
                {text:`[INFO] Device: NVIDIA RTX 4090 (24576 MB)`, color:'#33ff33'},
                {text:`[STATUS] Speed: 45,231.4 MH/s`, color:'#ff8800'},
                {text:`[STATUS] Progress: 14,344,391/14,344,391 (100%)`, color:'#ff8800'},
                {text:`[SUCCESS] ${net.hash.slice(0,28)}:password123`, color:'#00ffcc'},
                {text:`[OK] Session complete.`, color:'#00ff88'},
            ]
        },
        {
            cmd: `sqlmap -u http://${net.targetIP}/login --dump --batch`,
            output: [
                {text:`[SYSTEM] sqlmap 1.7.8 — automatic SQL injection`, color:'#cc88ff'},
                {text:`[INFO] Testing connection to target URL...`, color:'#33ff33'},
                {text:`[INFO] Parameter 'username' is injectable (UNION based)`, color:'#33ff33'},
                {text:`[STATUS] Dumping table: ${net.dbName}...`, color:'#ff8800'},
                {text:`[STATUS] Retrieved 4,291 rows`, color:'#ff8800'},
                {text:`[SUCCESS] Saved to /tmp/${net.dbName}.csv`, color:'#00ffcc'},
            ]
        },
    ];
}

function buildHackerIdleLogs(net) {
    return [
        `[INFO] Gateway: ${net.gatewayIP} — RTT 4ms`,
        `[DEBUG] Scanning subnet ${net.targetIP.split('.').slice(0,3).join('.')}.0/24...`,
        `[INFO] Port ${net.ports[0]?.port||22}/tcp [${net.ports[0]?.service||'ssh'}] open on ${net.targetIP}`,
        `[WARN] SSH Banner: 'Dropbear sshd 2018.76'`,
        `[SYSTEM] Loading brute force dictionary (rockyou.txt)...`,
        `[STATUS] Brute force speed: 450 attempts/sec`,
        `[INFO] Attempting ${net.user}:${net.user}...`,
        `[INFO] Attempting admin:admin123...`,
        `[SUCCESS] Credential match: ${net.user}:password123`,
        `[SYSTEM] Opening interactive shell session...`,
        `[STATUS] Shell spawned on tty1 (PID: ${net.pid})`,
        `[DEBUG] Injecting rootkit payload into /boot/...`,
        `[SYSTEM] Clearing authentication logs...`,
        `[OK] System footprint erased.`,
        `[INFO] Downloading ${net.dbName}.sql (4.2MB)`,
        `[SYSTEM] Decrypting database hashes (SHA-256)...`,
        `[SUCCESS] Hash cracked: ${net.hash.slice(0,16)}...`,
        `[NET] Routing tables redirected via ${net.gatewayIP}`,
        `[DEBUG] ARP cache poisoned: ${net.targetIP} → ${net.gatewayIP}`,
        `[INFO] Process ${net.pid2} hijacked successfully`,
    ];
}

let hackerCommands = [];
let hackerIdleLogs = [];
let hackerIdleLogIdx = 0;

function initHackerTerminal() {
    hackerFakeNetwork = generateFakeNetwork();
    hackerCommands = buildHackerCommands(hackerFakeNetwork);
    hackerIdleLogs = buildHackerIdleLogs(hackerFakeNetwork);
    hackerIdleLogIdx = 0;
    
    hackerLines = [];
    addHackerLine('════════════════════════════════════════════════', '#00ffcc');
    addHackerLine('     CYBER COMMAND CENTER — TERMINAL V1.0.4     ', '#00ffcc');
    addHackerLine('════════════════════════════════════════════════', '#00ffcc');
    addHackerLine(`[root@cybernode]# target set: ${hackerFakeNetwork.hostname} (${hackerFakeNetwork.targetIP})`, '#ffffff');
    addHackerLine('[SYSTEM] Initializing core subsystems...', '#cc88ff');
    
    hackerCodePos = 0;
    hackerPhase = 'idle';
    hackerCmdTyped = '';
    hackerCmdTarget = '';
    hackerCmdOutput = [];
    hackerCmdOutputIdx = 0;
    hackerCmdIdx = 0;
    lastHackerAutoLog = Date.now();
    lastHackerCmdTick = Date.now();
    hackerCmdPauseEnd = Date.now() + 3500;
    lastHackerCursorBlink = Date.now();
    hackerCursorBlink = true;
    hackerProgressBar = {active: false, label: '', progress: 0, speed: 0, lastUpdate: 0};
    hackerStats = {
        cpu: 20 + Math.floor(Math.random()*60),
        mem: 30 + Math.floor(Math.random()*50),
        netUp: 0.5 + Math.random()*5,
        netDown: 1 + Math.random()*10,
        packets: Math.floor(Math.random()*20000),
        lastUpdate: 0
    };
    hackerGlitching = false;
    hackerGlitchEnd = 0;
    lastHackerGlitch = Date.now();
    hackerGlitchNextIn = 15000 + Math.random()*20000;
}

function hackerTypeKey() {
    if (typeof window.playKeyClick === 'function') window.playKeyClick();
    const count = 3 + Math.floor(Math.random() * 3);
    for (let i = 0; i < count; i++) {
        if (hackerCodePos >= hackerPayloadCode.length) hackerCodePos = 0;
        const char = hackerPayloadCode[hackerCodePos++];
        if (char === '\n') {
            addHackerLine('', '#33ff33');
        } else {
            if (hackerLines.length === 0) addHackerLine('', '#33ff33');
            hackerLines[hackerLines.length - 1].text += char;
        }
    }
}

function renderHackerTerminal() {
    const now = Date.now();
    tvCtx.textAlign = 'left';
    tvCtx.textBaseline = 'alphabetic';
    
    // ── 1. GLITCH CHECK ──────────────────────────────────────
    if (!hackerGlitching && (now - lastHackerGlitch) > hackerGlitchNextIn) {
        hackerGlitching = true;
        hackerGlitchEnd = now + 100 + Math.random() * 180;
        lastHackerGlitch = now;
        hackerGlitchNextIn = 15000 + Math.random() * 20000;
        if (window.playNoise) window.playNoise(0.12, 0.07);
    }
    if (hackerGlitching && now > hackerGlitchEnd) hackerGlitching = false;
    
    // ── 2. BACKGROUND ────────────────────────────────────────
    tvCtx.fillStyle = 'rgba(3, 8, 3, 0.18)';
    tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
    
    // ── 3. GLITCH FRAME ──────────────────────────────────────
    if (hackerGlitching) {
        tvCtx.font = '11px monospace';
        const glitchChars = '█▓▒░│─┼╬╔╗╚╝═║ABCDEFabcdef0123456789!@#$%^&*';
        const cols = Math.floor(tvCanvas.width / 8);
        const rows = Math.floor(tvCanvas.height / 13);
        const glitchColors = ['#00ff00','#ff0077','#00ffff','#ffff00','#ffffff','#ff8800'];
        for (let r = 0; r < rows; r++) {
            if (Math.random() > 0.45) continue;
            tvCtx.fillStyle = glitchColors[Math.floor(Math.random() * glitchColors.length)];
            for (let c = 0; c < cols; c++) {
                tvCtx.fillText(glitchChars[Math.floor(Math.random() * glitchChars.length)], c * 8, r * 13 + 11);
            }
        }
        return;
    }
    
    // ── 4. UPDATE LIVE STATS ─────────────────────────────────
    if (now - hackerStats.lastUpdate > 900) {
        hackerStats.lastUpdate = now;
        hackerStats.cpu     = Math.max(5,  Math.min(99, hackerStats.cpu     + (Math.random()-0.45)*12));
        hackerStats.mem     = Math.max(10, Math.min(95, hackerStats.mem     + (Math.random()-0.50)*5));
        hackerStats.netUp   = Math.max(0.1, hackerStats.netUp   + (Math.random()-0.5)*1.5);
        hackerStats.netDown = Math.max(0.1, hackerStats.netDown + (Math.random()-0.5)*2.0);
        hackerStats.packets += Math.floor(Math.random() * 900);
    }
    
    // ── 5. ANIMATE PROGRESS BAR ──────────────────────────────
    if (hackerProgressBar.active && now - hackerProgressBar.lastUpdate > 80) {
        hackerProgressBar.lastUpdate = now;
        hackerProgressBar.progress = Math.min(100, hackerProgressBar.progress + hackerProgressBar.speed);
        if (hackerProgressBar.progress >= 100) {
            hackerProgressBar.active = false;
            addHackerLine(`[OK] ${hackerProgressBar.label} complete.`, '#00ff88');
        }
    }
    
    // ── 6. COMMAND SEQUENCE STATE MACHINE ────────────────────
    if (hackerPhase === 'idle') {
        if (now - lastHackerAutoLog > 1100) {
            lastHackerAutoLog = now;
            const log = hackerIdleLogs[hackerIdleLogIdx % hackerIdleLogs.length];
            hackerIdleLogIdx++;
            addHackerLine(log);
            if (window.playKeyClick) window.playKeyClick();
            // Trigger progress bars on relevant logs
            if (!hackerProgressBar.active) {
                if (log.includes('Downloading')) {
                    hackerProgressBar = {active:true, label:'Download',    progress:0, speed:1.2+Math.random(),     lastUpdate:now};
                } else if (log.includes('brute force')) {
                    hackerProgressBar = {active:true, label:'Brute force', progress:0, speed:0.6+Math.random()*0.8, lastUpdate:now};
                } else if (log.includes('Decrypting')) {
                    hackerProgressBar = {active:true, label:'Decryption',  progress:0, speed:0.9+Math.random(),     lastUpdate:now};
                }
            }
        }
        if (now > hackerCmdPauseEnd + 4000) {
            // Start next command sequence
            hackerPhase = 'typing_cmd';
            const cmdObj = hackerCommands[hackerCmdIdx % hackerCommands.length];
            hackerCmdTarget = `[root@cybernode]# ${cmdObj.cmd}`;
            hackerCmdOutput = cmdObj.output;
            hackerCmdTyped  = '';
            hackerCmdOutputIdx = 0;
            hackerCmdIdx++;
            lastHackerCmdTick = now;
            addHackerLine('', '#33ff33');
        }
    } else if (hackerPhase === 'typing_cmd') {
        if (now - lastHackerCmdTick > 55) {
            lastHackerCmdTick = now;
            if (hackerCmdTyped.length < hackerCmdTarget.length) {
                hackerCmdTyped += hackerCmdTarget[hackerCmdTyped.length];
                if (window.playKeyClick) window.playKeyClick();
                if (hackerLines.length > 0) {
                    hackerLines[hackerLines.length - 1].text = hackerCmdTyped;
                } else {
                    addHackerLine(hackerCmdTyped, '#ffffff');
                }
            } else {
                hackerPhase = 'pausing';
                hackerCmdPauseEnd = now + 300 + Math.random() * 500;
            }
        }
    } else if (hackerPhase === 'pausing') {
        if (now > hackerCmdPauseEnd) {
            hackerPhase = 'showing_output';
            lastHackerCmdTick = now;
        }
    } else if (hackerPhase === 'showing_output') {
        if (now - lastHackerCmdTick > 200) {
            lastHackerCmdTick = now;
            if (hackerCmdOutputIdx < hackerCmdOutput.length) {
                const ln = hackerCmdOutput[hackerCmdOutputIdx++];
                addHackerLine(ln.text, ln.color);
            } else {
                addHackerLine('', '#33ff33');
                hackerPhase = 'idle';
                hackerCmdPauseEnd = now;
            }
        }
    }
    
    // ── 7. CURSOR BLINK ──────────────────────────────────────
    if (now - lastHackerCursorBlink > 500) {
        hackerCursorBlink = !hackerCursorBlink;
        lastHackerCursorBlink = now;
    }
    
    // ── 8. LAYOUT AREAS ──────────────────────────────────────
    const panelW    = 172;
    const textAreaW = tvCanvas.width - panelW - 18;
    const lineH     = 16;
    const startY    = 18;
    
    // ── 9. DRAW LOG LINES ─────────────────────────────────────
    tvCtx.font     = '11px monospace';
    tvCtx.shadowBlur = 3;
    for (let i = 0; i < hackerLines.length; i++) {
        const ln = hackerLines[i];
        tvCtx.fillStyle  = ln.color || '#33ff33';
        tvCtx.shadowColor = ln.color || '#33ff33';
        let text = ln.text;
        if (i === hackerLines.length - 1 && hackerCursorBlink && hackerPhase !== 'typing_cmd') {
            text += '█';
        }
        tvCtx.fillText(text, 10, startY + i * lineH, textAreaW);
    }
    
    // ── 10. DRAW PROGRESS BAR ────────────────────────────────
    if (hackerProgressBar.active) {
        const filled = Math.floor((hackerProgressBar.progress / 100) * 28);
        const empty  = 28 - filled;
        const bar    = '[' + '='.repeat(filled) + (filled < 28 ? '>' : '') + ' '.repeat(Math.max(0, empty-1)) + ']';
        tvCtx.fillStyle  = '#ff8800';
        tvCtx.shadowColor = '#ff8800';
        tvCtx.shadowBlur  = 4;
        tvCtx.fillText(`${hackerProgressBar.label}: ${bar} ${Math.floor(hackerProgressBar.progress)}%`, 10, tvCanvas.height - 12);
    }
    
    // ── 11. DRAW STATS PANEL ─────────────────────────────────
    const px = tvCanvas.width - panelW - 4;
    const py = 12;
    const ph = 148;
    
    tvCtx.fillStyle = 'rgba(0, 18, 0, 0.75)';
    tvCtx.fillRect(px, py, panelW, ph);
    tvCtx.strokeStyle = '#33ff33';
    tvCtx.shadowColor = '#33ff33';
    tvCtx.shadowBlur  = 5;
    tvCtx.lineWidth   = 1;
    tvCtx.strokeRect(px, py, panelW, ph);
    
    const statBar = (val, max, len=10) => '█'.repeat(Math.round((val/max)*len)) + '░'.repeat(len - Math.round((val/max)*len));
    const cpuColor = hackerStats.cpu > 80 ? '#ff4444' : hackerStats.cpu > 60 ? '#ff8800' : '#33ff33';
    const memColor = hackerStats.mem > 80 ? '#ff4444' : '#33ff33';
    
    tvCtx.font = '10px monospace';
    tvCtx.textAlign = 'left';
    tvCtx.textBaseline = 'alphabetic';
    const panelLines = [
        {text:'╔ NODE STATUS ════╗', color:'#00ffcc'},
        {text:`CPU ${statBar(hackerStats.cpu,100,8)} ${Math.floor(hackerStats.cpu)}%`, color:cpuColor},
        {text:`MEM ${statBar(hackerStats.mem,100,8)} ${Math.floor(hackerStats.mem)}%`, color:memColor},
        {text:`↑ ${hackerStats.netUp.toFixed(1).padStart(4)} MB/s`, color:'#44aaff'},
        {text:`↓ ${hackerStats.netDown.toFixed(1).padStart(4)} MB/s`, color:'#44aaff'},
        {text:`PKT ${hackerStats.packets.toLocaleString()}`, color:'#ff8800'},
        {text:`PID ${hackerFakeNetwork.pid||28419}`, color:'#cc88ff'},
        {text:`TGT ${hackerFakeNetwork.targetIP||'192.168.1.x'}`, color:'#ff4444'},
        {text:`HST ${hackerFakeNetwork.hostname||'node-01.local'}`, color:'#ff4444'},
        {text:'╚═══════════════╝', color:'#00ffcc'},
    ];
    panelLines.forEach((ln, i) => {
        tvCtx.fillStyle  = ln.color;
        tvCtx.shadowColor = ln.color;
        tvCtx.shadowBlur  = 2;
        tvCtx.fillText(ln.text, px + 6, py + 14 + i * 14);
    });
    
    tvCtx.shadowBlur = 0;
}

// ==========================================
// --- SHOW 1: COSMOS CRUISER ---
// ==========================================
function initCosmosCruiser() {
    ccStars = [];
    for (let i = 0; i < 80; i++) {
        ccStars.push({
            x: (Math.random() - 0.5) * 800,
            y: (Math.random() - 0.5) * 800,
            z: Math.random() * 800
        });
    }
    ccPlanets = [];
    ccLogs = [
        "WARP INITIATED",
        "SYSTEMS OPERATIONAL: 100%",
        "WARPING TO SECTOR DELTA-9..."
    ];
    ccLastLog = Date.now();
}

function renderCosmosCruiser() {
    tvCtx.fillStyle = "#02020a";
    tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
    
    const cx = tvCanvas.width / 2;
    const cy = tvCanvas.height / 2;
    
    // Starfield warp
    tvCtx.fillStyle = "#fff";
    ccStars.forEach(s => {
        s.z -= 8;
        if (s.z <= 0) {
            s.z = 800;
            s.x = (Math.random() - 0.5) * 800;
            s.y = (Math.random() - 0.5) * 800;
        }
        
        const px = (s.x / s.z) * 400 + cx;
        const py = (s.y / s.z) * 400 + cy;
        const size = (1 - s.z / 800) * 4;
        
        if (px >= 0 && px < tvCanvas.width && py >= 0 && py < tvCanvas.height) {
            tvCtx.fillRect(px, py, size, size);
        }
    });
    
    // Planet drift
    if (ccPlanets.length === 0 && Math.random() < 0.01) {
        const colors = ["#ff5e36", "#3d85c6", "#6aa84f", "#e69138", "#8e7cc3"];
        ccPlanets.push({
            x: tvCanvas.width + 100,
            y: cy + (Math.random() - 0.5) * 200,
            r: 40 + Math.random() * 40,
            color: colors[Math.floor(Math.random() * colors.length)],
            speed: 0.5 + Math.random() * 0.5,
            rings: Math.random() > 0.5
        });
    }
    
    ccPlanets.forEach((p, idx) => {
        p.x -= p.speed;
        
        tvCtx.fillStyle = p.color;
        tvCtx.beginPath();
        tvCtx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        tvCtx.fill();
        
        const grad = tvCtx.createRadialGradient(p.x - p.r/3, p.y - p.r/3, p.r/10, p.x, p.y, p.r);
        grad.addColorStop(0, "rgba(255,255,255,0.2)");
        grad.addColorStop(0.8, "rgba(0,0,0,0.6)");
        grad.addColorStop(1, "rgba(0,0,0,0.95)");
        tvCtx.fillStyle = grad;
        tvCtx.beginPath();
        tvCtx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        tvCtx.fill();
        
        if (p.rings) {
            tvCtx.strokeStyle = "rgba(255,255,255,0.4)";
            tvCtx.lineWidth = 4;
            tvCtx.beginPath();
            tvCtx.ellipse(p.x, p.y, p.r * 1.6, p.r * 0.3, Math.PI/6, 0, Math.PI * 2);
            tvCtx.stroke();
        }
        
        if (p.x < -200) ccPlanets.splice(idx, 1);
    });
    
    // Spacecraft HUD grid lines
    tvCtx.strokeStyle = "rgba(0, 255, 255, 0.4)";
    tvCtx.lineWidth = 2;
    tvCtx.beginPath();
    tvCtx.arc(cx, cy, 50, 0, Math.PI * 2);
    tvCtx.stroke();
    
    tvCtx.beginPath();
    tvCtx.moveTo(cx - 70, cy); tvCtx.lineTo(cx - 20, cy);
    tvCtx.moveTo(cx + 20, cy); tvCtx.lineTo(cx + 70, cy);
    tvCtx.moveTo(cx, cy - 70); tvCtx.lineTo(cx, cy - 20);
    tvCtx.moveTo(cx, cy + 20); tvCtx.lineTo(cx, cy + 70);
    tvCtx.stroke();
    
    tvCtx.strokeStyle = "rgba(0, 255, 255, 0.15)";
    for (let i = 0; i <= tvCanvas.width; i += 80) {
        tvCtx.beginPath();
        tvCtx.moveTo(i, tvCanvas.height);
        tvCtx.lineTo(cx + (i - cx) * 0.2, cy + 100);
        tvCtx.stroke();
    }
    
    // Logs update
    const logEvents = [
        "Scanning planetary bodies...",
        "Asteroid belt ahead - adjusting shields",
        "Warp speed constant at Warp 9.7",
        "Energy signature detected in Sector 4",
        "Honeypot ping: Intruder blocked",
        "Analyzing nebula composition...",
        "Telemetry stable. Communication online",
        "Oxygen levels: 98% | Fuel: 74%"
    ];
    if (Date.now() - ccLastLog > 4000) {
        ccLogs.push(logEvents[Math.floor(Math.random() * logEvents.length)]);
        if (ccLogs.length > 5) ccLogs.shift();
        ccLastLog = Date.now();
    }
    
    tvCtx.fillStyle = "rgba(0, 0, 0, 0.8)";
    tvCtx.strokeStyle = "var(--cyan)";
    tvCtx.lineWidth = 2;
    tvCtx.fillRect(20, tvCanvas.height - 120, tvCanvas.width - 40, 100);
    tvCtx.strokeRect(20, tvCanvas.height - 120, tvCanvas.width - 40, 100);
    
    tvCtx.fillStyle = "var(--cyan)";
    tvCtx.font = "11px monospace";
    tvCtx.textAlign = "left";
    for (let i = 0; i < ccLogs.length; i++) {
        tvCtx.fillText(`> ${ccLogs[i]}`, 40, tvCanvas.height - 100 + i * 16);
    }
}

// ==========================================
// --- SHOW 2: CYBER NEWS NETWORK (CNN8) ---
// ==========================================
function initCyberNews() {
    cnNews = [
        "HACKER GROUP 'ANTIGRAVITY' ACCUSED OF STEALING DIGITAL CAKE INDEX...",
        "HONEYPOT PORT 22 BLOCKS MALICIOUS SCAN FROM KNOWN HOSTILE BOTNET...",
        "COFFEEMAKER DEMANDS CRYPTO RANSOM IN OFFICE BREAKROOM REBELLION...",
        "WARNING: SOLAR STORM THREATENS RETRO DIGITAL TV CHANNELS GLOBALLY...",
        "NEW BRUTALISM STYLING OFFICIALLY DECLARED RADICAL BY CASINO GAMBLERS...",
        "CYBER CREDITS ECONOMY BOOMING AFTER RECENT CRASH GAME HIGH-SCORE..."
    ];
    cnCities = [
        { name: "NEON VALLEY", temp: "22C", weather: "Acid Rain" },
        { name: "CYBER CITY", temp: "15C", weather: "Toxic Fog" },
        { name: "MATRIX CORE", temp: "99C", weather: "Overheating" },
        { name: "DARKNET VOID", temp: "-273C", weather: "Abs. Zero" },
        { name: "DOOM SECTOR", temp: "666C", weather: "Lava Rain" }
    ];
    cnNewsIdx = 0;
    cnCityIdx = 0;
    cnLastCityChange = Date.now();
    cnWeatherAnim = 0;
    cnTickerX = tvCanvas.width;
}

function renderCyberNews() {
    tvCtx.fillStyle = "#0c051c";
    tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
    
    tvCtx.fillStyle = "#1e0b3c";
    tvCtx.fillRect(0, 0, tvCanvas.width, 60);
    tvCtx.strokeStyle = "var(--purple)";
    tvCtx.lineWidth = 3;
    tvCtx.beginPath();
    tvCtx.moveTo(0, 60);
    tvCtx.lineTo(tvCanvas.width, 60);
    tvCtx.stroke();
    
    const headerPulse = 180 + Math.sin(Date.now() / 200) * 75;
    tvCtx.fillStyle = `rgb(${headerPulse}, 0, 255)`;
    tvCtx.font = "bold 20px monospace";
    tvCtx.textAlign = "center";
    tvCtx.fillText("CNN8: CYBER ARCHIVE BROADCAST", tvCanvas.width / 2, 38);
    
    const splitX = tvCanvas.width / 2;
    tvCtx.strokeStyle = "var(--purple)";
    tvCtx.beginPath();
    tvCtx.moveTo(splitX, 60);
    tvCtx.lineTo(splitX, tvCanvas.height - 60);
    tvCtx.stroke();
    
    if (Date.now() - cnLastCityChange > 5000) {
        cnCityIdx = (cnCityIdx + 1) % cnCities.length;
        cnLastCityChange = Date.now();
    }
    
    const city = cnCities[cnCityIdx];
    
    // Left pane
    tvCtx.fillStyle = "#fff";
    tvCtx.font = "14px monospace";
    tvCtx.textAlign = "left";
    tvCtx.fillText("LOCAL CYBER FORECAST", 30, 95);
    
    tvCtx.fillStyle = "var(--cyan)";
    tvCtx.font = "bold 24px monospace";
    tvCtx.fillText(city.name, 30, 140);
    
    tvCtx.fillStyle = "#fff";
    tvCtx.font = "16px monospace";
    tvCtx.fillText(`TEMP: ${city.temp}`, 30, 180);
    tvCtx.fillText(`WEATHER: ${city.weather}`, 30, 210);
    
    cnWeatherAnim += 0.05;
    if (city.weather.includes("Rain")) {
        tvCtx.fillStyle = "#555";
        tvCtx.beginPath();
        tvCtx.arc(280, 130, 25, 0, Math.PI*2);
        tvCtx.arc(310, 130, 30, 0, Math.PI*2);
        tvCtx.arc(330, 130, 20, 0, Math.PI*2);
        tvCtx.fill();
        
        tvCtx.strokeStyle = "#00ffff";
        for (let i = 0; i < 8; i++) {
            const rx = 270 + i * 10;
            const ry = 150 + ((cnWeatherAnim * 50 + i * 15) % 40);
            tvCtx.beginPath();
            tvCtx.moveTo(rx, ry);
            tvCtx.lineTo(rx - 2, ry + 8);
            tvCtx.stroke();
        }
    } else if (city.weather.includes("Fog") || city.weather.includes("Zero")) {
        tvCtx.strokeStyle = "rgba(255,255,255,0.2)";
        for (let i = 0; i < 4; i++) {
            const my = 130 + i * 20;
            const mx_offset = Math.sin(cnWeatherAnim + i) * 15;
            tvCtx.beginPath();
            tvCtx.moveTo(260 + mx_offset, my);
            tvCtx.bezierCurveTo(280 + mx_offset, my - 10, 320 + mx_offset, my + 10, 340 + mx_offset, my);
            tvCtx.stroke();
        }
    } else {
        const sunRadius = 25 + Math.sin(cnWeatherAnim) * 5;
        tvCtx.fillStyle = "#ff5e36";
        tvCtx.beginPath();
        tvCtx.arc(300, 150, sunRadius, 0, Math.PI*2);
        tvCtx.fill();
        
        tvCtx.strokeStyle = "#ffb000";
        for (let a = 0; a < 8; a++) {
            const angle = a * (Math.PI / 4) + cnWeatherAnim/2;
            const x1 = 300 + Math.cos(angle) * (sunRadius + 5);
            const y1 = 150 + Math.sin(angle) * (sunRadius + 5);
            const x2 = 300 + Math.cos(angle) * (sunRadius + 20);
            const y2 = 150 + Math.sin(angle) * (sunRadius + 20);
            tvCtx.beginPath();
            tvCtx.moveTo(x1, y1);
            tvCtx.lineTo(x2, y2);
            tvCtx.stroke();
        }
    }
    
    // Right pane
    tvCtx.fillStyle = "#fff";
    tvCtx.font = "14px monospace";
    tvCtx.fillText("FIREWALL SECURITY FEED", splitX + 30, 95);
    
    tvCtx.fillStyle = "rgba(0,255,0,0.8)";
    tvCtx.font = "11px monospace";
    tvCtx.fillText("[OK] HONEYPOT PORT 21 ARMED", splitX + 30, 130);
    tvCtx.fillText("[OK] HONEYPOT PORT 22 ARMED", splitX + 30, 150);
    tvCtx.fillText("[OK] HONEYPOT PORT 23 ARMED", splitX + 30, 170);
    
    tvCtx.strokeStyle = "rgba(0, 255, 0, 0.3)";
    tvCtx.lineWidth = 1;
    const graphY = 190;
    tvCtx.beginPath();
    tvCtx.rect(splitX + 30, graphY, splitX - 60, 45);
    tvCtx.stroke();
    
    tvCtx.beginPath();
    for (let x = 0; x < splitX - 60; x += 10) {
        const h = 20 + Math.sin((x + cnWeatherAnim * 40) / 20) * 15;
        if (x === 0) tvCtx.moveTo(splitX + 30 + x, graphY + 45 - h);
        else tvCtx.lineTo(splitX + 30 + x, graphY + 45 - h);
    }
    tvCtx.stroke();
    
    // Ticker
    tvCtx.fillStyle = "#000";
    tvCtx.fillRect(0, tvCanvas.height - 50, tvCanvas.width, 50);
    tvCtx.strokeStyle = "var(--purple)";
    tvCtx.lineWidth = 2;
    tvCtx.strokeRect(0, tvCanvas.height - 50, tvCanvas.width, 50);
    
    cnTickerX -= 2.0;
    const tickerText = `*** NEWS FEED: ${cnNews[cnNewsIdx]} ***`;
    tvCtx.fillStyle = "var(--purple)";
    tvCtx.font = "bold 15px monospace";
    tvCtx.textAlign = "left";
    tvCtx.fillText(tickerText, cnTickerX, tvCanvas.height - 20);
    
    const textWidth = tvCtx.measureText(tickerText).width;
    if (cnTickerX + textWidth < 0) {
        cnTickerX = tvCanvas.width;
        cnNewsIdx = (cnNewsIdx + 1) % cnNews.length;
    }
}

// ==========================================
// --- SHOW 3: EVOLUTION OF SAPIENS ---
// ==========================================
function initEvolutionSapiens() {
    evoStage = 0;
    lastEvoStageChange = Date.now();
    evoAnimProgress = 0;
    evoGlitchTime = 0;
}

function renderEvolutionSapiens() {
    const now = Date.now();
    const elapsed = now - lastEvoStageChange;
    
    if (elapsed > 10000) {
        evoStage = (evoStage + 1) % 4;
        lastEvoStageChange = now;
        evoGlitchTime = 15;
    }
    
    tvCtx.fillStyle = "#020803";
    tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
    
    const cx = tvCanvas.width / 2;
    const cy = tvCanvas.height / 2;
    
    const stageTitles = [
        "STAGE 01 - BIO-GENESIS [ORGANIC CELL]",
        "STAGE 02 - HOMO SAPIENS [COGNITIVE WALKER]",
        "STAGE 03 - AUGMENTED LIFE [CYBERNETIC CYBORG]",
        "STAGE 04 - THE SINGULARITY [SINGLE DIGITAL ENTITY]"
    ];
    
    tvCtx.fillStyle = "rgba(0, 255, 0, 0.7)";
    tvCtx.font = "bold 13px monospace";
    tvCtx.textAlign = "center";
    tvCtx.fillText(stageTitles[evoStage], cx, 40);
    
    if (evoGlitchTime > 0) {
        evoGlitchTime--;
        tvCtx.fillStyle = "rgba(0,255,0,0.15)";
        for (let i = 0; i < 5; i++) {
            const gy = Math.random() * tvCanvas.height;
            const gh = 10 + Math.random() * 30;
            const gx = (Math.random() - 0.5) * 50;
            tvCtx.fillRect(0, gy, tvCanvas.width, gh);
            tvCtx.drawImage(tvCanvas, gx, gy, tvCanvas.width, gh, 0, gy, tvCanvas.width, gh);
        }
        return;
    }
    
    evoAnimProgress += 0.05;
    
    if (evoStage === 0) {
        const cellRadius = 50;
        tvCtx.fillStyle = "rgba(0, 255, 0, 0.5)";
        tvCtx.strokeStyle = "#00ff00";
        tvCtx.lineWidth = 3;
        
        const dX = Math.sin(evoAnimProgress) * 40;
        
        tvCtx.beginPath();
        tvCtx.arc(cx - dX, cy, cellRadius + Math.sin(evoAnimProgress * 2) * 5, 0, Math.PI*2);
        tvCtx.fill();
        tvCtx.stroke();
        
        tvCtx.beginPath();
        tvCtx.arc(cx + dX, cy, cellRadius + Math.cos(evoAnimProgress * 2) * 5, 0, Math.PI*2);
        tvCtx.fill();
        tvCtx.stroke();
        
        tvCtx.fillStyle = "#00ff00";
        tvCtx.beginPath();
        tvCtx.arc(cx - dX, cy, 10, 0, Math.PI*2);
        tvCtx.arc(cx + dX, cy, 10, 0, Math.PI*2);
        tvCtx.fill();
        
    } else if (evoStage === 1) {
        const groundY = cy + 100;
        tvCtx.strokeStyle = "#00ff00";
        tvCtx.lineWidth = 2;
        tvCtx.beginPath();
        tvCtx.moveTo(0, groundY);
        tvCtx.lineTo(tvCanvas.width, groundY);
        tvCtx.stroke();
        
        const walkCycle = evoAnimProgress * 1.5;
        const hipX = cx;
        const hipY = cy;
        
        const leftFootX = hipX + Math.sin(walkCycle) * 20;
        const leftFootY = groundY;
        const rightFootX = hipX + Math.cos(walkCycle) * 20;
        const rightFootY = groundY;
        
        const ageProgress = (elapsed / 10000);
        const hunch = 20 - ageProgress * 20;
        const spineH = 50;
        const headX = hipX + hunch;
        const headY = hipY - spineH + Math.sin(walkCycle * 2) * 4;
        
        tvCtx.strokeStyle = "#00ff00";
        tvCtx.fillStyle = "#00ff00";
        tvCtx.lineWidth = 4;
        
        tvCtx.beginPath();
        tvCtx.arc(headX, headY, 12, 0, Math.PI*2);
        tvCtx.fill();
        
        tvCtx.beginPath();
        tvCtx.moveTo(headX, headY);
        tvCtx.lineTo(hipX, hipY);
        tvCtx.stroke();
        
        tvCtx.beginPath();
        tvCtx.moveTo(hipX, hipY);
        tvCtx.lineTo(hipX + Math.sin(walkCycle) * 10, hipY + 40);
        tvCtx.lineTo(leftFootX, leftFootY);
        tvCtx.stroke();
        
        tvCtx.beginPath();
        tvCtx.moveTo(hipX, hipY);
        tvCtx.lineTo(hipX + Math.cos(walkCycle) * 10, hipY + 40);
        tvCtx.lineTo(rightFootX, rightFootY);
        tvCtx.stroke();
        
        const shoulderX = headX + (hipX - headX) * 0.2;
        const shoulderY = headY + (hipY - headY) * 0.2;
        
        if (ageProgress < 0.5) {
            tvCtx.beginPath();
            tvCtx.moveTo(shoulderX, shoulderY);
            tvCtx.lineTo(shoulderX - 20, shoulderY + 30);
            tvCtx.stroke();
            
            tvCtx.strokeStyle = "#855";
            tvCtx.lineWidth = 6;
            tvCtx.beginPath();
            tvCtx.moveTo(shoulderX - 20, shoulderY + 30);
            tvCtx.lineTo(shoulderX - 35, shoulderY + 15);
            tvCtx.stroke();
        } else {
            tvCtx.beginPath();
            tvCtx.moveTo(shoulderX, shoulderY);
            tvCtx.lineTo(shoulderX + 15, shoulderY + 15);
            tvCtx.lineTo(shoulderX + 25, shoulderY + 5);
            tvCtx.stroke();
            
            tvCtx.fillStyle = "#00ffff";
            tvCtx.fillRect(shoulderX + 23, shoulderY + 2, 6, 10);
            
            tvCtx.fillStyle = "rgba(0, 255, 255, 0.3)";
            tvCtx.beginPath();
            tvCtx.moveTo(shoulderX + 25, shoulderY);
            tvCtx.lineTo(shoulderX + 60, shoulderY - 30);
            tvCtx.lineTo(shoulderX + 60, shoulderY + 10);
            tvCtx.fill();
        }
        
    } else if (evoStage === 2) {
        tvCtx.strokeStyle = "#00ff00";
        tvCtx.lineWidth = 2;
        
        tvCtx.beginPath();
        tvCtx.moveTo(cx - 60, cy - 80);
        tvCtx.quadraticCurveTo(cx - 100, cy - 80, cx - 100, cy);
        tvCtx.lineTo(cx - 80, cy + 80);
        
        tvCtx.moveTo(cx - 60, cy - 80);
        tvCtx.lineTo(cx + 30, cy - 60);
        tvCtx.lineTo(cx + 25, cy - 20);
        tvCtx.lineTo(cx + 45, cy - 15);
        tvCtx.lineTo(cx + 25, cy - 5);
        tvCtx.lineTo(cx + 30, cy + 10);
        tvCtx.lineTo(cx + 20, cy + 15);
        tvCtx.lineTo(cx + 28, cy + 25);
        tvCtx.lineTo(cx + 15, cy + 45);
        tvCtx.lineTo(cx - 40, cy + 50);
        tvCtx.lineTo(cx - 80, cy + 80);
        tvCtx.stroke();
        
        tvCtx.fillStyle = "#00ffff";
        tvCtx.beginPath();
        tvCtx.arc(cx + 10, cy - 25, 6, 0, Math.PI*2);
        tvCtx.fill();
        
        tvCtx.strokeStyle = "rgba(0, 255, 0, 0.4)";
        tvCtx.lineWidth = 1.5;
        tvCtx.beginPath();
        tvCtx.moveTo(cx - 90, cy + 20);
        tvCtx.lineTo(cx - 50, cy + 20);
        tvCtx.lineTo(cx - 30, cy - 10);
        tvCtx.lineTo(cx + 5, cy - 10);
        tvCtx.stroke();
        
        tvCtx.fillStyle = "rgba(0, 255, 0, 0.15)";
        tvCtx.font = "8px monospace";
        tvCtx.textAlign = "left";
        for (let i = 0; i < 5; i++) {
            const bx = cx - 70 + i * 15;
            const by = cy - 50 + ((evoAnimProgress * 15 + i * 20) % 80);
            tvCtx.fillText((Math.random() > 0.5 ? "1" : "0"), bx, by);
        }
        
    } else if (evoStage === 3) {
        tvCtx.strokeStyle = "#00ff00";
        tvCtx.lineWidth = 2;
        
        const angleX = evoAnimProgress * 0.3;
        const angleY = evoAnimProgress * 0.4;
        
        const size = 60;
        const vertices = [
            { x: -size, y: -size, z: -size },
            { x: size, y: -size, z: -size },
            { x: size, y: size, z: -size },
            { x: -size, y: size, z: -size },
            { x: -size, y: -size, z: size },
            { x: size, y: -size, z: size },
            { x: size, y: size, z: size },
            { x: -size, y: size, z: size }
        ];
        
        const edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],
            [4, 5], [5, 6], [6, 7], [7, 4],
            [0, 4], [1, 5], [2, 6], [3, 7]
        ];
        
        const projected = [];
        vertices.forEach(v => {
            let y1 = v.y * Math.cos(angleX) - v.z * Math.sin(angleX);
            let z1 = v.y * Math.sin(angleX) + v.z * Math.cos(angleX);
            let x2 = v.x * Math.cos(angleY) - z1 * Math.sin(angleY);
            let z2 = v.x * Math.sin(angleY) + z1 * Math.cos(angleY);
            
            const distance = 300;
            const scale = distance / (distance + z2);
            projected.push({
                x: x2 * scale + cx,
                y: y1 * scale + cy
            });
        });
        
        edges.forEach(edge => {
            const p1 = projected[edge[0]];
            const p2 = projected[edge[1]];
            tvCtx.beginPath();
            tvCtx.moveTo(p1.x, p1.y);
            tvCtx.lineTo(p2.x, p2.y);
            tvCtx.stroke();
        });
        
        projected.forEach(p => {
            tvCtx.fillStyle = "#00ff00";
            tvCtx.beginPath();
            tvCtx.arc(p.x, p.y, 4, 0, Math.PI*2);
            tvCtx.fill();
        });
        
        tvCtx.fillStyle = "rgba(0, 255, 0, 0.6)";
        tvCtx.font = "bold 14px monospace";
        tvCtx.textAlign = "center";
        tvCtx.fillText("SINGULARITY ACTIVE", cx, cy + 120);
        
        const floatProgress = (elapsed / 10000);
        tvCtx.fillStyle = `rgba(0, 255, 0, ${1 - floatProgress})`;
        tvCtx.font = "9px monospace";
        tvCtx.fillText("CONSCIOUSNESS INTEGRATED: 100%", cx, cy - 110);
        tvCtx.fillText("ENTITY STATUS: STABLE", cx, cy - 95);
    }
}

// ==========================================
// --- SHOW 4: CINEMATIC STORY MODE ---
// ==========================================
function initStoryMode() {
    storyReadingMode = false;
    activeStoryIndex = 0;
    activeChapterIndex = 0;
    storyTypeIndex = 0;
    storyTextTyped = "";
    storyIsLoading = true;
    storyList = [];
    storyImageLoaded = false;
    stopStoryAudio();
    
    fetchStoryList();
}

async function fetchStoryList() {
    try {
        if (window.location.protocol === 'file:') {
            throw new Error("Local file protocol detected, skipping network request");
        }
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1500);
        
        const res = await fetch("/api/story-proxy", { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (res.ok) {
            const data = await res.json();
            if (data.ok && data.stories && data.stories.length > 0) {
                storyList = data.stories;
            }
        }
    } catch (e) {
        console.error("Story Mode fetch failed or timed out:", e);
    } finally {
        if (!storyList || storyList.length === 0) {
            console.log("[Story Mode] Offline or file protocol detected. Loading local fallback chronicles.");
            storyList = getFallbackStories();
        }
        storyIsLoading = false;
        updateShowControlsUI();
    }
}

function getFallbackStories() {
    return [
        {
            "id": "cyber-1",
            "title": "Neon Grid Syndicate",
            "synopsis": "A rogue decker attempts to infiltrate the mainframe of a corrupt megastructure.",
            "theme": "cyberpunk",
            "chapters": [
                {
                    "title": "Chapter 1: The Breach",
                    "text": "The rain fell like static over the neon spires of Neo-Minato. Kael checked his cyberdeck. The firewall of the Megacorp was down, but the grid was alive. He had 30 seconds to copy the data before the security AI fried his brain...",
                    "image": "https://images.unsplash.com/photo-1515621061946-eff1c2a352bd?w=600&auto=format&fit=crop",
                    "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
                },
                {
                    "title": "Chapter 2: Netrunner Escape",
                    "text": "Sirens wailed in the physical world as Kael pulled the jack. His synapses sizzled from the feedback loop. Grabbing his coat, he slipped into the dark alleyways. Cybernetic enforcement guards were already closing in on his location...",
                    "image": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=600&auto=format&fit=crop",
                    "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
                }
            ]
        },
        {
            "id": "tactical-1",
            "title": "Operation Blackout",
            "synopsis": "An elite spec-ops team is deployed to disable a hijacked satellite tracking station.",
            "theme": "tactical",
            "chapters": [
                {
                    "title": "Chapter 1: Insertion",
                    "text": "The transport chopper hovered silently in the freezing mountain air. Sergeant Miller checked his night-vision goggles. 'Green light, go, go, go,' he whispered. One by one, the team rappelled into the snowy dark...",
                    "image": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=600&auto=format&fit=crop",
                    "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"
                },
                {
                    "title": "Chapter 2: Under Fire",
                    "text": "Sparks flew as a bullet clipped the console next to Miller. The tracking station was heavily fortified. 'Suppressing fire!' he roared, firing his carbine into the shadows. They had to upload the virus before dawn...",
                    "image": "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&auto=format&fit=crop",
                    "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3"
                }
            ]
        },
        {
            "id": "fantasy-1",
            "title": "The Last Rune",
            "synopsis": "A young wizard uncovers the secret to unlocking the dragon gates of Oakhaven.",
            "theme": "fantasy",
            "chapters": [
                {
                    "title": "Chapter 1: The Crypt",
                    "text": "Eldrin traced the glowing rune on the ancient stone door. Deep in the Catacombs of Oakhaven, the whispers of the sleeping dragon grew louder. He raised his staff, the blue crystal radiating light, and spoke the command word...",
                    "image": "https://images.unsplash.com/photo-1519074002996-a69e7ac46a42?w=600&auto=format&fit=crop",
                    "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3"
                },
                {
                    "title": "Chapter 2: Awakening",
                    "text": "With a low rumble, the stone door ground open. Gold and bones lay piled high in the cavern. In the center, a pair of ancient yellow eyes opened. The dragon breathed a low growl, waiting for the wizard to speak...",
                    "image": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600&auto=format&fit=crop",
                    "music": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3"
                }
            ]
        }
    ];
}

function handleStoryClick() {
    if (storyIsLoading) return;
    
    // 1. Browsing screen tap -> Select story & start reading Chapter 1
    if (!storyReadingMode) {
        if (storyList.length === 0) {
            storyIsLoading = true;
            fetchStoryList();
            return;
        }
        storyReadingMode = true;
        activeChapterIndex = 0;
        startChapter();
        updateShowControlsUI();
        return;
    }
    
    // 2. Reading screen tap -> Interactivity
    const story = storyList[activeStoryIndex];
    const chapter = story.chapters[activeChapterIndex];
    
    if (storyTypeIndex < chapter.text.length) {
        // Fast-forward text if typing is in progress
        storyTypeIndex = chapter.text.length;
        storyTextTyped = chapter.text;
    } else {
        // Move to next chapter or exit to browser if complete
        if (activeChapterIndex + 1 < story.chapters.length) {
            activeChapterIndex++;
            startChapter();
            updateShowControlsUI();
        } else {
            storyReadingMode = false;
            stopStoryAudio();
            updateShowControlsUI();
        }
    }
}

function startChapter() {
    storyTypeIndex = 0;
    storyTextTyped = "";
    storyLastTypeTime = Date.now();
    storyImageLoaded = false;
    
    const story = storyList[activeStoryIndex];
    const chapter = story.chapters[activeChapterIndex];
    
    // Load thematic illustration in background
    storyImage = new Image();
    storyImage.onload = () => { storyImageLoaded = true; };
    storyImage.src = chapter.image;
    
    // Load and stream background track
    stopStoryAudio();
    storyAudio = new Audio(chapter.music);
    storyAudio.loop = true;
    storyAudio.volume = 0.25;
    storyAudio.play().catch(e => console.log("Music autoplay blocked:", e));
}

function renderStoryMode() {
    const cx = tvCanvas.width / 2;
    const cy = tvCanvas.height / 2;
    
    // Draw background
    tvCtx.fillStyle = "#030206";
    tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
    
    if (storyIsLoading) {
        tvCtx.fillStyle = "rgba(0, 255, 255, 0.8)";
        tvCtx.font = "bold 16px monospace";
        tvCtx.textAlign = "center";
        tvCtx.fillText("LOADING LORE REGISTRY...", cx, cy);
        return;
    }
    
    if (storyList.length === 0) {
        tvCtx.fillStyle = "#ff3b30";
        tvCtx.font = "bold 14px monospace";
        tvCtx.textAlign = "center";
        tvCtx.fillText("CONNECTION TO LORE ARCHIVE TIMED OUT.", cx, cy - 20);
        tvCtx.fillStyle = "#fff";
        tvCtx.font = "12px monospace";
        tvCtx.fillText("TAP SCREEN TO RETRY CONNECTION", cx, cy + 20);
        return;
    }
    
    const story = storyList[activeStoryIndex];
    
    if (!storyReadingMode) {
        // --- SCREEN A: STORY BROWSING SELECTION ---
        // Title banner
        tvCtx.fillStyle = "var(--purple)";
        tvCtx.font = "bold 20px monospace";
        tvCtx.textAlign = "center";
        tvCtx.fillText("SELECT YOUR ARCHIVE CHRONICLE", cx, 65);
        
        // Active Story Card Container
        const cardW = Math.min(500, tvCanvas.width - 60);
        const cardH = 220;
        const cardX = cx - cardW / 2;
        const cardY = cy - 80;
        
        tvCtx.fillStyle = "rgba(10, 5, 25, 0.9)";
        tvCtx.strokeStyle = "var(--purple)";
        tvCtx.lineWidth = 3;
        tvCtx.fillRect(cardX, cardY, cardW, cardH);
        tvCtx.strokeRect(cardX, cardY, cardW, cardH);
        
        // Theme Badge Color Code (cyberpunk / tactical / fantasy)
        let themeColor = "var(--cyan)";
        if (story.theme === "fantasy") themeColor = "var(--orange)";
        if (story.theme === "tactical") themeColor = "var(--yellow)";
        
        tvCtx.fillStyle = themeColor;
        tvCtx.font = "bold 12px monospace";
        tvCtx.textAlign = "left";
        tvCtx.fillText(`THEME: ${story.theme.toUpperCase()}`, cardX + 30, cardY + 35);
        
        // Title
        tvCtx.fillStyle = "#fff";
        tvCtx.font = "bold 22px monospace";
        tvCtx.fillText(story.title.toUpperCase(), cardX + 30, cardY + 70);
        
        // Synopsis
        tvCtx.fillStyle = "#ccc";
        tvCtx.font = "13px monospace";
        drawWrappedText(tvCtx, story.synopsis, cardX + 30, cardY + 110, cardW - 60, 18);
        
        // Instructions
        tvCtx.fillStyle = "rgba(0, 255, 255, 0.7)";
        tvCtx.font = "bold 12px monospace";
        tvCtx.textAlign = "center";
        tvCtx.fillText("TAP SCREEN TO CHOOSE THIS CHRONICLE", cx, cy + 180);
        tvCtx.fillStyle = "#888";
        tvCtx.font = "11px monospace";
        tvCtx.fillText("PRESS NEXT TO CYCLE TO OTHER LORE STORIES", cx, cy + 205);
        
    } else {
        // --- SCREEN B: CINEMATIC CHAPTER READING MODE ---
        const chapter = story.chapters[activeChapterIndex];
        
        // Render Cover Image
        if (storyImageLoaded) {
            tvCtx.drawImage(storyImage, 0, 0, tvCanvas.width, tvCanvas.height);
        }
        
        // Draw dark cinematic overlay
        tvCtx.fillStyle = "rgba(0,0,0,0.65)";
        tvCtx.fillRect(0, 0, tvCanvas.width, tvCanvas.height);
        
        // Render headers
        tvCtx.fillStyle = "rgba(0, 255, 255, 0.8)";
        tvCtx.font = "bold 11px monospace";
        tvCtx.textAlign = "left";
        tvCtx.fillText(`CHRONICLE: ${story.title.toUpperCase()}`, 30, 45);
        
        tvCtx.fillStyle = "#fff";
        tvCtx.font = "bold 15px monospace";
        tvCtx.fillText(chapter.title.toUpperCase(), 30, 70);
        
        // Text Typewriter loop
        const now = Date.now();
        if (storyTypeIndex < chapter.text.length && now - storyLastTypeTime > 30) {
            storyTypeIndex++;
            storyTextTyped = chapter.text.slice(0, storyTypeIndex);
            storyLastTypeTime = now;
            
            // Play click sound on typing ticks (safely ignored if blocked by browser)
            playTypewriterClick();
        }
        
        // Dialogue Box at Bottom
        const boxH = 170;
        const boxY = tvCanvas.height - boxH - 20;
        const boxW = tvCanvas.width - 40;
        
        tvCtx.fillStyle = "rgba(5, 5, 10, 0.95)";
        tvCtx.strokeStyle = "var(--cyan)";
        tvCtx.lineWidth = 3;
        tvCtx.fillRect(20, boxY, boxW, boxH);
        tvCtx.strokeRect(20, boxY, boxW, boxH);
        
        // Dialogue inner text
        tvCtx.fillStyle = "#fff";
        tvCtx.font = "13px monospace";
        tvCtx.textAlign = "left";
        drawWrappedText(tvCtx, storyTextTyped, 45, boxY + 35, boxW - 50, 20);
        
        // Bottom Right flashing arrow once text is completely shown
        const isDone = storyTypeIndex >= chapter.text.length;
        if (isDone) {
            const arrowFlash = Math.floor(now / 500) % 2;
            if (arrowFlash === 0) {
                tvCtx.fillStyle = "var(--cyan)";
                tvCtx.font = "bold 14px monospace";
                tvCtx.textAlign = "right";
                tvCtx.fillText("▼", tvCanvas.width - 40, tvCanvas.height - 35);
            }
        }
        
        // Prompts
        tvCtx.fillStyle = "rgba(0, 255, 255, 0.4)";
        tvCtx.font = "9px monospace";
        tvCtx.textAlign = "right";
        if (!isDone) {
            tvCtx.fillText("[TAP SCREEN TO SKIP TYPING]", tvCanvas.width - 40, boxY - 12);
        } else {
            const isLast = activeChapterIndex + 1 >= story.chapters.length;
            const hint = isLast ? "[TAP SCREEN TO FINISH LORE]" : `[TAP SCREEN TO ADVANCE TO CHAPTER ${activeChapterIndex + 2}]`;
            tvCtx.fillText(hint, tvCanvas.width - 40, boxY - 12);
        }
        
        // Return instructions on control bar
        const titleSpan = document.getElementById('tv-movie-title');
        if (titleSpan) {
            titleSpan.textContent = `CH 03 - READING: ${story.title} (${activeChapterIndex+1}/${story.chapters.length})`;
        }
    }
}

function bootstrapTvEngine() {
    initTvEngine();
    requestAnimationFrame(renderTvLoop);
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", bootstrapTvEngine);
} else {
    bootstrapTvEngine();
}
