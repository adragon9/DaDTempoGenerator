# Package imports
import sys, json, os

# Class imports
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget,
    QPushButton, QVBoxLayout, QLabel,
    QProgressBar, QCheckBox, QHBoxLayout,
    QComboBox, QListView, QDialog,
    QMenu, QToolTip, QWidgetAction
)
from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal,
    QThread, QStringListModel, QTimer,
    QUrl, QElapsedTimer, QPoint,
    QEvent, QTimer
)
from PyQt6.QtGui import (
    QCloseEvent, QStandardItem, QStandardItemModel
)
from PyQt6.QtMultimedia import (
    QSoundEffect
)

# Custom class imports
import scripts.FileManagement as fm
import scripts.SongAnalyzer as sa
import helpers.DebugHelper as dh
import scripts.DataManagement as dm

# Splash screen
try:
    import pyi_splash # type:ignore
    pyi_splash.close()
except:
    pass

# Class Overrides
class CenterAlignedStringModel(QStringListModel):
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        return super().data(index, role)

class PositionedListView(QListView):
    def viewportEvent(self, e):
        assert e is not None
        if e.type() == QEvent.Type.ToolTip:
            index = self.indexAt(e.pos()) # type: ignore

            if index.isValid():
                text = self.model().data( # type: ignore
                    index, Qt.ItemDataRole.ToolTipRole
                )
                if text:
                    position = e.globalPos() + QPoint(12, 0) # type: ignore
                    QToolTip.showText(position, str(text), self.viewport())
                    return True

            QToolTip.hideText()
            e.ignore()
            return True

        return super().viewportEvent(e)

# Worker
class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    main_messenger = pyqtSignal(str)
    sub_messenger = pyqtSignal(str)
    list_delivery = pyqtSignal(list)
    
    def __init__(self, song_analyzer: sa.SongAnalyzer, single_scan: bool = False, folder_name: str|None=None):
        super().__init__()
        self.song_analyzer = song_analyzer
        self.song_analyzer.set_signals(progress_signal=self.progress, 
                                       main_messenger=self.main_messenger, 
                                       sub_messenger=self.sub_messenger, 
                                       list_delivery=self.list_delivery)
        self.single_scan = single_scan
        self.folder_name = folder_name
        
    def run(self):
        try:
            self.song_analyzer.load_predictor()
            if not self.single_scan:
                self.song_analyzer.run_processor()
            else:
                self.song_analyzer.run_single_shot(self.folder_name)
        finally:
            self.finished.emit()

