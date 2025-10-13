# 檔案名稱: devil_code_solver.py (版本 5.3 - 支援外部腳本暫停/繼續)
import pyautogui
import time
import requests
import base64
import os
import io
import json
import pyperclip
from PIL import Image
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數 (API 金鑰)
load_dotenv()
# ---密鑰格式  https://aistudio.google.com/app/apikey  該網址申請  並放在=後面  GEMINI_API_KEY=

# --- 您需要根據您的螢幕設定以下參數 ---

# 1. 惡魔密碼數字框在螢幕上的座標 (x, y, 向右寬度, 往下高度)
# *** 極度重要 ***: 請精準地只框選數字區域。
DIALOG_BOX_REGION = (2081, 989, 238, 134)

# 2. 設定輸入前要點擊的座標 (x, y)
CLICK_COORDINATE = (2268, 1099)
CLICK_TYPE = 'hold_click'

# 3. 按鍵精靈/腳本的 "暫停/繼續" 快捷鍵 (可選)
#    - 單一按鍵請填寫如: 'f1', 'f12'
#    - 組合鍵請用逗號分隔: 'alt,q', 'ctrl,r'
#    - 若不需要此功能，請留空: ''
MACRO_TOGGLE_KEYS = 'alt,6'

# 4. 設定滑鼠連點兩次之間的間隔時間 (秒)
DOUBLE_CLICK_INTERVAL = 0.001

# 5. 正常循環的間隔時間 (秒) 建議100
LOOP_INTERVAL = 100

# 6. 偵測到數字後，快速循環的間隔時間 (秒)
SHORT_INTERVAL = 5

# --- 以下為程式碼主體，通常不需要修改 ---

