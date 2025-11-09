#!/bin/bash

# -------------------------------------------------------------------
# 域名轮询系统 (Domain Rotation System) 一键安装脚本
# (c) 2025 Your Name
# [版本: 仅依赖Cloudflare Access进行安全防护]
# -------------------------------------------------------------------

# [!!! 重要 !!!] 您的 GitHub 仓库 URL
GITHUB_REPO_URL="https://github.com/aaron012001222/domain-rotation-system.git"

# 颜色定义
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
NC="\033[0m" # No Color

echo -e "${GREEN}=== 开始安装 域名轮询系统 ===${NC}"

# 步骤 1: 检查依赖 (git, docker, docker-compose)
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

# 步骤 3: [已删除] 不再需要生成管理员凭据

# 步骤 4: 构建并启动 Docker 容器
echo -e "\n${YELLOW}步骤 4: 正在构建 Docker 镜像 (这可能需要几分钟)...${NC}"
if ! sudo docker compose build; then
    echo -e "${RED}Docker 镜像构建失败。${NC}"
    exit 1
fi

# 步骤 5: 正在后台启动系统...
echo -e "\n${YELLOW}步骤 5: GANG正在后台启动系统...${NC}"
if ! sudo docker compose up -d; then
    echo -e "${RED}Docker 容器启动失败。${NC}"
    exit 1
fi

# 步骤 6: 完成
echo -e "\n${GREEN}===========================================${NC}"
echo -e "${GREEN} 域名轮询系统 安装成功! ${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "您的管理后台已在运行。"
echo -e "请通过您在 Cloudflare Access 中设置的后台 URL 访问:"
echo -e "${YELLOW}https://admin-panel.zhongzhuanzhongzhuan18.help${NC} (请替换为您的真实后台域名)"
echo ""
echo -e "[重要] 您的系统现在由 Cloudflare Access (邮箱验证码) 保护。"
echo ""
echo -e "下一步:"
echo -e "1. 确保您的中转域名 (例如: zhongzhuanzhongzhuan18.help) 在 Cloudflare DNS 中已正确配置。"
echo -e "2. 登录您的后台管理页面 (见上文)。"
echo -e "3. 在组管理中添加您的中转域名和落地域名。"
echo -e "4. 访问您的中转链接 (例如: http://zhongzhuanzhongzhuan18.help/go) 进行测试。"

exit 0