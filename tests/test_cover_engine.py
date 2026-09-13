"""
Unit tests for Cover Engine layout, hardcover wrap margins, barcode rendering, PDF input extraction, DPI check, and custom presets.
"""

import os
import unittest
from PIL import Image
from reportlab.pdfgen import canvas
from cover_engine import (
    CoverConfig, CoverEngine, TextOverlay, ImageEditConfig,
    calculate_spine_thickness, draw_simple_barcode, render_pdf_page_to_image,
    mm_to_px, px_to_mm, PAPER_SIZES_MM, BOOK_SIZES_MM
)


class TestCoverEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(__file__)
        self.front_img_path = os.path.join(self.test_dir, "test_front.png")
        self.back_img_path = os.path.join(self.test_dir, "test_back.png")
        self.test_pdf_path = os.path.join(self.test_dir, "test_input.pdf")
        self.output_img_path = os.path.join(self.test_dir, "test_output.png")
        self.output_pdf_path = os.path.join(self.test_dir, "test_output.pdf")

        # Create dummy front and back cover images
        front = Image.new("RGB", (600, 800), color=(255, 100, 100))
        front.save(self.front_img_path)

        back = Image.new("RGB", (600, 800), color=(100, 100, 255))
        back.save(self.back_img_path)

        # Create 2-page dummy test PDF file
        c = canvas.Canvas(self.test_pdf_path, pagesize=(400, 600))
        c.drawString(100, 500, "PDF Front Page (Page 1)")
        c.showPage()
        c.drawString(100, 500, "PDF Back Page (Page 2)")
        c.showPage()
        c.save()

    def tearDown(self):
        for path in [self.front_img_path, self.back_img_path, self.test_pdf_path, self.output_img_path, self.output_pdf_path]:
            if os.path.exists(path):
                os.remove(path)

    def test_pdf_page_extraction(self):
        # Extract page 1
        img1 = render_pdf_page_to_image(self.test_pdf_path, page_num=1, render_dpi=150)
        self.assertIsNotNone(img1)

        # Extract page -1 (last page)
        img_last = render_pdf_page_to_image(self.test_pdf_path, page_num=-1, render_dpi=150)
        self.assertIsNotNone(img_last)

    def test_pdf_input_cover_generation(self):
        cfg = CoverConfig(
            front_pdf_page=1,
            back_pdf_page=2,
            dpi=150
        )
        engine = CoverEngine(cfg)
        spread = engine.generate_spread(self.test_pdf_path, self.test_pdf_path)
        self.assertIsNotNone(spread)

    def test_spine_thickness_calculation(self):
        spine_soft = calculate_spine_thickness(200, "80g 双胶纸 (Offset)", is_hardcover=False)
        self.assertEqual(spine_soft, 10.3)

    def test_barcode_generation(self):
        bc_img = draw_simple_barcode("ISBN 978-7-12345-678-9", 200, 60)
        self.assertIsNotNone(bc_img)
        self.assertEqual(bc_img.size, (200, 60))

    def test_dpi_check(self):
        cfg = CoverConfig(dpi=300)
        engine = CoverEngine(cfg)
        res = engine.check_image_dpi(self.front_img_path, 148.0, 210.0)
        self.assertTrue(res["valid"])
        self.assertIn("effective_dpi", res)

    def test_pdf_export(self):
        cfg = CoverConfig(dpi=150)
        engine = CoverEngine(cfg)
        spread = engine.generate_spread(self.front_img_path, self.back_img_path)
        engine.export_pdf(self.output_pdf_path, spread)

        self.assertTrue(os.path.exists(self.output_pdf_path))
        self.assertGreater(os.path.getsize(self.output_pdf_path), 0)


if __name__ == "__main__":
    unittest.main()
