"""将原面板的逻辑几何映射到 niri 原生窗口，保留原布局及绘制"""
import time

from PySide6.QtCore import QObject, QPoint, QRect, QEvent, QTimer, Qt
from PySide6.QtWidgets import QApplication, QWidget, QGraphicsOpacityEffect


class Surfaces(QObject):
    """只管理本进程登记的气泡、日报及过渡画布"""
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller
        self.pet = controller.pet
        self.entries = {}
        self.dragging = None
        self.left = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.sync)
        self.serial = 0

    def bind(self, widget):
        """赋予独立原生窗口唯一标题，子控件不进入合成器定位流程"""
        if not widget.isWindow():
            return
        if widget in self.entries:
            return
        self.serial += 1
        widget.setWindowTitle('白龙 Linux 面板 ' + str(self.serial))
        widget._linux_surfaces = self
        self.entries[widget] = dict(point=QWidget.pos(widget), waiting=None, workspace=None, sent_at=0.)
        widget.installEventFilter(self)
        widget.destroyed.connect(lambda: self.entries.pop(widget, None))

    def window(self, widget):
        """只从 niri 控制器已过滤的本进程窗口中匹配标题"""
        return next((w for w in self.controller.windows.values() if w.get('title') == widget.windowTitle()), None)

    def actual(self, widget):
        """原生拖动读取合成器真实位置，不能累计 Qt 虚拟全局坐标"""
        window = self.window(widget)
        if not window:
            return None
        output = self.controller.workspaces.get(window.get('workspace_id'))
        screen = next((s for s in QApplication.screens() if s.name() == output), None)
        xy = window['layout'].get('tile_pos_in_workspace_view')
        if screen is None or xy is None:
            return None
        offset = window['layout']['window_offset_in_tile']
        return QPoint(round(xy[0] + offset[0]), round(xy[1] + offset[1])) + screen.geometry().topLeft()

    def move(self, widget, point):
        """同步保存布局目标，异步窗口确认不得改变正在计算的动画坐标系"""
        self.bind(widget)
        entry = self.entries[widget]
        entry['point'] = QPoint(point)
        if not self.timer.isActive():
            self.timer.start(0)

    def sync(self):
        """工作区切换和位移分别等待确认，避免重复累计相对增量"""
        if self.pet.closing:
            return
        for widget, entry in tuple(self.entries.items()):
            if widget is self.dragging or not widget.isVisible():
                continue
            window = self.window(widget)
            current = self.actual(widget)
            if not window or current is None:
                continue
            target = entry['point']
            screen = QApplication.screenAt(QRect(target, widget.size()).center()) or QApplication.primaryScreen()
            output = self.controller.workspaces.get(window.get('workspace_id'))
            if output != screen.name():
                key = ('monitor', screen.name())
                if entry['workspace'] != key:
                    entry['workspace'] = key
                    self.controller.action('MoveWindowToMonitor', id=window['id'], output=screen.name())
                continue
            # 附着面板与角色保持同一工作区，分离面板保留自己的工作区
            character = self.controller.character()
            detached = self.pet.settings.get('panel_detached') or not self.pet.settings.get('character_visible', True)
            if not detached and character and self.controller.workspaces.get(character.get('workspace_id')) == output and window.get('workspace_id') != character.get('workspace_id'):
                key = ('workspace', character['workspace_id'])
                if entry['workspace'] != key:
                    entry['workspace'] = key
                    self.controller.action('MoveWindowToWorkspace', window_id=window['id'], reference={'Id': character['workspace_id']}, focus=False)
                continue
            entry['workspace'] = None
            waiting = entry['waiting']
            if waiting is not None:
                if (current - waiting).manhattanLength() > 1 and time.monotonic() - entry['sent_at'] < 1.5:
                    self.timer.start(1500)
                    continue
                entry['waiting'] = None
            delta = target - current
            if delta.manhattanLength() <= 1:
                continue
            entry['waiting'] = QPoint(target)
            entry['sent_at'] = time.monotonic()
            self.timer.start(1500)
            self.controller.action('MoveFloatingWindow', id=window['id'], x={'AdjustFixed': delta.x()}, y={'AdjustFixed': delta.y()})

    def eventFilter(self, widget, event):
        """原生移动以离开后重新进入结束，Qt 模拟松手不结束拖动"""
        if self.dragging is widget:
            if event.type() == QEvent.Type.Leave:
                self.left = True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                return True
            elif event.type() == QEvent.Type.Enter and self.left:
                point = self.actual(widget)
                self.dragging = None
                widget._card_press = None
                widget._card_dragged = False
                if point is not None:
                    self.entries[widget]['point'] = point
                    self.pet.remember_card_anchor(QRect(point, widget.size()))
                    self.pet.position_bubble()
                    self.pet.save_settings()
                    if widget.report and widget.report.requested:
                        widget.report.sync_geometry()
            elif event.type() == QEvent.Type.Hide:
                self.dragging = None
        if event.type() in (QEvent.Type.Show, QEvent.Type.Resize):
            self.entries[widget]['waiting'] = None
            if not self.timer.isActive():
                self.timer.start(0)
        return False


