/// Place to put sdfs and materials shared between scenes ///
/* 
hint: to improve compile times, enclose shared functions between #ifdefs and add #defines to settings.glsl for each scene that requires these functions

ex:

#ifdef REQUIRE_GREEBLES
float fComplexGreeble(vec3 p, float moduleHeight, float moduleChance)
{
    vec2 cell = pMod(p.xz, vec2(2.0));
    vec4 rand = h4(cell);

    // minimum distance cell contents are away from edge
    const float padding = 0.2;
    float result = 1.0 - vmax(abs(p.xz)) + padding, cellBoundary = result;

    if(moduleChance > (rand.x + rand.y + rand.z + rand.w) * 0.25)
    {
        float cubeSize = sqr(rand.x) * (1.0 - padding);
        float pipeSize = sqr(rand.w) * (1.0 - padding);
        p.xz -= rand.yz * (1.0 - max(pipeSize, cubeSize) - padding);

        vec3 q = abs(p);
        float sz = cubeSize * (1.0 - rand.y * 0.2);
        result = min(result, fBoxChamfer(q, vec3(sz, sz * moduleHeight, sz)) - cubeSize * rand.y * 0.2);

        pipeSize *= 0.5;
        p.x = max(0.0, abs(p.x) - pipeSize);
        pModInterval(p.z, pipeSize * 0.9, -2, 2);
        result = min(result, fTorus(p, pipeSize * 0.2, pipeSize * 0.8 * moduleHeight));
    }

    result = max(abs(p.y - 0.5) - 0.5, result);
    return min(fOpEngrave(p.y, cellBoundary - padding, 0.07), result);
}
float fComplexGreeble(vec3 p){return fComplexGreeble(p,1.0,2.0);}
#endif

*/