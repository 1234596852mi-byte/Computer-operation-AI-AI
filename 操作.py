# system_control_tools.py (现在包含调度逻辑、图像识别、文本识别和核心自动化功能)
# ----------------------------------------------------
# 这是一个用于与 Gemini Function Calling 配合使用的工具模块。
# 它定义了 Python 函数，这些函数可以被 Gemini (通过 JSON 指令) 调用，
# 以实现鼠标和键盘的自动化操作，并包含一个 JSON 调度函数。
# ----------------------------------------------------

import io
import pyautogui
import time
import json 
from pathlib import Path
# 导入 NumPy，OpenCV 的图像操作通常需要它
import numpy as np 
import pyautogui
import pyperclip
import pytesseract
import cv2
import numpy as np
from PIL import Image
import difflib

import requests
# ----------------------------------------------------
# 全局设置 (Global Configuration)
# ----------------------------------------------------
# !!! 禁用 PyAutoGUI 的安全机制 !!!
pyautogui.FAILSAFE = False

# ----------------------------------------------------
# 依赖检查 (Dependency Check)
# ----------------------------------------------------
# 检查 OpenCV (cv2) 是否可用。
OPENCV_AVAILABLE = False
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    pass 

# 检查 OCR 库 (pytesseract 和 PIL) 是否可用。
TESSERACT_AVAILABLE = False
try:
    from PIL import Image
    import pytesseract
    # 假设 Tesseract 引擎路径已经配置 (如果未配置，第一次调用时会抛出异常)
    
    # ----------------------------------------------------
    # *** 强制指定 Tesseract 路径 (解决识别失败的关键一步) ***
    # 请确保路径指向你的 tesseract.exe 文件
    TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    # ----------------------------------------------------

    TESSERACT_AVAILABLE = True
except ImportError:
    pass

# ----------------------------------------------------

# ----------------------------------------------------
# 配置 (Configuration)
# ----------------------------------------------------
# !!! 用户需将此路径修改为存放自动化操作所需图片文件的实际目录 !!!
IMAGE_BASE_DIR = Path(r'C:\Users\Administrator\Desktop\ai-img') 

# ----------------------------------------------------
# 鼠标操作 (Mouse Operations)
# ----------------------------------------------------

def mouse_click(x: int = None, y: int = None, button: str = "left"):
    """
    将鼠标移动到指定的屏幕坐标并执行单次点击。
    如果 x 和 y 未提供 (即为 None)，则在鼠标的当前位置点击。
    Args:
        x (int | None): 屏幕的水平坐标（0 为最左侧）。
        y (int | None): 屏幕的垂直坐标（0 为最顶端）。
        button (str): 要点击的鼠标按键 ('left' 左键, 'right' 右键, 或 'middle' 中键)。
    """
    try:
        if x is None or y is None:
            # 获取当前鼠标位置，并在那里点击
            current_x, current_y = pyautogui.position()
            pyautogui.click(x=current_x, y=current_y, button=button)
            return f"已在当前坐标 ({current_x}, {current_y}) 处点击了 {button} 键 (因为未提供 x, y 坐标)。"
        else:
            pyautogui.click(x=x, y=y, button=button)
            return f"已在坐标 ({x}, {y}) 处点击了 {button} 键。"
    except Exception as e:
        return f"执行 mouse_click 失败: {e}"

def mouse_move(x: int, y: int, duration: float = 0.5):
    """
    将鼠标平滑移动到指定的屏幕坐标。
    Args:
        x (int): 目标水平坐标。
        y (int): 目标垂直坐标。
        duration (float): 移动过程持续的时间（秒）。
    """
    try:
        pyautogui.moveTo(x=x, y=y, duration=duration)
        return f"已将鼠标移动到 ({x}, {y})，耗时 {duration} 秒。"
    except Exception as e:
        return f"执行 mouse_move 失败: {e}"
    

def mouse_scroll(clicks: int):
    """
    控制鼠标滚轮滚动指定的“点击”量。
    正值向上/向前滚动，负值向下/向后滚动。
    Args:
        clicks (int): 滚动的量（正值向上，负值向下）。
                      通常 1 次点击相当于一行文本。
    """
    try:
        # 执行滚动操作。正值向上滚，负值向下滚。
        pyautogui.scroll(clicks)
        return f"已滚动鼠标滚轮 {clicks} 步。"
    except Exception as e:
        # 捕获并返回任何可能发生的异常
        return f"执行 mouse_scroll 失败: {e}"
    

