#version 420

out vec4 color;

uniform vec2 uResolution;

uniform sampler2D uImages[8];
uniform float uBloom = 0.2;
uniform float uLensDirt = 0.3;

void main()
{
    vec2 coord = gl_FragCoord.xy / uResolution;
    color = texture(uImages[0], coord);

    vec3 b0 = texture(uImages[1], coord).xyz;
    vec3 b1 = texture(uImages[2], coord).xyz * 0.6; // dampen to have less bending in gamma space
    vec3 b2 = texture(uImages[3], coord).xyz * 0.3; // dampen to have less bending in gamma space
    vec3 b3 = texture(uImages[4], coord).xyz;
    vec3 b4 = texture(uImages[5], coord).xyz;
    vec3 b5 = texture(uImages[6], coord).xyz;

    vec3 bloom = b0 * 0.5
               + b1 * 0.6
               + b2 * 0.6
               + b3 * 0.45
               + b4 * 0.35
               + b5 * 0.23;

    bloom /= 2.2;
    color.xyz = mix(color.xyz, bloom.xyz, uBloom);

    vec3 lens = texture(uImages[7], coord).xyz;
    vec3 lensBloom = b0 + b1 * 0.8 + b2 * 0.6 + b3 * 0.45 + b4 * 0.35 + b5 * 0.23;
    lensBloom /= 3.2;
    color.xyz = mix(color.xyz, lensBloom, (clamp(lens * uLensDirt, 0.0, 1.0)));
}
