/*
This distance field is used in fField and Lighting to add fake emissive shapes.
The material "out vec4 m" should be the RGB color and "-1" to indicate emissiveness.
*/
float fEmissive(vec3 point, out vec4 materialId)
{
    materialId = vec4(0, 0, 0, -1);
    return FAR;
}
float fEmissive(vec3 point) { vec4 materialId; return fEmissive(point, materialId); }

/*
Signed distance field, place to do 3D scene modeling.
The materialId can contain extra information, such as
texture coordinates and other magic numbers to choose
materials and colors in GetMaterial().

By convention I use the 4th component of materialId
to tell objects apart.

For reference of what exists, see header.glsl
noiselib.glsl, sdf.glsl in Templates/defeault.
It lists some uniforms, utilities and
all available noise and distance field functions.
*/
float fField(vec3 point, out vec4 materialId)
{
    // Back up the point, so if we modify it for a specific model we can easily reset for the next shape.
    vec3 originalPoint = point;

    // Declare some variable & call emissive function
    vec4 tempMaterialId;
    float tempResult, result = fEmissive(point, materialId);

    // Create a new shape, in this case floor
    tempResult = point.y;
    tempMaterialId = vec4(point, 0);
    // Merge the floor with the rest of the scene
    fOpUnion(result, tempResult, materialId, tempMaterialId);

    // Create a box shape
    point -= vec3(-4.0, 1.0, 0.0);
    tempResult = fBox(point, vec3(1.0));
    tempMaterialId = vec4(point, 1); // Note that this shape has a different materialId
    // Merge the floor with the rest of the scene
    fOpUnion(result, tempResult, materialId, tempMaterialId);

    // Restore the point in case it was modified for the previous shape
    point = originalPoint;

    // Create a sphere
    point -= vec3(0.0, 1.0, 0.0);
    tempResult = fSphere(point, 1.0);
    tempMaterialId = vec4(point, 2); // Again another material Id
    // Merge the floor with the rest of the scene
    fOpUnion(result, tempResult, materialId, tempMaterialId);

    // Restore the point in case it was modified for the previous shape
    point = originalPoint;

    // Create a torus
    point -= vec3(4.0, 1.0, 0.0);
    // This trick flips the up axis so that the torus is flat.
    point = point.xzy;
    // pR rotates a shape around an axis, using X axis here
    pR(point.yz, 0.5);
    tempResult = fTorus(point, 0.2, 1.0);
    tempMaterialId = vec4(point, 3); // Again another material Id
    // Merge the floor with the rest of the scene
    fOpUnion(result, tempResult, materialId, tempMaterialId);

    // Restore the point in case it was modified for the previous shape
    point = originalPoint;

    return result;
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

Ray has the following members:
vec3 origin
vec3 direction

Hit has the following members:
float totalDistance;
vec3 point
vec3 normal
vec4 materialId
*/
Material GetMaterial(Hit hit, Ray ray)
{
    // By convention I always use the 4th component in the materialId (in fField) to tell apart objects
    int objectId = int(hit.materialId.w);

    // The result material is black and non-specular by default
    // each object will override it's own components.
    Material result = Material(vec3(0.0), vec3(0.0), 0.0, 0.0, 0.0, 0.0, 0.0);

    // By convention I always use -1 for emissive shapes
    if(objectId == -1)
    {
        // Emissive color
        result.additive = hit.materialId.xyz;
    }

    // The floor material, an example of a texture lookup
    if(objectId == 0)
    {
        // uImages[3] is the first user-defined texture
        // in our case a perlin noise.
        // Note the nice .xxx trick to get 1 channel as a vec4
        // multiplying the texture look up coordinate scales the texture
        result.albedo = texture(uImages[3], hit.point.xz * 0.5).xxx;
        // we can multiply to tint the albedo
        result.albedo *= vec3(1.0, 0.5, 0.0);
    }

    // The box material, using tri-planar projection
    // See the fBump function (far) below to learn why the cube
    // has a noise heightmap applied to it.
    if(objectId == 1)
    {
        // Tri-planar projection maps the texture
        // so that it matches up correctly on our 3D shape
        result.albedo = textureTri(uImages[3], hit.point, hit.normal).yyy;
        // This next version is cheaper, because it uses only 1 texture look up instead of 3
        // by first doing the projection to a vec2, and then doing a normal 2D texture lookup.
        // It does not handle round edges properly, so the above version is better for spheres.
        // vec2 uv = projectTri(hit.point, hit.normal);
        // result.albedo = texture(uImages[3], uv).yyy;
    }

    // The sphere material, 100% reflective
    if(objectId == 2)
    {
        // specularity mixes from albedo to specular highlight
        result.specularity = 1.0;
        // roughness must always be > 0 to see a visible specular highlight
        result.roughness = 0.03;
        // reflectivity adds reflection to the material
        // should technically always match specularity but
        // it's separate for more control
        result.reflectivity = 1.0;
        // We can blur reflections, especially necessary for low resolution reflections
        // reflection resolution is controlled in settings.glsl, per-scene. See REFL_FACTOR.
        // result.blur = 1.0;
    }

    if(objectId == 3)
    {
        // Create 2 new materials, copy the result for start
        Material green = result;
        Material red = result;
        // Actually colorize
        green.albedo = vec3(0.4, 1.0, 0.4);
        red.albedo = vec3(1.0, 0.4, 0.4);

        // Some nice texturing tricks
        // let's make the green material striped
        green.albedo *= step(0.5, fract((hit.materialId.y + hit.materialId.z) * 5.0));
        // let's make the red material a checkerboard
        // divide the space into cells
        ivec2 cells = ivec2(hit.materialId.xy * 8.0) % 2;
        // based on the cells select a mixing weight
        float weight = 1.0;
        if(cells.x != cells.y)
            weight = 0.0;
        // fade the current albedo to a different color
        red.albedo = mix(red.albedo, vec3(0.1, 0.05, 0.2), weight);

        // Mix the materials based on the intersection point,
        // hit.materialId.xyz contains the intersection local to the shape.
        // Note that that is only the case because we manually did in fField
        float fade = smoothstep(-0.2, 0.2, hit.materialId.x);
        result = MixMaterial(green, red, fade);
    }

    return result;
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
For reasonable quality default shadows you can use the shadowArgs() (LOWER CASE s) helper function. Else
you may manually provide these settings in ShadowArgs (UPPER CASE S):

ShadowArgs(float near, float far, float hardness, int steps)

The final notable feature is "IMPL_EMISSIVE_LIGHT" which edits the result and
requires a distance field function of the form fEmissive(vec3 point, vec4 color)
where color.w is ignored.
*/
vec3 Lighting(LightData data)
{
    vec3 result = vec3(0);

    // Sun light
    result += DirectionalLight(data, vec3(0.5, 1.0, -1.0), vec3(1.0, 0.8, 0.5), shadowArgs());
    // version without shadows
    // result += DirectionalLight(data, vec3(0.5, 1.0, -1.0), vec3(1.0, 0.8, 0.5));

    // Point light
    // result += PointLight(data, vec3(-5.0, 3.0, 0.0), vec3(100.0, 10.0, 50.0), 1.0, shadowArgs());

    // Ambient light to brighten up those black regions
    // result += AmbientLight(data, vec3(0.01, 0.02, 0.04));

    // Rim light highlights the edge of the shape
    // result += RimLight(data, vec3(0.2, 0.5, 1.0) * 10.0, 16.0);

    // Emissive light
    IMPL_EMISSIVE_LIGHT(result, fEmissive);

    return result;
}

/*
Bump mapping function, it is entirely optional so for the sake of template usability
it returns immediately, with the extra example code there but not doing anything.

Generally returns a world space distance from hit.point + offset (often using fField)
with additional detail added to it.

Hit has the following members:
float totalDistance;
vec3 point
vec3 normal
vec4 materialId
*/
float fBump(Hit hit, vec3 offset)
{
    // First we get original distance
    // note that the offset vector is important here!
    float result = fField(hit.point + offset);

    // Get the object ID, just as in GetMaterial()
    int objectId = int(hit.materialId.w);

    if(objectId == 1)
    {
        // Bump map only the box
        // Using tri-planar projection so we can use a 2D noise function
        vec2 uv = projectTri(hit.point + offset, hit.normal);
        // This is using procedural noise
        result += perlin(uv * 8.0, 7, 2.0, 0.5) * 0.1;
        // This is a version using a texture lookup
        // result += texture(uImages[3], uv).x * 0.1;
    }

    // This is a way to generate your own texture coordinate
    // and add the offset accordingly. If you forget the offset,
    // the bump will not work.
    // vec2 uv = hit.materialId.xz + offset.xz;
    // result += texture(uImages[3], uv).x;

    return result;
}

/*
The Normal function implements the fBump function above, and edits the given hit data.
It's up to you to remove bump mapping, add normal mapping, or do other Normal related things.
*/
void Normal(inout Hit hit)
{
    const vec2 e = vec2(EPSILON+EPSILON,0.0);
    vec3 point = hit.point;
    vec4 taps = vec4(fField(point+e.xyy),fField(point+e.yxy),fField(point+e.yyx),fField(point));
    hit.normal = normalize(taps.xyz-taps.w);

    // begin bump mapping
    vec4 bump = vec4(fBump(hit,e.xyy),fBump(hit,e.yxy),fBump(hit,e.yyx),fBump(hit,vec3(0)));
    hit.normal = normalize(bump.xyz-bump.w);
    // end bump mapping
}

/*
Returns the color in the distance. Fog is the current fog amount, it can be used
to only render additional details at a certain distance (like sun disk and clouds)
to avoid those details from bleeding through objects.

You can use ray direction to composite sky gradients and sun discs.

Ray has the following members:
vec3 origin
vec3 direction
*/
vec3 FogColor(Ray ray, float fog)
{
    // In settings.glsl changing the FAR plane
    // changes the fog as well, it is always
    // stretched out between the camera and the far plane

    // In fogremap.glsl we can change the fog response

    // Mix white with blue to get a brighter horizon, and clear blue sky.
    float horizonGradient = smoothstep(-1.0, 0.2, ray.direction.y);
    vec3 skyGradient = mix(vec3(1.0), vec3(0.1, 0.2, 1.0), horizonGradient);

    // Multiply the result with a gradient to darken the sky directly above.
    float topOfSkyGradient = sat(1.1 - ray.direction.y);
    skyGradient *= topOfSkyGradient;

    // Sun example!
    /*
    // The sun direction should technically match the directional light, but I like to cheat
    vec3 sunDirection = normalize(vec3(0.0, 0.1, 1.0));
    // We dot product to get a gradient originating from the sun across the sky sphere
    float sunGradient = dot(ray.direction, sunDirection);
    // We smoothstep that value to remap it to a very samll disc in the sky towards the sunDirection
    float sunDisc = smoothstep(0.999, 1.0, sunGradient);
    // The sun should not fade in with the rest of the fog,
    // we don't want a foggy area to draw the sun 50% faded-in on top of other objects
    // so for that we use the "fog" amount and step it, so only when almost 100% foggy
    // the sun actually kicks in
    sunDisc *= step(0.99, fog);
    // Finally we add it with an arbitrary brightness, to kickstart the bloom
    skyGradient += sunDisc * vec3(100.0);

    // With different smooth step values we can get a big halo
    // simulating a hazy day. Here I see that as part of the fog
    // so I don't do the step(0.99, fog) trick.
    skyGradient += vec3(0.15) * smoothstep(0.99, 1.0, sunGradient);
    skyGradient += vec3(0.1) * smoothstep(0.9, 1.0, sunGradient);
    skyGradient += vec3(0.05) * smoothstep(0.5, 1.0, sunGradient);
    */

    return skyGradient;
}
