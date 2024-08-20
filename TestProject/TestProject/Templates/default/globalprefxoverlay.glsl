void main()
{
    outColor0 = texelFetch(uImages[0], ivec2(gl_FragCoord.xy),0);
    // Any scene-specific overlay
    PreFxOverlay(outColor0);
}
