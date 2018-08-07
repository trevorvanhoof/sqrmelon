/// Distance fields and spatial operators///
// Many distance functions & operators taken from http://mercury.sexy/hg_sdf/
// The original hg_sdf.glsl contains additional comments & distance functions you may wish to integrate.

// Rotate
void pR(inout vec2 p,float a){p=cos(a)*p+sin(a)*vec2(p.y,-p.x);}

// Inifnite tube
float fTube(vec2 p,float r){return length(p)-r;}

// Sphere
float fSphere(vec3 p,float r){return length(p)-r;}

// Infinite thick wall
float fSlab(float p,float s){return abs(p)-s;}

// Infinite box
float fBox(vec2 p,vec2 s){return vmax(abs(p)-s);}

// Box
float fBox(vec3 p,vec3 s){return vmax(abs(p)-s);}

// Octahedron
float fDiamond(vec3 p,float s){return dot(abs(p),normalize(vec3(1)))-s;}

// Subtract from the result to get a chamfered edge
float fBoxChamfer(vec3 p,vec3 s){p=abs(p)-s;s=max(p,0);return(s.x+s.y+s.z)*sqrt(0.5)+vmax(p-s);}
float fBoxChamfer(vec2 p,vec2 s){p=abs(p)-s;s=max(p,0);return(s.x+s.y)*sqrt(0.5)+vmax(p-s);}

// Subtract from the result to get a round edge
float fBoxRound(vec3 p,vec3 s)
{
    vec3 q=abs(p)-s;
    float r=vmax(q); // signed SDF for interior
    q=max(q,0);//clamp sides for shaped corners
    if(r>0) // shaped SDF for exterior
    	r=length(max(q,0));
    return r;
}

float fBoxRound(vec2 p,vec2 s)
{
    vec2 q=abs(p)-s;
    float r=vmax(q); // signed SDF for interior
    q=max(q,0);//clamp sides for shaped corners
    if(r>0) // shaped SDF for exterior
    	r=length(max(q,0));
    return r;
}

// Torus
float fTorus(vec3 p,float a,float r){return length(vec2(length(p.xy)-r,p.z))-a;}

// Square torus, basically an fBox wrapped around a circle,
// edit the source & change the fBox for other 2D shapes for more torus variations!
float fSquareTorus(vec3 p,vec2 s,float r){return fBox(vec2(fTube(p.xy,r),p.z),s);}

// Capped cylider
float fCylinder(vec3 p,float r,float h){return max(fTube(p.xz,r),fSlab(p.y,h));}

// Cylinder with rounded caps
float fCapsule(vec3 p,float r,float h){p.y=max(0,abs(p.y)-h);return length(p)-r;}

// 2D triangle
float fTriangle(vec2 p,float r){vec2 a=vec2(.25,-.144),b=normalize(a);return max(dot(vec2(abs(p.x),p.y)-a*r,b),p.y-.289*r);}

// 2D hexagon
float fHexagon(vec2 p,float s){s*=sqrt(2);return max(fTriangle(p.yx,s),fTriangle(-p.yx,s));}

/// Spatial modifiers ///
// Mod P by S, keeping 0 in the center of the segment, return cell ID
#define P(T,S)T pMod(inout T p,S s){T o=floor(p/s+.5);p=(fract(p/s+.5)-.5)*s;return o;}
P(float,float)
P(vec2,float)
P(vec2,vec2)
P(vec3,float)
P(vec3,vec3)
P(vec4,float)
P(vec4,vec4)
#undef P
// Map X to polar coordinates and modulo the angle so that N sections fit inside TAU, then recosntruct the euler coordinates.
float pModPolar(inout vec2 x,float n){float a=atan(x.x,x.y),b=length(x),c=pMod(a,TAU/n);x=vec2(cos(a),sin(a))*b;return mod(c,n);}

// Modulo functions but mirror adjacent cells
float pModMirror(inout float x,float s){s=pMod(x,s);if(int(s)%2==1)x=-x;return s;}
vec2 pModMirror(inout vec2 x,vec2 s){s=pMod(x,s);x=mix(x,-x,ivec2(s)%2);return s;}
vec3 pModMirror(inout vec3 x,vec3 s){s=pMod(x,s);x=mix(x,-x,ivec3(s)%2);return s;}
float pModPolarMirror(inout vec2 x,float n){float a=atan(x.x,x.y),b=length(x),c=pMod(a,TAU/n);if(int(c)%2==1)a=-a;x=vec2(cos(a),sin(a))*b;return mod(c,n);}

