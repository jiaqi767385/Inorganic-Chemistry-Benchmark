import json
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patheffects as path_effects

# =================================================================
# 1. 基础配置与映射
# =================================================================

# 章节索引映射，用于图表标签展示
CHAPTER_NAMES = {
    "1": "化学基础知识", "2": "化学热力学基础", "3": "化学反应速率", "4": "化学平衡",
    "5": "原子结构和元素周期律", "6": "分子结构和共价键理论", "7": "晶体结构",
    "8": "酸碱解离平衡", "9": "沉淀溶解平衡", "10": "氧化还原反应", "11": "配位化学基础",
    "12": "碱金属和碱土金属", "13": "硼族元素", "14": "碳族元素", "15": "氮族元素",
    "16": "氧族元素", "17": "卤素", "18": "氢和稀有气体",
    "19": "铜副族和锌副族", "20": "钛副族和钒副族", "21": "铬副族和锰副族",
    "22": "铁系和铂系元素", "23": "极地/镧系锕系", "24": "无机化学新兴领域"
}


# =================================================================
# 2. 数据解析模块
# =================================================================

def get_chapter_stats(data_list):
    """解析原始评测数据，按章节维度统计模型性能指标。

    Args:
        data_list (list): 包含模型评测项的字典列表。

    Returns:
        dict: 键为章节索引字符串，值为包含 count, correct, tokens, time 等指标的统计字典。
    """
    stats = {}
    for item in data_list:
        # 提取主章节索引（例如 "10-24" 提取为 "10"）
        chapter = str(item.get('index', '')).split('-')[0]
        eval_data = item.get('evaluation', {})
        usage = item.get('usage', {})
        duration = item.get('duration', {})

        if chapter not in stats:
            stats[chapter] = {
                "count": 0, "correct": 0,
                "p_tokens": 0, "c_tokens": 0,
                "reasoning_time": 0, "eval_time": 0
            }

        stats[chapter]["count"] += 1
        if eval_data.get('score', 0) == 1:
            stats[chapter]["correct"] += 1

        # 累加资源消耗
        stats[chapter]["p_tokens"] += usage.get('prompt_tokens', 0)
        stats[chapter]["c_tokens"] += usage.get('completion_tokens', 0)
        stats[chapter]["reasoning_time"] += duration.get('reasoning', 0)
        stats[chapter]["eval_time"] += duration.get('eval', 0)
    return stats


# =================================================================
# 3. 可视化组件
# =================================================================

def variable_radius_pie_chart(chapters, widths_data, inner_radius_ratios, labels, title=None):
    """
    绘制变半径南丁格尔玫瑰图，并自动优化窄扇区标签排布。

    功能特性：
    1. 自动排序：按扇区宽度升序排列，将窄扇区（小角度）集中于图表底部，避开顶部标题。
    2. 智能标签：宽扇区直接标注，窄扇区自动生成引线以防文字重叠。
    3. 维度展示：扇区角度代表总量（widths_data），扇区半径代表表现指标（inner_radius_ratios）。

    Args:
        chapters (list): 章节名或索引序列。
        widths_data (list): 扇区宽度数值，决定扇区弧度大小。
        inner_radius_ratios (list): 半径比例（0-1），决定扇区实心部分高度。
        labels (list): 随标签显示的补充数值或说明文本。
        title (str, optional): 图表标题。
    """
    if not widths_data or sum(widths_data) == 0: return

    # 1. 按宽度升序排列数据，确保窄扇区始于起始位置
    combined = sorted(zip(widths_data, chapters, inner_radius_ratios, labels), key=lambda x: x[0])
    widths_sorted, chapters_sorted, ratios_sorted, labels_sorted = zip(*combined)

    # 2. 计算极坐标弧度分布
    total_width_sum = sum(widths_sorted)
    widths = [(w / total_width_sum) * 2 * np.pi for w in widths_sorted]
    lefts = np.cumsum([0] + widths[:-1])

    # 3. 画布初始化与中文字体配置
    plt.rcParams['font.sans-serif'], plt.rcParams['axes.unicode_minus'] = ['SimHei'], False
    fig = plt.figure(figsize=(14, 11))
    ax = fig.add_subplot(111, projection='polar')
    plt.subplots_adjust(top=0.8, bottom=0.15, left=0.1, right=0.9)

    # 4. 旋转坐标轴：从3点钟方向顺时针绘制，使窄扇区汇聚在底部区域
    ax.set_theta_offset(0)
    ax.set_theta_direction(-1)

    colors = plt.cm.plasma(np.linspace(0, 1, len(chapters_sorted)))
    THRESHOLD_RAD = np.deg2rad(12) # 触发引线的角度阈值

    for i in range(len(chapters_sorted)):
        # 绘制背景背景(alpha=0.1)与数据扇区
        ax.bar(lefts[i], 1.0, width=widths[i], color=colors[i], alpha=0.1, align='edge', edgecolor='white')
        ax.bar(lefts[i], ratios_sorted[i], width=widths[i], color=colors[i], alpha=0.8, align='edge')

        mid_angle = lefts[i] + widths[i] / 2
        display_label = f"{CHAPTER_NAMES.get(chapters_sorted[i], chapters_sorted[i])}\n({labels_sorted[i]})"
        curr_deg = np.rad2deg(mid_angle) % 360

        # 5. 智能引线逻辑：根据扇区宽度和所处象限自动调整位置
        if widths[i] > THRESHOLD_RAD:
            ax.text(mid_angle, 1.15, display_label, ha='center', va='center', fontsize=7, fontweight='bold',
                    path_effects=[path_effects.withStroke(linewidth=2, foreground='white')])
        else:
            # 底部扇区（90°-270°）增加引线长度以防拥挤
            text_dist = 1.35 if (90 <= curr_deg <= 270) else 1.25
            ax.annotate(display_label, xy=(mid_angle, 1.01), xytext=(mid_angle, text_dist),
                        arrowprops=dict(arrowstyle='->', color='gray', lw=0.8, connectionstyle="arc3,rad=0.05"),
                        ha='left' if curr_deg < 180 else 'right', va='center', fontsize=7, fontweight='bold',
                        path_effects=[path_effects.withStroke(linewidth=2, foreground='white')])

    ax.set_axis_off()
    if title: fig.suptitle(title, fontsize=18, fontweight='bold', y=0.92)
    plt.show()


