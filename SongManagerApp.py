# Package imports
import sys, json

# Class imports
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget,
    QPushButton, QVBoxLayout, QLabel,
    QProgressBar, QCheckBox, QHBoxLayout,
    QComboBox, QListView, QDialog,
    QMenu
)
from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal,
    QThread, QStringListModel, QTimer,
    QUrl, QElapsedTimer, QPoint,
    QModelIndex
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
                border: 2px solid #555;
                border-radius: 7px;
                background: #FFF;
                height: 24px;
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
                background: #6ca760
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
        self.main_view = QListView()
        default = self.song_analyzer.get_song_names()
        self.liststringmodel = QStringListModel(default)
        self.main_view.setModel(self.liststringmodel)
        self.main_view.setMinimumHeight(400)
        self.main_view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.main_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        self.main_layout.addWidget(self.main_view, stretch=1)
        
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
        if self.state_manager.adjustBPM == 2:
            self.check_adjust_bpm.setCheckState(Qt.CheckState.Checked)
        else:
            self.check_adjust_bpm.setCheckState(Qt.CheckState.Unchecked)
            
        # self.check_vSurround = QCheckBox("Virtual Surround Sound")
        # if self.state_manager.virtualSurround == 2:
        #     self.check_vSurround.setCheckState(Qt.CheckState.Checked)
        # else:
        #     self.check_vSurround.setCheckState(Qt.CheckState.Unchecked)
        
        self.main_layout.addLayout(checkbox_layout, stretch=1)
        checkbox_layout.addWidget(self.check_adjust_bpm, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)
        # checkbox_layout.addWidget(self.check_vSurround, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)
        
        ### MAY NOT BE NEEDED DUE TO CALIBRATION TEST ###
        # # Comboboxes
        # combobox_layout_1 = QHBoxLayout()
        # combobox_layout_2 = QHBoxLayout()
        
        # self.combo_label_1 = QLabel("Audio Device Connection")
        # self.combo_label_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.combo_audiodevice = QComboBox() 
        # self.combo_audiodevice.addItems(self.state_manager.speakerTypes)
        # self.combo_audiodevice.setCurrentText(self.state_manager.currentSpeakerType)
        
        # self.combo_label_2 = QLabel("feels")
        # self.combo_label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.combo_beatfeel = QComboBox() 
        # self.combo_beatfeel.addItems(self.state_manager.beatFeelings)
        # self.combo_beatfeel.setCurrentText(self.state_manager.currentBeatFeeling)
        
        # self.combo_label_3 = QLabel("Controller/Keyboard Connection")
        # self.combo_label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.combo_controllertype = QComboBox()
        # self.combo_controllertype.addItems(self.state_manager.controllerTypes)
        # self.combo_controllertype.setCurrentText(self.state_manager.currentController)

        # self.main_layout.addLayout(combobox_layout_1)
        # self.main_layout.addLayout(combobox_layout_2)
        # combobox_layout_1.addWidget(self.combo_label_1)
        # combobox_layout_1.addWidget(self.combo_audiodevice, stretch=1)
        # combobox_layout_1.addWidget(self.combo_label_2)
        # combobox_layout_1.addWidget(self.combo_beatfeel, stretch=1)
        # combobox_layout_1.addWidget(self.combo_label_3)
        # combobox_layout_1.addWidget(self.combo_controllertype, stretch=1)
        
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
        
        self.main_layout.addWidget(self.run_button, Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.bw_button, Qt.AlignmentFlag.AlignCenter)
        
        # Connections
        self.run_button.clicked.connect(self.run_button_action)
        self.bw_button.clicked.connect(self.open_beat_window)
        self.main_view.customContextMenuRequested.connect(self.display_main_view_context)
        # Checkboxes
        checkboxes = self.main_widget.findChildren(QCheckBox)
        for checkbox in checkboxes:
            checkbox.clicked.connect(self.update_checkboxes)
            
        # Combos
        comboboxes = self.main_widget.findChildren(QComboBox)
        for combobox in comboboxes:
            combobox.currentTextChanged.connect(self.update_comboboxes)
        
    def settings_init(self):
        if self.persistent_settings:
            self.state_manager.adjustBPM = self.persistent_settings["adjustBPM"]
            # self.state_manager.virtualSurround = self.persistent_settings["virtualSurround"]
            # self.state_manager.currentSpeakerType = self.persistent_settings["currentSpeakerType"]
            # self.state_manager.currentBeatFeeling = self.persistent_settings["currentBeatFeeling"]
            # self.state_manager.currentController = self.persistent_settings["currentController"]
            # self.state_manager.currentConfidenceThresh = self.persistent_settings["currentConfidenceThresh"]
            self.state_manager.globalOffset = self.persistent_settings["globalOffset"]
        
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
        self.liststringmodel = QStringListModel(signal)
        self.main_view.setModel(self.liststringmodel)
    
    def run_button_action(self, single_scan: bool = False):
        """Launch the CPU‑heavy job in a worker thread."""
        if self.worker_thread and self.worker_thread.isRunning():
            return

        # Create the QThread + Worker pair
        self.worker_thread = QThread()
        if not single_scan:
            self.worker = Worker(self.song_analyzer)   # keep reference
        else:
            self.worker = Worker(self.song_analyzer, True, self.liststringmodel.data(self.main_view.currentIndex(), Qt.ItemDataRole.DisplayRole))
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
            self.percent_processed = None
        else:
            self.main_label.setText("Idle")
        
    
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
            list.setEnabled(False)
            
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
            list.setEnabled(True)
            
        # Hide Processing Elements
        self.message_label.setHidden(True)
        
    # Connections
    def update_checkboxes(self):
        self.state_manager.adjustBPM = self.check_adjust_bpm.checkState().value
        # self.state_manager.virtualSurround = self.check_vSurround.checkState().value
        
    def update_comboboxes(self):
        pass
        # self.state_manager.currentSpeakerType = self.combo_audiodevice.currentText()
        # self.state_manager.currentBeatFeeling = self.combo_beatfeel.currentText()
        # self.state_manager.currentController = self.combo_controllertype.currentText()
    
    def display_main_view_context(self, pos: QPoint):
        global_pos = self.main_view.viewport().mapToGlobal(pos) # type:ignore
        menu = QMenu(self.main_view)
        
        a_delete = menu.addAction("Scan")
        
        selected = menu.exec(global_pos)
        if selected == a_delete:
            self.run_button_action(True)
        
    def open_beat_window(self):
        beat_window = BeatOffsetTest(self.main_widget, state_manager=self.state_manager)
        beat_window.show()
        
