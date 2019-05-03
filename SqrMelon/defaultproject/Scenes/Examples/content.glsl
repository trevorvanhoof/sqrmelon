/*
Signed distance field, place to do 3D scene modeling.
*/
float fField(vec3 p, out vec4 m)
{
    // declare 2 distance variables, add a floor & default material
    float ir, r = p.y;
    m=vec4(p,0);

    // back up the point before modification
    vec3 p1 = p;

    // put a bunch of shapes on the X axis with unique material IDs

    // infinite tube
    ir = fTube(p.xz, 0.25);
    fOpUnion(r,ir,m,vec4(p,1));
    p.x += 1.0;

    // ball
    ir = fSphere(p-vec3(0,0.25,0), 0.25);
    fOpUnion(r,ir,m,vec4(p,2));
    p.x += 1.0;

    // cheap inifnite box
    ir = fBox(p.xz,vec2(0.25));
    fOpUnion(r,ir,m,vec4(p,3));
    p.x += 1.0;

    // cheap box
    ir = fBox(p-vec3(0,0.5,0),vec3(0.25));
    fOpUnion(r,ir,m,vec4(p,4));
    p.x += 1.0;

    // cheap octahedron
    ir = fDiamond(p-vec3(0,0.5,0),0.25);
    fOpUnion(r,ir,m,vec4(p,5));
    p.x += 1.0;

    // box with beveled edge
    ir = fBoxChamfer(p-vec3(0,0.5,0),vec3(0.15))-0.1;
    fOpUnion(r,ir,m,vec4(p,6));
    p.x += 1.0;

    // (accurate) box with round edge
    ir = fBoxRound(p-vec3(0,0.5,0),vec3(0.15))-0.1;
    fOpUnion(r,ir,m,vec4(p,7));
    p.x += 1.0;

    // torus
    ir = fTorus(p-vec3(0,0.5,0),0.1,0.25);
    fOpUnion(r,ir,m,vec4(p,8));
    p.x += 1.0;

    // square torus, see source to see it is a box wrapped around a torus, it could be any other shape as well!
    ir = fSquareTorus((p-vec3(0,0.5,0)).xzy,vec2(0.1,0.05),0.25);
    fOpUnion(r,ir,m,vec4(p,9));
    p.x += 1.0;

    // cylinder with flat caps
    ir = fCylinder(p-vec3(0,0.5,0),0.25,0.5);
    fOpUnion(r,ir,m,vec4(p,10));
    p.x += 1.0;

    // cylinder with round caps
    ir = fCapsule(p-vec3(0,0.5,0),0.25,0.5);
    fOpUnion(r,ir,m,vec4(p,11));
    p.x += 1.0;

    // hexagon 2D converted to hollow triangular pipe
    ir = fHexagon(p.xz,0.75);
    ir = abs(ir) - 0.01; // abs the result and give it thickness to create a pipe
    ir=max(ir,fSlab(p.y-1.0,0.25)); // intersect a slab to see inside
    fOpUnion(r,ir,m,vec4(p,12));
    p.x += 1.0;

    // demonstrate pModMirror, as it is most obvious with the triangle
    pModMirror(p.z, 1.0);
    // triangle 2D converted to hollwo triangular pipe
    ir = fTriangle(p.xz,0.75);
    ir = abs(ir) - 0.01; // abs the result and give it thickness to create a pipe
    ir=max(ir,p.y-1.0); // cut off the top to see inside
    fOpUnion(r,ir,m,vec4(p,13));
    p.x += 1.0;

    // demonstrate pModPolarMirror
    p = p1; // restore the point
    p -= 4.0;
    float cell = pModPolarMirror(p.xy, 8.0);
    p.x -= 4.0;
    p.y += 0.5;
    ir = length(p) - 1.0;
    fOpUnion(r,ir,m,vec4(p,14));

    // demonstrate random sizes
    p = p1; // restore the point
    p -= vec3(4.0, 4.0, -4.0);
    cell = pModPolar(p.xy, 8.0);
    p.x -= 4.0;
    ir = length(p) - snoise(uBeats + h1(cell) * 8.0);
    fOpUnion(r,ir,m,vec4(p,15));

    // demonstrate a space mod and a 2D shape (concept behind on fSquareTorus)
    p = p1; // restore the point
    p -= vec3(4.0, 4.0, 8.0);
    // calculate 2D uv around 3D tube
    vec2 uv = vec2(length(p.xy) - 3.0, p.z);
    // calculate complex 2D SDF
    pModPolar(uv, 5.0);
    ir = uv.x - 0.2;
    fOpUnion(r,ir,m,vec4(p,16));

    return r;
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
    int objectId = int(hit.materialId.w);

    if(objectId == 0) // checkboard floor
    {
        vec2 cells = floor(fract(hit.materialId.xz * 0.25) * 2.0);
        bool checker = cells.x == cells.y;
        return Material(vec3(checker ? 0.8 : 0.2), vec3(0.0), checker ? 0.1 : 0.2, checker ? 0.02 : 0.2, 0.0, 0.0, 0.0);
    }

    if(objectId == 13) // emissive triangles
    {
        float w = 1.0 - fract(uBeats);
        w *= smoothstep(1.1, 1.0, w * 1.1);
        float emissive = quad(w) * step(0.75,fract(floor(hit.point.z + 0.5 + floor(uBeats))*0.25));
        emissive *= pow(3.0, 8.0 * fract(floor(hit.point.z * 0.25 + 0.125)*0.25));
        return Material(vec3(0.0), vec3(1.0, 2.0, 3.0) * emissive, 0.0, 0.0, 0.0, 0.0, 0.0);
    }

    // default random hue per object
    return Material(hsv2rgb(h1(objectId), 1.0, 1.0), vec3(0.0), 0.0, 0.0, 0.0, 0.0, 0.0);
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

    result += DirectionalLight(data, vec3(1.0,-1.0,1.0), vec3(0.6, 0.5, 0.2));

    result += DirectionalLight(data, vec3(-1.0), vec3(0.1, 0.3, 0.5));

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

    // The hit.materialId can be used to not bump all objects the same
    int objectId = int(hit.materialId.w);
    if(objectId%2==1)
        return result;

    // Important to offset whatever we derive UVs from!
    vec2 uv = hit.point.xz + offset.xz;

    // enhance the checkers pattern by introducing bumped tiles
    // scale uvs to match material
    vec2 cells = abs(fract(uv * 0.5 + 0.5) - 0.5);
    float bump = -smoothstep(0.0, 0.01, vmin(cells)) * 0.02;
    // we can even randomly tilt each tile
    vec2 tilt = fract(uv * 0.5) * (h2(floor(uv * 0.5)) - 0.5);
    bump += (tilt.x + tilt.y) * 0.4;
    // mask result by original normal
    result += smoothstep(0.6, 0.7, hit.normal.y) * bump;
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
    return mix(vec3(1.0), vec3(0.2), smoothstep(-0.2, 0.2, ray.direction.y));
}
