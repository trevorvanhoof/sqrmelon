# SqrMelon
A tool for keyframe animation & fragment shader management for 64k executables.

## Manual
An extensive PDF can be found in the repo:
https://github.com/trevorvanhoof/sqrmelon/blob/master/SqrMelon%20manual.pdf

## Disclaimer
This tool is provided as-is, feel free to use it, contact me if you have any questions. 

While I am interested in bug reports and willing to help out, I urge you not to rely on me to fix them within small timeframes!

Beware that bugs & feature requests can be "beyond scope".

## Third party
SqrMelon is written with Python3.11+ (64 bit) and PySide2, it also depends on some third party python packages.
It comes with an install.txt with the right download links to help you get started.
The C++ Player project has some other dependencies, listed below:

In Release it also calls a post-build step which gives the .exe to kkrunchy to get the compressed final binary.
http://www.farbrausch.de/~fg/kkrunchy/
Get the "a" version and put it in SqrMelon/Player/

For audio we nowadays have various defines in "settings.h" that can open up dependencies you can download and use:

#### define AUDIO_64KLANG2
Requires the following files from https://github.com/hzdgopher/64klang
out of Player/Player to be placed in the 64klang2 sub folder like so:
 64klang2/sample_t.cpp
 64klang2/sample_t.h
 64klang2/Synth.cpp
 64klang2/Synth.h
 64klang2/SynthAllocator.cpp
 64klang2/SynthAllocator.h
 64klang2/SynthNode.cpp
 64klang2/SynthNode.h
 64klang2/SynthPlayer.cpp
 64klang2/SynthPlayer.h

64klang songs also export a 64k2Patch.h and 64k2Song.h which should be placed in the same folder

#### define AUDIO_BASS
Requires the following files from Bass 2.4 (from https://www.un4seen.com/download.php?bass24)
to be placed next to the other source files:
 bass.dll
 bass.h
 bass.lib

#### define AUDIO_WAVESABRE
Requires the following files from https://github.com/logicomacorp/WaveSabre
to be placed next to the other source files:
 wavesabreplayerlib.h
 wavesabrecore.h

#### define SUPPORT_PNG
Requires the following files from https://github.com/lvandeve/lodepng
to be placed next to the other source files:
 lodepng.h
 lodepng.cpp

In addition it requires WaveSabreCore.Lib and WaveSabrePlayer.lib, which
may easily be built by cloning the entire WaveSabre repo.
As of this moment there are no public pre-built release distrubtions.

## Other defines
#### define RESOLUTION_SELECTOR
This requires dialog.rc to be in the project resources. If it is missing or for othe reasons
the resource can not be resolved at runtime the app immediately exits before creating any windows.

Feel free to edit Dialog.rc so the resolution selector title matches the title in settings.h!

#### define SUPPORT_3D_TEXTURE
I have not used this in ages, but it should still work! It allows you to render a pass as horizontal strip of 3D texture slices,
which will automatically be rendered and cast to 3D texture. I used it to create static 3D volume textures for clouds in Eidolon.

## Success stories
SqrMelon has been used for the following productions:

Once upon a Time (2nd) at TDF 2017:

http://www.pouet.net/prod.php?which=68971

Eidolon (1st) at Revision 2017:

http://www.pouet.net/prod.php?which=69669

Yermom at Evoke 2017:

http://www.pouet.net/prod.php?which=71570

YIQI (2nd) at Trsac 2017:

http://www.pouet.net/prod.php?which=71977

\*Monster black Hole (video):

https://www.youtube.com/watch?v=xPzl1-UGky8

Party Gipfeler (3rd) at Revision 2018:

http://www.pouet.net/prod.php?which=75739

Transphosphorylation (2nd) at Revision 2018:

http://www.pouet.net/prod.php?which=75728


\* Star = final product did not use the player code, only the tool (& possibly frame by frame renderer).

## Credits

This tool was largely developed by:
Trevor van Hoof (Tropical Trevor) http://trevorius.com/

Various additions, bugfixes and ideas were contributed by Glow, Andro, Wurstgetrank amongst others.

The template project uses snippets from various sources, credited in comments in the source.
