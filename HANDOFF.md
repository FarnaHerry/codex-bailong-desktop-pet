# 项目交接要点

## Linux preview.2 发布验证（2026-10-25）

- 本轮重新通过 108 项回归、actionlint 和 279 个归档载荷 SHA256；源码目录用 bwrap 隐藏后，便携版与 AppImage 解压模式真实 IPC/额度/Token、位置保存恢复及正常退出通过，普通 FUSE 挂载也通过。Codex config/auth 与日常设置哈希保持不变。
- 打包监听实测使用外部 AppImage 路径创建独立 GUI 服务，手动退出不反复拉起；临时服务已清理。PyInstaller 的 Qt 运行钩子会预载 QtCore，不能将源码的无 Qt 结论套到冻结包；冻结监听没有 QtGui/QtWidgets 映射，5 秒采样单核 CPU 2.2%、RSS 44.0 MiB。
- 三种包体运行的两秒短采样单核 CPU 27.5–30.5%、RSS 226.7–363.3 MiB，包含启动与动画，非长期平均或性能对照。压缩健康为 degraded，不声称完整压缩行为通过。未做 KDE 包体、其他发行版、重新登录或 Windows 人工验收。证据 work/linux-build/preview2-*，源码外验收位于当前聊天 work/preview2。

## Linux 随 Codex 启动（2026-10-25）

- linux_app/codex_watch.py 复用原 LaunchGate，按当前用户 Electron 主进程的 PID/创建时间识别会话，排除 CLI 和 --type 子进程；live.py 的桌面存在检测共用此实现。--watch-codex 在 Qt 初始化及素材准备前进入监听，仅两秒扫描进程，不加载 Qt。未知权限状态不当作 Codex 退出。
- 独立 bailong-codex-watch.service 通过原设置页开关立即启停；触发的 GUI 使用 systemd-run 创建 bailong-codex-pet.service，避免停止监听时被同一 cgroup 杀死。普通开机启动仍只登记、不立即启动，原 app/Windows 逻辑未变；随 Codex 关闭尚未接入。
- Autostart 管理器支持独立单元和监听参数，启用失败恢复原文件与登记状态。调用宿主 systemctl/systemd-run 前恢复 PyInstaller LD_LIBRARY_PATH。临时服务通过 D-Bus 传参，仅美元变量需转义，不能套用 unit 文本的百分号转义；真实 systemd 合成路径验证通过。
- 108 项回归、actionlint 及 diff 检查通过。独立数据目录实测真实 Codex 启动触发、手动关闭不重拉起、关闭监听保留 GUI；监听进程未映射 Qt，5 秒短采样单核 CPU 1.2%、RSS 18.3 MiB。测试服务已清理，日常开关未开启；未退出用户 Codex、未重新登录及打包验收。证据 work/linux-autostart/watch-integration.log。

## Linux systemd 自启动（2026-10-25）

- linux_app/autostart.py 只替换 Linux 进程内 desktop、desktop_services、desktop_settings 的已导入启动函数，Windows app/ 源码不变。服务采用 graphical-session.target 的 WantedBy/After/PartOf，正常退出不重启；开关只 enable/disable，不用 --now。没有默认开启日常自启动，也没有启用 linger。
- 源码必须保留虚拟环境 sys.executable 的路径，不能 resolve 为系统 Python。AppImage 只在 frozen 且当前可执行文件位于 APPDIR 时采用经检查的外部 APPIMAGE；不存在则报错，不能登记临时路径。ExecStart 对引号、反斜线、百分号和美元符号分别转义，保留数据路径和 Codex 参数，桌面每次登录自动识别。
- 手工同名服务不覆盖，写入原子替换，启用失败恢复原文件与登记状态。systemctl 调用仅发生在设置读取/应用时，无后台轮询，每次等待上限 5 秒。服务操作仍在原同步设置流程中；没有做 UI 卡顿性能保证。
- 临时 bailong-autostart-validation.service 已在真实 systemd 用户管理器完成启用、ExecStart 特殊字符验证、执行和禁用，并删除该测试文件。Type=simple 的 start 返回不等于子进程已经写完测试结果，验证需等待结果文件。未注销登录验收，未新打包 AppImage。

