# Исследование: NVN или Vulkan? Полная картина шейдеров Minecraft Bedrock на Nintendo Switch

*Дата: 23 июля 2026. Статус: актуально для Bedrock 1.26.x, Atmosphère 1.11.2.*

## TL;DR — Вердикт

**Minecraft Bedrock на Nintendo Switch загружает шейдеры Vulkan (SPIR-V), а не NVN.**
Уверенность: очень высокая, подтверждено несколькими независимыми источниками.

- Тег платформы в реальных `material.bin` со Switch — `Vulkan`.
- `Nvn` — зарезервированный тег «на будущее»: ни одна вышедшая версия игры его не использует.
- Публичного компилятора NVN-шейдеров не существует (NDA Nintendo), а NVN-бэкенд bgfx — заглушка.
- **Практический вывод для проекта: основной пайплайн — Vulkan/SPIR-V через lazurite + bgfx shaderc. NVN-трек — исследовательский (roadmap R4).**

## 1. Как устроен RenderDragon на Switch

RenderDragon — движок Minecraft Bedrock, использующий шейдерную инфраструктуру bgfx.
Скомпилированные шейдеры лежат в контейнерах `*.material.bin` (по одному на материал,
внутри — варианты шейдеров под флаги + render state + метаданные).

Платформы шейдеров в формате material.bin:

| Платформа (тег) | Устройства | Формат байткода |
| :--- | :--- | :--- |
| `Direct3D_SM40/50/60/65` | Windows | DXBC/DXIL |
| `ESSL_100/300/310` | Android | GLSL ES |
| `Metal` | iOS / iPadOS / macOS | MSL |
| **`Vulkan`** | **Nintendo Switch (текущие версии)** | **SPIR-V** |
| `Nvn` | «Switch (future)» — зарезервировано, не используется | Maxwell ISA |
| `PSSL` | PlayStation | PSSL |

RenderDragon появился на Switch в **Bedrock 1.18.30 (апрель 2022)**. С этого момента
старые GLSL-шейдерпаки (.mcpack с исходниками) перестали работать — единственный путь
кастомных шейдеров: подмена `material.bin`.

## 2. Доказательства

1. **MaterialBinTool (ddf8196)** — README прямо перечисляет:
   *«Currently supported platforms: ESSL (Android), Direct3D (Win10), Metal (iOS), **Vulkan (Nintendo Switch)**»*.
   → https://github.com/ddf8196/MaterialBinTool

2. **Lazurite (veka0), docs/platforms.md** — таблица платформ: `Vulkan` → *Switch*;
   `Nvn` → *Switch (future)*. В коде (`platform.py`) у `Nvn` нет ветки компиляции вообще,
   у `Vulkan` — профиль `spirv` в shaderc.
   → https://veka0.github.io/lazurite/ и https://github.com/veka0/lazurite

3. **Документация сообщества RenderDragon-шейдеров (devendrn)**:
   *«RenderDragon runs on DirectX (Windows), OpenGL ES (Android), Metal (iOS/macOS) and **Vulkan (Nintendo Switch builds)**»*.
   → https://devendrn.github.io/renderdragon-shaders/docs/start.html

4. **bgfx (upstream)**: `renderer_nvn.cpp` — заглушка с нулевыми шейдерами;
   `BGFX_CONFIG_RENDERER_VULKAN` включён по умолчанию для NX; issue #1949 — автор bgfx:
   *«There is no full NVN renderer that I know of»*; issue #2221 (открыт до сих пор) —
   «Implement Deko3D as NVN renderer», т.е. NVN так и не реализован.
   → https://github.com/bkaradzic/bgfx/issues/1949 , https://github.com/bkaradzic/bgfx/issues/2221

5. **Lazurite issue #6** — сообщество сравнивает «vanilla materials **from switch**» с
   собранными lazurite: реальные дампы со Switch — Vulkan/SPIR-V. Там же зафиксирован
   известный баг: `s_MatTexture` некорректно работал на Vulkan (Switch) в сборках
   lazurite на 1.21.101+ — при работе проверять на актуальной версии.
   → https://github.com/veka0/lazurite/issues/6

## 3. Почему NVN-путь публично невозможен (пока)

