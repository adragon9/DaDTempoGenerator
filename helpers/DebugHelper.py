import subprocess, platform, os, time
from pathlib import Path

# Custom classes
import scripts.FileManagement as fm

class PrintManager():
    def __init__(self):
        pass
    
    def clear_terminal(self):
        cmd = "cls" if platform.system() == "Windows" else "clear"
        subprocess.run(cmd, shell=True)

class LogManager():
    def __init__(self, logfile: str | Path, encoding="utf-8"):
        self.file_manager = fm.FileManager()
        self.__data_path__ = self.file_manager.get_data_path()
        self.__log_path__ = f"{self.__data_path__}\\logs"
        
        if not os.path.exists(self.__log_path__):
            os.mkdir(self.__log_path__)
            
        self.__logfile__ = os.path.join(self.__log_path__, logfile)
        self.encoding = encoding
        
        if not os.path.exists(self.__logfile__):
            with open(self.__logfile__, 'w', encoding=self.encoding) as log:
                log.write("")
    
    def write(self, text: str):
        with open(self.__logfile__, 'a', encoding=self.encoding) as log:
            log.write(text+"\n")
    
    def read(self):
        with open(self.__logfile__, 'r', encoding=self.encoding) as log:
            return log.readlines()
    
    def wipe_log(self):
        with open(self.__logfile__, 'w', encoding=self.encoding) as log:
            log.write("")
    
    def get_log_time(self, format_str: str = "%d/%m/%Y @%H:%M:%S"):
        """
        Returns the time in a using time's strftime and time.localtime()\n
        Default format is day/month/year hours:mins:secs (24-hour)
        """
        return time.strftime(format_str, time.localtime())