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

/// Utilities ///
#define sat(x) clamp(x,0.,1.)

float vmax(vec2 v){return max(v.x,v.y);}
float vmax(vec3 v){return max(v.x,vmax(v.yz));}
float vmax(vec4 v){return max(vmax(v.xy),vmax(v.zw));}
float vmin(vec2 v){return min(v.x,v.y);}
float vmin(vec3 v){return min(v.x,vmin(v.yz));}

const float PI=3.1415926535897;
const float TAU=PI+PI;
float sqr(float x){return x*x;}
float cub(float x){return sqr(x)*x;}
float quad(float x){return sqr(sqr(x));}

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
