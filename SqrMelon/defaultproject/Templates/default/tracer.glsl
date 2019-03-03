// Main sphere tracing function, taking ideas from:
// http://erleuchtet.org/~cupe/permanent/enhanced_sphere_tracing.pdf
Hit Trace(Ray ray, float near, float far, int steps)
{
    // Compute pixel radius for cone trace
    float pixelRadius = uFrustum[2].y / uResolution.y * 0.5;

    vec4 materialId; // track material metadata of nearest point
    float fudge = 1.6; // over-relaxation to accelerate steps

    /* http://erleuchtet.org/~cupe/permanent/enhanced_sphere_tracing.pdf */
    float t = near;
    float previousRadius = 0.0;
    float stepLength = 0.0;

    for (int i = 0; i < steps; i++)
    {
        float signedRadius = fField(ray.origin + ray.direction * t, materialId) - t * pixelRadius;
        float radius = abs(signedRadius);

        bool sorFail = fudge > 1.0 && (radius + previousRadius) < stepLength;
        if (sorFail)
        {
            stepLength -= fudge * stepLength;
            fudge = 1.0;
        }
        else
            stepLength = signedRadius * fudge;

        previousRadius = radius;

        if (!sorFail && radius < t * pixelRadius || t > far)
            break;

        t += stepLength;
    }

    bool hit = t <= far;
    if(!hit)
        return Hit(far, vec3(0), vec3(0), vec4(0));

    return Hit(t, ray.origin + ray.direction * t, vec3(0.0), materialId);
}

float DoAO(Hit hit)
{
    float ao = 1.0;

    // Ambient occlusion
    #ifdef AO_WEIGHT
    const int AO_TAPS = 5;
    const float AO_DISTANCES[AO_TAPS] = float[](0.05, 0.2, 0.5, 1.5, 3.0);
    const float AO_WEIGHTS[AO_TAPS] = float[](1.0, 0.5, 0.3, 0.2, 0.1);
    for(int i = 0; i < AO_TAPS; ++i)
    {
        float d = AO_DISTANCES[i] * AO_RADIUS;
        float tap = sat(fField(hit.point + hit.normal * d) / d);
        ao *= mix(1.0, tap, AO_WEIGHTS[i] * AO_WEIGHT);
    }
    #endif

    return ao;
}

vec3 TraceAndShadeRefraction(Ray ray, float near, float far, int steps)
{
    Hit hit=Trace(ray, near, far, steps);

    // Get fog
    float fog = sat(FogRemap(sat(hit.totalDistance/FAR)));
    vec3 color = FogColor(ray, fog);

    // Fully occluded, stop further computation
    if(fog<1)
    {
        hit.normal = Normal(hit);
        Material material = GetMaterial(hit,ray);
        float ao = DoAO(hit);
        LightData data = LightData(ray, hit, material);
        color = mix(ao * Lighting(data) + material.additive, color, fog);
    }

    return color;
}

// TraceAndShade returns the light data to be used in the g buffers.
LightData TraceAndShade(Ray ray, float near, float far, int steps)
{
    Hit hit=Trace(ray, near, far, steps);

    // Get fog
    float fog = sat(FogRemap(sat(hit.totalDistance/FAR)));
    outColor0 = vec4(FogColor(ray, fog), hit.totalDistance);

    // Fully occluded, stop further computation
    if(fog==1)
    {
        return LightData(ray, hit, Material(vec3(0), vec3(0), 0, 0, 0, 0, 0));
    }

    // Compute normal
    hit.normal = Normal(hit);

    // Compute material
    Material material = GetMaterial(hit, ray);

    // Ambient occlusion
    float ao = DoAO(hit);

    // Compute lighting & output shaded pixel
    LightData data = LightData(ray, hit, material);
    outColor0 = mix(vec4(ao * Lighting(data) + material.additive, hit.totalDistance), outColor0, fog);

    // Return data for gbuffer creation in the main pass
    return data;
}
