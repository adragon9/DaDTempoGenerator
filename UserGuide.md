# User Guide

## Usage

### Checkboxes

- Adjust low bpm - This option will double the tempo of any song that falls under 90 bpm.
- Virtual Surround Sound - This adds about 40ms to the beat offset to account for virtual surround sound latency

### Comboboxes

- Audio Device Connection - Select the type of connection your audio device has to your PC/Gaming Device
- feels - Select if the punches in the game feel early, good, or late.
- Controller/Keyboard Connection - Select the type of connection your input device has to your PC/Gaming Device
- Confidence threshold for switching analysis methods - This combobox features Low, Medium, or High options. They directly impact at what threshold deeprhythm's confidence should be at before its tempo analysis is accepted. For example, if this is set to High deeprhythm must be no less than 90% confident for the song's tempo to not be re-evaluated by librosa.

### Buttons

- Run - runs the analysis

## Info

### Tempo analysis libraries

- Deeprhythm
- Librosa

### Tested with

- Windows 11
  - Intel i7-13700k
  - NVIDIA 3070ti 8GB VRAM
  - 32 GB RAM

### App Version

- 1.0.0-beta
