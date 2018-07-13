uniform float uSaturation = 1.0;
uniform float uLuminance = 1.0;
uniform float uOffset = 0.0;
uniform float uGamma = 1.0;

// Good & fast sRgb approximation from http://chilliant.blogspot.com.au/2012/08/srgb-approximations-for-hlsl.html
vec3 LinearToSRGB (vec3 rgb)
{
    rgb=max(rgb,vec3(0,0,0));
    return max(1.055*pow(rgb,vec3(0.416666667))-0.055,0.0);
}

void main()
{
    vec3 color = texelFetch(uImages[0],ivec2(gl_FragCoord.xy),0).xyz;
    color = pow(hsv2rgb( rgb2hsv(color) * vec3(1.0, uSaturation, uLuminance) + vec3(0.0, 0.0, uOffset) ), vec3(uGamma));
    outColor0=vec4(LinearToSRGB(color),1.0);
}
