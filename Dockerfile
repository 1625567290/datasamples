# 使用官方 Python 镜像作为基础
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
# 注意：你需要先创建一个 requirements.txt 文件
COPY requirements.txt requirements.txt

# 添加一行来尝试破坏缓存
RUN echo "Forcing cache invalidation $(date)"

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码到工作目录
# 将当前目录下的所有文件（包括 app.py 和 datasamples 文件夹）复制到镜像的 /app 目录
COPY . .

# 暴露 Flask 应用运行的端口
EXPOSE 5001

# 定义容器启动时运行的命令
# 使用 uvicorn 运行 Flask 应用 (app:app 指向 app.py 文件中的 app 实例)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001", "--workers", "1"] # 使用 uvicorn

# 注释掉或删除旧的 CMD 指令
# CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:app"]
# CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]