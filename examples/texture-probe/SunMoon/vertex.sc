#ifdef INSTANCING
  $input a_color0, a_position, a_texcoord0, i_data1, i_data2, i_data3
#else
  $input a_color0, a_position, a_texcoord0
#endif
$output v_color0, v_texcoord0, v_worldPos

#include <bgfx_shader.sh>

void main() {
#ifdef INSTANCING
    mat4 model;
    model[0] = vec4(i_data1.x, i_data2.x, i_data3.x, 0.0);
    model[1] = vec4(i_data1.y, i_data2.y, i_data3.y, 0.0);
    model[2] = vec4(i_data1.z, i_data2.z, i_data3.z, 0.0);
    model[3] = vec4(i_data1.w, i_data2.w, i_data3.w, 1.0);
    vec4 worldPos = mul(model, vec4(a_position, 1.0));
#else
    vec4 worldPos = mul(u_model[0], vec4(a_position, 1.0));
#endif
    v_color0 = a_color0;
    v_texcoord0 = a_texcoord0;
    v_worldPos = worldPos.xyz;
    gl_Position = mul(u_viewProj, vec4(worldPos.xyz, 1.0));
}
