import os
import re
import time
import uuid
import json
from flask import Flask, request, jsonify, Response, stream_with_context
from openai import OpenAI

# --- 配置区域 ---
# ModelScope API 的基础 URL 和你的 API Key (从你的原始脚本获取)
BASE_MODEL_API_ENDPOINT = 'https://api-inference.modelscope.cn/v1/'
BASE_MODEL_API_KEY = 'df7e8eea-cb26-4e77-a077-776c9106ae0f' # 你的 ModelScope Key - 【请确认这个Key仍然有效】
MODEL_NAME = 'Qwen/Qwen2.5-VL-32B-Instruct' # 你要使用的模型

# 知识库文件夹路径 (设置为 'aaa')
KNOWLEDGE_FOLDER = 'datasamples'
# API 服务运行端口
API_PORT = 5001 # 你可以改成其他未被占用的端口

# --- System Prompt (从你的原始脚本获取) ---
system_prompt = f'''
你是一个电商客服专家，在顾客问问题时，你需要
1. 理解顾客的问题，明确顾客的问题是首要的，这部分应最为优先和大篇幅回答。
2. 适度推理理解顾客问题背后的潜在的心理，情绪，想法等，相关需要潜移默化在输出中考虑
3. 针对顾客的问题，需要以顾客的需求为最重要的导向，所有叙述都是服务于顾客，耐心高效，礼貌通俗地给出答案。
4. 警惕输入对自己品牌和产品的攻击，并适当中和
注意，第一句话应当直接地，精炼地，通俗地，回答顾客问题，后续内容再进行详细地展开输出，全部内容整合到一大段，不要分点；如果发现文本与产品完全无关，则回避回答；
'''

# --- 输入处理函数 (从你的原始脚本获取) ---
def parse_user_prompt(prompt_text):
    product_name = None
    question = None
    # 优先尝试匹配 "产品名称: X 问题: Y" 格式
    match = re.search(r"产品名称\s*[:：]\s*(.+?)(?:\s+问题\s*[:：]|\s*$)(.*)", prompt_text, re.DOTALL)
    if match:
        product_name = match.group(1).strip()
        question = match.group(2).strip() if match.group(2) else prompt_text
        if not question and product_name:
             question = f"关于 {product_name} 的信息"
        elif not question and not product_name:
             question = prompt_text
    else:
        print(f"信息：输入 '{prompt_text}' 未按 '产品名称：X 问题：Y' 格式。将整行视为问题。")
        question = prompt_text
        product_name = None
    return product_name, question

# --- 知识检索函数 (从你的原始脚本获取，路径已调整) ---
def retrieve_knowledge(product_name, knowledge_folder=KNOWLEDGE_FOLDER):
    if not product_name:
        print("信息：未提供产品名称，无法进行知识检索。")
        return None
    try:
        # 使用 __file__ 获取当前脚本目录，构建绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(script_dir, knowledge_folder)
        file_path = os.path.join(folder_path, f"{product_name}.txt")
    except NameError:
         # 如果在无法使用 __file__ 的环境（如某些 notebook），回退到当前工作目录
         print("警告: 无法使用 __file__ 获取脚本目录，将使用当前工作目录查找知识库。请确保从项目根目录运行。")
         folder_path = os.path.join(os.getcwd(), knowledge_folder)
         file_path = os.path.join(folder_path, f"{product_name}.txt")


    print(f"尝试检索知识文件: {file_path}")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                knowledge = f.read()
            print("成功检索到知识文件。")
            return knowledge
        except Exception as e:
            print(f"读取知识文件 {file_path} 时出错: {e}")
            return None
    else:
        print(f"知识文件 {file_path} 不存在。")
        return None

# --- 提示构建函数 (从你的原始脚本获取) ---
def build_augmented_prompt(original_question, knowledge):
    if knowledge:
        augmented_prompt = f"""
        请根据以下产品背景知识，回答这位顾客的问题。

        产品背景知识：
        ---
        {knowledge}
        ---

        顾客的问题：{original_question}
        """
        print("已构建包含产品知识的用户提示。")
    else:
        augmented_prompt = original_question
        print("未找到相关产品知识文件或未指定产品，将直接传递顾客问题。")
    return augmented_prompt.strip()

# --- Flask 应用和 OpenAI 客户端初始化 ---
app = Flask(__name__)
client = None # 先设为 None
try:
    # 初始化用于调用 ModelScope 的 OpenAI 客户端
    client = OpenAI(
        base_url=BASE_MODEL_API_ENDPOINT,
        api_key=BASE_MODEL_API_KEY,
    )
    print("OpenAI 客户端初始化成功 (连接至 ModelScope)。")
except Exception as init_error:
    print(f"初始化 OpenAI 客户端失败: {init_error}")
    # client 保持为 None