## niri 人物输入区域（2026-10-25）

- `linux_app/wayland_input.py` 仅由 niri 入口安装，使用 QWindow mask 设置 Wayland 输入区域，不设置 QWidget mask；阈值位图从 KDE 实现提取到 input_shape.py，KDE 行为保持。Qt 6.9.2 Wayland 将空 mask 解释为整窗输入，空帧必须使用窗口外的非空矩形，不能传空 QRegion。输入区域随 surface commit 生效，设置后补一次绘制；同帧缓存防止形成持续重绘循环。
- 输入范围使用 Wayland 逻辑坐标；按住/原生拖动时保留整窗输入，确保原 niri 的 Leave/Enter 松手交接不会因人物姿态变化而失效。隐藏时不计算，计时器只在绘制后单次触发。窗口句柄、帧、翻转、大小和按住状态变化会更新区域。
- 95 项本地回归和 actionlint 通过，8 秒原生协议采样确认 set_input_region、无解码错误并正常退出。用户验收透明角落穿透、人物点击拖动、松手动画和气泡恢复均正常。独立诊断实例 10 秒短采样单核 CPU 28.6%、RSS 274.8 MiB，含动画及人工交互，不代表长期平均或性能对照。未改 app/Windows 入口；未重新打包，未完整验收分数缩放和跨屏热插拔。诊断日志在忽略目录 work/linux-validation/input-*。
- PR 跟进自动化 kde-pr 已删除，automation.toml 已不存在；先前暂停调用虽返回成功，但后续复核文件仍标 ACTIVE，不能只凭更新响应宣称已停用。

## PR #1 review 修复（2026-10-25）

- 维护者指出无条件把 Codex CLI 挂到 /tmp/bailong-codex 会破坏相邻文件查找。包装器现在始终在原路径执行；未被遮蔽的安装不重定位，CODEX_HOME 内的顶层安装子树（如 packages/）整体只读挂回原位置，保留脚本、模块与资源；/tmp 内的完整安装同理。根层 config/auth 仍只读，运行时文件仍只存在于临时 home。直接位于被遮蔽根目录的单个启动器明确拒绝，不猜测或绕过依赖。
- KDE 原 createAlphaMask 的阈值为 128，与 DesktopPet.alpha_hit 的 12 不同。现在提取 Alpha8，通过 Pillow 的 C 层查表按 alpha >= 12 打包为 LSB 位图，仅修改 ShapeInput；不裁切视觉边缘，不在 GUI 做逐像素 Python 循环。niri 目前没有逐像素输入区域，不能称它已遵循这一阈值，本次不顺带修改 niri。
- 修复后重新验证 190 项（Linux 适配/公告刷新 93 项）；新增合成相邻 helper/资源、配置/认证只读、运行时文件不外泄、alpha 11/12/127/128 及全部 alpha、四档 DPR 与水平翻转回归。真实 CLI 素材/TLS/额度自检重新通过。512px 位图转换 100 次微基准中位 0.383ms、最大 0.585ms，不代表整个 GUI 帧耗时。
- 本轮重新核对 9 组实际 Qt/X11 坐标、物理输入区和关闭置顶状态，无回调异常；21.22 秒含抓图及新索引的采样中 CPU 耗时 12.11 秒、末端 RSS 329.8 MiB，不是闲置平均，也未做同负载性能对照。记录在忽略目录 work/kde-review-validation。初始提交人工鼠标确认与本轮自动/原生验证分别记录；不声称重新做过 niri/Windows 人工验收或 KDE 打包验收。下面的初始提交记录保留当时结果，不能替代本轮 review 修复验证。

## KDE 适配与独立桌面入口（2026-10-25）

