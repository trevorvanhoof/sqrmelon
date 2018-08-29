#version 410

uniform sampler2D uImages[1];
uniform vec2 uResolution;

out vec4 outColor;

/*
// Vignette that can mix between a round and a square with rounded corners
// I'm not too happy with it really, it seems to just cut off the corners and not add a lot of depth
uniform float uVignette = 1.0;

const float VignetteAspect = 0.0;
const float VignetteRound = 0.0;
const float VignetteRadius = 0.66;
const float VignetteScale = 2.19;
const float VignettePow = 2.0;
const vec3 VignetteColor = vec3(0.0);

float fBoxRound(vec2 p, vec2 b)
{
    vec2 d = abs(p) - b;
    return length(max(d, 0)) + max(min(d.x, 0), min(d.y, 0));
}

vec3 Vignette(vec2 clipUv, vec3 col)
{
    float ar = mix(1.0, uResolution.y / uResolution.x, VignetteAspect);
    float w = uVignette * mix(
        fBoxRound(clipUv, VignetteRadius * vec2(ar, 1.0)),
        length(clipUv * vec2(ar, 1.0)) - VignetteRadius, VignetteRound) * VignetteScale;
    return mix(col, VignetteColor, pow(clamp(w, 0.0, 1.0), VignettePow));
}
*/

uniform float uChromaticAberrationRadius = 0.1;
const float ChromaticAberration = 1.0;
const int ChromaticAberrationSteps = 50;
const float ChromaticAberrationShape = 0.125;

// I mean, duh: https://www.shadertoy.com/view/MdsyDX
vec3 AberrationColor(float f)
{
    f = f * 3.0 - 1.5;
    return clamp(vec3(-f, 1.0 - abs(f), f), 0.0, 1.0);
}

vec3 ChromAb(vec2 uv, vec2 clipUv, vec3 col)
{
    vec3 chroma = vec3(0.0);
    vec3 w = vec3(0.001);
    vec2 dir = clipUv * pow(dot(clipUv, clipUv), ChromaticAberrationShape);

    for(int j = 1; j <= ChromaticAberrationSteps; ++j)
    {
        float t = float(j) / float(ChromaticAberrationSteps);
        float d = t * uChromaticAberrationRadius * 0.125;
        vec3 s = AberrationColor(t);
        w += s;
        chroma.xyz += texture(uImages[0], uv - dir * d).xyz * s;
    }

    return mix(col, chroma / w, ChromaticAberration);
}

void main()
{
    vec2 uv = gl_FragCoord.xy / uResolution;
    vec2 clipUv = uv * 2.0 - 1.0;
    outColor = texture(uImages[0], uv);
    outColor.xyz = ChromAb(uv, clipUv, outColor.xyz);
    // outColor.xyz = Vignette(clipUv, outColor.xyz);
}