- Компилятор GLSL → Maxwell ISA для NVN входит в закрытый Nintendo SDK (NDA).
- Открытый `uam` (deko3d/devkitPro) компилирует шейдеры для **homebrew** (dksh-контейнеры),
  но это не формат, который принимает retail-игра, и никто не подтвердил загрузку таких
  блобов RenderDragon'ом.
- В material.bin со Switch NVN-секций нет — игре просто нечем их грузить (bgfx NVN — заглушка).

Итог: NVN-инструментарий в MSS (`mss nvn ...`) — легитимное исследование (инспекция,
graft, выравнивание), но **не** путь доставки шейдеров в Minecraft сегодня. Это
зафиксировано в roadmap как R4 с честной формулировкой «prove or reject».

## 4. Рабочий пайплайн сегодня (Vulkan/SPIR-V)

Инструменты:

| Инструмент | Роль | Установка |
| :--- | :--- | :--- |
| **lazurite** | распаковка/сборка/merge material.bin, проектная система | `pip install lazurite` (PyPI 0.8.4) |
| **bgfx shaderc (форк bgfx-mcbe)** | компиляция bgfx SC-исходников в SPIR-V | бинарники: https://github.com/veka0/bgfx-mcbe/releases/tag/binaries |
| **MaterialBinTool** | альтернатива для распаковки/сборки (Java) | https://github.com/ddf8196/MaterialBinTool |
| **mcbe-shader-codebase** | восстановленные ванильные исходники шейдеров по версиям | https://github.com/veka0/mcbe-shader-codebase |
| **RenderDragonSourceCodeInv** | курируемые SC-исходники + скрипты сборки | https://github.com/SurvivalApparatusCommunication/RenderDragonSourceCodeInv |

Процесс:

1. Дамп romfs своей копии игры (nxdumptool/DBI) → извлечь ванильные `*.material.bin`.
2. `lazurite unpack` дампов → анализ; исходники брать из mcbe-shader-codebase.
3. Проект lazurite: `project.json` с `"platforms": ["Vulkan"]`, ванильные Switch-дампы
   как merge source.
4. `lazurite build --shaderc <bgfx-mcbe shaderc>` → SPIR-V → `material.bin` c тегом Vulkan.
5. Упаковка LayeredFS (это делает `mss build`) и установка на консоль (см. ниже).

Замечание: популярные шейдеры (Newb X Legacy и производные) официально собираются под
Android/Windows/iOS — **Switch-таргет не публикуют**, но их исходники + lazurite позволяют
собрать Vulkan-вариант самостоятельно. Это и есть ниша Minecraft Shader Studio.

> **Верификация (23.07.2026):** пайплайн проверен end-to-end в изолированной среде:
> lazurite 0.8.4 + shaderc bgfx-mcbe (1.18.121) + сериализованные ванильные материалы
> 1.26.10 → собран `Sky.material.bin` (format version 25, платформа **Vulkan**, 4 варианта
> шейдера: Vertex/Fragment × Instancing On/Off). Интеграция: команда `mss compile`,
> рабочий пример: `examples/first-light/`.

## 5. Установка на консоль

- **Title ID (Bedrock): `0100D71004694000`** (eShop «Minecraft», Mojang, релиз 20.06.2018).
  Подтверждение: tinfoil.io/Title/0100D71004694000 и структура сейвов Checkpoint
  (`0x0100D71004694000 Minecraft`) в гайдах GBAtemp.
- `01006BD001E06000` — **легаси** «Minecraft: Nintendo Switch Edition» (2017, мёртв с 2018,
  RenderDragon там нет — не наша цель).
- Minecraft **Preview на Switch не существует** (Preview доступен на Xbox/iOS/Windows/PS).
- Путь LayeredFS: `sdmc:/atmosphere/contents/0100D71004694000/romfs/renderer/materials/`.
  ⚠️ Точная внутренняя структура romfs требует сверки с дампом **своей** копии игры —
  ожидаемый путь `renderer/materials/*.material.bin` (как на других платформах), но это
  надо один раз подтвердить дампом (открытый вопрос №1).
- Отключение модов на один запуск: держать **L** при старте игры.
- **Риски бана**: модификация онлайн-игр — категория риска (Minecraft ходит в Xbox Live).
  Стандартная практика: emuMMC + полностью оффлайн (dns-mitm), онлайн — только с чистого
  sysNAND без LayeredFS. → https://nx.eiphax.tech/ban
