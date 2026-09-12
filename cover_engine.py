"""
Book Cover Layout Engine for Print Shops.
Generates print-ready A3/A4 spread covers with Back Cover, Spine, Front Cover, Crop Marks, and Fold Lines.
Includes image color adjustments, custom text overlays, and page count spine thickness calculator.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageColor

# Standard paper sizes in mm (Landscape orientation for cover spreads)
PAPER_SIZES_MM = {
    "A3": (420.0, 297.0),
    "A4": (297.0, 210.0),
    "SRA3": (450.0, 320.0),
    "A3+": (483.0, 329.0),
}

# Standard finished book sizes in mm (Single page / Front cover dimension)
BOOK_SIZES_MM = {
    "A5": (148.0, 210.0),
    "B5": (176.0, 250.0),
    "B5 (185x260)": (185.0, 260.0),
    "A4": (210.0, 297.0),
    "32k": (130.0, 184.0),
    "16k": (184.0, 260.0),
}

# Common paper thickness in mm per single sheet (1 sheet = 2 pages)
PAPER_TYPES_THICKNESS_MM = {
    "70g 双胶纸 (Offset Paper)": 0.09,
    "80g 双胶纸 (Offset Paper)": 0.10,
    "100g 双胶纸 (Offset Paper)": 0.12,
    "105g 铜版纸 (Art Paper)": 0.08,
    "128g 铜版纸 (Art Paper)": 0.095,
    "157g 铜版纸 (Art Paper)": 0.115,
    "200g 铜版纸 (Art Paper)": 0.15,
    "70g 轻型纸/蒙肯纸 (Bulky Paper)": 0.13,
    "80g 轻型纸/蒙肯纸 (Bulky Paper)": 0.15,
}


def calculate_spine_thickness(page_count: int, paper_type: str = "80g 双胶纸 (Offset Paper)", custom_sheet_thickness_mm: Optional[float] = None) -> float:
    """
    Calculate book spine thickness in mm.
    Formula: (page_count / 2) * sheet_thickness + cover_board_margin (approx 0.5mm)
    """
    if page_count <= 0:
        return 0.0

    if custom_sheet_thickness_mm is not None and custom_sheet_thickness_mm > 0:
        sheet_thick = custom_sheet_thickness_mm
    else:
        sheet_thick = PAPER_TYPES_THICKNESS_MM.get(paper_type, 0.10)

    sheets = (page_count + 1) // 2  # Round up to number of physical leaves/sheets
    spine_mm = sheets * sheet_thick
    # Add minor binding glue/margin factor (~0.5mm)
    return round(spine_mm + 0.3, 2)


def mm_to_px(mm: float, dpi: int = 300) -> int:
    """Convert millimeters to pixels at a given DPI."""
    return int(round(mm * dpi / 25.4))


def px_to_mm(px: int, dpi: int = 300) -> float:
    """Convert pixels to millimeters at a given DPI."""
    return px * 25.4 / dpi


@dataclass
class TextOverlay:
    text: str
    rel_x: float = 0.5            # Relative X position (0.0 to 1.0)
    rel_y: float = 0.5            # Relative Y position (0.0 to 1.0)
    font_size_pt: int = 24
    color: str = "#000000"
    is_vertical: bool = False
    bg_banner: bool = False       # Draw background banner behind text for contrast
    banner_color: str = "#FFFFFF"


@dataclass
class ImageEditConfig:
    brightness: float = 1.0        # 1.0 = normal, <1.0 darker, >1.0 brighter
    contrast: float = 1.0          # 1.0 = normal
    color_tint: Optional[str] = None # Tint hex overlay (e.g. #FF0000) or None
    tint_opacity: float = 0.2
    text_overlays: List[TextOverlay] = field(default_factory=list)


@dataclass
class CoverConfig:
    paper_width_mm: float = 420.0       # Sheet width (e.g. A3 landscape)
    paper_height_mm: float = 297.0      # Sheet height (e.g. A3 landscape)
    book_width_mm: float = 148.0        # Finished book width
    book_height_mm: float = 210.0       # Finished book height
    spine_width_mm: float = 10.0        # Spine thickness
    page_count: int = 0                 # Page count for auto-spine calculation
    paper_type: str = "80g 双胶纸 (Offset Paper)"
    bleed_mm: float = 3.0               # Bleed margin around cover trim
    dpi: int = 300                       # Print DPI (300 standard)
    bg_color: str = "#FFFFFF"           # Sheet background color
    spine_bg_color: Optional[str] = None # Spine fill color (None = auto/transparent)
    spine_text: str = ""                # Spine title text
    spine_text_color: str = "#000000"    # Spine title text color
    spine_text_size_pt: int = 14        # Font size for spine text
    spine_text_vertical: bool = True     # Vertical top-to-bottom text
    draw_crop_marks: bool = True         # Draw corner crop marks
    draw_fold_lines: bool = True         # Draw spine fold indicator lines
    draw_info_text: bool = True          # Draw job metadata on margin
    fill_mode: str = "fit"               # "fit", "fill", or "stretch"

    front_edit: ImageEditConfig = field(default_factory=ImageEditConfig)
    back_edit: ImageEditConfig = field(default_factory=ImageEditConfig)

    @property
    def total_spread_width_mm(self) -> float:
        """Total spread width including front cover, spine, back cover."""
        return self.book_width_mm * 2.0 + self.spine_width_mm

    @property
    def total_spread_height_mm(self) -> float:
        """Total spread height (same as single cover height)."""
        return self.book_height_mm


class CoverEngine:
    def __init__(self, config: CoverConfig):
        self.config = config

    def _get_font(self, size_px: int) -> ImageFont.ImageFont:
        """Attempt to load system CJK font or fall back to default PIL font."""
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

    def _apply_image_edits_and_overlays(
        self,
        img: Image.Image,
        edit_cfg: ImageEditConfig,
        dpi: int
    ) -> Image.Image:
        """Apply brightness, contrast, color tinting, and text overlays onto image."""
        img = img.convert("RGBA")

        # 1. Brightness
        if edit_cfg.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(edit_cfg.brightness)

        # 2. Contrast
        if edit_cfg.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(edit_cfg.contrast)

        # 3. Color Tint Overlay
        if edit_cfg.color_tint:
            try:
                tint_color = ImageColor.getrgb(edit_cfg.color_tint)
                tint_layer = Image.new("RGBA", img.size, tint_color + (int(255 * edit_cfg.tint_opacity),))
                img = Image.alpha_composite(img, tint_layer)
            except Exception:
                pass

        # 4. Text Overlays
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
        bg_color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    ) -> Image.Image:
        """Load an image file, resize it, and apply custom edits/overlays."""
        if not img_path or not os.path.isfile(img_path):
            blank = Image.new("RGBA", (target_w_px, target_h_px), bg_color)
            draw = ImageDraw.Draw(blank)
            draw.rectangle([(0, 0), (target_w_px - 1, target_h_px - 1)], outline=(200, 200, 200), width=3)
            if edit_cfg:
                blank = self._apply_image_edits_and_overlays(blank, edit_cfg, self.config.dpi)
            return blank

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
        """Render spine rectangle with optional background and text."""
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
        """
        Generate complete A3/A4 landscape paper sheet with Front, Spine, Back,
        Bleed, Crop Marks, Fold Lines, and Metadata.
        """
        cfg = self.config
        dpi = cfg.dpi

        # Convert sizes to pixels
        paper_w_px = mm_to_px(cfg.paper_width_mm, dpi)
        paper_h_px = mm_to_px(cfg.paper_height_mm, dpi)

        book_w_px = mm_to_px(cfg.book_width_mm, dpi)
        book_h_px = mm_to_px(cfg.book_height_mm, dpi)
        spine_w_px = mm_to_px(cfg.spine_width_mm, dpi)
        bleed_px = mm_to_px(cfg.bleed_mm, dpi)

        # Create base canvas
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

        # Cover positions with bleed
        back_w_px = book_w_px + bleed_px
        back_h_px = book_h_px + 2 * bleed_px

        front_w_px = book_w_px + bleed_px
        front_h_px = book_h_px + 2 * bleed_px

        spine_h_px = book_h_px + 2 * bleed_px

        # Load cover images with edits
        back_img = self._load_and_scale_image(back_cover_path, back_w_px, back_h_px, cfg.fill_mode, cfg.back_edit)
        front_img = self._load_and_scale_image(front_cover_path, front_w_px, front_h_px, cfg.fill_mode, cfg.front_edit)

        # Render spine
        spine_img = self._render_spine(spine_w_px, spine_h_px, front_img, back_img)

        # Paste onto paper canvas
        back_pos_x = trim_left_px - bleed_px
        back_pos_y = trim_top_px - bleed_px
        canvas.paste(back_img, (back_pos_x, back_pos_y), back_img)

        front_pos_x = spine_right_px
        front_pos_y = trim_top_px - bleed_px
        canvas.paste(front_img, (front_pos_x, front_pos_y), front_img)

        spine_pos_x = spine_left_px
        spine_pos_y = trim_top_px - bleed_px
        canvas.paste(spine_img, (spine_pos_x, spine_pos_y), spine_img)

        # Draw Overlay (Crop marks, Fold lines, Info text)
        overlay = Image.new("RGBA", (paper_w_px, paper_h_px), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        if cfg.draw_fold_lines:
            dash_len = mm_to_px(2.0, dpi)
            gap_len = mm_to_px(2.0, dpi)
            fold_color = (120, 120, 120, 200)

            for x_px in [spine_left_px, spine_right_px]:
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
                f"Paper: {cfg.paper_width_mm:.0f}x{cfg.paper_height_mm:.0f}mm | "
                f"Book: {cfg.book_width_mm:.0f}x{cfg.book_height_mm:.0f}mm | "
                f"Spine: {cfg.spine_width_mm:.1f}mm | "
                f"Bleed: {cfg.bleed_mm:.1f}mm | DPI: {cfg.dpi}"
            )
            info_x = trim_left_px
            info_y = trim_top_px - mm_to_px(12.0, dpi)
            if info_y > 10:
                draw.text((info_x, info_y), info_str, fill=(80, 80, 80, 255), font=font)

        final_image = Image.alpha_composite(canvas, overlay)
        return final_image.convert("RGB")

    def export_pdf(self, output_pdf_path: str, spread_image: Image.Image):
        """Export spread image to PDF preserving exact physical DPI and mm dimensions."""
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
