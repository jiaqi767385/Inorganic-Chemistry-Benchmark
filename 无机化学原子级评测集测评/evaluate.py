import requests
import json
import time
import re
import random
import sys
import os
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ================= 1. 日志重定向类 =================
class Logger(object):
    """
    同时将输出打印到屏幕和文件
    """
    def __init__(self, filename="log.txt"):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()


# ================= 2. 配置区 =================
# 默认 API 基础路径
BASE_URL = "http://10.200.95.16:30300/v1"
URL_021_32B = "http://jb-aionlineinferenceservice-155759600569185984-8000.z2120.nhss.zhejianglab.com:31040/v1"

# API Keys
DEFAULT_API_KEY = "sk-HT8ssY7PWUUWvRK9uoOfA8pnXaYYBnCtQ9hk1gW0p0xkCu2T"
MODEL_021_KEY = "sk-08rfGelDtcbHdyldemqgNkg4HL0pSuOoy9TPwCk0QXi7FuWJ"
KEY_021_32B = "zjlabllm"

REASONING_MODEL_LIST = [
    "021-reason",
    "021-reason-32b",
    "deepseek-v3.2-hz",
    "gemini-3.1-pro-preview-hz",
]

EVAL_MODES = {
    "flexible": """你是一个专业的无机化学教授，负责对学生的【生成答案】进行逻辑评审。
评分准则：
1. 语义与逻辑优先：简答题表述不要求字面一致。若生成答案在语义层面、化学逻辑和科学原理上与标准答案等价，必须给 1 分。
2. 承认多样性：解题的方法和途径并不唯一。只要生成答案正确解释了现象、推导出了正确产物且无原则性错误，应给 1 分。
3. 核心准则：不要盲目因为不一致而判定错误，需通过推理判断其化学本质是否正确。
4. 必须输出标准 JSON 格式：{"score": 0/1, "analysis": "..."}。"""
}

EVAL_MODEL = "qwen3.5-plus-hz"

# --- 全局控制变量 ---
SAMPLE_COUNT = None  # 设置为 None 则跑全量数据
MAX_WORKERS = 2
TIMEOUT_SECONDS = 2000
MAX_RETRIES = 5
PRECISION_THRESHOLD = "两位有效数字或两位小数"


# ================= 3. 核心功能函数 =================

def get_configured_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
    session.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))
    return session