def draw_comparison_bars(all_chapters, datas_list, model_names_list):
    """绘制跨模型对比的三种柱状图。

    Args:
        all_chapters (list): 所有章节索引。
        datas_list (list): 模型原始数据。
        model_names_list (list): 模型标识名。
    """
    plot_configs = [
        ("accuracy", "Accuracy (%)", "Cross-Model Accuracy Comparison"),
        ("tokens", "Total Tokens", "Cross-Model Token Usage"),
        ("duration", "Total Duration (s)", "Cross-Model Execution Time")
    ]

    for mode, y_label, title in plot_configs:
        plt.figure(figsize=(15, 8))
        x = np.arange(len(all_chapters))
        width = 0.8 / len(model_names_list)

        for idx, (data_list, model_name) in enumerate(zip(datas_list, model_names_list)):
            stats = get_chapter_stats(data_list)
            offset = idx * width - (len(model_names_list) - 1) * width / 2

            if mode == "accuracy":
                vals = [stats.get(ch, {"count": 0, "correct": 0})["correct"] /
                        max(stats.get(ch, {"count": 1})["count"], 1) * 100 for ch in all_chapters]
            elif mode == "tokens":
                vals = [stats.get(ch, {"p_tokens": 0, "c_tokens": 0})["p_tokens"] +
                        stats.get(ch, {"p_tokens": 0, "c_tokens": 0})["c_tokens"] for ch in all_chapters]
            elif mode == "duration":
                vals = [stats.get(ch, {"reasoning_time": 0, "eval_time": 0})["reasoning_time"] +
                        stats.get(ch, {"reasoning_time": 0, "eval_time": 0})["eval_time"] for ch in all_chapters]

            plt.bar(x + offset, vals, width, label=model_name)

        plt.title(title, fontsize=16, fontweight='bold')
        plt.ylabel(y_label)
        plt.xticks(x, [CHAPTER_NAMES.get(c, c) for c in all_chapters], rotation=45, ha='right')
        plt.legend(loc='upper right', frameon=True)
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.show()


