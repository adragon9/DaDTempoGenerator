import sys

# Classes
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget,
    QPushButton, QVBoxLayout, QLabel,
    QProgressBar, QCheckBox, QHBoxLayout,
    QComboBox
)
from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal,
    QThread
)

# Custom classes
import scripts.FileManagement as fm
import scripts.SongAnalyzer as sa
import helpers.DebugHelper as dh
import scripts.DataManagement as dm

try:
    import pyi_splash # type:ignore
    pyi_splash.close()
except:
    pass

class Worker(QObject):
    finished = pyqtSignal()          # emitted when run() is done
    progress = pyqtSignal(int)       # optional: percent‑complete

    def __init__(self, song_analyzer: sa.SongAnalyzer, state_manager: dm.MainWindowStateManager):
        super().__init__()
        self.song_analyzer = song_analyzer
        
    def run(self):
        try:
            self.song_analyzer.run_processor(self.progress)
        finally:
            self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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
        
        self.ui_init()
        
    def ui_init(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        self.main_label = QLabel()
        self.main_label.setText("Idle")
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(self.main_label, Qt.AlignmentFlag.AlignCenter)
        
        # Checkboxes
        checkbox_layout = QHBoxLayout()
        
        self.check_adjust_bpm = QCheckBox("Adjust Low BPM")
        self.check_adjust_bpm.setCheckState(Qt.CheckState.Checked)
        self.check_vSurround = QCheckBox("Virtual Surround Sound")
        self.check_vSurround.setCheckState(Qt.CheckState.Unchecked)
        
        self.main_layout.addLayout(checkbox_layout, Qt.AlignmentFlag.AlignCenter)
        checkbox_layout.addWidget(self.check_adjust_bpm)
        checkbox_layout.addWidget(self.check_vSurround)
        
        # Comboboxes
        combobox_layout_1 = QHBoxLayout()
        combobox_layout_2 = QHBoxLayout()
        
        self.combo_label_1 = QLabel("Device type")
        self.combo_label_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_audiodevice = QComboBox() 
        self.combo_audiodevice.addItems(self.state_manager.speakerTypes)
        self.combo_audiodevice.setMinimumWidth(250)
        self.combo_label_2 = QLabel("feels")
        self.combo_label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_beatfeel = QComboBox() 
        self.combo_beatfeel.addItems(self.state_manager.beatFeelings)
        self.combo_beatfeel.setMinimumWidth(250)
        self.combo_label_3 = QLabel("Controller/Keyboard")
        self.combo_label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_controllertype = QComboBox()
        self.combo_controllertype.addItems(self.state_manager.controllerTypes)
        self.combo_controllertype.setMinimumWidth(250)
        
        self.main_layout.addLayout(combobox_layout_1)
        self.main_layout.addLayout(combobox_layout_2)
        combobox_layout_1.addWidget(self.combo_label_1, Qt.AlignmentFlag.AlignCenter)
        combobox_layout_1.addWidget(self.combo_audiodevice)
        combobox_layout_1.addWidget(self.combo_label_2, Qt.AlignmentFlag.AlignCenter)
        combobox_layout_1.addWidget(self.combo_beatfeel)
        combobox_layout_2.addWidget(self.combo_label_3)
        combobox_layout_2.addWidget(self.combo_controllertype, stretch=1)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        self.main_layout.addWidget(self.progress_bar, Qt.AlignmentFlag.AlignCenter)
        
        self.run_button = QPushButton()
        self.run_button.setText("Run")
        
        self.main_layout.addWidget(self.run_button, Qt.AlignmentFlag.AlignCenter)
        
        # Connections
        self.run_button.clicked.connect(self.run_button_action)
        # Checkboxes
        self.check_adjust_bpm.clicked.connect(self.update_checkboxes)
        self.check_vSurround.clicked.connect(self.update_checkboxes)
        # Combos
        self.combo_audiodevice.currentTextChanged.connect(self.update_comboboxes)
        self.combo_beatfeel.currentTextChanged.connect(self.update_comboboxes)
        self.combo_controllertype.currentTextChanged.connect(self.update_comboboxes)
        
    def progress_action(self, signal):
        self.percent_processed = int((signal / self.song_count)*100)
        self.progress_bar.setValue(self.percent_processed)
        try:
            self.main_label.setText(self.song_analyzer.get_progress_string())
        except Exception as e:
            self.error_logger.write(f"Failed to update label text reason: {e}")
            
    def run_button_action(self):
        """Launch the CPU‑heavy job in a worker thread."""
        if self.worker_thread and self.worker_thread.isRunning():
            return

        # Create the QThread + Worker pair
        self.worker_thread = QThread()
        self.worker = Worker(self.song_analyzer, self.state_manager)   # keep reference
        self.worker.moveToThread(self.worker_thread)
            
        # Connect signals & slots
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(lambda a: self.progress_action(a))
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
        self.main_label.setText(f"{self.percent_processed}% of songs processed!")
    
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
    
    # Connections
    def update_checkboxes(self):
        self.state_manager.adjustBPM = self.check_adjust_bpm.checkState().value
        print(self.state_manager.adjustBPM)
        self.state_manager.virtualSurround = self.check_vSurround.checkState().value
        print(self.state_manager.adjustBPM)
        
    def update_comboboxes(self):
        self.state_manager.currentSpeakerType = self.combo_audiodevice.currentText()
        print(self.state_manager.currentSpeakerType)
        self.state_manager.currentBeatFeeling = self.combo_beatfeel.currentText()
        print(self.state_manager.currentBeatFeeling)
        self.state_manager.currentController = self.combo_controllertype.currentText()
        print(self.state_manager.currentController)
        
if __name__ == "__main__":     
    app = QApplication(sys.argv)

    mainWindow = MainWindow()
    mainWindow.setWindowTitle("DaD Tempo Generator")
    mainWindow.setMinimumSize(600, 400)

    mainWindow.show()
    sys.exit(app.exec())