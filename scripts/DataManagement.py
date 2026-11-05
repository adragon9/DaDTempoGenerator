from dataclasses import dataclass

# Main variable handler for the program.
@dataclass
class MainWindowStateManager():
    # Check boxes
    # 0 = False, 1 = Partial, 2 = True
    adjustBPM: int = 2
    freshScan: int = 0
    autoGenEventTrack: int = 0
    
    # Global offset  
    globalOffset: int = 0