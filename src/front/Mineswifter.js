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
    const AUTO_START = false;  // 改为手动启动，通过右侧面板按钮控制

    // ========== 侧边栏按钮配置（方便添加新按钮） ==========
    // 每个按钮：{ id, label, onClick, color? }
    // color 可选：'primary'（蓝）/ 'success'（绿）/ 'danger'（红）/ 'warning'（橙）/ 不填默认灰
    const SIDEBAR_BUTTONS = [
        { id: 'start',    label: '▶ 启动脚本', color: 'success', onClick: () => { isRunning = true; updateStatus('运行中...', '#4caf50'); mainLoop(); } },
        { id: 'stop',     label: '⏹ 停止脚本', color: 'danger',  onClick: () => { isRunning = false; updateStatus('已停止', '#f44336'); } },
        { id: 'config',   label: '⚙ 配置脚本', color: 'primary', onClick: () => { toggleConfigPanel(); } },
        { id: 'separator1', label: null },  // 分隔线
        { id: 'status',   label: null },     // 状态显示占位（由 updateStatus 填充）
    ];

    // ========== 运行时状态 ==========
    let isRunning = false;
    let stopRequested = false;
    let mainLoopTimer = null;

    function updateStatus(text, color) {
        const statusEl = document.getElementById('sweeper-status');
        if (statusEl) {
            statusEl.textContent = text;
            statusEl.style.color = color || '#aaa';
        }
    }

    // ========== 创建侧边栏 ==========
    function createSidebar() {
        // 注入样式
        const style = document.createElement('style');
        style.textContent = `
            #sweeper-sidebar {
                position: fixed;
                top: 50%;
                right: 12px;
                transform: translateY(-50%);
                z-index: 99999;
                background: #1e1e2e;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 16px 12px;
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-width: 130px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.5);
                font-family: 'Segoe UI', system-ui, sans-serif;
                user-select: none;
            }
            #sweeper-sidebar .sweeper-title {
                color: #ccc;
                font-size: 13px;
                font-weight: 600;
                text-align: center;
                padding-bottom: 6px;
                border-bottom: 1px solid #333;
                margin-bottom: 2px;
            }
            #sweeper-sidebar .sweeper-btn {
                display: block;
                width: 100%;
                padding: 8px 12px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 500;
                color: #fff;
                background: #3a3a4a;
                transition: background 0.2s, transform 0.1s;
                text-align: center;
                white-space: nowrap;
            }
            #sweeper-sidebar .sweeper-btn:hover {
                filter: brightness(1.2);
                transform: scale(1.03);
            }
            #sweeper-sidebar .sweeper-btn:active {
                transform: scale(0.97);
            }
            #sweeper-sidebar .sweeper-btn.primary { background: #2563eb; }
            #sweeper-sidebar .sweeper-btn.success { background: #16a34a; }
            #sweeper-sidebar .sweeper-btn.danger  { background: #dc2626; }
            #sweeper-sidebar .sweeper-btn.warning { background: #ea580c; }
            #sweeper-sidebar .sweeper-separator {
                height: 1px;
                background: #333;
                margin: 2px 0;
            }
            #sweeper-sidebar .sweeper-status {
                color: #aaa;
                font-size: 11px;
                text-align: center;
                padding: 4px 0;
                min-height: 18px;
            }
            #sweeper-config-panel {
                display: none;
                position: fixed;
                top: 50%;
                right: 160px;
                transform: translateY(-50%);
                z-index: 99998;
                background: #1e1e2e;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 20px;
                min-width: 220px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.5);
                font-family: 'Segoe UI', system-ui, sans-serif;
                color: #ccc;
                font-size: 13px;
            }
            #sweeper-config-panel label {
                display: block;
                margin-bottom: 4px;
                font-size: 12px;
            }
            #sweeper-config-panel input {
                width: 100%;
                padding: 6px 8px;
                border: 1px solid #444;
                border-radius: 4px;
                background: #2a2a3a;
                color: #ddd;
                font-size: 12px;
                margin-bottom: 10px;
                box-sizing: border-box;
            }
            #sweeper-config-panel input:focus {
                outline: none;
                border-color: #2563eb;
            }
        `;
        document.head.appendChild(style);

        // 构建侧边栏 DOM
        const sidebar = document.createElement('div');
        sidebar.id = 'sweeper-sidebar';

        // 标题
        const title = document.createElement('div');
        title.className = 'sweeper-title';
        title.textContent = '💣 扫雷助手';
        sidebar.appendChild(title);

        // 按配置生成按钮
        SIDEBAR_BUTTONS.forEach(btn => {
            if (btn.label === null) {
                // 分隔线或状态占位
                if (btn.id === 'status') {
                    const statusEl = document.createElement('div');
                    statusEl.id = 'sweeper-status';
                    statusEl.className = 'sweeper-status';
                    statusEl.textContent = '就绪';
                    sidebar.appendChild(statusEl);
                } else {
                    const sep = document.createElement('div');
                    sep.className = 'sweeper-separator';
                    sidebar.appendChild(sep);
                }
            } else {
                const button = document.createElement('button');
                button.className = 'sweeper-btn' + (btn.color ? ` ${btn.color}` : '');
                button.textContent = btn.label;
                button.addEventListener('click', btn.onClick);
                sidebar.appendChild(button);
            }
        });

        document.body.appendChild(sidebar);

        // 配置面板（初始隐藏）
        const configPanel = document.createElement('div');
        configPanel.id = 'sweeper-config-panel';
        configPanel.innerHTML = `
            <div style="font-weight:600;margin-bottom:12px;">⚙ 配置</div>
            <label for="sweeper-server-url">Python 服务地址</label>
            <input id="sweeper-server-url" type="text" value="${PYTHON_SERVER}" placeholder="http://127.0.0.1:5000/board">
            <button class="sweeper-btn primary" style="width:100%;margin-top:4px;" id="sweeper-save-config">💾 保存</button>
        `;
        document.body.appendChild(configPanel);

        // 保存配置按钮事件
        document.getElementById('sweeper-save-config').addEventListener('click', () => {
            const newUrl = document.getElementById('sweeper-server-url').value.trim();
            if (newUrl) {
                // 更新运行时使用的 server 地址（通过闭包变量）
                window.__sweeperServerUrl = newUrl;
                console.log('配置已保存:', newUrl);
                updateStatus('配置已保存 ✓', '#4caf50');
                setTimeout(() => {
                    if (!isRunning) updateStatus('就绪', '#aaa');
                }, 1500);
            }
            toggleConfigPanel(); // 关闭面板
        });
    }

    function toggleConfigPanel() {
        const panel = document.getElementById('sweeper-config-panel');
        if (panel) {
            panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
        }
    }

    // 重写 PYTHON_SERVER 为可运行时修改
    function getServerUrl() {
        return window.__sweeperServerUrl || PYTHON_SERVER;
    }

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
        // 检查停止标志
        if (!isRunning) {
            updateStatus('已停止', '#f44336');
            return;
        }

        const boardData = readBoard();
        if (!boardData) {
            console.log('未检测到棋盘，1秒后重试...');
            if (isRunning) mainLoopTimer = setTimeout(mainLoop, 1000);
            return;
        }

        console.log('棋盘读取成功，发送到 Python...');
        try {
            const response = await fetch(getServerUrl(), {
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
            if (isRunning) mainLoopTimer = setTimeout(mainLoop, 500);
        } catch (err) {
            console.error('通信错误:', err);
            updateStatus('连接失败，重试中...', '#f44336');
            if (isRunning) mainLoopTimer = setTimeout(mainLoop, 2000);
        }
    }

    // ========== 启动入口 ==========
    // 页面加载后创建侧边栏
    window.addEventListener('load', () => {
        setTimeout(createSidebar, 1000);
    });

    // 兼容：如果页面已加载完则直接创建
    if (document.readyState === 'complete') {
        setTimeout(createSidebar, 500);
    }

    // 暴露手动启动函数到全局
    window.startSweeper = () => {
        console.log('手动启动扫雷助手');
        isRunning = true;
        updateStatus('运行中...', '#4caf50');
        mainLoop();
    };

    // 暴露停止函数
    window.stopSweeper = () => {
        console.log('停止扫雷助手');
        isRunning = false;
        updateStatus('已停止', '#f44336');
    };
})();
