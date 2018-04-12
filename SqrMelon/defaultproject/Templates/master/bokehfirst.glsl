void main()
{
vec2 a=gl_FragCoord.xy/uResolution;
float b=texture(uImages[0],a).w;
c=vec4(f(b,d(b),a,vec2(0,1)/uResolution),b);
}
