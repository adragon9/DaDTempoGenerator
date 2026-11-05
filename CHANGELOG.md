# Changelogs

## [1.1.4-beta] [11/5/26]

- Code refactoring
- Bugfixes
- Further refinements on tempo estimation
- Added the ability to clear events for a song from the context menu
- Added logging that should catch problems stemming from the worker thread

## [1.1.3-beta] [11/4/26]

- updated stylesheets
- fixed a bug where the scan might have been occuring twice per song
- added support for generating event tracks automatically WIP
- fixed an issue where building the songlist quit early on error which lead to unscanned songs
- Added some safeguards to prevent duplicate song entries from appearing
- added additional tempo estimation passes to try to increase accuracy

## [1.1.2-beta] [11/3/26]

- Tempo estimations tweaked
  - Using priors now instead of just flat start bpms
- Hop length now accounts for varying sample rates
  - This should result in faster scanning and more accurate to similarly accurate guesses
- Settings are now saved upon being changed
- The viewer now uses the name that is in the Meta.json for the displayed song name
- Added tool tips so you can see where that song is located on you computer
- Added a fresh scan checkbox so that you can rescan all songs on demand
- UI Refinements
- Updated requirements
- Added a known issues document
- Updated some comments and cleaned up the code a bit
- Fixed being able to interact with the main window while the beat offset calibration window was open
- Added the ability to open the song folder from the context menu
- Added a visualizer to the beat offset calibration menu
- Updated beat calibration should be more consistent
- Cleaned up imports

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