# Windows
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # App styling
        style_sheet = """
            QWidget {
                background: #0e0e0e;
            }

            QLabel {
                font-size: 14pt;
            }
            
            QComboBox {
                font-size: 14pt;
                text-align: center;
                padding-left: 8px;
                padding-right: 8px;
            }
            
            QComboBox:hover {
                background: #2c2c2c;
            }
            
            QProgressBar {
                border: 2px ridge #404040;
                border-radius: 8px;
                background: #FFF;
                height: 12px;
                min-height: 24px;
                text-align: center;
                font: 12px;
                color: #000
            }
            
            QProgressBar::chunk {
                background: #3a5c34;
                border-radius: 5px;
            }
            
            QPushButton {
                background: #3a5c34;
                border-radius: 8px;
                font-size: 14pt;
                height: 36px;
            }
            
            QCheckBox {
                border-radius: 8px;
                font-size: 14pt;
            }
            
            QCheckBox::indicator:unchecked{
                background: #fff;
                border-radius: 4px;
            }
            
            QCheckBox::indicator:unchecked:hover{
                background: #bebebe;
            }
            
            QCheckBox::indicator:checked{
                background: #3a5c34;
                border: 2px solid #fff;
                border-radius: 4px;
            }
            
            QCheckBox::indicator:checked:hover{
                background: #1a2518;
            }
            
            QPushButton:hover {
                background: #1a2518;
            }

            QPushButton:pressed {
                background: #6ca760;
            }
            
            QScrollBar:vertical {
                background: #eee;
                border-radius: 4px;
                width: 12px;
                margin: 0;
            }

            QScrollBar::handle:vertical {
                background: #888;
                min-height: 24px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical:hover {
                background: #555;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """
        self.setStyleSheet(style_sheet)
        self.file_manager = fm.FileManager()
        self.error_logger = dh.LogManager(f"{Path(__file__).stem}_error-log.log")
        self.info_logger = dh.LogManager(f"{Path(__file__).stem}_info-log.log")
        self.state_manager = dm.MainWindowStateManager()
        self.song_analyzer = sa.SongAnalyzer(file_manager=self.file_manager, main_window_states=self.state_manager)
        
        self.song_analyzer.build_songlist(self.file_manager.get_imported_songs_path())
        self.song_names = self.song_analyzer.get_song_names()
        self.song_paths = self.song_analyzer.get_song_paths()
        self.paired_path_and_names = zip(self.song_names, self.song_paths)
        self.paired_path_and_names = sorted(self.paired_path_and_names, key=lambda x: x[0])
        self.song_count = self.song_analyzer.get_song_count()
        
        self.worker_thread = None
        self.percent_processed = None
        
        self.persistent_settings = self.file_manager.get_previous_user_choices()
        self.settings_init()
            
        self.ui_init()
        
    def ui_init(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        display_layout = QVBoxLayout()
        
        # List view
        default = self.song_analyzer.get_song_names()
        self.main_view = PositionedListView()
        self.list_view_model = QStandardItemModel(self.main_view)
        self.update_list_model(default)
        self.main_view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.main_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.main_view.setAlternatingRowColors(True)
        
        self.main_layout.addWidget(self.main_view, stretch=6)
        
        # Labels
        self.main_label = QLabel()
        self.main_label.setText("Idle")
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)
        
        self.message_label = QLabel()
        self.message_label.setHidden(True)
        self.message_label.setText("")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignTop)
        
        self.main_layout.addLayout(display_layout, stretch=1)
        display_layout.addWidget(self.main_label, stretch=1)
        display_layout.addWidget(self.message_label, stretch=1)
        
        # Checkboxes
        checkbox_layout = QHBoxLayout()
        
        self.check_adjust_bpm = QCheckBox("Adjust Low BPM")
        self.check_fresh_run = QCheckBox("Fresh Scan")
        
        # Add to layout        
        self.main_layout.addLayout(checkbox_layout, stretch=1)
        checkbox_layout.addWidget(self.check_adjust_bpm, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)
        checkbox_layout.addWidget(self.check_fresh_run, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)
                        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        self.main_layout.addWidget(self.progress_bar, Qt.AlignmentFlag.AlignCenter)
        # Buttons
        self.run_button = QPushButton()
        self.run_button.setText("Run")
        self.bw_button = QPushButton()
        self.bw_button.setText("Calibrate Offset")
        self.bw_button.setStyleSheet("""
                                        QPushButton{
                                            background: #4b727c;
                                        }
                                        
                                        QPushButton:hover{
                                            background: #2c474e;
                                        }
                                        
                                        QPushButton:pressed{
                                            background: #92bec9;
                                        }
                                     """)
        
        self.main_layout.addWidget(self.bw_button, Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.run_button, Qt.AlignmentFlag.AlignCenter)
        
        
        # Connections
        self.run_button.clicked.connect(self.run_button_action)
        self.bw_button.clicked.connect(self.open_beat_window)
        self.main_view.customContextMenuRequested.connect(self.display_main_view_context)
        
        # Checkboxes
        checkboxes = self.main_widget.findChildren(QCheckBox)
        for checkbox in checkboxes:
            checkbox.clicked.connect(self.update_checkboxes)
            
        # Set check states
        if self.state_manager.adjustBPM == 2:
            self.check_adjust_bpm.setCheckState(Qt.CheckState.Checked)
        else:
            self.check_adjust_bpm.setCheckState(Qt.CheckState.Unchecked)

        if self.state_manager.freshScan == 2:
            self.check_fresh_run.setCheckState(Qt.CheckState.Checked)
        else:
            self.check_fresh_run.setCheckState(Qt.CheckState.Unchecked)
        
    def settings_init(self):
        if self.persistent_settings:
            print(self.persistent_settings)
            self.state_manager.adjustBPM = self.persistent_settings["adjustBPM"]
            self.state_manager.globalOffset = self.persistent_settings["globalOffset"]
            self.state_manager.freshScan = self.persistent_settings["freshScan"]
            print(self.state_manager)
            
    def update_list_model(self, strings: list):
        strings.sort()
        for name, path in self.paired_path_and_names:
            item = QStandardItem(name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Find the folder that best fits the song
            item.setToolTip(path)
            self.list_view_model.appendRow(item)
        self.main_view.setModel(self.list_view_model)
        
    def progress_action(self, signal):            
        self.percent_processed = int((signal / self.song_count)*100)
        self.progress_bar.setValue(self.percent_processed)
    
    def main_messenger_manager(self, signal):
        self.message_label.clear()
        self.main_label.setText(signal)
    
    def sub_messenger_manager(self, signal):
        self.message_label.clear()
        self.message_label.setText(signal)
    
    def list_manager(self, signal):
        self.update_list_model(signal)
    
    def run_button_action(self, single_scan: bool = False):
        """Launch the CPU‑heavy job in a worker thread."""
        if self.worker_thread and self.worker_thread.isRunning():
            return

        # Create the QThread + Worker pair
        self.worker_thread = QThread()
        if not single_scan:
            self.worker = Worker(self.song_analyzer)   # keep reference
        else:
            self.worker = Worker(self.song_analyzer, True, self.list_view_model.data(self.main_view.currentIndex(), Qt.ItemDataRole.DisplayRole))
        self.worker.moveToThread(self.worker_thread)
            
        # Connect signals & slots
        self.worker_thread.started.connect(self.worker.run)
        if not single_scan:
            self.worker.progress.connect(lambda a: self.progress_action(a))
        self.worker.sub_messenger.connect(lambda a: self.sub_messenger_manager(a))
        self.worker.main_messenger.connect(lambda a: self.main_messenger_manager(a))
        self.worker.list_delivery.connect(lambda a: self.list_manager(a))
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        
        # Keep disabled #
        # self.worker.finished.connect(self.worker.deleteLater)
        # self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        # Disable elements
        self.disable_elements()
        self.worker_thread.start()
            
    def on_worker_finished(self):
        """Called *after* the background thread quits."""
        # Re‑enable elements
        self.enable_elements()
        if self.percent_processed:
            self.main_label.setText(f"{self.percent_processed}% of songs processed!")
            QTimer.singleShot(3000, lambda: self.main_label.setText("Idle"))
            self.percent_processed = None
        else:
            self.main_label.setText("Idle")
    
    # Element Management
    def disable_elements(self):
        # Buttons
        buttons = self.main_widget.findChildren(QPushButton)
        for button in buttons:
            button.setEnabled(False)
        # Checkboxes
        checkboxes = self.main_widget.findChildren(QCheckBox)
        for checkbox in checkboxes:
            checkbox.setEnabled(False)
        # Comboboxes
        comboboxes = self.main_widget.findChildren(QComboBox)
        for combobox in comboboxes:
            combobox.setEnabled(False)
        # Listviews
        listviews = self.main_widget.findChildren(QListView)
        for list in listviews:
            list.setSelectionMode(QListView.SelectionMode.NoSelection)
            list.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            
        # Show Processing Elements
        self.message_label.setHidden(False)
        
    def enable_elements(self):
        # Buttons
        buttons = self.main_widget.findChildren(QPushButton)
        for button in buttons:
            button.setEnabled(True)
        # Checkboxes
        checkboxes = self.main_widget.findChildren(QCheckBox)
        for checkbox in checkboxes:
            checkbox.setEnabled(True)
        # Comboboxes
        comboboxes = self.main_widget.findChildren(QComboBox)
        for combobox in comboboxes:
            combobox.setEnabled(True)
        # Listviews
        listviews = self.main_widget.findChildren(QListView)
        for list in listviews:
            list.setSelectionMode(QListView.SelectionMode.SingleSelection)
            list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # update stuff.
        self.check_fresh_run.setCheckState(Qt.CheckState.Unchecked)
        
        # Hide Processing Elements
        self.message_label.setHidden(True)
        
    # Connections
    def update_checkboxes(self):
        self.state_manager.adjustBPM = self.check_adjust_bpm.checkState().value
        self.state_manager.freshScan = self.check_fresh_run.checkState().value
        self.file_manager.save_state(self.state_manager)
        # self.state_manager.virtualSurround = self.check_vSurround.checkState().value
        
    def update_comboboxes(self):
        pass
        # self.state_manager.currentSpeakerType = self.combo_audiodevice.currentText()
        # self.state_manager.currentBeatFeeling = self.combo_beatfeel.currentText()
        # self.state_manager.currentController = self.combo_controllertype.currentText()
    
    def display_main_view_context(self, pos: QPoint):
        global_pos = self.main_view.viewport().mapToGlobal(pos) # type:ignore
        menu = QMenu(self.main_view)
        menu.setStyleSheet("""
                           QMenu {
                               background: #000;
                               border-radius: 0px;
                           }
                           """)
        
        def scan_action_wrapper():
            self.run_button_action(True)
            menu.close()
            
        def open_folder_action_wrapper():
            for song, path in self.paired_path_and_names:
                if song == self.list_view_model.data(self.main_view.currentIndex(), Qt.ItemDataRole.DisplayRole):
                    os.startfile(path)
                    break
            menu.close()
                
        a_scan = QWidgetAction(menu)
        a_open_folder = QWidgetAction(menu)
        a_close_menu = QWidgetAction(menu)
        
        button_stylesheet = """
            QPushButton {
                text-align: center;
                background:#000;
                border-radius: 0px;
                font-size: 8pt;
                padding-right: 8px;
                padding-left: 8px;
            }
            QPushButton:hover {
                background:#404040
            }
                
        """
        close_button_stylesheet = """
            QPushButton {
                text-align: center;
                background:#7e3939;
                border-radius: 0px;
                font-size: 8pt;
                padding-right: 8px;
                padding-left: 8px;
            }
            QPushButton:hover {
                background:rgb(178, 57, 57);
            }
                
        """
        
        
        button_a_scan = QPushButton("Scan")
        button_a_scan.setStyleSheet(button_stylesheet)
        
        button_a_open_folder = QPushButton("Open in Explorer")
        button_a_open_folder.setStyleSheet(button_stylesheet)
        
        button_a_close_menu = QPushButton("Close")
        button_a_close_menu.setStyleSheet(close_button_stylesheet)
        
        a_scan.setDefaultWidget(button_a_scan)
        a_open_folder.setDefaultWidget(button_a_open_folder)
        a_close_menu.setDefaultWidget(button_a_close_menu)
        
        button_a_scan.clicked.connect(scan_action_wrapper)
        button_a_open_folder.clicked.connect(open_folder_action_wrapper)
        button_a_close_menu.clicked.connect(menu.close)
        
        menu.addAction(a_scan)
        menu.addAction(a_open_folder)
        menu.addAction(a_close_menu)
        
        selected = menu.exec(global_pos)
        
    def open_beat_window(self):
        beat_window = BeatOffsetTest(self, state_manager=self.state_manager, file_manager=self.file_manager)
        beat_window.open()
        
class BeatOffsetTest(QDialog):
    '''
    EARLY BUILD\n
    Seems to be consistent across different hardware.
    '''
    def __init__(self, parent=None, bpm=120, target_taps=30, state_manager: dm.MainWindowStateManager | None = None,
                 file_manager: fm.FileManager | None = None):
        super().__init__(parent)
        self.setWindowTitle("Beat Offset Test")
        if bpm <= 0:
            raise ValueError("bpm must be greater than 0")
        self.state_manager = state_manager
        self.file_manager = file_manager
        self.bpm = bpm
        self.target_taps = target_taps
        self.beat_interval_ns = round(60_000_000_000 / bpm)
        self.offsets_ms = []
        self.running = False

        self.status_label = QLabel(f"Ready a sound will play at {bpm} bpm tap to the beat {target_taps} times to finish.\nPress 'space' or click the tap button." )
        self.result_label = QLabel("")
        self.start_button = QPushButton("Start")
        self.tap_button = QPushButton("Tap")
        self.visualizer_button = QPushButton(" ")
        
        # Setup tap button
        tap_stylesheet = """
            QPushButton{
                background: #4b727c;
                border-radius: 32px;
                margin: 12px;
            }
            
            QPushButton:hover{
                background: #2c474e;
            }
            
            QPushButton:pressed{
                background: #92bec9;
            }
        """
        
        self.tap_button.setStyleSheet(tap_stylesheet)
        size = 96
        self.tap_button.setFixedWidth(size)
        self.tap_button.setFixedHeight(size)
        self.tap_button.setEnabled(False)
        
        # Visualizer button setup
        self.visualizer_normal_style = """
            QPushButton {
                background-color: #4b727c;
                border: none;
                border-radius: 24px;
            }
        """
        self.visualizer_beat_style = """
            QPushButton {
                background-color: #92bec9;
                border: none;
                border-radius: 24px;
            }
        """
        self.visualizer_button.setFixedSize(size, size)
        self.visualizer_button.setStyleSheet(self.visualizer_normal_style)
        
        self.visualizer_reset_timer = QTimer(self)
        self.visualizer_reset_timer.setSingleShot(True)
        self.visualizer_reset_timer.timeout.connect(lambda: self.visualizer_button.setStyleSheet(self.visualizer_normal_style))

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_label)
        layout.addWidget(self.visualizer_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.tap_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.start_button)
        
        # Load a short WAV click from the same folder as this script.
        self.click = QSoundEffect(self)
        self.click.setSource(
            QUrl.fromLocalFile(".\\sounds\\BeatOffsetTest.wav")
        )
        self.click.setVolume(0.20)  # 0.0 to 1.0

        self.clock = QElapsedTimer()

        self.beat_timer = QTimer(self)
        self.beat_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.beat_timer.setSingleShot(True)
        self.beat_timer.timeout.connect(self._on_scheduled_beat)

        self.last_tapped_beat = None

        self.beat_index = 0
        self.beat_timer.setSingleShot(True)
        self.beat_timer.timeout.connect(self._on_scheduled_beat)
        
        self.start_button.clicked.connect(self.start_test)
        self.tap_button.clicked.connect(self.record_tap)

    def start_test(self):
        self.offsets_ms.clear()
        self.running = True
        self.last_tapped_beat = None

        self.start_button.setEnabled(False)
        self.tap_button.setEnabled(True)
        self.tap_button.setFocus()
        self.result_label.clear()
        self.status_label.setText("Listen to the beat and tap along.")

        self.clock.start()
        self.beat_index = 0
        self.play_beat()  # first beat, at the start of the test
        self.beat_index = 1
        self._schedule_next_beat()

    def _schedule_next_beat(self):
        now_ns = self.clock.nsecsElapsed()
        deadline_ns = self.beat_index * self.beat_interval_ns

        # If the UI was delayed, skip past missed deadlines rather than
        # firing several beats in a burst.
        if deadline_ns <= now_ns:
            self.beat_index = now_ns // self.beat_interval_ns + 1
            deadline_ns = self.beat_index * self.beat_interval_ns

        remaining_ns = deadline_ns - now_ns
        delay_ms = max(1, (remaining_ns + 999_999) // 1_000_000)
        self.beat_timer.start(delay_ms)

    def _on_scheduled_beat(self):
        if not self.running:
            return

        self.play_beat()
        self.beat_index += 1
        self._schedule_next_beat()
        
    def play_beat(self):
        self.visualizer_button.setStyleSheet(self.visualizer_beat_style)
        self.visualizer_reset_timer.start(120)
        if self.click.isLoaded():
            self.click.play()
        
    def record_tap(self):
        if not self.running:
            return
                
        elapsed_ns = self.clock.nsecsElapsed()
        beat_number = (elapsed_ns + self.beat_interval_ns // 2) // self.beat_interval_ns
        
        if beat_number == self.last_tapped_beat:
            return

        self.last_tapped_beat = beat_number
        expected_ns = beat_number * self.beat_interval_ns
        offset_ms = (elapsed_ns - expected_ns) / 1_000_000
        self.offsets_ms.append(offset_ms)
        
        self.status_label.setText(
            f"Tap recorded: {offset_ms:+.0f} ms\n"
            f"{len(self.offsets_ms)} of {self.target_taps}"
        )

        if len(self.offsets_ms) >= self.target_taps:
            self.finish_test()
            
    def keyPressEvent(self, a0):
        assert a0 is not None
        if a0.key() == Qt.Key.Key_Space and self.running:
            self.record_tap()
            a0.accept()
        else:
            super().keyPressEvent(a0)

    def finish_test(self):
        self.running = False
        self.beat_timer.stop()
        self.visualizer_reset_timer.stop()
        self.visualizer_button.setStyleSheet(self.visualizer_normal_style)
        self.tap_button.setEnabled(False)
        self.start_button.setEnabled(True)

        if not self.offsets_ms:
            self.status_label.setText("Test finished - no taps were recorded.")
            return

        average_signed = sum(self.offsets_ms) / len(self.offsets_ms)
        average_absolute = sum(abs(x) for x in self.offsets_ms) / len(self.offsets_ms)

        self.status_label.setText(
            f"Test finished - {len(self.offsets_ms)} taps recorded."
        )
        self.result_label.setText(
            f"Average offset: {average_signed:+.0f} ms\n"
            f"Average distance from beat: {average_absolute:.0f} ms"
        )
        
        # Update the global offset
        if self.state_manager != None:
            self.state_manager.globalOffset = round(average_signed)
            if self.file_manager:
                self.file_manager.save_state(self.state_manager)
    
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.running = False
        self.beat_timer.stop()
        self.visualizer_reset_timer.stop()
        self.visualizer_button.setStyleSheet(self.visualizer_normal_style)
        return super().closeEvent(a0)
    
if __name__ == "__main__":     
    app = QApplication(sys.argv)

    mainWindow = MainWindow()
    try:
        with open(Path(".\\data\\config\\settings.json"), 'r') as file:
            data = json.load(file)["version"]
            mainWindow.setWindowTitle(f"DaD Tempo Generator {data}")
    except:
        mainWindow.setWindowTitle("DaD Tempo Generator")
    mainWindow.setMinimumSize(1200, 600)

    mainWindow.show()
    sys.exit(app.exec())