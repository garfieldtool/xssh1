"""
Unit tests for Cover Engine layout, hardcover wrap margins, barcode rendering, DPI check, and PDF export.
"""

import os
import unittest
from PIL import Image
from cover_engine import (
    CoverConfig, CoverEngine, TextOverlay, ImageEditConfig,
    calculate_spine_thickness, draw_simple_barcode, mm_to_px, px_to_mm
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
        # Softcover 200P 80g offset paper -> 10.3mm
        spine_soft = calculate_spine_thickness(200, "80g 双胶纸 (Offset Paper)", is_hardcover=False)
        self.assertEqual(spine_soft, 10.3)

        # Hardcover 200P 80g offset paper -> 10.3 + 4.0 = 14.3mm
        spine_hard = calculate_spine_thickness(200, "80g 双胶纸 (Offset Paper)", is_hardcover=True)
        self.assertEqual(spine_hard, 14.3)

    def test_barcode_generation(self):
        bc_img = draw_simple_barcode("ISBN 978-7-12345-678-9", 200, 60)
        self.assertIsNotNone(bc_img)
        self.assertEqual(bc_img.size, (200, 60))

    def test_dpi_check(self):
        cfg = CoverConfig(dpi=300)
        engine = CoverEngine(cfg)
        res = engine.check_image_dpi(self.front_img_path, 148, 210)
        self.assertTrue(res["valid"])
        self.assertIn("effective_dpi", res)

    def test_hardcover_spread_dimensions(self):
        cfg = CoverConfig(
            binding_type="精装包壳",
            hardcover_wrap_mm=15.0,
            hardcover_groove_mm=8.0,
            paper_width_mm=420.0,
            paper_height_mm=297.0,
            book_width_mm=148.0,
            book_height_mm=210.0,
            spine_width_mm=12.0,
            show_barcode=True,
            barcode_text="1234567890",
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
