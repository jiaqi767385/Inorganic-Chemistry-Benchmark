import re


def reformat_question(input_text):
    lines = input_text.strip().split('\n')
    formatted_output = []
    global_index = 1

    current_main_title = ""
    # 匹配大题题干，如 "12-1 简释下列词语"
    main_pattern = re.compile(r'^\d+-\d+\s+(.*)')
    # 匹配带括号或序号的小题，如 "（1）" 或 "(1)"
    sub_pattern = re.compile(r'^[\(（]\d+[\)）]\s*(.*)')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检查是否是大题题干
        main_match = main_pattern.match(line)
        if main_match:
            current_main_title = main_match.group(1)
            continue

        # 检查是否是小题
        sub_match = sub_pattern.match(line)
        if sub_match:
            content = sub_match.group(1)
            # 按照要求格式化：12-N 题干 空格 题目内容
            new_line = f"10-{global_index} {current_main_title} {content}"
            formatted_output.append(new_line)
            global_index += 1

    # 修改点：使用 "\n\n" 进行连接，使题目之间产生空行
    return "\n\n".join(formatted_output)


def reformat_answer(input_text):
    """
    针对包含复杂 LaTeX 公式和 HTML 表格的化学答案进行原子级拆分。
    """
    # 1. 识别大题块：如 "12-1", "12-2"
    # 使用 split 拆分出大题编号和其对应的整块内容
    main_blocks = re.split(r'(\d+-\d+)\s*\n', input_text.strip())

    formatted_output = []
    global_index = 1

    # main_blocks 结构: ['', '12-1', '内容...', '12-2', '内容...']
    for i in range(1, len(main_blocks), 2):
        # main_id = main_blocks[i] # 原始大题号
        raw_content = main_blocks[i + 1].strip()

        # 清除大题开头的 "解：" 或 "解决："
        clean_content = re.sub(r'^(解|解决|解答)：?\s*', '', raw_content)

        # 2. 识别小题切分点
        # 逻辑：匹配行首的 (1) 或 （1），但要小心处理多行文本
        # 使用正则表达式在每个小题序号前插入特殊占位符，然后再切分
        # 这里的正则匹配：换行符 + (数字) 或 （数字）
        sub_split_pattern = r'\n\s*[\(（](\d+)[\)）]'

        # 检查开头是否就是第一个小题
        if not re.match(r'^[\(（]\d+[\)）]', clean_content):
            # 如果开头没有序号，可能整道大题就是一个整体，或者开头有描述性文字
            # 我们人为在开头加一个换行符以便正则统一处理
            proc_content = "\n" + clean_content
        else:
            proc_content = clean_content

        # 寻找所有小题的位置
        # 使用 finditer 找到所有 (n) 的位置，手动切分以保护中间的 table 和 formula
        indices = [m.start() for m in re.finditer(sub_split_pattern, proc_content)]

        sub_sections = []
        if not indices:
            # 如果没有找到任何小题序号，说明这道大题本身就是一个原子题目
            sub_sections.append(proc_content)
        else:
            # 按位置切分
            last_idx = 0
            for idx in indices:
                if proc_content[last_idx:idx].strip():
                    sub_sections.append(proc_content[last_idx:idx])
                last_idx = idx
            sub_sections.append(proc_content[last_idx:])

        # 3. 格式化输出
        for section in sub_sections:
            text = section.strip()
            if not text:
                continue

            # 移除段落开头的小题序号 (1) 或 （1）
            text = re.sub(r'^[\(（]\d+[\)）]\s*', '', text)
            # 同时也处理掉可能残留的换行后的小题序号（针对正则切分留下的痕迹）
            text = re.sub(r'^\s*[\(（]\d+[\)）]\s*', '', text)

            # 拼装结果：12-N + 内容
            new_entry = f"10-{global_index} {text}"
            formatted_output.append(new_entry)
            global_index += 1

    # 使用两个换行符连接，保证题目之间有空行
    return "\n\n".join(formatted_output)


