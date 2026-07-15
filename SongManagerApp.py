import sys

# Classes
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget,
    QPushButton, QVBoxLayout, QLabel,
    QProgressBar
)
from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal,
    QThread
)

# Custom classes
import scripts.FileManagement as fm
import scripts.SongAnalyzer as sa
import helpers.DebugHelper as dh

try:
    import pyi_splash
    pyi_splash.close()
except:
    pass

class Worker(QObject):
    finished = pyqtSignal()          # emitted when run() is done
    progress = pyqtSignal(int)       # optional: percent‑complete

    def __init__(self, song_analyzer: sa.SongAnalyzer):
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
        self.song_analyzer = sa.SongAnalyzer(file_manager=self.file_manager)
        self.error_logger = dh.LogManager(f"{Path(__file__).stem}_error-log.log")
        self.info_logger = dh.LogManager(f"{Path(__file__).stem}_info-log.log")
        
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
        self.worker = Worker(self.song_analyzer)   # keep reference
        self.worker.moveToThread(self.worker_thread)
            
        # Connect signals & slots
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(lambda a: self.progress_action(a))
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        # Keep disabled #
        # self.worker.finished.connect(self.worker.deleteLater)
        # self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.run_button.setEnabled(False)
        
        self.worker_thread.start()
        
    def on_worker_finished(self):
        """Called *after* the background thread quits."""
        # Re‑enable Run button
        self.run_button.setEnabled(True)
        self.main_label.setText(f"{self.percent_processed}% of songs processed!")
        
if __name__ == "__main__":     
    app = QApplication(sys.argv)

    mainWindow = MainWindow()
    mainWindow.setWindowTitle("DaD Tempo Generator")
    mainWindow.setMinimumSize(600, 400)

    mainWindow.show()
    sys.exit(app.exec())