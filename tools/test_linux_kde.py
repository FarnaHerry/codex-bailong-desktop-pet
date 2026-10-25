"""Verify input-only alpha masks without altering the rendered character."""
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock
import unittest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QApplication, QWidget
from linux_app.kde import InputShape, install


class InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_transparent_pixels_only_affect_mouse_shape(self):
        widget = QWidget()
        widget.resize(35, 10)  # Deliberately exercise QImage's padded bitmap rows.
        widget.show()
        source = QImage(35, 10, QImage.Format.Format_ARGB32_Premultiplied)
        source.fill(Qt.GlobalColor.transparent)
        painter = QPainter(source)
        painter.fillRect(9, 3, 8, 4, Qt.GlobalColor.white)
        painter.end()
        shape = InputShape.__new__(InputShape)
        shape.display, shape.last = 1, None
        shape.x11 = Mock()
        shape.x11.XCreateBitmapFromData.return_value = 42
        shape.xext = Mock()
        pet = SimpleNamespace(isVisible=widget.isVisible, windowHandle=widget.windowHandle, rect=widget.rect,
                              winId=Mock(side_effect=AssertionError('QWidget native ID may be stale')),
                              devicePixelRatioF=lambda: 1., size=widget.size, width=widget.width, height=widget.height,
                              frame_transform=lambda rect: QTransform(), frames=[QPixmap.fromImage(source)], settings={},
                              draw_frame=lambda p, rect: p.drawImage(0, 0, source))
        try:
            shape.update(pet)
            args = shape.x11.XCreateBitmapFromData.call_args.args
            bits = args[2]
            self.assertEqual((args[3], args[4]), (35, 10))
            self.assertEqual(len(bits), 5 * 10)
            hit = lambda x, y: bool(bits[y * 5 + x // 8] & (1 << (x % 8)))
            self.assertTrue(hit(12, 4))
            self.assertFalse(hit(0, 0))
            self.assertFalse(hit(20, 4))
            shape.xext.XShapeCombineMask.assert_called_once_with(1, int(widget.winId()), 2, 0, 0, 42, 0)
            self.assertTrue(widget.mask().isEmpty())  # Visual alpha was never clipped.
            shape.update(pet)
            self.assertEqual(shape.x11.XCreateBitmapFromData.call_count, 1)
            pet.settings['mouse_through'] = True
            shape.update(pet)
            self.assertFalse(any(shape.x11.XCreateBitmapFromData.call_args.args[2]))
            # Pin/through flags can recreate QWindow while QWidget keeps an old ID.
            pet.windowHandle = lambda: SimpleNamespace(winId=lambda: 54321)
            shape.update(pet)
            self.assertEqual(shape.xext.XShapeCombineMask.call_args.args[1], 54321)
            self.assertEqual(shape.x11.XCreateBitmapFromData.call_count, 3)
        finally:
            widget.close()

    def test_kde_does_not_install_niri_geometry_or_drag_overrides(self):
        from desktop import DesktopPet
        original = (DesktopPet.move, DesktopPet.mouseMoveEvent, DesktopPet.paintEvent)
        with ExitStack() as stack:
            install(stack)
            self.assertIs(DesktopPet.move, original[0])
            self.assertIs(DesktopPet.mouseMoveEvent, original[1])
            self.assertIsNot(DesktopPet.paintEvent, original[2])
        self.assertIs(DesktopPet.paintEvent, original[2])
