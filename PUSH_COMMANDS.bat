@echo off
chcp 65001
echo ==========================================
echo 酒店订单金融化项目 - GitHub推送脚本
echo ==========================================
echo.

cd /d "C:\Users\weida\Desktop\酒店研究"

echo [1/4] 检查Git状态...
git status
echo.

echo [2/4] 配置远程仓库...
git remote add origin https://github.com/David-coder-hnu/hotel-order-financialization.git 2>nul
git remote -v
echo.

echo [3/4] 切换到main分支...
git branch -m master main 2>nul
echo 当前分支:
git branch
echo.

echo [4/4] 推送到GitHub...
echo 正在推送代码，请稍候...
git push -u origin main
echo.

if %errorlevel% == 0 (
    echo ==========================================
    echo 推送成功！
    echo 请访问: https://github.com/David-coder-hnu/hotel-order-financialization
    echo ==========================================
) else (
    echo ==========================================
    echo 推送失败，请检查：
    echo 1. 网络连接是否正常
    echo 2. GitHub账号密码或Token是否正确
    echo 3. 仓库地址是否正确
    echo ==========================================
)

pause
