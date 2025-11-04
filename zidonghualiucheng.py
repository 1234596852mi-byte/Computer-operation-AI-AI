from io import BytesIO
import tkinter as tk
from tkinter import messagebox
import threading
from google import genai
from google.genai.errors import APIError
from google.genai import types 
import os
import datetime
import re 
import json
from pathlib import Path
from PIL import Image, UnidentifiedImageError 
import mimetypes 
from PIL import ImageGrab 

# 导入操作模块 (假设操作模块在同一目录下)
import 操作 

# 假设你已经定义了工具函数
AVAILABLE_TOOLS = [] 

# ====================================================
# !!! 关键修改: 直接定义 API 密钥变量 !!!
# 请将 'YOUR_GEMINI_API_KEY_HERE' 替换为你的真实密钥
# ====================================================
MY_API_KEY = '' # 请替换为你的真实密钥

# ====================================================
# 日志文件夹路径常量 
# ----------------------------------------------------
# ❗ 重点检查：请确保这个路径有写入权限且路径格式正确 ❗
# ====================================================
LOG_DIR_PATH = r'E:\蒋\测试\AI日志'

# API 历史记录文件的路径，用于快速加载
API_HISTORY_FILE = os.path.join(LOG_DIR_PATH, 'api_history_context.json')

# ====================================================
# 新增: 图片文件夹路径常量和允许的图片扩展名
# ====================================================
IMAGE_DIR_PATH = Path(r'C:\Users\Administrator\Desktop\ai-img')
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']


