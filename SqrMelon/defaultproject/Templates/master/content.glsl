// Change linear fog to something else
float FogRemap(float fog)
{
    return fog;
}

// Background color from ray and remapped fog distance
vec3 FogColor(Ray ray, float fog)
{
    return mix(vec3(1.0), vec3(0.2), smoothstep(-0.2, 0.2, ray.direction.y));
}

// Distance field describing the scene
float fField(vec3 p, out vec4 m)
{
    // declare 2 distance variables, add a floor & default material
    float ir, r = p.y + 0.5;
    m=vec4(p,0);

    ir = length(p - vec3(0.0, 0.0, 10.0)) - 0.5;
    fOpUnion(r,ir,m,vec4(p,1));

    return r;
}

// Material based on traced point, Normal, distance & materialId derived from fField above.
/*

struct Material
{
    vec3 albedo;                // surface color
    vec3 additive;              // add color after all shading has been done
    float specularity;          // ggx specular
    float roughness;            // ggx roughness
    float reflectivity;         // real reflections
    float blur;                 // blurry reflections
    float metallicity;          // colorize reflected specular and reflections by albedo
};
*/
Material GetMaterial(Hit hit)
{
    int objectId = int(hit.materialId.w);
    return Material(vec3(0.5), vec3(0.0), 0.0, 0.0, 0.0, 0.0, 0.0);
}

// Compute shaded pixel
vec3 Lighting(LightData data)
{
    vec3 result = vec3(0);

    result += DirectionalLight(data, vec3(0.5, 1.0, 1.0), vec3(1.0), shadowArgs());

    return result;
}

// Compute hit.normal, note it is vec3(0) at the start of this function
vec3 Normal(Hit hit)
{
    const vec2 e=vec2(EPSILON+EPSILON,0.0);
    vec3 point=hit.point;
    vec4 taps = vec4(fField(point+e.xyy),fField(point+e.yxy),fField(point+e.yyx),fField(point));
    return  normalize(taps.xyz-taps.w);
}
