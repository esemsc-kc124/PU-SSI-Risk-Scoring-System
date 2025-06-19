# --- Stage 1: 使用官方的Python镜像作为基础 ---
# This defines our starting point. We use an official Python image.
FROM python:3.12-slim

# --- Stage 2: 设置工作目录 ---
# This sets the working directory inside our "container".
WORKDIR /app

# --- Stage 3: 复制依赖文件并安装 ---
# First, copy the requirements file.
COPY requirements.txt requirements.txt
# Then, install all the Python libraries listed in it.
# We use --no-cache-dir to keep the image size small.
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 4: 复制您的所有项目代码 ---
# Copy all your application files (simulator.py, core.py, etc.) into the container.
COPY . .

# --- Stage 5: 告诉Docker，我们的应用会使用哪个端口 ---
# This informs Docker that our application will be listening on port 8080.
EXPOSE 8080

# --- Stage 6: 定义启动命令 ---
# This is the final command that will be run when the container starts.
# It executes our simulator.py script.
CMD ["python", "simulator.py"]
