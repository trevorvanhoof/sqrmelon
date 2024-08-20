// Post effect example, this effect does nothing but just shows the motions.
#version 410

// This is the previous buffer, coming through input0 in our pass in default.xml
// change [1] to something bigger if your post process has multiple inputs.
uniform sampler2D uImages[1];

uniform vec2 uResolution;

// This is what gets written to the output buffer,
// and sends down the line to the next pass.
out vec4 outColor;

void main()
{
    // This is the main post effect code
    // simply forwards the input 0 to the outColor.
    vec2 uv = gl_FragCoord.xy / uResolution;
    outColor = texture(uImages[0], uv);
}