def safe_api_call(messages, model):
    # 根据模型选择不同的 URL 和 Key
    if model == "021-reason-32b":
        target_url = f"{URL_021_32B}/chat/completions"
        current_key = KEY_021_32B
    elif model == "021-reason":
        target_url = f"{BASE_URL}/chat/completions"
        current_key = MODEL_021_KEY
    else:
        target_url = f"{BASE_URL}/chat/completions"
        current_key = DEFAULT_API_KEY

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {current_key}"}

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0, # 化学评测建议保持 0 提高稳定性
        "stream": False
    }

    # 特殊推理模型参数配置
    if model in ["021-reason", "021-reason-32b"]:
        payload.update({
            "chat_template_kwargs": {"enable_thinking": True},
            "repetition_penalty": 1.05,
            "presence_penalty": 1,
            "top_p": 0.95,
            "max_tokens": 50000
        })
        if model == "021-reason-32b":
            payload["stop"] = ["<|eot_id|>"]

    session = get_configured_session()
    for attempt in range(MAX_RETRIES):
        try:
            response = session.post(target_url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                time.sleep((attempt + 1) * 2 + random.random())
            else:
                print(f"Error {response.status_code} ({model}): {response.text}")
                time.sleep(1)
        except Exception:
            time.sleep(2)
    return None


def parse_md_to_dict(file_path):
    if not os.path.exists(file_path):
        print(f"❌ 错误：文件 {file_path} 不存在")
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    id_pattern = re.compile(r'^(\d+-\d+)', re.MULTILINE)
    matches = list(id_pattern.finditer(content))
    data_map = {}
    for i, match in enumerate(matches):
        q_id = match.group(1)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        data_map[q_id] = content[start:end].strip()
    return data_map


def process_task(q_id, q_text, a_text, model_name, eval_mode_name):
    # 1. 推理阶段
    reasoning_prompt = f"请利用无机化学知识回答以下题目。\n题目内容：\n{q_text}"
    start_r = time.time()
    ans_data = safe_api_call([{"role": "user", "content": reasoning_prompt}], model_name)

    if not ans_data or 'choices' not in ans_data:
        return {"index": q_id, "error": f"模型 {model_name} 请求失败",
                "evaluation": {"score": 0, "analysis": "模型无响应"}}

    msg = ans_data['choices'][0]['message']
    full_content = msg.get('content', "")
    full_reasoning = msg.get('reasoning_content', "")
    usage = ans_data.get('usage', {})
    duration_r = round(time.time() - start_r, 2)

    # 2. 评估阶段
    eval_sys = EVAL_MODES[eval_mode_name]
    eval_sys += f"\n注：数值结果若在【{PRECISION_THRESHOLD}】内应判定为正确。"

    start_e = time.time()
    eval_user = f"【题目】:\n{q_text}\n\n【标准答案】:\n{a_text}\n\n【生成答案】:\n{full_content}"
    eval_data = safe_api_call([{"role": "system", "content": eval_sys}, {"role": "user", "content": eval_user}],
                              EVAL_MODEL)

    eval_res = {"score": 0, "analysis": "未收到评估模型返回内容"}
    if eval_data and 'choices' in eval_data:
        raw_eval = eval_data['choices'][0]['message']['content']
        try:
            clean_text = re.sub(r'```json\s*|\s*```', '', raw_eval).strip()
            json_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            json_str = json_match.group(1) if json_match else clean_text
            eval_res = json.loads(json_str)
            eval_res["score"] = int(eval_res.get("score", 0))
        except Exception:
            score_match = re.search(r'["\']score["\']\s*:\s*(\d)', raw_eval)
            eval_res = {"score": int(score_match.group(1)) if score_match else 0,
                        "analysis": f"JSON解析失败。原始返回：\n{raw_eval}"}

    return {
        "index": q_id, "eval_mode": eval_mode_name, "question": q_text, "standard_answer": a_text,
        "reasoning": full_reasoning, "model_answer": full_content, "evaluation": eval_res,
        "duration": {"reasoning": duration_r, "eval": round(time.time() - start_e, 2)}, "usage": usage
    }


def run_experiment(input_question_file, input_answer_file):
    q_dict = parse_md_to_dict(input_question_file)
    a_dict = parse_md_to_dict(input_answer_file)
    all_ids = list(q_dict.keys())

    if not all_ids:
        print(f"⚠️ 跳过实验：在 {input_question_file} 中未发现题目。")
        return

    sample_label = SAMPLE_COUNT if SAMPLE_COUNT is not None else "全部"
    selected_ids = random.sample(all_ids, min(SAMPLE_COUNT, len(all_ids))) if SAMPLE_COUNT else all_ids

    summary_table = []

    print(f"✅ 测评基准已建立：{input_question_file}")
    print(f"📊 抽取 {len(selected_ids)} 道题。")
    print(f"🔍 对比范围：{len(REASONING_MODEL_LIST)} 模型 × {len(EVAL_MODES)} 评价标准。\n")

    for model_name in REASONING_MODEL_LIST:
        print(f"🚀 开始测试模型: {model_name}")
        for mode_key in EVAL_MODES.keys():
            safe_model_name = model_name.replace('-', '_').replace('.', '_')
            output_file = f'{safe_model_name}_{mode_key}_{sample_label}样本测试结果.json'

            mode_results = []
            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_id = {
                    executor.submit(process_task, qid, q_dict[qid], a_dict.get(qid, ""), model_name, mode_key): qid
                    for qid in selected_ids
                }
                for future in tqdm(as_completed(future_to_id), total=len(selected_ids),
                                   desc=f"进度 ({model_name} | {mode_key})", file=sys.stdout):
                    try:
                        mode_results.append(future.result())
                    except Exception as e:
                        print(f"\n🔴 运行时错误: {e}")

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(mode_results, f, ensure_ascii=False, indent=2)

            total_correct = sum(1 for r in mode_results if r.get('evaluation', {}).get('score') == 1)
            total_time = sum(r.get('duration', {}).get('reasoning', 0) for r in mode_results)
            total_tokens = sum((r.get('usage') or {}).get('total_tokens', 0) for r in mode_results)
            wrong_ids = [str(r.get('index')) for r in mode_results if r.get('evaluation', {}).get('score') != 1]

            summary_table.append({
                "model": model_name, "mode": mode_key.upper(),
                "accuracy": f"{total_correct}/{len(selected_ids)}",
                "time": f"{total_time:.2f}s", "tokens": total_tokens
            })

            print("-" * 75)
            print(f"📊 报告 | 模型: {model_name} | 模式: {mode_key.upper()}")
            print(f"✅ 正确率: {total_correct}/{len(selected_ids)} | ⏱️ 耗时: {total_time:.2f}s")
            print(f"❌ 错题: {', '.join(wrong_ids) if wrong_ids else '全部正确'}")
            print("-" * 75 + "\n")

    print("\n" + "=" * 95)
    print(f"{'推理模型':<35} | {'评估模式':<10} | {'正确率':<10} | {'耗时':<12} | {'Tokens':<10}")
    print("-" * 95)
    for entry in summary_table:
        print(f"{entry['model']:<35} | {entry['mode']:<10} | {entry['accuracy']:<10} | {entry['time']:<12} | {entry['tokens']:<10}")
    print("=" * 95 + "\n")


# ================= 4. 入口 =================
if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_path = f"logs/{timestamp}.txt"
    sys.stdout = Logger(log_path)

    # 第一批任务：定量计算
    run_experiment(
        '无机化学_无图片版_定量计算题_question.md',
        '无机化学_无图片版_定量计算题_answer.md'
    )

    # 第二批任务：化学推断
    run_experiment(
        '无机化学_无图片版_化学推断题_question.md',
        '无机化学_无图片版_化学推断题_answer.md'
    )