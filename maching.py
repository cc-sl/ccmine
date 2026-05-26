import cv2
import numpy as np
import os

# -------------------------- 配置 --------------------------
BIG_IMAGE_PATH = "photos/tile_bg/tile_source.png"
TEMPLATE_DIR = "photos/tile/"
SAVE_RESULT_PATH = "match_result.png"
MATCH_THRESHOLD = 0.8        # 匹配阈值
NMS_OVERLAP_RATIO = 0.4      # 重叠面积 / 较小框面积 > 此值则抑制
WEIGHT_SIGMA_FACTOR = 0.35   # 权重分布的sigma系数，越小中心越集中（0.2~0.5）
# ---------------------------------------------------------

def create_center_weight_mask(h, w, sigma_factor=0.35):
    """
    生成中心高、边缘低的权重掩码（高斯分布），取值范围 0~1
    中心 ≈ 1.0，边缘 ≈ 0.0
    sigma_factor 越小，权重越集中在中心
    """
    y, x = np.ogrid[:h, :w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    sigma = min(h, w) * sigma_factor
    weight = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * sigma ** 2))
    return weight.astype(np.float32)


def match_with_scores(big_img_gray, template_gray, threshold, weight_mask):
    """
    返回所有匹配位置及对应分数（已按分数从高到低排序）
    支持传入权重掩码进行加权匹配
    """
    h, w = template_gray.shape[:2]

    # ===== 关键：传入 weight_mask 做加权匹配 =====
    result = cv2.matchTemplate(big_img_gray, template_gray,
                               cv2.TM_CCOEFF_NORMED, mask=weight_mask)

    # 找到所有超过阈值的位置
    ys, xs = np.where(result >= threshold)
    if len(ys) == 0:
        return [], w, h, []

    scores = result[ys, xs]

    # 按分数从高到低排序
    order = np.argsort(scores)[::-1]
    locations = list(zip(xs[order].tolist(), ys[order].tolist()))
    scores = scores[order].tolist()

    # 单个模板内部 NMS
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
    """计算两个框的交集面积占较小框面积的比例"""
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


def main():
    # 读取大图
    big_img = cv2.imread(BIG_IMAGE_PATH, cv2.IMREAD_UNCHANGED)
    if big_img is None:
        print(f"错误：找不到大图 {BIG_IMAGE_PATH}")
        return

    big_img_display = big_img.copy()
    if big_img.shape[-1] == 4:
        big_gray = cv2.cvtColor(big_img, cv2.COLOR_BGRA2GRAY)
    else:
        big_gray = cv2.cvtColor(big_img, cv2.COLOR_BGR2GRAY)

    # 扫描模板目录
    template_files = sorted([
        f for f in os.listdir(TEMPLATE_DIR)
        if f.lower().endswith('.png')
    ])
    if not template_files:
        print(f"错误：在 {TEMPLATE_DIR} 下没有找到任何 .png 文件")
        return

    print(f"找到 {len(template_files)} 个模板文件：{template_files}\n")

    # ========== 第一步：收集所有模板的所有检测结果 ==========
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

        h, w = template_gray.shape[:2]

        # ===== 为每个模板生成中心高权重掩码 =====
        weight_mask = create_center_weight_mask(h, w, WEIGHT_SIGMA_FACTOR)

        # 匹配（带权重掩码）
        locations, w, h, scores = match_with_scores(
            big_gray, template_gray, MATCH_THRESHOLD, weight_mask
        )

        label = os.path.splitext(filename)[0]
        short_label = label.split('_', 1)[1][0] if '_' in label else label

        print(f"[{filename}] 找到 {len(locations)} 个匹配")
        for (x, y), score in zip(locations, scores):
            print(f"  - ({x}, {y})  score={score:.3f}")
            all_detections.append((x, y, w, h, score, short_label))

    # ========== 第二步：全局 NMS ==========
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

    # ========== 第三步：绘制结果 ==========
    for x, y, w, h, score, label in final_detections:
        cv2.rectangle(big_img_display, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(big_img_display, label, (x + 5, y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    cv2.imwrite(SAVE_RESULT_PATH, big_img_display)
    print(f"结果图已保存：{SAVE_RESULT_PATH}")

    # 显示
    screen_max_height = 768
    img_h, img_w = big_img_display.shape[:2]
    if img_h > screen_max_height:
        scale = screen_max_height / img_h
        show_img = cv2.resize(big_img_display, (int(img_w * scale), int(img_h * scale)))
    else:
        show_img = big_img_display

    cv2.imshow("所有匹配结果（缩放版）", show_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
