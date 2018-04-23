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
SqrMelon is written with Python2.7 (64 bit) and PyQt4, it also depends on some third party python packages.
It comes with an install.txt with the right download links to help you get started.
The C++ Player project has some other dependencies, listed below:

We included 64klang for music, but adding different synths should be trivial.
SqrMelon/Player/64klang2 already contains the necessary files, but you may find the latest version at:
https://github.com/hzdgopher/64klang

In Release it also calls a post-build step which gives the .exe to kkrunchy to get the compressed final binary.
http://www.farbrausch.de/~fg/kkrunchy/
Get the "a" version and put it in SqrMelon/Player/

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
