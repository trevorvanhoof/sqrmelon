#version 420
uniform vec2 uResolution;
uniform sampler2D uImages[1];
out vec4 outColor0;
void main()
{
    outColor0 = 0.25 * (
     + texelFetch(uImages[0], ivec2(gl_FragCoord.xy * 2), 0)
     + texelFetch(uImages[0], ivec2(gl_FragCoord.xy * 2) + ivec2(1, 0), 0)
     + texelFetch(uImages[0], ivec2(gl_FragCoord.xy * 2) + ivec2(0, 1), 0)
     + texelFetch(uImages[0], ivec2(gl_FragCoord.xy * 2) + ivec2(1, 1), 0)
    );
}