- KDE 变更基于 helantianshen/main 的 `3144a67`（v1.0.0 + Linux/niri 基线），只提交源码适配，未制作或发布安装包。
- 按上游 issue #2 的隔离与验收建议整理：niri 使用独立 `run_niri.py`，KDE 使用独立 `run_kde.py`；两者固定自己的桌面，共享 Linux 生命周期。`run_linux.py` 保留自动选择和 `--desktop kde/niri` 兼容入口。Qt 在后端选定后才导入，不要把 Qt 原生 Wayland 的虚拟坐标当作 KDE 实际窗口位置。
- `linux_app/kde.py` 使用 X Shape 的 ShapeInput 区域实现透明像素鼠标穿透，不调用 QWidget.setMask 裁切视觉透明边缘。按 DPR 生成物理像素位图，原画、变换与人物大小保持。单次事件计时器在绘制后合并更新，隐藏/同帧不重复上传。
- Qt 6.9.2 切换置顶时可能重建 QWindow，而 QWidget.winId() 仍返回旧 ID；必须使用 windowHandle().winId() 操作 X11 资源。初轮探针因旧 ID 误报 BadWindow；改正后原生坐标、尺寸、置顶状态和命中区均已重新核对。
- 初始提交曾把 CODEX_HOME 内的 CLI 单文件重定位到沙箱 /tmp/bailong-codex；该实现会破坏相邻运行依赖，已被上面的 review 修复替换，不得恢复。config/auth 只读及运行时隔离继续保留。
- 桌面进程识别不再根据 CLI 父目录猜 ChatGPT 路径，而是确认同名 Electron 主程序旁的 resources/app.asar 并排除 --type 子进程，允许 CLI 与桌面程序分开安装。
- 新建 Python 3.12.15 / PySide6 6.9.2 虚拟环境，32 个轻量素材文件逐项 SHA-256 核对。185 项回归及 app/linux_app/tools 和三个 Linux 入口编译检查通过；真实额度、Token、IPC 与公告已接通。Evernight Vista 44.0.1（Fedora 44 衍生）、x86_64、Plasma / KWin 6.7.5 Wayland、200% 缩放下实际 X11 坐标与 Qt 目标匹配，覆盖程序化移动、设置/聊天、日报、分离、胶囊往返、人物 1.0/1.4 倍及取消置顶。
- 用户人工确认真实鼠标拖动、松手后的气泡跟随和透明区域点击正常。XTest 在本会话未送达角色，不能用注入替代该反馈；其他缩放、热插拔、多屏、长期运行和真实全屏播放器未验收。原 Linux 预览版的其他功能边界仍保留。
- 原生切换探针的 21.63 秒采样包含多次控件抓图，进程 CPU 耗时 9.15 秒、末端 RSS 276.2 MiB；日常实例另一次 8 秒短采样为单核 CPU 17.9%、末端 RSS 349.1 MiB。这些不是长期平均、性能优化对照或显示帧率。诊断、截图和数据均在忽略目录 work/kde-validation，日常实例使用 XDG 数据目录，未修改桌面全局规则。
- 运行与验证入口见 docs/KDE.md，其中按 issue 清单逐项区分已验证、未专项验收和未实现。会话跳转、视频全屏让位、Windows 更新/安装管理未适配，不把保留的 UI 入口视为 Linux 支持。KDE 日常启动 `.venv/bin/python run_kde.py`；已有日常实例时先从托盘退出，不要为重复启动删除有效锁。

## 既有基线与历史记录

开始改动前先读 `AGENTS.md`，再读本文件，随后核对当前源码和版本对应的验收记录。不要把旧版验证结果当作新版结果。

