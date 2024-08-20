void main()
{
    ivec2 uv=ivec2(gl_FragCoord.xy);
    outColor0=texelFetch(uImages[0],uv,0);
#ifdef REFL_FACTOR
    // fade out reflection by fog
    outColor0.xyz+=texture(uImages[1],(uv/uResolution)/REFL_FACTOR).xyz*(1-FogRemap(sat(outColor0.w/FAR)));
#endif
}
