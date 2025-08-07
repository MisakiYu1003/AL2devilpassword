import pyautogui
import time

print("螢幕座標獲取工具已啟動。")
print("請將您的滑鼠指標移動到螢幕上的任何位置。")
print("按下 Ctrl+C 即可結束程式。")

try:
    while True:
        # 獲取當前滑鼠的 X 和 Y 座標
        x, y = pyautogui.position()
        
        # 格式化輸出字串，讓數字對齊，方便觀看
        positionStr = 'X: ' + str(x).rjust(4) + ' Y: ' + str(y).rjust(4)
        
        # 在同一行上不斷更新座標訊息
        print(positionStr, end='')
        print('\b' * len(positionStr), end='', flush=True)
        
        # 短暫延遲，避免過度消耗系統資源
        time.sleep(0.1)

except KeyboardInterrupt:
    # 當使用者按下 Ctrl+C 時，優雅地結束程式
    print('\n\n程式已結束。')

