
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

float fField(vec3 p, out vec4 m);

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