def count_questions(file_path):
    # 定义匹配题目序号的正则表达式
    # 格式说明：行首开始，数字 + 横杠 + 数字，后面紧跟空格
    # 例如：1-14, 2-3, 23-45
    question_pattern = re.compile(r'^\d+-\d+(?=\s)')

    question_count = 0
    question_list = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 查找当前行是否匹配题目序号格式
                match = question_pattern.match(line)
                if match:
                    question_count += 1
                    question_list.append(match.group())

        # 打印统计结果
        print(f"--- 统计报告 ---")
        print(f"发现题目总数：{question_count} 道")
        if question_list:
            print(f"部分题目序号样例：{', '.join(question_list[:5])} ... {question_list[-1]}")

    except FileNotFoundError:
        print("错误：未找到指定文件。")
    except Exception as e:
        print(f"运行出错：{e}")

raw_data1 = r"""
10-1 正确写出下列电对在酸性介质中的电极反应式及各电极反应的能斯特方程。
(1) $\mathrm{H}^{+} / \mathrm{H}_{2}$ ; 
(2) $\mathrm{Fe}^{3+} / \mathrm{Fe}^{2+}$ ; 
(3) $\mathrm{Sn}^{2+} / \mathrm{Sn}$ ; 
(4) $\mathrm{CuBr} / \mathrm{Cu}$ ; 
(5) $\mathrm{GeO}_2 / \mathrm{Ge}$ ; 
(6) $\mathrm{Bi}_{2} \mathrm{O}_{4} / \mathrm{BiO}^{+}$ ; 
（7） $\mathrm{CO}_{2} / \mathrm{HCOOH}$ 
（8）HCOOH/HCHO； 
(9) $\left[\mathrm{PdBr}_4\right]^{2-} / \mathrm{Pd}$ ; 
(10) $\mathrm{AgC_2H_3O_2 / Ag}$ ; 
(11) $\mathrm{O}_2 / \mathrm{H}_2\mathrm{O}_2$ 
(12) $\mathrm{H}_2\mathrm{O}_2 / \mathrm{H}_2\mathrm{O}$ 。

10-2 正确写出下列电对在碱性介质中的电极反应式及各电极反应的能斯特方程。
(1) $\mathrm{Ba(OH)}_2 / \mathrm{Ba}$ ; (2) $\mathrm{BeO} / \mathrm{Be}$ ; (3) $\mathrm{HO}_2^- / \mathrm{OH}^-$ ; 
(4) $\mathrm{H}_2\mathrm{PO}_2^- / \mathrm{P}$ ; (5) $\mathrm{O}_2 / \mathrm{HO}_2^-$ ; (6) $\mathrm{MnCO}_3 / \mathrm{Mn}$ ; 
(7) $\mathrm{PO}_4^{3-}/\mathrm{HPO}_3^{2-}$ ; (8) $\mathrm{H}_2\mathrm{O}/\mathrm{H}_2$ ; (9) $\mathrm{O}_3/\mathrm{O}_2$ ; 
(10) $\mathrm{AgO / Ag_2O}$ ; (11) $\mathrm{MnO_4^{2 - } / MnO_2}$ ; (12) $\mathrm{Bi}_2\mathrm{O}_3 / \mathrm{Bi}$ 。

10-4 将下列氧化还原反应设计成为两个半电池反应，并利用本书附录中标准电极电势表的数据，求出 $298\mathrm{K}$ 时反应的平衡常数 $K^{\ominus}$ 。
（1） $2\mathrm{Fe}^{2 + } + \mathrm{Cl}_2 = 2\mathrm{Fe}^{3 + } + 2\mathrm{Cl}^-$ 
(2) $\mathrm{Zn + Hg_2Cl_2 = 2Hg + Zn^{2 + } + 2Cl^-}$ 
（3） $\mathrm{Cl}_2 + \mathrm{H}_2\mathrm{O} = \mathrm{HClO} + \mathrm{H}^+ +\mathrm{Cl}^-$ 
(4) $2\mathrm{H}_{2}\mathrm{O} = 2\mathrm{H}_{2} + \mathrm{O}_{2}$

10-5 将下列非氧化还原反应设计成为两个半电池反应，并利用本书附录中标准电极电势表的数据，求出 $298\mathrm{K}$ 时反应的平衡常数 $K^{\ominus}$ 。
(1) $\mathrm{H}_{2} \mathrm{O} = \mathrm{H}^{+} + \mathrm{OH}^{-}$ 
(2) $\mathrm{PbI}_2 = \mathrm{Pb}^{2+} + 2\mathrm{I}^-$ 
(3) $\mathrm{Pt}^{2+} + 4\mathrm{Cl}^{-} = [\mathrm{PtCl}_{4}]^{2-}$

"""

