# 使用官方 Node 镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json（如果有）
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制项目源码（开发时会被挂载覆盖）
COPY . .

# 默认命令（会被 compose 中的 command 覆盖）
CMD ["npm", "run", "dev"]