def get_gemini_api_key():
    """從環境變數中獲取 Gemini API 金鑰"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("錯誤：找不到 GEMINI_API_KEY。請確認您已經設定好 .env 檔案。")
        exit()
    return api_key

def press_macro_keys():
    """解析並按下設定的快捷鍵"""
    if not MACRO_TOGGLE_KEYS:
        return
    try:
        keys = [key.strip() for key in MACRO_TOGGLE_KEYS.split(',')]
        if len(keys) > 1:
            print(f"正在執行組合鍵: {keys}")
            pyautogui.hotkey(*keys)
        elif len(keys) == 1 and keys[0]:
            print(f"正在執行單一按鍵: {keys[0]}")
            pyautogui.press(keys[0])
    except Exception as e:
        print(f"執行快捷鍵 '{MACRO_TOGGLE_KEYS}' 時發生錯誤: {e}")

def capture_screen_region(region):
    """擷取螢幕指定區域的畫面。"""
    try:
        screenshot = pyautogui.screenshot(region=region)
        screenshot.save("debug_screenshot.png")
        return screenshot
    except Exception as e:
        print(f"擷取螢幕時發生錯誤：{e}")
        return None

def encode_image_to_base64(image: Image.Image):
    """將 PIL.Image 物件轉換為 Base64 編碼的字串"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def get_numbers_from_image(image: Image.Image, api_key: str):
    """使用 Gemini Vision API 從圖片中辨識數字，並加入兩段式驗證。"""
    print("正在將圖片傳送至 Gemini API 進行兩段式驗證...")

    base64_image = encode_image_to_base64(image)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    prompt_text = (
        "Your task is to analyze an image from a game's anti-bot system. "
        "First, determine if the image contains any distorted, cursive, handwritten-style digits. "
        "Based on your determination, respond with a JSON object with two keys: 'contains_digits' (boolean) and 'extracted_number' (string or null). "
        "If handwritten-style digits are present, set 'contains_digits' to true and put the number sequence in 'extracted_number'. "
        "If NO handwritten-style digits are present (e.g., it's just a game scene), set 'contains_digits' to false and 'extracted_number' to null. "
        "Example 1: Image contains '85989' -> Respond: {\"contains_digits\": true, \"extracted_number\": \"85989\"} "
        "Example 2: Image is a game scene with no captcha -> Respond: {\"contains_digits\": false, \"extracted_number\": null}"
    )

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt_text},
                {"inline_data": {"mime_type": "image/png", "data": base64_image}}
            ]
        }]
    }

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if 400 <= response.status_code < 500:
                print(f"呼叫 API 時發生客戶端錯誤 (代碼: {response.status_code})，將不會重試。")
                print(f"錯誤訊息: {response.text}")
                return None
            response.raise_for_status()
            result = response.json()

            if 'candidates' in result and result['candidates']:
                text_content = result['candidates'][0]['content']['parts'][0]['text']
                print(f"Gemini API 回傳原始 JSON: '{text_content}'")

                try:
                    cleaned_text = text_content.strip().replace('```json', '').replace('```', '')
                    response_json = json.loads(cleaned_text)

                    if response_json.get("contains_digits") is True:
                        extracted_number = response_json.get("extracted_number")
                        if extracted_number and isinstance(extracted_number, str) and extracted_number.isdigit():
                            print(f"AI 確認圖片中有數字，辨識結果為: {extracted_number}")
                            return extracted_number
                        else:
                            print("警告：AI 聲稱有數字，但回傳的數字格式不正確。")
                            return None
                    else:
                        print("AI 確認圖片中沒有惡魔密碼數字。")
                        return None

                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    print(f"警告：無法將 AI 回應解析為預期的 JSON 格式。錯誤: {e}")
                    return None

            print("警告：Gemini API 回傳的資料格式不符預期。")
            return None
        except requests.exceptions.RequestException as e:
            print(f"呼叫 API 時發生網路錯誤 (第 {attempt + 1} 次嘗試): {e}")
            if attempt < max_retries - 1:
                print(f"將在 {retry_delay} 秒後重試...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("已達到最大重試次數，本次辨識失敗。")
                return None
        except Exception as e:
            print(f"處理 API 回應時發生未知錯誤：{e}")
            return None
    return None

def main():
    """主執行函數"""
    print("惡魔密碼自動辨識程式已啟動。")
    print("按下 Ctrl+C 可以中止程式。")
    api_key = get_gemini_api_key()
    is_first_detection = True # 用於標記是否為本輪第一次偵測到
    try:
        while True:
            # --- 正常循環偵測 ---
            if is_first_detection:
                print(f"\n--- 正常循環，將在 {LOOP_INTERVAL} 秒後掃描 ---")
                time.sleep(LOOP_INTERVAL)
            else:
                print(f"\n--- 快速循環，將在 {SHORT_INTERVAL} 秒後再次偵測 ---")
                time.sleep(SHORT_INTERVAL)

            image_to_process = capture_screen_region(DIALOG_BOX_REGION)
            if image_to_process is None:
                continue

            numbers_to_type = get_numbers_from_image(image_to_process, api_key)

            if numbers_to_type:
                # --- 首次偵測到數字，執行 "暫停" 快捷鍵 ---
                if is_first_detection:
                    print("首次偵測到數字，準備執行前置快捷鍵...")
                    press_macro_keys()
                    is_first_detection = False
                    time.sleep(0.5) # 短暫延遲確保腳本已暫停

                print(f"偵測到數字: {numbers_to_type}！準備進行自動化輸入...")

                try:
                    # --- 滑鼠動作區塊 ---
                    print(f"移動滑鼠至 {CLICK_COORDINATE} 並執行 '{CLICK_TYPE}' 動作...")
                    original_pos = pyautogui.position()
                    pyautogui.moveTo(CLICK_COORDINATE[0], CLICK_COORDINATE[1])

                    if CLICK_TYPE == 'click': pyautogui.click()
                    elif CLICK_TYPE == 'double': pyautogui.doubleClick(interval=DOUBLE_CLICK_INTERVAL)
                    elif CLICK_TYPE == 'hold_click':
                        pyautogui.mouseDown(); time.sleep(0.001); pyautogui.mouseUp()
                    
                    pyautogui.moveTo(original_pos[0], original_pos[1])
                    print("滑鼠已歸位。")

                    # --- 鍵盤輸入區塊 ---
                    print(f"準備使用剪貼簿貼上數字: {numbers_to_type}")
                    pyperclip.copy(numbers_to_type)
                    time.sleep(0.2)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.5)
                    pyautogui.press('enter')
                    print("已成功輸入數字並按下 Enter。")

                    # --- 完成輸入後，執行 "恢復" 快捷鍵 ---
                    print("輸入完成，準備執行後置快捷鍵...")
                    press_macro_keys()

                except Exception as e:
                    print(f"自動化操作時發生錯誤：{e}")
            else:
                # 如果之前偵測到過，但現在沒偵測到，就重置旗標
                if not is_first_detection:
                    print("惡魔密碼已消失，恢復正常循環模式。")
                    is_first_detection = True

    except KeyboardInterrupt:
        print("\n程式已由使用者手動中止。")
    except Exception as e:
        print(f"\n程式發生未預期的嚴重錯誤：{e}")

if __name__ == "__main__":
    main()