- 当前公开基线 v0.9.9 / UI87。完整 Windows 包和程序更新包按同一源码构建；高清素材是独立、按内容哈希校验的资源。
- 状态来自 IPC 与本机日志。IPC 已终止的回合可能在稍后才读到同回合日志；已关闭回合不能被重新打开，新回合要用不同的回合编号进入。
- `父UUID_分支UUID.jsonl` 可能是用户编辑消息后形成的同一对话日志分支：若元数据归属父会话且首个回合是根用户操作，要用父会话 ID 显示和跳转。真实代理子会话可能有相似文件名，应凭自身元数据或代理归属判断。没有回合编号的完成提醒无法自动确认，恢复时清理，也不应再次创建。
- 旧 Token 历史库被锁或暂时不可读时保留迁移待重试状态。只有确认迁移完成或旧库确实无需迁移后，才能写入来源标记；旧库原文件不移动。
- 卡片、人物与日报的形变要检查实际窗口交接。截图覆盖层和原生控件重复布局会产生闪烁或震颤；不能仅凭定时器数值推断桌面帧率。
- 人物自动移动以手动放置点为中心，默认仅水平。自动位置保存不能反过来更新活动中心。
- 高 DPI 下绘制、点击、拖动必须共用坐标换算。状态图标静置卡顿曾来自粗粒度计时和主线程重复磁盘扫描；缓存只作显示提示，启用素材前仍完整校验。
- 发布前确认 GitHub 副本与本地源版本一致，完整包、程序包和校验清单全部准备好再公开。不要把运行时数据库、账号凭据、日志或角色动画写入 Git 历史。
- 公开版本只按 GitHub 上一稳定版进位；本机 v1.0.4 与公开 v1.0.0 分离。仅卡片发布用仓库内 tools/pyinstaller_keep_files.py，不能依赖本机未跟踪的 本地实装 辅助脚本。构建输出要使用全新路径；完整包、程序更新包、仅卡片包和独立轻量资源分别验 SHA 后再发布。

## Linux 隔离最小验证（2026-10-25）

- `tools/linux_probe.py` 复用原 GUI 与 IPC 解析器；运行方法及证据边界见 `docs/LINUX_VALIDATION.md`。Python 3.12 虚拟环境在 `.venv`，状态和素材在 Git 忽略的 `work/linux-validation`。
- 原生 Wayland 下 Qt 的 `move()` 可改变应用内部坐标，而 niri 实际窗口位置不变；不能用 QWidget.geometry() 单独验证桌宠移动和气泡定位。
- XWayland 的工具窗口未出现在本机 niri windows 列表；Qt 坐标变化及 ABOVE 属性均不足以证明实际定位、层级和拖动通过。用户确认显示基本正常但拖动异常，尚未区分后端验收。
- IPC 两次订阅收到真实工作中状态，28 项既有状态解析测试通过；真实完成/审批/压缩及 Windows 无回归仍未验收。


### Linux 探针真实数据接入（2026-10-25）

PyCharm 配置已启用 `--live`。Linux 专用适配集中在 tools/linux_live.py 与 tools/linux_codex_readonly，未修改 app 生产模块。实际使用 Unix IPC、会话日志、只读 SQLite 和沙箱化的账户额度 RPC；桌宠状态在 work/linux-validation/state-live，演示状态独立。bwrap 使用临时 Codex home 加只读 config/auth 挂载；仅根目录只读会使当前 CLI 初始化失败，因此必须为运行时数据库保留临时可写空间。不得降级为无沙箱查询。

40 秒 offscreen 测试确认 IPC、额度查询和 Token 统计可用，28 个既有测试通过；保护文件前后内容一致。会话额度会按原规则覆盖较旧接口额度，界面来源不一定一直显示接口。GTK color-mix 来自系统 GTK 3 CSS，探针只清空本进程主题桥接，Qt 仍为 Fusion。需用户停止旧 PyCharm 实例后重启；拖动、完整状态转换和跨平台视觉一致性仍待验收。详情见 docs/LINUX_VALIDATION.md。


### niri 原生拖动与透明画布（2026-10-25）

用户人工确认最终一轮拖动、持续拎起动画、松手后气泡定位正常，矩形边框消失。PyCharm 改为 `gui --backend wayland --niri --live --manual --seconds 3600`，适配仅在 tools/linux_niri.py，未编辑 app 生产源码。XWayland 诊断抓到虚拟全局坐标反馈累加；原生移动采用 startSystemMove，气泡依据 niri WindowLayoutsChanged 的实际坐标定位。MoveFloatingWindow 的 SetFixed 基于工作区原点，不能直接传 Qt/IPC 的屏幕坐标；当前使用实际坐标差 AdjustFixed。

