/*
This distance field is used in fField and Lighting to add fake emissive shapes.
The material "out vec4 m" should be the RGB color and "-1" to indicate emissiveness.
*/
float fEmissive(vec3 p, out vec4 m)
{
    m = vec4(0, 0, 0, -1);
    return FAR;
}
float fEmissive(vec3 p) { vec4 m; return fEmissive(p, m); }

/*
Signed distance field, place to do 3D scene modeling.
*/
float fField(vec3 p, out vec4 m)
{
    vec4 im;
    vec3 op=p;
    float ir, r = fEmissive(p, m);

    ir = fBoxRound(p, vec3(0.5)) - 0.15;
    fOpUnion(r,ir,m,vec4(p,1));

    return r;
}

/*
Returns the color in the distance.
You can use ray direction to composite sky gradients and sun discs.
*/
vec3 FogColor(Ray ray, float fog)
{
    return mix(vec3(1.0), vec3(0.1, 0.2, 1.0), smoothstep(-1.0, 0.2, ray.direction.y)) * sat(1.1-ray.direction.y);
}

/*
Returns a Material struct with the following info:
vec3 albedo
vec3 additive
float specularity
float roughness
float reflectivity
float blur
float metallicity
*/
Material GetMaterial(Hit hit, Ray ray)
{
    int objectId = int(hit.materialId.w);
    if(objectId==-1) // emissive material
        return Material(vec3(0.0), vec3(hit.materialId.xyz), 0.0, 0.0, 0.0, 0.0, 0.0);
    // tri planar project
    vec2 uv = projectTri(hit.point, hit.normal);
    // noise texture sample
    vec4 noiseSample = texture(uImages[0], uv);
    // have fun with the noise to generate some emissive blobs
    vec3 emissive = vec3(1.0, 0.0, 1.0) * smoothstep(0.75, 0.85, noiseSample.x);
    emissive += vec3(0.0, 1.0, 1.0) * smoothstep(0.25, 0.15, noiseSample.x);
    noiseSample.x = quad(1.0 - abs(noiseSample.x - 0.5) * 2.0);
    return Material(noiseSample.xxx, emissive, 0.5, 0.1, 0.0, 0.0, 0.0);
}

/*
Lighting & shading is done here, after all material and ray intersection data have been collected.
These are the currently implemented lighting functions:

vec3 AmbientLight(LightData data, vec3 color)
vec3 RimLight(LightData data, vec3 color, float power)
vec3 DirectionalLight(LightData data, vec3 direction, vec3 color)
vec3 DirectionalLight(LightData data, vec3 direction, vec3 color, ShadowArgs shadow)
vec3 PointLight(LightData data, vec3 point, vec3 color)
vec3 PointLight(LightData data, vec3 point, vec3 color, float lightRadius)
vec3 PointLight(LightData data, vec3 point, vec3 color, float lightRadius, ShadowArgs shadow)

ShadowArgs control the shadow ray settings, when no ShadowArgs are provided no shadow ray is traced.
For reasonable quality default shaodws you can use the shadowArgs() helper function. Else
you may manually provide these settings:

ShadowArgs(float near, float far, float hardness, int steps)

The final notable feature is "IMPL_EMISSIVE_LIGHT" which edits the result and
requires a distance field function of the form fEmissive(vec3 point, vec4 color)
where color.w is ignored.
*/
vec3 Lighting(LightData data)
{
    vec3 result = vec3(0);
    result += DirectionalLight(data, vec3(0.5, 1.0, 1.0), vec3(1.0), shadowArgs());

    // Emissive light
    IMPL_EMISSIVE_LIGHT(result, fEmissive);

    return result;
}

/*
Bump mapping function, it is entirely optional so for the sake of template usability
it returns immediately, with the extra example code there but not doing anything
*/
float fBump(Hit hit, vec3 offset)
{
    // First we get original distance
    // note that the offset vector is important here!
    float result = fField(hit.point + offset);
    return result;

    // tri planar project, note the offset
    vec2 uv = projectTri(hit.point + offset, hit.normal);
    // noise texture sample
    vec4 noiseSample = texture(uImages[0], uv * 10.0);
    // add to result & return
    result += noiseSample.x * 0.01;
    return result;
}

/*
The Normal function implements the fBump function above, and edits the given hit data.
It's up to you to remove bump mapping, add normal mapping, or do other Normal related things.
*/
void Normal(inout Hit hit)
{
    const vec2 e=vec2(EPSILON+EPSILON,0.0);
    vec3 point=hit.point;
    vec4 taps = vec4(fField(point+e.xyy),fField(point+e.yxy),fField(point+e.yyx),fField(point));
    hit.normal = normalize(taps.xyz-taps.w);

    // begin bump mapping
    vec4 bump = vec4(fBump(hit,e.xyy),fBump(hit,e.yxy),fBump(hit,e.yyx),fBump(hit,vec3(0)));
    hit.normal = normalize(bump.xyz-bump.w);
    // end bump mapping
}
