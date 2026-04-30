import re


def main():
    input_filename = '无机化学习题集_无图片版.md'
    q_output_filename = '无机化学习题集_无图片版_question.md'
    a_output_filename = '无机化学习题集_无图片版_answer.md'

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            content = f.read()

        # 核心逻辑：先找出所有题目的起始位置
        # 使用 MULTILINE 模式定位所有行首的 X-Y 题号
        header_pattern = re.compile(r'^(\d+-\d+)', re.MULTILINE)
        headers = list(header_pattern.finditer(content))

        questions = []
        answers = []

        for i in range(len(headers)):
            # 当前题号及其在全文中的起始位置
            q_num = headers[i].group(1)
            start_pos = headers[i].start()

            # 确定当前题目的结束边界（即下一题的开始或文件末尾）
            end_pos = headers[i + 1].start() if i + 1 < len(headers) else len(content)

            # 截取本题完整块（题干 + 解：...）
            block = content[start_pos:end_pos]

            # 根据“解：”进行分割
            # split_parts[0] 是题号+题干，split_parts[1] 是“解：”之后的部分
            split_parts = re.split(r'\n解：', block, maxsplit=1)

            # 1. 提取题干部分
            q_text = split_parts[0].strip()
            questions.append(q_text)

            # 2. 提取解答部分
            if len(split_parts) > 1:
                # 重新加上题号，方便对应
                a_text = f"{q_num}\n解：{split_parts[1].strip()}"
                answers.append(a_text)
            else:
                # 以防万一某题没有“解：”部分
                answers.append(f"{q_num}\n（暂无解答）")

        # 保存题干文件
        with open(q_output_filename, 'w', encoding='utf-8') as f_q:
            f_q.write('\n\n'.join(questions))

        # 保存解答文件
        with open(a_output_filename, 'w', encoding='utf-8') as f_a:
            f_a.write('\n\n'.join(answers))

        print(f"处理完成！")
        print(f"共检测到题目数量: {len(questions)}")
        print(f"题干已保存至: {q_output_filename}")
        print(f"解答已保存至: {a_output_filename}")

    except FileNotFoundError:
        print(f"找不到文件: {input_filename}")
    except Exception as e:
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()