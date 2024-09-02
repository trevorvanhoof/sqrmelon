---

Clone the WaveSabre submodule, you will need that for the includes

---

#### Updating the prebuilt binaries 

(i.e. in case of visual studio version mismatch)

Download
  https://web.archive.org/web/20200502121517/https://www.steinberg.net/sdk_downloads/vstsdk366_27_06_2016_build_61.zip 
and unzip it into 
  sqrmelon\MelonPan\synths\WaveSabre\Vst3.x 
wwithout the VST3 SDK intermediate folder - so that sqrmelon\MelonPan\synths\WaveSabre\Vst3.x\base exists.

Open the x86_x64 Cross Tools Command Prompt for your visual studio version, 
found in Start Menu -> Programs -> Visual Studio # -> Visual Studio Tools -> VC 
(just search for x86 and it should pop up!)

In that terminal, navigate to
  sqrmelon\MelonPan\synths\WaveSabre 
and run:
  cmake -B build -A Win32

Open 
  sqrmelon\MelonPan\synths\WaveSabre\build\WaveSabre.sln
change the target from Debug to MinSizeRel, and build the entire solution.

Take these files:
  sqrmelon\MelonPan\synths\WaveSabre\build\WaveSabreCore\MinSizeRel\WaveSabreCore.lib
  sqrmelon\MelonPan\synths\WaveSabre\build\WaveSabrePlayerLib\MinSizeRel\WaveSabrePlayerLib.lib
  sqrmelon\MelonPan\synths\WaveSabre\build\MSVCRT\MinSizeRel\msvcrt.lib
And move them to:
  sqrmelon\MelonPan\synths\WaveSabre_prebuilt