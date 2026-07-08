// Cyber Casino - Optimized & Graphically Pleasing Cyber Tetris
(function() {
    const COLS = 10;
    const ROWS = 20;
    const CELL_SIZE = 20; // 200x400 canvas

    let board = [];
    let canvas, ctx;
    let nextCanvas, nextCtx;
    let holdCanvas, holdCtx;
    
    let score = 0;
    let lines = 0;
    let level = 1;
    
    let currentPiece = null;
    let nextPiece = null;
    let holdPiece = null;
    let holdUsed = false;
    
    let gameLoopId = null;
    let dropCounter = 0;
    let lastTime = 0;
    let dropInterval = 1000;
    
    let isPaused = false;
    let isGameOver = false;
    let isGameActive = false;
    
    let lineClearAnimation = null; // Stores lines currently clearing for animation
    let screenShakeTime = 0;

    const keys = {
        left: false,
        right: false,
        down: false
    };
    let activeDirection = null; // 'left' or 'right'
    let dasTime = 0;
    let arrTime = 0;
    let softDropTime = 0;

    const SHAPES = {
        'I': [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]],
        'O': [[1,1],[1,1]],
        'T': [[0,1,0],[1,1,1],[0,0,0]],
        'S': [[0,1,1],[1,1,0],[0,0,0]],
        'Z': [[1,1,0],[0,1,1],[0,0,0]],
        'J': [[1,0,0],[1,1,1],[0,0,0]],
        'L': [[0,0,1],[1,1,1],[0,0,0]]
    };

    const COLORS = {
        'I': '#33ccff', // Cyan
        'O': '#ffcc00', // Yellow
        'T': '#ff3366', // Hot Pink
        'S': '#00e699', // Green
        'Z': '#ff3366', // Red
        'J': '#33ccff', // Blue
        'L': '#ff6600'  // Orange
    };

    function initTetris() {
        canvas = document.getElementById('tetris-canvas');
        if (!canvas) return;
        ctx = canvas.getContext('2d');
        
        nextCanvas = document.getElementById('tetris-next-canvas');
        nextCtx = nextCanvas.getContext('2d');
        
        holdCanvas = document.getElementById('tetris-hold-canvas');
        holdCtx = holdCanvas.getContext('2d');

        // Clear boards
        resetBoard();
        
        // Listeners for keyboard controls
        document.removeEventListener('keydown', handleKeyDown);
        document.removeEventListener('keyup', handleKeyUp);
        document.addEventListener('keydown', handleKeyDown);
        document.addEventListener('keyup', handleKeyUp);
    }

    function resetBoard() {
        board = Array.from({ length: ROWS }, () => new Array(COLS).fill(0));
    }

    function createPiece(type) {
        return {
            matrix: JSON.parse(JSON.stringify(SHAPES[type])),
            x: Math.floor((COLS - SHAPES[type][0].length) / 2),
            y: type === 'I' ? -1 : 0,
            type: type
        };
    }

    function getRandomPieceType() {
        const types = ['I', 'O', 'T', 'S', 'Z', 'J', 'L'];
        return types[Math.floor(Math.random() * types.length)];
    }

    function startTetrisGame() {
        if (typeof window.deductCredits === 'function') {
            if (!window.deductCredits(50)) {
                if (typeof showToast === 'function') {
                    showToast("Insufficient credits! Cost is 50 ₡.", "error");
                } else {
                    alert("Insufficient credits! Cost is 50 ₡.");
                }
                return;
            }
        }

        // Setup screen displays
        document.getElementById('tetris-start-screen').style.display = 'none';
        document.getElementById('tetris-gameover-overlay').style.display = 'none';
        document.getElementById('tetris-game-container').style.display = 'flex';
        document.getElementById('tetris-toolbar').style.display = 'flex';

        // Reset state variables
        resetBoard();
        score = 0;
        lines = 0;
        level = 1;
        dropInterval = 1000;
        holdPiece = null;
        holdUsed = false;
        isPaused = false;
        isGameOver = false;
        isGameActive = true;
        
        updateScoreUI();

        // Initialize pieces
        nextPiece = createPiece(getRandomPieceType());
        spawnPiece();

        // Run game loop
        lastTime = performance.now();
        if (gameLoopId) cancelAnimationFrame(gameLoopId);
        gameLoopId = requestAnimationFrame(gameLoop);
    }

    function spawnPiece() {
        currentPiece = nextPiece;
        nextPiece = createPiece(getRandomPieceType());
        holdUsed = false;

        // Check if block overlaps instantly (Game Over)
        if (checkCollision(currentPiece.matrix, currentPiece.x, currentPiece.y)) {
            triggerGameOver();
        }

        drawNextPiece();
    }

    function checkCollision(matrix, offsetCol, offsetRow) {
        for (let r = 0; r < matrix.length; r++) {
            for (let c = 0; c < matrix[r].length; c++) {
                if (matrix[r][c] !== 0) {
                    const boardCol = offsetCol + c;
                    const boardRow = offsetRow + r;

                    // Wall boundaries
                    if (boardCol < 0 || boardCol >= COLS || boardRow >= ROWS) {
                        return true;
                    }

                    // Existing block overlap (ignore top buffer zone check)
                    if (boardRow >= 0 && board[boardRow][boardCol] !== 0) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    function mergePiece() {
        const matrix = currentPiece.matrix;
        for (let r = 0; r < matrix.length; r++) {
            for (let c = 0; c < matrix[r].length; c++) {
                if (matrix[r][c] !== 0) {
                    const boardRow = currentPiece.y + r;
                    const boardCol = currentPiece.x + c;
                    if (boardRow >= 0) {
                        board[boardRow][boardCol] = currentPiece.type;
                    }
                }
            }
        }
        // Small screen shake on piece land
        triggerScreenShake(3);
    }

    function rotatePiece() {
        const matrix = currentPiece.matrix;
        const n = matrix.length;
        const rotated = Array.from({ length: n }, () => new Array(n).fill(0));
        
        for (let r = 0; r < n; r++) {
            for (let c = 0; c < n; c++) {
                rotated[c][n - 1 - r] = matrix[r][c];
            }
        }

        // Basic wall-kick test
        let originalX = currentPiece.x;
        let offset = 0;
        
        while (checkCollision(rotated, currentPiece.x, currentPiece.y) && offset < 3) {
            offset++;
            currentPiece.x += (offset % 2 === 0) ? -offset : offset;
        }

        if (!checkCollision(rotated, currentPiece.x, currentPiece.y)) {
            currentPiece.matrix = rotated;
        } else {
            // Revert X
            currentPiece.x = originalX;
        }
    }

    function dropPiece() {
        currentPiece.y++;
        if (checkCollision(currentPiece.matrix, currentPiece.x, currentPiece.y)) {
            currentPiece.y--;
            mergePiece();
            checkLineClears();
            spawnPiece();
        }
        dropCounter = 0;
    }

    function hardDropPiece() {
        if (!isGameActive || isPaused || isGameOver) return;
        let count = 0;
        while (!checkCollision(currentPiece.matrix, currentPiece.x, currentPiece.y + 1)) {
            currentPiece.y++;
            count++;
        }
        mergePiece();
        checkLineClears();
        spawnPiece();
        dropCounter = 0;
        
        // Larger screen shake on hard drop
        triggerScreenShake(8);
    }

    function holdCurrentPiece() {
        if (holdUsed || !isGameActive || isPaused || isGameOver) return;

        if (holdPiece === null) {
            holdPiece = { type: currentPiece.type };
            currentPiece = nextPiece;
            nextPiece = createPiece(getRandomPieceType());
        } else {
            const temp = holdPiece.type;
            holdPiece = { type: currentPiece.type };
            currentPiece = createPiece(temp);
        }

        holdUsed = true;
        drawHoldPiece();
    }

    function checkLineClears() {
        let clearedIndexes = [];
        for (let r = ROWS - 1; r >= 0; r--) {
            if (board[r].every(val => val !== 0)) {
                clearedIndexes.push(r);
            }
        }

        if (clearedIndexes.length > 0) {
            // Trigger flashing white clear animation
            lineClearAnimation = {
                rows: clearedIndexes,
                start: performance.now(),
                duration: 120 // ms
            };
            
            // Wait for clear animation to complete before adjusting stats
            setTimeout(() => {
                clearedIndexes.forEach(rowIndex => {
                    board.splice(rowIndex, 1);
                    board.unshift(new Array(COLS).fill(0));
                });
                lineClearAnimation = null;
                
                // Calculate Credits reward & stats
                const count = clearedIndexes.length;
                lines += count;
                level = Math.floor(lines / 10) + 1;
                dropInterval = Math.max(50, 1000 - (level - 1) * 100);

                let pointsEarned = 0;
                let creditsEarned = 0;

                if (count === 1) {
                    pointsEarned = 100;
                    creditsEarned = 10;
                } else if (count === 2) {
                    pointsEarned = 300;
                    creditsEarned = 25;
                } else if (count === 3) {
                    pointsEarned = 500;
                    creditsEarned = 45;
                } else if (count === 4) {
                    pointsEarned = 800; // Tetris!
                    creditsEarned = 100;
                    triggerScreenShake(15); // Maximum shake!
                    if (typeof showToast === 'function') {
                        showToast("🔥 TETRIS BONUS! +100 ₡", "success");
                    }
                }

                score += pointsEarned * level;
                
                // Pay user credits
                if (typeof window.addCredits === 'function' && creditsEarned > 0) {
                    window.addCredits(creditsEarned);
                }

                updateScoreUI();
            }, 120);
        }
    }

    function getGhostY() {
        let ghostY = currentPiece.y;
        while (!checkCollision(currentPiece.matrix, currentPiece.x, ghostY + 1)) {
            ghostY++;
        }
        return ghostY;
    }

    function triggerScreenShake(intensity) {
        screenShakeTime = intensity;
    }

    function updateScoreUI() {
        document.getElementById('tetris-score').innerText = score;
        document.getElementById('tetris-lines').innerText = lines;
    }

    function triggerGameOver() {
        isGameOver = true;
        isGameActive = false;
        if (gameLoopId) cancelAnimationFrame(gameLoopId);
        
        document.getElementById('tetris-final-score').innerText = score;
        document.getElementById('tetris-final-lines').innerText = lines;
        document.getElementById('tetris-gameover-overlay').style.display = 'flex';
    }

    function toggleTetrisPause() {
        if (!isGameActive || isGameOver) return;
        isPaused = !isPaused;
        const btn = document.getElementById('tetris-btn-pause');
        if (isPaused) {
            btn.innerText = "RESUME";
            btn.style.background = "var(--yellow)";
            btn.style.color = "#000";
        } else {
            btn.innerText = "PAUSE";
            btn.style.background = "var(--bg-card)";
            btn.style.color = "var(--text-primary)";
            lastTime = performance.now();
            gameLoopId = requestAnimationFrame(gameLoop);
        }
        draw();
    }

    function quitTetrisGame() {
        isGameActive = false;
        isPaused = false;
        if (gameLoopId) cancelAnimationFrame(gameLoopId);
        
        // Reset key states
        keys.left = false;
        keys.right = false;
        keys.down = false;
        activeDirection = null;
        
        document.getElementById('tetris-game-container').style.display = 'none';
        document.getElementById('tetris-toolbar').style.display = 'none';
        document.getElementById('tetris-start-screen').style.display = 'flex';
    }

    // Expose globally so casino_engine can kill loop on tab switch
    window.quitTetrisGame = quitTetrisGame;

    function moveLeft() {
        if (!currentPiece) return;
        currentPiece.x--;
        if (checkCollision(currentPiece.matrix, currentPiece.x, currentPiece.y)) {
            currentPiece.x++;
        }
    }

    function moveRight() {
        if (!currentPiece) return;
        currentPiece.x++;
        if (checkCollision(currentPiece.matrix, currentPiece.x, currentPiece.y)) {
            currentPiece.x--;
        }
    }

    function updateControls(deltaTime) {
        if (activeDirection) {
            dasTime += deltaTime;
            if (dasTime >= 170) { // DAS threshold (170ms)
                arrTime += deltaTime;
                while (arrTime >= 30) { // ARR speed (30ms per shift)
                    if (activeDirection === 'left') {
                        moveLeft();
                    } else if (activeDirection === 'right') {
                        moveRight();
                    }
                    arrTime -= 30;
                }
            }
        }
        
        if (keys.down) {
            softDropTime += deltaTime;
            while (softDropTime >= 40) { // Soft drop repeat speed (40ms per step)
                dropPiece();
                softDropTime -= 40;
            }
        }
    }

    function handleKeyDown(e) {
        if (!isGameActive || isPaused || isGameOver) return;

        // Block page scrolling for game controls keys
        if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space"].includes(e.code)) {
            e.preventDefault();
        }

        switch (e.code) {
            case 'ArrowLeft':
            case 'KeyA':
                if (!keys.left) {
                    keys.left = true;
                    activeDirection = 'left';
                    dasTime = 0;
                    arrTime = 0;
                    moveLeft();
                }
                break;
            case 'ArrowRight':
            case 'KeyD':
                if (!keys.right) {
                    keys.right = true;
                    activeDirection = 'right';
                    dasTime = 0;
                    arrTime = 0;
                    moveRight();
                }
                break;
            case 'ArrowDown':
            case 'KeyS':
                if (!keys.down) {
                    keys.down = true;
                    softDropTime = 0;
                    dropPiece();
                }
                break;
            case 'ArrowUp':
            case 'KeyW':
                rotatePiece();
                break;
            case 'Space':
                hardDropPiece();
                break;
            case 'KeyC':
            case 'ShiftLeft':
            case 'ShiftRight':
                holdCurrentPiece();
                break;
            case 'KeyP':
                toggleTetrisPause();
                break;
        }
        draw();
    }

    function handleKeyUp(e) {
        switch (e.code) {
            case 'ArrowLeft':
            case 'KeyA':
                keys.left = false;
                if (activeDirection === 'left') {
                    activeDirection = keys.right ? 'right' : null;
                    dasTime = 0;
                }
                break;
            case 'ArrowRight':
            case 'KeyD':
                keys.right = false;
                if (activeDirection === 'right') {
                    activeDirection = keys.left ? 'left' : null;
                    dasTime = 0;
                }
                break;
            case 'ArrowDown':
            case 'KeyS':
                keys.down = false;
                break;
        }
    }

    function gameLoop(time) {
        if (!isGameActive || isPaused || isGameOver) return;

        const deltaTime = time - lastTime;
        lastTime = time;

        updateControls(deltaTime);

        dropCounter += deltaTime;
        if (dropCounter > dropInterval) {
            dropPiece();
        }

        draw();
        gameLoopId = requestAnimationFrame(gameLoop);
    }

    // Draw functions (Optimized canvas renders)
    function drawBlock(ctx, x, y, color, size, isGhost = false) {
        ctx.save();
        if (isGhost) {
            ctx.fillStyle = 'rgba(255,255,255,0.06)';
            ctx.strokeStyle = 'rgba(255,204,0,0.3)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([3, 3]);
            ctx.fillRect(x, y, size, size);
            ctx.strokeRect(x + 1, y + 1, size - 2, size - 2);
        } else {
            ctx.fillStyle = color;
            ctx.strokeStyle = '#111';
            ctx.lineWidth = 2;
            ctx.fillRect(x, y, size, size);
            ctx.strokeRect(x, y, size, size);
            
            // Bevel highlights and shadow overlays (Neo-Brutalist look)
            ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
            ctx.fillRect(x + 2, y + 2, size - 6, 3); // top highlight
            ctx.fillRect(x + 2, y + 5, 3, size - 8); // left highlight
            
            ctx.fillStyle = 'rgba(0, 0, 0, 0.25)';
            ctx.fillRect(x + size - 5, y + 2, 3, size - 4); // right shadow
            ctx.fillRect(x + 2, y + size - 5, size - 4, 3); // bottom shadow
        }
        ctx.restore();
    }

    function draw() {
        ctx.save();
        
        // Handle screen shake logic
        if (screenShakeTime > 0) {
            const dx = (Math.random() - 0.5) * screenShakeTime;
            const dy = (Math.random() - 0.5) * screenShakeTime;
            ctx.translate(dx, dy);
            screenShakeTime *= 0.8;
            if (screenShakeTime < 0.5) screenShakeTime = 0;
        }

        // 1. Clear main board
        ctx.fillStyle = '#050a0e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // 2. Draw grid backdrop
        ctx.strokeStyle = '#10171d';
        ctx.lineWidth = 1;
        for (let c = 0; c <= COLS; c++) {
            ctx.beginPath();
            ctx.moveTo(c * CELL_SIZE, 0);
            ctx.lineTo(c * CELL_SIZE, ROWS * CELL_SIZE);
            ctx.stroke();
        }
        for (let r = 0; r <= ROWS; r++) {
            ctx.beginPath();
            ctx.moveTo(0, r * CELL_SIZE);
            ctx.lineTo(COLS * CELL_SIZE, r * CELL_SIZE);
            ctx.stroke();
        }

        // 3. Draw stationary board blocks
        for (let r = 0; r < ROWS; r++) {
            for (let c = 0; c < COLS; c++) {
                if (board[r][c] !== 0) {
                    // Check if current row is undergoing line-clear flashing
                    if (lineClearAnimation && lineClearAnimation.rows.includes(r)) {
                        ctx.fillStyle = '#ffffff';
                        ctx.strokeStyle = '#111';
                        ctx.lineWidth = 2;
                        ctx.fillRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
                        ctx.strokeRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE);
                    } else {
                        drawBlock(ctx, c * CELL_SIZE, r * CELL_SIZE, COLORS[board[r][c]], CELL_SIZE);
                    }
                }
            }
        }

        // 4. Draw falling block preview (Ghost Piece)
        if (currentPiece && !isPaused && !isGameOver) {
            const ghostY = getGhostY();
            const matrix = currentPiece.matrix;
            for (let r = 0; r < matrix.length; r++) {
                for (let c = 0; c < matrix[r].length; c++) {
                    if (matrix[r][c] !== 0) {
                        const drawY = (ghostY + r) * CELL_SIZE;
                        if (drawY >= 0) {
                            drawBlock(ctx, (currentPiece.x + c) * CELL_SIZE, drawY, null, CELL_SIZE, true);
                        }
                    }
                }
            }
        }

        // 5. Draw active falling piece
        if (currentPiece && !isPaused && !isGameOver) {
            const matrix = currentPiece.matrix;
            for (let r = 0; r < matrix.length; r++) {
                for (let c = 0; c < matrix[r].length; c++) {
                    if (matrix[r][c] !== 0) {
                        const drawY = (currentPiece.y + r) * CELL_SIZE;
                        if (drawY >= 0) {
                            drawBlock(ctx, (currentPiece.x + c) * CELL_SIZE, drawY, COLORS[currentPiece.type], CELL_SIZE);
                        }
                    }
                }
            }
        }

        // 6. Draw Pause screen overlay
        if (isPaused) {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.65)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'var(--yellow)';
            ctx.font = '900 18px "Space Grotesk", sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('PAUSED', canvas.width / 2, canvas.height / 2);
        }

        ctx.restore();
    }

    function drawNextPiece() {
        nextCtx.fillStyle = '#000';
        nextCtx.fillRect(0, 0, nextCanvas.width, nextCanvas.height);
        
        if (!nextPiece) return;
        
        const matrix = nextPiece.matrix;
        const color = COLORS[nextPiece.type];
        
        // Center alignment offsets inside 60x60 container
        const blockSize = 12;
        const offsetX = (nextCanvas.width - matrix[0].length * blockSize) / 2;
        const offsetY = (nextCanvas.height - matrix.length * blockSize) / 2;

        for (let r = 0; r < matrix.length; r++) {
            for (let c = 0; c < matrix[r].length; c++) {
                if (matrix[r][c] !== 0) {
                    drawBlock(nextCtx, offsetX + c * blockSize, offsetY + r * blockSize, color, blockSize);
                }
            }
        }
    }

    function drawHoldPiece() {
        holdCtx.fillStyle = '#000';
        holdCtx.fillRect(0, 0, holdCanvas.width, holdCanvas.height);
        
        if (!holdPiece) return;
        
        const matrix = SHAPES[holdPiece.type];
        const color = COLORS[holdPiece.type];
        
        // Center alignment offsets
        const blockSize = 12;
        const offsetX = (holdCanvas.width - matrix[0].length * blockSize) / 2;
        const offsetY = (holdCanvas.height - matrix.length * blockSize) / 2;

        for (let r = 0; r < matrix.length; r++) {
            for (let c = 0; c < matrix[r].length; c++) {
                if (matrix[r][c] !== 0) {
                    drawBlock(holdCtx, offsetX + c * blockSize, offsetY + r * blockSize, color, blockSize);
                }
            }
        }
    }

    // Expose functions globally
    window.startTetrisGame = startTetrisGame;
    window.toggleTetrisPause = toggleTetrisPause;
    window.quitTetrisGame = quitTetrisGame;

    // Run initializer when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTetris);
    } else {
        initTetris();
    }
})();
