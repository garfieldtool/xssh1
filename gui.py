"""
GUI Interface for Windows Book Cover Generator Tool.
Built with Tkinter for desktop compatibility.
Includes Spine Thickness Calculator and Cover Image Editing / Text Overlays.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk

from cover_engine import (
    CoverConfig, CoverEngine, TextOverlay, ImageEditConfig,
    PAPER_SIZES_MM, BOOK_SIZES_MM, PAPER_TYPES_THICKNESS_MM, calculate_spine_thickness
)


class BookCoverApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("A3 / A4 打印店专业书籍封面拼版生成工具 v1.1")
        self.root.geometry("1180x780")
        self.root.minsize(1000, 680)

        # File paths
        self.front_cover_path = tk.StringVar()
        self.back_cover_path = tk.StringVar()

        # Paper & Dimensions
        self.paper_preset_var = tk.StringVar(value="A3")
        self.paper_width_var = tk.DoubleVar(value=420.0)
        self.paper_height_var = tk.DoubleVar(value=297.0)

        self.book_preset_var = tk.StringVar(value="A5")
        self.book_width_var = tk.DoubleVar(value=148.0)
        self.book_height_var = tk.DoubleVar(value=210.0)

        self.spine_width_var = tk.DoubleVar(value=10.0)
        self.bleed_var = tk.DoubleVar(value=3.0)
        self.dpi_var = tk.IntVar(value=300)

        # Spine Calculator
        self.page_count_var = tk.IntVar(value=200)
        self.paper_type_var = tk.StringVar(value="80g 双胶纸 (Offset Paper)")

        # Spine Text Options
        self.spine_text_var = tk.StringVar(value="")
        self.spine_text_color_var = tk.StringVar(value="#000000")
        self.spine_text_size_var = tk.IntVar(value=14)
        self.spine_text_vertical_var = tk.BooleanVar(value=True)
        self.spine_bg_color_var = tk.StringVar(value="#FFFFFF")
        self.use_custom_spine_bg_var = tk.BooleanVar(value=False)

        # Printing & Prepress Marks
        self.draw_crop_marks_var = tk.BooleanVar(value=True)
        self.draw_fold_lines_var = tk.BooleanVar(value=True)
        self.draw_info_text_var = tk.BooleanVar(value=True)
        self.fill_mode_var = tk.StringVar(value="fit")

        # Front Cover Editing & Text Overlays
        self.front_brightness_var = tk.DoubleVar(value=1.0)
        self.front_contrast_var = tk.DoubleVar(value=1.0)
        self.front_tint_color_var = tk.StringVar(value="")
        self.front_title_text_var = tk.StringVar(value="")
        self.front_title_color_var = tk.StringVar(value="#000000")
        self.front_title_size_var = tk.IntVar(value=28)

        # Back Cover Editing & Text Overlays
        self.back_brightness_var = tk.DoubleVar(value=1.0)
        self.back_contrast_var = tk.DoubleVar(value=1.0)
        self.back_tint_color_var = tk.StringVar(value="")
        self.back_text_var = tk.StringVar(value="")
        self.back_text_color_var = tk.StringVar(value="#333333")
        self.back_text_size_var = tk.IntVar(value=16)

        # Preview cache
        self.current_preview_image = None
        self.tk_preview_image = None

        self._build_ui()
        self._on_paper_preset_change()
        self._on_book_preset_change()
        self.update_preview()

    def _build_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_paned, width=420)
        main_paned.add(left_frame, weight=0)

        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # Scrollable notebook container on left
        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_layout = ttk.Frame(notebook)
        tab_spine_calc = ttk.Frame(notebook)
        tab_cover_edit = ttk.Frame(notebook)

        notebook.add(tab_layout, text=" 1. 规格与拼版 ")
        notebook.add(tab_spine_calc, text=" 2. 页数厚度计算器 ")
        notebook.add(tab_cover_edit, text=" 3. 图片修饰与文字 ")

        # --- TAB 1: Specs & Layout ---
        self._build_layout_tab(tab_layout)

        # --- TAB 2: Spine Thickness Calculator ---
        self._build_spine_calc_tab(tab_spine_calc)

        # --- TAB 3: Cover Image Editing & Text Overlays ---
        self._build_cover_edit_tab(tab_cover_edit)

        # Right Preview Canvas Area
        preview_lf = ttk.LabelFrame(right_frame, text=" 拼版实时预览 (A3 Spread Preview) ", padding=10)
        preview_lf.pack(fill=tk.BOTH, expand=True)

        self.preview_canvas = tk.Canvas(preview_lf, bg="#404040", borderwidth=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", lambda e: self._render_preview_on_canvas())

    def _build_layout_tab(self, parent):
        scroll_canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=scroll_canvas.yview)
        content = ttk.Frame(scroll_canvas)

        content.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.create_window((0, 0), window=content, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Files
        f_lf = ttk.LabelFrame(content, text=" 封面图片选择 ", padding=10)
        f_lf.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(f_lf, text="正面封面:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(f_lf, textvariable=self.front_cover_path, width=22).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(f_lf, text="浏览...", command=self._browse_front_cover).grid(row=0, column=2, pady=2)

        ttk.Label(f_lf, text="背面封面:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(f_lf, textvariable=self.back_cover_path, width=22).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(f_lf, text="浏览...", command=self._browse_back_cover).grid(row=1, column=2, pady=2)

        # Dimensions
        d_lf = ttk.LabelFrame(content, text=" 纸张与成书尺寸 (毫米 mm) ", padding=10)
        d_lf.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(d_lf, text="打印纸张规格:").grid(row=0, column=0, sticky="w", pady=2)
        paper_cb = ttk.Combobox(d_lf, textvariable=self.paper_preset_var, values=list(PAPER_SIZES_MM.keys()) + ["自定义"], state="readonly", width=12)
        paper_cb.grid(row=0, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        paper_cb.bind("<<ComboboxSelected>>", lambda e: self._on_paper_preset_change())

        f_paper = ttk.Frame(d_lf)
        f_paper.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Entry(f_paper, textvariable=self.paper_width_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_paper, text=" x ").pack(side=tk.LEFT)
        ttk.Entry(f_paper, textvariable=self.paper_height_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_paper, text=" mm").pack(side=tk.LEFT)

        ttk.Label(d_lf, text="成品书籍规格:").grid(row=2, column=0, sticky="w", pady=2)
        book_cb = ttk.Combobox(d_lf, textvariable=self.book_preset_var, values=list(BOOK_SIZES_MM.keys()) + ["自定义"], state="readonly", width=12)
        book_cb.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        book_cb.bind("<<ComboboxSelected>>", lambda e: self._on_book_preset_change())

        f_book = ttk.Frame(d_lf)
        f_book.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Entry(f_book, textvariable=self.book_width_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_book, text=" x ").pack(side=tk.LEFT)
        ttk.Entry(f_book, textvariable=self.book_height_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_book, text=" mm").pack(side=tk.LEFT)

        ttk.Label(d_lf, text="书脊厚度 (Spine):").grid(row=4, column=0, sticky="w", pady=2)
        f_spine = ttk.Frame(d_lf)
        f_spine.grid(row=4, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Entry(f_spine, textvariable=self.spine_width_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_spine, text=" mm").pack(side=tk.LEFT)

        ttk.Label(d_lf, text="出血边距 (Bleed):").grid(row=5, column=0, sticky="w", pady=2)
        f_bleed = ttk.Frame(d_lf)
        f_bleed.grid(row=5, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Entry(f_bleed, textvariable=self.bleed_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_bleed, text=" mm (标准3mm)").pack(side=tk.LEFT)

        ttk.Label(d_lf, text="打印分辨率 (DPI):").grid(row=6, column=0, sticky="w", pady=2)
        ttk.Combobox(d_lf, textvariable=self.dpi_var, values=[150, 300, 600], state="readonly", width=8).grid(row=6, column=1, columnspan=2, sticky="w", padx=5, pady=2)

        # Marks
        m_lf = ttk.LabelFrame(content, text=" 印前角线与参数 ", padding=10)
        m_lf.pack(fill=tk.X, padx=5, pady=5)

        ttk.Checkbutton(m_lf, text="绘制裁切角线 (Crop Marks)", variable=self.draw_crop_marks_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(m_lf, text="绘制书脊折痕虚线 (Fold Lines)", variable=self.draw_fold_lines_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(m_lf, text="打印版本标注信息 (Job Info)", variable=self.draw_info_text_var).pack(anchor="w", pady=2)

        ttk.Label(m_lf, text="图片填充方式:").pack(anchor="w", pady=(5, 2))
        f_mode = ttk.Frame(m_lf)
        f_mode.pack(anchor="w")
        ttk.Radiobutton(f_mode, text="保持比例 (Fit)", variable=self.fill_mode_var, value="fit").pack(side=tk.LEFT)
        ttk.Radiobutton(f_mode, text="裁剪填充 (Fill)", variable=self.fill_mode_var, value="fill").pack(side=tk.LEFT)
        ttk.Radiobutton(f_mode, text="拉伸 (Stretch)", variable=self.fill_mode_var, value="stretch").pack(side=tk.LEFT)

        # Action Buttons
        btn_frame = ttk.Frame(content, padding=10)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="刷新预览 (Refresh)", command=self.update_preview, width=18).pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="导出高清图片 (Export Image)", command=self.export_image, width=18).pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="导出 PDF (Export PDF)", command=self.export_pdf, width=18).pack(fill=tk.X, pady=3)

    def _build_spine_calc_tab(self, parent):
        calc_lf = ttk.LabelFrame(parent, text=" 根据内页页数与纸张自动计算书脊厚度 ", padding=15)
        calc_lf.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(calc_lf, text="书本内页总页数 (P数):", font=("SimSun", 10, "bold")).grid(row=0, column=0, sticky="w", pady=10)
        f_page = ttk.Frame(calc_lf)
        f_page.grid(row=0, column=1, sticky="w", padx=10, pady=10)
        ttk.Spinbox(f_page, from_=4, to=2000, increment=2, textvariable=self.page_count_var, width=8).pack(side=tk.LEFT)
        ttk.Label(f_page, text=" 页 (P)").pack(side=tk.LEFT)

        ttk.Label(calc_lf, text="内页纸张材质与克重:", font=("SimSun", 10, "bold")).grid(row=1, column=0, sticky="w", pady=10)
        paper_type_cb = ttk.Combobox(
            calc_lf, textvariable=self.paper_type_var,
            values=list(PAPER_TYPES_THICKNESS_MM.keys()), state="readonly", width=28
        )
        paper_type_cb.grid(row=1, column=1, sticky="w", padx=10, pady=10)

        ttk.Button(calc_lf, text="计算并套用书脊厚度", command=self._apply_spine_calculation, width=22).grid(row=2, column=0, columnspan=2, pady=15)

        # Spine Title Settings
        s_lf = ttk.LabelFrame(calc_lf, text=" 书脊文字与外观设置 ", padding=10)
        s_lf.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(s_lf, text="书脊书名:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(s_lf, textvariable=self.spine_text_var, width=22).grid(row=0, column=1, columnspan=2, sticky="w", padx=5, pady=2)

        ttk.Label(s_lf, text="文字方向:").grid(row=1, column=0, sticky="w", pady=2)
        f_orient = ttk.Frame(s_lf)
        f_orient.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Radiobutton(f_orient, text="竖排 (直书)", variable=self.spine_text_vertical_var, value=True).pack(side=tk.LEFT)
        ttk.Radiobutton(f_orient, text="横排 (旋转)", variable=self.spine_text_vertical_var, value=False).pack(side=tk.LEFT)

        ttk.Label(s_lf, text="字号大小 (pt):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Spinbox(s_lf, from_=8, to=72, textvariable=self.spine_text_size_var, width=6).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(s_lf, text="文字颜色:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Button(s_lf, text="选择颜色", command=self._choose_spine_text_color).grid(row=3, column=1, sticky="w", padx=5, pady=2)

        ttk.Checkbutton(s_lf, text="自定义书脊底色", variable=self.use_custom_spine_bg_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Button(s_lf, text="选择底色", command=self._choose_spine_bg_color).grid(row=4, column=2, sticky="w", pady=2)

    def _build_cover_edit_tab(self, parent):
        scroll_canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=scroll_canvas.yview)
        content = ttk.Frame(scroll_canvas)

        content.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.create_window((0, 0), window=content, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Front Cover Edit
        fe_lf = ttk.LabelFrame(content, text=" 正面封面 (Front Cover) 图片修饰与标题 ", padding=10)
        fe_lf.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(fe_lf, text="亮度 (Brightness):").grid(row=0, column=0, sticky="w", pady=2)
        s_fb = ttk.Scale(fe_lf, from_=0.5, to=1.5, variable=self.front_brightness_var, command=lambda e: self.update_preview())
        s_fb.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(fe_lf, text="对比度 (Contrast):").grid(row=1, column=0, sticky="w", pady=2)
        s_fc = ttk.Scale(fe_lf, from_=0.5, to=1.5, variable=self.front_contrast_var, command=lambda e: self.update_preview())
        s_fc.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(fe_lf, text="封面叠加标题文字:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(fe_lf, textvariable=self.front_title_text_var, width=20).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(fe_lf, text="标题字号 (pt):").grid(row=3, column=0, sticky="w", pady=2)
        f_fts = ttk.Frame(fe_lf)
        f_fts.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        ttk.Spinbox(f_fts, from_=10, to=100, textvariable=self.front_title_size_var, width=6).pack(side=tk.LEFT)
        ttk.Button(f_fts, text="文字颜色", command=self._choose_front_title_color).pack(side=tk.LEFT, padx=5)

        # Back Cover Edit
        be_lf = ttk.LabelFrame(content, text=" 背面封面 (Back Cover) 图片修饰与简介 ", padding=10)
        be_lf.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(be_lf, text="亮度 (Brightness):").grid(row=0, column=0, sticky="w", pady=2)
        s_bb = ttk.Scale(be_lf, from_=0.5, to=1.5, variable=self.back_brightness_var, command=lambda e: self.update_preview())
        s_bb.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(be_lf, text="对比度 (Contrast):").grid(row=1, column=0, sticky="w", pady=2)
        s_bc = ttk.Scale(be_lf, from_=0.5, to=1.5, variable=self.back_contrast_var, command=lambda e: self.update_preview())
        s_bc.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(be_lf, text="封底叠加文字 (如ISBN/价格):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(be_lf, textvariable=self.back_text_var, width=20).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(be_lf, text="字号大小 (pt):").grid(row=3, column=0, sticky="w", pady=2)
        f_bts = ttk.Frame(be_lf)
        f_bts.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        ttk.Spinbox(f_bts, from_=8, to=60, textvariable=self.back_text_size_var, width=6).pack(side=tk.LEFT)
        ttk.Button(f_bts, text="文字颜色", command=self._choose_back_text_color).pack(side=tk.LEFT, padx=5)

        ttk.Button(content, text="重置修饰与文字", command=self._reset_image_edits, width=20).pack(pady=10)

    def _browse_front_cover(self):
        path = filedialog.askopenfilename(
            title="选择正面封面图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff"), ("所有文件", "*.*")]
        )
        if path:
            self.front_cover_path.set(path)
            self.update_preview()

    def _browse_back_cover(self):
        path = filedialog.askopenfilename(
            title="选择背面封面图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff"), ("所有文件", "*.*")]
        )
        if path:
            self.back_cover_path.set(path)
            self.update_preview()

    def _on_paper_preset_change(self):
        preset = self.paper_preset_var.get()
        if preset in PAPER_SIZES_MM:
            w, h = PAPER_SIZES_MM[preset]
            self.paper_width_var.set(w)
            self.paper_height_var.set(h)

    def _on_book_preset_change(self):
        preset = self.book_preset_var.get()
        if preset in BOOK_SIZES_MM:
            w, h = BOOK_SIZES_MM[preset]
            self.book_width_var.set(w)
            self.book_height_var.set(h)

    def _apply_spine_calculation(self):
        try:
            pages = self.page_count_var.get()
            ptype = self.paper_type_var.get()
            spine_mm = calculate_spine_thickness(pages, ptype)
            self.spine_width_var.set(spine_mm)
            messagebox.showinfo("计算完成", f"根据 {pages}P {ptype} 计算得出:\n推算书脊厚度约为: {spine_mm} mm\n已自动更新至拼版参数中。")
            self.update_preview()
        except Exception as e:
            messagebox.showerror("计算失败", f"计算书脊厚度时出错: {str(e)}")

    def _choose_spine_text_color(self):
        color = colorchooser.askcolor(title="选择书脊文字颜色", color=self.spine_text_color_var.get())
        if color[1]:
            self.spine_text_color_var.set(color[1])
            self.update_preview()

    def _choose_spine_bg_color(self):
        color = colorchooser.askcolor(title="选择书脊背景颜色", color=self.spine_bg_color_var.get())
        if color[1]:
            self.spine_bg_color_var.set(color[1])
            self.use_custom_spine_bg_var.set(True)
            self.update_preview()

    def _choose_front_title_color(self):
        color = colorchooser.askcolor(title="选择正面标题文字颜色", color=self.front_title_color_var.get())
        if color[1]:
            self.front_title_color_var.set(color[1])
            self.update_preview()

    def _choose_back_text_color(self):
        color = colorchooser.askcolor(title="选择封底文字颜色", color=self.back_text_color_var.get())
        if color[1]:
            self.back_text_color_var.set(color[1])
            self.update_preview()

    def _reset_image_edits(self):
        self.front_brightness_var.set(1.0)
        self.front_contrast_var.set(1.0)
        self.front_title_text_var.set("")
        self.back_brightness_var.set(1.0)
        self.back_contrast_var.set(1.0)
        self.back_text_var.set("")
        self.update_preview()

    def _get_config(self) -> CoverConfig:
        front_overlays = []
        if self.front_title_text_var.get().strip():
            front_overlays.append(TextOverlay(
                text=self.front_title_text_var.get(),
                rel_x=0.5,
                rel_y=0.4,
                font_size_pt=self.front_title_size_var.get(),
                color=self.front_title_color_var.get(),
                bg_banner=True
            ))

        back_overlays = []
        if self.back_text_var.get().strip():
            back_overlays.append(TextOverlay(
                text=self.back_text_var.get(),
                rel_x=0.5,
                rel_y=0.8,
                font_size_pt=self.back_text_size_var.get(),
                color=self.back_text_color_var.get(),
                bg_banner=True
            ))

        front_edit = ImageEditConfig(
            brightness=self.front_brightness_var.get(),
            contrast=self.front_contrast_var.get(),
            text_overlays=front_overlays
        )

        back_edit = ImageEditConfig(
            brightness=self.back_brightness_var.get(),
            contrast=self.back_contrast_var.get(),
            text_overlays=back_overlays
        )

        return CoverConfig(
            paper_width_mm=self.paper_width_var.get(),
            paper_height_mm=self.paper_height_var.get(),
            book_width_mm=self.book_width_var.get(),
            book_height_mm=self.book_height_var.get(),
            spine_width_mm=self.spine_width_var.get(),
            page_count=self.page_count_var.get(),
            paper_type=self.paper_type_var.get(),
            bleed_mm=self.bleed_var.get(),
            dpi=self.dpi_var.get(),
            spine_text=self.spine_text_var.get(),
            spine_text_color=self.spine_text_color_var.get(),
            spine_text_size_pt=self.spine_text_size_var.get(),
            spine_text_vertical=self.spine_text_vertical_var.get(),
            spine_bg_color=self.spine_bg_color_var.get() if self.use_custom_spine_bg_var.get() else None,
            draw_crop_marks=self.draw_crop_marks_var.get(),
            draw_fold_lines=self.draw_fold_lines_var.get(),
            draw_info_text=self.draw_info_text_var.get(),
            fill_mode=self.fill_mode_var.get(),
            front_edit=front_edit,
            back_edit=back_edit
        )

    def update_preview(self):
        try:
            cfg = self._get_config()
            preview_cfg = CoverConfig(**{**cfg.__dict__, "dpi": 100})
            engine = CoverEngine(preview_cfg)
            self.current_preview_image = engine.generate_spread(
                self.front_cover_path.get(),
                self.back_cover_path.get()
            )
            self._render_preview_on_canvas()
        except Exception as e:
            messagebox.showerror("计算错误", f"生成预览时出错: {str(e)}")

    def _render_preview_on_canvas(self):
        if self.current_preview_image is None:
            return

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()

        if cw <= 10 or ch <= 10:
            return

        img = self.current_preview_image
        iw, ih = img.size

        scale = min((cw - 20) / iw, (ch - 20) / ih)
        nw = max(1, int(iw * scale))
        nh = max(1, int(ih * scale))

        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        self.tk_preview_image = ImageTk.PhotoImage(resized)

        self.preview_canvas.delete("all")
        cx = cw // 2
        cy = ch // 2
        self.preview_canvas.create_image(cx, cy, image=self.tk_preview_image)

    def export_image(self):
        try:
            cfg = self._get_config()
            save_path = filedialog.asksaveasfilename(
                title="导出高清晰封面图片",
                defaultextension=".png",
                filetypes=[("PNG图片 (*.png)", "*.png"), ("JPEG图片 (*.jpg)", "*.jpg")]
            )
            if not save_path:
                return

            engine = CoverEngine(cfg)
            high_res_img = engine.generate_spread(
                self.front_cover_path.get(),
                self.back_cover_path.get()
            )
            high_res_img.save(save_path, dpi=(cfg.dpi, cfg.dpi))
            messagebox.showinfo("导出成功", f"封面拼版已成功保存至:\n{save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出图片时发生错误:\n{str(e)}")

    def export_pdf(self):
        try:
            cfg = self._get_config()
            save_path = filedialog.asksaveasfilename(
                title="导出 1:1 矢量 PDF 文件",
                defaultextension=".pdf",
                filetypes=[("PDF文件 (*.pdf)", "*.pdf")]
            )
            if not save_path:
                return

            engine = CoverEngine(cfg)
            high_res_img = engine.generate_spread(
                self.front_cover_path.get(),
                self.back_cover_path.get()
            )
            engine.export_pdf(save_path, high_res_img)
            messagebox.showinfo("导出成功", f"PDF文件已成功生成至:\n{save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出PDF时发生错误:\n{str(e)}")


def main():
    root = tk.Tk()
    app = BookCoverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