class BeatOffsetTest(QDialog):
    '''
    THIS IS EXTREMELY BETA AND PARTIALLY AI GENERATED.\n
    I EDITED IT TO MAKE IT WORK FAST AND BE AN EXAMPLE TO BUILD OFF OF.\n
    THIS WILL PROBABLY NOT REMAIN AS IS FOR THE FINAL BUILD.
    '''
    def __init__(self, parent=None, bpm=100, target_taps=30, state_manager: dm.MainWindowStateManager | None = None):
        super().__init__(parent)
        self.setWindowTitle("Beat Offset Test")

        self.state_manager = state_manager
        self.bpm = bpm
        self.target_taps = target_taps
        self.beat_interval_ns = 60_000_000_000 / bpm
        self.offsets_ms = []
        self.running = False

        self.status_label = QLabel(f"Ready a sound will play at {bpm} bpm tap to the beat {target_taps} times to finish.\nPress 'space' or click the tap button." )
        self.result_label = QLabel("")
        self.start_button = QPushButton("Start")
        self.tap_button = QPushButton("Tap")
        self.tap_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tap_button)
        layout.addWidget(self.result_label)
        layout.addWidget(self.start_button)

        self.start_button.clicked.connect(self.start_test)
        self.tap_button.clicked.connect(self.record_tap)

        # Load a short WAV click from the same folder as this script.
        self.click = QSoundEffect(self)
        self.click.setSource(
            QUrl.fromLocalFile(".\\sounds\\BeatOffsetTest.wav")
        )
        self.click.setVolume(0.20)  # 0.0 to 1.0

        self.clock = QElapsedTimer()

        self.beat_timer = QTimer(self)
        self.beat_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.beat_timer.timeout.connect(self.play_beat)

        self.last_tapped_beat = None

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
        self.play_beat()
        self.beat_timer.start(round(60_000 / self.bpm))
        # self.end_timer.start(self.duration_seconds * 1000)

    def play_beat(self):
        if self.click.isLoaded():
            self.click.play()

    def record_tap(self):
        if not self.running:
            return
                
        elapsed_ns = self.clock.nsecsElapsed()
        beat_number = round(elapsed_ns / self.beat_interval_ns)
        
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
        if a0.key() == Qt.Key.Key_Space and self.running:
            self.record_tap()
            a0.accept()
        else:
            super().keyPressEvent(a0)

    def finish_test(self):
        self.running = False
        self.beat_timer.stop()
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