// Ported from https://www.shadertoy.com/view/Xd3GDl
#version 420
uniform vec2 uResolution;
uniform sampler2D uImages[1];
uniform float uSeconds,uSharpDist,uSharpRange,uBlurFalloff,uMaxBlur;
out vec4 c;
float d(float a){return uMaxBlur*min(1,max(0,abs(a-uSharpDist)-uSharpRange)/uBlurFalloff);}
float e(vec2 a){a=fract(a*vec2(5.3987,5.4421));a+=dot(a.yx,a.xy+vec2(21.5351,14.3137));return fract(a.x*a.y*95.4307);}
vec3 f(float a,float b,vec2 g,vec2 h)
{
vec3 k=vec3(0);
for(int i=0;i<16;++i)
{
float r=(i+e(g+float(i+uSeconds))-.5)/15.-.5;
vec2 p=g+r*b*h;
vec4 j=texture(uImages[0],p);
if(j.w<a)
{
p=g+r*min(b,d(j.w))*h;
p=g+r*d(j.w)*h;
j=texture(uImages[0],p);
}
k+=j.xyz;
}
return max(k/16,0);
}
