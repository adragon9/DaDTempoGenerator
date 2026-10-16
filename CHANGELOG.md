# Changelog

## [1.1.0-beta] - [UNDATED]

### Fixed

- Error 'SongAnalyzer' object has no attribute 'progress_string' while trying to get the progress string.
- "Error only 0-dimensional arrays can be converted to Python scalars while conver" wasn't a finished sentence.

### Added

- Ignore options to the rest of the dropdowns
- Framework for single song scanning (not yet implemented completely)

### Changed

- Tempo Algorithm
- Beat Offset calculation
- UI Appearance updated

### Removed

- Removed the precision selection dropdown, it serves no purpose with the new algorithm
- Miscellaneous unused definitions

---

## [1.0.0-beta] - 2026-04-08

_Initial beta release._

### Added

- Adjust low bpm toggle
- Virtual surround sound toggle
- Device type, beat feeling, and input device type options
- Confidence threshold options
- More verbose progress updates
- User guide

### Changed

- Tempo estimation methods updated in attempt to compete with games official tool release
- Beat Offset detection updated, now comprised of (first detected beat + user hardware latency data)
- File management methods changed
- More robust system for preventing rescans when uneeded

### Removed

- Removed unecessary imports

---
