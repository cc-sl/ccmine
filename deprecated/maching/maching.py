import cv2
import numpy as np
import os

# -------------------------- 配置 --------------------------
BIG_IMAGE_PATH = "photos/tile_bg/tile_source.png"
TEMPLATE_DIR = "photos/tile/"
SAVE_RESULT_PATH = "match_result.png"
SAVE_BINARY_PATH = "binary_result.png"       # 新增：保存二值化结果
MATCH_THRESHOLD = 0.7
NMS_OVERLAP_RATIO = 0.4

ENABLE_BINARIZATION = True
BINARY_BLOCK_SIZE = 15
BINARY_C_VALUE = 2
# ---------------------------------------------------------


def binarize(img_gray, block_size=15, c_value=2):
    """自适应阈值二值化"""
    binary = cv2.adaptiveThreshold(
        img_gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c_value
    )
    return binary


def create_center_weight_mask(h, w, sigma_factor=0.35):
    """生成中心高权重掩码"""
    y, x = np.ogrid[:h, :w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    sigma = min(h, w) * sigma_factor
    weight = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * sigma ** 2))
    return weight.astype(np.float32)


def match_with_scores(big_img, template, threshold, weight_mask=None):
    h, w = template.shape[:2]
    result = cv2.matchTemplate(big_img, template,
                               cv2.TM_CCOEFF_NORMED, mask=weight_mask)
    ys, xs = np.where(result >= threshold)
    if len(ys) == 0:
        return [], w, h, []

    scores = result[ys, xs]
    order = np.argsort(scores)[::-1]
    locations = list(zip(xs[order].tolist(), ys[order].tolist()))
    scores = scores[order].tolist()

    keep_locs = []
    keep_scores = []
    for (x, y), score in zip(locations, scores):
        suppressed = False
        for (kx, ky) in keep_locs:
            if abs(x - kx) < w and abs(y - ky) < h:
                suppressed = True
                break
        if not suppressed:
            keep_locs.append((x, y))
            keep_scores.append(score)

    return keep_locs, w, h, keep_scores


def compute_overlap_ratio(x1, y1, w1, h1, x2, y2, w2, h2):
    ix1 = max(x1, x2)
    iy1 = max(y1, y2)
    ix2 = min(x1 + w1, x2 + w2)
    iy2 = min(y1 + h1, y2 + h2)
    if ix1 >= ix2 or iy1 >= iy2:
        return 0.0
    inter_area = (ix2 - ix1) * (iy2 - iy1)
    min_area = min(w1 * h1, w2 * h2)
    if min_area == 0:
        return 0.0
    return inter_area / min_area


def show_and_wait(img, window_title, max_height=768):
    """缩放显示图片，按任意键继续"""
    h, w = img.shape[:2]
    if h > max_height:
        scale = max_height / h
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    cv2.imshow(window_title, img)


def main():
    # ===== 1. 读取大图 =====
    big_img = cv2.imread(BIG_IMAGE_PATH, cv2.IMREAD_UNCHANGED)
    if big_img is None:
        print(f"错误：找不到大图 {BIG_IMAGE_PATH}")
        return

    big_img_display = big_img.copy()
    if big_img.shape[-1] == 4:
        big_gray = cv2.cvtColor(big_img, cv2.COLOR_BGRA2GRAY)
    else:
        big_gray = cv2.cvtColor(big_img, cv2.COLOR_BGR2GRAY)

    # ===== 2. 二值化（同时保存和显示结果） =====
    if ENABLE_BINARIZATION:
        big_for_match = binarize(big_gray, BINARY_BLOCK_SIZE, BINARY_C_VALUE)
        print("✅ 已启用二值化：基于自适应阈值将图像转为黑白，仅保留图案形状")

        # ---- 保存二值化结果图 ----
        cv2.imwrite(SAVE_BINARY_PATH, big_for_match)
        print(f"📁 二值化结果已保存：{SAVE_BINARY_PATH}")

        # ---- 显示二值化图 ----
        show_and_wait(big_for_match, "二值化结果（按任意键继续匹配）")
        cv2.waitKey(0)
    else:
        big_for_match = big_gray
        print("ℹ️ 未启用二值化：使用原始灰度图匹配")

    # ===== 3. 扫描模板目录 =====
    template_files = sorted([
        f for f in os.listdir(TEMPLATE_DIR)
        if f.lower().endswith('.png')
    ])
    if not template_files:
        print(f"错误：在 {TEMPLATE_DIR} 下没有找到任何 .png 文件")
        return

    print(f"找到 {len(template_files)} 个模板文件：{template_files}\n")

    # ===== 4. 收集检测结果 =====
    all_detections = []

    for filename in template_files:
        template_path = os.path.join(TEMPLATE_DIR, filename)
        template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
        if template is None:
            print(f"跳过（无法读取）：{template_path}")
            continue

        # 转灰度
        if template.shape[-1] == 4:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGRA2GRAY)
        else:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # 模板也二值化
        if ENABLE_BINARIZATION:
            template_for_match = binarize(
                template_gray, BINARY_BLOCK_SIZE, BINARY_C_VALUE
            )
        else:
            template_for_match = template_gray

        h, w = template_for_match.shape[:2]
        weight_mask = create_center_weight_mask(h, w, sigma_factor=0.35)

        locations, w, h, scores = match_with_scores(
            big_for_match, template_for_match,
            MATCH_THRESHOLD, weight_mask
        )

        label = os.path.splitext(filename)[0]
        short_label = label.split('_', 1)[1][0] if '_' in label else label

        print(f"[{filename}] 找到 {len(locations)} 个匹配")
        for (x, y), score in zip(locations, scores):
            print(f"  - ({x}, {y})  score={score:.3f}")
            all_detections.append((x, y, w, h, score, short_label))

    # ===== 5. 全局 NMS =====
    print(f"\n===== 全局 NMS 去重（共 {len(all_detections)} 个候选） =====")
    all_detections.sort(key=lambda d: d[4], reverse=True)

    final_detections = []
    for det in all_detections:
        x, y, w, h, score, label = det
        suppressed = False
        for fd in final_detections:
            fx, fy, fw, fh, fscore, flabel = fd
            ratio = compute_overlap_ratio(x, y, w, h, fx, fy, fw, fh)
            if ratio > NMS_OVERLAP_RATIO:
                suppressed = True
                break
        if not suppressed:
            final_detections.append(det)

    print(f"去重后保留 {len(final_detections)} 个检测结果\n")

    # ===== 6. 绘制最终结果 =====
    for x, y, w, h, score, label in final_detections:
        cv2.rectangle(big_img_display, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(big_img_display, label, (x + 5, y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    cv2.imwrite(SAVE_RESULT_PATH, big_img_display)
    print(f"📁 匹配结果已保存：{SAVE_RESULT_PATH}")

    # ===== 7. 显示最终匹配结果 =====
    show_and_wait(big_img_display, "匹配结果（按任意键退出）")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
