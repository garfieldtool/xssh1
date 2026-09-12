# Windows 打印店书籍封面拼版生成工具 (Book Cover Generator for Print Shops)

专为快印店、打印店、图文广告店以及个人出版设计的 Windows 桌面小工具。输入书籍的**正面封面**和**背面封面**图片，即可自动计算书脊厚度、叠加裁切角线（Crop Marks）与折痕虚线，一键生成符合 1:1 印刷标准的高清 **A3 / A4 封面拼版图** (支持 PNG、JPG 以及矢量 PDF 导出)。

---

## 🌟 主要功能特点

1. **精准尺寸计算与拼版 (A3 / A4 Spread)**：
   - 自动将【封底（Back） + 书脊（Spine） + 封面（Front）】居中拼贴到指定尺寸的打印纸张（如 A3 420x297mm，A4，SRA3，A3+ 等）上。
   - 支持设置成品书籍规格（A5、B5、16开、32开或自定义尺寸）。

2. **专业印前标注（角线与折痕）**：
   - **裁切角线 (Crop Marks)**：在四角和书脊两侧生成标准的印刷裁切角线，方便装订切纸。
   - **折痕虚线 (Fold Lines)**：指示压痕机/压折线位置。
   - **3mm 标准出血 (Bleed)**：防止切边白边。

3. **书脊自定义 (Spine Customization)**：
   - 支持自定义书脊厚度（例如 5mm, 10mm, 15mm）。
   - 支持在书脊上添加书名，支持中文竖排（直书）与横排旋转。
   - 支持自定义书脊文字字号、颜色以及书脊背景填充色（亦可自动取封面边缘颜色）。

4. **实时图形预览与 100% 比例导出**：
   - 提供直观的实时拼版预览画布。
   - 支持一键导出 **300 DPI 高清印刷图 (PNG/JPG)** 以及 **1:1 矢量 PDF 文件**。

---

## 🖥️ 运行与开发环境

- **操作系统**：Windows 10 / Windows 11 / Linux
- **依赖语言**：Python 3.8+
- **关键依赖包**：`Pillow`, `ReportLab`, `PyInstaller` (用于打包)

### 1. 本地直接运行

```bash
# 1. 安装依赖
pip install pillow reportlab

# 2. 启动应用程序
python main.py
```

### 2. 运行自动化测试

```bash
python -m unittest discover -s tests
```

---

## 📦 打包为 Windows 单文件/独立 EXE 程序

在 Windows 环境下，可使用项目附带的打包脚本一键打包成独立运行的 `.exe` 软件，无需安装 Python 环境即可在打印店电脑上运行。

### 打包步骤：

双击运行根目录下的 `build_exe.bat` 脚本，或者在终端执行：

```bash
python build_exe.py
```

打包完成后，可在 `dist/BookCoverGenerator/` 目录下找到 `BookCoverGenerator.exe` 可执行程序。
