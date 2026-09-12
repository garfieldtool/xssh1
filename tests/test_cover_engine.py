"""
Unit tests for Cover Engine layout and PDF export.
"""

import os
import unittest
from PIL import Image
from cover_engine import CoverConfig, CoverEngine, mm_to_px, px_to_mm


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
        # 25.4 mm @ 300 DPI should be exactly 300 px
        self.assertEqual(mm_to_px(25.4, 300), 300)
        self.assertAlmostEqual(px_to_mm(300, 300), 25.4, delta=0.01)

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

        expected_w = mm_to_px(420.0, 300)  # 4961
        expected_h = mm_to_px(297.0, 300)  # 3508

        self.assertEqual(spread.size, (expected_w, expected_h))

    def test_spine_text_rendering(self):
        cfg = CoverConfig(
            spine_text="测试书名",
            spine_width_mm=15.0,
            spine_text_vertical=True,
            spine_bg_color="#FFDD00",
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
