import os, json, charset_normalizer
from typing import Any
import deeprhythm_custom, librosa, torch
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from scipy.ndimage import median_filter
from sklearn.cluster import KMeans
from pathlib import Path
from PyQt6.QtCore import (
    pyqtBoundSignal
)

# Custom Imports
import helpers.DebugHelper as dh
import scripts.FileManagement as fm
import scripts.DataManagement as dm

class SongAnalyzer():
    def __init__(self, file_manager: fm.FileManager|None=None, main_window_states: dm.MainWindowStateManager|None=None):
        self.error_logger = dh.LogManager(f"{Path(__file__).stem}_error-log.log")
        self.info_logger = dh.LogManager(f"{Path(__file__).stem}_info-log.log")
        self.info_logger.wipe_log()
        self.file_manager = file_manager
        self.model = deeprhythm_custom.DeepRhythmPredictor()
        self.main_window_states = main_window_states
        self.model.load_model()
        self.tempo_segments_mode = False

    def build_songlist(self, imported_song_path: str|Path|os.DirEntry):
        '''
        Get the list of songs to work with.
        '''
        if type(imported_song_path) == str:
            try:
                Path(imported_song_path)
            except Exception as e:
                self.error_logger.write(f"{e} in build_songlist during string conversion.")
                
        self.song_names = []
        self.song_dirs = []
        try:
            for folder in os.scandir(imported_song_path):
                self.song_names.append(folder.name)
                self.song_dirs.append(folder.path)
        except Exception as e:
            self.error_logger.write(f"Failed to scans songs for reason: {e}")
            
    # get functions  
    def get_song_names(self):
        return self.song_names
    
    def get_song_paths(self):
        return self.song_dirs
    
    def get_song_count(self):
        self.song_count = len(self.get_song_names())
        return self.song_count
    
    def get_progress_string(self):
        if self.progress_string:
            return self.progress_string
        else:
            pass
    
    # Song analysis
    def _librosa_tempo(self, y, sr, onset_env):
        tempo_lib = librosa.feature.tempo(y=y, sr=sr, onset_envelope=onset_env)
        return tempo_lib[0]
    
    # partially AI Generated adjust later.
    def _librosa_segmented_tempo(self, y, sr, onset_env):
        pass
    
    def _get_tempo(self, audio_path, model: deeprhythm_custom.DeepRhythmPredictor):
        y, sr = librosa.load(audio_path, sr=None)
              
        sr = int(sr)
        low, high = self._adaptive_cutoffs(y, sr)
        
        if low < high:
            y = self._filter_y(y, sr, int(low), int(high))
        
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)

        if not self.tempo_segments_mode:
            # y_array_fix = np.ascontiguousarray(y)
            # tempo, confidence = model.predict_from_audio(audio=y_array_fix, sr=sr, include_confidence=True) # type: ignore
                    
            # if confidence < 0.7:
            tempos, confs = model.predict_per_frame(audio_path, include_confidence=True)
            tempos = np.asarray(tempos)
            confs = np.asarray(confs)
            
            mask = confs > 0.7
            if np.any(mask):
                t = tempos[mask]
                c = confs[mask]

                # cluster-based dominant tempo
                tempo = self._cluster_tempo(t)

                # confidence = strongest frame
                confidence = float(np.max(c))
            else:
                tempo = self._librosa_tempo(y=y, sr=sr, onset_env=onset_env)
                confidence = 0
                    
            beat_offset = self._beat_offset()
            
            if self.main_window_states and self.main_window_states.adjustBPM == 2:
                if tempo <= 90:
                    tempo = tempo * 2
                    
            return tempo, [], confidence, beat_offset
        else:
            pass
            return 0, [], 0, 0

    def _beat_offset(self):
        offset_ms = 0
        if self.main_window_states:
            if self.main_window_states.currentBeatFeeling.lower() == "good":
                match self.main_window_states.currentSpeakerType:
                    case "Wired Headphones":
                        offset_ms = 5
                    case "Bluetooth Headphones":
                        offset_ms = 180
                    case "Desktop/PC Speakers":
                        offset_ms = 20
                    case "TV via HDMI":
                        offset_ms = 55
                    case "Steam Deck":
                        offset_ms = 8
                    case "Wireless 2.4GHz":
                        offset_ms = 12
                    case "Custom/Unkown":
                        offset_ms = 30
                    case _:
                        offset_ms = 0
                    
            elif self.main_window_states.currentBeatFeeling.lower() == "early":
                match self.main_window_states.currentSpeakerType:
                    case "Wired Headphones":
                        offset_ms = 20
                    case "Bluetooth Headphones":
                        offset_ms = 195
                    case "Desktop/PC Speakers":
                        offset_ms = 35
                    case "TV via HDMI":
                        offset_ms = 70
                    case "Steam Deck":
                        offset_ms = 23
                    case "Wireless 2.4GHz":
                        offset_ms = 27
                    case "Custom/Unkown":
                        offset_ms = 45
                    case _:
                        offset_ms = 0
                    
            elif self.main_window_states.currentBeatFeeling.lower() == "late":
                match self.main_window_states.currentSpeakerType:
                    case "Wired Headphones":
                        offset_ms = -15
                    case "Bluetooth Headphones":
                        offset_ms = 160
                    case "Desktop/PC Speakers":
                        offset_ms = 0
                    case "TV via HDMI":
                        offset_ms = 35
                    case "Steam Deck":
                        offset_ms = -12
                    case "Wireless 2.4GHz":
                        offset_ms = -8
                    case "Custom/Unkown":
                        offset_ms = 10
                    case _:
                        offset_ms = 0
                        
            if self.main_window_states.currentController.lower() != "wired":
                match self.main_window_states.currentController:
                    case "Wireless 2.4Ghz":
                        offset_ms += 4
                    case "Wireless Bluetooth":
                        offset_ms += 16
                    case "Ignore":
                        pass
                    case _:
                        pass
                        
            if self.main_window_states.virtualSurround == 2:
                offset_ms += 40
            
            return offset_ms
        
        else:
            return 0

    # Assistant functions
    def _filter_y(self, y, sr, lowcut=60, highcut=900, order=4):
        # Calculate normalized frequencies
        nyquist = 0.5 * sr
        low = lowcut / nyquist
        high = highcut / nyquist
        
        try:
            b, a = signal.butter(order, [low, high], btype='bandpass') # type: ignore
            return signal.filtfilt(b, a, y)
        except Exception as e:
            # print(f"Filtering failed: {e}")
            pass
        return y
        
    def _adaptive_cutoffs(self, y: np.ndarray, sr: int) -> tuple[float, float]:
        S = np.abs(np.fft.rfft(y))
        freqs = np.fft.rfftfreq(len(y), 1/sr)

        # normalize magnitudes
        mag = S / S.max()

        # cumulative energy distribution
        cdf = np.cumsum(mag)
        cdf /= cdf[-1]

        low = freqs[np.searchsorted(cdf, 0.10)]
        high = freqs[np.searchsorted(cdf, 0.90)]


        low  = max(50.0, low)
        high = min(1500.0, high)
        
        if high - low < 100:
            mid = (high + low) / 2
            low = max(50, mid - 50)
            high = min(1500, mid + 50)

        return low, high

    def _cluster_tempo(self, tempos) -> Any | int:
        tempos = np.asarray(tempos).reshape(-1, 1)
        if tempos.shape[0] == 1:
            return tempos[0, 0]
        
        if tempos.shape[0] == 0:
            return 0
        
        kmeans = KMeans(n_clusters=2, n_init=5)
        labels = kmeans.fit_predict(tempos)
        centers = kmeans.cluster_centers_.flatten()
        return centers[np.argmax(np.bincount(labels))]    

    def _load_json_utf16(self, path: Path):
        raw = path.read_bytes()
        enc = charset_normalizer.detect(raw)["encoding"] or "utf-8"

        if enc.lower().startswith("utf-16"):
            text = raw.decode(enc)
        else:
            text = raw.decode(enc, errors="replace")

        return json.loads(text)
 
    def _dump_json_as_utf8(self, path: Path, data):
        text = json.dumps(data, indent=4, ensure_ascii=False)
        path.write_text(text, encoding="utf-8")

    def _update_tempo(self, audio_file, model, json_file, data):
        if not self.tempo_segments_mode:
            tempo, tempo_segments, confidence, beat_offset = self._get_tempo(audio_file, model)
            tempo = int(tempo)
            data["tempo"] = tempo # type: ignore
            data["beatOffset"] = beat_offset # type: ignore
            data["customTempoSections"] = []
            self._dump_json_as_utf8(Path(json_file), data)
        else:
            tempo, tempo_segments, confidence, beat_offset = self._get_tempo(audio_file, model)
            tempo = int(tempo)
            data["tempo"] = tempo # type: ignore
            data["beatOffset"] = beat_offset # type: ignore
            data["customTempoSections"] = []
            try:
                if len(tempo_segments) > 1:
                    for segment in tempo_segments:
                        data["customTempoSections"].append(
                            {
                                "tempo":segment[2],
                                "startAbsoluteTime":segment[0]
                            }
                        )
            except:
                pass
            finally:
                self._dump_json_as_utf8(Path(json_file), data)
                confidence = 0.0
        return tempo, confidence, beat_offset
    
    def _update_beatoffset(self, data, json_file, beat_offset):
        if not self.tempo_segments_mode:
            data["beatOffset"] = beat_offset # type: ignore
            self._dump_json_as_utf8(Path(json_file), data)
    
    # Main processor
    # This needs a serious rework...
    def run_processor(self, signal: pyqtBoundSignal):
        '''
        This will allow me to send progress data back to the main window.
        '''
        signal.emit(1) # initial emission
        
        for i, path in enumerate(self.song_dirs):
            self.progress_string = f"Analyzing {self.song_names[i]}"
            
            json_file = None
            data = None
            audio_file = None
            tempo = None
            confidence = None
            beat_offset = None
            
            for file in os.scandir(path):
                if file.name == "Audio.ogg":
                    audio_file = file
                elif file.name == "Meta.json":
                    json_file = str(file.path)
                else:
                    self.error_logger.write(f"Unknown file: {file}")
                    continue
                
                if json_file:
                    data = self._load_json_utf16(Path(json_file))
                else:
                    continue
                
                if self.file_manager and (data and audio_file):
                    scanned_song = self.file_manager.check_scanned_song(self.song_names[i])
                    scan_low_bpm = (data["tempo"] <= 90 and self.main_window_states and self.main_window_states.adjustBPM == 2)
                    
                    if scanned_song:
                        # update beat_offset
                        beat_offset = self._beat_offset()
                        self._update_beatoffset(data, json_file, beat_offset)
                        
                        # Check for game data and scanned song list tempo mismatch.
                        if data["tempo"] != scanned_song["tempo"] or scan_low_bpm:
                            tempo, confidence, beat_offset = self._update_tempo(audio_file, self.model, json_file, data)
                            
                        # log
                        write_string = f"{self.song_names[i]} (Tempo: {scanned_song["tempo"]}, Confidence: {int(scanned_song["confidence"]*100)}%)"
                        self.info_logger.write(write_string)
                        
                        # update scanned songs list
                        if self.file_manager:
                            self.file_manager.update_scanned_item(self.song_names[i], beat_offset=beat_offset)
                            
                # Log results
                if (tempo and confidence and beat_offset):
                    self.info_logger.write(f"{self.song_names[i]} (Tempo: {tempo}, Confidence: {int(confidence*100)}%)")
                    if self.file_manager:
                        self.file_manager.add_scanned_item(self.song_names[i], tempo ,beat_offset, confidence)
                    
            signal.emit(i+1) # emit progress
            
        if self.file_manager:
            self.file_manager.save_state(main_window_states=self.main_window_states)

            