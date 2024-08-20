#version 410

out vec4 g;

uniform vec2 uResolution;

uniform sampler2D uImages[8];
uniform float uBloom = 0.08,
uLensDirt = 0.1;

void main()
{
    vec2 h = gl_FragCoord.xy / uResolution;
    g = texture(uImages[0], h);

    vec3 a = texture(uImages[1], h).xyz,
    b = texture(uImages[2], h).xyz * .6, // dampen to have less bending in gamma space
    c = texture(uImages[3], h).xyz * .3, // dampen to have less bending in gamma space
    d = texture(uImages[4], h).xyz,
    e = texture(uImages[5], h).xyz,
    f = texture(uImages[6], h).xyz;

    g.xyz = mix(g.xyz, (a * .5
               + b * .6
               + c * .6
               + d * .45
               + e * .35
               + f * .23) / 2.2, uBloom);

    g.xyz = mix(g.xyz, (a + b * .8 + c * .6 + d * .45 + e * .35 + f * .23) / 3.2, (clamp(texture(uImages[7], h).xyz * uLensDirt, 0, 1)));
}
