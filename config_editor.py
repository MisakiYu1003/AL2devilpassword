# 檔案名稱: config_editor.py (版本 5.5 - 新增快速循環設定)
import tkinter as tk
from tkinter import ttk, messagebox
import re
import os
import subprocess
import sys

try:
    import screeninfo
except ImportError:
    messagebox.showerror("缺少函式庫", "找不到 'screeninfo' 函式庫。\n請先執行 'pip install screeninfo' 來安裝。")
    sys.exit()

try:
    import keyboard
except ImportError:
    messagebox.showerror("缺少函式庫", "找不到 'keyboard' 函式庫。\n請先執行 'pip install keyboard' 來安裝。\n\n注意：在某些系統上可能需要系統管理員權限 (以系統管理員身分執行 cmd)。")
    sys.exit()


if sys.platform == 'win32':
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e:
            print(f"警告：設定 DPI 感知失敗: {e}")

# --- 常數設定 ---
ENV_FILE = ".env"
SCRIPT_FILE = "devil_code_solver.py"
DIALOG_VAR_NAME = "DIALOG_BOX_REGION"
CLICK_VAR_NAME = "CLICK_COORDINATE"
LOOP_VAR_NAME = "LOOP_INTERVAL"
SHORT_INTERVAL_VAR_NAME = "SHORT_INTERVAL" # 新增常數
CLICK_TYPE_VAR_NAME = "CLICK_TYPE"
MACRO_KEY_VAR_NAME = "MACRO_TOGGLE_KEYS"
MODEL_OPTIONS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro",  "gemini-3-pro-preview", "gemini-3-flash-preview","gemma-3-27b-it","gemma-3-4b-it"]
CLICK_OPTIONS_MAP = {
    '左鍵單擊 (Click)': 'click',
    '左鍵雙擊 (DoubleClick)': 'double',
    '左鍵長按 (Hold Click)': 'hold_click',
    '無 (僅移動)': 'none'
}
CLICK_OPTIONS_DISPLAY = list(CLICK_OPTIONS_MAP.keys())
CLICK_VALUES_MAP = {v: k for k, v in CLICK_OPTIONS_MAP.items()}

# Tkinter 的 keysym 對應 pyautogui 的名稱
KEYSYM_MAP = {
    'control_l': 'ctrl', 'control_r': 'ctrl',
    'alt_l': 'alt', 'alt_r': 'alt',
    'shift_l': 'shift', 'shift_r': 'shift',
    'win_l': 'win', 'win_r': 'win',
    'return': 'enter',
    'backspace': 'backspace',
    'delete': 'delete',
    'escape': 'esc',
    'prior': 'pageup',
    'next': 'pagedown'
}