class GeminiApp:
    def __init__(self, master):
        self.master = master
        master.title("Form1 - Gemini AI 聊天应用 (支持图片上传)")
        master.geometry("800x600")

        self.chat = None
        self.client = None
        self.model = 'gemini-2.5-flash'

          # 【新增】置顶状态变量
        self.is_always_on_top = False 
        
        # 1. 先创建 GUI 控件
        self.create_widgets()

        # 2. 显示初始欢迎信息和加载状态
        self.append_to_output("欢迎使用 Gemini 聊天应用！本应用**已启用日志持久化记忆和自动图片上传功能**。\n")
        self.append_to_output("--- 记忆加载中，请稍候... ---\n") 
        self.status_label.config(text="初始化中：正在加载历史记录...")

        # 3. 启动线程进行 API 初始化和历史加载
        thread = threading.Thread(target=self._thread_init_process)
        thread.start()

        # 启动时的第一条日志记录
        self._log_message("[System Control]: --- 应用启动 ---")

    def _thread_init_process(self):
        """在后台线程中进行耗时的历史记录加载和 API 初始化。"""
        previous_history = []
        raw_log_content = None 
        initial_response_text = None 
        error = None

        try:
            # 1. 尝试加载历史
            previous_history, raw_log_content = self._load_api_history()
            
            # 2. 初始化 API 客户端
            self.client = genai.Client(api_key=MY_API_KEY)
            
            # 3. 初始化 Chat 会话
            self.chat = self.client.chats.create(
                model=self.model, 
                history=previous_history,
                config=types.GenerateContentConfig(tools=AVAILABLE_TOOLS)
            )
            
            # 4. 如果 raw_log_content 不为 None (即使用了慢速 TXT 解析)，则发送原始日志内容
            if raw_log_content:
                initial_prompt = (
                    "我刚刚加载了以下历史聊天记录 (带时间戳和角色前缀的原始文本)。请忽略这些格式，并用一句话简短地总结一下我们的上次对话主题，以便我们继续聊天。这是为了确认您已成功加载。\n\n"
                    f"--- 历史日志内容 ---\n{raw_log_content}"
                )
                
                initial_response = self.chat.send_message(initial_prompt)
                initial_response_text = initial_response.text
                
        except Exception as e:
            self.client = None
            self.chat = None
            error = e

        # 5. 调度 GUI 更新在主线程中运行
        self.master.after(0, self._post_init_gui_update, previous_history, error, initial_response_text)

    def _post_init_gui_update(self, previous_history, error, initial_response_text=None):
        """在主线程中执行 GUI 更新和弹窗操作。"""
        
        if error:
            if MY_API_KEY == 'YOUR_GEMINI_API_KEY_HERE':
                msg = "错误：请将代码中的 'YOUR_GEMINI_API_KEY_HERE' 替换为你的真实 API 密钥！"
            else:
                msg = f"无法初始化 Gemini 客户端或聊天会话。请检查密钥是否有效。\n错误信息: {error}"
            
            messagebox.showerror("API 初始化失败", msg)
            self.status_label.config(text="错误: API 初始化失败")
            self.input_text.config(state='disabled')

        elif previous_history:
            history_message = f"--- 成功加载 {len(previous_history)} 条历史记录。聊天已恢复上下文。---"
            self.append_to_output(history_message + "\n")
            self._log_message(history_message)
            self.status_label.config(text="准备就绪 (已加载历史)")
            self.input_text.config(state='normal')
        else:
            self.status_label.config(text="准备就绪 (无历史记录)")
            self.input_text.config(state='normal')
            
        if initial_response_text:
            gemini_display_text = f"[Gemini 记忆摘要]: {initial_response_text}\n"
            self.append_to_output(gemini_display_text)
            self._log_message(gemini_display_text.strip())
            
        # 无论成功还是失败，都显示加载完成
        messagebox.showinfo("加载完成", "初始化及记忆加载完毕")


    def _load_api_history(self):
        """
        尝试从 JSON 文件加载 API 历史记录 (快速路径)，如果失败则回退到解析纯文本日志 (慢速路径)。
        Returns: tuple (history: list, raw_log_content: str or None)
        """
        history = []
        raw_log_content = None 

        # 1. 快速路径：尝试从结构化 JSON 文件加载历史
        try:
            if os.path.exists(API_HISTORY_FILE):
                with open(API_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    print("--- 成功：从 JSON 文件加载历史记录。 (快速) ---")
                    return history, raw_log_content 
        except Exception as e:
            print(f"警告：无法从 JSON 文件加载历史记录 ({API_HISTORY_FILE})。尝试解析纯文本日志。错误: {e}")
            
        # 2. 慢速路径：如果 JSON 失败，回退到解析最新的纯文本日志文件
        log_dir = LOG_DIR_PATH
        if not os.path.exists(log_dir):
            return history, raw_log_content 
        
        log_files = []
        for filename in os.listdir(log_dir):
            if re.match(r"\d{4}-\d{2}-\d{2}_聊天日志\.txt", filename):
                log_files.append(os.path.join(log_dir, filename))
                
        if not log_files:
            return history, raw_log_content 

        log_files.sort(key=os.path.getmtime, reverse=True) 
        latest_log_file = log_files[0]
        
        print(f"--- 警告：正在解析纯文本日志文件加载历史: {latest_log_file} (慢速) ---")

        try:
            with open(latest_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                raw_log_content = "".join(lines) 
            
            current_role = None
            current_text = ""
            
            # 3. 解析日志内容
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 匹配日志中的角色和文本内容
                match_user = re.match(r"\[\d{2}:\d{2}:\d{2}\]\s*\[You\]:\s*(.*)", line)
                match_gemini = re.match(r"\[\d{2}:\d{2}:\d{2}\]\s*\[Gemini\]:\s*(.*)", line)
                
                # 匹配系统控制消息 (需要跳过，因为这不是模型直接的回复)
                match_sys_control = re.match(r"\[\d{2}:\d{2}:\d{2}\]\s*\[System Control.*?\]:\s*(.*)", line)
                match_model_command = re.match(r"\[\d{2}:\d{2}:\d{2}\]\s*\[Model Command.*?\]:\s*(.*)", line)
                
                if (match_sys_control and not re.search(r"Image Status", line)) or match_model_command:
                    continue 

                # 找到新的用户消息或模型消息，并结束上一条消息
                if match_user or match_gemini:
                    if current_role and current_text:
                        if current_text.strip():
                            history.append({'role': current_role, 'parts': [{'text': current_text.strip()}]})
                    
                    if match_user:
                        current_role = 'user'
                        current_text = match_user.group(1).strip()
                    elif match_gemini:
                        current_role = 'model'
                        current_text = match_gemini.group(1).strip()
                    
                else:
                    # 否则，它可能是多行消息的后续部分
                    current_text += "\n" + line
                    
            # 4. 处理文件末尾的最后一条消息
            if current_role and current_text.strip():
                history.append({'role': current_role, 'parts': [{'text': current_text.strip()}]})


        except Exception as e:
            print(f"警告：解析纯文本历史记录失败。错误: {e}")
            return [], None 

        if history and history[0].get('role') == 'model' and '欢迎使用 Gemini 聊天应用' in history[0].get('parts')[0].get('text', ''):
            history.pop(0)

        return history, raw_log_content

    def _save_api_history(self):
        """
        将当前 Chat 会话的历史记录保存到 JSON 文件中，供下次快速加载。
        为避免文件过大和超出 API 上下文限制，我们仅保存最近的 20 条消息。
        """
        if not self.chat:
            return
        
        try:
            # 1. 获取完整的聊天历史
            full_history = self.chat.get_history()
            
            # 2. 截断历史记录：保留最近 20 条消息 (10 对对话)
            history_to_save = full_history[-20:] 

            # 过滤掉空的或格式不正确的历史消息
            filtered_history = [
                h.to_dict() for h in history_to_save 
                if h.role and h.parts and h.parts[0].text
            ]

            # 3. 确保日志目录存在
            if not os.path.exists(LOG_DIR_PATH):
                os.makedirs(LOG_DIR_PATH, exist_ok=True)
                
            # 4. 写入 JSON 文件
            with open(API_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(filtered_history, f, ensure_ascii=False, indent=2)
            
            print(f"--- 成功：将 {len(filtered_history)} 条历史记录保存到 JSON (用于快速加载)。 ---")
            
        except Exception as e:
            # 遇到权限或路径问题时，打印警告到控制台
            print(f"!!! 严重警告：保存 API 历史到 JSON 失败。错误: {e}")
            self._log_message(f"[System Error]: 保存 API 历史到 JSON 失败。错误: {type(e).__name__}: {e}")

    def _log_message(self, message):
        """将消息写入日志文件，并确保目录存在。每天使用一个新文件。"""
        log_dir = LOG_DIR_PATH
        
        if not os.path.exists(log_dir):
            try:
                # 尝试创建目录
                os.makedirs(log_dir)
            except OSError as e:
                # 目录创建失败时，直接返回并打印警告
                print(f"!!! 严重警告：无法创建日志目录 {log_dir}。日志记录失败。错误: {e}")
                return
        
        current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        log_filename = f"{current_date_str}_聊天日志.txt"
        log_file_path = os.path.join(LOG_DIR_PATH, log_filename)

        try:
            timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
            # 以追加模式写入
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(timestamp + message + "\n")
        except Exception as e:
            # 写入失败时，打印警告到控制台，这是日志写入失败最可能触发的地方。
            print(f"!!! 严重警告：写入日志文件失败。请检查文件路径和权限。错误: {e}")


    def _get_latest_image_part(self):
        """
        捕获当前屏幕截图，并返回其 genai.types.Part 对象。
        
        Returns: 
            tuple: (image_part: types.Part or None, status_message: str)
        """

        try:
            # 1. 核心步骤：捕获屏幕截图
            screenshot_image = ImageGrab.grab()

            if screenshot_image is None:
                return None, "错误：无法捕获屏幕截图（可能是权限问题或环境限制）。"

            # 2. 将 PIL Image 对象保存到内存中的字节流 (BytesIO)
            #    我们选择 PNG 格式，因为它无损且兼容性好。
            img_byte_arr = BytesIO()
            screenshot_image.save(img_byte_arr, format='PNG')
            file_bytes = img_byte_arr.getvalue()
            
            mime_type = 'image/png'  # 截图固定为 PNG 格式

            # 3. 核心步骤：使用 types.Part.from_bytes() 构造 Part 对象
            image_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            
            # 4. （可选）为 Part 对象添加描述信息
            #image_part.file_path = "屏幕截图" 

            # 返回 Part 对象和描述信息
            return image_part, f"已自动附加屏幕截图 ({len(file_bytes) / 1024:.2f} KB)"
                
        except Exception as e:
            # 记录完整的异常类型和消息
            error_type = type(e).__name__
            error_msg_full = f"捕获屏幕截图失败。错误类型: {error_type}, 详情: {e}"
            print(f"错误：{error_msg_full}")
            
            # 记录到日志
            # self._log_message(f"[System Error]: {error_msg_full}") # 取消注释以启用日志
            
            # 返回给用户的提示信息
            return None, f"捕获屏幕截图失败: {error_type}。请检查系统权限或 PIL 库。"
    
    def create_widgets(self):
        # ----------------------------------------------------
        # 1. 顶部历史记录/输出框架 (带滚动条)
        # ----------------------------------------------------
        top_frame = tk.Frame(self.master, padx=5)
        top_frame.pack(side="top", fill="both", expand=True, pady=(5, 2))

        v_scrollbar = tk.Scrollbar(top_frame)
        v_scrollbar.pack(side="right", fill="y")

        self.output_text = tk.Text(
            top_frame,
            font=("Consolas", 10),
            wrap="word",
            borderwidth=2,
            relief="sunken",
            yscrollcommand=v_scrollbar.set,
            state='disabled'
        )
        self.output_text.pack(side="left", fill="both", expand=True)
        v_scrollbar.config(command=self.output_text.yview)
        
        # ----------------------------------------------------
        # 2. 底部输入框架 (多行文本框作为输入区)
        # ----------------------------------------------------
        bottom_frame = tk.Frame(self.master, padx=5)
        bottom_frame.pack(side="bottom", fill="x", pady=(2, 5))

        self.input_text = tk.Text(
            bottom_frame,
            font=("Arial", 11),
            height=5,
            borderwidth=2,
            relief="sunken",
            # 默认禁用输入，直到初始化完成
            state='disabled' 
        )
        self.input_text.pack(side="left", fill="x", expand=True, padx=(0, 10))

        """

        send_button = tk.Button(
            bottom_frame,
            text="发送 (Ctrl+Enter)",
            command=self.start_api_call_thread,
            height=4
        )
        send_button.pack(side="right", fill="y")

        self.input_text.bind('<Control-Return>', self.start_api_call_thread)
        self.input_text.bind('<Key-Return>', lambda e: 'break')
        """
        # --- 新增：按钮组框架，用于容纳两个按钮 ---
        button_frame = tk.Frame(bottom_frame)
        button_frame.pack(side="right", fill="y")
        
        # 【新增】置顶按钮
        self.topmost_button = tk.Button(
            button_frame,
            text="置顶 (Off)", # 初始文本
            command=self.toggle_topmost,
            height=2 # 分配一半高度
        )
        self.topmost_button.pack(side="top", fill="x", pady=(0, 2))


        # 发送按钮 (现在放在新的 button_frame 中)
        send_button = tk.Button(
            button_frame, # 修改父组件为 button_frame
            text="发送 (Enter)",
            command=self.start_api_call_thread,
            height=2 # 分配一半高度
        )
        send_button.pack(side="bottom", fill="x")

        # ----------------------------------------------------
        # ❗ 关键修改点 2: 绑定新的快捷键 ❗
        # ----------------------------------------------------
        # 1. 绑定普通的回车键 (<Return>) 到发送函数
        self.input_text.bind('<Return>', self.start_api_call_thread) 
        
        # 2. 绑定 Shift+回车键 (<Shift-Return>) 作为插入换行符的方式
        #    返回 'insert' 告诉 Tkinter 执行默认的插入换行操作
        self.input_text.bind('<Shift-Return>', lambda e: 'insert')

        # ----------------------------------------------------
        # 3. 状态栏 
        # ----------------------------------------------------
        self.status_label = tk.Label(
            self.master, 
            text="正在初始化...", 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W, 
            font=("Arial", 9)
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)


    def append_to_output(self, text):
        """向输出文本框追加内容并滚动到底部"""
        self.output_text.config(state='normal')
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')

    def toggle_topmost(self):
        """切换主窗口的置顶状态。"""
        
        # 切换状态
        self.is_always_on_top = not self.is_always_on_top
        
        # 使用 Tkinter 的 attributes 方法设置窗口属性
        # True 表示置顶，False 表示取消置顶
        self.master.attributes('-topmost', self.is_always_on_top)
        
        # 更新按钮文本以反映当前状态
        if self.is_always_on_top:
            self.topmost_button.config(text="置顶 (On)")
            self.status_label.config(text="准备就绪 (窗口已置顶)")
            print("--- 系统控制: 窗口已置顶 ---")
        else:
            self.topmost_button.config(text="置顶 (Off)")
            self.status_label.config(text="准备就绪")
            print("--- 系统控制: 窗口已取消置顶 ---")

    def start_api_call_thread(self, event=None):
        """在新的线程中启动 API 调用，防止 GUI 假死"""
        user_prompt = self.input_text.get("1.0", tk.END).strip()
        
        if not user_prompt:
            # 如果是事件触发 (按键)，且内容为空，则直接返回 'break'，阻止换行
            if event:
                return 'break'
            return

        # 1. 记录并显示用户请求
        user_display_text = f"\n[You]: {user_prompt}\n"
        self.append_to_output(user_display_text)
        self._log_message(user_display_text.strip())

        # 2. 自动清除输入区
        self.input_text.delete("1.0", tk.END)

        if not self.client or not self.chat:
            self.append_to_output("--- Gemini 错误: API 客户端或聊天会话未初始化或密钥缺失。---\n")
            self._log_message("--- Gemini 错误: API 客户端或聊天会话未初始化或密钥缺失。---")
            return
        
        # 3. 禁用输入/发送，并显示状态提示
        self.master.config(cursor="wait")
        self.status_label.config(text="正在发送请求到 Gemini... 请稍候。") 
        self.input_text.config(state='disabled')
        
        # 4. 启动新线程进行 API 调用
        thread = threading.Thread(target=self.call_gemini_api, args=(user_prompt,))
        thread.start()
        if event:
            return 'break'

    def call_gemini_api(self, prompt):
        """实际进行 Gemini API 调用的函数 (在新线程中运行)"""
        try:
            
            # # 1. 尝试获取最新图片 Part
            # # image_status_msg: 包含文件名和大小的描述
            # image_part, image_status_msg = self._get_latest_image_part()

            # # 2. 构造内容列表
            # contents = []
            
            # # 3. 日志记录图片发送状态 
            # log_status_prefix = "[System Control: Image Status]: "
            # log_message = ""
            
            # if image_part:
            #     """
            #     # 记录完整的图片路径和信息
            #     full_path = str(image_part.file_path.resolve())
            #     log_message = f"{log_status_prefix}图片已发送 - 路径: {full_path} | 详情: {image_status_msg}"
                
            #     # 在主线程中显示图片附加状态信息给用户看
            #     self.master.after(0, self.append_to_output, f"--- [System]: 图片已自动附加: {image_part.file_path.name} ---\n")
                
            #     contents.append(image_part)
            #     """
            #        # --------------------------------------------------
            #     # 修复点 1：移除对 image_part.file_path 的访问。
            #     #           直接使用 image_status_msg 进行日志记录。
            #     # --------------------------------------------------
            #     log_message = f"{log_status_prefix}图片已发送 - 详情: {image_status_msg}"
                
            #     # 在主线程中显示图片附加状态信息给用户看
            #     # 修复点 2：将 .file_path.name 替换为通用的 "屏幕截图" 
            #     self.master.after(0, self.append_to_output, f"--- [System]: 图片已自动附加: 屏幕截图 ---\n")
                
            #     contents.append(image_part)
            # else:
            #     """
            #     # 如果未找到图片，记录 "图片未发送" 和原因 (image_status_msg)
            #     log_message = f"{log_status_prefix}图片未发送 (原因: {image_status_msg})"

            #     # ----------------------------------------------------
            #     # !!! 新增: 在文本框中显示图片未发送状态 !!!
            #     # ----------------------------------------------------
            #     user_friendly_msg = f"--- [System]: 图片未发送 (提示: {image_status_msg}) ---\n"
            #     self.master.after(0, self.append_to_output, user_friendly_msg)
            #     # ----------------------------------------------------
            #     """
            #      # 如果未找到图片，记录 "图片未发送" 和原因 (image_status_msg)
            #     log_message = f"{log_status_prefix}图片未发送 (原因: {image_status_msg})"

            #     # !!! 在文本框中显示图片未发送状态 !!!
            #     user_friendly_msg = f"--- [System]: 图片未发送 (提示: {image_status_msg}) ---\n"
            #     self.master.after(0, self.append_to_output, user_friendly_msg)

            # # 统一记录最终的图片发送状态
            # self._log_message(log_message) 
            # # -----------------------------------------------
            
            # # 4. 添加用户文本 prompt
            # contents.append(prompt)
              # ----------------------------------------------------
            # ❗ 关键修改点 1: 检查 prompt 是否以 "abc" 结尾 ❗
            # ----------------------------------------------------
            gemini_response = "" # 初始化变量以确保在 finally 或 except 块之后它有值

            # [原有的 should_include_screenshot 和 contents 构造逻辑...
            should_include_screenshot = prompt.lower().endswith("abc")
            image_part, image_status_msg = None, "未尝试捕获屏幕截图 (Prompt中不含'abc'后缀)"

            # 1. 尝试获取最新图片 Part
            # 初始化为 None 和默认消息

            if should_include_screenshot:
                # 只有当 should_include_screenshot 为 True 时才执行截图捕获
                self.master.after(0, self.append_to_output, "--- [System]: 检测到 'abc' 后缀，正在捕获屏幕截图... ---\n")
                
                # image_part: types.Part or None
                # image_status_msg: 描述信息或错误信息
                image_part, image_status_msg = self._get_latest_image_part()
            
            # ----------------------------------------------------
            # 2. 构造内容列表
            # ----------------------------------------------------
            contents = []
            
            # 3. 日志记录图片发送状态 
            log_status_prefix = "[System Control: Image Status]: "
            log_message = ""
            
            # ----------------------------------------------------
            # ❗ 关键修改点 2: 更新图片内容和状态的逻辑 ❗
            # ----------------------------------------------------
            if image_part:
                # 图片已成功捕获
                log_message = f"{log_status_prefix}图片已发送 - 详情: {image_status_msg}"
                
                # 在主线程中显示图片附加状态信息给用户看
                self.master.after(0, self.append_to_output, f"--- [System]: 图片已自动附加: 屏幕截图 ({image_status_msg.split('(')[-1].strip()}) ---\n")
                
                contents.append(image_part)
            else:
                # 图片未发送或未尝试发送
                if should_include_screenshot:
                    # 尝试了但失败了
                    log_message = f"{log_status_prefix}图片未发送 (原因: {image_status_msg})"
                    user_friendly_msg = f"--- [System]: 图片未发送 (提示: {image_status_msg}) ---\n"
                    self.master.after(0, self.append_to_output, user_friendly_msg)
                else:
                    # 根本没尝试
                    log_message = f"{log_status_prefix}{image_status_msg}"
                    # 此处不再额外向 output_text 追加，因为 status_msg 已经足够清晰
                    
            # 统一记录最终的图片发送状态
            self._log_message(log_message) 
            # -----------------------------------------------
            
            # 4. 移除 prompt 中的 "abc" 并添加用户文本
            if should_include_screenshot:
                # 如果发送了图片，移除 'abc'，并将剩余部分作为文本内容
                prompt_for_api = prompt[:-3].strip() 
            else:
                # 如果未发送图片，则使用完整 prompt
                prompt_for_api = prompt

            contents.append(prompt_for_api) # 文本内容总是最后一个
            
            # 如果 prompt_for_api 为空 (用户只输入了 'abc')，则添加一个默认提示
            if not prompt_for_api:
                contents.append("请分析这张截图。")

                contents.append(prompt_for_api or "请分析这张截图。") # 确保 contents 列表非空
                # 5. 调用 API
            response = self.chat.send_message(contents)
                
                # 无论是否有函数调用，我们都将完整的文本内容作为结果返回
            gemini_response = response.text
            
        except APIError as e:
            gemini_response = f"--- Gemini API 请求失败 ---\n错误: {e}"
        except Exception as e:
            gemini_response = f"--- 发生未知错误 ---\n错误: {e}"
            
        # 将结果返回到主线程进行 GUI 更新
        self.master.after(0, self.update_gui_with_response, gemini_response)
    


    

    def update_gui_with_response(self, response_text):
        """
        在主线程中更新 GUI 状态、输出内容，并保存 API 历史记录。
        """
        
        # ----------------------------------------------------
        # 1. 解析并执行所有 'aaaa' 包裹的内容 
        # ----------------------------------------------------
        matches = re.findall(r"aaaa(.*?)aaaa", response_text, re.DOTALL)
        execution_successful = True 
        if matches:
            for i, extracted_content in enumerate(matches):
                extracted_content = extracted_content.strip()
                
                # --- 1.1. 显示和记录模型生成的 JSON 指令 ---
                json_command_display = f"\n[Model Command (JSON Output) #{i+1}]: \n{extracted_content}\n"
                self.append_to_output(json_command_display)
                self._log_message(f"[Model Command #{i+1}]: {extracted_content}")
                
                # 1.2. **核心步骤：调用操作模块**
                try:
                    # 假设 process_content 成功时返回一个非错误字符串或None
                    result = 操作.process_content(extracted_content)
                    print(f"--- 成功执行指令 #{i+1}：操作结果: {result} ---") 

                   # ⭐⭐⭐ 检查操作结果是否包含“失败/错误”关键词 ⭐⭐⭐
                    if result and ("失败" in result or "错误" in result or "未找到" in result or "不准" in result):
                    # 1. 定义终止消息
                     termination_message = f"🚨 操作 #{i+1} 返回失败信息，终止后续操作。结果: {result}"
                        
                     # 2. 【关键】显示本次操作结果
                    self.append_to_output(f"\n[System Control #{i+1}]: {result}\n")
                        
                    # 3. 显示终止信息
                    print(termination_message)
                    self.append_to_output(f"\n[System Halt]: {termination_message}\n")

                    #弹出窗口
                    messagebox.showerror("警告：自动化流程报错！",f"🚨 操作 #{i+1} 返回失败信息，终止后续操作。结果: {result}")

                    execution_successful = False    
                    # 4. 跳出循环
                    break
                    
                except Exception as e:
                    # --- 错误处理和终止逻辑 (新增) ---
                    # 1. 构造错误信息
                    execution_successful = False
                    error_message = (
                        f"本地执行操作 #{i+1} 失败！\n"
                        f"JSON内容: {extracted_content[:100]}...\n"
                        f"错误: {type(e).__name__}: {e}"
                    )
                    """
                    result = f"本地执行操作失败: {e}"
                    print(f"--- 错误：{error_message} ---") 
                    
                    # 2. 弹窗提醒 (在主线程中)
                    messagebox.showerror("操作执行错误", error_message)
                    
                    # 3. 终止后续的 process_content 调用
                    # 使用 break 跳出 for 循环，但函数会继续执行后续的文本显示和状态重置。
                    break 
                    # -----------------------------------------------
"""
                # 1.3. 显示和记录操作结果
                op_display_text = f"\n[System Control #{i+1}]: {result}\n"
                self.append_to_output(op_display_text)
                self._log_message(f"[System Control #{i+1}]: {result}")
        

         # ----------------------------------------------------
        # 2. 【关键】当循环被中断时，这里可以执行特定的善后工作！
        # ----------------------------------------------------
        if not execution_successful:
            # 例如：如果流程中断，你可以发送一个日志或更改状态信息
            print("--- 自动化流程已被中断，执行中断后的特殊清理 ---")
            pass # 可以在这里添加只有在失败时才需要的代码
        
        # ----------------------------------------------------
        # 2. 显示 Gemini 的文本回复 (完整的回复内容)
        # ----------------------------------------------------
        if response_text:
            gemini_display_text = f"[Gemini]: {response_text}\n"
            
            # 统一显示逻辑
            self.append_to_output(gemini_display_text)
            self._log_message(gemini_display_text.strip())

        # 3. 保存 API 历史到 JSON (供下次快速加载)
        # 重点：如果日志路径或权限有问题，这里可能会失败，并打印严重警告。
        self._save_api_history()
        
        # 4. 重置 GUI 状态
        self.input_text.config(state='normal') 
        self.master.config(cursor="")
        self.status_label.config(text="准备就绪")
        
# --- 主程序入口 ---
if __name__ == "__main__":
    # 检查 API 密钥是否已替换
    if MY_API_KEY == 'YOUR_GEMINI_API_KEY_HERE':
        root = tk.Tk()
        root.withdraw() # 隐藏主窗口
        messagebox.showerror("配置错误", "请先将代码中的 'MY_API_KEY' 变量替换为你的真实 Gemini API 密钥！")
        root.destroy()
    else:
        # 检查必要的库是否安装
        try:
            import PIL.Image
        except ImportError:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("依赖缺失", "请运行 'pip install Pillow' 安装图片处理库。")
            root.destroy()
        else:
            root = tk.Tk()
            app = GeminiApp(root)
            root.mainloop()
