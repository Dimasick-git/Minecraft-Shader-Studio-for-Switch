#version 450 core
// Minecraft Shader Studio — Author: Dimasick-git
layout(location = 0) in vec3 in_position;
layout(binding = 0, std140) uniform Camera { mat4 view_projection; } camera;
void main() { gl_Position = camera.view_projection * vec4(in_position, 1.0); }
