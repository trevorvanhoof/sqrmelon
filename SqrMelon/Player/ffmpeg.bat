"ffmpeg.exe" -i "soundtrack.mp3" -framerate 60 -i "demo_%%05d.tga" -c:v libx264 -profile:v high -crf 20 -pix_fmt yuv420p -acodec copy -y "video.mp4"
pause