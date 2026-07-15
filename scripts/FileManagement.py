import os, json

# Classes
from pathlib import Path

# Custom classes
import helpers.DebugHelper as dh

class FileManager():
    def __init__(self):
        self.__data_path__ = r'.\data'
        self.__settings_path__ = f"{self.__data_path__}\\config\\settings.json"
        self._make_dirs()
        
        self.__scanned_path__ = self.get_scanned_songs_path()
        
    # Private functions
    def _create_settings(self):
        with open(self.__settings_path__, 'w', encoding='utf-8') as file:
            default_settings = {
                "paths": {
                    "DaDImportedSongsDir": "~\\AppData\\Local\\Pagoda\\Saved\\ImportedSongs",
                    "data":".\\data",
                },
                "files":{
                    "scanned_songs":"scanned_songs.json"
                }
            }
            json.dump(default_settings, file, indent=4)
    
    def _make_dirs(self):
        # Creates the data folder
        if not os.path.exists(self.__data_path__):
            try:
                os.mkdir(self.__data_path__)
            except Exception as e:
                print(f"Error {e} in _make_dirs()")
                
        # Creates the config file with default settings       
        if not os.path.exists(self.__settings_path__):
            try:
                os.mkdir(f"{self.__data_path__}\\config")
            except FileExistsError as e:
                pass
            finally:
                self._create_settings()
    
    # Get objects
    def get_imported_songs_path(self):
        with open(self.__settings_path__, 'r') as file:
            data = json.load(file)
        
        try:
            imported_song_path = os.path.expanduser(data["paths"]["DaDImportedSongsDir"])
        except Exception as e:
            imported_song_path = data["paths"]["DaDImportedSongsDir"]
        
        return imported_song_path
    
    # These all need restructuring latter I don't like them. 
    def get_data_path(self):
        with open(self.__settings_path__, 'r') as settings:
            data = json.load(settings)
            
        self.__data_path__ = data["paths"]["data"]
        return data["paths"]["data"]
    
    def get_scanned_songs_path(self):
        with open(self.__settings_path__, 'r') as settings:
            data = json.load(settings)
            
        self.__scanned_path__ = data["files"]["scanned_songs"]
        return data["files"]["scanned_songs"]
    
    def check_scanned_song(self, name):
        if not os.path.exists(f"{self.__data_path__}\\{self.__scanned_path__}"):
            with open(f"{self.__data_path__}\\{self.__scanned_path__}", 'w') as file:
                scanned_songs = {
                    "songs":{}
                }
                json.dump(scanned_songs, file, indent=4)
                
        with open(f"{self.__data_path__}\\{self.__scanned_path__}", 'r') as file:
            scanned_songs = json.load(file)
        try:
            return scanned_songs["songs"][name]
        except KeyError:
            return None
            
    # List generators
    def add_scanned_item(self, name, tempo, beat_offset, confidence):
        if not os.path.exists(f"{self.__data_path__}\\{self.__scanned_path__}"):
            with open(f"{self.__data_path__}\\{self.__scanned_path__}", 'w') as file:
                scanned_songs = {
                    "songs":{}
                }
                json.dump(scanned_songs, file, indent=4)
                
        try:
            with open(f"{self.__data_path__}\\{self.__scanned_path__}", 'r') as file:
                json.load(file)
        except Exception:
            with open(f"{self.__data_path__}\\{self.__scanned_path__}", 'w') as file:
                scanned_songs = {
                    "songs":{}
                }
                json.dump(scanned_songs, file, indent=4)
                
        with open(f"{self.__data_path__}\\{self.__scanned_path__}", 'r') as file:
            scanned_songs = json.load(file)
            
            scanned_songs["songs"][name] = {
                "tempo":tempo,
                "beatOffset":beat_offset,
                "confidence": confidence
            }
            
        with open(f"{self.__data_path__}\\{self.__scanned_path__}", 'w') as file:
            json.dump(scanned_songs, file, indent=4)
        
        
        