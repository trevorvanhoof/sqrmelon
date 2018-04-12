#version 410
uniform sampler2D uImages[1];
out vec4 outColor0;
// Good & fast sRgb approximation from http://chilliant.blogspot.com.au/2012/08/srgb-approximations-for-hlsl.html
vec3 LinearToSRGB (vec3 rgb)
{
    rgb=max(rgb,vec3(0,0,0));
    return max(1.055*pow(rgb,vec3(0.416666667))-0.055,0.0);
}
void main()
{
    outColor0=vec4(LinearToSRGB(texelFetch(uImages[0],ivec2(gl_FragCoord.xy),0).xyz),1.0);
}
