"""Window fitting must not clip operating controls on smaller work areas."""
import unittest

from nexus.app import window_geometry


class WindowGeometryTests(unittest.TestCase):
    def test_work_area_bounds_include_restore_and_minimum_size(self):
        for width,height in ((1920,1040),(1280,680),(1024,728),(800,560),(320,240)):
            with self.subTest(work_area=(width,height)):
                result=window_geometry(width,height)
                self.assertLessEqual(result['width'],width)
                self.assertLessEqual(result['height'],height)
                self.assertLessEqual(result['min_size'][0],result['width'])
                self.assertLessEqual(result['min_size'][1],result['height'])
                self.assertTrue(result['maximized'])

    def test_large_desktop_does_not_create_unbounded_restore_size(self):
        result=window_geometry(7680,4320)
        self.assertEqual((result['width'],result['height']),(1450,950))

    def test_invalid_display_measurement_is_rejected(self):
        for value in (0,-1,True,800.5,None):
            with self.assertRaises(ValueError):window_geometry(value,720)


if __name__=='__main__':unittest.main()
