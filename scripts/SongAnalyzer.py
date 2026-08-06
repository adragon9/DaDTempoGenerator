# Package imports
import os
import deeprhythm_custom, librosa
import numpy as np

# Class imports
from pathlib import Path
from PyQt6.QtCore import (
    pyqtBoundSignal
)

# Custom Imports
import helpers.DebugHelper as dh
import scripts.FileManagement as fm
import scripts.DataManagement as dm

class SongAnalyzer():
    def __init__(self, file_manager: fm.FileManager, main_window_states: dm.MainWindowStateManager, progress_signal: pyqtBoundSignal | None = None):
        self.error_logger = dh.LogManager(f"{Path(__file__).stem}_error-log.log")
        self.info_logger = dh.LogManager(f"{Path(__file__).stem}_info-log.log")
        self.info_logger.wipe_log()
        self.file_manager = file_manager
        self.model = deeprhythm_custom.DeepRhythmPredictor()
        self.main_window_states = main_window_states
        self.tempo_segments_mode = False
        self.progress_signal = progress_signal

    # Prep functions        
    def build_songlist(self, imported_song_path: str|Path|os.DirEntry):
        '''
        Get the list of songs to work with.
        '''
        if type(imported_song_path) == str:
            try:
                Path(imported_song_path)
            except Exception as e:
                self.error_logger.write(f"Error {e} when building song list.")
                
        self.song_names = []
        self.song_dirs = []
        try:
            for folder in os.scandir(imported_song_path):
                self.song_names.append(folder.name)
                self.song_dirs.append(folder.path)
        except Exception as e:
            self.error_logger.write(f"Error {e} while attempting to scan {imported_song_path}")

    def load_predictor(self):
        self._emit_signal(101)
        self.model.load_model() 
    
    # Signal management
    # Called from main window to get signal
    def set_progress_signal(self, signal: pyqtBoundSignal):
        self.progress_signal = signal

    # Emits progress signal code
    def _emit_signal(self, signal_code: int):
        if self.progress_signal:
            self.progress_signal.emit(signal_code)
            
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

    # Logic helpers
    def _check_rescan(self):
        # Currently either all settings are there or none I'll need to fix that.
        prev_settings = self.file_manager.get_previous_settings()
        rescan_beat_offset = False
        rescan_tempo = False
        
        last_feeling = None
        last_speakerType = None
        last_precision = None
        last_controller = None
        last_adjustBPM = None
        last_virtualSurround = None
        
        try:
            if prev_settings:
                last_feeling = prev_settings["currentBeatFeeling"]
                last_speakerType = prev_settings["currentSpeakerType"]
                last_precision = prev_settings["currentConfidenceThresh"]
                last_controller = prev_settings["currentController"]
                last_adjustBPM = prev_settings["adjustBPM"]
                last_virtualSurround = prev_settings["virtualSurround"]
        except Exception as e:
            self.error_logger.write(f"Error {e} in _check_rescan")
        
        if self.main_window_states.currentBeatFeeling != last_feeling:
            rescan_beat_offset = True
        elif self.main_window_states.currentController != last_controller:
            rescan_beat_offset = True
        elif self.main_window_states.currentSpeakerType != last_speakerType:
            rescan_beat_offset = True
        elif self.main_window_states.virtualSurround != last_virtualSurround:
            rescan_beat_offset = True
            
        if self.main_window_states.currentConfidenceThresh != last_precision:
            rescan_tempo = True
        elif self.main_window_states.adjustBPM != last_adjustBPM:
            rescan_tempo = True
            
        return rescan_tempo, rescan_beat_offset

    def _get_confidence_threshold(self)-> float | int:
        extreme_code = 1
        if not self.main_window_states:
            return extreme_code

        match self.main_window_states.currentConfidenceThresh:
            case "Low":
                return .7
            case "Medium":
                return .8
            case "High":
                return .9
            case _:
                return extreme_code

    # Song analysis
    def _onset_evaluation(self, y, sr):
        harmonics, percussion = librosa.effects.hpss(y)
        
        onset_env_perc = librosa.onset.onset_strength(
            y=percussion,
            sr=sr,
            aggregate=np.mean,
        )
        onset_env_harm = librosa.onset.onset_strength(
            y=harmonics,
            sr=sr,
            aggregate=np.mean
        )
        
        peaks_perc = librosa.onset.onset_detect(
            y=y,
            sr=sr,
            onset_envelope=onset_env_perc
        )
        peaks_harm = librosa.onset.onset_detect(
            y=y,
            sr=sr,
            onset_envelope=onset_env_harm
        )

        tempogram_perc = librosa.feature.tempogram(
            onset_envelope=onset_env_perc,
            sr=sr
        )
        tempogram_harm = librosa.feature.tempogram(
            onset_envelope=onset_env_perc,
            sr=sr
        )
        
        onset_env_perc_energy = np.sum(onset_env_perc)
        onset_env_harm_energy = np.sum(onset_env_harm)
        
        num_onsets_perc = len(peaks_perc)
        num_onsets_harm = len(peaks_harm)
        
        tempogram_perc_rms = float(np.max(np.mean(tempogram_perc, axis=1)))
        tempogram_harm_rms = float(np.max(np.mean(tempogram_harm, axis=1)))
        
        perc_data = (onset_env_perc_energy, num_onsets_perc, tempogram_perc_rms)
        harm_data = (onset_env_harm_energy, num_onsets_harm, tempogram_harm_rms)
        
        perc_score = sum(perc_data)
        harm_score = sum(harm_data)

        if perc_score > harm_score:
            return onset_env_perc
        elif perc_score < harm_score:
            return onset_env_harm
        else:
            return librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.mean)
        
    def _librosa_tempo(self, y, sr, onset_env, tempo_guess: int | float | None = None):
        print(tempo_guess)
        if tempo_guess:
            tempo = librosa.feature.tempo(y=y, sr=sr, onset_envelope=onset_env, start_bpm=tempo_guess)
        else:
            tempo = librosa.feature.tempo(y=y, sr=sr, onset_envelope=onset_env)
        try:
            tempo = float(tempo)
        except TypeError as e:
            tempo = float(tempo[0]) # type: ignore
            self.error_logger.write(f"Error {e} while conver")
            
        return tempo
    
    def _beat_offset(self, audio_file, onset_strength: np.ndarray | None = None, tempo: int | float = 120):
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
        
        self._emit_signal(2021)
        # Get time to first beat
        y, sr = librosa.load(audio_file, sr=None)
        sr = sr // 2
        if not np.any(onset_strength): 
            onset_strength = self._onset_evaluation(y, sr)
        
        self._emit_signal(2021)
        onset_env = librosa.onset.onset_detect(y=y, sr=sr, onset_envelope=onset_strength, backtrack=True)
        
        self._emit_signal(2021)
        beat_timing = librosa.frames_to_time(onset_env, sr=sr)
        first_beat_ms = (beat_timing[0] * 1000)
        
        self._emit_signal(2021)
        if first_beat_ms:
            beat_length_ms = 60000 / tempo
            return_val = first_beat_ms + offset_ms
            
            # Return based off bars, no idea if this'll work
            if return_val >= 1000:
                return_val = ((return_val % beat_length_ms) / beat_length_ms)
                
            return round(return_val)
        else:
            beat_length_ms = 60000 / tempo
            return_val = offset_ms
            
            # Return based off bars, no idea if this'll work
            if return_val >= 1000:
                return_val = (return_val % beat_length_ms) / beat_length_ms
                
            return round(return_val)
 
    def _adjust_tempo(self, tempo: int | float, tempo_below: int = 90):
        if tempo <= tempo_below:
            old_tempo = tempo
            tempo *= 2
            return tempo, old_tempo
        else:
            return tempo, tempo
    
    # Main tempo retrieval
    def _get_tempo(self, audio_path, model: deeprhythm_custom.DeepRhythmPredictor):
        tempo = 0.0
        confidence = 0.0
        
        y = None
        sr = None
        onset_env = None
        
        precision_level = self._get_confidence_threshold()
        
        self._emit_signal(201)
        self._emit_signal(2011)
        tempo, confidence = model.predict(audio_path, include_confidence=True)# type: ignore
        if confidence < precision_level:
            self._emit_signal(20111)
            y, sr = librosa.load(audio_path, sr=None)
            sr = sr // 2
        
            self._emit_signal(201111)
            onset_env = self._onset_evaluation(y, sr)
            
            self._emit_signal(201112)
            tempo = self._librosa_tempo(y=y, sr=sr, onset_env=onset_env, tempo_guess=tempo)
            confidence = 999
            
        self._emit_signal(202)
        if not np.all((np.any(y), np.any(sr), np.any(onset_env))):
            self._emit_signal(2021)
            y, sr = librosa.load(audio_path, sr=None)
            sr = sr // 2
            onset_env = self._onset_evaluation(y, sr)
            
        beat_offset = self._beat_offset(
            audio_file=audio_path,
            onset_strength=onset_env,
            tempo=tempo
        )
                       
        return tempo, confidence, beat_offset
    
    # Main
    def run_processor(self):
        scanned_song = {}
            
        for i, path in enumerate(self.song_dirs):
            self._emit_signal(102)
            self.progress_string = f"Analyzing {self.song_names[i]}"
            
            json_file = None
            imported_song = None
            audio_file = None
            tempo = None
            confidence = 0
            beat_offset = 0
            fix_low_bpm = (self.main_window_states and self.main_window_states.adjustBPM == 2) # Init for the variable.
            write_string = ""
            old_tempo = 0
            beat_sync = []
            rescan_tempo, rescan_beat_offset = self._check_rescan()
            
            for file in os.scandir(path):
                if file.name == "Audio.ogg":
                    audio_file = file
                elif file.name == "Meta.json":
                    json_file = str(file.path)
                else:
                    self.error_logger.write(f"Unknown file: {file}")
                    continue
                
                if json_file:
                    imported_song = self.file_manager._load_json_utf16(Path(json_file))
                else:
                    continue
                
                if self.file_manager and (imported_song and audio_file):
                    tempo = imported_song["tempo"]
                    scanned_song = self.file_manager.check_scanned_song(self.song_names[i])  
                    if scanned_song:
                        tempo = scanned_song["tempo"]
                        old_tempo = tempo
                        # Check for game data and scanned song list tempo mismatch.
                        if round(imported_song["tempo"], 2) != round(scanned_song["tempo"], 2) and round(imported_song["tempo"], 2) != round(scanned_song["adjustedTempo"], 2):
                            tempo, confidence, beat_offset = self._get_tempo(audio_path=audio_file, model=self.model)
                            old_tempo = tempo
                            # _get_tempo already adjusts the bpm
                            rescan_beat_offset = False
                        elif rescan_tempo:
                            tempo, confidence, beat_offset = self._get_tempo(audio_path=audio_file, model=self.model)
                            old_tempo = tempo
                            # _get_tempo already adjusts the bpm
                            rescan_beat_offset = False
                        else:
                            beat_offset = scanned_song["beatOffset"]
                    else:
                        tempo, confidence, beat_offset = self._get_tempo(audio_path=audio_file, model=self.model)
                        old_tempo = tempo
                    
                    if fix_low_bpm:
                        tempo, old_tempo = self._adjust_tempo(tempo)
                         
                    if rescan_beat_offset:
                        beat_offset = self._beat_offset(audio_file=audio_file, tempo=tempo)
                    
                    # Round the tempo data to a meaningful level of percision.
                    # DO THIS LAST roudning can mess up calculations.
                    tempo = round(tempo, 2)
                    old_tempo = round(old_tempo, 2)
                    
                    if not confidence and scanned_song:
                        confidence = scanned_song["confidence"]
                    elif confidence == 999:
                        confidence = "No Value"
                    
                    imported_song["tempo"] = tempo
                    imported_song["customTempoSections"] = []
                    if np.any(beat_sync):
                        for beat in beat_sync: # type: ignore
                            imported_song["customTempoSections"].append(
                                {
                                    "tempo": tempo,
                                    "startAbsoluteTime": beat
                                }
                            )
                    else:
                        imported_song["customTempoSections"] = []
                    imported_song["beatOffset"] = beat_offset
                                            
                    self.file_manager._dump_json_as_utf8(Path(json_file).resolve(), imported_song)
                    
                    if type(confidence) != str:     
                        write_string = f"{self.song_names[i]} (Tempo: {tempo}, Confidence: {int(confidence * 100)}%, {beat_offset})"
                    else:
                        write_string = f"{self.song_names[i]} (Tempo: {tempo}, Confidence: {confidence}, {beat_offset})"
                    
                    # log
                    self.info_logger.write(write_string)
                    
                    song_data = {
                        "tempo":old_tempo,
                        "adjustedTempo":tempo,
                        "beatOffset":beat_offset,
                        "confidence":confidence,
                    }
                    
                    if scanned_song:
                        self.file_manager.update_scanned_item(self.song_names[i], song_data)
                    else:
                        self.file_manager.add_scanned_item(self.song_names[i], song_data)
            self._emit_signal(i+1)
        self.file_manager.save_state(main_window_states=self.main_window_states)
