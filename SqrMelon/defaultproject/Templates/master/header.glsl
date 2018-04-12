#version 410

// Precision of the distance field & normal calculation.
const float EPSILON = 0.001;

// Current render target size in pixels (width, height)
uniform vec2 uResolution;

// Image input as defined in the template.
// Because this header is included everywhere the array size just matches the max input count in the shader graph.
// Some passes may not use all indices (or otherwise access inactive texture IDs).
uniform sampler2D uImages[3];

// Time from the tool
uniform float uBeats;
uniform float uSeconds;

// Camera view matrix
uniform mat4 uV;

// Frustum is precomputed from the field of view
uniform mat4 uFrustum;

// First output buffer
out vec4 outColor0;

struct Ray
{
    vec3 origin;
    vec3 direction;
};

struct Hit
{
    float totalDistance;
    vec3 point;
    vec3 normal;
    vec4 materialId;
};

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

Material MixMaterial(Material a, Material b, float w)
{
    return Material(mix(a.albedo, b.albedo, w),
    mix(a.additive, b.additive, w),
    mix(a.specularity, b.specularity, w),
    mix(a.roughness, b.roughness, w),
    mix(a.reflectivity, b.reflectivity, w),
    mix(a.blur, b.blur, w),
    mix(a.metallicity, b.metallicity, w));
}

// Shoots a ray through the current pixel based on uV and uFrustum
Ray ScreenRayUV(vec2 uv)
{
    vec3 direction = mix(mix(uFrustum[0].xyz, uFrustum[1].xyz, uv.x), mix(uFrustum[2].xyz, uFrustum[3].xyz, uv.x), uv.y);
    return Ray(uV[3].xyz, normalize(direction * mat3(uV)));
}
// Shoots a ray through the current pixel based on uV and uFrustum
Ray ScreenRay(){return ScreenRayUV(gl_FragCoord.xy/uResolution);}

const float PI=3.1415926535897;
const float TAU=PI+PI;
float sqr(float x){return x*x;}
float cub(float x){return sqr(x)*x;}
float quad(float x){return sqr(sqr(x));}

/// Distance fields and spatial operators///
// Many distance functions & operators taken from http://mercury.sexy/hg_sdf/
// The original hg_sdf.glsl contains additional comments & distance functions you may wish to integrate.

#define sat(x) clamp(x,0.,1.)

float vmax(vec2 v){return max(v.x,v.y);}
float vmax(vec3 v){return max(v.x,vmax(v.yz));}
float vmax(vec4 v){return max(vmax(v.xy),vmax(v.zw));}
float vmin(vec2 v){return min(v.x,v.y);}
float vmin(vec3 v){return min(v.x,vmin(v.yz));}

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
float pModPolar(inout vec2 x,float n){float a=atan(x.x,x.y),b=length(x),c=pMod(a,TAU/n);x=vec2(cos(a),sin(a))*b;return int(c)%int(n);}

// Modulo functions but mirror adjacent cells
float pModMirror(inout float x,float s){s=pMod(x,s);if(int(s)%2==1)x=-x;return s;}
vec2 pModMirror(inout vec2 x,vec2 s){s=pMod(x,s);x=mix(x,-x,ivec2(s)%2);return s;}
vec3 pModMirror(inout vec3 x,vec3 s){s=pMod(x,s);x=mix(x,-x,ivec3(s)%2);return s;}
float pModPolarMirror(inout vec2 x,float n){float a=atan(x.x,x.y),b=length(x),c=pMod(a,TAU/n);if(int(c)%2==1)a=-a;x=vec2(cos(a),sin(a))*b;return int(c)%int(n);}

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

/// Color conversions ///
// https://gist.github.com/sugi-cho/6a01cae436acddd72bdf
vec3 rgb2hsv(vec3 c)
{
    vec4 K=vec4(0,-1/3.,2/3.,-1),
    p=mix(vec4(c.bg,K.wz),vec4(c.gb,K.xy),step(c.b,c.g)),
    q=mix(vec4(p.xyw,c.r),vec4(c.r,p.yzx),step(p.x,c.r));
    float d=q.x-min(q.w,q.y),e=1.0e-10;
    return vec3(abs(q.z+(q.w-q.y)/(6*d+e)),d/(q.x+e),q.x);
}
vec3 hsv2rgb(vec3 c){return c.z*mix(vec3(1),sat(abs(fract(vec3(1,2/3.,1/3.)+c.x)*6-3)-1),c.y);}
vec3 rgb2hsv(float r,float g,float b){return rgb2hsv(vec3(r,g,b));}
vec3 hsv2rgb(float h,float s,float v){return hsv2rgb(vec3(h,s,v));}

// tri-planar texture blend
vec4 textureTri(sampler2D img,vec3 p,vec3 n){n=abs(n);n/=max(.0001,n.x+n.y+n.z);return texture(img,p.yz)*n.x+texture(img,p.xz)*n.y+texture(img,p.xy)*n.z;}
vec4 textureTwo(sampler2D img,vec3 p,vec3 n){n=abs(n);n/=max(.0001,n.x+n.z);return texture(img,p.zy)*n.x+texture(img,p.xy)*n.z;} // a texture3 that pretents n.y = 0.0
vec4 textureTri(sampler2D img,vec3 p,vec3 n,float w){n=normalize(pow(abs(n),vec3(w)));n/=max(.0001,n.x+n.y+n.z);return texture(img,p.yz)*n.x+texture(img,p.xz)*n.y+texture(img,p.xy)*n.z;}
// tri-planar projection for UV coordinates (no blend)
vec2 projectTri(vec3 p,vec3 n){n=abs(n);if(n.x>vmax(n.yz))return p.zy;if(n.y>n.z)return p.xz;return p.xy;}
// tri-planar projection for UV coordinates without mirrored edges on vertical planes
vec2 projectTri2(vec3 p,vec3 n){vec3 s=sign(n);n=abs(n);if(n.x>vmax(n.yz))return p.zy*vec2(s.x,1);if(n.y>n.z)return p.xz*s.y;return p.xy*vec2(-s.z,1);}

