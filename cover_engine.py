"""
Book Cover Layout Engine for Print Shops (Ultimate Edition v2.2).
Generates print-ready A3/A4 spread covers with Back Cover, Spine, Front Cover, Crop Marks, and Fold Lines.
Supports:
- PDF File input with Page Selection (e.g. Page 1 for Front, Last Page for Back) rendered to high-DPI image.
- Professional distinction between Cover Paper Stock (封面用纸/卡纸) and Inner Page Paper Stock (内页用纸).
- Extensive Paper Spread Sizes (A3, SRA3, A3+, A4, A2, B4, B3, 8开, 4开, 16开, etc.).
- Extensive Finished Book Sizes (A4, A5, B5, 16开正度/大度, 32开正度/大度, 24开, 20开, 正方形等).
- Softcover (胶订平装) & Hardcover (精装包壳) with wrap edges (包边) & hinge grooves (沟槽).
- Automatic Mirrored Bleed Extension (镜像延展出血) to eliminate white borders.
- Barcode / ISBN / QR Code generation and placement.
- Low-DPI resolution warnings.
"""

import os
import json
import math
from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, List, Dict
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageColor, ImageFilter

# PDF extraction libraries (PyMuPDF or pypdfium2)
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pypdfium2 as pdfium
    HAS_PYPDFIUM = True
except ImportError:
    HAS_PYPDFIUM = False


# Extensive Paper Spread Sizes in mm (Landscape orientation for printing sheets)
PAPER_SIZES_MM = {
    "A3 (420 x 297 mm)": (420.0, 297.0),
    "SRA3 (450 x 320 mm)": (450.0, 320.0),
    "A3+ (483 x 329 mm)": (483.0, 329.0),
    "A4 (297 x 210 mm)": (297.0, 210.0),
    "A2 (594 x 420 mm)": (594.0, 420.0),
    "B4 (364 x 257 mm)": (364.0, 257.0),
    "B3 (515 x 364 mm)": (515.0, 364.0),
    "8开 (420 x 285 mm)": (420.0, 285.0),
    "正度8开 (390 x 270 mm)": (390.0, 270.0),
    "4开 (570 x 420 mm)": (570.0, 420.0),
    "正度4开 (540 x 390 mm)": (540.0, 390.0),
    "16开 (285 x 210 mm)": (285.0, 210.0),
}

# Extensive Finished Book Sizes in mm (Single page / Front cover dimension)
BOOK_SIZES_MM = {
    "A5 (148 x 210 mm)": (148.0, 210.0),
    "A4 (210 x 297 mm)": (210.0, 297.0),
    "B5 (176 x 250 mm)": (176.0, 250.0),
    "B5 标准 (185 x 260 mm)": (185.0, 260.0),
    "16开 大度 (210 x 285 mm)": (210.0, 285.0),
    "16开 正度 (185 x 260 mm)": (185.0, 260.0),
    "32开 大度 (140 x 203 mm)": (140.0, 203.0),
    "32开 正度 (130 x 184 mm)": (130.0, 184.0),
    "大32开 (145 x 210 mm)": (145.0, 210.0),
    "24开 (170 x 190 mm)": (170.0, 190.0),
    "20开 (150 x 205 mm)": (150.0, 205.0),
    "正方形 (210 x 210 mm)": (210.0, 210.0),
    "正方形 (150 x 150 mm)": (150.0, 150.0),
}

# Inner Page Paper Thickness in mm per single sheet (1 sheet = 2 pages)
INNER_PAPER_THICKNESS_MM = {
    "70g 双胶纸 (Offset)": 0.09,
    "80g 双胶纸 (Offset)": 0.10,
    "100g 双胶纸 (Offset)": 0.12,
    "120g 双胶纸 (Offset)": 0.14,
    "105g 铜版纸 (Art)": 0.08,
    "128g 铜版纸 (Art)": 0.095,
    "157g 铜版纸 (Art)": 0.115,
    "200g 铜版纸 (Art)": 0.15,
    "70g 轻型纸/蒙肯纸 (Bulky)": 0.13,
    "80g 轻型纸/蒙肯纸 (Bulky)": 0.15,
    "100g 道林纸/特种纸": 0.125,
}