Qt 6.9 原生移动会发送模拟松手，不能据此结束动画；当前忽略该事件，等待 Leave 后 Enter。气泡不能 hide/show 重新映射，否则 niri 会先居中；使用 QGraphicsOpacityEffect 仅隐藏绘制，松手定位后等待本机弹簧动画约 700ms 恢复。33 个针对性测试通过；原 test_native_interactions 的 3 失败、1 错误未解决且未纳入通过数，该测试没有加载适配且含缺失素材。新代码、现有 Windows 入口和实际 Windows 回归验收需区分。

为去除透明画布矩形阴影，在本机 ~/.config/niri/__custom__.kdl 末尾添加仓库 configs/niri-probe.kdl 的 include，仅作用于 app-id bailong-linux-probe。备份在 work/linux-validation/niri-custom-before.kdl，niri validate 通过；未改 GTK 主题、Codex 配置或系统 Python。后续移植重点：分离气泡、其他面板、跨屏及位置持久化；本次人工确认不覆盖这些路径。


### Linux 持续运行入口（2026-10-25）

新增根目录 run_linux.py，装配入口为 linux_app/launcher.py，无演示数据、截图采样或自动退出计时。原 tools/linux_live.py、tools/linux_niri.py、tools/linux_codex_readonly 移至 linux_app/live.py、linux_app/niri.py、linux_app/codex_readonly；验证脚本和测试共用这些模块，运行时平台替换使用可恢复的上下文管理器，未修改 app 生产源码。requirements-linux.txt 为共享依赖源，原验证依赖文件引用它。

PyCharm 配置文件为 .run/Bailong Linux.run.xml，名称「桌宠 Linux」，使用项目 Python 3.12 .venv，启动 run_linux.py，无参数。niri 现有规则扩展为同时匹配正式 bailong-linux 与原 bailong-linux-probe，无新增全局主题改动。

默认自身状态位于 XDG_DATA_HOME/codex-bailong/BailongEnhanced（本机 ~/.local/share/codex-bailong/BailongEnhanced）。首次仅迁移验证阶段的设置和已校验素材，后续保留设置/素材选择；凭据不复制，Codex 数据源仍只读，额度程序仍使用 bwrap。QLockFile 使用零过期时间防止长期运行后误判；同目录重复启动已拒绝。SIGINT/SIGTERM 关闭窗口及工作线程并释放目录锁。

36 个针对性测试通过，实际正式入口验证额度、Token、IPC 均正常，SIGTERM 退出码 0、目录锁已释放。config.toml/auth.json/gtk.css 内容保持一致。未做整小时耐久测试，时限移除依据正式入口没有生命周期计时器。一次启动后 10 秒采样 CPU 约占单核 20.6%，早期 RSS 约 259 MiB，包含角色动画与实时监测，不能视为长期平均或性能优化结论。其他既有移植边界保留，详见 docs/LINUX.md。


### niri 自主走动（2026-10-25）

Linux 正式入口不再强制 wandering=False；首次升级开启并写 linux_wandering_ready 标记，之后保留用户暂停状态。仅 linux_app/niri.py 适配 DesktopPet 的 Python 坐标读写与 start/stop_walk，原移动路径、范围、速度、随机调度和动画选择仍使用 app 原实现，app 源码未修改。

actual_position 将 niri 输出内位置加上当前 QScreen 逻辑原点；走动请求保留最新目标，33ms 计时器仅在有移动时运行，等布局变化确认后才提交下一增量，1500ms 无确认则停止本次走动。鼠标按下通过原 stop_walk 路径清除目标与计时器，原生拖动结束后待实际布局恢复再更新 wander_home。气泡沿用现有布局订阅跟随。

用户确认会走动，询问被拖走姿态；已核实原素材没有 moveAnimations，原 start_walk 回退 dragAnimation，未更改素材/动画。两分钟采样含 walk/drag/landing/idle，气泡布局误差中位数0、最大2逻辑像素、异步连接采样峰值1；另一真实 niri 窗口测试在走动中注入鼠标按下后位置保持不变，超出边界目标被约束到完整画布内。41项针对性测试通过；跨屏、不同缩放和所有输入设备尚未完整人工验收。详情与重现证据在 docs/LINUX.md、忽略目录 work/linux-validation/walk-result.json 和 walk-contract.json。

### Linux/niri 位置持久化

