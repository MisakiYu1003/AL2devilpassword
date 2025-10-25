# 檔案名稱: config_editor.py (版本 9.5 - 回歸穩定模板匹配)
import tkinter as tk
from tkinter import ttk, messagebox
import re, os, subprocess, sys
try: import screeninfo
except ImportError: messagebox.showerror("缺少函式庫", "請執行 'pip install screeninfo'"); sys.exit()
try: import keyboard
except ImportError: messagebox.showerror("缺少函式庫", "請執行 'pip install keyboard'"); sys.exit()
try: import cv2, numpy
except ImportError: messagebox.showwarning("缺少函式庫", "警告：'圖像辨識模式' 需要 'opencv-python' 和 'numpy'")
if sys.platform == 'win32':
    import ctypes
    try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass
SCRIPT_FILE = "devil_code_all.py"; ENV_FILE = ".env"
MODEL_OPTIONS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]

class ScreenSelector:
    # (ScreenSelector Class 不變)
    def __init__(self, parent, mode):
        self.parent, self.mode, self.result = parent, mode, None; self.overlay = tk.Toplevel(parent); self.overlay.overrideredirect(True); monitors = screeninfo.get_monitors(); min_x, min_y = min(m.x for m in monitors), min(m.y for m in monitors); total_width, total_height = max(m.x + m.width for m in monitors) - min_x, max(m.y + m.height for m in monitors) - min_y; self.overlay.geometry(f"{total_width}x{total_height}+{min_x}+{min_y}"); self.overlay.attributes("-alpha", 0.3); self.canvas = tk.Canvas(self.overlay, cursor="cross", bg="gray"); self.canvas.pack(fill="both", expand=True); self.start_x, self.start_y, self.rect = None, None, None
        if self.mode == "region": info_text, binds = "請按住滑鼠左鍵拖曳，框選出數字所在的矩形區域。\n(支援所有螢幕)\n按下 ESC 鍵取消", [("<ButtonPress-1>", self.on_press), ("<B1-Motion>", self.on_drag), ("<ButtonRelease-1>", self.on_release_region)]
        else: info_text, binds = "請在目標位置點擊滑鼠左鍵一次。\n(支援所有螢幕)\n按下 ESC 鍵取消", [("<ButtonPress-1>", self.on_release_point)]
        for b in binds: self.canvas.bind(b[0], b[1])
        primary_monitor = next(m for m in monitors if m.is_primary); text_x, text_y = (primary_monitor.x-min_x)+primary_monitor.width/2, (primary_monitor.y-min_y)+primary_monitor.height/2; self.canvas.create_text(text_x, text_y, text=info_text, font=("Arial", 20, "bold"), fill="white", justify='center'); self.overlay.bind("<Escape>", self.cancel); self.overlay.focus_force()
    def on_press(self, event): self.start_x, self.start_y = event.x_root, event.y_root; self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline='red', width=2)
    def on_drag(self, event): start_canvas_x, start_canvas_y = self.start_x - int(self.overlay.geometry().split('+')[1]), self.start_y - int(self.overlay.geometry().split('+')[2]); self.canvas.coords(self.rect, start_canvas_x, start_canvas_y, event.x, event.y)
    def on_release_region(self, event): x, y, width, height = min(self.start_x, event.x_root), min(self.start_y, event.y_root), abs(event.x_root - self.start_x), abs(event.y_root - self.start_y); self.result = (x, y, width, height) if width > 0 and height > 0 else None; self.overlay.destroy()
    def on_release_point(self, event): self.result = (event.x_root, event.y_root); self.overlay.destroy()
    def cancel(self, event=None): self.result = None; self.overlay.destroy()

class ConfigApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("惡魔密碼辨識器 - 設定工具 (v9.5)")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.confidence_var = tk.StringVar(value="0.8") # 回歸
        self.api_key_var = tk.StringVar(); self.model_name_var = tk.StringVar(); self.detection_mode_var = tk.StringVar(value='image')
        self.dialog_region_var = tk.StringVar(value="(尚未設定)"); self.click_coord_var = tk.StringVar(value="(尚未設定)")
        self.template_paths_var = tk.StringVar(value="template_input_field.png")
        self.number_offset_var = tk.StringVar(value="(-70, -80, 130, 45)"); self.click_offset_var = tk.StringVar(value="(0, 0)")
        self.loop_interval_var = tk.StringVar(value="3"); self.short_interval_var = tk.StringVar(value="5")
        self.click_type_var = tk.StringVar(); self.macro_key_var = tk.StringVar(value="尚未設定")
        self.is_recording = False; self.running_process = None
        self.create_widgets()
        self.load_initial_values()
        self.after(50, self._adapt_window_size)

    def create_widgets(self):
        container = ttk.Frame(self); container.pack(fill="both", expand=True, padx=10, pady=5); self.canvas = tk.Canvas(container, highlightthickness=0); scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview); self.scrollable_frame = ttk.Frame(self.canvas); self.scrollable_frame.bind("<Configure>", self._on_frame_configure); self.canvas.bind_all("<MouseWheel>", self._on_mousewheel); self.scrollable_frame.bind_all("<MouseWheel>", self._on_mousewheel); self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw"); self.canvas.configure(yscrollcommand=scrollbar.set); self.canvas.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y")
        ai_lf = ttk.LabelFrame(self.scrollable_frame, text="AI 設定", padding=10); ai_lf.pack(fill="x", pady=5, padx=10); ttk.Label(ai_lf, text="1. Gemini API 金鑰:").pack(anchor='w', padx=5); ttk.Entry(ai_lf, textvariable=self.api_key_var, show="*").pack(fill="x", padx=5, pady=(2, 10)); ttk.Label(ai_lf, text="2. AI 模型選擇:").pack(anchor='w', padx=5); ttk.Combobox(ai_lf, textvariable=self.model_name_var, values=MODEL_OPTIONS, state='readonly').pack(fill="x", padx=5, pady=2)
        mode_lf = ttk.LabelFrame(self.scrollable_frame, text="偵測模式選擇", padding=10); mode_lf.pack(fill="x", pady=10, padx=10); ttk.Radiobutton(mode_lf, text="固定座標模式 (傳統、高效)", variable=self.detection_mode_var, value='fixed', command=self.toggle_mode_widgets).pack(anchor='w'); ttk.Radiobutton(mode_lf, text="圖像辨識模式 (模板匹配)", variable=self.detection_mode_var, value='image', command=self.toggle_mode_widgets).pack(anchor='w')
        self.fixed_mode_frame = ttk.LabelFrame(self.scrollable_frame, text="固定座標模式設定", padding=10); self.fixed_mode_frame.pack(fill="x", pady=5, padx=10); f_dialog_frame = ttk.Frame(self.fixed_mode_frame); f_dialog_frame.pack(fill="x", pady=3); ttk.Label(f_dialog_frame, text="數字框範圍:").pack(side="left", padx=5); ttk.Label(f_dialog_frame, textvariable=self.dialog_region_var, font=("Courier", 10)).pack(side="left", padx=5, fill='x', expand=True); ttk.Button(f_dialog_frame, text="開始框選", command=self.select_dialog_region).pack(side="right", padx=5); f_click_frame = ttk.Frame(self.fixed_mode_frame); f_click_frame.pack(fill="x", pady=3); ttk.Label(f_click_frame, text="點擊座標:").pack(side="left", padx=5); ttk.Label(f_click_frame, textvariable=self.click_coord_var, font=("Courier", 10)).pack(side="left", padx=5, fill='x', expand=True); ttk.Button(f_click_frame, text="開始選點", command=self.select_click_coordinate).pack(side="right", padx=5)
        self.image_mode_frame = ttk.LabelFrame(self.scrollable_frame, text="圖像辨識模式設定", padding=10); self.image_mode_frame.pack(fill="x", pady=5, padx=10)
        i_template_frame = ttk.Frame(self.image_mode_frame); i_template_frame.pack(fill="x", pady=3, anchor='w')
        ttk.Label(i_template_frame, text="模板圖片 (用逗號分隔):").pack(side="left", padx=5)
        ttk.Entry(i_template_frame, textvariable=self.template_paths_var).pack(side="left", padx=5, fill='x', expand=True)
        i_conf_frame = ttk.Frame(self.image_mode_frame); i_conf_frame.pack(fill="x", pady=3, anchor='w')
        ttk.Label(i_conf_frame, text="辨識信賴度 (0.0-1.0):").pack(side="left", padx=5)
        ttk.Entry(i_conf_frame, textvariable=self.confidence_var, width=10).pack(side="left", padx=5)
        i_offset_info = ttk.Label(self.image_mode_frame, text="注意：以下位移皆相對於找到的模板圖片『中心點』計算", foreground="blue")
        i_offset_info.pack(fill="x", pady=(5,0), padx=5)
        i_num_offset_frame = ttk.Frame(self.image_mode_frame); i_num_offset_frame.pack(fill="x", pady=3, anchor='w')
        ttk.Label(i_num_offset_frame, text="數字區域相對位移:").pack(side="left", padx=5); ttk.Entry(i_num_offset_frame, textvariable=self.number_offset_var, width=25).pack(side="left", padx=5)
        i_click_offset_frame = ttk.Frame(self.image_mode_frame); i_click_offset_frame.pack(fill="x", pady=3, anchor='w')
        ttk.Label(i_click_offset_frame, text="點擊位置相對位移:").pack(side="left", padx=5); ttk.Entry(i_click_offset_frame, textvariable=self.click_offset_var, width=25).pack(side="left", padx=5)
        adv_lf = ttk.LabelFrame(self.scrollable_frame, text="進階設定", padding=10); adv_lf.pack(fill="x", pady=10, padx=10); interval_frame = ttk.Frame(adv_lf); interval_frame.pack(fill="x", pady=3, anchor='w'); ttk.Label(interval_frame, text="正常循環(秒):").pack(side="left", padx=5); ttk.Entry(interval_frame, textvariable=self.loop_interval_var, width=8).pack(side="left", padx=10); ttk.Label(interval_frame, text="快速循環(秒):").pack(side="left", padx=5); ttk.Entry(interval_frame, textvariable=self.short_interval_var, width=8).pack(side="left", padx=5); click_type_frame = ttk.Frame(adv_lf); click_type_frame.pack(fill="x", pady=3, anchor='w'); ttk.Label(click_type_frame, text="滑鼠點擊方式:").pack(side="left", padx=5); ttk.Combobox(click_type_frame, textvariable=self.click_type_var, values=['click', 'double', 'hold_click'], state='readonly', width=15).pack(side="left", padx=5); macro_frame = ttk.Frame(adv_lf); macro_frame.pack(fill="x", padx=5, pady=5); ttk.Label(macro_frame, text="腳本暫停/繼續快捷鍵 (可選):").pack(side="left", padx=5); ttk.Label(macro_frame, textvariable=self.macro_key_var, font=("Courier", 10), relief="sunken", padding=(5, 2), width=15).pack(side="left", padx=10); self.record_button = ttk.Button(macro_frame, text="設定", command=self.start_recording); self.record_button.pack(side="left", padx=5); ttk.Button(macro_frame, text="清除", command=self.clear_hotkey).pack(side="left")
        control_frame = ttk.Frame(self); control_frame.pack(fill="x", padx=10, pady=(5,10)); control_frame.columnconfigure((0, 1), weight=1); style = ttk.Style(self); style.configure("Accent.TButton", font=("Arial", 12, "bold")); self.run_button = ttk.Button(control_frame, text="儲存設定並開始執行", command=self.save_all_and_run, style="Accent.TButton"); self.run_button.grid(row=0, column=0, padx=5, ipady=10, sticky="ew"); self.stop_button = ttk.Button(control_frame, text="停止執行", command=self.stop_script, state="disabled"); self.stop_button.grid(row=0, column=1, padx=5, ipady=10, sticky="ew"); self.status_var = tk.StringVar(value="請完成設定，點擊下方按鈕執行。"); ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)

    def _get_value(self, content, var_name, default):
        pattern = fr"^{var_name}\s*=\s*(.*)"; match = re.search(pattern, content, re.MULTILINE); return match.group(1).strip() if match else default

    def load_initial_values(self):
        try:
            if os.path.exists(ENV_FILE):
                with open(ENV_FILE, 'r') as f: match = re.search(r"GEMINI_API_KEY=(.*)", f.read()); self.api_key_var.set(match.group(1).strip() if match else "")
        except Exception as e: print(f"讀取 .env 失敗: {e}")
        if not os.path.exists(SCRIPT_FILE): messagebox.showerror("錯誤", f"找不到主程式檔案: {SCRIPT_FILE}"); self.destroy(); return
        try:
            with open(SCRIPT_FILE, 'r', encoding='utf-8') as f: content = f.read()
            model_match = re.search(r"/models/(.*?):generateContent", content)
            self.model_name_var.set(model_match.group(1) if model_match and model_match.group(1) in MODEL_OPTIONS else MODEL_OPTIONS[0])
            self.detection_mode_var.set(self._get_value(content, "DETECTION_MODE", "'fixed'").strip("'"))
            self.dialog_region_var.set(self._get_value(content, "DIALOG_BOX_REGION", "(尚未設定)"))
            self.click_coord_var.set(self._get_value(content, "CLICK_COORDINATE", "(尚未設定)"))
            paths_list_str = self._get_value(content, "TEMPLATE_IMAGE_PATHS", "['template_input_field.png']")
            try: self.template_paths_var.set(", ".join(eval(paths_list_str)))
            except: self.template_paths_var.set("template_input_field.png")
            self.confidence_var.set(self._get_value(content, "CONFIDENCE_LEVEL", "0.8"))
            self.number_offset_var.set(self._get_value(content, "NUMBER_REGION_OFFSET", "(-70, -80, 130, 45)"))
            self.click_offset_var.set(self._get_value(content, "CLICK_OFFSET", "(0, 0)"))
            self.loop_interval_var.set(self._get_value(content, "LOOP_INTERVAL", "3"))
            self.short_interval_var.set(self._get_value(content, "SHORT_INTERVAL", "5"))
            self.click_type_var.set(self._get_value(content, "CLICK_TYPE", "'hold_click'").strip("'"))
            macro_key = self._get_value(content, "MACRO_TOGGLE_KEYS", "''").strip("'")
            self.macro_key_var.set(macro_key if macro_key else "尚未設定")
        except Exception as e: messagebox.showerror("讀取錯誤", f"讀取 {SCRIPT_FILE} 失敗: {e}")
        self.toggle_mode_widgets()

    def save_settings(self):
        if not self.api_key_var.get().strip(): messagebox.showerror("錯誤", "API 金鑰為必填項！"); return False
        try:
            with open(ENV_FILE, 'w') as f: f.write(f"GEMINI_API_KEY={self.api_key_var.get().strip()}")
            with open(SCRIPT_FILE, 'r', encoding='utf-8') as f: content = f.read()
            new_model = self.model_name_var.get()
            content = re.sub(r'(url\s*=\s*f".*?/models/)(.*?)(:generateContent.*")', fr'\g<1>{new_model}\g<3>', content, flags=re.MULTILINE)
            paths_list = [f"'{path.strip()}'" for path in self.template_paths_var.get().split(',') if path.strip()]
            template_paths_formatted = f"[{', '.join(paths_list)}]"
            settings_to_save = { "DETECTION_MODE": f"'{self.detection_mode_var.get()}'", "DIALOG_BOX_REGION": self.dialog_region_var.get(), "CLICK_COORDINATE": self.click_coord_var.get(), "TEMPLATE_IMAGE_PATHS": template_paths_formatted, "CONFIDENCE_LEVEL": self.confidence_var.get(), "NUMBER_REGION_OFFSET": self.number_offset_var.get(), "CLICK_OFFSET": self.click_offset_var.get(), "LOOP_INTERVAL": self.loop_interval_var.get(), "SHORT_INTERVAL": self.short_interval_var.get(), "CLICK_TYPE": f"'{self.click_type_var.get()}'", "MACRO_TOGGLE_KEYS": f"'{self.macro_key_var.get() if self.macro_key_var.get() != '尚未設定' else ''}'"}
            # 移除舊的不用的設定項，以防萬一
            content = re.sub(r"^MIN_MATCH_COUNT\s*=\s*.*", "", content, flags=re.MULTILINE)
            for var, val in settings_to_save.items():
                pattern = re.compile(fr"^{var}\s*=\s*.*", re.MULTILINE)
                replacement = f"{var} = {val}"
                if pattern.search(content): content = pattern.sub(replacement, content)
                else: content = f"{replacement}\n{content}"
            with open(SCRIPT_FILE, 'w', encoding='utf-8') as f: f.write(content)
            return True
        except Exception as e: messagebox.showerror("儲存失敗", f"寫入檔案時發生錯誤: {e}"); return False
        
    def _adapt_window_size(self): self.update_idletasks(); req_width = self.scrollable_frame.winfo_reqwidth(); req_height = self.scrollable_frame.winfo_reqheight(); final_width = req_width + 50; final_height = req_height + 120; screen_width = self.winfo_screenwidth(); screen_height = self.winfo_screenheight(); final_width = min(final_width, int(screen_width * 0.9)); final_height = min(final_height, int(screen_height * 0.9)); pos_x = (screen_width // 2) - (final_width // 2); pos_y = (screen_height // 2) - (final_height // 2); self.geometry(f"{final_width}x{final_height}+{pos_x}+{pos_y}"); self.minsize(final_width, 400)
    def _on_frame_configure(self, event): self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    def _on_mousewheel(self, event): self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    def _set_children_state(self, parent, state):
        for widget in parent.winfo_children():
            try: widget.configure(state=state)
            except tk.TclError: pass
            self._set_children_state(widget, state)
    def toggle_mode_widgets(self):
        selected_mode = self.detection_mode_var.get()
        if selected_mode == 'fixed': self._set_children_state(self.fixed_mode_frame, 'normal'); self._set_children_state(self.image_mode_frame, 'disabled')
        elif selected_mode == 'image': self._set_children_state(self.fixed_mode_frame, 'disabled'); self._set_children_state(self.image_mode_frame, 'normal')
    def save_all_and_run(self):
        if self.save_settings():
            try: self.running_process = subprocess.Popen([sys.executable, SCRIPT_FILE], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0); self.status_var.set(f"主程式 '{SCRIPT_FILE}' 正在背景執行中..."); self.run_button.config(state="disabled"); self.stop_button.config(state="normal")
            except Exception as e: messagebox.showerror("啟動失敗", f"無法啟動 {SCRIPT_FILE}：\n{e}")
    def stop_script(self):
        if self.running_process and self.running_process.poll() is None: self.running_process.terminate(); self.status_var.set("主程式已成功終止。")
        else: self.status_var.set("主程式未在執行或已自行結束。")
        self.running_process = None; self.run_button.config(state="normal"); self.stop_button.config(state="disabled")
    def on_closing(self):
        if self.running_process and self.running_process.poll() is None:
            if messagebox.askyesno("確認", "主程式仍在執行中，您確定要關閉並中止主程式嗎？"): self.stop_script(); self.destroy()
        else: self.destroy()
    def select_dialog_region(self): self.withdraw(); selector = ScreenSelector(self, mode="region"); self.wait_window(selector.overlay); self.deiconify(); self.dialog_region_var.set(str(selector.result) if selector.result else self.dialog_region_var.get());
    def select_click_coordinate(self): self.withdraw(); selector = ScreenSelector(self, mode="point"); self.wait_window(selector.overlay); self.deiconify(); self.click_coord_var.set(str(selector.result) if selector.result else self.click_coord_var.get());
    def start_recording(self):
        if self.is_recording: return
        self.is_recording = True; self.status_var.set("錄製模式：請按下快捷鍵... (按 ESC 取消)"); self.record_button.config(text="錄製中...", state="disabled"); self.grab_set(); self.bind("<KeyPress>", self.on_key_press_record); self.bind("<Escape>", self.cancel_recording)
    def stop_recording(self): self.is_recording = False; self.status_var.set("錄製完成。"); self.record_button.config(text="設定", state="normal"); self.unbind("<KeyPress>"); self.unbind("<Escape>"); self.grab_release()
    def cancel_recording(self, event=None):
        if not self.is_recording: return; self.status_var.set("錄製已取消。"); self.stop_recording(); return "break"
    def on_key_press_record(self, event):
        if event.keysym.lower() in ('control_l', 'control_r', 'alt_l', 'alt_r', 'shift_l', 'shift_r', 'win_l', 'win_r'): return
        parts = []; KEYSYM_MAP = {'return': 'enter', 'escape': 'esc'}
        if keyboard.is_pressed('ctrl'): parts.append('ctrl')
        if keyboard.is_pressed('alt'): parts.append('alt')
        if keyboard.is_pressed('shift'): parts.append('shift')
        if keyboard.is_pressed('win'): parts.append('win')
        key_name = KEYSYM_MAP.get(event.keysym.lower(), event.keysym.lower())
        if key_name not in parts: parts.append(key_name)
        self.macro_key_var.set(",".join(parts)); self.stop_recording(); return "break"
    def clear_hotkey(self): self.macro_key_var.set("尚未設定"); self.status_var.set("快捷鍵設定已清除。")

if __name__ == "__main__":
    app = ConfigApp()
    app.mainloop()