# First Light — первый тестовый Vulkan-шейдер для Switch

Минимальный рабочий пример пайплайна MSS: ванильное небо Minecraft Bedrock с
одним аккуратным твиком — усиленным градиентом зенита («первый свет»).
Собирается в `Sky.material.bin` с платформой **Vulkan (SPIR-V)** — именно такой
формат загружает Switch-версия игры (вердикт: [docs/RESEARCH-2026-07.md](../../docs/RESEARCH-2026-07.md)).

Пайплайн проверен end-to-end 23.07.2026: `lazurite build` + shaderc (bgfx-mcbe)
успешно собирают этот проект в material.bin с тегом Vulkan (format version 25,
4 варианта шейдера: Vertex/Fragment × Instancing On/Off).

## Состав

```
first-light/
├─ project.json      конфиг lazurite-проекта (профили switch и android)
├─ shader.json       манифест MSS-пака (для mss build)
├─ Sky/              исходники материала неба (bgfx SC)
│  ├─ config.json    маппинг флагов (Instancing → INSTANCING) и файлов
│  ├─ vertex.sc      ванильная логика + твик FIRST_LIGHT_STRENGTH
│  ├─ fragment.sc    ванильный passthrough
│  └─ varying.def.sc атрибуты и varyings как в ванилле
├─ vanilla/          сюда кладутся ванильные материалы (merge source) — НЕ коммитить!
└─ include/          сюда кладутся хедеры bgfx (bgfx_shader.sh) — скачиваются скриптом
```

## Подготовка (один раз)

1. Python 3.10+ и lazurite:
   ```bash
   pip install lazurite
   ```
2. Тулчейн (shaderc + хедеры bgfx) и, опционально, сериализованные ванильные
   материалы (1.26.10, из dev-релиза newb-shader):
   ```bash
   python3 scripts/fetch_toolchain.py --vanilla
   ```
3. **Рекомендуется для финальной сборки:** ванильные материалы из дампа *вашей*
   копии игры (nxdumptool/DBI → RomFS → `renderer/materials/`). Положите
   `Sky.material.bin` из дампа в `vanilla/` — merge пройдёт по вашей версии игры.
   Ванильные файлы (как .bin, так и .material.json) — собственность Mojang,
   **не коммитьте и не распространяйте их** (папка vanilla/ в .gitignore).

## Сборка

Из корня репозитория:

```bash
# компиляция под Switch (Vulkan) прямо в папку пака
mss compile examples/first-light -o examples/first-light/materials \
    --shaderc toolchains/bin/shadercRelease

# упаковка LayeredFS-архива (title ID Bedrock подставляется по умолчанию)
mss build examples/first-light --minecraft-version 1.26.34 \
    --atmosphere-version 1.11.2 --allow-untested
```

Результат: `dist/mss-first-light-0.1.0.zip` со структурой
`atmosphere/contents/0100D71004694000/romfs/renderer/materials/Sky.material.bin` —
распаковать в корень SD-карты. Установка и риски: [docs/wiki/SWITCH_GUIDE.md](../../docs/wiki/SWITCH_GUIDE.md).

Проверка на Android-устройстве (без консоли): профиль `--profile android`
собирает ESSL-вариант, который можно подложить через MaterialBinLoader.

## Твик

Сила эффекта задаётся макросом (по умолчанию 0.35):

```bash
mss compile examples/first-light -o ... -d "FIRST_LIGHT_STRENGTH 0.6"
```

`FIRST_LIGHT_STRENGTH 0.0` даёт полностью ванильное небо — удобно для
A/B-проверки, что пайплайн не ломает картинку сам по себе.

## Известные ограничения

- Метаданные из dev-релиза newb-shader соответствуют 1.26.10; для точного
  соответствия вашей версии игры используйте материалы из собственного дампа.
- Сообщалось о баге семплеров (`s_MatTexture`) на Vulkan в сборках lazurite
  (veka0/lazurite#6, эпоха 1.21.101). Материал Sky семплеры не использует,
  поэтому пример от него не зависит — но проверка на железе обязательна.
- Первый запуск на консоли — по протоколу R2 (см. ROADMAP): сначала пустой
  тест `FIRST_LIGHT_STRENGTH 0.0`, потом эффект.
