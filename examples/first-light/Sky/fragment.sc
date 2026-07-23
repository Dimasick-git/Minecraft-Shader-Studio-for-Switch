$input v_color0, v_texcoord0, v_worldPos

#include <bgfx_shader.sh>

void main() {
    gl_FragColor = vec4(v_color0.rgb, v_color0.a);
}
