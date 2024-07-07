import tkinter as tk
from tkinter import ttk, messagebox, font
from deep_translator import GoogleTranslator
import pyautogui
import win32gui
import win32com.client
import time
import os
import wcocr
import hashlib
import pykakasi 
import difflib
from ttkbootstrap import Style

# Initialize WeChat OCR
wechat_path = r"e:\WeChat\[3.9.11.19]"
wechatocr_path = os.getenv("APPDATA") + r"\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7079\extracted\WeChatOCR.exe"
wcocr.init(wechatocr_path, wechat_path)

class WindowSelector:
    def __init__(self):
        self.hwnd = None

    def get_windows(self):
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                windows.append((hwnd, win32gui.GetWindowText(hwnd)))
            return True
        windows = []
        win32gui.EnumWindows(callback, windows)
        return windows

    def select_window(self):
        windows = self.get_windows()
        root = tk.Tk()
        root.title("选择游戏窗口")
        listbox = tk.Listbox(root, width=50)
        listbox.pack(padx=10, pady=10)

        for _, title in windows:
            listbox.insert(tk.END, title)

        def on_select():
            selection = listbox.curselection()
            if selection:
                self.hwnd = windows[selection[0]][0]
                root.quit()

        button = tk.Button(root, text="选择", command=on_select)
        button.pack(pady=5)

        root.mainloop()
        root.destroy()
        return self.hwnd

