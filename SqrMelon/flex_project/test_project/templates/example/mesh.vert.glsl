#version 410

layout(location=0) in vec3 aP;

void main() {
    gl_Position = vec4(aP, 1.0);
    // gl_Position.x = gl_VertexID * 0.001;
    // gl_Position.y = gl_VertexID % 2 - 0.5 + sin(gl_VertexID * 0.01);
    // gl_Position.z = 0.0;
}
