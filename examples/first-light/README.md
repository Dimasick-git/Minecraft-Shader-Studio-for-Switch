# First Light — контрольный Sky-шейдер для Switch/Vulkan

`first-light` — минимальный пример для материала `Sky`. Он сохраняет простую геометрию ванильного неба и добавляет один параметр `FIRST_LIGHT_STRENGTH`, усиливающий градиент зенита. В отличие от `texture-probe`, пример не использует семплеры; поэтому он годится как **первый контрольный тест пути `material.bin → LayeredFS → Sky`**, но не доказывает работу текстурных материалов.

> Сборка сообщает только `built-and-inspected`. `hardware-verified` — ручной результат проверки на вашей Switch. Сначала рекомендуется выполнить [`../texture-probe`](../texture-probe/README.md), потому что текстурный Vulkan-путь остаётся наиболее важным открытым риском.

## Подготовка

1. Установите зависимости MSS и скачайте host-`shaderc` с BGFX headers:

   ```bash
   python -m pip install -e .
   python3 scripts/fetch_toolchain.py
   ```

2. Из RomFS **своей** Switch-версии Minecraft возьмите:

   ```text
   renderer/materials/Sky.material.bin
   ```

3. Убедитесь, что baseline принадлежит Switch/Vulkan и сохраните его hash:

   ```bash
   mss material inspect /путь/к/Sky.material.bin
   ```

Файлы из вашей игры не коммитятся: при сборке MSS копирует baseline только в игнорируемую `vanilla/` внутри данного example. Открытые reference-материалы, которые можно скачать через `fetch_toolchain.py --reference-merge`, не являются заменой Switch baseline.

## Сборка

```bash
mss compile examples/first-light \
  -o examples/first-light/materials \
  --shaderc toolchains/bin/shadercRelease \
  --baseline /путь/к/Sky.material.bin \
  -d "FIRST_LIGHT_STRENGTH 0.35"
```

После этого зафиксируйте структурную проверку отдельной командой:

```bash
mss material compare \
  --baseline /путь/к/Sky.material.bin \
  --candidate examples/first-light/materials/Sky.material.bin
```

`FIRST_LIGHT_STRENGTH 0.0` отключает только цветовой твик и подходит для A/B-проверки. Положительный `compatible: true` означает, что имя, format version, `Vulkan`, стадии и варианты материала сохранены; он не оценивает изображение на консоли.

## Установка и безопасный тест

```bash
mss build examples/first-light \
  --minecraft-version ВАША_ВЕРСИЯ \
  --atmosphere-version ВАША_ВЕРСИЯ \
  --allow-untested
```

Распакуйте архив в корень SD-карты согласно [Switch guide](../../docs/wiki/SWITCH_GUIDE.md). Если игра не запускается, удерживайте `L` при старте для отключения LayeredFS-модов, затем удалите последний overlay. До первой проверки на железе не распространяйте результат как рабочий Switch-пак.

## Ограничения

| Вопрос | Статус |
|---|---|
| Сохранение Vulkan и основных material metadata | Проверяется MSS автоматически при `--baseline`. |
| Реальное отображение неба на Switch | Требует ручного наблюдения. |
| Семплеры и текстуры Vulkan | Не проверяются этим примером; используйте `texture-probe`. |
| Поддержка других версий Minecraft | Нужен baseline из RomFS соответствующей версии. |

Контекст и публичные источники: [актуальное исследование Switch/Vulkan](../../docs/RESEARCH-2026-08.md).
