uniform float uBlack = 0.0;
uniform float uWhite = 0.0;
uniform float uMirrorX = 0.0;

uniform float uSaturation = 1.0;
uniform float uExposure = 0.0;
uniform float uGamma = 1.0;

uniform float uVignetting = 0.0;
uniform vec3 uVignetteColor = vec3(0);

uniform float uGlitchAmountA = 0.0;
// X tiles, Y tiles, intensity, animation speed in beats
uniform vec4 uGlitchAmountB = vec4(9.0, 16.0, 0.0, 9.0);

uniform float uFilmGrain = 0.0;

// https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/
vec3 ACESFilm( vec3 x )
{
    const float a = 2.51;
    const float b = 0.03;
    const float c = 2.43;
    const float d = 0.59;
    const float e = 0.14;
    return sat((x*(a*x+b))/(x*(c*x+d)+e));
}

// Good & fast sRgb approximation from http://chilliant.blogspot.com.au/2012/08/srgb-approximations-for-hlsl.html
vec3 LinearToSRGB(vec3 rgb)
{
    rgb=max(rgb,vec3(0,0,0));
    return max(1.055*pow(rgb,vec3(0.416666667))-0.055,0.0);
}

void main()
{
    vec2 uv = vec2(gl_FragCoord.xy) / uResolution;
    if(uMirrorX != 0.0)
        uv.x = 1.0 - uv.x;

    // jittering horizontal bars
    float line = floor(uv.y * 10.0);
    line = floor(uv.y * mix(10.0, 30.0, h1(line)));
    uv.x += uGlitchAmountA * cub(snoise(uBeats * 8.0 + line * 100.0) - 0.5);

    vec3 color = texture(uImages[0], uv).xyz;

    // Black, white
    float glitchB = (snoise(uBeats * uGlitchAmountB.w + 1001 * h1(floor(uv * uGlitchAmountB.xy))) * 2.0 - 1.0) * uGlitchAmountB.z;
    float black = sat(uBlack + glitchB);
    float white = sat(uWhite - glitchB);
    color = mix(color, vec3(0.0), 1.0 - sqr(1.0 - black));
    color = mix(color, vec3(1.0), sqr(white));

    // Film grain
    float x = (uv.x + 4.0) * (uv.y + 4.0) * (uSeconds + 10.0) * 10.0;
    float grain = clamp(mod((mod(x, 13.0) + 1.0) * (mod(x, 123.0) + 1.0), 0.01) - 0.005, 0.0, 1.0) * 50.0 * uFilmGrain;
    color *= 1.0 - grain;

    // additional color correction
    color = pow(hsv2rgb(rgb2hsv(color) * vec3(1.0, uSaturation, pow(2.0, uExposure))), vec3(uGamma));

    // tone mapping & gamma correction
    color = LinearToSRGB(ACESFilm(max(color, 0.0)));

	// vigneting
	vec2 q = gl_FragCoord.xy / uResolution;
    color = mix(uVignetteColor, color, mix(1.0, pow(16.0 * q.x * q.y * (1.0 - q.x) * (1.0 - q.y), 0.25), uVignetting));

    outColor0 = vec4(color,1.0);
}
