from dataclasses import dataclass
from typing import Literal
@dataclass
class MainWindowStateManager():
    # Check boxes
    # 0 = False, 1 = Partial, 2 = True
    adjustBPM: int = 2
    virtualSurround: int = 0
    
    # Combobox stuff
    speakerTypes = ["Wired Headphones", "Bluetooth Headphones", "Desktop/PC Speakers",
                    "TV via HDMI", "Steam Deck", "Wireless 2.4GHz", "Custom/Unkown"]
    beatFeelings = ["Early", "Good", "Late"]
    controllerTypes = ["Wired", "Wireless 2.4Ghz", "Wireless Bluetooth", "Ignore"]
    currentSpeakerType: str = speakerTypes[0]
    currentBeatFeeling: str = beatFeelings[0]
    currentController: str = controllerTypes[0]