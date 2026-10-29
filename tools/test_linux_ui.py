"""Linux 新版界面适配只改变平台接入，保留上游布局与绘制"""
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from PySide6.QtCore import QEvent, QPoint, QRect, QObject, Qt
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QGraphicsOpacityEffect
from compact_bubble import CompactBubble
from daily_report import DailyReport
from desktop_settings import SettingsDialog
from hover_hints import HintBubble, TrayHints
from linux_app import surfaces, ui
from test_settings_controls import PetStub

APP = QApplication.instance() or QApplication([])


class LinuxUiTests(unittest.TestCase):
    """覆盖 niri 原点转换、StatusNotifier 文本及本机来源约束"""
    def tearDown(self):
        """释放测试窗口，不接触日常桌宠和配置"""
        for widget in APP.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        APP.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        APP.processEvents()

    def test_hint_uses_card_origin_even_when_owned_by_report(self):
        """日报可能有不同的 Qt 虚拟原点，顶栏锚点仍须使用卡片原点"""
        bubble = CompactBubble()
        bubble.move(20, 30)
        report = DailyReport(bubble)
        report.move(100, 200)
        controller = QObject()
        controller.pet = SimpleNamespace(bubble=bubble, closing=False, isVisible=lambda: False)
        manager = surfaces.Surfaces(controller)
        manager.bind(bubble)
        manager.bind(report)
        manager.entries[bubble]['point'] = QPoint(280, 390)
        manager.entries[report]['point'] = QPoint(280, 80)
        popup = HintBubble()
        virtual = QWidget.mapToGlobal(bubble, QPoint())
        anchor = QRect(virtual + QPoint(45, 10), bubble._header_actions[0].size())
        with ExitStack() as stack:
            original = HintBubble.present
            observed = stack.enter_context(patch.object(HintBubble, 'present', wraps=original))
            surfaces.install(stack)
            popup.present('数据', '', anchor, bubble.screen(), card_top=virtual.y(), owner=report)
            values = observed.call_args
            self.assertEqual(values.args[3].topLeft(), QPoint(325, 400))
            self.assertEqual(values.kwargs['card_top'], 390)
            self.assertIs(popup.windowHandle().transientParent(), report.windowHandle())
            self.assertIn(popup, manager.entries)
            self.assertEqual(popup.windowHandle().mask().boundingRect(), QRect(-1, -1, 1, 1))
            self.assertEqual(popup.geometry().topLeft(), manager.entries[popup]['point'])
            self.assertLessEqual(abs(popup.geometry().bottom() - bubble.y()), 2)
            self.assertEqual(bubble.pos(), QPoint(280, 390))
        manager.timer.stop()

    def test_tray_text_and_settings_are_scoped_to_linux(self):
        """原提示生成和设置草稿保留，适配退出后原方法恢复"""
        original = SettingsDialog.build_page_2
        with ExitStack() as stack:
            stack.enter_context(patch('desktop_settings.autostart_enabled', return_value=False))
            stack.enter_context(patch('codex_startup.enabled', return_value=False))
            ui.install(stack)
            pet = PetStub()
            dialog = SettingsDialog(pet, embedded=True)
            self.assertEqual(dialog.path_source.currentData(), 'windows')
            self.assertEqual(dialog.path_source.buttons['windows'].text(), 'Linux 本机')
            self.assertFalse(dialog.path_source.buttons['wsl'].isEnabled())
            self.assertTrue(dialog.fields['codex_exit'].isEnabled())
            self.assertIn('图形桌面', dialog.startup.text())
            self.assertNotIn('Windows', dialog.codex_startup.text())
            tray = QSystemTrayIcon(pet)
            hints = TrayHints(tray, pet)
            hints.set_text('周额度 86%', '下次重置 10/30 18:00')
            self.assertEqual(tray.toolTip(), '周额度 86%\n下次重置 10/30 18:00')
            self.assertFalse(hints.watch.isActive())
            hints.close()
        self.assertIs(SettingsDialog.build_page_2, original)

    def test_transition_has_one_visible_renderer_and_unmaps_idle_helper(self):
        """准备期原窗不动，动画期仅临时画布可见，结束后没有额外窗口"""
        bubble = CompactBubble()
        bubble.move(100, 300)
        bubble.show()
        APP.processEvents()
        controller = QObject()
        controller.pet = SimpleNamespace(bubble=bubble, closing=False, isVisible=lambda: False)
        controller.windows = {}
        controller.opacity = QGraphicsOpacityEffect(bubble)
        controller.opacity.setOpacity(1)
        bubble.setGraphicsEffect(controller.opacity)
        manager = surfaces.Surfaces(controller)
        manager.bind(bubble)
        transition = bubble.size_transition
        with ExitStack() as stack:
            surfaces.install(stack)
            for navigate in (lambda: bubble.set_mode('mini'), lambda: bubble.set_mode('auto'),
                             lambda: bubble.set_mode('mini'), bubble.toggle_details):
                source = bubble.geometry()
                navigate()
                self.assertEqual(transition._linux_stage, 'preparing')
                self.assertEqual(bubble.geometry(), source)
                self.assertEqual(controller.opacity.opacity(), 1)
                self.assertIsNone(transition.landing.image)
                canvas = transition.landing.geometry()
                transition.release_landing()
                self.assertEqual(transition._linux_stage, 'playing')
                self.assertEqual(controller.opacity.opacity(), 0)
                transition.animation.setCurrentTime(transition.animation.duration() // 2)
                self.assertEqual(transition.landing.geometry(), canvas)
                transition.complete()
                self.assertEqual(transition._linux_stage, 'landing')
                self.assertEqual(controller.opacity.opacity(), 0)
                self.assertEqual(transition.landing.geometry(), canvas)
                self.assertIsNotNone(transition.landing.image)
                transition.release_landing()
                self.assertEqual(controller.opacity.opacity(), 1)
                self.assertFalse(transition.landing.isVisible())
                self.assertFalse(transition.landing_timer.isActive())
            bubble.set_mode('mini')
            transition.complete()
            transition.release_landing()
            self.assertEqual(controller.opacity.opacity(), 1)
            self.assertFalse(transition.landing.isVisible())
            bubble.set_mode('auto')
            bubble.hide()
            self.assertEqual(controller.opacity.opacity(), 1)
            self.assertFalse(transition.landing.isVisible())
            self.assertFalse(transition.landing_timer.isActive())
        manager.timer.stop()

    def test_attached_popup_overlaps_native_move_with_original_animation(self):
        """附着角色时仅等 popup 暴露，原动画期间完成目标定位并保留排队导航"""
        pet = QWidget()
        pet.show()
        bubble = CompactBubble()
        bubble.move(100, 300)
        bubble.show()
        APP.processEvents()
        pet.bubble = bubble
        pet.closing = False
        controller = QObject()
        controller.pet = pet
        controller.windows = {}
        controller.opacity = QGraphicsOpacityEffect(bubble)
        controller.opacity.setOpacity(1)
        bubble.setGraphicsEffect(controller.opacity)
        manager = surfaces.Surfaces(controller)
        manager.bind(bubble)
        transition = bubble.size_transition
        with ExitStack() as stack:
            surfaces.install(stack)
            bubble.set_mode('mini')
            self.assertIs(transition.landing._linux_popup_parent, pet)
            self.assertEqual(transition.landing.windowType(), Qt.WindowType.ToolTip)
            # 原生子表面会绕过气泡的绘制透明度，并声明不透明矩形
            for child in (bubble.content, transition.cover):
                self.assertFalse(child.testAttribute(Qt.WidgetAttribute.WA_NativeWindow))
                self.assertIsNone(child.windowHandle())
            self.assertEqual(transition.landing_timer.interval(), 0)
            APP.processEvents()
            if transition._linux_stage == 'preparing':
                transition.release_landing()
            self.assertEqual(transition._linux_stage, 'playing')
            self.assertEqual(transition.animation.duration(), 440)
            self.assertEqual(bubble.geometry(), transition.target_rect)
            self.assertEqual(controller.opacity.opacity(), 0)
            bubble.set_mode('auto')
            self.assertEqual(bubble._pending_mode, 'auto')
            transition.complete()
            self.assertEqual(bubble.bubble_mode, 'auto')
            self.assertEqual(transition.animation.duration(), 480)
            self.assertIn(transition._linux_stage, ('preparing', 'playing'))
            APP.processEvents()
            if transition._linux_stage == 'preparing':
                transition.release_landing()
            transition.complete()
            self.assertEqual(transition.landing_timer.interval(), 0)
            transition.release_landing()
            self.assertEqual(controller.opacity.opacity(), 1)
            self.assertFalse(transition.landing.isVisible())
            self.assertFalse(transition.running)
            for child in (bubble.content, transition.cover):
                self.assertFalse(child.testAttribute(Qt.WidgetAttribute.WA_NativeWindow))
                self.assertIsNone(child.windowHandle())
        manager.timer.stop()


if __name__ == '__main__':
    unittest.main()
