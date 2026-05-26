import cv2
import numpy as np

# -------------------------- 配置 --------------------------
BIG_IMAGE_PATH = "photos/tile_bg/tile_source.png"
TEMPLATE_DIR = "photos/tile/"
TEMPLATE_COUNT = 8
SAVE_RESULT_PATH = "match_result.png"
MATCH_THRESHOLD = 0.8  # 匹配阈值，0.8~0.95之间，越高越严格
# ---------------------------------------------------------

def match_all_templates(big_img_gray, template_gray, threshold):
    """
    找到所有超过阈值的匹配位置（支持一张图匹配多次）
    """
    h, w = template_gray.shape[:2]
    result = cv2.matchTemplate(big_img_gray, template_gray, cv2.TM_CCOEFF_NORMED)

    # 找到所有大于阈值的位置
    locations = np.where(result >= threshold)
    # 转换为 (x, y) 列表
    locations = list(zip(*locations[::-1]))

    # 去重：防止同一个位置重复框选（非极大值抑制）
    unique_locations = []
    for loc in locations:
        duplicate = False
        for ul in unique_locations:
            if abs(loc[0] - ul[0]) < w and abs(loc[1] - ul[1]) < h:
                duplicate = True
                break
        if not duplicate:
            unique_locations.append(loc)

    return unique_locations, w, h

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

    print("===== 开始多位置模板匹配 =====\n")

    # 遍历 0~7 所有模板
    for i in range(TEMPLATE_COUNT):
        template_path = f"{TEMPLATE_DIR}tile_{i}.png"
        template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
        if template is None:
            print(f"跳过：{template_path}")
            continue

        # 转灰度
        if template.shape[-1] == 4:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGRA2GRAY)
        else:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # 匹配所有位置
        locations, w, h = match_all_templates(big_gray, template_gray, MATCH_THRESHOLD)
        print(f"[tile_{i}.png] 找到 {len(locations)} 个匹配")

        # 画出所有匹配框
        for idx, (x, y) in enumerate(locations):
            print(f"  - 位置{idx+1}：({x}, {y})")
            cv2.rectangle(big_img_display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(big_img_display, f"{i}", (x + 5, y + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    # 保存结果
    cv2.imwrite(SAVE_RESULT_PATH, big_img_display)
    print(f"\n结果图已保存：{SAVE_RESULT_PATH}")

    # 小屏幕自适应缩放显示
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