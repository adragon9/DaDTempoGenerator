# Package imports
import os
import deeprhythm_custom, librosa
import numpy as np
import time
import statistics
import secrets
import math

# Class imports
from pathlib import Path
from PyQt6.QtCore import (
    pyqtBoundSignal
)
from typing import Literal
from bisect import bisect_left
from collections import defaultdict
from scipy import signal
from scipy.stats import lognorm
from scipy.ndimage import uniform_filter1d, gaussian_filter1d
from scipy.signal import find_peaks
# Custom Imports
import helpers.DebugHelper as dh
import scripts.FileManagement as fm
import scripts.DataManagement as dm


class SongAnalyzer():
    def __init__(self, file_manager: fm.FileManager, main_window_states: dm.MainWindowStateManager, progress_signal: pyqtBoundSignal | None = None,
                 main_messenger: pyqtBoundSignal | None = None, sub_messenger: pyqtBoundSignal | None = None, list_delivery: pyqtBoundSignal | None = None):
        self.error_logger = dh.LogManager(f"{Path(__file__).stem}_error-log.log")
        self.info_logger = dh.LogManager(f"{Path(__file__).stem}_info-log.log")
        self.info_logger.wipe_log()
        self.file_manager = file_manager
        self.model = deeprhythm_custom.DeepRhythmPredictor()
        self.main_window_states = main_window_states
        self.tempo_segments_mode = False
        self.progress_signal = progress_signal
        self.main_messenger = main_messenger
        self.sub_messenger = sub_messenger
        self.json_file = None
        self.audio_file = None

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
        for folder in os.scandir(imported_song_path):
            try:
                data = self.file_manager._load_json_utf16(Path(os.path.join(folder.path, "Meta.json")))
                self.song_names.append(data["songName"])
                self.song_dirs.append(folder.path)
            except FileNotFoundError as e:
                self.error_logger.write(f"The folder located at {folder} is missing its 'Meta.json' file!")
        
        pairs = zip(self.song_names, self.song_dirs)
        pairs = list(dict.fromkeys(pairs))
        
        # Clear old lists before rebuild
        self.song_names.clear()
        self.song_dirs.clear()
        for name, path in pairs:
            self.song_names.append(name)
            self.song_dirs.append(path)
            
        # Ensure no duplicates
        self.song_names = list(dict.fromkeys(self.song_names))
        self.song_dirs = list(dict.fromkeys(self.song_dirs))
        
    def load_predictor(self):
        self._emit_signal('sm', "Loading deeprhythm model.")
        self.model.load_model() 
    
    # Signal management
    # Called from main window to get signal
    def set_signals(self,
                    progress_signal: pyqtBoundSignal,
                    main_messenger: pyqtBoundSignal,
                    sub_messenger: pyqtBoundSignal,
                ):
        """
        Need to switch to passing in a list or dict of bound signals
        """
        
        self.progress_signal = progress_signal
        self.main_messenger = main_messenger
        self.sub_messenger = sub_messenger

    # Emits progress signal code
    def _emit_signal(self, signal_code: Literal["ps","mm","sm"], message: str | int = ""):
        '''
        signal codes:
        - ps: Progress signal
        - mm: Main messenger
        - sm: Sub messenger
        '''
        if self.progress_signal and signal_code == "ps":
            self.progress_signal.emit(message)
        elif self.sub_messenger and signal_code == "sm":
            self.sub_messenger.emit(message)
        elif self.main_messenger and signal_code == "mm":
            self.main_messenger.emit(message)
            
    # get functions  
    def get_song_names(self):
        return self.song_names
    
    def get_song_paths(self):
        return self.song_dirs
    
    def get_song_count(self):
        self.song_count = len(self.get_song_names())
        return self.song_count
    
    # Logic helpers
    def _check_rescan(self):
        # Currently either all settings are there or none I'll need to fix that.
        self.prev_settings = self.file_manager.get_previous_user_choices()
        rescan_beat_offset = False
        rescan_tempo = False
                
        last_adjustBPM = None
        last_global_offset = None

        try:
            if self.prev_settings:
                last_adjustBPM = self.prev_settings["adjustBPM"]
                last_global_offset = self.prev_settings["globalOffset"]   
        except Exception as e:
            self.error_logger.write(f"Error {e} in _check_rescan")
                
        beatOffset_vars = [
            (self.main_window_states.globalOffset != last_global_offset)
        ]
        if any(beatOffset_vars):
            rescan_beat_offset = True
        
        rescan_vars = [
            (self.main_window_states.adjustBPM != last_adjustBPM),
            self.main_window_states.freshScan
        ]
        if any(rescan_vars):
            rescan_tempo = True
            
        return rescan_tempo, rescan_beat_offset

    # Song analysis            
    def _beat_offset(self, audio_file, tempo: int | float = 120):
        offset_ms = 0
        offset_ms += self.main_window_states.globalOffset
            
        self._emit_signal('sm', f"Beat offset measurement starting at: {offset_ms}ms")
        
        # Get time to first beat
        y, sr = librosa.load(audio_file, sr=None)
        hop_length = int(sr // (len(y) // sr))
        
        onset_detect = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)

        beat_timing = librosa.frames_to_time(onset_detect, sr=sr, hop_length=hop_length)
        first_beat_ms = (beat_timing[0] * 1000)
        
        if first_beat_ms:
            self._emit_signal('sm', f"First beat detected at approximately: {first_beat_ms}ms")
            beat_length_ms = 60000 / tempo
            return_val = first_beat_ms + offset_ms
            
            # Return based off bars, no idea if this'll work
            if return_val >= 1000:
                return_val = ((return_val % beat_length_ms) / beat_length_ms)
                
            self._emit_signal('sm', f"Beatoffset estimated at: {return_val}")  
            return round(return_val)
        else:
            self._emit_signal('sm', f"No first beat detected.")
            beat_length_ms = 60000 / tempo
            return_val = offset_ms
    
            # Return based off bars, no idea if this'll work
            if return_val >= 1000:
                return_val = (return_val % beat_length_ms) / beat_length_ms
                
            self._emit_signal('sm', f"Beatoffset estimated at: {return_val}")  
            return round(return_val)
 
    def _adjust_tempo(self, tempo: int | float, tempo_below: int = 90):
        if tempo <= tempo_below:
            old_tempo = tempo
            tempo *= 2
            return tempo, old_tempo
        else:
            return tempo, tempo
        
    def list_to_num(self, item)->float|int:
        try:
            return item[0]
        except:
            return item
        
    def _create_envelope(self, y, sr, hop_length: int):
        self._emit_signal('sm', f"Creating envelope with hop length of: {hop_length}")
        
        harmonics, percussion = librosa.effects.hpss(y=y, hop_length=hop_length)
        # Full song pass
        self._emit_signal('sm', f"Creating full song envelope.")
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
                
        # percussion pass
        self._emit_signal('sm', f"Creating percussion envelope.")
        onset_env_p = librosa.onset.onset_strength(y=percussion,  sr=sr, hop_length=hop_length)
        
        # harmonics pass
        self._emit_signal('sm', f"Creating harmonics envelope.")
        onset_env_h = librosa.onset.onset_strength(y=harmonics, sr=sr, hop_length=hop_length)
                
        return onset_env, onset_env_p, onset_env_h
    
    def _get_closest_val(self, tempos: list[int|float], guess: int|float) -> int | float:
        tempos.sort()
        pos = bisect_left(tempos, guess)
        if pos == 0:
            return tempos[0]
        if pos == len(tempos):
            return tempos[-1]
        before = tempos[pos - 1]
        after = tempos[pos]
        
        if after - guess < guess - before:
            return after
        else:
            return before
     
    # Event management
    def _generate_trackID(self) -> str:
        '''Generates trackInstanceId for the event manager'''
        # The more examples I create the better the generator gets
        examples = [
            "7E575FD94083803BF8477D81E7A3D570",
            "7CAB92814FB8F49DDFBE6485F8422711",
            "1871A2954BEB16B28B6ADE940F6EB289",
            "DFD3439B4EC23D5461E13682B4A20523",
            "1B18233E418ADE043BFAF1945AAD00A8",
            "389E6A454094D231EF1588A72C534845",
            "A7AC521C4C0C32A0D295ACAB67D630D4",
            "32B551404B4D3EB42638F5B7FD4C9584",
            "E932FB01432BA545B45A6E97A160614C",
            
        ]
        
        # Create a library of letters to use in the generator
        alphabet_library = set()
        number_library = set()
        for example in examples:
            for digit in example:
                if digit.isalpha():
                    alphabet_library.add(digit)
                else:
                    number_library.add(digit)
                    
        alphabet_library = ''.join(alphabet_library)
        number_library = ''.join(number_library)
        
        library = alphabet_library + number_library
        
        # Create the id
        trackID = ''.join(secrets.choice(library) for _ in range(32))
        
        return trackID
        
    def _get_event_locations(self, timestamps: np.ndarray|list, tempo: int|float) -> list:
        event_locs = []
        beats_per_bar = 4
        bps = tempo/60
        for onset in timestamps:
            elapsed_beats = onset * bps
            bar_num = int(elapsed_beats // beats_per_bar) + 1
            beat_in_bar = int(elapsed_beats % beats_per_bar) + 1
            event_locs.append((bar_num, beat_in_bar))
        event_locs = sorted(event_locs, key=lambda x: x[0])
        
        return event_locs
    
    def _generate_event_timestamps(self, y, sr, hop_length: int):
        '''
        Generates timestamps based on energy changes in the song
        '''
        timestamps = []
        if self.audio_file:
            y, sr = librosa.load(self.audio_file.path, sr=None)
        # Describe harmony, timbre, and loudness over time.
        chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop_length)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
        rms = librosa.feature.rms(y=y, hop_length=hop_length)

        # Each row is one feature over time.
        X = np.vstack([chroma, mfcc, rms])

        # Put features on comparable scales, then smooth small frame-to-frame changes.
        row_mean = X.mean(axis=1, keepdims=True)
        row_std = X.std(axis=1, keepdims=True)
        X = (X - row_mean) / np.maximum(row_std, 1e-8)

        smooth_frames = max(1, int(0.5 * sr / hop_length))  # 0.5-second smoothing
        X = uniform_filter1d(X, size=smooth_frames, axis=1)

        # Compare the average features in a window before and after each candidate point.
        window_sec = 3.0
        window_frames = int(window_sec * sr / hop_length)
        n_frames = X.shape[1] # type: ignore

        novelty = np.zeros(n_frames)
        if n_frames > 2 * window_frames:
            prefix = np.pad(np.cumsum(X, axis=1), ((0, 0), (1, 0)))
            centers = np.arange(window_frames, n_frames - window_frames)

            before = (prefix[:, centers] - prefix[:, centers - window_frames]) / window_frames
            after = (prefix[:, centers + window_frames] - prefix[:, centers]) / window_frames

            # Larger values mean a bigger change across the candidate point.
            novelty[centers] = np.linalg.norm(before - after, axis=0) / np.sqrt(X.shape[0])

        # Smooth the change curve and select only prominent, separated peaks.
        novelty = gaussian_filter1d(novelty, sigma=max(1, 0.5 * sr / hop_length))
        valid = novelty[window_frames : n_frames - window_frames]

        if valid.size:
            height_cutoff = np.percentile(valid, 90)
            prominence_cutoff = max(0.02, 0.20 * (np.percentile(valid, 95) - np.median(valid)))

            min_gap_sec = 10
            peaks, _ = find_peaks(
                novelty,
                height=height_cutoff,
                prominence=prominence_cutoff,
                distance=int(min_gap_sec * sr / hop_length),
            )

            # Exclude edge regions where a full comparison window isn't available.
            peaks = peaks[
                (peaks >= window_frames) &
                (peaks < n_frames - window_frames)
            ]

            times_sec = librosa.frames_to_time(peaks, sr=sr, hop_length=hop_length)
            timestamps = [round(float(t), 2) for t in times_sec]
        else:
            timestamps = []
        
        return timestamps
        
    def event_creator(self, y, sr, hop_length: int, tempo: int | float):
        trackID = self._generate_trackID()
        hop_length = hop_length // 2
        timestamps = self._generate_event_timestamps(y, sr, hop_length)
        event_locs = self._get_event_locations(timestamps, tempo)
        beat_tracks_data = {
                "beatTracks": [
                {
                    "trackInstanceId": trackID,
                    "trackType": "RequestArenaSwap",
                    "bEnabled": True,
                    "bBeepEventsEnabled": False,
                    "events": [
                    ]
                }
            ]
        }
        
        for event_loc in event_locs:
            beat_tracks_data["beatTracks"][0]["events"].append(
                {
                    "timestamp":{
                        "barNumber": int(event_loc[0]),
                        "beatNumber": int(event_loc[1]),
                        "sliceNumber": 0,
                        "sliceCount": 1,
                        "msOffset": 0
                    }
                }
            )
            
        if self.imported_song:
            self.imported_song["beatTracks"] = beat_tracks_data["beatTracks"]
        else:
            self.error_logger.write(f"Could not write for {self.audio_file} json file not found.")
    
    def clear_events(self, folder):
        meta_path = Path(os.path.join(folder, "Meta.json"))
        data = self.file_manager._load_json_utf16(meta_path)
        try:
            data["beatTracks"].clear()
            self.file_manager._dump_json_as_utf8(meta_path, data)
        except KeyError:
            return
    
    # Custom tempo scoring
    def _beat_grid_score(self, onset_env, bpm, sr, hop_length):
        x = np.asarray(onset_env, dtype=float)
        x = (x - x.mean()) / (x.std() + 1e-8)
        period = 60 * sr / (bpm * hop_length)
        frames = np.arange(len(x))
        best = -np.inf

        for phase in np.linspace(0, period, 80, endpoint=False):
            n = int((len(x) - phase - period / 2) // period) + 1
            if n < 4:
                continue

            beats = phase + period * np.arange(n)
            halfway = beats + period / 2

            score = np.mean(
                np.interp(beats, frames, x) -
                np.interp(halfway, frames, x)
            )
            best = max(best, score)

        return best
    
    def _custom_tempo_guess(self, onset_env, sr, hop_length, init_guess: int|float|None):
        score = self._beat_grid_score(onset_env, init_guess, sr, hop_length)
        if score >= .8:
            return (init_guess, score)
        
        high_scores = []
        t = init_guess
        if score > .8:
            if (t, round(score, 2)) not in high_scores:
                high_scores.append((t, round(score, 2)))
                
        threshhold_score = .8
        while not high_scores and threshhold_score > 0:
            t = 60
            for i in range(60, 200):
                score = self._beat_grid_score(onset_env, t, sr, hop_length)
                if score > threshhold_score:
                    if (t, round(score, 2)) not in high_scores:
                        high_scores.append((t, round(score, 2)))
                t += 1
            threshhold_score -= .1
            
        return high_scores
    
    # Main tempo retrieval
    def generate_data(self, audio_path, model: deeprhythm_custom.DeepRhythmPredictor):
        confidence = 0.0
        tempo = [] # starts as a list and gets narrowed to my best guess
        data = None
        
        self._emit_signal('sm', f"Begining tempo estimation.")
        
        # Load song and get hop length
        y, sr = librosa.load(audio_path, sr = None, mono=True)
        hop_length = round(sr * 256 / (sr / 2))
                
        # initial guess
        try:
            data = self.file_manager._load_json_utf16(Path(self.json_file)) # type: ignore
            guess, confidence = (data["analyseResult"]["tempo"], data["analyseResult"]["fitQuality"])
            # Prevents obscenely low guesses from being used
            if guess < 60 or confidence < .7:
                raise KeyError
        except (KeyError, TypeError):
            tempo_guesses, confidences = model.predict_per_frame(audio_path, include_confidence=True)
            pairs = [(key, value) for key, value in zip(tempo_guesses, confidences)] # type: ignore
            pairs = sorted(pairs, key=lambda p: p[1])
            confidences_by_guess = defaultdict(list)
        
            for guess, conf in pairs:
                confidences_by_guess[guess].append(conf)
                
            averages = {
                guess: sum(confs) / len(confs)
                for guess, confs in confidences_by_guess.items()
            }
            guess, confidence = (pairs[-1][0], averages[pairs[-1][0]])
        
            if confidence < .8:
                guess, confidence = max(averages.items(), key=lambda x: x[1])
                     
        # Refine estimation
        y_trimmed, _ = librosa.effects.trim(y, top_db=40)
        
        # Create envelopes
        onset_env, onset_env_p, onset_env_h = self._create_envelope(sr=sr, y=y_trimmed, hop_length=hop_length)
        
        # Generate priors tightens the range based on confidence
        if confidence < .5:
            prior = lognorm(s=.16, scale=guess)
        elif .5 < confidence < .8:
            prior = lognorm(s=.08, scale=guess)
        elif confidence >= .8:
            prior = lognorm(s=.02, scale=guess)
        else:
            prior = lognorm(s=.2, scale=120)
            
        # Pass 1: Full
        self._emit_signal('sm', f"Pass 1: Full track")
        tempo_full, _ = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env, hop_length=hop_length, prior=prior)# type: ignore
        
        # Pass 2: Percussion
        self._emit_signal('sm', f"Pass 2: Percussion")
        tempo_p, _p = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env_p, hop_length=hop_length, prior=prior)# type: ignore
        
        # Pass 3: Harmonics
        self._emit_signal('sm', f"Pass 3: Harmonics")
        tempo_h, _h = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env_h, hop_length=hop_length, prior=prior)# type: ignore
        
        # have to check them, the editor problems were annoying me
        scores = []
        if (type(tempo_full) == np.ndarray and type(tempo_p) == np.ndarray and type(tempo_h) == np.ndarray):
            self._emit_signal('sm', "Checking tempos in range 60, 200 for beat scores, this may take a moment\nPass 1 of 3")
            scores.extend(self._custom_tempo_guess(onset_env, sr, hop_length, tempo_full[0]))
            self._emit_signal('sm', "Checking tempos in range 60, 200 for beat scores, this may take a moment\nPass 2 of 3")
            scores.extend(self._custom_tempo_guess(onset_env, sr, hop_length, tempo_p[0]))
            self._emit_signal('sm', "Checking tempos in range 60, 200 for beat scores, this may take a moment\nPass 3 of 3")
            scores.extend(self._custom_tempo_guess(onset_env, sr, hop_length, tempo_h[0]))
                        
        # Build and sort various lists used later
        tempos = [self.list_to_num(tempo_full), self.list_to_num(tempo_p), self.list_to_num(tempo_h)]
        scores = sorted(scores, key=lambda x: x[0]) # Sort by score
        scores = list(dict.fromkeys(scores)) # Remove duplicates
        tempos = list(dict.fromkeys(tempos)) # Remove duplicates
        extracted_tempos = [x[0] for x in scores]
        
        try:
            # The margin of error for deeprhythm is 2-ish so if there is a guess within 2
            # I'll use my custom tempo guess
            distance_from_guess = abs(self._get_closest_val(extracted_tempos, guess) - guess)
            if  distance_from_guess < 2:
                guess = self._get_closest_val(extracted_tempos, guess)
            elif scores and scores[0][0] * 2 in extracted_tempos:
                guess = scores[0][0] * 2
        except IndexError as e:
            print(e)


        # Extract the tempo from the list that is closest to
        # the initial guess
        tempo = self._get_closest_val(tempos, guess)
        distance_from_guess = abs(tempo - guess)
        
        # Just use the guess if the refinement
        # isn't outside the margin of error
        if distance_from_guess < 2:
            tempo = guess
        
        if type(tempo) == list:
            self.list_to_num(tempo)
        
        # I figure if that method came up with exactly 1 match and the score is that high
        # it oughta be good
        if len(scores) == 1 and scores[0][1] > 1:
            tempo = scores[0][0]
            
        # Basically if they both round to the same int I'm considering that good
        # It's usually better to not have floats for tempos anyways.
        if type(tempo) == int | float:
            if round(guess) == round(tempo) and guess != tempo:
                tempo = round(tempo)
            else:
                tempo = math.floor(tempo)
        
        confidence = '-' # I am not confident easy way to solve that, remove confidence.

        tempo = self.list_to_num(tempo) # Convert from a list obj to a number             
            
        self._emit_signal('sm', f"Tempo estimate: {tempo}")
        beat_offset = self._beat_offset(audio_file=audio_path, tempo=tempo)
                
        # Event code
        if self.main_window_states.autoGenEventTrack == 2:
            self._emit_signal('sm', f"Creating event track")
            self.event_creator(y=y_trimmed, sr=sr, hop_length=hop_length, tempo=tempo)
            
        return tempo, confidence, beat_offset
    
    # Main
    def run_processor(self):
        scanned_song = {}
        self._emit_signal("ps", 0)
        for i, path in enumerate(self.song_dirs):
            self._emit_signal("mm", f"{self.song_dirs[i]}")
            
            self.json_file = None
            self.imported_song = None
            self.audio_file = None
            tempo = None
            confidence = 0
            beat_offset = 0
            fix_low_bpm = (self.main_window_states and self.main_window_states.adjustBPM == 2) # Init for the variable.
            write_string = ""
            old_tempo = 0
            rescan_tempo, rescan_beat_offset = self._check_rescan()
            
            for file in os.scandir(path):
                if file.name == "Audio.ogg":
                    # Need to go through the code and replace audio path with this
                    self.audio_file = file
                elif file.name == "Meta.json":
                    self.json_file = str(file.path)
                else:
                    self.error_logger.write(f"Unknown file: {file}")
                    continue
                
                if self.json_file:
                    self.imported_song = self.file_manager._load_json_utf16(Path(self.json_file))
                else:
                    continue
            
            if not self.audio_file or not self.json_file:
                self.error_logger.write(f"Failed to get need json and audio files!")
                return
            
            if self.file_manager and (self.imported_song and self.audio_file):
                
                tempo = self.imported_song["tempo"]
                scanned_song = self.file_manager.check_scanned_song(self.song_names[i])  
                
                if scanned_song:
                    
                    tempo = scanned_song["tempo"]
                    old_tempo = tempo
                    
                    # Check for game data and scanned song list tempo mismatch.
                    if (round(self.imported_song["tempo"], 2) != round(scanned_song["tempo"], 2)
                        and round(self.imported_song["tempo"], 2) != round(scanned_song["adjustedTempo"], 2)):
                        
                        tempo, confidence, beat_offset = self.generate_data(audio_path=self.audio_file, model=self.model)
                        old_tempo = tempo
                        # _get_tempo already adjusts the bpm
                        rescan_beat_offset = False
                        
                    elif rescan_tempo:
                        
                        tempo, confidence, beat_offset = self.generate_data(audio_path=self.audio_file, model=self.model)
                        old_tempo = tempo
                        # _get_tempo already adjusts the bpm
                        rescan_beat_offset = False
                        
                    else:
                        beat_offset = scanned_song["beatOffset"]   
                else:
                    tempo, confidence, beat_offset = self.generate_data(audio_path=self.audio_file, model=self.model)
                    old_tempo = tempo
                
                if fix_low_bpm:
                    tempo, old_tempo = self._adjust_tempo(tempo, 95)
                        
                if rescan_beat_offset:
                    beat_offset = self._beat_offset(audio_file=self.audio_file, tempo=tempo)
                    

                # Round the tempo data to a meaningful level of percision.
                # DO THIS LAST roudning can mess up calculations.
                tempo = round(tempo, 2)
                old_tempo = round(old_tempo, 2)
                
                if not confidence and scanned_song:
                    confidence = scanned_song["confidence"]
                                    
                self.imported_song["tempo"] = tempo
                self.imported_song["customTempoSections"] = []
                self.imported_song["beatOffset"] = beat_offset
                                        
                self.file_manager._dump_json_as_utf8(Path(self.json_file).resolve(), self.imported_song)
                
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
            self._emit_signal('ps', i+1)
        self.main_window_states.freshScan = 0
        self.file_manager.save_state(main_window_states=self.main_window_states)
        self._emit_signal("ps", 0)
        
    def run_single_shot(self, folder_path):
        if not folder_path:
            return
        
        self._emit_signal("mm", f"Scanning {folder_path}")
        
        # Init vars
        self.imported_song = None
        tempo = None
        confidence = 0
        beat_offset = 0
        fix_low_bpm = (self.main_window_states and self.main_window_states.adjustBPM == 2) # Init for the variable.
        write_string = ""
        old_tempo = 0
        
        for file in os.scandir(folder_path):
            if file.name == "Audio.ogg":
                self.audio_file = file
            elif file.name == "Meta.json":
                self.json_file = str(file.path)
            else:
                self.error_logger.write(f"Unknown file: {file}")
                continue
            if self.json_file:
                self.imported_song = self.file_manager._load_json_utf16(Path(self.json_file))
            else:
                continue
            
        if not self.audio_file or not self.json_file:
            self.error_logger.write(f"Failed to get need json and audio files!")
            return
        
        if self.file_manager and (self.imported_song and self.audio_file):
            tempo = self.imported_song["tempo"]
            scanned_song = self.file_manager.check_scanned_song(folder_path)  
            time.sleep(3)
            tempo, confidence, beat_offset = self.generate_data(audio_path=self.audio_file, model=self.model)
            if fix_low_bpm:
                tempo, old_tempo = self._adjust_tempo(tempo, 95)
                                    
            # Round the tempo data to a meaningful level of percision.
            # DO THIS LAST roudning can mess up calculations.
            tempo = round(tempo, 2)
            old_tempo = round(old_tempo, 2)
            
            if not confidence and scanned_song:
                confidence = scanned_song["confidence"]
                            
            self.imported_song["tempo"] = tempo
            self.imported_song["customTempoSections"] = []
            self.imported_song["beatOffset"] = beat_offset
                        
            self.file_manager._dump_json_as_utf8(Path(self.json_file).resolve(), self.imported_song)
            
            if type(confidence) != str:     
                write_string = f"{folder_path} (Tempo: {tempo}, Confidence: {int(confidence * 100)}%, {beat_offset})"
            else:
                write_string = f"{folder_path} (Tempo: {tempo}, Confidence: {confidence}, {beat_offset})"
            
            # log
            self.info_logger.write(write_string)
            
            song_data = {
                "tempo":old_tempo,
                "adjustedTempo":tempo,
                "beatOffset":beat_offset,
                "confidence":confidence,
            }
            
            if scanned_song:
                self.file_manager.update_scanned_item(folder_path, song_data)
            else:
                self.file_manager.add_scanned_item(folder_path, song_data)
                    
        self.file_manager.save_state(main_window_states=self.main_window_states)