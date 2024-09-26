#version 410

uniform sampler2D uImages[1];

out vec4 fragColor;

void main() {
    fragColor = texelFetch(uImages[0], ivec2(gl_FragCoord.xy), 0);
}
