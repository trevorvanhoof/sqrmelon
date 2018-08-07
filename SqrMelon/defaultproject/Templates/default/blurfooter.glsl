<<<<<<< Updated upstream:SqrMelon/defaultproject/Templates/master/directionalblurrefl.glsl
#version 410

out vec4 c;

uniform vec2 uResolution;

uniform sampler2D uImages[1];
uniform vec2 uDirection;
uniform float uBlurSize;

const float e[7]=float[7](0.0205,.0855,.232,.324,.232,.0855,.0205);
uniform float g; // use input reflection roughness for blur kernel?
=======
const float e[7]=float[7](0.0205,.0855,.232,.324,.232,.0855,.0205);
>>>>>>> Stashed changes:SqrMelon/defaultproject/Templates/default/blurfooter.glsl

void main()
{
vec2 f=gl_FragCoord.xy/uResolution;
vec2 a=uDirection/uResolution*uBlurSize
#ifdef uUseAlpha
*texture(uImages[0],f).w
#endif
,b=f-a*3;
c=vec4(0);
for(int d=0;d<7;d++)
{
c+=texture(uImages[0],b)*e[d];
b+=a;
}
}
