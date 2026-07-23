import os, json, charset_normalizer
import deeprhythm_custom, librosa
import numpy as np
import scipy.signal as signal
from sklearn.cluster import KMeans
from pathlib import Path
from PyQt6.QtCore import (
    pyqtBoundSignal
)

# Custom Imports
import helpers.DebugHelper as dh
import scripts.FileManagement as fm

class SongAnalyzer():
    def __init__(self, file_manager: fm.FileManager|None=None):
        self.error_logger = dh.LogManager(f"{Path(__file__).stem}_error-log.log")
        self.info_logger = dh.LogManager(f"{Path(__file__).stem}_info-log.log")
        self.info_logger.wipe_log()
        self.file_manager = file_manager
        self.model = deeprhythm_custom.DeepRhythmPredictor()
        self.model.load_model()  

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
    def _librosa_tempo(self, audio_path):
        y, sr = librosa.load(audio_path)
        low, high = self._adaptive_cutoffs(y, int(sr))
        # print(low, high)
        if low < high:
            y = self._filter_y(y, sr, int(low), int(high))
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo_lib = librosa.feature.tempo(y=y, sr=sr, onset_envelope=onset_env)
        # print(tempo_lib)
        return tempo_lib[0]

    def _get_tempo(self, audio_path, model: deeprhythm_custom.DeepRhythmPredictor):
        tempo, confidence = model.predict(audio_path, include_confidence=True) # type: ignore

        if confidence < 0.7:
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
                tempo = self._librosa_tempo(audio_path)
                
        # Adjust up or down to get it within DaD's 120~200bpm recommended range.
        ## Plan to make this feature option in future releases.
        if tempo < 100:
            tempo *= 2
        elif tempo > 240:
            tempo = int(tempo / 2)

        return tempo, confidence

    def _beat_offset(self, audio_path: str | Path | os.DirEntry):
        y, sr = librosa.load(audio_path)
        low, high = self._adaptive_cutoffs(y, int(sr))
        # print(low, high)
        y = self._filter_y(y, sr, int(low), int(high))
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, onset_envelope=onset_env)
        if len(onset_frames) == 0:
            return 0.0

        first_onset_sec = librosa.frames_to_time(onset_frames[0], sr=sr)
        
        return round(first_onset_sec * 1000, 3)

    # filter highs and lows
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

    def _cluster_tempo(self, tempos):
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
        tempo, confidence = self._get_tempo(audio_file, model)
        tempo = int(tempo)
        beat_offset = self._beat_offset(audio_file)
        data["tempo"] = tempo # type: ignore
        data["beatOffset"] = beat_offset # type: ignore
        self._dump_json_as_utf8(Path(json_file), data)
        return tempo, confidence, beat_offset
    
    # Main processor
    def run_processor(self, signal: pyqtBoundSignal):
        '''
        This will allow me to send progress data back to the main window.
        '''
        for i, path in enumerate(self.song_dirs):
            self.progress_string = f"Analyzing {self.song_names[i]}"
            signal.emit(i+1)
            for file in os.scandir(path):
                if file.name == "Audio.ogg":
                    audio_file = file
                elif file.name == "Meta.json":
                    json_file = str(file.path)
                    try:
                        data = self._load_json_utf16(Path(json_file))
                        if self.file_manager:
                            try:
                                scanned_song = self.file_manager.check_scanned_song(self.song_names[i])
                                if scanned_song:
                                    if (data["tempo"], data["beatOffset"]) == (scanned_song["tempo"], scanned_song["beatOffset"]):
                                        self.info_logger.write(
                                            f"{self.song_names[i]} (Tempo: {scanned_song["tempo"]}, Confidence: {int(scanned_song["confidence"]*100)}%)" # type: ignore 
                                            ) 
                                        continue
                                    else:
                                        tempo, confidence, beat_offset = self._update_tempo(audio_file, self.model, json_file, data) # type: ignore 
                                else:
                                    raise KeyError
                            except KeyError, ValueError:
                                tempo, confidence, beat_offset = self._update_tempo(audio_file, self.model, json_file, data) # type: ignore 
                            except Exception as e:
                                print(e)
                        # Log results
                        self.info_logger.write(f"{self.song_names[i]} (Tempo: {tempo}, Confidence: {int(confidence*100)}%)") # type: ignore 
                        if self.file_manager:
                            self.file_manager.add_scanned_item(self.song_names[i], tempo ,beat_offset, confidence) # type: ignore
                    except Exception as e:
                        print(f"Error: {e} in run_processor")
                        self.error_logger.write(f"Failed to open json file in run_processor reason: {e} (file:{path})")
                else:
                    self.error_logger.write(f"Unknown file: {file}")

            