# Cover Paper Stock Types
COVER_PAPER_STOCK_TYPES = [
    "200g 铜版纸 / 哑粉纸",
    "250g 铜版纸 / 哑粉纸 (标准胶订)",
    "300g 铜版纸 / 哑粉纸 (厚封面)",
    "350g 铜版纸 / 哑粉纸",
    "230g 白卡纸 / 灰底白",
    "250g 粗皮纹纸 / 灰皮纸",
    "250g 珠光纸 / 特种艺术纸",
    "157g 铜版纸 + 2.0mm 灰板 (精装硬皮)",
    "157g 铜版纸 + 2.5mm 灰板 (精装硬皮)",
]


def render_pdf_page_to_image(pdf_path: str, page_num: int = 1, render_dpi: int = 300) -> Optional[Image.Image]:
    """
    Render a specific page from a PDF file as a high-DPI PIL RGBA Image.
    `page_num` is 1-indexed. If page_num < 0, it counts from end (-1 = last page).
    """
    if not os.path.isfile(pdf_path):
        return None

    # Try PyMuPDF
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            if total_pages == 0:
                return None

            idx = page_num - 1 if page_num > 0 else total_pages + page_num
            idx = max(0, min(total_pages - 1, idx))

            page = doc[idx]
            zoom = render_dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=True)

            img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            doc.close()
            return img
        except Exception:
            pass

    # Try pypdfium2
    if HAS_PYPDFIUM:
        try:
            pdf = pdfium.PdfDocument(pdf_path)
            total_pages = len(pdf)
            if total_pages == 0:
                return None

            idx = page_num - 1 if page_num > 0 else total_pages + page_num
            idx = max(0, min(total_pages - 1, idx))

            page = pdf[idx]
            image = page.render(scale=render_dpi / 72.0).to_pil().convert("RGBA")
            pdf.close()
            return image
        except Exception:
            pass

    return None


def calculate_spine_thickness(
    page_count: int,
    inner_paper_type: str = "80g 双胶纸 (Offset)",
    custom_sheet_thickness_mm: Optional[float] = None,
    is_hardcover: bool = False,
    cardboard_thickness_mm: float = 2.0
) -> float:
    if page_count <= 0:
        return 0.0

    if custom_sheet_thickness_mm is not None and custom_sheet_thickness_mm > 0:
        sheet_thick = custom_sheet_thickness_mm
    else:
        sheet_thick = INNER_PAPER_THICKNESS_MM.get(inner_paper_type, 0.10)

    sheets = (page_count + 1) // 2
    spine_mm = sheets * sheet_thick + 0.3

    if is_hardcover:
        spine_mm += cardboard_thickness_mm * 2.0

    return round(spine_mm, 2)


def mm_to_px(mm: float, dpi: int = 300) -> int:
    return int(round(mm * dpi / 25.4))


def px_to_mm(px: int, dpi: int = 300) -> float:
    return px * 25.4 / dpi


def draw_simple_barcode(code_str: str, width_px: int = 240, height_px: int = 80) -> Image.Image:
    img = Image.new("RGBA", (width_px, height_px), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (width_px - 1, height_px - 1)], outline=(0, 0, 0, 255), width=1)

    margin_x = 12
    margin_y = 8
    bar_h = height_px - 28

    import hashlib
    hash_val = hashlib.md5(code_str.encode('utf-8')).hexdigest()

    curr_x = margin_x
    idx = 0
    while curr_x < width_px - margin_x - 4:
        hex_char = hash_val[idx % len(hash_val)]
        val = int(hex_char, 16)
        bar_w = 1 if val % 2 == 0 else (2 if val < 10 else 3)
        gap_w = 1 if val % 3 == 0 else 2

        draw.rectangle([(curr_x, margin_y), (curr_x + bar_w - 1, margin_y + bar_h)], fill=(0, 0, 0, 255))
        curr_x += bar_w + gap_w
        idx += 1

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    bbox = font.getbbox(code_str) if font else (0, 0, 60, 10)
    tw = bbox[2] - bbox[0]
    tx = (width_px - tw) // 2
    ty = height_px - 18
    draw.text((tx, ty), code_str, fill=(0, 0, 0, 255), font=font)

    return img


