out vec4 outColor1;
out vec4 outColor2;

void main()
{
    Ray ray=ScreenRay();
    float near=texelFetch(uImages[0],ivec2(gl_FragCoord.xy/8),0).x;
    LightData data=TraceAndShade(ray,near,FAR,STEPS);

    // store hit point & normal in world space
    // pack normal into 32 bits:
    // unused bit, sign bit, 15-bit Y, 15-bit X
    // since normals are in range -1 to 1 we can map to fixed 15-bit range
    ivec2 xy=ivec2(data.hit.normal.xy*16383.5+16383.5)&32767;
    int z=sign(data.hit.normal.z)<0?1<<30:0;
    outColor1=vec4(data.hit.point,intBitsToFloat(z|xy.y<<15|xy.x));

    // specular color (after baking reflectivity & metallicity) & roughness output
    outColor2 = vec4(mix(vec3(1), data.material.albedo, data.material.metallicity) * data.material.reflectivity, data.material.blur);
}