class ScreenSelector:
    def __init__(self, parent, mode):
        self.parent, self.mode, self.result = parent, mode, None; self.overlay = tk.Toplevel(parent); self.overlay.overrideredirect(True)
        monitors = screeninfo.get_monitors(); min_x, min_y = min(m.x for m in monitors), min(m.y for m in monitors)
        total_width, total_height = max(m.x + m.width for m in monitors) - min_x, max(m.y + m.height for m in monitors) - min_y
        self.overlay.geometry(f"{total_width}x{total_height}+{min_x}+{min_y}"); self.overlay.attributes("-alpha", 0.3)
        self.canvas = tk.Canvas(self.overlay, cursor="cross", bg="gray"); self.canvas.pack(fill="both", expand=True)
        self.start_x, self.start_y, self.rect = None, None, None
        if self.mode == "region": info_text, binds = "請按住滑鼠左鍵拖曳，框選出數字所在的矩形區域。\n(支援所有螢幕)\n按下 ESC 鍵取消", [("<ButtonPress-1>", self.on_press), ("<B1-Motion>", self.on_drag), ("<ButtonRelease-1>", self.on_release_region)]
        else: info_text, binds = "請在目標位置點擊滑鼠左鍵一次。\n(支援所有螢幕)\n按下 ESC 鍵取消", [("<ButtonPress-1>", self.on_release_point)]
        for b in binds: self.canvas.bind(b[0], b[1])
        primary_monitor = next(m for m in monitors if m.is_primary); text_x, text_y = (primary_monitor.x-min_x)+primary_monitor.width/2, (primary_monitor.y-min_y)+primary_monitor.height/2
        self.canvas.create_text(text_x, text_y, text=info_text, font=("Arial", 20, "bold"), fill="white", justify='center')
        self.overlay.bind("<Escape>", self.cancel); self.overlay.focus_force()
    def on_press(self, event): self.start_x, self.start_y = event.x_root, event.y_root; self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline='red', width=2)
    def on_drag(self, event): start_canvas_x, start_canvas_y = self.start_x - int(self.overlay.geometry().split('+')[1]), self.start_y - int(self.overlay.geometry().split('+')[2]); self.canvas.coords(self.rect, start_canvas_x, start_canvas_y, event.x, event.y)
    def on_release_region(self, event): x, y, width, height = min(self.start_x, event.x_root), min(self.start_y, event.y_root), abs(event.x_root - self.start_x), abs(event.y_root - self.start_y); self.result = (x, y, width, height) if width > 0 and height > 0 else None; self.overlay.destroy()
    def on_release_point(self, event): self.result = (event.x_root, event.y_root); self.overlay.destroy()
    def cancel(self, event=None): self.result = None; self.overlay.destroy()

class ConfigApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("惡魔密碼辨識器 - 設定工具-版本 5.5")
        self.geometry("580x680")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.api_key_var, self.dialog_region_var = tk.StringVar(), tk.StringVar()
        self.click_coord_var, self.loop_interval_var = tk.StringVar(), tk.StringVar()
        self.short_interval_var = tk.StringVar() # 新增變數
        self.model_name_var, self.click_type_var = tk.StringVar(), tk.StringVar()
        self.macro_key_var = tk.StringVar(value="尚未設定")
        self.is_recording = False
        self.running_process = None
        self.create_widgets()
        self.load_initial_values()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="15"); main_frame.pack(fill="both", expand=True)
        settings_frame = ttk.Frame(main_frame); settings_frame.pack(fill="x", expand=True)

        ttk.LabelFrame(settings_frame, text="1. Gemini API 金鑰設定", padding="10").pack(fill="x", pady=5)
        ttk.Entry(settings_frame.winfo_children()[-1], textvariable=self.api_key_var).pack(side="left", fill="x", expand=True, padx=5)
        ttk.LabelFrame(settings_frame, text="2. AI 模型設定", padding="10").pack(fill="x", pady=5)
        ttk.Combobox(settings_frame.winfo_children()[-1], textvariable=self.model_name_var, values=MODEL_OPTIONS, state='readonly').pack(side="left", padx=5)
        ttk.LabelFrame(settings_frame, text="3. 惡魔密碼數字框範圍", padding="10").pack(fill="x", pady=5)
        dialog_lf = settings_frame.winfo_children()[-1]
        ttk.Label(dialog_lf, text="目前數值:").pack(side="left", padx=5); ttk.Label(dialog_lf, textvariable=self.dialog_region_var, font=("Courier", 10)).pack(side="left", padx=5)
        ttk.Button(dialog_lf, text="開始框選", command=self.select_dialog_region).pack(side="right", padx=5)
        click_frame = ttk.LabelFrame(settings_frame, text="4. 輸入前滑鼠動作", padding="10"); click_frame.pack(fill="x", pady=5)
        coord_frame = ttk.Frame(click_frame); coord_frame.pack(fill="x")
        ttk.Label(coord_frame, text="動作座標:").pack(side="left", padx=5); ttk.Label(coord_frame, textvariable=self.click_coord_var, font=("Courier", 10)).pack(side="left", padx=5)
        ttk.Button(coord_frame, text="開始選點", command=self.select_click_coordinate).pack(side="right", padx=5)
        type_frame = ttk.Frame(click_frame); type_frame.pack(fill="x", pady=(5,0))
        ttk.Label(type_frame, text="動作類型:").pack(side="left", padx=5)
        ttk.Combobox(type_frame, textvariable=self.click_type_var, values=CLICK_OPTIONS_DISPLAY, state='readonly', width=25).pack(side="left", padx=5)

        # --- *** 修改後的第 5 項設定 *** ---
        interval_lf = ttk.LabelFrame(settings_frame, text="5. 循環間隔設定 (秒)", padding="10")
        interval_lf.pack(fill="x", pady=5)
        ttk.Label(interval_lf, text="正常循環 (建議>100):").pack(side="left", padx=(5,0))
        ttk.Entry(interval_lf, textvariable=self.loop_interval_var, width=8).pack(side="left", padx=(5, 15))
        ttk.Label(interval_lf, text="快速循環 (偵測到後):").pack(side="left", padx=(5,0))
        ttk.Entry(interval_lf, textvariable=self.short_interval_var, width=8).pack(side="left", padx=5)

        # --- 第 6 項設定不變 ---
        macro_lf = ttk.LabelFrame(settings_frame, text="6. 按鍵精靈暫停/繼續快捷鍵 (可選)", padding="10")
        macro_lf.pack(fill="x", pady=5)
        macro_display_frame = ttk.Frame(macro_lf)
        macro_display_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(macro_display_frame, text="目前設定:").pack(side="left")
        ttk.Label(macro_display_frame, textvariable=self.macro_key_var, font=("Courier", 10, "bold"), relief="sunken", padding=(5, 2), width=20).pack(side="left", padx=10)
        self.record_button = ttk.Button(macro_display_frame, text="設定快捷鍵", command=self.start_recording)
        self.record_button.pack(side="left", padx=5)
        ttk.Button(macro_display_frame, text="清除", command=self.clear_hotkey).pack(side="left")

        control_frame = ttk.Frame(main_frame); control_frame.pack(fill="x", pady=20)
        control_frame.columnconfigure(0, weight=1); control_frame.columnconfigure(1, weight=1)
        style = ttk.Style(self); style.configure("Accent.TButton", font=("Arial", 12, "bold"))
        self.run_button = ttk.Button(control_frame, text="儲存設定並開始執行", command=self.save_all_and_run, style="Accent.TButton")
        self.run_button.grid(row=0, column=0, padx=5, ipady=10, sticky="ew")
        self.stop_button = ttk.Button(control_frame, text="停止執行", command=self.stop_script, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5, ipady=10, sticky="ew")
        self.status_var = tk.StringVar(value="請依序完成設定，點擊下方按鈕執行。")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def start_recording(self):
        if self.is_recording: return
        self.is_recording = True
        self.status_var.set("錄製模式：請直接在鍵盤上按下您要設定的快捷鍵... (按 ESC 取消)")
        self.record_button.config(text="錄製中...", state="disabled")
        self.grab_set()
        self.bind("<KeyPress>", self.on_key_press_record)
        self.bind("<Escape>", self.cancel_recording)

    def stop_recording(self):
        self.is_recording = False
        self.status_var.set("錄製完成。")
        self.record_button.config(text="設定快捷鍵", state="normal")
        self.unbind("<KeyPress>")
        self.unbind("<Escape>")
        self.grab_release()

    def cancel_recording(self, event=None):
        if not self.is_recording: return
        self.status_var.set("錄製已取消。")
        self.stop_recording()
        return "break"

    def on_key_press_record(self, event):
        if event.keysym in ('Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Shift_L', 'Shift_R', 'Win_L', 'Win_R', 'Meta_L', 'Meta_R'):
            return

        parts = []
        if keyboard.is_pressed('ctrl') or keyboard.is_pressed('left ctrl') or keyboard.is_pressed('right ctrl'):
            parts.append('ctrl')
        if keyboard.is_pressed('alt') or keyboard.is_pressed('left alt') or keyboard.is_pressed('right alt'):
            if not ('ctrl' in parts and keyboard.is_pressed('right alt')):
                 parts.append('alt')
        if keyboard.is_pressed('shift') or keyboard.is_pressed('left shift') or keyboard.is_pressed('right shift'):
            parts.append('shift')
        if keyboard.is_pressed('win') or keyboard.is_pressed('left windows') or keyboard.is_pressed('right windows'):
            parts.append('win')

        key_name = event.keysym.lower()
        if key_name in KEYSYM_MAP:
            key_name = KEYSYM_MAP[key_name]
        
        if key_name not in parts:
            parts.append(key_name)
        
        hotkey_string = ",".join(parts)
        self.macro_key_var.set(hotkey_string)
        self.stop_recording()
        return "break"

    def clear_hotkey(self):
        self.macro_key_var.set("尚未設定")
        self.status_var.set("快捷鍵設定已清除。")

    def load_initial_values(self):
        try:
            if os.path.exists(ENV_FILE):
                with open(ENV_FILE, 'r') as f:
                    match = re.search(r"GEMINI_API_KEY=(.*)", f.read())
                    if match: self.api_key_var.set(match.group(1).strip())
        except Exception: pass
        if not os.path.exists(SCRIPT_FILE): messagebox.showerror("錯誤", f"找不到主程式檔案: {SCRIPT_FILE}"); self.destroy(); return
        try:
            with open(SCRIPT_FILE, 'r', encoding='utf-8') as f: content = f.read()
            model_match = re.search(r"/models/(.*?):generateContent", content); self.model_name_var.set(model_match.group(1) if model_match and model_match.group(1) in MODEL_OPTIONS else MODEL_OPTIONS[0])
            dialog_match = re.search(fr"{DIALOG_VAR_NAME}\s*=\s*(\(.*\))", content); self.dialog_region_var.set(dialog_match.group(1) if dialog_match else "(尚未設定)")
            click_match = re.search(fr"{CLICK_VAR_NAME}\s*=\s*(\(.*\))", content); self.click_coord_var.set(click_match.group(1) if click_match else "(尚未設定)")
            
            # --- *** 更新讀取邏輯 *** ---
            loop_match = re.search(fr"{LOOP_VAR_NAME}\s*=\s*(\d+\.?\d*)", content); self.loop_interval_var.set(loop_match.group(1) if loop_match else "100")
            short_interval_match = re.search(fr"{SHORT_INTERVAL_VAR_NAME}\s*=\s*(\d+\.?\d*)", content); self.short_interval_var.set(short_interval_match.group(1) if short_interval_match else "10")

            click_type_match = re.search(fr"{CLICK_TYPE_VAR_NAME}\s*=\s*['\"](.*?)['\"]", content)
            if click_type_match and click_type_match.group(1) in CLICK_VALUES_MAP: self.click_type_var.set(CLICK_VALUES_MAP[click_type_match.group(1)])
            else: self.click_type_var.set(CLICK_OPTIONS_DISPLAY[0])
            
            macro_key_match = re.search(fr"{MACRO_KEY_VAR_NAME}\s*=\s*['\"](.*?)['\"]", content)
            self.macro_key_var.set(macro_key_match.group(1) if (macro_key_match and macro_key_match.group(1)) else "尚未設定")
        except Exception as e: messagebox.showerror("讀取錯誤", f"讀取 {SCRIPT_FILE} 失敗: {e}")

    def save_settings(self):
        # --- *** 更新驗證邏輯 *** ---
        try:
            float(self.loop_interval_var.get().strip())
            float(self.short_interval_var.get().strip())
        except ValueError:
            messagebox.showerror("錯誤", "正常循環和快速循環的秒數都必須是純數字！"); return False
        
        if not all([self.api_key_var.get().strip(), self.model_name_var.get().strip(), self.click_type_var.get()]):
            messagebox.showerror("錯誤", "API 金鑰, AI 模型和點擊方式為必填項！"); return False

        try:
            with open(ENV_FILE, 'w') as f: f.write(f"GEMINI_API_KEY={self.api_key_var.get().strip()}")
            with open(SCRIPT_FILE, 'r', encoding='utf-8') as f: content = f.read()
            new_model = self.model_name_var.get().strip()
            pattern = re.compile(r'(url\s*=\s*f".*?/models/)(.*?)(:generateContent.*")', re.MULTILINE)
            content = pattern.sub(fr'\g<1>{new_model}\g<3>', content)
            
            # --- *** 更新儲存邏輯 *** ---
            for var, val_str in [(DIALOG_VAR_NAME, self.dialog_region_var.get()),
                                 (CLICK_VAR_NAME, self.click_coord_var.get()),
                                 (LOOP_VAR_NAME, self.loop_interval_var.get()),
                                 (SHORT_INTERVAL_VAR_NAME, self.short_interval_var.get())]:
                pattern = re.compile(fr"^{var}\s*=\s*.*", re.MULTILINE)
                content = pattern.sub(f"{var} = {val_str}", content)
            
            click_type_value = CLICK_OPTIONS_MAP[self.click_type_var.get()]
            macro_key_value = self.macro_key_var.get()
            if macro_key_value == "尚未設定": macro_key_value = ""

            for var, val_str in [(CLICK_TYPE_VAR_NAME, click_type_value), (MACRO_KEY_VAR_NAME, macro_key_value)]:
                pattern = re.compile(fr"^{var}\s*=\s*.*", re.MULTILINE)
                content = pattern.sub(f"{var} = '{val_str}'", content)

            with open(SCRIPT_FILE, 'w', encoding='utf-8') as f: f.write(content)
            return True
        except Exception as e: messagebox.showerror("儲存失敗", f"寫入檔案時發生錯誤: {e}"); return False

    def save_all_and_run(self):
        if self.save_settings():
            try:
                self.running_process = subprocess.Popen([sys.executable, SCRIPT_FILE])
                self.status_var.set(f"主程式 '{SCRIPT_FILE}' 正在執行中...")
                self.run_button.config(state="disabled"); self.stop_button.config(state="normal")
            except Exception as e: messagebox.showerror("啟動失敗", f"無法啟動 {SCRIPT_FILE}：\n{e}")

    def stop_script(self):
        if self.running_process and self.running_process.poll() is None:
            self.running_process.terminate(); self.status_var.set("主程式已成功終止。")
        else: self.status_var.set("主程式未在執行或已自行結束。")
        self.running_process = None; self.run_button.config(state="normal"); self.stop_button.config(state="disabled")

    def on_closing(self):
        if self.running_process and self.running_process.poll() is None:
            if messagebox.askyesno("確認", "主程式仍在執行中，您確定要關閉並中止主程式嗎？"): self.stop_script(); self.destroy()
        else: self.destroy()

    def select_dialog_region(self):
        self.withdraw(); selector = ScreenSelector(self, mode="region"); self.wait_window(selector.overlay); self.deiconify()
        if selector.result: self.dialog_region_var.set(str(selector.result)); self.status_var.set(f"數字框範圍已暫存")

    def select_click_coordinate(self):
        self.withdraw(); selector = ScreenSelector(self, mode="point"); self.wait_window(selector.overlay); self.deiconify()
        if selector.result: self.click_coord_var.set(str(selector.result)); self.status_var.set(f"點擊座標已暫存")

if __name__ == "__main__":
    app = ConfigApp()
    app.mainloop()