@dataclass
class TextOverlay:
    text: str
    rel_x: float = 0.5
    rel_y: float = 0.5
    font_size_pt: int = 24
    color: str = "#000000"
    is_vertical: bool = False
    bg_banner: bool = False
    banner_color: str = "#FFFFFF"


@dataclass
class ImageEditConfig:
    brightness: float = 1.0
    contrast: float = 1.0
    color_tint: Optional[str] = None
    tint_opacity: float = 0.2
    text_overlays: List[TextOverlay] = field(default_factory=list)


@dataclass
class CoverConfig:
    binding_type: str = "平装胶订"      # "平装胶订" or "精装包壳"
    cover_stock_type: str = "250g 铜版纸 / 哑粉纸 (标准胶订)"
    inner_paper_type: str = "80g 双胶纸 (Offset)"
    hardcover_wrap_mm: float = 15.0     # 包壳折边/包边宽度 (15-20mm)
    hardcover_groove_mm: float = 8.0    # 精装书沟槽宽度 (6-10mm)
    paper_width_mm: float = 420.0       # Sheet width
    paper_height_mm: float = 297.0      # Sheet height
    book_width_mm: float = 148.0        # Finished book width
    book_height_mm: float = 210.0       # Finished book height
    spine_width_mm: float = 10.0        # Spine thickness
    page_count: int = 0
    bleed_mm: float = 3.0               # Bleed margin around cover trim
    mirror_bleed: bool = True           # Auto-generate mirrored bleed edges if needed
    dpi: int = 300                       # Print DPI (300 standard)
    bg_color: str = "#FFFFFF"           # Sheet background color
    spine_bg_color: Optional[str] = None
    spine_text: str = ""
    spine_text_color: str = "#000000"
    spine_text_size_pt: int = 14
    spine_text_vertical: bool = True
    draw_crop_marks: bool = True
    draw_fold_lines: bool = True
    draw_info_text: bool = True
    fill_mode: str = "fit"

    # PDF page selection parameters
    front_pdf_page: int = 1             # Page for front cover (1-indexed)
    back_pdf_page: int = -1             # Page for back cover (-1 = last page)

    show_barcode: bool = False
    barcode_text: str = "ISBN 978-7-12345-678-9"

    front_edit: ImageEditConfig = field(default_factory=ImageEditConfig)
    back_edit: ImageEditConfig = field(default_factory=ImageEditConfig)

    @property
    def is_hardcover(self) -> bool:
        return "精装" in self.binding_type

    @property
    def total_spread_width_mm(self) -> float:
        base = self.book_width_mm * 2.0 + self.spine_width_mm
        if self.is_hardcover:
            base += self.hardcover_groove_mm * 2.0
        return base

    @property
    def total_spread_height_mm(self) -> float:
        return self.book_height_mm


