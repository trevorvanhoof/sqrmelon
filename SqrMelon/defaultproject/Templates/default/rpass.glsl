
// reflection pass is a little special, it writes to a full screen pass because the tool can't dynamically edit buffer sizes
// so this way we can have a setting for "reflection quality" in the shader code & discard unused fragments, it's still quite cheap

void main()
{
    outColor0=vec4(0);
    #ifdef REFL_FACTOR
    // discard pixels outside the reflection buffer range
    ivec2 fc=ivec2(gl_FragCoord.xy);
    if(fc.x>=uResolution.x/REFL_FACTOR||fc.y>=uResolution.y/REFL_FACTOR)
        return;
    vec4 specularColor_roughness=texelFetch(uImages[2],fc*REFL_FACTOR,0);
    // discard non reflective pixels
    if(vmax(specularColor_roughness)==0.0)
        return;
    Ray ray=ScreenRayUV(gl_FragCoord.xy/(uResolution/REFL_FACTOR));
    vec4 gbuf=texelFetch(uImages[1],fc*REFL_FACTOR,0);
    // extract packed normal
    int n=floatBitsToInt(gbuf.w);
    // XY component
    vec2 nc=sat(vec2(n&32767,(n>>15)&32767)/16383.5-1);
    // Z component
    vec3 normal=normalize(vec3(nc,sqrt(1.0-dot(nc,nc))*((n>>30)==1?-1:1)));
    ray=Ray(gbuf.xyz,reflect(ray.direction,normal));
    TraceAndShade(ray,REFL_NEAR,REFL_FAR,REFL_STEPS);
    // forward specular color and roughness
    outColor0.xyz *= specularColor_roughness.xyz;
    outColor0.w = specularColor_roughness.w;
    #endif
}
