uniform float uBlack = 0.0;
uniform float uWhite = 0.0;

uniform float uSaturation = 1.0;
uniform float uLuminance = 1.0;
uniform float uGamma = 1.0;

uniform float uGlitchAmountA = 0.0;

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

    // jittering horizontal bars
    uv.x += uGlitchAmountA * quad(snoise(uBeats * 8.0 + floor(uv.y * 10.0) * 100.0));

    vec3 color = texture(uImages[0], uv).xyz;

    // Black, white
    color = mix(color, vec3(0.0), 1.0 - pow(1.0 - uBlack, 2.0));
    color = mix(color, vec3(1.0), pow(uWhite, 2.2));

    // Shit film grain
    float grainAmount = 0.8;
    float grainStrength = 50.0 * grainAmount;
    float x = (uv.x + 4.0) * (uv.y + 4.0) * (uSeconds + 10.0) * 10.0;
    float grain = clamp(mod((mod(x, 13.0) + 1.0) * (mod(x, 123.0) + 1.0), 0.01) - 0.005, 0.0, 1.0) * grainStrength;
    color *= 1.0 - grain;

    // additional color correction
    color = pow(hsv2rgb(rgb2hsv(color) * vec3(1.0, uSaturation, uLuminance)), vec3(uGamma));

    // tone mapping & gamma correction
    color = LinearToSRGB(ACESFilm(max(color, 0.0)));

    outColor0 = vec4(color,1.0);
}
