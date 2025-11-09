#!/bin/bash

# [!!! 重要 !!!] 您的 GitHub 仓库 URL (已正确设置)
GITHUB_REPO_URL="https://github.com/aaron012001222/domain-rotation-system.git"

# 颜色定义
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
NC="\033[0m" # No Color

echo -e "${GREEN}=== 开始安装 域名轮询系统 (安全强化版) ===${NC}"

# 步骤 1: 检查依赖 (git, docker, docker-compose, htpasswd)
echo -e "\n${YELLOW}步骤 1: 检查并安装依赖...${NC}"

# 更新 apt 缓存
sudo apt-get update

# 检查 Git
if ! command -v git &> /dev/null; then
    echo "未找到 Git，正在安装..."
    sudo apt-get install -y git
fi

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "未找到 Docker，正在使用官方脚本安装..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
fi

# 检查 Docker Compose v2 插件
if ! docker compose version &> /dev/null; then
    echo "未找到 Docker Compose，正在安装..."
    sudo apt-get install -y docker-compose-plugin
fi

# [新] 检查 htpasswd (来自 apache2-utils)
if ! command -v htpasswd &> /dev/null; then
    echo "未找到 htpasswd，正在安装 apache2-utils..."
    sudo apt-get install -y apache2-utils
fi

echo -e "${GREEN}所有依赖均已准备就绪。${NC}"

# 步骤 2: 克隆项目代码
echo -e "\n${YELLOW}步骤 2: 从 GitHub 克隆项目代码...${NC}"
if [ -d "domain-rotation-system" ]; then
    echo "检测到 'domain-rotation-system' 目录已存在，进入目录并尝试拉取更新..."
    cd domain-rotation-system
    git pull
else
    git clone $GITHUB_REPO_URL
    if [ $? -ne 0 ]; then
        echo -e "${RED}项目克隆失败。请检查您的 GITHUB_REPO_URL 是否正确。${NC}"
        exit 1
    fi
    cd domain-rotation-system
fi

# 步骤 3: [新] 生成管理员凭据
echo -e "\n${YELLOW}步骤 3: 正在生成管理员凭据...${NC}"
ADMIN_USER="admin"
# 生成一个 12 位的随机密码
ADMIN_PASS=$(openssl rand -base64 12)

# 在 frontend 目录下创建 .htpasswd 文件
# Dockerfile 将会把它复制到 Nginx 容器中
htpasswd -c -b ./frontend/.htpasswd $ADMIN_USER $ADMIN_PASS
if [ $? -ne 0 ]; then
    echo -e "${RED}创建 .htpasswd 文件失败。${NC}"
    exit 1
fi
echo "密码文件已创建。"

# 步骤 4: 构建并启动 Docker 容器
echo -e "\n${YELLOW}步骤 4: 正在构建 Docker 镜像 (这可能需要几分钟)...${NC}"
if ! sudo docker compose build; then
    echo -e "${RED}Docker 镜像构建失败。${NC}"
    exit 1
fi

# 步骤 5: 正在后台启动系统...
echo -e "\n${YELLOW}步骤 5: 正在后台启动系统...${NC}"
if ! sudo docker compose up -d; then
    echo -e "${RED}Docker 容器启动失败。${NC}"
    exit 1
fi

# 步骤 6: 完成
PUBLIC_IP=$(curl -s ifconfig.me)
echo -e "\n${GREEN}===========================================${NC}"
echo -e "${GREEN} 域名轮询系统 安装成功! ${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "您的管理后台已在运行。"
echo -e "请通过您的服务器 IP 访问: ${YELLOW}http://${PUBLIC_IP}${NC}"
echo ""
echo -e "${RED}!!! 重要：请保存您的登录凭据 !!!${NC}"
echo -e "用户名: ${YELLOW}${ADMIN_USER}${NC}"
echo -e "密 码: ${YELLOW}${ADMIN_PASS}${NC}"
echo ""
echo -e "下一步:"
echo -e "1. 将您的中转域名 (例如: go1.example.com) 通过 A 记录指向: ${YELLOW}${PUBLIC_IP}${NC}"
echo -e "2. 访问 ${YELLOW}http://${PUBLIC_IP}${NC} 并使用上述密码登录。"
echo -e "3. 在组管理中添加您的中转域名 (go1.example.com) 和落地域名。"
echo -e "4. 访问您的中转链接 (例如: http://go1.example.com/go) 进行测试。"

exit 0