/// Lighting and shading models ///
struct LightData
{
    Ray ray; // ray used to generate hit
    Hit hit; // hit data, mostly for normal
    Material material; // material info so we can shade
};

float G1V(float dotNV, float k){return 1.0 / (dotNV * (1.0 - k)+k);}

float ggxSpecular(float NdotV, float NdotL, vec3 N, vec3 L, vec3 V, float roughness)
{
    float F0 = 0.5;
    // http://filmicworlds.com/blog/optimizing-ggx-shaders-with-dotlh/
    vec3 H = normalize(V + L);
    float NdotH = sat(dot(N, H));
    float LdotH = sat(dot(L, H));
    float a2 = roughness * roughness;

    float D = a2 / (PI * sqr(sqr(NdotH) * (a2 - 1.0) + 1.0));

    LdotH = 1.0 - LdotH;
    float F = F0 + (1.0 - F0) * cub(LdotH) * LdotH;

    float vis = G1V(NdotL, a2 * 0.5) * G1V(NdotV, a2 * 0.5);
    return NdotL * D * F * vis;
}

vec3 AmbientLight(LightData data, vec3 color)
{
    return data.material.albedo * color * (1.0 - data.material.specularity);
}

vec3 RimLight(LightData data, vec3 color, float power)
{
	return pow(min(1.0 + dot(data.hit.normal, data.ray.direction), 1.0), power) * data.material.albedo * color;
}

// ShadowArgs struct & default constructor helper.
struct ShadowArgs
{
    float near;
    float far;
    float hardness;
    int steps;
};
ShadowArgs shadowArgs(){return ShadowArgs(0.1,100.0,128.0,32);}

float fField(vec3 p);

// Basic soft shadow function from http://www.iquilezles.org/www/articles/rmshadows/rmshadows.htm
float Shadow(Ray ray, ShadowArgs shadow)
{
	float dist = shadow.near;
	float atten = 1.0;
	for(int i = 0; i < shadow.steps; ++i)
	{
        #ifdef SHADOW_CASTER
		float sampl = fShadowCaster(ray.origin + ray.direction * dist);
		#else
		float sampl = fField(ray.origin + ray.direction * dist);
        #endif
		if(sampl<EPSILON)
			return 0.0;
		if(dist > shadow.far)
			return atten;
		atten = min(atten, shadow.hardness * sampl / dist);
		dist += sampl;
	}
	return atten;
}

// Core lighting function.
vec3 _DirectionalLight(LightData data, vec3 direction, vec3 color, float atten)
{
    float satNdotV = sat(dot(data.hit.normal, -data.ray.direction));
    float satNdotL = sat(dot(data.hit.normal, normalize(direction)));
    return color * mix(
        // diffuse
        atten * data.material.albedo * satNdotL,
        // specular
        mix(atten, 1.0, data.material.roughness) * // apply shadow on rough specular
        mix(vec3(1.0), data.material.albedo, data.material.metallicity) * // metallicity
        ggxSpecular(satNdotV, satNdotL, data.hit.normal, normalize(direction), -data.ray.direction, max(0.001, data.material.roughness)),

        data.material.specularity);
}

// Directional light.
vec3 DirectionalLight(LightData data, vec3 direction, vec3 color)
{
    return _DirectionalLight(data, direction, color, 1.0);
}

// Directional light with shadow arg.
vec3 DirectionalLight(LightData data, vec3 direction, vec3 color, ShadowArgs shadow)
{
    return _DirectionalLight(data, direction, color, Shadow(Ray(data.hit.point, normalize(direction)), shadow));
}

// Core point light function, attenuation argument can be used to apply shadows.
vec3 _PointLight(LightData data, vec3 point, vec3 color, float lightRadius, float atten)
{
    vec3 direction = point - data.hit.point;
    float d = length(direction);
    float dd = sqr(d);
    if(lightRadius>0.0)
        atten /= (1.0 + (d + d) / lightRadius + dd / sqr(lightRadius));
    else // infinitesimal light radius
        atten /= dd;
    return _DirectionalLight(data, direction, color, atten);
}

// Infinitesimal point light.
vec3 PointLight(LightData data, vec3 point, vec3 color)
{
    return _PointLight(data, point, color, 0.0, 1.0);
}

// Point light.
vec3 PointLight(LightData data, vec3 point, vec3 color, float lightRadius)
{
    return _PointLight(data, point, color, lightRadius, 1.0);
}

// Point light with radius & shadow, light radius is not used by shadowing function, only for falloff.
vec3 PointLight(LightData data, vec3 point, vec3 color, float lightRadius, ShadowArgs shadow)
{
    return _PointLight(data, point, color, lightRadius, Shadow(Ray(data.hit.point, normalize(data.hit.point - point)), shadow));
}