def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0):
    """
    将鼠标从起始坐标拖动到结束坐标。
    Args:
        start_x (int): 拖动的起始水平坐标。
        start_y (int): 拖动的起始垂直坐标。
        end_x (int): 拖动的结束水平坐标。
        end_y (int): 拖动的结束垂直坐标。
        duration (float): 拖动过程持续的时间（秒）。
    """
    try:
        pyautogui.moveTo(start_x, start_y)
        pyautogui.dragTo(end_x, end_y, duration=duration)
        return f"已从 ({start_x}, {start_y}) 拖动到 ({end_x}, {end_y})，耗时 {duration} 秒。"
    except Exception as e:
        return f"执行 mouse_drag 失败: {e}"

def find_image_and_click(image_path: str, confidence: float = 0.8, button: str = "left"):
    """
    在屏幕上查找指定的图片文件，如果找到，则点击其中心位置。
    该函数使用预定义的 IMAGE_BASE_DIR 路径来查找图片。

    Args:
        image_path (str): 目标图片的文件名（如 'edge_icon.png'）。
                          文件将从 IMAGE_BASE_DIR 中加载。
        confidence (float): 匹配的精确度（0.0 到 1.0）。
                            注意：此参数需要安装 'opencv-python' 库。
        button (str): 要点击的鼠标按键 ('left' 左键, 'right' 右键, 或 'middle' 中键)。
    """
    # 1. 构造完整的图片路径
    full_image_path = IMAGE_BASE_DIR.joinpath(image_path)
    
    try:
        # 2. 检查文件是否存在
        if not full_image_path.exists():
            return f"失败：本地找不到图片文件 '{full_image_path}'。请检查 IMAGE_BASE_DIR 配置和文件名是否正确。"

        # 3. 尝试定位图片在屏幕上的位置
        if OPENCV_AVAILABLE:
            location = pyautogui.locateCenterOnScreen(
                str(full_image_path), 
                confidence=confidence,
                grayscale=False
            )
        else:
            location = pyautogui.locateCenterOnScreen(
                str(full_image_path), 
                grayscale=False
            )
        
        if location is None:
            confidence_msg = f" (信心度: {confidence})" if OPENCV_AVAILABLE else ""
            return f"失败：未在屏幕上找到图片 '{image_path}'{confidence_msg}"
        
        # 4. 如果找到，点击中心点
        pyautogui.click(x=location.x, y=location.y, button=button)
        return f"成功：已在屏幕上找到并点击图片 '{image_path}' 的中心位置 ({location.x}, {location.y})。"

    except Exception as e:
        error_detail = str(e) if str(e) else "未知系统或权限错误。"
        return f"执行 find_image_and_click 失败：{error_detail}。请确保图片文件格式正确且 PyAutoGUI 可访问屏幕。"

# ----------------------------------------------------
# 文本识别操作 (OCR Operations)
# ----------------------------------------------------

# ==========================================================
# !! 请根据你实际运行的服务地址进行配置 !!
OCR_API_URL = 'http://10.8.1.199:8089/api/tr-run/' 
# ==========================================================


