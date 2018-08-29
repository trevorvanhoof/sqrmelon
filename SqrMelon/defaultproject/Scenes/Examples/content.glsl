// Background color from ray and remapped fog distance
vec3 FogColor(Ray ray, float fog)
{
    return mix(vec3(1.0), vec3(0.2), smoothstep(-0.2, 0.2, ray.direction.y));
}

// Distance field describing the scene
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

// Material based on traced point, normal, distance & materialId derived from fField above.
Material GetMaterial(Hit hit)
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

// Compute shaded pixel
vec3 Lighting(LightData data)
{
    vec3 result = vec3(0);

    result += DirectionalLight(data, vec3(0.5, 1.0, 1.0), vec3(1.0), shadowArgs());

    result += DirectionalLight(data, vec3(1.0,-1.0,1.0), vec3(0.6, 0.5, 0.2));

    result += DirectionalLight(data, vec3(-1.0), vec3(0.1, 0.3, 0.5));

    return result;
}

// Compute hit.normal, note it is vec3(0) at the start of this function
float Bump(vec3,Hit); // part of bump mapping example in Normal function below
vec3 Normal(Hit hit)
{
    const vec2 e=vec2(EPSILON+EPSILON,0.0);
    vec3 point=hit.point;
    vec4 taps = vec4(fField(point+e.xyy),fField(point+e.yxy),fField(point+e.yyx),fField(point));
    hit.normal = normalize(taps.xyz-taps.w); // store inside hit.normal so Bump function does not need additional arguments

    // it is possible to change the result of fField for bump mapping
    // in this example I first compute a regular normal to use as mask and only bump map horizontal surfaces
    taps.x += Bump(e.xyy, hit);
    taps.y += Bump(e.yxy, hit);
    taps.z += Bump(e.yyx, hit);
    taps.w += Bump(vec3(0), hit);

    return normalize(taps.xyz-taps.w);
}

float Bump(vec3 offset, Hit hit)
{
    // Important to offset whatever we derive UVs from!
    vec2 uv = hit.point.xz + offset.xz;

    // the hit.materialId can be used to not bump all objects the same
    int objectId = int(hit.materialId.w);
    if(objectId%2==1)
        return 0.;

    // enhance the checkers pattern by introducing bumped tiles
    // scale uvs to match material
    vec2 cells = abs(fract(uv * 0.5 + 0.5) - 0.5);
    float bump = -smoothstep(0.0, 0.01, vmin(cells)) * 0.02;
    // we can even randomly tilt each tile
    vec2 tilt = fract(uv * 0.5) * (h2(floor(uv * 0.5)) - 0.5);
    bump += (tilt.x + tilt.y) * 0.4;
    // mask result by original normal
    return smoothstep(0.6, 0.7, hit.normal.y) * bump;
}