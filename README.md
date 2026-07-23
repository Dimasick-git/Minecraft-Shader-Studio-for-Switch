<div align="center">
  <img src="assets/logo.svg" width="112" alt="Minecraft Shader Studio logo">
  <h1>Minecraft Shader Studio</h1>
  <p><strong>Native tools and a LayeredFS pack builder for experimental Minecraft Bedrock RenderDragon work on Nintendo Switch.</strong></p>
  <p><img alt="R&D" src="https://img.shields.io/badge/status-active%20R%26D-2783DE"> <img alt="C++20" src="https://img.shields.io/badge/C%2B%2B-20-2783DE"> <img alt="tests" src="https://img.shields.io/badge/tests-native%20%2B%20Python-46A171"></p>
</div>

> [!IMPORTANT]
> **Вердикт исследования (июль 2026): Switch-версия Minecraft загружает шейдеры Vulkan (SPIR-V)** — поэтому основной пайплайн проекта это Vulkan (Lazurite + bgfx shaderc). NVN/Maxwell-инструменты (`uam-nvn`, `devkitPro/uam`) — экспериментальный R&D-трек (roadmap R4): игра такие шейдеры сейчас не загружает. Доказательства и источники: [docs/RESEARCH-2026-07.md](docs/RESEARCH-2026-07.md). RenderDragon-контейнеры по-прежнему проверяются по версиям и hardware fixtures.

## Quick Start (Быстрый старт)

1.  **Установка**:
    ```bash
    python -m pip install -e .
    ```
2.  **Создание проекта**:
    ```bash
    mss init "MyCoolShader" --author "YourName"
    cd MyCoolShader
    ```
3.  **Добавление материалов**: Поместите ваши `.material.bin` в папку `materials/`.
4.  **Сборка**:
    ```bash
    # --allow-untested: 1.26.34 обнаружена, но ещё не подтверждена на железе
    mss build . --minecraft-version 1.26.34 --atmosphere-version 1.11.2 --title-id 0100D71004694000 --allow-untested
    ```

## Реально компилируемые компоненты

### Native CLI — C++20

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/minecraft-shader-studio validate examples/vibrant-lite
```

Команды:

```text
minecraft-shader-studio version
minecraft-shader-studio validate <pack>
minecraft-shader-studio plan <pack> <title-id>
```

### Pack builder — Python 3.11+

```bash
python -m pip install -e .
mss latest
mss doctor
mss init <name> [--preset {basic,newb-x,mcbe-codebase}]
mss unpack <material.bin> -o <output_dir>
mss validate <pack>
mss build <pack> --minecraft-version <v> --atmosphere-version <v> --title-id <id>
```

### База знаний и документация

Мы собрали всю необходимую информацию для разработчиков шейдеров:
- [Исследование: NVN или Vulkan? (июль 2026)](docs/RESEARCH-2026-07.md) — вердикт: Switch грузит Vulkan/SPIR-V; доказательства, тулчейн, источники.
- [Технические детали RenderDragon на Switch](docs/wiki/RENDERDRAGON_SWITCH.md) — про NVN, Vulkan и форматы файлов.
- [Гайд по LayeredFS и Title ID](docs/wiki/SWITCH_GUIDE.md) — как правильно устанавливать шейдеры на консоль.

### Интеграция с внешними инструментами

Проект поддерживает:
- **Lazurite**: Распаковка, анализ и сборка материалов (основной тулчейн).
- **MaterialBinTool**: Глубокая работа с `.material.bin`.
- **bgfx shaderc (форк bgfx-mcbe)**: Компиляция bgfx SC → SPIR-V (Vulkan — то, что реально грузит Switch).
- **uam-nvn / uam**: Экспериментальный NVN/Maxwell-трек (R&D).

### Vulkan пайплайн (основной для Switch)

Switch-версия Minecraft загружает именно SPIR-V, поэтому это главный трек проекта:
```bash
mss vulkan compile your_shader.glsl --stage vert --output build/vulkan
```



### Switch loader — C++/libnx

```bash
# В devkitPro shell с devkitA64 и libnx
make -C switch-loader
```

Loader собирается в `minecraft-shader-studio.nro`. Сейчас реализован безопасный UI-каркас; запись overlay будет включена только после атомарного rollback и тестов на Erista/Mariko.

## NVN pipeline (экспериментальный R&D)

Проект напрямую интегрирует открытый `uam-nvn` и использует `devkitPro/uam` как fallback. Реализованы компиляция GLSL в 64-байтово выровненный Maxwell payload, инспекция NVN-бинарников и экспериментальное сохранение 0x30-байтового NVN prefix из пользовательского шаблона. **Minecraft эти бинарники сейчас не загружает** (тег `Nvn` зарезервирован «на будущее») — трек существует для исследования формата (roadmap R4).

```bash
export MSS_UAM=/path/to/uam-nvn
mss nvn compile examples/nvn/minimal.vert --stage vert --output build/nvn
mss nvn inspect base.nvn.bin
mss nvn graft --template base.nvn.bin --raw build/nvn/minimal.vert.maxwell.bin --output build/nvn/minimal.nvn.bin
```

Техническая схема и upstream-компоненты: [docs/NVN_PIPELINE.md](docs/NVN_PIPELINE.md).

## Структура

```text
native/              C++20 host CLI и unit tests
src/mss/             Python pack builder
switch-loader/       libnx homebrew application
compatibility/       rolling version matrix
examples/            публичные тестовые fixtures
.github/workflows/   CI, release и version watcher
```

## Последние targets на 23 июля 2026

- Minecraft Bedrock detected: `1.26.34` (preview: `1.26.50`);
- Title ID (Bedrock): `0100D71004694000`;
- Atmosphère: `1.11.2` (FW 22.5.0).

Новые версии автоматически обнаруживаются. Они получают статус `detected` и блокируются до проверки, чтобы проект не заявлял ложную совместимость.

## Ограничения

Проект не включает Minecraft, ключи, дампы, Nintendo SDK и проприетарные `material.bin`. Он не обходит лицензию и не преобразует произвольный GLSL в NVN. Поддерживаются только файлы, законно полученные пользователем из собственной копии игры.

## Проверки

CI собирает C++ на Linux, Windows и macOS, запускает native tests, Python tests, compileall и secret scan. Автор исходников: **Dimasick-git**.

Лицензия: MIT. Проект не связан с Mojang, Microsoft, Nintendo или Atmosphère-NX.
