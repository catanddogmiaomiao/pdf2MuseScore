import unittest
from PIL import Image, ImageDraw
from pdf2muse.segmentation import detect_page


class SegmentationTests(unittest.TestCase):
    def test_blank_page(self):
        self.assertEqual(detect_page(Image.new('L',(1000,1000),255))['rows'],[])

    def test_short_staff_and_stem(self):
        image = Image.new('L',(1000,500),255)
        draw = ImageDraw.Draw(image)
        for y in (100,110,120,130,140):
            draw.line((50,y,450,y),fill=0)
        for x in (50,200,320,450):
            draw.line((x,100,x,140),fill=0)
        draw.line((270,90,270,140),fill=0)
        draw.ellipse((256,135,270,144),fill=0)
        page = detect_page(image)
        self.assertEqual(len(page['rows']),1)
        self.assertEqual(len(page['rows'][0]['measures']),3)
        self.assertNotIn(270,page['rows'][0]['boundaries'])
