# Разработка шейдеров для Minecraft Bedrock (RenderDragon) на Nintendo Switch

Этот документ содержит техническую информацию о том, как работает графический движок RenderDragon на Nintendo Switch и как разрабатывать для него кастомные шейдеры.

> **Главный факт (проверено, июль 2026):** Switch-сборка Minecraft Bedrock загружает
> шейдеры **Vulkan (SPIR-V)**. Тег `Nvn` в формате material.bin зарезервирован «на будущее»
> и ни одной вышедшей версией игры не используется. Полное исследование с доказательствами:
> [docs/RESEARCH-2026-07.md](../RESEARCH-2026-07.md).

## Архитектура RenderDragon на Switch

RenderDragon — графический движок Minecraft Bedrock, построенный на шейдерной
инфраструктуре bgfx. На Switch он работает **поверх Vulkan** с момента появления
(Bedrock 1.18.30, апрель 2022). Распространённое заблуждение о «раннем NVN-периоде»
не подтверждается: NVN-бэкенд в bgfx — заглушка, а во всех известных дампах
`material.bin` со Switch лежит SPIR-V с тегом платформы `Vulkan`.

Роль NVN сегодня:

- `Nvn` существует в enum платформ формата material.bin (в lazurite помечен как
  «Switch (future)»), но ветки компиляции для него нет ни в одном публичном инструменте.
- Публичный компилятор GLSL → Maxwell ISA для retail-игр отсутствует (NDA Nintendo);
  открытый `uam` из deko3d обслуживает homebrew, а не RenderDragon.

## Форматы файлов

### 1. .material.bin
Основной контейнер материалов RenderDragon. Содержит:
- Скомпилированные бинарные шейдеры (варианты под флаги/пассы).
- Описание параметров материала (render states, samplers, inputs).
- Метаданные о вариантах шейдера (flags).

Для работы с форматом используйте **Lazurite** (основной инструмент) или **MaterialBinTool**.

### 2. Бинарные форматы шейдеров
- **SPIR-V (Vulkan)** — то, что реально грузит Switch-версия: промежуточный байткод,
  драйвер компилирует его на лету.
- **Maxwell ISA (NVN)** — нативный код GPU с заголовком SPH. В Minecraft **не используется**;
  интересен только для исследовательского трека (см. `mss nvn`, roadmap R4).

## Инструментарий

| Инструмент | Назначение |
| :--- | :--- |
| **Lazurite** (`pip install lazurite`) | Проектная система: распаковка, анализ, сборка и merge `material.bin` |
| **bgfx shaderc (форк bgfx-mcbe)** | Компиляция bgfx SC-исходников в SPIR-V — шейдеры MCBE написаны в формате bgfx SC, обычный glslang их не соберёт |
| **MaterialBinTool** (Java) | Альтернативная распаковка/сборка `.material.bin` |
| **mcbe-shader-codebase** | Восстановленные ванильные исходники шейдеров по версиям игры |
| **glslangValidator** | Отдельные SPIR-V эксперименты вне material.bin (`mss vulkan compile`) |
| **uam-nvn / uam** | Экспериментальный NVN-трек (`mss nvn`), к Minecraft сейчас не применим |

## Процесс разработки (Workflow)

1. **Получение оригиналов**: задампите romfs **своей** копии игры (nxdumptool/DBI) и
   извлеките ванильные `*.material.bin`. Не распространяйте их — это собственность Mojang.
2. **Распаковка**: `mss unpack` / `lazurite unpack` для анализа структуры и флагов.
3. **Исходники**: возьмите ванильный код нужного материала из mcbe-shader-codebase
   (или RenderDragonSourceCodeInv) и модифицируйте GLSL/SC.
4. **Сборка под Switch**: проект lazurite с `"platforms": ["Vulkan"]` и ванильными
   Switch-дампами как merge source; компиляция через bgfx-mcbe shaderc (профиль spirv).
5. **Упаковка**: `mss build` соберёт LayeredFS-структуру с правильным Title ID.
6. **Инъекция**: файлы попадают в
   `atmosphere/contents/0100D71004694000/romfs/renderer/materials/`
   (детали и риски: [SWITCH_GUIDE.md](SWITCH_GUIDE.md)).

Известный подводный камень: баг семплера `s_MatTexture` на Vulkan (Switch) в паках,
собранных lazurite (issue veka0/lazurite#6, репортился на 1.21.101) — при переходе на
новые версии игры проверяйте на железе.

## Полезные ссылки
- [Исследование NVN vs Vulkan (июль 2026)](../RESEARCH-2026-07.md) — вердикт и все источники.
- [Lazurite](https://github.com/veka0/lazurite) — основной тулчейн.
- [bgfx-mcbe](https://github.com/veka0/bgfx-mcbe) — патченный shaderc (бинарники в releases).
- [MCBE Shader Codebase](https://github.com/veka0/mcbe-shader-codebase) — база ванильных исходников.
- [RenderDragonSourceCodeInv](https://github.com/SurvivalApparatusCommunication/RenderDragonSourceCodeInv) — курируемые SC-исходники.
- [Newb X Legacy](https://github.com/devendrn/newb-x-mcbe) — эталонный шейдер (официального Switch-таргета нет — собирается самостоятельно).
- [RenderDragon Shader List](https://github.com/DominoKorean/Render-dragon-shader-list) — каталог инструментов и шейдеров.
