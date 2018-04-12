// Pass that forwards the texture by default, but allows injection of additional code before the post processing pipeline is hit.
// Notice that alpha is "intersection to camera distance", for depth of field. Return uSharpDist for pixels that should not be blurred.
void main()
{
    outColor0=texelFetch(uImages[0],ivec2(gl_FragCoord.xy),0);
}