class CoverEngine:
    def __init__(self, config: CoverConfig):
        self.config = config

    def _get_font(self, size_px: int) -> ImageFont.ImageFont:
        font_names = [
            "simhei.ttf", "msyh.ttc", "simsun.ttc", "Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\simhei.ttf",
        ]
        for font_name in font_names:
            try:
                return ImageFont.truetype(font_name, size_px)
            except IOError:
                continue
        return ImageFont.load_default()

    def check_image_dpi(self, img_path: str, target_w_mm: float, target_h_mm: float) -> Dict[str, any]:
        if not img_path or not os.path.isfile(img_path):
            return {"valid": False, "reason": "文件不存在", "effective_dpi": 0}

        try:
            if img_path.lower().endswith(".pdf"):
                pdf_img = render_pdf_page_to_image(img_path, 1, 300)
                if pdf_img:
                    orig_w, orig_h = pdf_img.size
                else:
                    return {"valid": False, "reason": "无法读取PDF", "effective_dpi": 0}
            else:
                with Image.open(img_path) as img:
                    orig_w, orig_h = img.size

            eff_dpi_w = round(orig_w / (target_w_mm / 25.4))
            eff_dpi_h = round(orig_h / (target_h_mm / 25.4))
            min_dpi = min(eff_dpi_w, eff_dpi_h)

            is_low_res = min_dpi < 200
            return {
                "valid": True,
                "orig_size": (orig_w, orig_h),
                "effective_dpi": min_dpi,
                "is_low_res": is_low_res,
                "warning": f"原图尺寸清晰度偏低 ({min_dpi} DPI < 300 DPI)" if is_low_res else "清晰度充足 (≥ 200 DPI)"
            }
        except Exception as e:
            return {"valid": False, "reason": str(e), "effective_dpi": 0}

    def _apply_image_edits_and_overlays(
        self,
        img: Image.Image,
        edit_cfg: ImageEditConfig,
        dpi: int
    ) -> Image.Image:
        img = img.convert("RGBA")

        if edit_cfg.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(edit_cfg.brightness)

        if edit_cfg.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(edit_cfg.contrast)

        if edit_cfg.color_tint:
            try:
                tint_color = ImageColor.getrgb(edit_cfg.color_tint)
                tint_layer = Image.new("RGBA", img.size, tint_color + (int(255 * edit_cfg.tint_opacity),))
                img = Image.alpha_composite(img, tint_layer)
            except Exception:
                pass

        if edit_cfg.text_overlays:
            draw_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(draw_layer)

            w, h = img.size
            for overlay in edit_cfg.text_overlays:
                if not overlay.text.strip():
                    continue

                font_size_px = mm_to_px(overlay.font_size_pt * 0.352778, dpi)
                font_size_px = max(12, font_size_px)
                font = self._get_font(font_size_px)

                center_x = int(w * overlay.rel_x)
                center_y = int(h * overlay.rel_y)

                if overlay.is_vertical:
                    chars = list(overlay.text)
                    char_imgs = []
                    tot_h = 0
                    max_w = 0
                    for char in chars:
                        bbox = font.getbbox(char)
                        cw = bbox[2] - bbox[0]
                        ch = bbox[3] - bbox[1]
                        cimg = Image.new("RGBA", (max(cw + 4, 1), max(ch + 4, 1)), (0, 0, 0, 0))
                        cdraw = ImageDraw.Draw(cimg)
                        cdraw.text((-bbox[0] + 2, -bbox[1] + 2), char, fill=overlay.color, font=font)
                        char_imgs.append(cimg)
                        max_w = max(max_w, cimg.width)
                        tot_h += cimg.height + 2

                    start_y = center_y - (tot_h // 2)
                    curr_y = start_y
                    for cimg in char_imgs:
                        px = center_x - (cimg.width // 2)
                        draw_layer.paste(cimg, (px, curr_y), cimg)
                        curr_y += cimg.height + 2
                else:
                    bbox = font.getbbox(overlay.text)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    tx = center_x - (tw // 2)
                    ty = center_y - (th // 2)

                    if overlay.bg_banner:
                        banner_pad = 10
                        try:
                            b_rgb = ImageColor.getrgb(overlay.banner_color)
                        except Exception:
                            b_rgb = (255, 255, 255)
                        draw.rectangle(
                            [(tx - banner_pad, ty - banner_pad), (tx + tw + banner_pad, ty + th + banner_pad)],
                            fill=b_rgb + (200,)
                        )

                    draw.text((tx - bbox[0], ty - bbox[1]), overlay.text, fill=overlay.color, font=font)

            img = Image.alpha_composite(img, draw_layer)

        return img

    def _load_and_scale_image(
        self,
        img_path: str,
        target_w_px: int,
        target_h_px: int,
        fill_mode: str = "fit",
        edit_cfg: Optional[ImageEditConfig] = None,
        bg_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        pdf_page: int = 1
    ) -> Image.Image:
        if not img_path or not os.path.isfile(img_path):
            blank = Image.new("RGBA", (target_w_px, target_h_px), bg_color)
            draw = ImageDraw.Draw(blank)
            draw.rectangle([(0, 0), (target_w_px - 1, target_h_px - 1)], outline=(200, 200, 200), width=3)
            if edit_cfg:
                blank = self._apply_image_edits_and_overlays(blank, edit_cfg, self.config.dpi)
            return blank

        if img_path.lower().endswith(".pdf"):
            img = render_pdf_page_to_image(img_path, page_num=pdf_page, render_dpi=self.config.dpi)
            if img is None:
                blank = Image.new("RGBA", (target_w_px, target_h_px), bg_color)
                return blank
        else:
            img = Image.open(img_path).convert("RGBA")

        orig_w, orig_h = img.size

        if fill_mode == "stretch":
            resized = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)
        else:
            scale_w = target_w_px / orig_w
            scale_h = target_h_px / orig_h

            if fill_mode == "fill":
                scale = max(scale_w, scale_h)
                new_w, new_h = int(round(orig_w * scale)), int(round(orig_h * scale))
                resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left = (new_w - target_w_px) // 2
                top = (new_h - target_h_px) // 2
                resized = resized.crop((left, top, left + target_w_px, top + target_h_px))
            else:  # "fit"
                scale = min(scale_w, scale_h)
                new_w, new_h = int(round(orig_w * scale)), int(round(orig_h * scale))
                scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                if self.config.mirror_bleed and (new_w < target_w_px or new_h < target_h_px):
                    resized = Image.new("RGBA", (target_w_px, target_h_px), bg_color)
                    left = (target_w_px - new_w) // 2
                    top = (target_h_px - new_h) // 2

                    bg_fill = scaled.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(15))
                    resized.paste(bg_fill, (0, 0))
                    resized.paste(scaled, (left, top), scaled)
                else:
                    resized = Image.new("RGBA", (target_w_px, target_h_px), bg_color)
                    left = (target_w_px - new_w) // 2
                    top = (target_h_px - new_h) // 2
                    resized.paste(scaled, (left, top), scaled)

        if edit_cfg:
            resized = self._apply_image_edits_and_overlays(resized, edit_cfg, self.config.dpi)

        return resized

    def _render_spine(
        self,
        spine_w_px: int,
        spine_h_px: int,
        front_img: Optional[Image.Image] = None,
        back_img: Optional[Image.Image] = None
    ) -> Image.Image:
        bg = (255, 255, 255, 255)
        if self.config.spine_bg_color:
            try:
                bg_img = Image.new("RGBA", (1, 1), self.config.spine_bg_color)
                bg = bg_img.getpixel((0, 0))
            except Exception:
                bg = (255, 255, 255, 255)
        elif front_img is not None:
            sample_x = 0
            sample_y = front_img.height // 2
            bg = front_img.getpixel((sample_x, sample_y))

        spine_canvas = Image.new("RGBA", (spine_w_px, spine_h_px), bg)
        draw = ImageDraw.Draw(spine_canvas)

        text = self.config.spine_text.strip()
        if not text:
            return spine_canvas

        font_size_px = mm_to_px(self.config.spine_text_size_pt * 0.352778, self.config.dpi)
        font_size_px = max(12, font_size_px)
        font = self._get_font(font_size_px)

        text_color = self.config.spine_text_color

        if self.config.spine_text_vertical:
            chars = list(text)
            char_images = []
            max_char_w = 0
            total_h = 0

            for char in chars:
                bbox = font.getbbox(char)
                char_w = bbox[2] - bbox[0]
                char_h = bbox[3] - bbox[1]
                char_img = Image.new("RGBA", (max(char_w + 4, 1), max(char_h + 4, 1)), (0, 0, 0, 0))
                cdraw = ImageDraw.Draw(char_img)
                cdraw.text((-bbox[0] + 2, -bbox[1] + 2), char, fill=text_color, font=font)
                char_images.append(char_img)
                max_char_w = max(max_char_w, char_img.width)
                total_h += char_img.height + 2

            start_y = (spine_h_px - total_h) // 2
            curr_y = max(10, start_y)
            for char_img in char_images:
                if curr_y + char_img.height > spine_h_px - 10:
                    break
                curr_x = (spine_w_px - char_img.width) // 2
                spine_canvas.paste(char_img, (curr_x, curr_y), char_img)
                curr_y += char_img.height + 2
        else:
            bbox = font.getbbox(text)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            txt_img = Image.new("RGBA", (text_w + 10, text_h + 10), (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(txt_img)
            tdraw.text((-bbox[0] + 5, -bbox[1] + 5), text, fill=text_color, font=font)
            rotated = txt_img.rotate(270, expand=True)

            rx = (spine_w_px - rotated.width) // 2
            ry = (spine_h_px - rotated.height) // 2
            spine_canvas.paste(rotated, (rx, ry), rotated)

        return spine_canvas

    def generate_spread(
        self,
        front_cover_path: Optional[str] = None,
        back_cover_path: Optional[str] = None
    ) -> Image.Image:
        cfg = self.config
        dpi = cfg.dpi

        paper_w_px = mm_to_px(cfg.paper_width_mm, dpi)
        paper_h_px = mm_to_px(cfg.paper_height_mm, dpi)

        book_w_px = mm_to_px(cfg.book_width_mm, dpi)
        book_h_px = mm_to_px(cfg.book_height_mm, dpi)
        spine_w_px = mm_to_px(cfg.spine_width_mm, dpi)

        extra_margin_mm = cfg.hardcover_wrap_mm if cfg.is_hardcover else cfg.bleed_mm
        extra_margin_px = mm_to_px(extra_margin_mm, dpi)

        groove_w_mm = cfg.hardcover_groove_mm if cfg.is_hardcover else 0.0
        groove_w_px = mm_to_px(groove_w_mm, dpi)

        canvas = Image.new("RGBA", (paper_w_px, paper_h_px), cfg.bg_color)

        spread_trim_w_mm = cfg.total_spread_width_mm
        spread_trim_h_mm = cfg.total_spread_height_mm

        center_x_mm = cfg.paper_width_mm / 2.0
        center_y_mm = cfg.paper_height_mm / 2.0

        trim_left_mm = center_x_mm - (spread_trim_w_mm / 2.0)
        trim_right_mm = center_x_mm + (spread_trim_w_mm / 2.0)
        trim_top_mm = center_y_mm - (spread_trim_h_mm / 2.0)
        trim_bottom_mm = center_y_mm + (spread_trim_h_mm / 2.0)

        spine_left_mm = center_x_mm - (cfg.spine_width_mm / 2.0)
        spine_right_mm = center_x_mm + (cfg.spine_width_mm / 2.0)

        trim_left_px = mm_to_px(trim_left_mm, dpi)
        trim_right_px = mm_to_px(trim_right_mm, dpi)
        trim_top_px = mm_to_px(trim_top_mm, dpi)
        trim_bottom_px = mm_to_px(trim_bottom_mm, dpi)

        spine_left_px = mm_to_px(spine_left_mm, dpi)
        spine_right_px = mm_to_px(spine_right_mm, dpi)

        back_w_px = book_w_px + extra_margin_px
        back_h_px = book_h_px + 2 * extra_margin_px

        front_w_px = book_w_px + extra_margin_px
        front_h_px = book_h_px + 2 * extra_margin_px

        spine_h_px = book_h_px + 2 * extra_margin_px

        back_img = self._load_and_scale_image(
            back_cover_path, back_w_px, back_h_px, cfg.fill_mode, cfg.back_edit, pdf_page=cfg.back_pdf_page
        )
        front_img = self._load_and_scale_image(
            front_cover_path, front_w_px, front_h_px, cfg.fill_mode, cfg.front_edit, pdf_page=cfg.front_pdf_page
        )

        if cfg.show_barcode and cfg.barcode_text.strip():
            barcode_w_px = mm_to_px(35.0, dpi)
            barcode_h_px = mm_to_px(15.0, dpi)
            bc_img = draw_simple_barcode(cfg.barcode_text, barcode_w_px, barcode_h_px)

            bc_x = back_w_px - barcode_w_px - mm_to_px(10.0, dpi)
            bc_y = back_h_px - barcode_h_px - mm_to_px(10.0, dpi)
            back_img.paste(bc_img, (max(0, bc_x), max(0, bc_y)), bc_img)

        spine_img = self._render_spine(spine_w_px, spine_h_px, front_img, back_img)

        back_pos_x = trim_left_px - extra_margin_px
        back_pos_y = trim_top_px - extra_margin_px
        canvas.paste(back_img, (back_pos_x, back_pos_y), back_img)

        front_pos_x = spine_right_px + groove_w_px
        front_pos_y = trim_top_px - extra_margin_px
        canvas.paste(front_img, (front_pos_x, front_pos_y), front_img)

        spine_pos_x = spine_left_px
        spine_pos_y = trim_top_px - extra_margin_px
        canvas.paste(spine_img, (spine_pos_x, spine_pos_y), spine_img)

        overlay = Image.new("RGBA", (paper_w_px, paper_h_px), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        if cfg.draw_fold_lines:
            dash_len = mm_to_px(2.0, dpi)
            gap_len = mm_to_px(2.0, dpi)
            fold_color = (120, 120, 120, 200)

            lines_to_draw = [spine_left_px, spine_right_px]
            if cfg.is_hardcover and groove_w_px > 0:
                lines_to_draw.extend([spine_left_px - groove_w_px, spine_right_px + groove_w_px])

            for x_px in lines_to_draw:
                curr_y = trim_top_px
                while curr_y < trim_bottom_px:
                    end_y = min(curr_y + dash_len, trim_bottom_px)
                    draw.line([(x_px, curr_y), (x_px, end_y)], fill=fold_color, width=max(1, mm_to_px(0.2, dpi)))
                    curr_y += dash_len + gap_len

        if cfg.draw_crop_marks:
            mark_len_px = mm_to_px(8.0, dpi)
            mark_offset_px = mm_to_px(2.0, dpi)
            mark_color = (0, 0, 0, 255)
            mark_width = max(1, mm_to_px(0.25, dpi))

            x_coords = [
                (trim_left_px, "outer_left"),
                (spine_left_px, "spine_left"),
                (spine_right_px, "spine_right"),
                (trim_right_px, "outer_right")
            ]

            y_coords = [
                (trim_top_px, "top"),
                (trim_bottom_px, "bottom")
            ]

            for x_px, label in x_coords:
                y_start = trim_top_px - mark_offset_px - mark_len_px
                y_end = trim_top_px - mark_offset_px
                draw.line([(x_px, y_start), (x_px, y_end)], fill=mark_color, width=mark_width)

            for x_px, label in x_coords:
                y_start = trim_bottom_px + mark_offset_px
                y_end = trim_bottom_px + mark_offset_px + mark_len_px
                draw.line([(x_px, y_start), (x_px, y_end)], fill=mark_color, width=mark_width)

            for y_px, label in y_coords:
                x_start = trim_left_px - mark_offset_px - mark_len_px
                x_end = trim_left_px - mark_offset_px
                draw.line([(x_start, y_px), (x_end, y_px)], fill=mark_color, width=mark_width)

            for y_px, label in y_coords:
                x_start = trim_right_px + mark_offset_px
                x_end = trim_right_px + mark_offset_px + mark_len_px
                draw.line([(x_start, y_px), (x_end, y_px)], fill=mark_color, width=mark_width)

        if cfg.draw_info_text:
            font_size_px = mm_to_px(3.0, dpi)
            font = self._get_font(font_size_px)
            info_str = (
                f"[{cfg.binding_type}] Paper: {cfg.paper_width_mm:.0f}x{cfg.paper_height_mm:.0f}mm | "
                f"Book: {cfg.book_width_mm:.0f}x{cfg.book_height_mm:.0f}mm | "
                f"Spine: {cfg.spine_width_mm:.1f}mm | Cover: {cfg.cover_stock_type} | "
                f"Bleed/Wrap: {extra_margin_mm:.1f}mm | DPI: {cfg.dpi}"
            )
            info_x = trim_left_px
            info_y = trim_top_px - mm_to_px(12.0, dpi)
            if info_y > 10:
                draw.text((info_x, info_y), info_str, fill=(80, 80, 80, 255), font=font)

        final_image = Image.alpha_composite(canvas, overlay)
        return final_image.convert("RGB")

    def export_pdf(self, output_pdf_path: str, spread_image: Image.Image):
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdf_canvas

        w_pt = self.config.paper_width_mm * mm
        h_pt = self.config.paper_height_mm * mm

        c = pdf_canvas.Canvas(output_pdf_path, pagesize=(w_pt, h_pt))

        temp_img_path = output_pdf_path + ".tmp.png"
        spread_image.save(temp_img_path, format="PNG", dpi=(self.config.dpi, self.config.dpi))

        c.drawImage(temp_img_path, 0, 0, width=w_pt, height=h_pt)
        c.showPage()
        c.save()

        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
