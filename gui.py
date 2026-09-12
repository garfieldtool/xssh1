"""
GUI Interface for Windows Book Cover Generator Tool.
Built with Tkinter for lightweight desktop compatibility.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk

from cover_engine import CoverConfig, CoverEngine, PAPER_SIZES_MM, BOOK_SIZES_MM


class BookCoverApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("A3 / A4 打印店专业书籍封面拼版生成工具 v1.0")
        self.root.geometry("1100x720")
        self.root.minsize(950, 650)

        # File paths
        self.front_cover_path = tk.StringVar()
        self.back_cover_path = tk.StringVar()

        # Config variables
        self.paper_preset_var = tk.StringVar(value="A3")
        self.paper_width_var = tk.DoubleVar(value=420.0)
        self.paper_height_var = tk.DoubleVar(value=297.0)

        self.book_preset_var = tk.StringVar(value="A5")
        self.book_width_var = tk.DoubleVar(value=148.0)
        self.book_height_var = tk.DoubleVar(value=210.0)

        self.spine_width_var = tk.DoubleVar(value=10.0)
        self.bleed_var = tk.DoubleVar(value=3.0)
        self.dpi_var = tk.IntVar(value=300)

        self.spine_text_var = tk.StringVar(value="")
        self.spine_text_color_var = tk.StringVar(value="#000000")
        self.spine_text_size_var = tk.IntVar(value=14)
        self.spine_text_vertical_var = tk.BooleanVar(value=True)
        self.spine_bg_color_var = tk.StringVar(value="#FFFFFF")
        self.use_custom_spine_bg_var = tk.BooleanVar(value=False)

        self.draw_crop_marks_var = tk.BooleanVar(value=True)
        self.draw_fold_lines_var = tk.BooleanVar(value=True)
        self.draw_info_text_var = tk.BooleanVar(value=True)
        self.fill_mode_var = tk.StringVar(value="fit")

        # Preview image cache
        self.current_preview_image = None
        self.tk_preview_image = None

        self._build_ui()
        self._on_paper_preset_change()
        self._on_book_preset_change()
        self.update_preview()

    def _build_ui(self):
        # Main layout: Left panel (Settings), Right panel (Preview)
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left control frame
        left_frame = ttk.Frame(main_paned, width=380)
        main_paned.add(left_frame, weight=0)

        # Right preview frame
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # --- Left Scrollable Control Notebook / Sections ---
        canvas_scroll = tk.Canvas(left_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas_scroll.yview)
        scroll_content = ttk.Frame(canvas_scroll)

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )

        canvas_scroll.create_window((0, 0), window=scroll_content, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)

        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 1. File Selection Section
        file_lf = ttk.LabelFrame(scroll_content, text=" 1. 封面图片选择 ", padding=10)
        file_lf.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(file_lf, text="正面封面 (Front):").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(file_lf, textvariable=self.front_cover_path, width=25).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(file_lf, text="浏览...", command=self._browse_front_cover).grid(row=0, column=2, pady=2)

        ttk.Label(file_lf, text="背面封面 (Back):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(file_lf, textvariable=self.back_cover_path, width=25).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(file_lf, text="浏览...", command=self._browse_back_cover).grid(row=1, column=2, pady=2)

        # 2. Paper & Dimensions Section
        dim_lf = ttk.LabelFrame(scroll_content, text=" 2. 纸张与成书尺寸 (毫米 mm) ", padding=10)
        dim_lf.pack(fill=tk.X, padx=5, pady=5)

        # Paper preset
        ttk.Label(dim_lf, text="打印纸张规格:").grid(row=0, column=0, sticky="w", pady=2)
        paper_cb = ttk.Combobox(
            dim_lf, textvariable=self.paper_preset_var,
            values=list(PAPER_SIZES_MM.keys()) + ["自定义"], state="readonly", width=12
        )
        paper_cb.grid(row=0, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        paper_cb.bind("<<ComboboxSelected>>", lambda e: self._on_paper_preset_change())

        ttk.Label(dim_lf, text="纸张尺寸 (W x H):").grid(row=1, column=0, sticky="w", pady=2)
        f_paper = ttk.Frame(dim_lf)
        f_paper.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Entry(f_paper, textvariable=self.paper_width_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_paper, text=" x ").pack(side=tk.LEFT)
        ttk.Entry(f_paper, textvariable=self.paper_height_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_paper, text=" mm").pack(side=tk.LEFT)

        # Book preset
        ttk.Label(dim_lf, text="成品书籍规格:").grid(row=2, column=0, sticky="w", pady=2)
        book_cb = ttk.Combobox(
            dim_lf, textvariable=self.book_preset_var,
            values=list(BOOK_SIZES_MM.keys()) + ["自定义"], state="readonly", width=12
        )
        book_cb.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        book_cb.bind("<<ComboboxSelected>>", lambda e: self._on_book_preset_change())

        ttk.Label(dim_lf, text="单面尺寸 (W x H):").grid(row=3, column=0, sticky="w", pady=2)
        f_book = ttk.Frame(dim_lf)
        f_book.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Entry(f_book, textvariable=self.book_width_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_book, text=" x ").pack(side=tk.LEFT)
        ttk.Entry(f_book, textvariable=self.book_height_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_book, text=" mm").pack(side=tk.LEFT)

        # Spine width & Bleed
        ttk.Label(dim_lf, text="书脊厚度 (Spine):").grid(row=4, column=0, sticky="w", pady=2)
        f_spine = ttk.Frame(dim_lf)
        f_spine.grid(row=4, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Entry(f_spine, textvariable=self.spine_width_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_spine, text=" mm").pack(side=tk.LEFT)

        ttk.Label(dim_lf, text="出血边距 (Bleed):").grid(row=5, column=0, sticky="w", pady=2)
        f_bleed = ttk.Frame(dim_lf)
        f_bleed.grid(row=5, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Entry(f_bleed, textvariable=self.bleed_var, width=6).pack(side=tk.LEFT)
        ttk.Label(f_bleed, text=" mm (标准3mm)").pack(side=tk.LEFT)

        ttk.Label(dim_lf, text="打印分辨率 (DPI):").grid(row=6, column=0, sticky="w", pady=2)
        ttk.Combobox(
            dim_lf, textvariable=self.dpi_var,
            values=[150, 300, 600], state="readonly", width=8
        ).grid(row=6, column=1, columnspan=2, sticky="w", padx=5, pady=2)

        # 3. Spine Options Section
        spine_lf = ttk.LabelFrame(scroll_content, text=" 3. 书脊文字与背景 ", padding=10)
        spine_lf.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(spine_lf, text="书脊书名:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(spine_lf, textvariable=self.spine_text_var, width=22).grid(row=0, column=1, columnspan=2, sticky="w", padx=5, pady=2)

        ttk.Label(spine_lf, text="文字方向:").grid(row=1, column=0, sticky="w", pady=2)
        f_orient = ttk.Frame(spine_lf)
        f_orient.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=2)
        ttk.Radiobutton(f_orient, text="竖排 (直书)", variable=self.spine_text_vertical_var, value=True).pack(side=tk.LEFT)
        ttk.Radiobutton(f_orient, text="横排 (旋转)", variable=self.spine_text_vertical_var, value=False).pack(side=tk.LEFT)

        ttk.Label(spine_lf, text="字号大小 (pt):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Spinbox(spine_lf, from_=8, to=72, textvariable=self.spine_text_size_var, width=6).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(spine_lf, text="文字颜色:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Button(spine_lf, text="选择颜色", command=self._choose_text_color).grid(row=3, column=1, sticky="w", padx=5, pady=2)

        ttk.Checkbutton(spine_lf, text="自定义书脊底色", variable=self.use_custom_spine_bg_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Button(spine_lf, text="选择底色", command=self._choose_spine_bg_color).grid(row=4, column=2, sticky="w", pady=2)

        # 4. Printing & Print Shop Marks Section
        mark_lf = ttk.LabelFrame(scroll_content, text=" 4. 打印店角线与印前设置 ", padding=10)
        mark_lf.pack(fill=tk.X, padx=5, pady=5)

        ttk.Checkbutton(mark_lf, text="绘制裁切角线 (Crop Marks)", variable=self.draw_crop_marks_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(mark_lf, text="绘制书脊折痕虚线 (Fold Lines)", variable=self.draw_fold_lines_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(mark_lf, text="打印版本标注信息 (Job Info)", variable=self.draw_info_text_var).pack(anchor="w", pady=2)

        ttk.Label(mark_lf, text="图片填充方式:").pack(anchor="w", pady=(5, 2))
        f_mode = ttk.Frame(mark_lf)
        f_mode.pack(anchor="w")
        ttk.Radiobutton(f_mode, text="保持比例 (Fit)", variable=self.fill_mode_var, value="fit").pack(side=tk.LEFT)
        ttk.Radiobutton(f_mode, text="裁剪填充 (Fill)", variable=self.fill_mode_var, value="fill").pack(side=tk.LEFT)
        ttk.Radiobutton(f_mode, text="拉伸适应 (Stretch)", variable=self.fill_mode_var, value="stretch").pack(side=tk.LEFT)

        # Action Buttons
        btn_frame = ttk.Frame(scroll_content, padding=10)
        btn_frame.pack(fill=tk.X, padx=5, pady=10)

        ttk.Button(btn_frame, text="刷新预览 (Refresh)", command=self.update_preview, width=18).pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="导出高清图片 (Export Image)", command=self.export_image, width=18).pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="导出 PDF (Export PDF)", command=self.export_pdf, width=18).pack(fill=tk.X, pady=3)

        # --- Right Preview Canvas Area ---
        preview_lf = ttk.LabelFrame(right_frame, text=" 拼版实时预览 (A3 Spread Preview) ", padding=10)
        preview_lf.pack(fill=tk.BOTH, expand=True)

        self.preview_canvas = tk.Canvas(preview_lf, bg="#404040", borderwidth=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", lambda e: self._render_preview_on_canvas())

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

    def _choose_text_color(self):
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

    def _get_config(self) -> CoverConfig:
        return CoverConfig(
            paper_width_mm=self.paper_width_var.get(),
            paper_height_mm=self.paper_height_var.get(),
            book_width_mm=self.book_width_var.get(),
            book_height_mm=self.book_height_var.get(),
            spine_width_mm=self.spine_width_var.get(),
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
        )

    def update_preview(self):
        try:
            cfg = self._get_config()
            # Generate spread using low DPI (e.g. 100 DPI) for fast preview responsiveness
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
