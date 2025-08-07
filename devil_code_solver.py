import pyautogui
import time
import requests
import base64
import os
import io
import re
import json # 匯入 JSON 處理模組
import pyperclip # *** 新增 ***：匯入剪貼簿處理模組
from PIL import Image
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數 (API 金鑰)
load_dotenv()
# ---密鑰格式  https://aistudio.google.com/app/apikey  該網址申請  並放在=後面  GEMINI_API_KEY=

# --- 您需要根據您的螢幕設定以下參數 ---

# 1. 惡魔密碼數字框在螢幕上的座標 (x, y, 向右寬度, 往下高度)
# *** 極度重要 ***: 請精準地只框選數字區域。
DIALOG_BOX_REGION = (2136, 1234, 250, 100)  

# 2. 設定輸入前要點擊的座標 (x, y)
#    建議設定為遊戲視窗內的一個安全位置。
CLICK_COORDINATE = (2357, 1358)

# 3. *** 新增 ***: 設定滑鼠連點兩次之間的間隔時間 (秒)
DOUBLE_CLICK_INTERVAL = 0.25

# 4. 正常循環的間隔時間 (秒) 建議100
LOOP_INTERVAL = 100

# 5. 偵測到數字後，快速循環的間隔時間 (秒)
SHORT_INTERVAL = 10

# --- 以下為程式碼主體，通常不需要修改 ---

def get_gemini_api_key():
    """從環境變數中獲取 Gemini API 金鑰"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("錯誤：找不到 GEMINI_API_KEY。請確認您已經設定好 .env 檔案。")
        exit()
    return api_key

def capture_screen_region(region):
    """擷取螢幕指定區域的畫面。"""
    try:
        # print(f"正在擷取螢幕區域：{region}")
        screenshot = pyautogui.screenshot(region=region)
        # 儲存截圖以供除錯
        screenshot.save("debug_screenshot.png") 
        # print("已儲存除錯用截圖至 'debug_screenshot.png'。")
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
    
    """使用 Gemini Vision API 可以自行更換版本如:gemini-2.5-flash-lite換成gemini-2.5-pro 。"""
    base64_image = encode_image_to_base64(image)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    # *** 已更新：使用兩段式驗證的 AI 指令 (Prompt) ***
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
                
                # *** 已更新：解析 JSON 並進行兩段式驗證 ***
                try:
                    # 清理 AI 可能回傳的 Markdown 格式
                    cleaned_text = text_content.strip().replace('```json', '').replace('```', '')
                    response_json = json.loads(cleaned_text)
                    
                    # 檢查 AI 是否判斷有數字
                    if response_json.get("contains_digits") is True:
                        extracted_number = response_json.get("extracted_number")
                        # 再次驗證回傳的數字是否為有效的字串
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
    try:
        while True:
            # --- 正常循環 ---
            print(f"\n--- 正常循環，將在 {LOOP_INTERVAL} 秒後掃描 ---")
            time.sleep(LOOP_INTERVAL)
            
            # 1. 擷取固定座標的畫面
            image_to_process = capture_screen_region(DIALOG_BOX_REGION)
            if image_to_process is None:
                continue

            # 2. 將圖片送去辨識
            numbers_to_type = get_numbers_from_image(image_to_process, api_key)
            
            # --- 智慧循環偵測 ---
            # 如果偵測到了數字，就進入快速循環模式
            while numbers_to_type:
                print(f"偵測到數字: {numbers_to_type}！進入快速偵測模式...")
                
                try:
                    # 1. 移動滑鼠、點擊並歸位
                    print(f"移動滑鼠至 {CLICK_COORDINATE} 並點擊兩次...")
                    original_pos = pyautogui.position() # 儲存滑鼠原始位置
                    pyautogui.moveTo(CLICK_COORDINATE[0], CLICK_COORDINATE[1], duration=0.25)
                    # *** 已更新：使用可設定的連點間隔 ***
                    pyautogui.doubleClick(interval=DOUBLE_CLICK_INTERVAL) 
                    pyautogui.moveTo(original_pos[0], original_pos[1], duration=0.25) # 將滑鼠移回原位
                    print("滑鼠已歸位。")
                    
                    # *** 已更新：使用剪貼簿來避免輸入法干擾 ***
                    print(f"準備使用剪貼簿貼上數字: {numbers_to_type}")
                    pyperclip.copy(numbers_to_type) # 將數字複製到剪貼簿
                    time.sleep(0.2) # 等待剪貼簿準備就緒
                    pyautogui.hotkey('ctrl', 'v') # 模擬貼上 (Ctrl+V)
                    
                    time.sleep(0.5)
                    pyautogui.press('enter')
                    print("已成功輸入數字並按下 Enter。")

                except Exception as e:
                    print(f"自動化操作時發生錯誤：{e}")

                # 3. 等待短時間後，再次偵測
                print(f"處理完畢，將在 {SHORT_INTERVAL} 秒後再次偵測...")
                time.sleep(SHORT_INTERVAL)
                
                # 重新擷取與辨識，以更新循環條件
                image_to_process = capture_screen_region(DIALOG_BOX_REGION)
                if image_to_process:
                    numbers_to_type = get_numbers_from_image(image_to_process, api_key)
                else:
                    numbers_to_type = None # 如果截圖失敗，就設為 None 以跳出循環

            # 當 numbers_to_type 為 None 時，代表快速循環結束
            print("未偵測到數字，恢復正常循環。")

    except KeyboardInterrupt:
        print("\n程式已由使用者手動中止。")
    except Exception as e:
        print(f"\n程式發生未預期的嚴重錯誤：{e}")

if __name__ == "__main__":
    main()
