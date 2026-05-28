// ==UserScript==
// @name         Mineswifter 自动扫雷
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  自动读取棋盘，交给Python推理并模拟点击
// @author       cc-sl
// @match        *://mineswifter.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ========== 配置区 ==========
    const PYTHON_SERVER = 'http://127.0.0.1:5000/board';
    const AUTO_START = true;

    // ========== 读取棋盘 ==========
    function readBoard() {
        // 获取所有 .Cj，取格子数最多的那个（避免取到装饰性容器）
        const allBoards = document.querySelectorAll('.Cj');
        if (!allBoards.length) return null;

        let bestBoard = null;
        let maxCells = 0;
        allBoards.forEach(b => {
            const count = b.querySelectorAll('.Cb.fz').length;
            if (count > maxCells) {
                maxCells = count;
                bestBoard = b;
            }
        });
        if (!bestBoard || maxCells === 0) return null;

        const board = bestBoard;
        const cells = board.querySelectorAll('.Cb.fz');
        const cellSize = 180;

        // 内部坐标尺寸
        const internalW = parseInt(board.style.width);
        const internalH = parseInt(board.style.height);
        const cols = Math.round(internalW / cellSize);
        const rows = Math.round(internalH / cellSize);

        // 页面位置和缩放
        const rect = board.getBoundingClientRect();
        const scaleX = rect.width / internalW;
        const scaleY = rect.height / internalH;
        const boardScreenX = rect.left + window.scrollX;
        const boardScreenY = rect.top + window.scrollY;

        // 构建二维数组
        const grid = Array.from({ length: rows }, () => Array(cols).fill({ state: 'hidden', type: null }));

        cells.forEach(cell => {
            const left = parseInt(cell.style.left);
            const top = parseInt(cell.style.top);
            const col = Math.round(left / cellSize);
            const row = Math.round(top / cellSize);

            const type = cell.dataset.type !== undefined ? cell.dataset.type : null;
            const state = cell.dataset.state !== undefined ? cell.dataset.state : 'unselect';

            grid[row][col] = { state, type };
        });

        return { rows, cols, cellSize, scaleX, scaleY, boardScreenX, boardScreenY, grid, board };
    }

    // ========== 模拟操作（点击/插旗） ==========
    function executeActions(actions, scaleX, scaleY, boardScreenX, boardScreenY, cellSize) {
        if (!actions || actions.length === 0) {
            console.log('没有操作指令');
            return;
        }

        // 按顺序执行，每个动作延迟 200ms
        let delay = 0;
        actions.forEach(action => {
            const { action: act, x, y } = action;
            const centerX = boardScreenX + (x * cellSize + cellSize / 2) * scaleX;
            const centerY = boardScreenY + (y * cellSize + cellSize / 2) * scaleY;

            setTimeout(() => {
                const eventOpts = {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: centerX,
                    clientY: centerY,
                    button: act === 'flag' ? 2 : 0,
                    buttons: act === 'flag' ? 2 : 1,
                };

                const target = document.elementFromPoint(centerX, centerY) || document.body;

                // 触发完整鼠标事件序列
                target.dispatchEvent(new MouseEvent('mousedown', eventOpts));
                target.dispatchEvent(new MouseEvent('mouseup', eventOpts));
                target.dispatchEvent(new MouseEvent('click', eventOpts));

                // 插旗时额外触发 contextmenu 事件（有些游戏监听这个）
                if (act === 'flag') {
                    target.dispatchEvent(new MouseEvent('contextmenu', eventOpts));
                }

                console.log(`${act} at (${x}, ${y})`);
            }, delay);

            delay += 200;
        });
    }

    // ========== 主逻辑：读取 → 发送 → 执行 ==========
    async function mainLoop() {
        const boardData = readBoard();
        if (!boardData) {
            console.log('未检测到棋盘，1秒后重试...');
            setTimeout(mainLoop, 1000);
            return;
        }

        console.log('棋盘读取成功，发送到 Python...');
        try {
            const response = await fetch(PYTHON_SERVER, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(boardData)
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const actions = await response.json();
            console.log('收到操作指令:', actions);

            executeActions(
                actions,
                boardData.scaleX,
                boardData.scaleY,
                boardData.boardScreenX,
                boardData.boardScreenY,
                boardData.cellSize
            );

            // 操作后延时再读下一次（等待动画）
            setTimeout(mainLoop, 500);
        } catch (err) {
            console.error('通信错误:', err);
            setTimeout(mainLoop, 2000);
        }
    }

    // ========== 启动入口 ==========
    if (AUTO_START) {
        // 等待页面加载后启动
        window.addEventListener('load', () => {
            setTimeout(mainLoop, 1500);
        });
    }

    // 暴露手动启动函数到全局
    window.startSweeper = () => {
        console.log('手动启动扫雷助手');
        mainLoop();
    };
})();
