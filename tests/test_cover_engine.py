"""
Unit tests for Cover Engine layout, spine thickness calculation, image editing, and PDF export.
"""

import os
import unittest
from PIL import Image
from cover_engine import (
    CoverConfig, CoverEngine, TextOverlay, ImageEditConfig,
    calculate_spine_thickness, mm_to_px, px_to_mm
)


class TestCoverEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(__file__)
        self.front_img_path = os.path.join(self.test_dir, "test_front.png")
        self.back_img_path = os.path.join(self.test_dir, "test_back.png")
        self.output_img_path = os.path.join(self.test_dir, "test_output.png")
        self.output_pdf_path = os.path.join(self.test_dir, "test_output.pdf")

        # Create dummy front and back cover images
        front = Image.new("RGB", (600, 800), color=(255, 100, 100))
        front.save(self.front_img_path)

        back = Image.new("RGB", (600, 800), color=(100, 100, 255))
        back.save(self.back_img_path)

    def tearDown(self):
        for path in [self.front_img_path, self.back_img_path, self.output_img_path, self.output_pdf_path]:
            if os.path.exists(path):
                os.remove(path)

    def test_mm_to_px_conversion(self):
        self.assertEqual(mm_to_px(25.4, 300), 300)
        self.assertAlmostEqual(px_to_mm(300, 300), 25.4, delta=0.01)

    def test_spine_thickness_calculation(self):
        # 200P 80g offset paper -> 100 sheets * 0.10mm + 0.3mm margin = 10.3mm
        spine = calculate_spine_thickness(200, "80g 双胶纸 (Offset Paper)")
        self.assertEqual(spine, 10.3)

        # 0P -> 0mm
        self.assertEqual(calculate_spine_thickness(0), 0.0)

    def test_spread_dimensions_a3_300dpi(self):
        cfg = CoverConfig(
            paper_width_mm=420.0,
            paper_height_mm=297.0,
            book_width_mm=148.0,
            book_height_mm=210.0,
            spine_width_mm=10.0,
            dpi=300
        )
        engine = CoverEngine(cfg)
        spread = engine.generate_spread(self.front_img_path, self.back_img_path)

        expected_w = mm_to_px(420.0, 300)
        expected_h = mm_to_px(297.0, 300)

        self.assertEqual(spread.size, (expected_w, expected_h))

    def test_image_edits_and_text_overlay(self):
        front_edit = ImageEditConfig(
            brightness=1.2,
            contrast=1.1,
            text_overlays=[TextOverlay(text="封面主标题", font_size_pt=36, color="#FF0000", bg_banner=True)]
        )
        cfg = CoverConfig(
            front_edit=front_edit,
            dpi=150
        )
        engine = CoverEngine(cfg)
        spread = engine.generate_spread(self.front_img_path, self.back_img_path)
        self.assertIsNotNone(spread)

    def test_pdf_export(self):
        cfg = CoverConfig(dpi=150)
        engine = CoverEngine(cfg)
        spread = engine.generate_spread(self.front_img_path, self.back_img_path)
        engine.export_pdf(self.output_pdf_path, spread)

        self.assertTrue(os.path.exists(self.output_pdf_path))
        self.assertGreater(os.path.getsize(self.output_pdf_path), 0)


if __name__ == "__main__":
    unittest.main()
