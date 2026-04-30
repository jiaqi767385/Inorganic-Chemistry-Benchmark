import re
import os
import requests
from google import genai
from google.genai import types

# --- 配置部分 ---
GEMINI_API_KEY = "你的_API_KEY"
SOURCE_FILE = "第1章.md"

# 初始化最新的 Gemini 客户端
client = genai.Client(api_key=GEMINI_API_KEY)


def get_gemini_description(image_url):
    """使用最新 SDK 识别网络图片"""
    try:
        # 下载图片
        response = requests.get(image_url, timeout=20)
        response.raise_for_status()

        # 调用 Gemini 2.0 / 1.5 系列模型
        # 注意：这里模型名称建议使用 gemini-1.5-flash 或 gemini-2.0-flash
        res = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                "请用简练的中文描述这张图片的内容，用于替换文档中的图片标签。",
                types.Part.from_bytes(data=response.content, mime_type="image/jpeg")
            ]
        )
        return res.text.strip()
    except Exception as e:
        return f"[描述生成失败: {str(e)}]"


def process_and_log(input_path):
    if not os.path.exists(input_path):
        print(f"找不到文件: {input_path}")
        return

    file_base, _ = os.path.splitext(input_path)
    log_file_path = f"{file_base}_image_replace.md"

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 增强版正则：兼容更多 Markdown 图片变体
    img_pattern = r'!\[(.*?)\]\((.*?)\)'
    matches = re.findall(img_pattern, content)

    if not matches:
        print("--- 诊断信息 ---")
        print(f"当前文件前 500 个字符内容如下：\n{content[:500]}")
        print("----------------")
        print("未检测到图片语法。请确保文件内容包含 ![alt](url) 格式。")
        return

    print(f"检测到 {len(matches)} 张图片，开始处理...")
    modified_content = content
    log_entries = [f"# 图片修改记录: {input_path}\n"]

    for i, (alt, path) in enumerate(matches, 1):
        # 移除路径两端的空格或换行（有时 MinerU 转换会带空格）
        clean_path = path.strip()
        print(f"[{i}/{len(matches)}] 正在识别: {clean_path[:50]}...")

        description = get_gemini_description(clean_path)

        # 替换原文件内容
        old_tag = f"![{alt}]({path})"  # 注意这里用原 path 匹配，避免 clean_path 匹配失败
        new_tag = f"**[图片描述 {i}：{description}]**"
        modified_content = modified_content.replace(old_tag, new_tag)

        # 记录日志
        log_entries.append(f"### 修改序号：{i}\n- **原链接**: {clean_path}\n- **描述**: {description}\n---\n")

    # 写入文件
    with open(input_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    with open(log_file_path, 'w', encoding='utf-8') as f:
        f.writelines(log_entries)

    print(f"\n成功！原始文件已更新，详情请看: {log_file_path}")


def main():
    process_and_log(SOURCE_FILE)


if __name__ == "__main__":
    main()