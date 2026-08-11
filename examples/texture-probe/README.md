# Switch Vulkan Texture Probe

`texture-probe` — это **диагностический**, а не декоративный пакет. Он минимально изменяет материал `SunMoon` и читает `s_SunMoonTexture`; тем самым пакет проверяет главный нерешённый риск публичного Vulkan-пайплайна Lazurite: корректно ли на Nintendo Switch сохраняются текстурный binding и семплирование после пересборки `material.bin`.

> Успешная команда `mss compile` означает только `built-and-inspected`. Статус `hardware-verified` можно присвоить исключительно после теста на вашей Switch в CFW. Не публикуйте и не коммитьте ванильные `material.bin` из игры.

## Подготовка baseline

Из RomFS **вашей** установленной Switch-версии Minecraft возьмите ровно один файл:

```text
renderer/materials/SunMoon.material.bin
```

Сначала убедитесь, что это нужный Vulkan-материал и зафиксируйте его hash/format:

```bash
mss material inspect /путь/к/SunMoon.material.bin
```

В отчёте должна быть `"Vulkan"` в `platforms`. Если её нет, файл не подходит для этого примера.

## Сборка

Сначала скачайте совместимый host-`shaderc` и хедеры BGFX:

```bash
python3 scripts/fetch_toolchain.py
```

Затем соберите материал. Опция `--baseline` копирует только ваш `SunMoon.material.bin` в игнорируемую локальную папку `vanilla/`, создаёт результат и проверяет, что у него сохранились имя, format version, Vulkan, стадии и хотя бы один вариант шейдера.

```bash
mss compile examples/texture-probe \
  -o examples/texture-probe/materials \
  --shaderc toolchains/bin/shadercRelease \
  --baseline /путь/к/SunMoon.material.bin \
  -d "TEXTURE_PROBE_STRENGTH 0.25"
```

Для независимого повторного отчёта выполните:

```bash
mss material compare \
  --baseline /путь/к/SunMoon.material.bin \
  --candidate examples/texture-probe/materials/SunMoon.material.bin
```

`compatible: true` является необходимой **структурной** проверкой, однако в JSON намеренно остаётся `hardware_verified: false`.

## Установка и наблюдение

Упакуйте только полученный материал и установите LayeredFS-архив по стандартному пути Atmosphère:

```bash
mss build examples/texture-probe \
  --minecraft-version ВАША_ВЕРСИЯ \
  --atmosphere-version ВАША_ВЕРСИЯ \
  --allow-untested
```

В CFW откройте мир, где виден солнечный или лунный диск. При работающем пути `s_SunMoonTexture` диск должен быть обычной текстурой с мягким cyan-сдвигом. Значение `TEXTURE_PROBE_STRENGTH 0.0` убирает именно цветовой сдвиг и полезно для A/B-проверки.

| Наблюдение на консоли | Интерпретация | Следующее действие |
|---|---|---|
| Текстура солнца/луны видна, есть слабый cyan-сдвиг | `s_SunMoonTexture` загрузился и прошёл через пересобранный Vulkan-материал. | Сохраните JSON `inspect/compare`, точные версии игры, Lazurite и shaderc как аппаратный отчёт. |
| Текстура чёрная, белая, отсутствует либо игра падает | Возможен воспроизводимый текстурный Vulkan-дефект или несовпадение baseline/версии. | Удерживайте `L` при запуске для отключения модов, затем сохраните исходный и собранный файлы локально, запустите `mss material inspect` для обоих и прикрепите отчёты к репродуктору. |
| Нет cyan-сдвига, но текстура нормальная | Материал мог не быть подменён либо strength не дошёл до shaderc. | Проверьте путь `romfs/renderer/materials/SunMoon.material.bin`, SHA-256 в hash manifest пакета и повторите с `TEXTURE_PROBE_STRENGTH 0.8`. |

## Границы теста

Этот пример не доказывает работу `RenderChunk`, теней, PBR или тяжёлых паков. Он намеренно проверяет один простой текстурный material перед сложными шейдерами. Ранние посты 2022–2023 о «рабочих шейдерах» на Switch описывали временное отключение RenderDragon и не применимы к текущему пути Vulkan; подробности и источники приведены в [`docs/RESEARCH-2026-08.md`](../../docs/RESEARCH-2026-08.md).
