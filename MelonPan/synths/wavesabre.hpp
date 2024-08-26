#include "WaveSabre/WaveSabrePlayerLib/include/WaveSabrePlayerLib.h"
#include "WaveSabre/WaveSabreCore/include/WaveSabreCore.h"

using namespace WaveSabrePlayerLib;

#include "../../content/WaveSabreSong.h"

WaveSabrePlayerLib::RealtimePlayer player(&Song, 1);

void audioInit() {
}

void audioPlay() {
	player.Play();
}

float audioCursor() {
	return (float)player.GetSongPos();
}
