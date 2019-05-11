// This is a basic noise look up texture
// it has perlin noise with different zoom
// levels in every color channel.
void main()
{
    vec2 uv = gl_FragCoord.xy/uResolution;
    outColor0 = vec4(
        perlin(uv,  8.0, 7, 2.0, 0.5),
        perlin(uv, 16.0, 7, 2.0, 0.5),
        perlin(uv, 32.0, 7, 2.0, 0.5),
        perlin(uv, 64.0, 7, 2.0, 0.5)
    );
}