def find_text_and_move(text_to_find: str, confidence: float = 0.5):
    """
    1. 截图整个屏幕。
    2. 将图片上传到 chineseocr_lite API 服务。
    3. 解析返回的 JSON 结果。
    4. 模糊匹配识别到的文字。
    5. 如果找到，将鼠标平滑移动到匹配文字的中心。

    Args:
        text_to_find (str): 要在屏幕上查找的文本。
        confidence (float): 匹配文字的最低置信度要求（0.0到1.0）。
    
    Returns:
        str: 执行结果或错误信息。
    """

    # --- 1. 截图整个屏幕 ---
    print("🚀 正在截图整个屏幕...")
    try:
        screenshot = pyautogui.screenshot()
    except Exception as e:
        return f"❌ 截图失败: {e}"

    # 将 PIL 图像对象转换为内存中的 PNG 格式数据
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    img_data = img_byte_arr.getvalue()
    
    # --- 2. 上传这个图片并获取结果 ---
    print(f"📡 正在上传图片至 OCR 服务: {OCR_API_URL}")
    try:
        # 使用 'file' 作为字段名，这是我们前面确认的 API 要求的字段
        files = {'file': ('screenshot.png', img_data, 'image/png')}
        response = requests.post(OCR_API_URL, files=files, timeout=2000)

    except requests.exceptions.ConnectionError:
        return f"❌ 连接失败！请确保 chineseocr_lite 服务正在运行在 {OCR_API_URL}。"
    except requests.exceptions.Timeout:
        return "❌ 请求超时。请检查网络或增加 timeout。"
    except Exception as e:
        return f"❌ 请求失败: {e}"

    # --- 3. 解析返回的 JSON ---
    if response.status_code != 200:
        return f"❌ API 请求失败，状态码: {response.status_code}，返回内容: {response.text}"
    
    try:
        json_data = response.json()
        if json_data.get('code') != 200:
            return f"❌ OCR 服务返回错误: {json_data.get('msg', '未知错误')}"
        
        text_data = json_data.get('data', {}).get('raw_out', [])
        if not text_data:
            return "❌ OCR 服务未识别到任何文本。"

    except Exception as e:
        return f"❌ JSON 解析失败: {e}，原始响应: {response.text}"

    # --- 4. 模糊匹配我所传的文字 ---
    normalized_target = text_to_find.strip().lower().replace(" ", "")
    print(f"🔎 开始匹配文本 '{text_to_find}' (标准化目标: '{normalized_target}')")

    for item in text_data:
        # item 结构通常是 [Box_Coords, Text, Confidence]
        box_coords = item[0]
        word = item[1].strip()
        current_confidence = item[2] 
        
        if not word:
            continue
            
        normalized_word = word.strip().lower().replace(" ", "")

        # 使用 SequenceMatcher 计算相似度
        similarity = difflib.SequenceMatcher(None, normalized_word, normalized_target).ratio()
        
        # 匹配逻辑：目标文本被包含，或相似度高，且置信度满足要求
        if (normalized_target in normalized_word or similarity >= 0.7) and current_confidence >= confidence:
            
            # --- 5. 将鼠标移到文字中心 ---
            # Box_Coords 是 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] 格式
            x_coords = [p[0] for p in box_coords]
            y_coords = [p[1] for p in box_coords]
             #[[833, 879], [959, 881], [958, 905], [832, 902]]
            # 计算边界框的左上角和右下角
            left = min(x_coords)
            top = min(y_coords)
            right = max(x_coords)
            bottom = max(y_coords)

            center_x = (left + right) // 2
            center_y = (top + bottom) // 2

            pyautogui.moveTo(center_x, center_y, duration=0.4)
            
            return (f"✅ 找到文本 '{text_to_find}' (OCR='{word}', 置信度={current_confidence:.2f}, 相似度={similarity:.2f}) "
                      f"→ 鼠标已平滑移动到 ({center_x}, {center_y})")

    return f"❌ 未找到文本 '{text_to_find}'，可能 OCR 不准或置信度 ({confidence:.2f}) 太高。"

def paste_text(text: str, wait_time: float = 0.1):
    """
    通过系统剪贴板实现文本的稳定输入，特别适用于中文等非 ASCII 字符。

    原理：将文本复制到剪贴板，然后模拟 Ctrl+V (粘贴) 操作。
    
    Args:
        text (str): 要输入的文本内容（支持中文）。
        wait_time (float): 粘贴操作前等待时间（秒），确保剪贴板操作完成。
    """
    try:
        # 1. 将中文内容写入系统剪贴板
        pyperclip.copy(text)
        
        # 2. 短暂等待，确保内容已完全复制到剪贴板
        time.sleep(wait_time)
        
        # 3. 模拟按下 Ctrl + V (粘贴) 快捷键
        # 注意: 如果是 Mac 系统，请将 'ctrl' 改为 'command'
        pyautogui.hotkey('ctrl', 'v') 
        
        # 4. （可选）模拟按下 Enter 键
        # pyautogui.press('enter') 
        
        return f"已通过剪贴板成功输入文本: '{text[:30]}...' (共 {len(text)} 个字符)"
    
    except Exception as e:
        return f"执行 paste_text 失败，请检查是否安装了 pyautogui 和 pyperclip: {e}"

# ----------------------------------------------------
# 键盘操作 (Keyboard Operations)
# ----------------------------------------------------

def type_text(text: str, interval: float = 0.05):
    """
    模拟键盘输入一段文本。
    Args:
        text (str): 要输入的文本内容。
        interval (float): 每个字符之间的输入间隔（秒）。
    """
    try:
        pyautogui.typewrite(text, interval=interval)
        return f"已输入文本: '{text[:20]}...' (共 {len(text)} 个字符)"
    except Exception as e:
        return f"执行 type_text 失败: {e}"


