// This pass is applied before any other post effects like DoF and bloom. Add 2D, composite raytraced elements, etc.
// Notice that alpha is "intersection to camera distance", for depth of field. Return uSharpDist for pixels that should not be blurred.
uniform float uGodRays = 0.3;
uniform vec3 uGodRayDir = vec3(0.0, 1.0, 0.0);

vec2 lightSS()
{
    // Compute the light position in screen space
    vec3 frustumSpaceLightDir = normalize(mat3(uV) * -uGodRayDir);
    return frustumSpaceLightDir.xy / uFrustum[0].xy;
}

void main()
{
    outColor0 = texelFetch(uImages[0], ivec2(gl_FragCoord.xy),0);
    float depth = outColor0.w;
    if(uGodRays==0.0)
    {
        return;
    }
    // God rays
    const int SAMPLES = 32;

    vec2 uv = gl_FragCoord.xy / uResolution;
    float decay = 0.75; // Falloff, as we radiate outwards.
    vec2 l = lightSS(); // Light origin.

    vec2 tuv =  uv - 0.5 - l.xy * 0.45;
    vec2 dTuv = (tuv * uGodRays / SAMPLES) * sat(dot(normalize(uGodRayDir), uV[2].xyz)*4+2);

    float totalWeight =  1.0;

    // Jittering, to get rid of banding.
    // Vitally important when accumulating discontinuous samples,
    // especially when only a few layers are being used.
    uv += dTuv * (h1(gl_FragCoord.xy + uSeconds) - 0.5);
    float weight = 1.0;
    float b = sat(outColor0.w / FAR);
    for(int i = 0; i < SAMPLES; ++i)
    {
        uv -= dTuv;
        // radial blur tap
        vec4 s = texture(uImages[0], uv);
        s.xyz = hsv2rgb(sat(rgb2hsv(s.xyz)-vec3(0,0,6)));
        // bias based on volume of space we're traveling through, closer objects get less radial blur influence
        float w = weight * b;
        // accumulate samples
        outColor0.xyz += s.xyz * w;
        totalWeight += w;
        // propagate falloff
        weight *= decay;
    }
    // normalize outputs
    outColor0.xyz /= totalWeight;

    // Any scene-specific overlay
    PreFxOverlay(outColor0);
}
