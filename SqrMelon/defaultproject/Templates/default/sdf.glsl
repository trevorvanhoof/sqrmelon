/// Distance fields and spatial operators ///
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
float fBoxChamfer(vec3 p,vec3 s){p=abs(p)-s;s=max(p,0);return(s.x+s.y+s.z)*sqrt(0.333)+vmax(p-s);}
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
float fCapsule(vec2 p,float r,float h){p.y=max(0,abs(p.y)-h);return length(p)-r;}

// 2D triangle, r = edge length
float fTriangle(vec2 p,float r){vec2 a=vec2(.25,-.144),b=normalize(a);return max(dot(vec2(abs(p.x),p.y)-a*r,b),p.y-.289*r);}

// 2D hexagon, r = edge length
float fHexagon(vec2 p,float r){r*=3;return max(fTriangle(p.yx,r),fTriangle(-p.yx,r));}

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
float pModMirror(inout float x,float s){s=pMod(x,s);if(mod(s,2.0)==1.0)x=-x;return s;}
vec2 pModMirror(inout vec2 x,vec2 s){s=pMod(x,s);x=mix(x,-x,mod(s,vec2(2.0)));return s;}
vec3 pModMirror(inout vec3 x,vec3 s){s=pMod(x,s);x=mix(x,-x,mod(s,vec3(2.0)));return s;}
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
// Cone with correct distances to tip and base circle. Y is up, 0 is in the middle of the base.
float fCone(vec3 p, float radius, float height) {
	vec2 q = vec2(length(p.xz), p.y);
	vec2 tip = q - vec2(0, height);
	vec2 mantleDir = normalize(vec2(height, radius));
	float mantle = dot(tip, mantleDir);
	float d = max(mantle, -q.y);
	float projected = dot(tip, vec2(mantleDir.y, -mantleDir.x));
	
	// distance to tip
	if ((q.y > height) && (projected < 0)) {
		d = max(d, length(tip));
	}
	
	// distance to base ring
	if ((q.x > radius) && (projected > length(vec2(height, radius)))) {
		d = max(d, length(q - vec2(radius, 0)));
	}
	return d;
}

// Distance to line segment between <a> and <b>, used for fCapsule() version 2 below
float fLineSegment(vec2 p, vec2 a, vec2 b) {
	vec2 ab = b - a;
	float t = sat(dot(p - a, ab) / dot(ab, ab));
	return length((ab * t + a) - p);
}

// Capsule version 2: between two end points <a> and <b> with radius r
float fCapsule(vec2 p, vec2 a, vec2 b, float r) {
	return fLineSegment(p, a, b) - r;
}

// Distance to line segment between <a> and <b>, used for fCapsule() version 2 below
float fLineSegment(vec3 p, vec3 a, vec3 b) {
	vec3 ab = b - a;
	float t = sat(dot(p - a, ab) / dot(ab, ab));
	return length((ab * t + a) - p);
}

// Capsule version 2: between two end points <a> and <b> with radius r
float fCapsule(vec3 p, vec3 a, vec3 b, float r) {
	return fLineSegment(p, a, b) - r;
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

float fOpUnionStairs(float a, float b, float r, float n) {
	float s = r/n;
	float u = b-r;
	return min(min(a,b), 0.5 * (u + a + abs ((mod (u - a + s, 2 * s)) - s)));
}

// Polyhedra
const vec2 GDFa=vec2(sqrt(1./3.),-sqrt(1./3.));const vec3 GDFb=vec3(0.85065080835,0.52573111211,0);const vec3 GDFc=vec3(0.93417235896,0.35682208977,0);vec3 GDFVectors[19] = vec3[19](vec3(1,0,0),vec3(0,1,0),vec3(0,0,1),GDFa.xxx,GDFa.yxx,GDFa.xyx,GDFa.xxy,GDFc.zyx,GDFc.zyx*vec3(1,-1,1),GDFc.xzy,GDFc.xzy*vec3(-1,1,1),GDFc.yxz,GDFc.yxz*vec3(-1,1,1),GDFb.zxy,GDFb.zxy*vec3(1,-1,1),GDFb.yzx,GDFb.yzx*vec3(-1,1,1),GDFb,GDFb*vec3(-1,1,1));
float fGDF(vec3 p,float r,int s,int e){float d=0;for(int i=s;i<=e;++i)d=max(d,abs(dot(p,GDFVectors[i])));return d-r;}
float fIcosahedron(vec3 p,float r){return fGDF(p,r,3,12);}
float fDodecahedron(vec3 p,float r){return fGDF(p,r,13,18);}
float fTruncatedOctahedron(vec3 p,float r){return fGDF(p,r,0,6);}
float fTruncatedIcosahedron(vec3 p,float r){return fGDF(p,r,3,18);}

// end hg_sdf

float fOctahedron(vec3 p, float r){return dot(abs(p),vec3(1.0))/sqrt(3)-r;}

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
float fOpIntersectTaper(float a,float b,float r){return max(b,min(a,(a-r-b)*sqrt(0.5)));}

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
