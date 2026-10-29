"""验证气泡布局与 Linux 入口的原生拖动边界"""
import unittest
from PySide6.QtCore import QRect, QPoint
from linux_app.niri import bubble_position


class LayoutTests(unittest.TestCase):
    """固定间距与边缘翻转必须保持原有逻辑像素布局"""
    def test_center_and_gap(self):
        """非零工作区原点不应叠加到窗口坐标"""
        point = bubble_position(832, 425, (256, 256), (268, 188), 188, QRect(0, 25, 1920, 1055))
        self.assertEqual(point, QPoint(826, 229))

    def test_top_flips_below(self):
        """气泡在顶部空间不足时转到角色下方"""
        point = bubble_position(400, 80, (256, 256), (268, 188), 188, QRect(0, 25, 1920, 1055))
        self.assertEqual(point, QPoint(394, 344))

    def test_edges_and_fractional_coordinates(self):
        """浮点布局坐标按逻辑像素取整并保持气泡在输出范围内"""
        area = QRect(0, 25, 1920, 1055)
        point = bubble_position(0.2, 500.2, (256, 256), (268, 188), 188, area)
        self.assertEqual(point, QPoint(0, 304))
        point = bubble_position(1800, 500, (256, 256), (268, 188), 188, area)
        self.assertEqual(point.x(), 1652)


class DragTests(unittest.TestCase):
    """全局坐标突变不得进入原来的位移累计路径"""
    def test_synthetic_release_does_not_finish_native_drag(self):
        """Qt 的模拟松手必须被忽略，离开后重新进入才结束原生拖动"""
        from types import SimpleNamespace
        from unittest.mock import Mock
        from PySide6.QtCore import QEvent
        from linux_app.niri import NiriWindows
        pet = SimpleNamespace(_niri_drag=True, _niri_left=False, mouseReleaseEvent=Mock())
        controller = SimpleNamespace(pet=pet, position=Mock(), reveal=SimpleNamespace(start=Mock()))
        event = lambda kind: SimpleNamespace(type=lambda: kind)
        self.assertTrue(NiriWindows.eventFilter(controller, pet, event(QEvent.Type.MouseButtonRelease)))
        self.assertTrue(pet._niri_drag)
        NiriWindows.eventFilter(controller, pet, event(QEvent.Type.Enter))
        self.assertTrue(pet._niri_drag)
        NiriWindows.eventFilter(controller, pet, event(QEvent.Type.Leave))
        NiriWindows.eventFilter(controller, pet, event(QEvent.Type.Enter))
        self.assertFalse(pet._niri_drag)
        pet.mouseReleaseEvent.assert_called_once()

    def test_native_move_and_lock(self):
        """只用窗口内坐标判断拖动阈值；锁定移动时不调用合成器"""
        from contextlib import ExitStack
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        from PySide6.QtCore import QPointF, Qt
        from desktop import DesktopPet
        from linux_app.niri import install
        event = SimpleNamespace(position=lambda: QPointF(30, 30), buttons=lambda: Qt.MouseButton.LeftButton,
                                globalPosition=Mock(side_effect=AssertionError('不应读取虚拟全局坐标')), accept=Mock())
        handle = SimpleNamespace(startSystemMove=Mock(return_value=True))
        pet = SimpleNamespace(_niri_windows=SimpleNamespace(opacity=SimpleNamespace(setOpacity=Mock()), reveal=SimpleNamespace(stop=Mock())), settings={}, _pointer_pressed=True, _niri_press=QPoint(10, 10),
                              windowHandle=lambda: handle, click_timer=SimpleNamespace(stop=Mock()),
                              last_click=1, drag_samples=[1], generation=0, gate=SimpleNamespace(state='idle'),
                              bubble_timer=SimpleNamespace(stop=Mock()), bubble=SimpleNamespace(hide=Mock(), size_transition=SimpleNamespace(cancel=Mock())),
                              play=Mock(), manifest={'dragAnimation': 'drag'}, idles=['idle'])
        original = DesktopPet.mouseMoveEvent
        with ExitStack() as stack:
            install(stack)
            DesktopPet.mouseMoveEvent(pet, event)
            handle.startSystemMove.assert_called_once()
            self.assertEqual(pet.drag_samples, [])
            self.assertIsNone(pet.last_click)
            event.accept.assert_called_once()
            self.assertTrue(pet._niri_drag)
            pet.play.assert_called_once_with('drag', 'drag')
            pet.bubble.size_transition.cancel.assert_called_once()
            pet.settings['no_move'] = True
            DesktopPet.mouseMoveEvent(pet, event)
            handle.startSystemMove.assert_called_once()
        self.assertIs(DesktopPet.mouseMoveEvent, original)


if __name__ == '__main__':
    unittest.main()