/// Combinational operators ///
// In-place operators with material ID support
void fOpUnion(inout float a,float b,inout vec4 m,vec4 n){if(b<a){a=b;m=n;}}
void fOpIntersection(inout float a,float b,inout vec4 m,vec4 n){if(b>a){a=b;m=n;}}
void fOpDifference(inout float a,float b,inout vec4 m,vec4 n){if(-b>a){a=-b;m=n;}}
// Special intersection shapes from hg_sdf
float fOpUnionRound(float a,float b,float r){return max(r,min(a,b))-length(max(r-vec2(a,b),0));}
float fOpUnionChamfer(float a,float b,float r){return min(a,min(b,(a+b-r)*sqrt(.5)));}
float fOpIntersectionRound(float a,float b,float r){return min(-r,max(a,b))+length(max(r+vec2(a,b),0));}
float fOpIntersectionChamfer(float a,float b,float r){return max(a,max(b,(a+b+r)*sqrt(.5)));}
float fOpDifferenceRound(float a,float b,float r){return fOpIntersectionRound(a,-b,r);}
float fOpDifferenceChamfer(float a,float b,float r){return fOpIntersectionChamfer(a,-b,r);}
float fOpUnionSoft(float a,float b,float r){return min(a,b)-sqr(max(r-abs(a-b),0))*.25/r;}

/// Additional functions ///
// Blocks with random heights in the XZ plane
float fGreeble(vec3 p,float h)
{
    vec2 cell = pMod(p.xz, vec2(1.0));
    float bounds = vmax(abs(p.xz));
    return max(p.y - h, min(0.6 - bounds, max(p.y - h * h1(cell), bounds - 0.45)));
}

// http://mercury.sexy/hg_sdf/
float fOpUnionStairs(float a, float b, float r, float n) {
	float s = r/n;
	float u = b-r;
	return min(min(a,b), 0.5 * (u + a + abs ((mod (u - a + s, 2 * s)) - s)));
}

// produces a cylindical pipe that runs along the intersection.
// No objects remain, only the pipe. This is not a boolean operator.
float fOpPipe(float a, float b, float r) {
	return length(vec2(a, b)) - r;
}

// first object gets a v-shaped engraving where it intersect the second
float fOpEngrave(float a, float b, float r) {
	return max(a, (a + r - abs(b))*sqrt(0.5));
}

// first object gets a capenter-style groove cut out
float fOpGroove(float a, float b, float ra, float rb) {
	return max(a, min(a + ra, rb - abs(b)));
}

// first object gets a capenter-style tongue attached
float fOpTongue(float a, float b, float ra, float rb) {
	return min(a, max(a - ra, abs(b) - rb));
}

// Engrave with round edges at the sides, like a soft material was pushed down by a thin object.
float fOpEngraveRound(float a,float b,float r){return max(a,min(r-abs(b),min(a+r,length(abs(vec2(a,b))-r)-r)));}

/*
Cut B out of A, but make the edge wider at the cutting point.
   (B)
 _______
 \     /  <-- taper radius
  |   |
  |(A)|
  |   |
*/
float IntersectTaper(float a,float b,float r){return max(b,min(a,(a-r-b)*sqrt(0.5)));}

// Modulo within a certain start and end point, fitting N cells in there. Returns cell size and cell ID as vec2.
/*vec2 pModRange(inout float x, float start, float end, float numCells)
{
    float range = end - start;
    float cellSize = range / numCells;
    if(x < start + cellSize)
    {
        x -= start + cellSize * 0.5;
        return vec2(cellSize, 0);
    }
    if(x > end - cellSize)
    {
        x -= end - cellSize * 0.5;
        return vec2(cellSize, numCells - 1.);
    }
    float t = (x - start) / range;
    float cellId = floor(t * numCells);
    t = (fract(t * numCells) - 0.5) / numCells;
    x = t * range;
    return vec2(range / numCells, cellId);
}*/
vec2 pModRange(inout float x,float s,float e,float n){float d=e-s,z=d/n,t=(x-s)/d,i=floor(t*n);if(x<s+z){x-=s+z*.5;return vec2(z,0);}if(x>e-z){x-=e-z*.5;return vec2(z,n-1);}x=(fract(t*n)-.5)*d/n;return vec2(d/n,i);}

