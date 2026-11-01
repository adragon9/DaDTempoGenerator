# Changelog

## [1.1.1-beta] [11/1/26]

- Added Offset Calibration
- Tempo algorithm changed again
  - Looking for the right composition of speed and accuracy. This will be an ongoing battle.
- Changed the changelog format
- Commented out large chunks of code related to previous beat offset features
  - These blocks of comments will be removed later
- Updated feedback messages so that the user knows what the program is doing.
- Added sound folder for sound effects
  - Right now the only sound effect is for the calibration test.
- Updated README to reflect the current application features.
- Added single song scanning

---

## [1.1.0-beta] - [I forgot when I did this one]

- Error 'SongAnalyzer' object has no attribute 'progress_string' while trying to get the progress string.
- "Error only 0-dimensional arrays can be converted to Python scalars while conver" wasn't a finished sentence.
- Ignore options to the rest of the dropdowns
- Framework for single song scanning (not yet implemented completely)
- Tempo Algorithm
- Beat Offset calculation
- UI Appearance updated
- Removed the precision selection dropdown, it serves no purpose with the new algorithm
- Miscellaneous unused definitions
- Added a list veiw of all scanned song
  - Note: Song names may be cut off, it uses the folder name containing the song and that has a character limit
    I will be addressing that later.

---

## [1.0.0-beta] - 2026-04-08

_Initial beta release._

- Adjust low bpm toggle
- Virtual surround sound toggle
- Device type, beat feeling, and input device type options
- Confidence threshold options
- More verbose progress updates
- User guide
- Tempo estimation methods updated in attempt to compete with games official tool release
- Beat Offset detection updated, now comprised of (first detected beat + user hardware latency data)
- File management methods changed
- More robust system for preventing rescans when uneeded
- Removed unecessary imports

---
