from dataclasses import dataclass

# Main variable handler for the program.
@dataclass
class MainWindowStateManager():
    # Check boxes
    # 0 = False, 1 = Partial, 2 = True
    adjustBPM: int = 2
    virtualSurround: int = 0
    
    # Global offset, signed int    
    globalOffset: int = 0
    
    # Combobox stuff
    # speakerTypes = ["Wired Headphones", "Bluetooth Headphones", "Desktop/PC Speakers",
    #                 "TV via HDMI", "Steam Deck", "Wireless 2.4GHz", "Custom/Unkown", "Ignore"]
    # beatFeelings = ["Early", "Good", "Late", "Ignore"]
    # controllerTypes = ["Wired", "Wireless 2.4Ghz", "Wireless Bluetooth", "Ignore"]
    # librosaReliance = ["Low", "Medium", "High"]
    # currentSpeakerType: str = speakerTypes[0]
    # currentBeatFeeling: str = beatFeelings[0]
    # currentController: str = controllerTypes[0]
    # currentConfidenceThresh: str = librosaReliance[1]
