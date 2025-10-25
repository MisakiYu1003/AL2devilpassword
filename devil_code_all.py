# 檔案名稱: devil_code_all.py (版本 9.7 - 完整修正版)
import pyautogui, time, requests, base64, os, io, json, pyperclip, re
from PIL import Image
from dotenv import load_dotenv
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
load_dotenv()

# --- 偵錯模式開關 ---
DEBUG_MODE = False

# --- 這部分設定將由 config_editor.py 自動修改 (每個設定佔獨立一行) ---
DETECTION_MODE = 'image'
DIALOG_BOX_REGION = (0, 0, 100, 100)
CLICK_COORDINATE = (50, 50)
TEMPLATE_IMAGE_PATHS = ['template_a.png', 'template_b.png', 'template_c.png', 'template_d.png']
CONFIDENCE_LEVEL = 0.8  # 回歸：辨識信賴度
NUMBER_REGION_OFFSET = (-200, -100, 230,90) # (從中心點往左/右, 往上/下, 截圖寬度, 截圖高度)
CLICK_OFFSET = (0, 0) # (從中心點往左/右, 往上/下)
MACRO_TOGGLE_KEYS = ''
CLICK_TYPE = 'hold_click'
LOOP_INTERVAL = 3
SHORT_INTERVAL = 5
# --- 設定區結束 ---

# --- *** 核心修正：將所有必要的輔助函式加回來 *** ---
def get_gemini_api_key():
    api_key = os.getenv("GEMINI_API_KEY");
    if not api_key: print("錯誤：找不到 GEMINI_API_KEY。"); exit()
    return api_key

def press_macro_keys():
    if not MACRO_TOGGLE_KEYS: return
    try:
        keys = [key.strip() for key in MACRO_TOGGLE_KEYS.split(',')]
        if len(keys) > 1: pyautogui.hotkey(*keys)
        elif len(keys) == 1 and keys[0]: pyautogui.press(keys[0])
    except Exception as e: print(f"執行快捷鍵 '{MACRO_TOGGLE_KEYS}' 時發生錯誤: {e}")

