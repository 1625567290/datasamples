// 获取 DOM 元素
const chatOutput = document.getElementById('chat-output');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');

// --- 配置 API ---
// 使用相对路径，这样它会指向加载页面的同一个域名的 API
const API_ENDPOINT = '/v1/chat/completions'; // 修改这里，移除域名和端口
// 前端不需要 API Key，认证由后端 app.py 处理
const API_KEY = null;

// 发送消息的函数
async function sendMessage() {
    const messageText = userInput.value.trim();
    if (messageText === '') {
        return; // 如果输入为空，则不执行任何操作
    }

    // 1. 在界面上显示用户发送的消息
    displayMessage(messageText, 'user');
    userInput.value = ''; // 清空输入框
    scrollToBottom();

    // 2. (可选) 显示加载提示
    const loadingMessageElement = displayMessage('AI 正在思考中...', 'bot loading');
    scrollToBottom();

    try {
        // 3. 调用本地的 Wrapper API (app.py)
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            // 发送 OpenAI Chat Completions 格式的 body
            body: JSON.stringify({
                // model 字段可以随意写一个，因为后端 app.py 会使用它自己的 MODEL_NAME
                model: "qwen-custom-wrapper",
                messages: [
                    // 只发送当前用户的消息即可，system prompt 和知识库由后端处理
                    { role: "user", content: messageText }
                ],
                stream: false // 【重要】设置为 false 以接收完整响应，而不是流。
                             // 如果你想测试流式，改为 true，但需要重写下面的响应处理逻辑。
            })
        });

        // 检查响应是否成功
        if (!response.ok) {
             let errorData = {};
             let errorMessage = `API 请求失败，状态码：${response.status}`;
             try {
                 // 尝试解析后端返回的 JSON 错误信息
                 errorData = await response.json();
                 if (errorData.error && errorData.error.message) {
                     errorMessage = errorData.error.message;
                 } else {
                     errorMessage = JSON.stringify(errorData); // 如果格式不符合预期，显示原始 JSON
                 }
             } catch (parseError) {
                 // 如果连JSON都解析不了，就用状态文本
                 errorMessage = response.statusText || errorMessage;
             }
             throw new Error(errorMessage);
        }

        // 解析 JSON 响应 (OpenAI Chat Completion 格式)
        const data = await response.json();

        // 4. 从 API 响应中提取 AI 的回复
        const aiReply = data.choices?.[0]?.message?.content || '抱歉，未能获取到有效回复。';

        // 5. 更新界面：用 AI 回复替换 "思考中..."
        loadingMessageElement.textContent = aiReply;
        // 移除 loading 类，保留 bot 类
        loadingMessageElement.classList.remove('loading'); // 只移除 loading

    } catch (error) {
        console.error('调用 API 时出错:', error);
        // 6. 处理错误情况：在界面上显示错误信息
        loadingMessageElement.textContent = `出错了: ${error.message || error}`;
        // 同样只移除 loading 类
        loadingMessageElement.classList.remove('loading');
        loadingMessageElement.style.color = 'red'; // 标红显示错误
    } finally {
        // 确保无论成功或失败，最终都滚动到底部
         scrollToBottom();
         
    }
}

// 在聊天输出区显示消息的辅助函数
function displayMessage(text, sender) {
    const messageElement = document.createElement('div');
    // 将 sender 字符串按空格分割成单独的类名
    const classes = sender.split(' ');
    // 添加 'message' 类和 sender 提供的所有类
    messageElement.classList.add('message', ...classes); // 使用扩展运算符添加所有类
    messageElement.textContent = text;
    chatOutput.appendChild(messageElement);
    return messageElement; // 返回创建的元素，方便后续操作（如移除loading）
}

// 滚动到聊天输出区底部的函数
function scrollToBottom() {
    chatOutput.scrollTop = chatOutput.scrollHeight;
}

// --- 事件监听 ---
// 点击发送按钮时发送消息
sendButton.addEventListener('click', sendMessage);

// 按下 Enter 键时也发送消息
userInput.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault(); // 阻止默认的回车换行行为
        sendMessage();
    }
});

// 初始化时滚动到底部（如果有初始消息）
scrollToBottom();

