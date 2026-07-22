#version 450 core
// Minecraft Shader Studio — Author: Dimasick-git
layout(location = 0) out vec4 out_color;
layout(binding = 1, std140) uniform Tint { vec4 color; } tint;
void main() { out_color = tint.color; }