class TranslatorGUI:
    def __init__(self, master):
        self.master = master
        master.title("实时游戏翻译器")

        # Use ttkbootstrap for a modern look
        style = Style(theme="cosmo")

        # Set window size and make it resizable
        master.geometry("900x700")
        master.minsize(600, 400)

        # Custom fonts
        self.title_font = font.Font(family="Microsoft YaHei", size=16, weight="bold")
        self.text_font = font.Font(family="Microsoft YaHei", size=12)

        # Main frame
        main_frame = ttk.Frame(master, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="游戏实时翻译助手", font=self.title_font, foreground="#3498db")
        title_label.pack(pady=(0, 20))

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Main tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="主界面")

        # Settings tab
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="设置")

        # Create main tab content
        self.create_main_tab()

        # Create settings tab content
        self.create_settings_tab()

        # Button frame
        button_frame = ttk.Frame(main_frame, padding=(0, 20, 0, 0))
        button_frame.pack(fill=tk.X)

        # Create select window button
        self.select_window_button = ttk.Button(button_frame, text="选择游戏窗口", command=self.select_window, style="info.TButton")
        self.select_window_button.pack(side=tk.LEFT, padx=(0, 10))

        # Create start/stop button
        self.start_stop_button = ttk.Button(button_frame, text="开始翻译", command=self.toggle_translation, style="success.TButton")
        self.start_stop_button.pack(side=tk.LEFT)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.is_translating = False
        self.hwnd = None
        self.last_screenshot_hash = None
        self.last_ocr_result = None
        self.threshold_top = 0.5
        self.threshold_bottom = 0.9

    def create_main_tab(self):
        # Original text area
        original_frame = ttk.LabelFrame(self.main_tab, text="原文", padding=10)
        original_frame.pack(fill=tk.BOTH, expand=True)

        self.original_text = tk.Text(original_frame, height=5, width=50, font=self.text_font, wrap=tk.WORD)
        self.original_text.pack(fill=tk.BOTH, expand=True)

        # Romaji text area
        romaji_frame = ttk.LabelFrame(self.main_tab, text="罗马字注音", padding=10)
        romaji_frame.pack(fill=tk.BOTH, expand=True)

        self.romaji_text = tk.Text(romaji_frame, height=5, width=50, font=self.text_font, wrap=tk.WORD)
        self.romaji_text.pack(fill=tk.BOTH, expand=True)

        # Translated text area
        translated_frame = ttk.LabelFrame(self.main_tab, text="翻译", padding=10)
        translated_frame.pack(fill=tk.BOTH, expand=True)

        self.translated_text = tk.Text(translated_frame, height=5, width=50, font=self.text_font, wrap=tk.WORD)
        self.translated_text.pack(fill=tk.BOTH, expand=True)

    def create_settings_tab(self):
        # Threshold input frame
        threshold_frame = ttk.LabelFrame(self.settings_tab, text="阈值设置", padding=10)
        threshold_frame.pack(fill=tk.X, pady=(10, 0))

        # Threshold top input
        ttk.Label(threshold_frame, text="上阈值 (0-1):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.threshold_top_var = tk.StringVar(value="0.5")
        self.threshold_top_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_top_var, width=10)
        self.threshold_top_entry.grid(row=0, column=1, padx=5, pady=5)

        # Threshold bottom input
        ttk.Label(threshold_frame, text="下阈值 (0-1):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.threshold_bottom_var = tk.StringVar(value="0.9")
        self.threshold_bottom_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_bottom_var, width=10)
        self.threshold_bottom_entry.grid(row=1, column=1, padx=5, pady=5)

        # Apply threshold button
        self.apply_threshold_button = ttk.Button(threshold_frame, text="应用阈值", command=self.apply_threshold, style="info.TButton")
        self.apply_threshold_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10)

    def apply_threshold(self):
        try:
            self.threshold_top = float(self.threshold_top_var.get())
            self.threshold_bottom = float(self.threshold_bottom_var.get())
            if 0 <= self.threshold_top < self.threshold_bottom <= 1:
                self.status_var.set(f"阈值已更新: 上 {self.threshold_top}, 下 {self.threshold_bottom}")
            else:
                raise ValueError("阈值必须在0到1之间，且上阈值必须小于下阈值")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set("阈值更新失败")

    def select_window(self):
        selector = WindowSelector()
        self.hwnd = selector.select_window()
        if self.hwnd:
            title = win32gui.GetWindowText(self.hwnd)
            messagebox.showinfo("窗口选择", f"选择的窗口: {title}")
            self.status_var.set(f"已选择窗口: {title}")
        else:
            messagebox.showwarning("窗口选择", "未选择窗口")
            self.status_var.set("未选择窗口")

    def toggle_translation(self):
        if not self.hwnd:
            messagebox.showwarning("警告", "请先选择游戏窗口")
            return

        if self.is_translating:
            self.is_translating = False
            self.start_stop_button.config(text="开始翻译", style="success.TButton")
            self.status_var.set("翻译已停止")
        else:
            self.is_translating = True
            self.start_stop_button.config(text="停止翻译", style="danger.TButton")
            self.status_var.set("正在翻译...")
            self.translate_loop()

    def translate_loop(self):
        if not self.is_translating:
            self.start_stop_button.config(text="开始翻译", state=tk.NORMAL)
            return

        try:
            def process_ocr_result(ocr_result, window_height):
                threshold_top = int(window_height * self.threshold_top)
                threshold_bottom = int(window_height * self.threshold_bottom)
                filtered_text = [block for block in ocr_result if threshold_bottom > block['top'] > threshold_top]
                sorted_text = sorted(filtered_text, key=lambda block: (block['top'], block['left']))
                processed_text = ''.join([block['text'] for block in sorted_text])
                return processed_text
            
            def get_romaji(text_jp) -> str:
                text = text_jp
                kks = pykakasi.kakasi()
                result = kks.convert(text)
                sentence = ""
                for item in result:
                    word = item['orig'] + " (%s) " % item['hira'] if not item['orig'] == item['hira'] else item['orig']
                    sentence += word
                return sentence
                    
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            window_height = bottom - top
            print(f"window_height: {window_height}")

            screenshot_path = os.path.join(os.getcwd(), "screenshot.png")
            pyautogui.screenshot(screenshot_path, region=(left, top, right-left, bottom-top))
            
            ocr_result = wcocr.ocr(screenshot_path)

            if ocr_result['errcode'] == 0:
                ocr_result_text = ''.join([block['text'] for block in ocr_result['ocr_response']])
                
                if self.last_ocr_result is None or difflib.SequenceMatcher(None, ocr_result_text, self.last_ocr_result).ratio() < 0.95:
                    self.last_ocr_result = ocr_result_text
                    
                    japanese_text = process_ocr_result(ocr_result['ocr_response'], window_height)
                    print(f"Detected Japanese text: {japanese_text}")
                    
                    romaji_text = get_romaji(japanese_text)
                    print(f"Romaji text: {romaji_text}")

                    chinese_text = GoogleTranslator(source="ja", target="zh-CN").translate(text=japanese_text)
                    print(f"Chinese text: {chinese_text}")

                    self.original_text.delete(1.0, tk.END)
                    self.original_text.insert(tk.END, japanese_text)
                    self.romaji_text.delete(1.0, tk.END)
                    self.romaji_text.insert(tk.END, romaji_text)
                    self.translated_text.delete(1.0, tk.END)
                    self.translated_text.insert(tk.END, chinese_text)
                else:
                    print("Same context")
            else:
                print("No text detected in image")
            
            os.remove(screenshot_path)
        except Exception as e:
            messagebox.showerror("错误", f"翻译过程中出现错误: {str(e)}")
            self.is_translating = False
            self.start_stop_button.config(text="开始翻译", state=tk.NORMAL)
        
        if self.is_translating:
            self.master.after(1000, self.translate_loop)

def main():
    root = tk.Tk()
    gui = TranslatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()