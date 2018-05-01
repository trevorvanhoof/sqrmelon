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
float fBoxChamfer(vec3 p,vec3 s){p=abs(p)-s;s=max(p,0);return(s.x+s.y+s.z)*(1/sqrt(3))+vmax(p-s);}

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
void fOpDifference(inout float a,float b,inout vec4 m,vec4 n){if(-b>a){a=b;m=n;}}
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
float fGreeble(vec3 p,float h,float f)
{
    vec2 cell = pMod(p.xz, vec2(1.0));
    float bounds = vmax(abs(p.xz));
    return max(p.y - h, min(0.6 - bounds, max(p.y - h * pow(snoise(snoise(cell/8.0,4.0)+uBeats/4.0,4.0),f), bounds - 0.45)));
}
