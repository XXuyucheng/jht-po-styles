# jht-po-styles

从聚水潭协同平台 H5 采购单详情页提取款号（`C310-1-…`），支持截止号、跳过、删除线、Markdown 复选框。

页面是带 `#` hash 路由的 uni-app SPA，**必须用 Playwright 打开完整 URL**，不能用 `requests`/`curl`。

## Windows 安装包（推荐）

本机是 macOS 时**无法直接生成 Windows `.exe`**，请用下面任一方式：

### A. GitHub Actions 自动打包

1. 把本仓库推到 GitHub
2. 打开 **Actions → Build Windows EXE → Run workflow**
3. 跑完后下载产物 `JhtPoStyles-windows-portable.zip`
4. 在 Windows 解压，双击 `JhtPoStyles.exe`
5. 首次点「开始提取」时会自动下载 Chromium（约 150MB，需联网）到  
   `%LOCALAPPDATA%\jht-po-styles\ms-playwright`

打版本标签也会发 Release：

```bash
git tag v1.0.0
git push origin v1.0.0
```

### B. 在 Windows 电脑上本地打包

```powershell
cd jht-po-styles
.\packaging\build_windows.ps1
```

产物：

| 路径 | 说明 |
|------|------|
| `dist\JhtPoStyles\JhtPoStyles.exe` | 可直接运行 |
| `dist\JhtPoStyles-windows-portable.zip` | 便携压缩包 |

可选安装程序：安装 [Inno Setup](https://jrsoftware.org/isinfo.php)，打开 `packaging\installer.iss` 编译，得到 `dist\JhtPoStyles-Setup.exe`。

## 图形界面（开发机）

```bash
cd ~/Projects/jht-po-styles
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python jht_po_ui.py
# 或打包入口：
python app_main.py
```

## 命令行用法

URL 请加双引号，避免 shell 把 `&` 当成后台任务：

```bash
python jht_po_styles.py "https://jhtwechat.erp321.com/jht/h5/wx/#/pages/wx/purchaseorder/detail/index?po_id=..."
```

### 常用参数

| 参数 | 含义 |
|------|------|
| `--until 6047` | 提取到该主号段为止（默认不含本号） |
| `--inclusive` | 含截止号本身 |
| `--skip 2780,2763` | 按主号段删除 |
| `--strike 2234,5507` | 删除线标记（组合款任一片段命中即标记） |
| `--md` | 输出 `- [ ]` / `- [x]` |
| `--unicode-strike` | U+0336 组合删除线（备忘录更易见） |
| `--headed` | 有头模式排查登录 |
| `-o FILE` | 写入文件 |

## 安装依赖（开发）

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

打包额外依赖：`pip install -r requirements-build.txt`

## 登录态

若标题不是「订单详情」，可勾选 UI 的「显示浏览器」或：

```bash
python jht_po_styles.py "URL" --headed --user-data-dir ./chrome-profile
```

## 说明

- Chromium **不打进安装包**，首次提取时下载，避免包体积过大、路径难处理
- Gradio 会在本机打开浏览器界面（默认 `http://127.0.0.1:7860`）
- 与 Cursor Skill `jht-purchase-order-styles` 共用同一套提取规则
