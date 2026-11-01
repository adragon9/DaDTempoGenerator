# Package imports
import os, json, charset_normalizer

# Class imports
from pathlib import Path

# Definition imports
from dataclasses import asdict

# Custom class imports
import scripts.DataManagement as dm

class FileManager():
    def __init__(self):
        self.__data_path__ = Path('.\\data').resolve()
        self.__settings_path__ = Path(os.path.join(str(self.__data_path__), "config\\settings.json")).resolve()
        self._make_dirs()
        
        self.__scanned_path__ = self.get_scanned_songs_path()
        
    # Private functions
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
                pass
                
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
        data = self._load_json_utf16(self.__settings_path__)
        return Path(data["paths"]["data"]).resolve()
    
    def get_scanned_songs_path(self) -> Path:
        data = self._load_json_utf16(self.__settings_path__)
        return Path(os.path.join(self.__data_path__, data["files"]["scanned_songs"])).resolve()
    
    def get_previous_user_choices(self):
        try:
            return self._load_json_utf16(self.__scanned_path__)["user_choices"]
        except Exception as e:
            return None
    
    def check_scanned_song(self, name):
        scanned_songs = {
            "songs":{}
        }
        try:
            if not os.path.exists(self.__scanned_path__):
                self._dump_json_as_utf8(self.__scanned_path__, scanned_songs)
            scanned_songs = self._load_json_utf16(self.__scanned_path__)
        except json.decoder.JSONDecodeError:
            self._dump_json_as_utf8(self.__scanned_path__, scanned_songs)
            return None
            
        try:
            return scanned_songs["songs"][name]
        except KeyError:
            return None
            
    # List generators
    def add_scanned_item(self, obj_name: str, obj: dict):
        if not os.path.exists(self.__scanned_path__):
            scanned_songs = {
                "songs":{}
            }
            self._dump_json_as_utf8(self.__scanned_path__, scanned_songs)
        
        scanned_songs = self._load_json_utf16(self.__scanned_path__)                
        scanned_songs["songs"][obj_name] = obj
        self._dump_json_as_utf8(self.__scanned_path__, scanned_songs)
            
    def update_scanned_item(self, obj_name: str, obj:dict):
        data = self._load_json_utf16(self.__scanned_path__)
        data["songs"][obj_name].update(obj)
        self._dump_json_as_utf8(self.__scanned_path__, data)
            
    def save_state(self, main_window_states: dm.MainWindowStateManager|None):
        if main_window_states:
            data = self._load_json_utf16(self.__scanned_path__)
            
            user_choice_dict = asdict(main_window_states)
            print(user_choice_dict)
            user_choice_dict_scrubbed = {}
            for key in user_choice_dict:
                if type(user_choice_dict[key]) == list:
                    continue
                else:
                    user_choice_dict_scrubbed[key] = user_choice_dict[key]
            
            print(user_choice_dict_scrubbed)
            data["user_choices"] = user_choice_dict_scrubbed
            
            with open(self.__scanned_path__, 'w') as file:
                json.dump(data, file, indent=4)
        else:
            return None