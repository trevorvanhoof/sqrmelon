void main()
{
vec2 a=gl_FragCoord.xy/uResolution;
float b=texelFetch(uImages[0],ivec2(gl_FragCoord.xy),0).w;
c=vec4(min(f(b,d(b),a,vec2(.866,.5)/uResolution),f(b,d(b),a,vec2(-.866,.5)/uResolution)),b);
}
