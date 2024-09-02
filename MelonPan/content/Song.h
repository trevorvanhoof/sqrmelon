#include <WaveSabreCore.h>
#include <WaveSabrePlayerLib.h>

WaveSabreCore::Device *SongFactory(SongRenderer::DeviceId id)
{
	switch (id)
	{
	case SongRenderer::DeviceId::Slaughter: return new WaveSabreCore::Slaughter();
	}
	return nullptr;
}

const unsigned char SongBlob[] =
{
	0x8c, 0x00, 0x00, 0x00, 0x44, 0xac, 0x00, 0x00, 0x25, 0x49,
	0x92, 0x24, 0x49, 0x92, 0x24, 0x40, 0x01, 0x00, 0x00, 0x00,
	0x01, 0xac, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x3f, 0x00, 0x00, 0x80, 0x3f, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x31, 0xdf, 0x7f, 0x3f, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x69,
	0xb4, 0xe7, 0x3c, 0x00, 0x00, 0x00, 0x3f, 0x0a, 0xd7, 0x23,
	0x3c, 0x00, 0x00, 0x00, 0x00, 0x69, 0xb4, 0xe7, 0x3c, 0x00,
	0x00, 0x80, 0x3f, 0x0a, 0xd7, 0x23, 0x3c, 0x00, 0x00, 0x00,
	0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x69,
	0xb4, 0xe7, 0x3c, 0x00, 0x00, 0x00, 0x3f, 0x0a, 0xd7, 0x23,
	0x3c, 0x00, 0x00, 0x00, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0xac, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00,
	0x00, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3c,
	0x64, 0xea, 0x24, 0x00, 0x00, 0xbc, 0xea, 0x24, 0x00, 0x00,
	0x3c, 0x64, 0xea, 0x24, 0x00, 0x00, 0xbc, 0xea, 0x24, 0x00,
	0x00, 0x3c, 0x64, 0xea, 0x24, 0x00, 0x00, 0xbc, 0xea, 0x24,
	0x00, 0x00, 0x3c, 0x64, 0xea, 0x24, 0x00, 0x00, 0xbc, 0xea,
	0x24, 0x00, 0x00, 0x3c, 0x64, 0xea, 0x24, 0x00, 0x00, 0xbc,
	0xea, 0x24, 0x00, 0x00, 0x3c, 0x64, 0xea, 0x24, 0x00, 0x00,
	0xbc, 0xea, 0x24, 0x00, 0x00, 0x3c, 0x64, 0xea, 0x24, 0x00,
	0x00, 0xbc, 0xea, 0x24, 0x00, 0x00, 0x3c, 0x64, 0xea, 0x24,
	0x00, 0x00, 0xbc, 0x8a, 0x73, 0x02, 0x00, 0x3c, 0x64, 0xea,
	0x24, 0x00, 0x00, 0xbc, 0xea, 0x24, 0x00, 0x00, 0x3c, 0x64,
	0xea, 0x24, 0x00, 0x00, 0xbc, 0xea, 0x24, 0x00, 0x00, 0x3c,
	0x64, 0xea, 0x24, 0x00, 0x00, 0xbc, 0xea, 0x24, 0x00, 0x00,
	0x3c, 0x64, 0xea, 0x24, 0x00, 0x00, 0xbc, 0xea, 0x24, 0x00,
	0x00, 0x3c, 0x64, 0xea, 0x24, 0x00, 0x00, 0xbc, 0xea, 0x24,
	0x00, 0x00, 0x3c, 0x64, 0xea, 0x24, 0x00, 0x00, 0xbc, 0xea,
	0x24, 0x00, 0x00, 0x3c, 0x64, 0xea, 0x24, 0x00, 0x00, 0xbc,
	0xea, 0x24, 0x00, 0x00, 0x3c, 0x64, 0xea, 0x24, 0x00, 0x00,
	0xbc, 0x00, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0xc5,
	0x8f, 0x61, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3f, 0x01, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc5,
	0x8f, 0x61, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3f, 0x01,
	0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x80, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x01,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

SongRenderer::Song Song = {
	SongFactory,
	SongBlob
};
