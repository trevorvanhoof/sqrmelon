#version 430

layout (local_size_x = 10, local_size_y = 10, local_size_z = 10) in;

layout(std430, binding=0) writeonly buffer BLOCK { float vertices[]; };

void main() {
    uint workGroupSize = gl_WorkGroupSize.x * gl_WorkGroupSize.y * gl_WorkGroupSize.z;
    uint globalOffset = ((gl_WorkGroupID.z * gl_NumWorkGroups.y + gl_WorkGroupID.y) * gl_NumWorkGroups.x + gl_WorkGroupID.x) * workGroupSize;
    uint globalIndex = globalOffset + gl_LocalInvocationIndex;
    vertices[globalIndex * 3 + 0] = globalIndex * 0.01 - 1.0;
    vertices[globalIndex * 3 + 1] = globalIndex % 2 - 0.5 + sin(globalIndex * 0.01);
    vertices[globalIndex * 3 + 2] = 0.0;
}
