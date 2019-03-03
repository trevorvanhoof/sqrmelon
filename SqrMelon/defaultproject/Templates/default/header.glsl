#version 410

// Precision of the distance field & normal calculation.
const float EPSILON = 0.0001;

// Current render target size in pixels (width, height)
uniform vec2 uResolution;

// Image input as defined in the template.
// Because this header is included everywhere the array size just matches the max input count in the shader graph.
// Some passes may not use all indices (or otherwise access inactive texture IDs).
uniform sampler2D uImages[8];

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
uniform vec3 uShake = vec3(0.0,0.0,0.0);
uniform float uFishEye = 0.0;
const float PI=3.1415926535897;
Ray ScreenRayUV(vec2 uv)
{
    vec2 suv=vec2(uBeats*uShake.x,uShake.y);
    vec3 direction = mix(mix(uFrustum[0].xyz, uFrustum[1].xyz, uv.x), mix(uFrustum[2].xyz, uFrustum[3].xyz, uv.x), uv.y);
    return Ray(uV[3].xyz
             + uV[0].xyz*(texture(uImages[3],suv).y-.5)*uShake.z
             + uV[1].xyz*(texture(uImages[3],suv+.5).y-.5)*uShake.z,
               normalize(direction * mat3(uV)));
}
// Shoots a ray through the current pixel based on uV and uFrustum
vec2 FishEyeUV(float amount, float factor)
{
    //normalized coords with some cheat
    vec2 uv = gl_FragCoord.xy / (uResolution.x / factor);
	float aspectRatio = uResolution.x / uResolution.y;
	vec2 center = vec2(0.5, 0.5 / aspectRatio);
	vec2 direction = uv - center;
	float radius = length(direction);

	// stick to corners
	float bind = length(center);
	float power = PI / bind * amount;
	/*if (power < 0.0)
	{
	    // stick to borders
	    if (aspectRatio < 1.0) bind = center.x;
	    else bind = center.y;
	}*/

	// if (power > 0.0) // fisheye
    uv = center + (direction / radius) * tan(radius * power) * bind / tan( bind * power);
	// else if (power < 0.0) // antifisheye
	//	   uv = center + normalize(direction) * atan(radius * -power * 10.0) * bind / atan(-power * bind * 10.0);
	// else
	//     uv = uv;

    return vec2(uv.x, uv.y * aspectRatio);
}
Ray ScreenRay(float factor)
{
    return ScreenRayUV((uFishEye > 0.) ? FishEyeUV(uFishEye, factor) : (gl_FragCoord.xy / (uResolution / factor)));
}
Ray ScreenRay()
{
    return ScreenRay(1.0);
}

/// Utilities ///
#define sat(x) clamp(x,0.,1.)

float vmax(vec2 v){return max(v.x,v.y);}
float vmax(vec3 v){return max(v.x,vmax(v.yz));}
float vmax(vec4 v){return max(vmax(v.xy),vmax(v.zw));}
float vmin(vec2 v){return min(v.x,v.y);}
float vmin(vec3 v){return min(v.x,vmin(v.yz));}

const float TAU=PI+PI;
#define ops(T) T sqr(T x){return x*x;} T cub(T x){return sqr(x)*x;} T quad(T x){return sqr(sqr(x));}
ops(float)
ops(vec2)
ops(vec3)
ops(vec4)
#undef ops

float stepPass(float a,float b){return step(a,b)*b;}
float stepNormalized(float a,float b){return stepPass(0.,(b-a)/(1.-a));}

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

// Clamped remap function (remaps one range to another range)
float cremap(float x, float imin, float imax, float omin, float omax){return mix(omin,omax,sat((x-imin)/(imax-imin)));}