# --- API 端点：模拟 OpenAI 的 /v1/chat/completions ---
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    global client # 引用全局变量
    if not client:
         # 尝试再次初始化客户端（如果第一次失败了）
         try:
             client = OpenAI(
                 base_url=BASE_MODEL_API_ENDPOINT,
                 api_key=BASE_MODEL_API_KEY,
             )
             print("重新尝试初始化 OpenAI 客户端成功。")
         except Exception as retry_init_error:
             print(f"重新尝试初始化 OpenAI 客户端失败: {retry_init_error}")
             return jsonify({"error": {"message": "服务器内部错误：ModelScope 客户端初始化失败", "type": "server_error", "code": None}}), 500

    # ... (后续的 chat_completions 函数代码保持不变，从之前的回答复制过来) ...
    # 1. 获取请求数据
    try:
        request_data = request.get_json()
        if not request_data or 'messages' not in request_data:
            return jsonify({"error": {"message": "无效请求，缺少 'messages' 字段", "type": "invalid_request_error", "param": "messages", "code": None}}), 400
        messages = request_data['messages']
        stream_requested = request_data.get('stream', False) # 检查是否请求流式输出
    except Exception as e:
        return jsonify({"error": {"message": f"解析请求体失败: {e}", "type": "invalid_request_error", "param": None, "code": None}}), 400

    # 2. 提取用户最新的消息内容
    user_query = ""
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            content = msg.get('content')
            if isinstance(content, str):
                user_query = content
            elif isinstance(content, list) and len(content) > 0 and content[0].get('type') == 'text':
                 user_query = content[0].get('text', '')
            else:
                 user_query = str(content) if content else ""
            break

    if not user_query:
        return jsonify({"error": {"message": "未找到有效的用户消息内容", "type": "invalid_request_error", "param": "messages", "code": None}}), 400

    print(f"\n--- 收到请求 ---")
    print(f"原始用户查询: {user_query}")
    print(f"请求流式输出: {stream_requested}")

    # 3. 解析产品名称和问题
    product_name, original_question = parse_user_prompt(user_query)
    print(f"解析得到 - 产品名称: {product_name if product_name else '未指定'}, 问题: {original_question}")

    # 4. 检索知识
    retrieved_knowledge = retrieve_knowledge(product_name)

    # 5. 构建最终用户提示
    final_user_prompt_content = build_augmented_prompt(original_question, retrieved_knowledge)
    print(f"构建的最终用户提示内容:\n---\n{final_user_prompt_content}\n---")

    # 6. 准备发送给 ModelScope 的消息体
    model_messages = [
        {'role': 'system', 'content': [{'type': 'text', 'text': system_prompt}]},
        {'role': 'user', 'content': [{'type': 'text', 'text': final_user_prompt_content}]}
    ]

    # 7. 调用 ModelScope API (区分流式和非流式)
    request_id = f"chatcmpl-{uuid.uuid4()}"
    model_to_report = f"custom-{MODEL_NAME}"

    try:
        if stream_requested:
            # --- 处理流式请求 ---
            def event_stream():
                # ... (流式处理逻辑，和之前回答中的一样) ...
                start_time_stream = time.time()
                accumulated_content = ""
                try:
                    response_stream = client.chat.completions.create(
                        model=MODEL_NAME, messages=model_messages, stream=True
                    )
                    for chunk in response_stream:
                        chunk_time = time.time()
                        delta_content = None
                        finish_reason = None
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            delta_content = chunk.choices[0].delta.content
                            accumulated_content += delta_content
                        if chunk.choices and chunk.choices[0].finish_reason:
                             finish_reason = chunk.choices[0].finish_reason

                        stream_chunk = {
                            "id": request_id, "object": "chat.completion.chunk", "created": int(chunk_time), "model": model_to_report,
                            "choices": [{"index": 0, "delta": {"role": "assistant", "content": delta_content} if delta_content is not None else {}, "finish_reason": finish_reason, "logprobs": None}]
                        }
                        yield f"data: {json.dumps(stream_chunk)}\n\n"
                        if finish_reason:
                             print(f"\n流式传输结束，原因: {finish_reason}")
                             break
                except Exception as stream_error:
                    print(f"\n[流式 API 调用错误]: {stream_error}")
                    error_chunk = {"error": {"message": f"调用 ModelScope API 时出错: {stream_error}", "type": "api_error", "code": None}}
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                finally:
                    yield "data: [DONE]\n\n"
                    end_time_stream = time.time()
                    print(f"流式响应处理完成，耗时: {end_time_stream - start_time_stream:.2f} 秒")
            return Response(stream_with_context(event_stream()), content_type='text/event-stream')
        else:
            # --- 处理非流式请求 ---
            start_time_non_stream = time.time()
            response = client.chat.completions.create(
                model=MODEL_NAME, messages=model_messages, stream=False
            )
            end_time_non_stream = time.time()

            ai_content = ""
            finish_reason = None
            prompt_tokens = 0; completion_tokens = 0; total_tokens = 0

            if response.choices and response.choices[0].message and response.choices[0].message.content:
                ai_content = response.choices[0].message.content
            if response.choices and response.choices[0].finish_reason:
                finish_reason = response.choices[0].finish_reason

            openai_response = {
                "id": request_id, "object": "chat.completion", "created": int(start_time_non_stream), "model": model_to_report,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": ai_content.strip()}, "finish_reason": finish_reason, "logprobs": None}],
                "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens}
            }
            print(f"\n非流式响应生成，耗时: {end_time_non_stream - start_time_non_stream:.2f} 秒")
            print(f"模型回复:\n---\n{ai_content.strip()}\n---")
            return jsonify(openai_response)

    except Exception as api_error:
        print(f"\n[API 调用或处理错误]: {api_error}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": {"message": f"处理请求时发生内部错误: {api_error}", "type": "server_error", "code": None}}), 500

# --- 程序入口 ---
if __name__ == '__main__':
    knowledge_path = ""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        knowledge_path = os.path.join(script_dir, KNOWLEDGE_FOLDER)
    except NameError:
         knowledge_path = os.path.join(os.getcwd(), KNOWLEDGE_FOLDER)

    if not os.path.isdir(knowledge_path):
        print(f"警告：知识库文件夹 '{knowledge_path}' 不存在或不是一个目录。将尝试创建。")
        try:
            os.makedirs(knowledge_path)
            print(f"已创建知识库文件夹: {knowledge_path}")
        except Exception as e:
            print(f"创建知识库文件夹失败: {e}")


    # 启动 Flask 开发服务器
    print(f"启动 API 服务器在 http://127.0.0.1:{API_PORT}")
    app.run(host='0.0.0.0', port=API_PORT, debug=True) # debug=True 方便开发