// Modulo over a single axis, but limit the maximum number of steps, stopping tiling at the given start (s) and end (e) distance. Notice they should be mutliples of the size (z).
float pModInterval(inout float p,float z,float s,float e){float c=floor(p/z+.5);p=(fract(p/z+.5)-.5)*z;if(c>e){p+=z*(c-e);return e;}if(c<s){p+=z*(c-s);return s;}return c;}

// Remap the given point to have Y as distance to a triangle and X as distance along the closest edge. Seams occur at the corners.
vec2 pTriangleSpace(vec2 p,float r){vec2 a=vec2(.25,-.144)*r*2,b=normalize(a),c=vec2(vec2(0,a.y)+p),d=p*b,e=vec2(p.x*b.y,d.y+a.y);a=vec2(p.y*b.x,-d.x);b=e+a;a=e-a;if(b.y>c.y)c=b;if(a.y>c.y)c=a;return c;}

// Pipe / Cylinder with thickness.
float fHollowTube(vec3 p,float r,float h,float t){return max(abs(length(p.xz)-r)-t,abs(p.y)-h);}

// Capsule: A Cylinder with round caps on both sides
float fCapsule(vec2 p, float r, float c) {
	return mix(abs(p.x) - r, length(vec2(p.x, abs(p.y) - c)) - r, step(c, abs(p.y)));
}

// Distance to line segment between <a> and <b>, used for fCapsule() version 2below
float fLineSegment(vec2 p, vec2 a, vec2 b) {
	vec2 ab = b - a;
	float t = sat(dot(p - a, ab) / dot(ab, ab));
	return length((ab * t + a) - p);
}

// Capsule version 2: between two end points <a> and <b> with radius r
float fCapsule(vec2 p, vec2 a, vec2 b, float r) {
	return fLineSegment(p, a, b) - r;
}

// Distance to line segment between <a> and <b>, used for fCapsule() version 2below
float fLineSegment(vec3 p, vec3 a, vec3 b) {
	vec3 ab = b - a;
	float t = sat(dot(p - a, ab) / dot(ab, ab));
	return length((ab * t + a) - p);
}

// Capsule version 2: between two end points <a> and <b> with radius r
float fCapsule(vec3 p, vec3 a, vec3 b, float r) {
	return fLineSegment(p, a, b) - r;
}

float fOctahedron(vec3 p, float r)
{
    return dot(abs(p),vec3(1.0))/sqrt(3)-r;
}

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

vec2 pHexagonTiles(inout vec2 uv, out float edgeDist)
{
    /** Subdivide 2D space in tiling hexagons **/
    // hegagon border distance
    // hexagon aspect ratio
    uv.x *= sqrt(4.0/3.0);

    // this is how big cells should be so the hexagon corners are ON a circle of radius 1
    // (as opposed to cells that are 1 unit wide, meaning a circle of radius 1 fits snugly in the hexagon)
    const float onCircleAdjust = 0.5 / sqrt(0.75);

    // adjust so our hexagons have an oncircle of radius 1
    uv *= onCircleAdjust;
    // and align with the center of the screen
    uv.x -= 0.5;

    // track horizontal tiling
    float cx = floor(uv.x);
    // stagger columns
    uv.y += mod(floor(uv.x), 2.0) * 0.5;
    // track vertical tiling
    float cy = floor(uv.y);
    // get tile-local uv
    vec2 st = fract(uv) - 0.5;
    // get hexagon distance
    uv = abs(st);
    float s = max(uv.x * 1.5 + uv.y, uv.y + uv.y);
    // if s > 1.0 it actually belongs to the adjacent hexagon
    if(s > 1.0)
    {
        // this part is just to adjust tile ID for the
        // adjacent hexagons overlapping this tile

        // vertical tiling is different per column
        float o = -sign(mod(cx,2.0)-0.5);
        if(st.y * o > 0.0)
        {
            cy += o;
        }

        // horizontal tiling is pretty straight forward
        cx += sign(st.x);

        // adjust local UVs as well so they are now fully hexagon local
		st.x -= sign(st.x);
        st.y -= sign(st.y) * 0.5;
    }
    // hexagon distance accros tile boundaries
    s = abs(s - 1.0);
    // invert the aspect ratio and size correction of the local uvs
    st.x *= sqrt(0.75);
    st /= onCircleAdjust;

    uv = st;
    edgeDist = s;
    return vec2(cx, cy);
}
