$input v_color0, v_texcoord0, v_worldPos

#include <bgfx_shader.sh>

SAMPLER2D(s_SunMoonTexture, 0);

#ifndef TEXTURE_PROBE_STRENGTH
#define TEXTURE_PROBE_STRENGTH 0.25
#endif

void main() {
    vec4 sampled = texture2D(s_SunMoonTexture, v_texcoord0);
    // Видимый, но мягкий маркер: если семплер работает, солнце/луна получают
    // холодный cyan-сдвиг. Чёрный/белый/отсутствующий диск — полезный сигнал
    // для воспроизведения известной проблемы Vulkan с текстурными материалами.
    vec3 diagnosticTint = mix(sampled.rgb, sampled.rgb * vec3(0.82, 1.06, 1.18), TEXTURE_PROBE_STRENGTH);
    gl_FragColor = vec4(diagnosticTint, sampled.a) * v_color0;
}