def radar_chart(norm_metrics, model_names):
    """绘制所有模型综合对比的雷达图，优化 Legend 布局。

    Args:
        norm_metrics (list): 归一化得分列表。
        model_names (list): 模型名称。
    """
    labels = ['Accuracy', 'Speed', 'Economy']
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    plt.subplots_adjust(right=0.75)  # 给右侧图例留出空间

    for m_stats, name in zip(norm_metrics, model_names):
        values = [m_stats['acc'], m_stats['speed'], m_stats['economy']]
        values += values[:1]
        ax.plot(angles, values, linewidth=2.5, label=name, marker='o', markersize=6)
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.tick_params(axis='x', pad=30)
    ax.set_xticklabels(labels, fontweight='bold', fontsize=12)
    ax.set_ylim(0, 1.25)  # 视觉留白
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])

    plt.title("Cross-Model Multi-Dimensional Comparison", fontsize=16, fontweight='bold', y=1.1)
    # 优化图例位置和间距，防止重叠
    plt.legend(loc='upper left', bbox_to_anchor=(1.15, 1.0), labelspacing=1.2, fontsize=10, frameon=False)
    plt.show()


# =================================================================
# 4. 执行流程控制
# =================================================================

def analyze(datas_list, model_names_list):
    """分析引擎主入口：执行 3xN 玫瑰图 + 3 柱状图 + 1 雷达图。

    Args:
        datas_list (list): 模型原始数据 JSON 列表。
        model_names_list (list): 模型名称列表。
    """
    all_chapters = sorted(list(set().union(*(get_chapter_stats(d).keys() for d in datas_list))),
                          key=lambda x: int(x) if x.isdigit() else 999)

    # 第一部分：每个模型 3 张玫瑰图
    for d, name in zip(datas_list, model_names_list):
        s = get_chapter_stats(d)
        chs = sorted(s.keys(), key=lambda x: int(x) if x.isdigit() else 999)

        # 1. Accuracy Rose
        variable_radius_pie_chart(
            chs,
            [s[k]["count"] for k in chs],
            [s[k]["correct"] / s[k]["count"] for k in chs],
            [f"{s[k]['correct'] / s[k]['count'] * 100:.0f}%" for k in chs],
            title=f"Accuracy Rose: {name}"
        )

        # 2. Token Rose
        t_list = [s[k]["p_tokens"] + s[k]["c_tokens"] for k in chs]
        r_list = [s[k]["c_tokens"] / max(s[k]["p_tokens"] + s[k]["c_tokens"], 1) for k in chs]
        l_list = [f"{s[k]['p_tokens'] + s[k]['c_tokens']}" for k in chs]
        variable_radius_pie_chart(chs, t_list, r_list, l_list, title=f"Token Distribution: {name}")

        # 3. Duration Rose
        d_list = [s[k]["reasoning_time"] + s[k]["eval_time"] for k in chs]
        rd_list = [s[k]["eval_time"] / max(s[k]["reasoning_time"] + s[k]["eval_time"], 1) for k in chs]
        ld_list = [f"{s[k]['reasoning_time'] + s[k]['eval_time']:.1f}s" for k in chs]
        variable_radius_pie_chart(chs, d_list, rd_list, ld_list, title=f"Duration Rose: {name}")

    # 第二部分：3 张跨模型柱状图
    draw_comparison_bars(all_chapters, datas_list, model_names_list)

    # 第三部分：1 张综合雷达图
    metrics = []
    for d in datas_list:
        s = get_chapter_stats(d)
        total_q = sum(v["count"] for v in s.values())
        acc = sum(v["correct"] for v in s.values()) / max(total_q, 1)
        tks = sum(v["p_tokens"] + v["c_tokens"] for v in s.values())
        dur = sum(v["reasoning_time"] + v["eval_time"] for v in s.values())
        metrics.append({"acc": acc, "tks": tks, "dur": dur})

    min_tks = min(m["tks"] for m in metrics if m["tks"] > 0)
    min_dur = min(m["dur"] for m in metrics if m["dur"] > 0)

    norm_metrics = [{"acc": m["acc"], "speed": min_dur / m["dur"], "economy": min_tks / m["tks"]} for m in metrics]
    radar_chart(norm_metrics, model_names_list)


if __name__ == "__main__":
    configs = [
        ("021-reason", "021_reason_flexible_全部样本测试结果.json"),
        ("deepseek-v3.2-hz", "deepseek_v3_2_hz_flexible_全部样本测试结果.json"),
        ("gemini-3.1-pro-preview-hz", "gemini_3_1_pro_preview_hz_flexible_全部样本测试结果.json")
    ]

    all_datas, names = [], []
    for name, path in configs:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                all_datas.append(json.load(f))
                names.append(name)
        except Exception as e:
            print(f"Error loading {path}: {e}")

    if len(all_datas) == len(configs):
        analyze(all_datas, names)