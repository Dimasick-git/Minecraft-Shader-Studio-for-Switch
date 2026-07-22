// Minecraft Shader Studio Loader
// Author: Minecraft-git
#include <switch.h>
#include <cstdio>

int main(int argc, char** argv) {
    consoleInit(nullptr);
    std::printf("\x1b[2;2HMinecraft Shader Studio\n");
    std::printf("\x1b[4;2HStatus: active R&D / fail-closed\n");
    std::printf("\x1b[6;2HPacks: sdmc:/switch/mss/packs/\n");
    std::printf("\x1b[8;2HNo game assets are bundled or downloaded.\n");
    std::printf("\x1b[10;2HPress + to exit.\n");
    PadState pad; padConfigureInput(1, HidNpadStyleSet_NpadStandard); padInitializeDefault(&pad);
    while (appletMainLoop()) { padUpdate(&pad); if (padGetButtonsDown(&pad) & HidNpadButton_Plus) break; consoleUpdate(nullptr); }
    consoleExit(nullptr); return 0;
}