def find_solution_explorer_project(project_name: str, confidence: float = 0.3, click: bool = True):
    """
    专门用于在 Visual Studio 的“解决方案资源管理器”中查找并（可选地）点击指定的项目名称。
    该函数会首先激活“解决方案资源管理器”窗口，然后进行 OCR 识别，
    并尝试将识别结果限定在屏幕右侧区域，以提高查找项目节点的准确性。

    Args:
        project_name (str): 要在解决方案资源管理器中查找的项目名称。
        confidence (float): 文本识别的最低置信度（0.0到1.0）。
        click (bool): 如果找到，是否点击项目名称的中心。默认为 True。
    Returns:
        str: 执行结果或错误信息。
    """
    # 1. 激活“解决方案资源管理器”
    # 使用 key_press 是为了利用已有的工具函数，并确保触发相关逻辑和延迟
    key_press(["ctrl", "alt", "l"])
    wait_ms(500) # 等待窗口激活，多给一些时间确保UI更新

    # 2. 截图整个屏幕
    try:
        screenshot = pyautogui.screenshot()
    except Exception as e:
        return f"❌ 截图失败: {e}"

    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    img_data = img_byte_arr.getvalue()

    # 3. 上传图片进行 OCR 识别
    try:
        files = {'file': ('screenshot.png', img_data, 'image/png')}
        response = requests.post(OCR_API_URL, files=files, timeout=2000)
    except requests.exceptions.ConnectionError:
        return f"❌ 连接失败！请确保 chineseocr_lite 服务正在运行在 {OCR_API_URL}。"
    except requests.exceptions.Timeout:
        return "❌ 请求超时。请检查网络或增加 timeout。"
    except Exception as e:
        return f"❌ OCR 请求失败: {e}"

    if response.status_code != 200:
        return f"❌ API 请求失败，状态码: {response.status_code}，返回内容: {response.text}"
    
    try:
        json_data = response.json()
        if json_data.get('code') != 200:
            return f"❌ OCR 服务返回错误: {json_data.get('msg', '未知错误')}"
        text_data = json_data.get('data', {}).get('raw_out', [])
        if not text_data:
            return "❌ OCR 服务未识别到任何文本。"
    except Exception as e:
        return f"❌ JSON 解析失败: {e}，原始响应: {response.text}"

    # 获取屏幕宽度，用于判断右侧区域
    screen_width, screen_height = pyautogui.size()
    # 假设解决方案资源管理器在屏幕右侧大约 1/4 宽度区域。
    # 根据提供的图片（Solution Explorer在右侧，约占1/4到1/3的宽度），
    # 我们可以设定一个合理的左边界。
    solution_explorer_left_bound = screen_width * 0.7 

    normalized_target = project_name.strip().lower().replace(" ", "")

    best_match = None
    best_similarity = 0.0
    best_ocr_confidence = 0.0

    for item in text_data:
        box_coords = item[0]
        word = item[1].strip()
        current_ocr_confidence = item[2] 
        
        if not word:
            continue
            
        normalized_word = word.strip().lower().replace(" ", "")
         # *** 新增过滤条件：跳过包含“解决方案”的文本 ***
        if "解决方案" in word:
            print(f"Skipping solution title: '{word}'") # 调试信息
            continue
        similarity = difflib.SequenceMatcher(None, normalized_word, normalized_target).ratio()
        
        # 计算边界框
        x_coords = [p[0] for p in box_coords]
        y_coords = [p[1] for p in box_coords]
        left = min(x_coords)
        top = min(y_coords)
        right = max(x_coords)
        bottom = max(y_coords)
        
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2

        # 过滤条件：
        # 1. 文本相似度 (必须达到一定阈值，或目标文本被包含)
        # 2. OCR 置信度 (必须达到指定阈值)
        # 3. 中心点在屏幕右侧区域 (Solution Explorer 的大致位置)
        if ((normalized_target in normalized_word or similarity >= 0.7) and
            current_ocr_confidence >= confidence and
            center_x > solution_explorer_left_bound): # 关键的区域过滤条件

            # 优先选择相似度最高的，如果相似度相同则选择OCR置信度更高的
            if similarity > best_similarity or \
               (similarity == best_similarity and current_ocr_confidence > best_ocr_confidence):
                best_similarity = similarity
                best_ocr_confidence = current_ocr_confidence
                best_match = (center_x, center_y, word, current_ocr_confidence, similarity)

    if best_match:
        center_x, center_y, word, current_ocr_confidence, similarity = best_match
        if click:
            pyautogui.moveTo(center_x, center_y, duration=0.2)
            pyautogui.click()
            return (f"✅ 找到并点击解决方案资源管理器中的项目 '{project_name}' (OCR='{word}', "
                    f"置信度={current_ocr_confidence:.2f}, 相似度={similarity:.2f}) → 坐标 ({center_x}, {center_y})")
        else:
            return (f"✅ 找到解决方案资源管理器中的项目 '{project_name}' (OCR='{word}', "
                    f"置信度={current_ocr_confidence:.2f}, 相似度={similarity:.2f}) → 位于 ({center_x}, {center_y})")
    else:
        return (f"❌ 未在屏幕右侧的解决方案资源管理器区域找到项目 '{project_name}'，"
                f"可能 OCR 不准或置信度 ({confidence:.2f}) 太高，或项目不在可见区域。")