def encode_image_to_base64(image: Image.Image):
    """將 PIL.Image 物件轉換為 Base64 編碼的字串"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def get_numbers_from_image(image: Image.Image, api_key: str):
    print("【API】接收到原始截圖，開始進行圖像預處理...");
    if OPENCV_AVAILABLE:
        open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR); gray_image = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        processed_image_cv = cv2.adaptiveThreshold(gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 9)
        image_to_send = Image.fromarray(processed_image_cv); print("【API】圖像預處理完成。")
    else: image_to_send = image; print("【API】警告：未安裝 OpenCV，將使用原始圖片進行辨識。")
    if DEBUG_MODE: image_to_send.save("debug_processed_for_api.png"); print("【偵錯】已將預處理後準備發送的圖片儲存為 'debug_processed_for_api.png'")
    
    base64_image = encode_image_to_base64(image_to_send) # <--- 現在這個函式是存在的
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    prompt_text = (
        "Analyze the provided image which contains a sequence of distorted, cursive digits. "
        "Your task is to act as an expert OCR engine. Follow these steps:\n"
        "1. Identify each individual digit from left to right.\n"
        "2. Concatenate the digits into a single string.\n"
        "3. Output ONLY the final string of digits. Do not include any explanation, preamble, or formatting.\n"
        "Example: If you see '7', '5', '6', '3', '9', the final output must be '75639'."
    )
    payload = {"contents": [{"parts": [{"text": prompt_text}, {"inline_data": {"mime_type": "image/png", "data": base64_image}}]}]}
    print("【API】正在將處理後的圖片傳送至 Gemini API...");
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20); response.raise_for_status(); result = response.json()
        if DEBUG_MODE: print(f"【偵錯】收到 API 原始回傳: {json.dumps(result, indent=2)}")
        if 'candidates' in result and result['candidates']:
            extracted_text = result['candidates'][0]['content']['parts'][0]['text'].strip(); cleaned_numbers = re.sub(r'\D', '', extracted_text)
            if cleaned_numbers: print(f"【API】AI 辨識結果為: {cleaned_numbers}"); return cleaned_numbers
            else: print(f"【API】警告：AI 回傳的內容不含任何數字 ('{extracted_text}')"); return None
        print("【API】警告：API 回傳的資料格式不符預期。"); return None
    except Exception as e: print(f"【API】呼叫或解析 API 時發生錯誤: {e}"); return None

def draw_debug_window(screenshot, template_box, number_box, click_point):
    if not OPENCV_AVAILABLE: return
    screen_cv = np.array(screenshot); screen_cv = cv2.cvtColor(screen_cv, cv2.COLOR_RGB2BGR)
    cv2.rectangle(screen_cv, (template_box[0], template_box[1]), (template_box[0] + template_box[2], template_box[1] + template_box[3]), (0, 255, 0), 2)
    cv2.rectangle(screen_cv, (number_box[0], number_box[1]), (number_box[0] + number_box[2], number_box[1] + number_box[3]), (0, 0, 255), 2)
    cv2.circle(screen_cv, click_point, 10, (255, 0, 0), -1)
    cv2.imshow("Debug Vision", screen_cv); cv2.waitKey(3000); cv2.destroyAllWindows()

def perform_automation(numbers, click_coord):
    if DEBUG_MODE: print(f"【偵錯】Dry Run: 將點擊 {click_coord} 輸入 {numbers}。跳過實際操作。"); return True
    print(f"【執行】準備點擊 {click_coord} 並輸入 {numbers}...");
    try:
        original_pos = pyautogui.position(); pyautogui.moveTo(click_coord);
        if CLICK_TYPE == 'click': pyautogui.click()
        elif CLICK_TYPE == 'double': pyautogui.doubleClick()
        elif CLICK_TYPE == 'hold_click': pyautogui.mouseDown(); time.sleep(0.01); pyautogui.mouseUp()
        pyautogui.moveTo(original_pos); pyperclip.copy(numbers); time.sleep(0.2); pyautogui.hotkey('ctrl', 'v'); time.sleep(0.5); pyautogui.press('enter');
        print("【執行】已成功輸入數字並按下 Enter。"); return True
    except Exception as e: print(f"【執行】自動化操作時發生錯誤：{e}"); return False

def find_captcha_by_template_matching():
    if not OPENCV_AVAILABLE: print("錯誤: '圖像辨識模式' 需要 OpenCV。"); return None, None
    print("【模板匹配】正在擷取全螢幕...")
    screenshot_pil = pyautogui.screenshot()
    screen_gray = cv2.cvtColor(np.array(screenshot_pil), cv2.COLOR_RGB2GRAY)
    for template_path in TEMPLATE_IMAGE_PATHS:
        if not os.path.exists(template_path):
            print(f"【辨識】警告: 找不到模板 '{template_path}'，已跳過。")
            continue
        print(f"【辨識】正在使用模板 '{template_path}' 進行匹配...")
        template_cv = cv2.imread(template_path, 0)
        if template_cv is None: print(f"【辨識】錯誤: 無法讀取模板 '{template_path}'。"); continue
        found_this_template = None
        for scale in np.linspace(0.8, 1.2, 21)[::-1]:
            w, h = int(template_cv.shape[1] * scale), int(template_cv.shape[0] * scale)
            if w == 0 or h == 0 or w > screen_gray.shape[1] or h > screen_gray.shape[0]: continue
            resized = cv2.resize(template_cv, (w, h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(screen_gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if found_this_template is None or max_val > found_this_template[0]:
                found_this_template = (max_val, max_loc, (w, h))
        if found_this_template and found_this_template[0] > CONFIDENCE_LEVEL:
            max_val, max_loc, (w, h) = found_this_template
            print(f"【辨識】成功匹配到模板 '{template_path}'! 信賴度: {max_val:.2f}")
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            num_box = (center_x + NUMBER_REGION_OFFSET[0], center_y + NUMBER_REGION_OFFSET[1], NUMBER_REGION_OFFSET[2], NUMBER_REGION_OFFSET[3])
            click_pt = (center_x + CLICK_OFFSET[0], center_y + CLICK_OFFSET[1])
            if DEBUG_MODE:
                template_box_for_debug = (max_loc[0], max_loc[1], w, h)
                draw_debug_window(screenshot_pil, template_box_for_debug, num_box, click_pt)
            return num_box, click_pt
    print(f"【辨識】在所有模板中均未找到足夠相似的目標。")
    return None, None

def main():
    print(f"惡魔密碼辨識器 (v9.7 - 完整修正版) 已啟動，模式: {DETECTION_MODE.upper()}")
    if DEBUG_MODE: print("="*30 + "\n      警告：目前處於偵錯模式！\n" + "="*30)
    api_key = get_gemini_api_key(); is_first_detection = True
    try:
        while True:
            numbers, click_target = None, None; interval = LOOP_INTERVAL if is_first_detection else SHORT_INTERVAL
            print(f"\n--- [模式: {DETECTION_MODE.upper()}] 掃描中 (間隔 {interval} 秒) ---"); time.sleep(interval)
            if DETECTION_MODE == 'fixed':
                image = pyautogui.screenshot(region=DIALOG_BOX_REGION); numbers = get_numbers_from_image(image, api_key); click_target = CLICK_COORDINATE
            elif DETECTION_MODE == 'image':
                num_region, click_target = find_captcha_by_template_matching()
                if num_region and click_target:
                    valid_region = (max(0, num_region[0]), max(0, num_region[1]), num_region[2], num_region[3])
                    image = pyautogui.screenshot(region=valid_region); numbers = get_numbers_from_image(image, api_key)
            else: print(f"錯誤：未知的偵測模式 '{DETECTION_MODE}'。"); break
            if numbers and click_target:
                if is_first_detection:
                    print("【流程】首次偵測到數字...");
                    if not DEBUG_MODE: press_macro_keys()
                    is_first_detection = False; time.sleep(0.5)
                if perform_automation(numbers, click_target):
                    print("【流程】輸入完成...");
                    if not DEBUG_MODE: press_macro_keys()
            elif not is_first_detection: print("【流程】惡魔密碼已消失..."); is_first_detection = True
    except KeyboardInterrupt: print("\n程式已由使用者手動中止。")
    except Exception as e: print(f"\n程式發生未預期的嚴重錯誤：{e}")

if __name__ == "__main__":
    main()