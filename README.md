<div align="center">
  <img src="assets/logo.svg" width="112" alt="Minecraft Shader Studio logo">
  <h1>Minecraft Shader Studio</h1>
  <p><strong>Native tools and a LayeredFS pack builder for experimental Minecraft Bedrock RenderDragon work on Nintendo Switch.</strong></p>
  <p><img alt="R&D" src="https://img.shields.io/badge/status-active%20R%26D-2783DE"> <img alt="C++20" src="https://img.shields.io/badge/C%2B%2B-20-2783DE"> <img alt="tests" src="https://img.shields.io/badge/tests-native%20%2B%20Python-46A171"></p>
</div>

> [!IMPORTANT]
> Это реальный собираемый проект с интеграцией открытых NVN/Maxwell-инструментов. `uam-nvn` используется как основной GLSL-компилятор, `devkitPro/uam` — как fallback. RenderDragon-контейнеры по-прежнему проверяются по версиям и hardware fixtures.

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
mss validate examples/vibrant-lite
mss build examples/vibrant-lite --minecraft-version 26.32 \
  --atmosphere-version 1.11.2 --title-id YOUR_TITLE_ID --output dist
```

### Switch loader — C++/libnx

```bash
# В devkitPro shell с devkitA64 и libnx
make -C switch-loader
```

Loader собирается в `minecraft-shader-studio.nro`. Сейчас реализован безопасный UI-каркас; запись overlay будет включена только после атомарного rollback и тестов на Erista/Mariko.

## NVN pipeline

Проект теперь напрямую интегрирует открытый `uam-nvn` и использует `devkitPro/uam` как fallback. Реализованы компиляция GLSL в 64-байтово выровненный Maxwell payload, инспекция NVN-бинарников и экспериментальное сохранение 0x30-байтового NVN prefix из пользовательского шаблона.

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

## Последние targets на 22 июля 2026

- Minecraft Bedrock detected: `26.33`;
- последний проверенный fixture: `26.32`;
- Atmosphère: `1.11.2`.

Новые версии автоматически обнаруживаются. Они получают статус `detected` и блокируются до проверки, чтобы проект не заявлял ложную совместимость.

## Ограничения

Проект не включает Minecraft, ключи, дампы, Nintendo SDK и проприетарные `material.bin`. Он не обходит лицензию и не преобразует произвольный GLSL в NVN. Поддерживаются только файлы, законно полученные пользователем из собственной копии игры.

## Проверки

CI собирает C++ на Linux, Windows и macOS, запускает native tests, Python tests, compileall и secret scan. Автор исходников: **Dimasick-git**.

Лицензия: MIT. Проект не связан с Mojang, Microsoft, Nintendo или Atmosphère-NX.
