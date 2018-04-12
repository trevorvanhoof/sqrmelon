
#ifdef CAPTURE_TO_IMAGES

#include <stdio.h>
#include <malloc.h>


void StoreTGAImageToFile(const char* filename, int width, int height, unsigned char* pixels)
{
	FILE* file = 0;
	fopen_s(&file, filename, "wb");

	//write out identification number
	char idSize = (char)0;
	fwrite(&idSize, sizeof(unsigned char), 1, file);

	char colorMap = (char)0;
	fwrite(&colorMap, sizeof(unsigned char), 1, file);

	char colorType = (char)2;
	fwrite(&colorType, sizeof(char), 1, file);

	//colour map specification
	short int colourMapEntryOffset = 0;
	short int colourMapLength = 0;
	unsigned char colourMapEntrySize = 0;
	fwrite(&colourMapEntryOffset, sizeof(short int), 1, file);
	fwrite(&colourMapLength, sizeof(short int), 1, file);
	fwrite(&colourMapEntrySize, sizeof(unsigned char), 1, file);

	short int xOrig = 0;
	short int yOrig = 0;
	short int width16 = width;
	short int height16 = height;
	unsigned char bitdepth = (char)32;
	unsigned char imageDesc = (char)0;

	fwrite(&xOrig, sizeof(short int), 1, file);
	fwrite(&yOrig, sizeof(short int), 1, file);
	fwrite(&width16, sizeof(short int), 1, file);
	fwrite(&height16, sizeof(short int), 1, file);
	fwrite(&bitdepth, sizeof(unsigned char), 1, file);

	imageDesc = 0;
	imageDesc = 0x00000000;
	fwrite(&imageDesc, sizeof(char), 1, file);

	fwrite(pixels, 1, width*height * 4, file);

	fclose(file);
}



/*
Write the current view to a file
The multiple fputc()s can be replaced with
fwrite(image,width*height*3,1,fptr);
If the memory pixel order is the same as the destination file format.
*/
int WindowDump(int width, int height)
{
	int i, j;
	FILE *fptr;
	static int counter = 0; /* This supports animation sequences */
	char fname[32];
	unsigned char *image;

	bool stereo = false;

	/* Allocate our buffer for the image */
	if ((image = (unsigned char *)malloc(4 * width*height*sizeof(char))) == NULL) 
	{
		fprintf(stderr, "Failed to allocate memory for image\n");
		return(FALSE);
	}

	glPixelStorei(GL_PACK_ALIGNMENT, 1);

	/* Open the file */
	sprintf_s(fname, 32, "demo_%05d.tga", counter);


	/* Copy the image into our buffer */
	glReadBuffer(GL_BACK_LEFT);
	glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, image);

	// Shift B and R
	for (int i = 0; i < width*height * 4; i += 4)
	{
		char R = image[i + 0];
		image[i + 0] = image[i + 2];
		image[i + 2] = R;
	}

	StoreTGAImageToFile(fname, width, height, image);

	/* Clean up */
	counter++;
	free(image);
	return(TRUE);
}

#endif // CAPTURE_TO_IMAGES
