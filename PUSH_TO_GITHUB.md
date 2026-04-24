# 推送到GitHub说明

## 步骤1：在GitHub上创建新仓库

1. 登录您的GitHub账号
2. 点击右上角 "+" 号，选择 "New repository"
3. 填写仓库信息：
   - Repository name: `hotel-order-financialization` (或您喜欢的名称)
   - Description: `酒店订单金融化可行性分析 - 基于ABS/RWA金融模型`
   - 选择 "Public" 或 "Private"
   - 不要勾选 "Initialize this repository with a README"
4. 点击 "Create repository"

## 步骤2：配置本地Git仓库

在终端中执行以下命令（替换为您的GitHub用户名和仓库名）：

```bash
# 添加远程仓库（替换为您的实际仓库地址）
git remote add origin https://github.com/YOUR_USERNAME/hotel-order-financialization.git

# 验证远程仓库
git remote -v

# 推送代码到GitHub
git push -u origin master
```

## 步骤3：验证推送

1. 打开浏览器访问您的GitHub仓库页面
2. 确认所有文件都已上传：
   - README.md
   - LICENSE
   - .gitignore
   - src/ 目录下的代码文件
   - data/ 目录下的数据文件
   - output/ 目录下的输出文件

## 常见问题

### 1. 身份验证失败

如果提示需要用户名密码，请使用Personal Access Token：

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token"
3. 选择 "repo" 权限
4. 生成Token并复制
5. 在推送时，用户名输入您的GitHub用户名，密码输入Token

### 2. 分支名称问题

如果GitHub默认分支是 `main` 而不是 `master`：

```bash
# 重命名本地分支
git branch -m master main

# 推送到main分支
git push -u origin main
```

### 3. 大文件问题

如果CSV文件太大无法推送，可以在 `.gitignore` 中添加：

```
data/*.csv
output/*.json
output/*.png
```

然后重新提交：

```bash
git add .gitignore
git commit -m "Ignore large data files"
git push origin master
```

## 项目结构说明

推送后，您的GitHub仓库将包含以下结构：

```
hotel-order-financialization/
├── README.md              # 项目说明
├── LICENSE                # MIT许可证
├── .gitignore             # Git忽略文件
├── data/                  # 数据文件
│   ├── cleaned_hotel_prices.csv
│   ├── hotel_future_prices.csv
│   ├── hotel_info.csv
│   └── ...
├── src/                   # 源代码
│   ├── hotel_simulation_v5.py
│   ├── generate_simple_pdf.py
│   └── clean_and_generate_prices.py
└── output/                # 输出文件
    ├── simulation_report_v5.json
    ├── simulation_visualization_v5.png
    └── 酒店订单金融化可行性分析报告.html
```

## 后续更新

当您修改代码后，可以按以下步骤更新GitHub：

```bash
# 查看修改的文件
git status

# 添加修改的文件
git add .

# 提交修改
git commit -m "描述您的修改"

# 推送到GitHub
git push origin master
```

## 需要帮助？

如果您在推送过程中遇到问题，请查看：
- GitHub文档：https://docs.github.com/cn
- Git文档：https://git-scm.com/doc