新增 linux_app/placement.py，仅在 Linux 适配安装期间替换保存和恢复入口。Windows 初始化时会调用 save_settings，而 Wayland 窗口此时只有占位坐标，因此必须保留原 screen_position，等 niri 确认布局后再更新。输出名称从 WorkspacesChanged 映射取得，不能依赖跨屏时可能滞后的 QWidget.screen。恢复按显示器、输出内坐标分两阶段确认，气泡跨工作区也须先确认再计算相对增量。位置锁不阻止恢复；缺失输出回退首个 Qt 屏幕。45 项针对性测试通过，双屏、真实重启、位置锁与缺失输出配置在独立状态目录实测通过，证据 work/linux-validation/placement-*.json。未改 app 目录或 Windows 入口，也未证明全部 Windows 专属功能已移植。

### Linux 重置公告卡片一直查询中

正式入口遗留 refresh_reset_feed 空替换且没有创建 ResetThread，导致 reset_snapshot 永久为 None。已去掉空替换并在 launcher.create_pet 连接原 ResetThread 的 ready、failed、diagnostic、busy、completed 信号后启动，原关闭流程负责停止线程。无须改 app 或 Windows 入口。52 项公告、刷新与启动相关测试通过；独立状态目录的真实 GUI 启动实测公告接口 0.79 秒返回 available/ok，卡片状态 empty、文案「暂无安排」，证据 work/linux-validation/reset-result.json。公告为第三方公开信息，不是本机账户额度到账保证。

### Linux 面板几何桥接

linux_app/surfaces.py 仅替换 CompactBubble、DailyReport、NativeLanding 的几何读写，保留原逻辑目标与原画布动画，niri 布局确认后提交下一次增量。日报窗口透明度使用 QGraphicsOpacityEffect，因为 Wayland 原生 windowOpacity 不受支持。DesktopPet.geometry 同步实际布局；缩放位移在 apply_settings 结束后提交，避免被关闭走动时的 stop_walk 清除。分离气泡采用 startSystemMove，模拟松手与实际结束分开处理。原 app 目录无改动。

原生窗口阶段检查见忽略目录 work/linux-validation/surface_check.py、surfaces-result.json、surface-check.log，稳定位置误差 0–1 逻辑像素，设置/聊天抓图已检查；位置恢复回归通过。21 项 Linux 测试通过；原 55 项面板测试中两项 test_bubble_resize 锚点测试失败（该次运行没有安装 Linux 适配），日志 gui-unit.log。动画闪跳、分离拖动及多屏交互仍需用户人工验收，不可写成全部视觉一致性已证明。测试进程均已退出。

### Linux 便携包及 AppImage

独立构建环境为 work/linux-build/venv（Python 3.12.14），固定依赖 tools/requirements-linux-build.txt；构建 tools/build_linux.py 使用 PyInstaller onedir 平铺布局，resources ROOT 在冻结后取可执行文件父目录。包内只包含已逐项 SHA256 校验的轻量素材，不从验证 state 或日常设置生成发布配置。tools/package_linux.py 从同一目录生成 tar.zst 与 AppImage；官方工具和运行时 SHA 固定在 tools/appimage-tools.lock.json。包内资源只读，用户数据目录沿用原 Linux 默认位置。

运行时 --check-runtime 完整校验素材、初始化 TLS、查询真实额度。宿主 Codex 查询前恢复 LD_LIBRARY_PATH_ORIG；退出信号处理器仅设置标记，由 Qt 定时器执行关闭，避免信号重入 Qt notify 时崩溃。严格测试沙箱须 --dev-bind /dev /dev，否则 /dev/null 权限错误会导致误判额度查询失败。AppImage 在用户命名空间可能不能执行 FUSE 挂载，因此分别测试正常挂载和 --appimage-extract-and-run。

本机 niri 的桌宠规则已原样复制到 ~/.config/niri/bailong-linux.kdl，仅替换 __custom__.kdl 中该条 include，niri validate 通过，原文件备份 work/linux-build/niri-custom-before.kdl。源码可移走而不影响规则。Windows app 目录未改动，未提交或推送。