- **Switch 2 (июнь 2025): CFW нет** (на июль 2026 есть только userland-эксплойт Gezine,
  без LayeredFS) — целевая платформа проекта: Switch 1 на Atmosphère 1.11.2 (FW 22.5.0).

## 6. Vibrant Visuals

Официальный графический апгрейд Mojang (deferred rendering, июнь 2025) **не поддерживается
на Switch и Switch 2** — в списке устройств только Xbox, PlayStation, Android, iOS, PC.
Switch остаётся на forward-пайплайне → наши моды подменяют форвардные материалы.
Для проекта это плюс: на Switch кастомные шейдеры — единственный способ «прокачать» картинку.
→ https://www.minecraft.net/en-us/vibrant-visuals-update

## 7. Рекомендации для Minecraft Shader Studio

1. **Vulkan/SPIR-V — основной пайплайн** (`mss vulkan`, интеграция lazurite): именно он
   даёт работающие шейдеры на консоли. NVN (`mss nvn`) — экспериментальный R&D-трек (R4).
2. Использовать правильный Title ID по умолчанию: `0100D71004694000`.
3. Схема версий Bedrock: в 2026 ченджлоги Mojang используют шорт-нотацию «26.34», а
   движок и теги bedrock-samples — полную (`v1.26.34.x`). Проект хранит **полную форму
   `1.26.34`**, детектор версий нормализует обе нотации. Актуально на 23.07.2026:
   релиз **1.26.34** (samples-репозиторий отстаёт на v1.26.30.5), preview 1.26.50.
4. Не коммитить и не распространять ванильные `material.bin` (собственность Mojang) —
   только собственные исходники и собранные из них паки. Дампы пользователь делает сам
   со своей копии игры.
5. Следующий практический шаг: собрать через lazurite минимальный Vulkan-пак
   (например, модификация неба/тумана на базе mcbe-shader-codebase) и проверить на
   консоли (Erista/Mariko) по протоколу R2.

## 8. Открытые вопросы

1. Подтвердить дампом точный путь материалов в romfs Switch-версии (ожидается
   `renderer/materials/`).
2. Проверить актуальность бага `s_MatTexture` (lazurite #6) на 1.26.x.
3. Выяснить, отличается ли формат material.bin 1.26.x от 1.21.x (version у контейнера),
   и зафиксировать поддерживаемые версии в matrix.json по результатам теста на железе.
4. Найти/собрать референсные Switch-паки других авторов для сравнения (публичных репо
   с готовыми Atmosphere-структурами не обнаружено — ниша свободна).

## Источники

- https://github.com/ddf8196/MaterialBinTool — платформы material.bin
- https://veka0.github.io/lazurite/ — документация lazurite, таблица платформ
- https://github.com/veka0/lazurite/issues/6 — Switch-дампы = Vulkan; баг s_MatTexture
- https://github.com/veka0/bgfx-mcbe — патченный shaderc для MCBE
- https://github.com/veka0/mcbe-shader-codebase — ванильные исходники шейдеров
- https://github.com/SurvivalApparatusCommunication/RenderDragonSourceCodeInv — SC-исходники
- https://github.com/devendrn/newb-x-mcbe и https://devendrn.github.io/renderdragon-shaders/ — экосистема шейдеров
- https://github.com/bkaradzic/bgfx/issues/1949 , https://github.com/bkaradzic/bgfx/issues/2221 — статус NVN в bgfx
- https://tinfoil.io/Title/0100D71004694000 — Title ID Bedrock на Switch
- https://www.digminecraft.com/version_history/nintendo_switch/release_1_18_30.php — RenderDragon на Switch (1.18.30)
- https://www.minecraft.net/en-us/vibrant-visuals-update — устройства Vibrant Visuals (без Switch)
- https://nx.eiphax.tech/ban — риски бана при CFW
- https://gbatemp.net/threads/how-to-install-custom-maps-texture-packs-and-addons-for-minecraft-bedrock-for-nintendo-switch.542742/ — модификация Bedrock на Switch (Checkpoint, title ID)

---
*Исследование выполнено автономным мейнтейнером проекта. Владелец: Dimasick-git.*