def key_press(keys: list[str]):
    """
    执行单个按键的按下或组合键（热键）操作，例如 Ctrl+C 或 Enter 键。
    Args:
        keys (list[str]): 一个包含要按下的一个或多个按键名称的列表。
                          示例：['ctrl', 'c'] (执行复制) 或 ['enter'] (执行回车)。
    """
    try:
        key_str = ', '.join(keys)
        if len(keys) == 1:
            pyautogui.press(keys[0])
        elif len(keys) > 1:
            # *keys 用于解包列表作为单独的参数传入 hotkey
            pyautogui.hotkey(*keys)
        else:
            return "错误：未提供任何按键指令。"
            
        return f"已按下键/组合键: {key_str}"
    except Exception as e:
        return f"执行 key_press 失败: {e}"

# ----------------------------------------------------
# 输入法控制 (IME Control)
# ----------------------------------------------------

def switch_ime_to_english():
    """
    尝试切换系统的输入法到英文/默认模式。
    """
    try:
        pyautogui.hotkey('ctrl', 'space')
        time.sleep(0.1)
        return "尝试切换输入法到英文模式 (执行热键: Ctrl + Space)。如果未成功，请检查系统输入法设置。"
    except Exception as e:
        return f"执行 switch_ime_to_english 失败: {e}"


# ----------------------------------------------------
# 时间控制 (Time Control)
# ----------------------------------------------------

def wait_ms(ms: int):
    """
    暂停程序的执行指定的毫秒数 (ms)。
    Args:
        ms (int): 要等待的毫秒数。
    """
    try:
        # 将毫秒转换为秒 (ms / 1000.0)
        duration_s = ms / 1000.0
        time.sleep(duration_s)
        return f"已暂停执行 {ms} 毫秒 ({duration_s} 秒)。"
    except Exception as e:
        return f"执行 wait_ms 失败: {e}"


# 将所有工具函数放在一个字典中，方便通过函数名查找
AVAILABLE_TOOLS_MAP = {
    'mouse_click': mouse_click,
    'mouse_move': mouse_move,
    'mouse_drag': mouse_drag,
    'find_image_and_click': find_image_and_click, 
    'find_text_and_move': find_text_and_move, # 新增文本识别工具
    'type_text': type_text,
    'key_press': key_press,
    'switch_ime_to_english': switch_ime_to_english, 
    'wait_ms': wait_ms ,
    'find_solution_explorer_project':find_solution_explorer_project,
    'mouse_scroll':mouse_scroll,#鼠标滚轮操作
    'paste_text':paste_text # <-- **已确认包含**
   
}

# ----------------------------------------------------
# 核心调度函数 (Gemini Chat App 中调用的函数)
# ----------------------------------------------------

def process_content(json_string: str) -> str:
    """
    解析 Gemini 发送的 JSON 指令，并执行相应的自动化操作。
    Args:
        json_string (str): 包含函数名和参数的 JSON 字符串。
    Returns:
        str: 操作的执行结果或错误信息。
    """
    try:
        # 1. 解析 JSON 字符串
        data = json.loads(json_string)
        
        # 2. 假设指令格式是 { "function": "func_name", "args": { ... } }
        function_name = data.get('function')
        args = data.get('args', {})
        
        if function_name not in AVAILABLE_TOOLS_MAP:
            return f"错误：找不到名为 '{function_name}' 的工具函数。"
            
        # 3. 查找并调用相应的函数，使用 **args 解包字典参数
        tool_function = AVAILABLE_TOOLS_MAP[function_name]
        
        # 调用函数并获取结果
        result = tool_function(**args)
        
        return result
        
    except json.JSONDecodeError:
        return "错误：接收到的内容不是有效的 JSON 格式。"
    except TypeError as e:
        # 打印详细错误，帮助用户调试参数缺失等问题 (如你遇到的 mouse_click 错误)
        return f"错误：函数参数类型或数量不匹配。详细: {e}"
    except Exception as e:
        return f"执行指令时发生未知错误: {e}"
