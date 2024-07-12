import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog
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
import configparser
import sqlite3

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

class DictionaryFeature:
    def __init__(self, master, notebook, db_path):
        self.master = master
        self.notebook = notebook
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.create_table()
        
        # create add word area in main tab
        self.create_main_dict_area()
        
        # create dictionary tab
        self.create_dict_tab()

    def create_main_dict_area(self):

        self.main_dict_frame = ttk.LabelFrame(self.master, text="快速添加词汇")
        self.main_dict_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(self.main_dict_frame, text="日语:").grid(row=0, column=0, padx=5, pady=2)
        self.jp_entry = ttk.Entry(self.main_dict_frame, width=20)
        self.jp_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(self.main_dict_frame, text="中文:").grid(row=0, column=2, padx=5, pady=2)
        self.cn_entry = ttk.Entry(self.main_dict_frame, width=20)
        self.cn_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(self.main_dict_frame, text="罗马音:").grid(row=0, column=4, padx=5, pady=2)
        self.romaji_entry = ttk.Entry(self.main_dict_frame, width=20)
        self.romaji_entry.grid(row=0, column=5, padx=5, pady=2)

        add_button = ttk.Button(self.main_dict_frame, text="添加", command=self.add_word)
        add_button.grid(row=0, column=6, padx=5, pady=2)

    def create_dict_tab(self):

        self.dict_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dict_tab, text="词典")

        self.word_list = ttk.Treeview(self.dict_tab, columns=('Japanese', 'Chinese', 'Romaji'), show='headings')
        self.word_list.heading('Japanese', text='日语')
        self.word_list.heading('Chinese', text='中文')
        self.word_list.heading('Romaji', text='罗马音')
        self.word_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        delete_button = ttk.Button(self.dict_tab, text="删除选中", command=self.delete_word)
        delete_button.pack(pady=10)

        self.load_words()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dictionary
        (id INTEGER PRIMARY KEY,
         japanese TEXT NOT NULL,
         chinese TEXT NOT NULL,
         romaji TEXT)
        ''')
        self.conn.commit()

    def add_word(self):
        japanese = self.jp_entry.get()
        chinese = self.cn_entry.get()
        romaji = self.romaji_entry.get()

        if japanese and chinese:
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO dictionary (japanese, chinese, romaji) VALUES (?, ?, ?)",
                           (japanese, chinese, romaji))
            self.conn.commit()

            self.word_list.insert('', 'end', values=(japanese, chinese, romaji))

            self.jp_entry.delete(0, tk.END)
            self.cn_entry.delete(0, tk.END)
            self.romaji_entry.delete(0, tk.END)

            self.master.status_var.set("词汇添加成功")

    def delete_word(self):
        selected_item = self.word_list.selection()[0]
        values = self.word_list.item(selected_item)['values']

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM dictionary WHERE japanese=? AND chinese=? AND romaji=?", values)
        self.conn.commit()

        self.word_list.delete(selected_item)
        self.master.status_var.set("词汇删除成功")

    def load_words(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT japanese, chinese, romaji FROM dictionary")
        for row in cursor.fetchall():
            self.word_list.insert('', 'end', values=row)

    def auto_fill(self, japanese_text):
        # autofill Chinese trans
        chinese_text = GoogleTranslator(source="ja", target="zh-CN").translate(text=japanese_text)
        self.cn_entry.delete(0, tk.END)
        self.cn_entry.insert(0, chinese_text)

        # autofill romaji
        kks = pykakasi.kakasi()
        result = kks.convert(japanese_text)
        romaji = ' '.join([item['hepburn'] for item in result])
        self.romaji_entry.delete(0, tk.END)
        self.romaji_entry.insert(0, romaji)

class TranslatorGUI:
    def __init__(self, master):
        self.master = master
        master.title("实时游戏翻译器")

        # Load configuration
        self.config = configparser.ConfigParser()
        self.config_file = 'translator_config.ini'
        self.load_config()
        
        # Initialize WeChat paths
        self.wechat_path = tk.StringVar(value=self.config.get('Paths', 'wechat_path', fallback=r"C:\Program Files (x86)\Tencent\WeChat\[3.9.11.17]"))
        self.wechatocr_path = tk.StringVar(value=self.config.get('Paths', 'wechatocr_path', fallback=os.getenv("APPDATA") + r"\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7079\extracted\WeChatOCR.exe"))

        # Initialize thresholds
        self.threshold_top = float(self.config.get('Thresholds', 'threshold_top', fallback='0'))
        self.threshold_bottom = float(self.config.get('Thresholds', 'threshold_bottom', fallback='1'))
        self.threshold_left = float(self.config.get('Thresholds', 'threshold_left', fallback='0'))
        self.threshold_right = float(self.config.get('Thresholds', 'threshold_right', fallback='1'))

        # Use ttkbootstrap for a modern look
        style = Style(theme="cosmo")

        # Set window size and make it resizable
        master.geometry("900x800")
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

        # About tab
        self.about_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.about_tab, text="关于")

        # Initialize dictionary feature
        self.db_path = self.config.get('Database', 'path', fallback='user_dictionary.db')
        self.dict_feature = DictionaryFeature(self.main_tab, self.notebook, self.db_path)

        # Load words into dictionary
        self.dict_feature.load_words()

        # Create main tab content
        self.create_main_tab()

        # Bind text selection to add word
        self.original_text.bind("<<Selection>>", self.on_text_select)
     

        # Create settings tab content
        self.create_settings_tab()

        # Create about tab content
        self.create_about_tab()

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


    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.config['Paths'] = {
                'wechat_path': r"C:\Program Files (x86)\Tencent\WeChat\[3.9.11.17]",
                'wechatocr_path': os.getenv("APPDATA") + r"\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\7079\extracted\WeChatOCR.exe"
            }
            self.config['Thresholds'] = {
                'threshold_top': '0',
                'threshold_bottom': '1',
                'threshold_left': '0',
                'threshold_right': '1'
            }
            self.config['Database'] = {
                'path': 'user_dictionary.db'
            }
            self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

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
        threshold_frame.pack(fill=tk.X, pady=(10, 0), padx=10)

        # Create a grid layout for more organized placement
        threshold_frame.columnconfigure(1, weight=1)
        threshold_frame.columnconfigure(3, weight=1)

        # Top threshold input
        ttk.Label(threshold_frame, text="上阈值 (0-1):").grid(row=0, column=0, padx=(5,20), pady=5, sticky=tk.W)
        self.threshold_top_var = tk.StringVar(value=str(self.threshold_top))
        self.threshold_top_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_top_var, width=10)
        self.threshold_top_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # Bottom threshold input
        ttk.Label(threshold_frame, text="下阈值 (0-1):").grid(row=1, column=0, padx=(5,20), pady=5, sticky=tk.W)
        self.threshold_bottom_var = tk.StringVar(value=str(self.threshold_bottom))
        self.threshold_bottom_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_bottom_var, width=10)
        self.threshold_bottom_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # Left threshold input
        ttk.Label(threshold_frame, text="左阈值 (0-1):").grid(row=0, column=2, padx=(20,5), pady=5, sticky=tk.W)
        self.threshold_left_var = tk.StringVar(value=str(self.threshold_left))
        self.threshold_left_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_left_var, width=10)
        self.threshold_left_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # Right threshold input
        ttk.Label(threshold_frame, text="右阈值 (0-1):").grid(row=1, column=2, padx=(20,5), pady=5, sticky=tk.W)
        self.threshold_right_var = tk.StringVar(value=str(self.threshold_right))
        self.threshold_right_entry = ttk.Entry(threshold_frame, textvariable=self.threshold_right_var, width=10)
        self.threshold_right_entry.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        # Apply threshold button
        self.apply_threshold_button = ttk.Button(threshold_frame, text="应用阈值", command=self.apply_threshold, style="info.TButton")
        self.apply_threshold_button.grid(row=2, column=0, columnspan=4, padx=5, pady=10, sticky=tk.W)

        # WeChat path settings frame
        wechat_frame = ttk.LabelFrame(self.settings_tab, text="WeChat 路径设置", padding=10)
        wechat_frame.pack(fill=tk.X, pady=(10, 0), padx=10)

        # WeChat path input
        ttk.Label(wechat_frame, text="WeChat 路径:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.wechat_path_entry = ttk.Entry(wechat_frame, textvariable=self.wechat_path, width=50)
        self.wechat_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(wechat_frame, text="浏览", command=lambda: self.browse_path(self.wechat_path)).grid(row=0, column=2, padx=5, pady=5)

        # WeChatOCR path input
        ttk.Label(wechat_frame, text="WeChatOCR 路径:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.wechatocr_path_entry = ttk.Entry(wechat_frame, textvariable=self.wechatocr_path, width=50)
        self.wechatocr_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(wechat_frame, text="浏览", command=lambda: self.browse_path(self.wechatocr_path)).grid(row=1, column=2, padx=5, pady=5)

        # Apply WeChat paths button
        self.apply_wechat_paths_button = ttk.Button(wechat_frame, text="应用 WeChat 路径", command=self.apply_wechat_paths, style="info.TButton")
        self.apply_wechat_paths_button.grid(row=2, column=0, columnspan=3, padx=5, pady=10, sticky=tk.W)

        # Configure the grid
        wechat_frame.columnconfigure(1, weight=1)

        # Database path settings
        db_frame = ttk.LabelFrame(self.settings_tab, text="数据库设置", padding=10)
        db_frame.pack(fill=tk.X, pady=(10, 0), padx=10)

        ttk.Label(db_frame, text="数据库路径:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.db_path_var = tk.StringVar(value=self.db_path)
        self.db_path_entry = ttk.Entry(db_frame, textvariable=self.db_path_var, width=50)
        self.db_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        ttk.Button(db_frame, text="浏览", command=self.choose_db_path).grid(row=0, column=2, padx=5, pady=5)

        # Apply database path button
        self.apply_db_path_button = ttk.Button(db_frame, text="应用数据库路径", command=self.apply_db_path, style="info.TButton")
        self.apply_db_path_button.grid(row=1, column=0, columnspan=3, padx=5, pady=10, sticky=tk.W)

        # Configure the grid
        db_frame.columnconfigure(1, weight=1)

    def create_about_tab(self):
        about_frame = ttk.Frame(self.about_tab, padding=20)
        about_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(about_frame, text="游戏实时翻译助手", font=self.title_font)
        title_label.pack(pady=(0, 10))

        # Author info
        author_label = ttk.Label(about_frame, text="by: YUKINOLOV", font=self.text_font)
        author_label.pack()

        # GitHub link
        link_label = ttk.Label(about_frame, text="GitHub: https://github.com/sl-shen/galgame-text-translator", 
                               font=self.text_font, foreground="blue", cursor="hand2")
        link_label.pack(pady=(5, 20))
        link_label.bind("<Button-1>", lambda e: self.open_link("https://github.com/sl-shen/galgame-text-translator"))

        # Version info (optional)
        version_label = ttk.Label(about_frame, text="版本: 1.0", font=self.text_font)
        version_label.pack()

    def open_link(self, url):
        import webbrowser
        webbrowser.open_new(url)

    def browse_path(self, path_var):
        path = filedialog.askdirectory() if "WeChat" in path_var.get() else filedialog.askopenfilename()
        if path:
            path_var.set(path)

    def apply_wechat_paths(self):
        try:
            wechat_path = self.wechat_path.get()
            wechatocr_path = self.wechatocr_path.get()
            
            if not os.path.exists(wechat_path):
                raise ValueError("WeChat 路径不存在")
            if not os.path.exists(wechatocr_path):
                raise ValueError("WeChatOCR 路径不存在")
            
            # Re-initialize WeChat OCR with new paths
            wcocr.init(wechatocr_path, wechat_path)
            
            # Save the new paths to config
            self.config['Paths']['wechat_path'] = wechat_path
            self.config['Paths']['wechatocr_path'] = wechatocr_path
            self.save_config()
            
            self.status_var.set("WeChat 路径已更新并保存")
            messagebox.showinfo("成功", "WeChat 路径已成功更新并保存")
        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set("WeChat 路径更新失败")

    def apply_threshold(self):
        try:
            self.threshold_top = float(self.threshold_top_var.get())
            self.threshold_bottom = float(self.threshold_bottom_var.get())
            self.threshold_left = float(self.threshold_left_var.get())
            self.threshold_right = float(self.threshold_right_var.get())
            if 0 <= self.threshold_top < self.threshold_bottom <= 1 and 0 <= self.threshold_left < self.threshold_right <= 1:
                # Save the new thresholds to config
                self.config['Thresholds']['threshold_top'] = str(self.threshold_top)
                self.config['Thresholds']['threshold_bottom'] = str(self.threshold_bottom)
                self.config['Thresholds']['threshold_left'] = str(self.threshold_left)
                self.config['Thresholds']['threshold_right'] = str(self.threshold_right)
                self.save_config()
                self.status_var.set(f"阈值已更新并保存: 上 {self.threshold_top}, 下 {self.threshold_bottom}, 左 {self.threshold_left}, 右 {self.threshold_right}")
                messagebox.showinfo("成功", "阈值已成功更新并保存")
            else:
                raise ValueError("阈值必须在0到1之间，且上阈值必须小于下阈值，左阈值必须小于右阈值")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set("阈值更新失败")

    def choose_db_path(self):
        db_path = filedialog.asksaveasfilename(defaultextension=".db",
                                               filetypes=[("SQLite Database", "*.db")])
        if db_path:
            self.db_path_var.set(db_path)

    def apply_db_path(self):
        new_db_path = self.db_path_var.get()
        if new_db_path != self.db_path:
            try:
                # Create a new connection to the new database
                new_conn = sqlite3.connect(new_db_path)
                
                # Create the table in the new database
                cursor = new_conn.cursor()
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS dictionary
                (id INTEGER PRIMARY KEY,
                 japanese TEXT NOT NULL,
                 chinese TEXT NOT NULL,
                 romaji TEXT)
                ''')
                new_conn.commit()

                # Copy data from old database to new database
                old_conn = self.dict_feature.conn
                old_cursor = old_conn.cursor()
                new_cursor = new_conn.cursor()

                old_cursor.execute("SELECT * FROM dictionary")
                rows = old_cursor.fetchall()

                new_cursor.executemany("INSERT INTO dictionary VALUES (?, ?, ?, ?)", rows)
                new_conn.commit()

                # Close old connection and update to new connection
                old_conn.close()
                self.dict_feature.conn = new_conn
                self.db_path = new_db_path

                # Update config
                self.config['Database']['path'] = new_db_path
                self.save_config()

                # Refresh dictionary display
                self.dict_feature.word_list.delete(*self.dict_feature.word_list.get_children())
                self.dict_feature.load_words()

                self.status_var.set("数据库路径已更新并保存")
                messagebox.showinfo("成功", "数据库路径已成功更新并保存")
            except Exception as e:
                messagebox.showerror("错误", f"更新数据库路径时出错: {str(e)}")
                self.status_var.set("数据库路径更新失败")
        else:
            self.status_var.set("数据库路径未变更")

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
            def process_ocr_result(ocr_result, window_height, window_length):
                threshold_top = int(window_height * self.threshold_top)
                threshold_bottom = int(window_height * self.threshold_bottom)
                threshold_left = int(window_length * self.threshold_left)
                threshold_right = int(window_length * self.threshold_right)

                filtered_text = [block for block in ocr_result 
                                if threshold_bottom > block['top'] > threshold_top
                                and threshold_right > block['left'] > threshold_left]
                
                print(f"filtered_ocr_result: {filtered_text}")
                
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
            window_length = right - left
            print(f"window_height: {window_height}")
            print(f"window_length: {window_length}")

            screenshot_path = os.path.join(os.getcwd(), "screenshot.png")
            pyautogui.screenshot(screenshot_path, region=(left, top, right-left, bottom-top))
            
            ocr_result = wcocr.ocr(screenshot_path)
            
            if ocr_result['errcode'] == 0:
                ocr_result_text = ''.join([block['text'] for block in ocr_result['ocr_response']])
                
                if self.last_ocr_result is None or difflib.SequenceMatcher(None, ocr_result_text, self.last_ocr_result).ratio() < 0.95:
                    self.last_ocr_result = ocr_result_text
                    
                    japanese_text = process_ocr_result(ocr_result['ocr_response'], window_height, window_length)
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

    def on_text_select(self, event):
        try:
            selected_text = self.original_text.selection_get()
            self.dict_feature.jp_entry.delete(0, tk.END)
            self.dict_feature.jp_entry.insert(0, selected_text)
            
            # autofill romaji and translation
            self.dict_feature.auto_fill(selected_text)
        except tk.TclError:
            pass  

def main():
    root = tk.Tk()
    gui = TranslatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()