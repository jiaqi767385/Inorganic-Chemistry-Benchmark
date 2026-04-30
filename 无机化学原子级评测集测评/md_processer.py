import os
import re
import json


def chucking(file_path):
    if not os.path.exists(file_path):
        print(f"错误：找不到文件 {file_path}")
        return

    print(f"\n>>> 正在处理文件: {os.path.basename(file_path)}")
    with open(file_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # 1. 预清洗：删除孤立页码行
    full_text = re.sub(r'^\s*\d+\s*$', '', full_text, flags=re.MULTILINE)

    # 2. 提取目录关键词
    toc_match = re.search(r'#\s*总目录(.*?)(?=\n#\s+)', full_text, re.DOTALL)
    if not toc_match:
        toc_match = re.search(r'#\s*目录(.*?)(?=\n#\s+)', full_text, re.DOTALL)

    if not toc_match:
        print(f"跳过关键词提取：{file_path} 中未找到 '# 总目录' 标记。")
        return

    raw_keywords = re.findall(r'(绪论|第[一二三四五六七八九十\d]+[章节].*?|附录|索引|元素周期表)', toc_match.group(1))
    keywords = list(dict.fromkeys([k.strip() for k in raw_keywords if k.strip()]))

    # 3. 物理定位每个章节的起始位置
    positions = []
    for k in keywords:
        pattern = r'^#\s+' + re.escape(k)
        match = re.search(pattern, full_text, re.MULTILINE)
        if match:
            positions.append({'title': k, 'start': match.start()})

    positions.sort(key=lambda x: x['start'])

    base_dir = os.path.dirname(os.path.abspath(file_path))
    qa_output_path = os.path.join(base_dir, "inorganic_qa_final.jsonl")

    current_file_qa_count = 0

    for i in range(len(positions)):
        current = positions[i]
        start_pos = current['start']
        end_pos = positions[i + 1]['start'] if i + 1 < len(positions) else len(full_text)

        # 获取切片
        chunk = full_text[start_pos:end_pos].strip()
        lines = chunk.split('\n')

        clean_lines = []
        for idx, line in enumerate(lines):
            strip_line = line.strip()

            # --- 强力截断逻辑 ---
            # A. 碰到下一章的一级标题（且不是块的第一行），立即停止
            if idx > 0 and strip_line.startswith("# "):
                title_content = strip_line.replace("# ", "").strip()
                if any(k in title_content for k in keywords if k != current['title']) or "目录" in title_content:
                    break

            # B. 彻底过滤掉装饰横线（如 __________）和目录点号线
            if re.match(r'^[_\-\s\.·]{3,}$', strip_line) or re.search(r'\.{5,}|····', strip_line):
                continue

            clean_lines.append(line)

        # 清除末尾可能残留的空行
        while clean_lines and not clean_lines[-1].strip():
            clean_lines.pop()

        final_text = "\n".join(clean_lines).strip()
        safe_filename = re.sub(r'[\\/:*?"<>|#]', '', current['title']).strip()

        # 4. 文件保存逻辑：针对 附录、索引 使用 append 模式
        # 只要文件名包含这些关键词，就执行追加写入
        is_append_file = any(kw in safe_filename for kw in ["附录", "索引"])
        save_path = os.path.join(base_dir, f"{safe_filename}.md")

        if is_append_file:
            # 使用 'a' 模式追加
            with open(save_path, 'a', encoding='utf-8') as f:
                f.write("\n\n" + final_text)
            print(f"  [APPEND] 已追加至: {safe_filename}.md")
        else:
            # 常规章节使用 'w' 模式覆盖（或创建）
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
            print(f"  [SAVE] 已生成: {safe_filename}.md")

        # 5. QA 提取 (始终使用 append 模式汇总)
        ex_match = re.search(r'\n#+\s*(?:思考题与)?习题\s*\n(.*)', final_text, re.DOTALL | re.IGNORECASE)
        if ex_match:
            ex_text = ex_match.group(1)
            # 切分题号（如 1-1, 11-1 等）
            questions = re.split(r'\n(?=\d+[\-－\.．]\d+|\d+[\.．]\s)', ex_text)

            with open(qa_output_path, 'a', encoding='utf-8') as f_qa:
                for q in questions:
                    q_text = q.strip()
                    if len(q_text) > 10:
                        qa_item = {
                            "instruction": f"请解答关于《无机化学》{safe_filename}的习题。",
                            "input": q_text,
                            "output": "待补充"
                        }
                        f_qa.write(json.dumps(qa_item, ensure_ascii=False) + "\n")
                        current_file_qa_count += 1

    print(f"--- 文件 {os.path.basename(file_path)} 处理完毕，新增 QA 对: {current_file_qa_count} ---")


if __name__ == "__main__":
    # 依次处理上册和下册的两个部分
    # 所有 QA 将汇总到同一个 inorganic_qa_final.jsonl
    # 附录和索引也将自动合并

    path1 = "/tmp/pycharm_project_527/无机化学原子级评测集构建/无机化学上册.md"
    chucking(path1)

    path2 = "/tmp/pycharm_project_527/无机化学原子级评测集构建/无机化学下册_1_346.md"
    chucking(path2)

    path3 = "/tmp/pycharm_project_527/无机化学原子级评测集构建/无机化学下册_347_496.md"
    chucking(path3)

    print("\n[FINISH] 全书三部分内容已全部处理完成！")