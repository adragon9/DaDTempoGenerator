# Package imports
import sys, json

# Class imports
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
    finished = pyqtSignal()          # emitted when run() is done
    progress = pyqtSignal(int)       # optional: percent‑complete

    def __init__(self, song_analyzer: sa.SongAnalyzer, state_manager: dm.MainWindowStateManager):
        super().__init__()
        self.song_analyzer = song_analyzer
        self.song_analyzer.set_progress_signal(self.progress)
        
    def run(self):
        try:
            self.song_analyzer.load_predictor()
            self.song_analyzer.run_processor()
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
        
        self.persistent_settings = self.file_manager.get_previous_settings()
        self.settings_init()
            
        self.ui_init()
        
    def ui_init(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        display_layout = QHBoxLayout()
        
        self.main_label = QLabel()
        self.main_label.setText("Idle")
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addLayout(display_layout, stretch=4)
        display_layout.addWidget(self.main_label, stretch=1)
        
        # Checkboxes
        checkbox_layout = QHBoxLayout()
        
        self.check_adjust_bpm = QCheckBox("Adjust Low BPM")
        if self.state_manager.adjustBPM == 2:
            self.check_adjust_bpm.setCheckState(Qt.CheckState.Checked)
        else:
            self.check_adjust_bpm.setCheckState(Qt.CheckState.Unchecked)
            
        self.check_vSurround = QCheckBox("Virtual Surround Sound")
        if self.state_manager.virtualSurround == 2:
            self.check_vSurround.setCheckState(Qt.CheckState.Checked)
        else:
            self.check_vSurround.setCheckState(Qt.CheckState.Unchecked)
        
        self.main_layout.addLayout(checkbox_layout, stretch=2)
        checkbox_layout.addWidget(self.check_adjust_bpm, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)
        checkbox_layout.addWidget(self.check_vSurround, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter|Qt.AlignmentFlag.AlignBottom)
        
        # Comboboxes
        combobox_layout_1 = QHBoxLayout()
        combobox_layout_2 = QHBoxLayout()
        
        self.combo_label_1 = QLabel("Audio Device Connection")
        self.combo_label_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_audiodevice = QComboBox() 
        self.combo_audiodevice.addItems(self.state_manager.speakerTypes)
        self.combo_audiodevice.setCurrentText(self.state_manager.currentSpeakerType)
        
        self.combo_label_2 = QLabel("feels")
        self.combo_label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_beatfeel = QComboBox() 
        self.combo_beatfeel.addItems(self.state_manager.beatFeelings)
        self.combo_beatfeel.setCurrentText(self.state_manager.currentBeatFeeling)
        
        self.combo_label_3 = QLabel("Controller/Keyboard Connection")
        self.combo_label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_controllertype = QComboBox()
        self.combo_controllertype.addItems(self.state_manager.controllerTypes)
        self.combo_controllertype.setCurrentText(self.state_manager.currentController)
        
        self.combo_label_4 = QLabel("Confidence threshold for switching analysis methods")
        self.combo_label_4.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.combo_precisionlevel = QComboBox()
        self.combo_precisionlevel.addItems(self.state_manager.librosaReliance)
        self.combo_precisionlevel.setCurrentText(self.state_manager.currentConfidenceThresh)
        self.combo_warning_1 = QLabel("")
        if self.state_manager.currentConfidenceThresh== "High":
            self.combo_warning_1.setText(f"WARNING: Setting this to {self.state_manager.currentConfidenceThresh} will greatly increase processing time!")
        elif self.state_manager.currentConfidenceThresh == "Medium":
            self.combo_warning_1.setText(f"Setting this to {self.state_manager.currentConfidenceThresh} is recommended.")
        else:
            self.combo_warning_1.setHidden(True)
        self.combo_warning_1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addLayout(combobox_layout_1)
        self.main_layout.addLayout(combobox_layout_2)
        combobox_layout_1.addWidget(self.combo_label_1)
        combobox_layout_1.addWidget(self.combo_audiodevice, stretch=1)
        combobox_layout_1.addWidget(self.combo_label_2)
        combobox_layout_1.addWidget(self.combo_beatfeel, stretch=1)
        combobox_layout_1.addWidget(self.combo_label_3)
        combobox_layout_1.addWidget(self.combo_controllertype, stretch=1)
        combobox_layout_2.addWidget(self.combo_label_4)
        combobox_layout_2.addWidget(self.combo_precisionlevel, stretch=1)
        combobox_layout_2.addWidget(self.combo_warning_1)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        self.main_layout.addWidget(self.progress_bar, Qt.AlignmentFlag.AlignCenter)
        
        self.run_button = QPushButton()
        self.run_button.setText("Run")
        
        self.main_layout.addWidget(self.run_button, Qt.AlignmentFlag.AlignCenter)
        
        # Connections
        # Buttons
        self.run_button.clicked.connect(self.run_button_action)
        
        # Checkboxes
        checkboxes = self.main_widget.findChildren(QCheckBox)
        for checkbox in checkboxes:
            checkbox.clicked.connect(self.update_comboboxes)
            
        # Combos
        comboboxes = self.main_widget.findChildren(QComboBox)
        for combobox in comboboxes:
            combobox.currentTextChanged.connect(self.update_comboboxes)
        
    def settings_init(self):
        if self.persistent_settings:
            self.state_manager.adjustBPM = self.persistent_settings["adjustBPM"]
            self.state_manager.virtualSurround = self.persistent_settings["virtualSurround"]
            self.state_manager.currentSpeakerType = self.persistent_settings["currentSpeakerType"]
            self.state_manager.currentBeatFeeling = self.persistent_settings["currentBeatFeeling"]
            self.state_manager.currentController = self.persistent_settings["currentController"]
            self.state_manager.currentConfidenceThresh = self.persistent_settings["currentConfidenceThresh"]
        
    def progress_action(self, signal):
        try:
            progress_string = self.song_analyzer.get_progress_string()
        except Exception as e:
            progress_string = None
            self.error_logger.write(f"Error {e} while trying to get the progress string.")
            
        match signal:
            case 101:
                self.main_label.setText("Loading deeprhythm model...")
            case 102:
                self.main_label.setText(progress_string)
            case 201:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting tempo(1/2)""")
            case 2011:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting tempo(1/2)
                                        \nAttempting deeprhythm analysis""")
            case 20111:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting tempo(1/2)
                                        \ndeeprhythm confidence too low attempting librosa analysis""")
            case 201111:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting tempo(1/2)
                                        \ndeeprhythm confidence too low attempting librosa analysis
                                        \nPreparing onset envelope(1/2)""")
            case 201112:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting tempo(1/2)
                                        \ndeeprhythm confidence too low attempting librosa analysis
                                        \nEstimating tempo(2/2)""")
            case 202:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting beat offset(2/2)""")
            case 2021:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting beat offset(2/2)
                                        \nPreparing onset envelope(1/4)""")
            case 2022:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting beat offset(2/2)
                                        \nDetecting first beat(2/4)""")
            case 2023:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting beat offset(2/2)
                                        \nConverting first frame to seconds(3/4)""")
            case 2024:
                self.main_label.setText(f"""{progress_string}
                                        \nGetting beat offset(2/2)
                                        \nCalculating offset(4/4)""")
            case _:
                self.percent_processed = int((signal / self.song_count)*100)
                self.progress_bar.setValue(self.percent_processed)
                if progress_string:
                    self.main_label.setText(progress_string)
                else:
                    self.main_label.setText("Error retrieving song name.")
            
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
        self.state_manager.virtualSurround = self.check_vSurround.checkState().value
        
    def update_comboboxes(self):
        self.state_manager.currentSpeakerType = self.combo_audiodevice.currentText()
        self.state_manager.currentBeatFeeling = self.combo_beatfeel.currentText()
        self.state_manager.currentController = self.combo_controllertype.currentText()
        self.state_manager.currentConfidenceThresh = self.combo_precisionlevel.currentText()
        if self.state_manager.currentConfidenceThresh== "High":
            self.combo_warning_1.setHidden(False)
            self.combo_warning_1.setText(f"WARNING: Setting this to {self.state_manager.currentConfidenceThresh} will greatly increase processing time!")
        elif self.state_manager.currentConfidenceThresh == "Medium":
            self.combo_warning_1.setHidden(False)
            self.combo_warning_1.setText(f"Setting this to {self.state_manager.currentConfidenceThresh} is recommended.")
        else:
            self.combo_warning_1.setHidden(True)

        
if __name__ == "__main__":     
    app = QApplication(sys.argv)

    mainWindow = MainWindow()
    try:
        with open(Path(".\\data\\config\\settings.json"), 'r') as file:
            data = json.load(file)["version"]
            mainWindow.setWindowTitle(f"DaD Tempo Generator {data}")
    except:
        mainWindow.setWindowTitle("DaD Tempo Generator")
    mainWindow.setMinimumSize(900, 600)

    mainWindow.show()
    sys.exit(app.exec())