# 智能金融产品顾问

这是一个基于智谱AI的智能金融产品顾问系统，使用Streamlit构建用户界面。

## 功能特点

- 实时对话交互
- 集成智谱AI GLM-4模型
- 智能产品推荐
- 自动关单提醒
- 完整的对话历史记录
- 错误处理和日志记录

## 安装步骤

1. 克隆项目到本地
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 在`.env`文件中配置您的智谱AI API密钥：
   ```
   ZHIPUAI_API_KEY=your_api_key_here
   ```

## 本地运行

执行以下命令启动应用：
```bash
streamlit run chatbot.py
```

## 部署方式

### 1. Streamlit Cloud部署（推荐）

1. 将代码推送到GitHub仓库
2. 访问 [Streamlit Cloud](https://streamlit.io/cloud)
3. 使用GitHub账号登录
4. 点击 "New app" 并选择您的仓库
5. 在 "Advanced settings" 中配置环境变量
6. 点击 "Deploy" 开始部署

### 2. Docker部署

1. 构建镜像：
   ```bash
   docker-compose build
   ```

2. 启动服务：
   ```bash
   docker-compose up -d
   ```

3. 访问 http://localhost:8501

### 3. 云服务器部署

1. 安装依赖：
   ```bash
   sudo apt update
   sudo apt install python3-pip
   pip3 install -r requirements.txt
   ```

2. 使用screen保持后台运行：
   ```bash
   screen -S chatbot
   streamlit run chatbot.py --server.port 8501 --server.address 0.0.0.0
   ```

3. 配置Nginx反向代理（可选）：
   ```nginx
   server {
       listen 80;
       server_name your_domain.com;
       
       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
       }
   }
   ```

## 注意事项

- 请确保您有有效的智谱AI API密钥
- 保护好您的API密钥，不要将其提交到版本控制系统
- 建议在生产环境中使用HTTPS
- 定期备份产品数据
- 监控API使用情况和成本 