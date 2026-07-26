# DaDTempoGen README
## Description

DaDTempoGen scans imported songs for Dead as Disco and generates a Beat Offset and Tempo estimate and writes it to the songs json file. 

## How to install & Use

### Installation
1. Download the 7z archive containing the program
2. Extract it to any **NON-SYSTEM** location.

### Usage
1. Run the exe.
    + DO NOT MOVE THE FILE "deeprhythm-0.7.pth" OUT OF THE SAME FOLDER AS THE EXE. IT WILL CRASH.
    + The game will not update at run time, you must run this *and then* start the game.

2. Click Run.
    + You may see the command prompt flash when the deeprhytm model loads don't really know how to stop it from doing that right now but figured I'd give you a heads up.

3. Check the data folder for all generated logs and json files.

## Need to know

+ DaDTempoGen first and foremost is in alpha. This is a proof of concept more or less but it should still be fairly accurate.

+ There is an experimental branch which will recieve updates *far* more frequently than the main branch. The reason is that I have the main branch posted on nexus and that requires constant security checks so updates for the main branch must be substantial.
  + Please note that with this branch many things may be different, for example, I have the current experimental branch set to use native sample rates. This means that it may use more memory on average to process a song.

+ If you find any issues please post it either in the issues section here or the bugs section on nexus mods.

+ If you are coming from nexus and the project there says that my files are suspicious you can take a look at the virus total analysis of the project [here](https://www.virustotal.com/gui/file/a162c9cd069397e349e69db1bd6abb95db29c88b3f8b1a54d5221bf02a4a0717).
  + This is only for the main branch, though feel free to run the experimental through virus total as well if you'd like.
 
+ Sometimes you may not here hits connect in game... I can only guess that it's because DaDTempoGen lines the tempo up with the kick and the kick of the song drowns out the sound of the punch. Not sure how to fix that.

+  This relies on a vanilla installation it assumes the file path to the songs is:
    +  "C:\Users\{user}\AppData\Local\Pagoda\Saved\ImportedSongs"
    +  That being said you should be able to change the settings in "\data\config\settings.json"
 
+ This is only tested on Windows 11 it may or may not be compatible with Windows 10 and is almost certainly not compatible with non-windows OS's. I will look into cross-platform compatibility much, much further down the line.

+ This application is memory and CPU heavy due to the tempo estimation libraries I used. The highest I have seen it use is around ~1.8 GB of memory but depending on things like the length of the song it could be much higher. I will be working on optimizing this at some point but for now I wanted to get the main features up and running for the ALPHA phase.
    + Though be prepared that the memory and CPU usage just is what it is, I want this to be as accurate as possible and it may just have to stay this way.

## Future Plans

Right now my plans are to add some basic options for things that will allow the user to customize their experience, such as:
1. The ability to turn off auto-double and auto-halving to keep the songs tempo within 120-200bpm.
2. The ability to select a standard sample rate resolution.
3. The ability to blacklist/whitelist certain songs to either never be analyzed or always be analyzed.

As for main features these are a bit more ambitious in someways and will take some time:
1. Segment analysis.
  + In other words, I want to be able to have varying tempos for different segments of a song. (this will probably be the last feature I focus on)
2. Song editor.
  + After generating I'd like you to be able to go through each song and make changes as you see fit all within the app.

As for more minor things, I will be tweaking the analysis pretty frequently until I feel I have the best possible generalized tempo estimation and, of course bug fixes.

