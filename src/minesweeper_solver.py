from flask import Flask, request, jsonify
from flask_cors import CORS  # 如果没有安装，下面会单独装

app = Flask(__name__)
CORS(app)  # 允许油猴脚本跨域请求

# ========== 扫雷求解逻辑（基础版但可用） ==========
def solve_board(rows, cols, grid):
    """
    grid: 二维数组, grid[row][col] = {"state": "...", "type": "..."}
    返回操作列表: [{"action": "click", "x": col, "y": row}, {"action": "flag", "x": col, "y": row}, ...]
    """
    actions = []

    # 先统计所有已翻开数字的格子
    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            if cell["state"] != "select":  # 已翻开
                continue
            num = int(cell["type"]) if cell["type"] is not None else 0
            if num == 0:
                continue

            # 获取周围 8 个邻居
            neighbors = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        neighbors.append((nr, nc))

            # 统计邻居中未翻开和插旗数量
            hidden_cells = []
            flagged_count = 0
            for nr, nc in neighbors:
                nb = grid[nr][nc]
                if nb["state"] in ("unselect", None, "hidden"):
                    hidden_cells.append((nr, nc))
                elif nb["state"] == "flag":
                    flagged_count += 1

            # 规则1：数字 == 周围插旗数 → 周围所有未翻开格子都是安全的，可以点
            if num == flagged_count and hidden_cells:
                for nr, nc in hidden_cells:
                    if {"action": "click", "x": nc, "y": nr} not in actions:
                        actions.append({"action": "click", "x": nc, "y": nr})

            # 规则2：数字 == 周围未翻开+插旗数 → 所有未翻开格子都是雷，插旗
            if num == len(hidden_cells) + flagged_count and hidden_cells:
                for nr, nc in hidden_cells:
                    if {"action": "flag", "x": nc, "y": nr} not in actions:
                        actions.append({"action": "flag", "x": nc, "y": nr})

    # 如果没有推理出任何操作，随机点一个未翻开格子（可选，防止卡死）
    if not actions:
        for r in range(rows):
            for c in range(cols):
                if grid[r][c]["state"] in ("unselect", "hidden", None):
                    actions.append({"action": "click", "x": c, "y": r})
                    return actions  # 只点一个
    return actions

# ========== API 路由 ==========
@app.route('/board', methods=['POST'])
def handle_board():
    data = request.get_json()
    rows = data['rows']
    cols = data['cols']
    grid = data['grid']  # 二维列表

    actions = solve_board(rows, cols, grid)
    return jsonify(actions)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