raw_data2 = r"""
10-1
（1） $\mathrm{H}^{+} / \mathrm{H}_{2}$ 
$$
2 \mathrm {H} ^ {+} + 2 \mathrm {e} ^ {-} = \mathrm {H} _ {2}
$$
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {[ c (\mathrm {H} ^ {+}) ] ^ {2}}{p (\mathrm {H} _ {2})}
$$
(2) $\mathrm{Fe}^{3+} / \mathrm{Fe}^{2+}$ 
$$
\mathrm {F e} ^ {3 +} + \mathrm {e} ^ {-} = \mathrm {F e} ^ {2 +}
$$
$$
E = E ^ {\ominus} + 0. 0 5 9 \mathrm {V} \lg \frac {c (\mathrm {F e} ^ {3 +})}{c (\mathrm {F e} ^ {2 +})}
$$
(3) $\mathrm{Sn}^{2+} / \mathrm{Sn}$ 
$$
\mathrm {S n} ^ {2 +} + 2 \mathrm {e} ^ {-} = \mathrm {S n}
$$
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg c (\mathrm {S n} ^ {2 +})
$$
(4) $\mathrm{CuBr} / \mathrm{Cu}$ 
$$
\mathrm {C u B r} + \mathrm {e} ^ {-} = \mathrm {C u} + \mathrm {B r} ^ {-}
$$
$$
E = E ^ {\ominus} + 0. 0 5 9 \mathrm {V} \lg \frac {1}{c (\mathrm {B r} ^ {-})}
$$
(5) $\mathrm{GeO}_2 / \mathrm{Ge}$ 
$$
\mathrm {G e O} _ {2} + 4 \mathrm {H} ^ {+} + 4 \mathrm {e} ^ {-} = \mathrm {G e} + 2 \mathrm {H} _ {2} \mathrm {O}
$$
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{4} \lg [ c (\mathrm {H} ^ {+}) ] ^ {4}
$$
(6) $\mathrm{Bi}_2\mathrm{O}_4 / \mathrm{BiO}^+$ 
$$
\mathrm {B i} _ {2} \mathrm {O} _ {4} + 4 \mathrm {H} ^ {+} + 2 \mathrm {e} ^ {-} = 2 \mathrm {B i O} ^ {+} + 2 \mathrm {H} _ {2} \mathrm {O}
$$
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {[ c (\mathrm {H} ^ {+}) ] ^ {4}}{[ c (\mathrm {B i O} ^ {+}) ] ^ {2}}
$$
① $c(\mathrm{H}^{+})$ 应为 $\frac{c(\mathrm{H}^{+})}{c^{\ominus}}, p(\mathrm{H}_{2})$ 应为 $\frac{p(\mathrm{H}_{2})}{p^{\ominus}}$ ，因为在本章习题中书写繁琐，故采用上面的简写表示。凡对数符号后面的均为相对浓度和相对分压。
(7) $\mathrm{CO}_{2} / \mathrm{HCOOH}$ $\mathrm{CO}_{2} + 2\mathrm{H}^{+} + 2\mathrm{e}^{-} = \mathrm{HCOOH}$ 
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {\left[ c (\mathrm {H} ^ {+}) \right] ^ {2} p (\mathrm {C O} _ {2})}{c (\mathrm {H C O O H})}
$$
(8) HCOOH/HCHO HCOOH + 2H⁺ + 2e⁻ = HCHO + H₂O 
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {c (\mathrm {H C O O H}) [ c (\mathrm {H} ^ {+}) ] ^ {2}}{c (\mathrm {H C H O})}
$$
(9) $\left[\mathrm{PdBr}_4\right]^{2-} / \mathrm{Pd}$ $\left[\mathrm{PdBr}_4\right]^{2-} + 2\mathrm{e}^{-} = \mathrm{Pd} + 4\mathrm{Br}^{-}$ 
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {c \left\{\left[ \mathrm {P d B r} _ {4} \right] ^ {2 -} \right\}}{\left[ c (\mathrm {B r} ^ {-}) \right] ^ {4}}
$$
(10) $\mathrm{AgC_2H_3O_2 / Ag}$ $\mathrm{AgC_2H_3O_2 + e^- = Ag + C_2H_3O_2^-}$ 
$$
E = E ^ {\ominus} + 0. 0 5 9 \mathrm {V} \lg \frac {1}{c \left(\mathrm {C} _ {2} \mathrm {H} _ {3} \mathrm {O} _ {2} ^ {-}\right)}
$$
(11) $\mathrm{O}_2 / \mathrm{H}_2\mathrm{O}_2$ $\mathrm{O}_2 + 2\mathrm{H}^+ + 2\mathrm{e}^- = \mathrm{H}_2\mathrm{O}_2$ 
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {\left[ c (\mathrm {H} ^ {+}) \right] ^ {2} p (\mathrm {O} _ {2})}{c (\mathrm {H} _ {2} \mathrm {O} _ {2})}
$$
(12) $\mathrm{H}_2\mathrm{O}_2 / \mathrm{H}_2\mathrm{O}$ $\mathrm{H}_2\mathrm{O}_2 + 2\mathrm{H}^+ + 2\mathrm{e}^- = 2\mathrm{H}_2\mathrm{O}$ 
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \left\{c \left(\mathrm {H} _ {2} \mathrm {O} _ {2}\right) \left[ c \left(\mathrm {H} ^ {+}\right) \right] ^ {2} \right\}
$$

10-2
（1） $\mathrm{Ba(OH)_2 / Ba}$ $\mathrm{Ba(OH)_2 + 2e^- = Ba + 2OH^-}$ 
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {1}{\left[ c (\mathrm {O H} ^ {-}) \right] ^ {2}}
$$
(4) $\mathrm{H}_2\mathrm{PO}_2^- / \mathrm{P}$ $\mathrm{H}_2\mathrm{PO}_2^- + \mathrm{e}^- = \mathrm{P} + 2\mathrm{OH}^-$ 
$$
E = E ^ {\ominus} + 0. 0 5 9 \mathrm {V} \lg \frac {c (\mathrm {H} _ {2} \mathrm {P O} _ {2} ^ {-})}{[ c (\mathrm {O H} ^ {-}) ] ^ {2}}
$$
(7) $\mathrm{PO}_4^{3-} / \mathrm{HPO}_3^{2-}$ $\mathrm{PO}_4^{3-} + 2\mathrm{H}_2\mathrm{O} + 2\mathrm{e}^- = \mathrm{HPO}_3^{2-} + 3\mathrm{OH}^-$ 
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {c \left(\mathrm {P O} _ {4} ^ {3 -}\right)}{c \left(\mathrm {H P O} _ {3} ^ {2 -}\right) \left[ c (\mathrm {O H} ^ {-}) \right] ^ {3}}
$$
(10) $\mathrm{AgO / Ag_2O}$ $2\mathrm{AgO} + \mathrm{H}_2\mathrm{O} + 2\mathrm{e}^{-} = \mathrm{Ag}_2\mathrm{O} + 2\mathrm{OH}^-$ 
$$
E = E ^ {\ominus} + \frac {0 . 0 5 9 \mathrm {V}}{2} \lg \frac {1}{\left[ c (\mathrm {O H} ^ {-}) \right] ^ {2}}
$$

10-4
解：（1）正极 $\frac{1}{2}\mathrm{Cl}_2 + \mathrm{e}^- = \mathrm{Cl}^-$ $E_{+}^{\ominus} = 1.35827\mathrm{V}$ 
负极 $\mathrm{Fe}^{3+} + \mathrm{e}^{-} = \mathrm{Fe}^{2+}$ $E_{-}^{\ominus} = 0.771\mathrm{~V}$ 
$$
E ^ {\ominus} = E _ {+} ^ {\ominus} - E _ {-} ^ {\ominus} = 1. 3 5 8 2 7 \mathrm {V} - 0. 7 7 1 \mathrm {V} = 0. 5 8 7 \mathrm {V}
$$
由 $E^{\ominus} = \frac{0.059\mathrm{~V}}{z}\mathrm{lg}K^{\ominus}$ 
得 $\lg K^{\ominus} = \frac{zE^{\ominus}}{0.059\mathrm{V}} = \frac{1\times 0.587\mathrm{~V}}{0.059\mathrm{~V}} = 9.95$ 
故反应
$$
\mathrm {F e} ^ {2 +} + \frac {1}{2} \mathrm {C l} _ {2} = \mathrm {F e} ^ {3 +} + \mathrm {C l} ^ {-}
$$
的 $K^{\ominus} = 8.9 \times 10^{9}$ , 所以反应 (1) 的 $K^{\ominus} = (8.9 \times 10^{9})^{2} = 7.9 \times 10^{19}$ 。
（2）正极 $\mathrm{Hg_2Cl_2 + 2e^- = 2Hg + 2Cl^-}$ $E_{+}^{\ominus} = 0.26808\mathrm{V}$ 
负极 $\mathrm{Zn}^{2+} + 2\mathrm{e}^{-} = \mathrm{Zn}$ $E_{-}^{\ominus} = -0.7618\mathrm{V}$ 
$$
E ^ {\ominus} = E _ {+} ^ {\ominus} - E _ {-} ^ {\ominus} = 0. 2 6 8 0 8 \mathrm {V} - (- 0. 7 6 1 8 \mathrm {V}) = 1. 0 2 9 9 \mathrm {V}
$$
$$
\lg K ^ {\ominus} = \frac {z E ^ {\ominus}}{0 . 0 5 9 \mathrm {V}} = \frac {2 \times 1 . 0 2 9 9 \mathrm {V}}{0 . 0 5 9 \mathrm {V}} = 3 4. 9 2
$$
故反应
$$
\mathrm {Z n} + \mathrm {H g} _ {2} \mathrm {C l} _ {2} = 2 \mathrm {H g} + \mathrm {Z n} ^ {2 +} + 2 \mathrm {C l} ^ {-}
$$
的 $K^{\ominus} = 8.3\times 10^{34}$ 
（3）正极 $\frac{1}{2}\mathrm{Cl}_2 + \mathrm{e}^- = \mathrm{Cl}^-$ $E_{+}^{\ominus} = 1.35827\mathrm{V}$ 
负极 $\mathrm{HClO} + \mathrm{H}^{+} + \mathrm{e}^{-} = \frac{1}{2}\mathrm{Cl}_{2} + \mathrm{H}_{2}\mathrm{O}$ $E_{-}^{\ominus} = 1.611\mathrm{~V}$ 
$$
E ^ {\ominus} = E _ {+} ^ {\ominus} - E _ {-} ^ {\ominus} = 1. 3 5 8 2 7 \mathrm {V} - 1. 6 1 1 \mathrm {V} = - 0. 2 5 3 \mathrm {V}
$$
$$
\lg K ^ {\ominus} = \frac {z E ^ {\ominus}}{0 . 0 5 9 \mathrm {V}} = \frac {1 \times (- 0 . 2 5 3 \mathrm {V})}{0 . 0 5 9 \mathrm {V}} = - 4. 2 9
$$
故反应
$$
\mathrm {C l} _ {2} + \mathrm {H} _ {2} \mathrm {O} = \mathrm {H C l O} + \mathrm {H} ^ {+} + \mathrm {C l} ^ {-}
$$
的 $K^{\ominus} = 5.1\times 10^{-5}$ 
（4）正极 $2\mathrm{H}^{+} + 2\mathrm{e}^{-} = \mathrm{H}_{2}$ $E_{+}^{\ominus} = 0.00000\mathrm{V}$ 
负极 $\mathrm{O}_2 + 4\mathrm{H}^+ +4\mathrm{e}^- = 2\mathrm{H}_2\mathrm{O}$ $E_{-}^{\ominus} = 1.229\mathrm{V}$ 
$$
E ^ {\ominus} = E _ {+} ^ {\ominus} - E _ {-} ^ {\ominus} = 0. 0 0 0 0 0 \mathrm {V} - 1. 2 2 9 \mathrm {V} = - 1. 2 2 9 \mathrm {V}
$$
$$
\lg K ^ {\ominus} = \frac {z E ^ {\ominus}}{0 . 0 5 9 \mathrm {V}} = \frac {4 \times (- 1 . 2 2 9 \mathrm {V})}{0 . 0 5 9 \mathrm {V}} = - 8 3. 3 2
$$
故反应
$$
2 \mathrm {H} _ {2} \mathrm {O} = 2 \mathrm {H} _ {2} + \mathrm {O} _ {2}
$$
的 $K^{\ominus} = 4.8\times 10^{-84}$

10-5
解：（1）正极 $\frac{1}{4}\mathrm{O}_2 + \frac{1}{2}\mathrm{H}_2\mathrm{O} + \mathrm{e}^- = \mathrm{OH}^-$ $E_{+}^{\ominus} = 0.401\mathrm{V}$ 
负极 $\frac{1}{4}\mathrm{O}_2 + \mathrm{H}^+ +\mathrm{e}^- = \frac{1}{2}\mathrm{H}_2\mathrm{O}$ $E_{-}^{\ominus} = 1.229\mathrm{~V}$ 
$$
E ^ {\ominus} = E _ {+} ^ {\ominus} - E _ {-} ^ {\ominus} = 0. 4 0 1 \mathrm {V} - 1. 2 2 9 \mathrm {V} = - 0. 8 2 8 \mathrm {V}
$$
$$
\lg K ^ {\ominus} = \frac {z E ^ {\ominus}}{0 . 0 5 9 \mathrm {V}} = \frac {1 \times (- 0 . 8 2 8 \mathrm {V})}{0 . 0 5 9 \mathrm {V}} = - 1 4. 0
$$
故反应
$$
\mathrm {H} _ {2} \mathrm {O} = \mathrm {H} ^ {+} + \mathrm {O H} ^ {-}
$$
的 $K^{\ominus} = 1.0\times 10^{-14}$ 
（2）正极 $\mathrm{PbI}_2 + 2\mathrm{e}^{-} = \mathrm{Pb}^{-} + 2\mathrm{I}^{-}$ $E_{+}^{\ominus} = -0.365\mathrm{V}$ 
负极 $\mathrm{Pb}^{2+} + 2\mathrm{e}^{-} = \mathrm{Pb}$ $E_{-}^{\ominus} = -0.1262\mathrm{~V}$ 
$$
E ^ {\ominus} = E _ {+} ^ {\ominus} - E _ {-} ^ {\ominus} = - 0. 3 6 5 \mathrm {V} - (- 0. 1 2 6 2 \mathrm {V}) = - 0. 2 3 9 \mathrm {V}
$$
$$
\lg K ^ {\ominus} = \frac {z E ^ {\ominus}}{0 . 0 5 9 \mathrm {V}} = \frac {2 \times (- 0 . 2 3 9 \mathrm {V})}{0 . 0 5 9 \mathrm {V}} = - 8. 1 0
$$
故反应
$$
\mathrm {P b I} _ {2} = \mathrm {P b} ^ {2 +} + 2 \mathrm {I} ^ {-}
$$
的 $K^{\ominus} = 7.9\times 10^{-9}$ 
（3）正极 $\mathrm{Pt}^{2+} + 2\mathrm{e}^{-} = \mathrm{Pt}$ $E_{+}^{\ominus} = 1.18\mathrm{V}$ 
负极 $\left[\mathrm{PtCl}_4\right]^{2-} + 2\mathrm{e}^{-} = \mathrm{Pt} + 4\mathrm{Cl}^{-}$ $E_{-}^{\ominus} = 0.755\mathrm{V}$ 
$$
E ^ {\ominus} = E _ {+} ^ {\ominus} - E _ {-} ^ {\ominus} = 1. 1 8 \mathrm {V} - 0. 7 5 5 \mathrm {V} = 0. 4 2 5 \mathrm {V}
$$
$$
\lg K ^ {\ominus} = \frac {z E ^ {\ominus}}{0 . 0 5 9 \mathrm {V}} = \frac {2 \times 0 . 4 2 5 \mathrm {V}}{0 . 0 5 9 \mathrm {V}} = 1 4. 4 1
$$
故反应
$$
\mathrm {P t} ^ {2 +} + 4 \mathrm {C l} ^ {-} = [ \mathrm {P t C l} _ {4} ] ^ {2 -}
$$
的 $K^{\ominus} = 2.6\times 10^{14}$

"""

if __name__ == "__main__":
    count_questions('无机化学_无图片版_化学推断题_question.md')
   # 执行转换
    #result = reformat_question(raw_data1)
    #print(result)
    #result = reformat_answer(raw_data2)
    #print(result)