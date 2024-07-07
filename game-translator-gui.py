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

        # Set the theme to "clam" for a modern look
        style = ttk.Style()
        style.theme_use("clam")

        # Create a custom font
        self.custom_font = font.Font(family="FZLanTingHei", size=13)

        # Create a frame for the text boxes
        text_frame = ttk.Frame(master, padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # Create and place original text box
        self.original_label = ttk.Label(text_frame, text="原文:", font=self.custom_font)
        self.original_label.pack(anchor=tk.W)
        self.original_text = tk.Text(text_frame, height=8, width=50, font=self.custom_font, wrap=tk.WORD)
        self.original_text.pack(fill=tk.X, expand=True)

        # Create and place romaji text box
        self.romaji_label = ttk.Label(text_frame, text="罗马字注音:", font=self.custom_font)
        self.romaji_label.pack(anchor=tk.W, pady=(10, 0))
        self.romaji_text = tk.Text(text_frame, height=8, width=50, font=self.custom_font, wrap=tk.WORD)
        self.romaji_text.pack(fill=tk.X, expand=True)

        # Create and place translated text box
        self.translated_label = ttk.Label(text_frame, text="翻译:", font=self.custom_font)
        self.translated_label.pack(anchor=tk.W, pady=(10, 0))
        self.translated_text = tk.Text(text_frame, height=8, width=50, font=self.custom_font, wrap=tk.WORD)
        self.translated_text.pack(fill=tk.X, expand=True)


        # Create a frame for the buttons
        button_frame = ttk.Frame(master, padding=10)
        button_frame.pack(fill=tk.X)

        # Create select window button
        self.select_window_button = ttk.Button(button_frame, text="选择游戏窗口", command=self.select_window)
        self.select_window_button.pack(side=tk.LEFT, padx=(0, 10))

        # Create start/stop button
        self.start_stop_button = ttk.Button(button_frame, text="开始翻译", command=self.toggle_translation)
        self.start_stop_button.pack(side=tk.LEFT)

        self.is_translating = False
        self.hwnd = None
        self.last_screenshot_hash = None
        self.last_ocr_result = None
    def select_window(self):
        selector = WindowSelector()
        self.hwnd = selector.select_window()
        if self.hwnd:
            title = win32gui.GetWindowText(self.hwnd)
            messagebox.showinfo("窗口选择", f"选择的窗口: {title}")
        else:
            messagebox.showwarning("窗口选择", "未选择窗口")

    def toggle_translation(self):
        if not self.hwnd:
            messagebox.showwarning("警告", "请先选择游戏窗口")
            return

        if self.is_translating:
            self.is_translating = False
            self.start_stop_button.config(text="开始翻译")
        else:
            self.is_translating = True
            self.start_stop_button.config(text="停止翻译")
            self.translate_loop()
    
    def translate_loop(self):
        if not self.is_translating:
            self.start_stop_button.config(text="开始翻译", state=tk.NORMAL)
            return

        try:
            def process_ocr_result(ocr_result, window_height):
                threshold_top = window_height * 0.5
                threshold_bottom = window_height * 0.9
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
            #print(f"Raw ocr: {ocr_result}")

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