<div align="center">
  <img src="assets/logo.svg" width="112" alt="Minecraft Shader Studio logo">
  <h1>Minecraft Shader Studio</h1>
  <p><strong>Инструменты сборки и диагностический стенд для экспериментальных RenderDragon/Vulkan-материалов Minecraft Bedrock на Nintendo Switch.</strong></p>
  <p><img alt="R&D" src="https://img.shields.io/badge/status-controlled%20R%26D-2783DE"> <img alt="C++20" src="https://img.shields.io/badge/C%2B%2B-20-2783DE"> <img alt="tests" src="https://img.shields.io/badge/tests-native%20%2B%20Python-46A171"></p>
</div>

> **Статус проекта.** Lazurite документирует `Vulkan` как платформу Switch, а LayeredFS позволяет подменять файлы RomFS в CFW. Это делает Vulkan `material.bin` практическим направлением исследования, но **не доказывает** работу конкретного пользовательского шейдера на устройстве. MSS различает `built-and-inspected` и `hardware-verified`; второй статус присваивается только после теста на вашей консоли. Подробный обзор публичных наработок: [исследование от 11 августа 2026](docs/RESEARCH-2026-08.md). [1]

## Что реально делает MSS

| Возможность | Статус | Что это означает |
|---|---|---|
| Сборка BGFX SC в Lazurite-проекте | Реализовано | Используется `shaderc` из `bgfx-mcbe` для сборки `material.bin` под профиль `Vulkan`. |
| Проверка Switch baseline | Реализовано | `mss compile --profile switch` требует ванильный Vulkan `.material.bin` из RomFS той же версии игры и проверяет invariants результата. |
| Инспекция material.bin | Реализовано | `mss material inspect` сохраняет hash, format version, платформы, стадии, варианты и число texture buffers. |
| Контрольный тест текстур | Реализовано | `examples/texture-probe` проверяет `s_SunMoonTexture` перед сложными материалами. |
| Работа на конкретной Switch | Не подтверждено автоматически | Требует controlled hardware test, наблюдения в игре и сохранённого отчёта. |
| NVN/Maxwell-путь | Экспериментальный | Не является методом загрузки материала Minecraft; не используйте его для Switch-пака. |

## Перед началом

Установите Python 3.11+ и зависимости проекта. Для разработки из clone используйте editable-установку; для запуска тестов без установки применяйте `PYTHONPATH=src`.

```bash
python -m pip install -e .
python3 scripts/fetch_toolchain.py
mss doctor
```

Скрипт загружает открытые host-инструменты `shaderc` и BGFX headers по закреплённой ревизии и проверяет SHA-256 для поддерживаемого Linux toolchain; после этого MSS автоматически находит `toolchains/bin/shadercRelease`. Его опция `--reference-merge` скачивает только открытые reference-материалы для изучения; это **не** Switch baseline. Для реальной проверки baseline должен быть извлечён пользователем из RomFS своей копии Minecraft и соответствовать установленной версии игры.

## Контролируемый Switch/Vulkan workflow

Сначала протестируйте минимум — `SunMoon` с одной текстурой. Это целенаправленно проверяет открытый риск Lazurite/Vulkan с texture sampler, прежде чем менять `RenderChunk` или переносить большой shader pack. [2]

```bash
# 1. Взять из RomFS своей Switch-версии игры:
#    renderer/materials/SunMoon.material.bin
mss material inspect /путь/к/SunMoon.material.bin

# 2. Собрать минимальный texture probe; baseline обязателен для profile switch.
mss compile examples/texture-probe \
  -o examples/texture-probe/materials \
  --baseline /путь/к/SunMoon.material.bin \
  -d "TEXTURE_PROBE_STRENGTH 0.25"

# 3. Получить независимый структурный отчёт.
mss material compare \
  --baseline /путь/к/SunMoon.material.bin \
  --candidate examples/texture-probe/materials/SunMoon.material.bin

# 4. Упаковать LayeredFS-архив. Версии указывайте от своей установки.
mss build examples/texture-probe \
  --minecraft-version ВАША_ВЕРСИЯ \
  --atmosphere-version ВАША_ВЕРСИЯ \
  --allow-untested
```

Положительный `material compare` говорит, что собранный файл сохраняет имя, format version, `Vulkan`, стадии и варианты baseline. Он **не** проверяет изображение и всегда оставляет `hardware_verified: false`. Инструкции наблюдения, A/B-теста и rollback приведены в [README texture-probe](examples/texture-probe/README.md).

После успешной texture-проверки можно аналогично собрать `first-light`, передав собственный `Sky.material.bin` как baseline:

```bash
mss compile examples/first-light \
  -o examples/first-light/materials \
  --baseline /путь/к/Sky.material.bin \
  -d "FIRST_LIGHT_STRENGTH 0.35"
```

Опция `--unsafe-no-baseline` существует только для CI и smoke-сборок. CLI маркирует такой результат как `smoke-build-only`; его нельзя устанавливать на Switch.

## Аппаратная проверка и rollback

LayeredFS ожидает структуру `sd:/atmosphere/contents/<title_id>/romfs/...`. Если игра перестала запускаться после установки теста, удерживайте `L` при запуске, чтобы отключить моды, затем удалите последний `.material.bin` из overlay. [3]

| Наблюдение | Значение | Следующий шаг |
|---|---|---|
| Sun/Moon видны с мягким cyan-сдвигом | Texture probe прошёл на этой связке baseline, игры и toolchain. | Сохранить отчёты `inspect/compare`, версии и SHA-256; только затем переходить к сложному материалу. |
| Чёрная/белая текстура, crash, отсутствие эффекта | Обнаружен полезный failure; это может быть sampler-баг или несоответствие baseline/версии. | Откатить LayeredFS, сохранить отчёты и подготовить репродуктор для upstream. |
| Файл собран, но на консоли не проверялся | Только `built-and-inspected`. | Не заявлять работу на Switch и не распространять как готовый shader pack. |

## Команды

```text
mss doctor
mss latest
mss init <name> [--preset {basic,newb-x,mcbe-codebase}]
mss material inspect <material.bin>
mss material compare --baseline <switch.material.bin> --candidate <built.material.bin>
mss compile <project> --baseline <switch.material.bin> [--shaderc <custom-shaderc>]
mss build <pack> --minecraft-version <v> --atmosphere-version <v> [--allow-untested]
mss validate <pack>
mss unpack <material.bin> -o <output_dir>
```

## Проверки разработки

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

## Структура репозитория

```text
native/              C++20 host CLI и unit tests
src/mss/             Python CLI, build и material inspection
switch-loader/       libnx homebrew UI-каркас; overlay-запись не реализована
compatibility/       rolling version matrix
examples/            публичные исходники и диагностические fixtures
docs/                исследования, протоколы и Switch guide
```

## Лицензия и ограничения

Проект не содержит Minecraft, ключи, дампы, Nintendo SDK или проприетарные `material.bin`. Используйте только файлы, законно полученные из собственной копии игры. Никакая часть этого проекта не обходит лицензионные механизмы и не превращает произвольный GLSL в подтверждённый NVN-материал Minecraft.

[1]: docs/RESEARCH-2026-08.md "Актуальный статус пользовательских RenderDragon-шейдеров на Nintendo Switch"
[2]: https://github.com/veka0/lazurite/issues/6 "Lazurite issue #6 — broken textures on Vulkan"
[3]: https://switch.hacks.guide/extras/game_modding.html "NH Switch Guide — Game modding with LayeredFS"