def install(stack):
    """限定三个原生表面类型的几何入口，子控件和 Windows 实现不受影响"""
    from .overrides import replace
    from compact_bubble import CompactBubble
    from daily_report import DailyReport
    from panel_transition import NativeLanding

    def bridge(widget):
        """沿父对象找到已绑定气泡，兼容延迟创建的日报与过渡画布"""
        current = widget
        while current is not None:
            value = getattr(current, '_linux_surfaces', None)
            if value:
                value.bind(widget)
                return value
            current = current.parentWidget()
        return None

    def pos(widget):
        """向布局返回已提交目标，原生拖动期间返回实际坐标"""
        manager = bridge(widget)
        if manager:
            actual = manager.actual(widget) if manager.dragging is widget else None
            return actual if actual is not None else QPoint(manager.entries[widget]['point'])
        return QWidget.pos(widget)

    def geometry(widget):
        """逻辑原点与 Qt 实际画布尺寸组成布局矩形"""
        return QRect(pos(widget), widget.size())

    def move(widget, *args):
        """程序化定位交给合成器，窗口尺寸仍由原 Qt 布局管理"""
        manager = bridge(widget)
        if not manager:
            return QWidget.move(widget, *args)
        manager.move(widget, args[0] if len(args) == 1 else QPoint(*args))

    def set_geometry(widget, *args):
        """先登记新原点再调整画布，resizeEvent 始终看到一致的逻辑几何"""
        manager = bridge(widget)
        if not manager:
            return QWidget.setGeometry(widget, *args)
        rect = QRect(args[0]) if len(args) == 1 else QRect(*args)
        manager.move(widget, rect.topLeft())
        QWidget.resize(widget, rect.size())

    def screen(widget):
        """跨屏动画的边界计算使用目标屏幕，不依赖滞后的 Qt 屏幕信号"""
        if bridge(widget):
            return QApplication.screenAt(geometry(widget).center()) or QApplication.primaryScreen()
        return QWidget.screen(widget)

    for cls in (CompactBubble, DailyReport, NativeLanding):
        for name, method in dict(pos=pos, x=lambda w: pos(w).x(), y=lambda w: pos(w).y(), geometry=geometry,
                                 frameGeometry=geometry, move=move, setGeometry=set_geometry, screen=screen).items():
            stack.enter_context(replace(cls, name, method))

    press = CompactBubble.card_pointer_press
    release = CompactBubble.card_pointer_release

    def pointer_press(bubble, event):
        """保留可拖动区域判定，仅使用窗口内坐标判断阈值"""
        result = press(bubble, event)
        if result:
            bubble._linux_card_press = event.position().toPoint()
        return result

    def pointer_move(bubble, event):
        """分离面板交给 Wayland 原生移动，避免全局坐标反馈"""
        manager = bridge(bubble)
        if not manager or not bubble._card_press or not event.buttons() & Qt.MouseButton.LeftButton:
            return False
        if manager.dragging is bubble:
            return True
        if (event.position().toPoint() - bubble._linux_card_press).manhattanLength() <= 5:
            return False
        manager.dragging = bubble
        manager.left = False
        if bubble.windowHandle().startSystemMove():
            manager.entries[bubble]['waiting'] = None
            bubble._card_dragged = True
            return True
        manager.dragging = None
        return False

    def pointer_release(bubble):
        """合成器接管后不把模拟松手误认成用户释放"""
        manager = bridge(bubble)
        if manager and manager.dragging is bubble:
            return True
        return release(bubble)

    stack.enter_context(replace(CompactBubble, 'card_pointer_press', pointer_press))
    stack.enter_context(replace(CompactBubble, 'card_pointer_move', pointer_move))
    stack.enter_context(replace(CompactBubble, 'card_pointer_release', pointer_release))

    def set_opacity(widget, opacity):
        """Wayland 用绘制透明度隐藏日报，保持动画交接时原生窗口存在"""
        if not hasattr(widget, '_linux_opacity'):
            widget._linux_opacity = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(widget._linux_opacity)
        widget._linux_opacity.setOpacity(opacity)

    def opacity(widget):
        """向原联动动画返回同一绘制透明度，保持取消与恢复语义"""
        return widget._linux_opacity.opacity() if hasattr(widget, '_linux_opacity') else 1.

    stack.enter_context(replace(DailyReport, 'setWindowOpacity', set_opacity))
    stack.enter_context(replace(DailyReport, 'windowOpacity', opacity))
