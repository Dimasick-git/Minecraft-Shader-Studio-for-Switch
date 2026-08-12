<div align="center">
  <img src="assets/logo.svg" width="112" alt="Minecraft Shader Studio">
  <h1>Minecraft Shader Studio</h1>
  <p><strong>Сборка и проверка экспериментальных RenderDragon/Vulkan-материалов Minecraft Bedrock для Nintendo Switch.</strong></p>
</div>

> **Честный статус:** MSS создаёт и структурно проверяет `Vulkan material.bin`, но не может автоматически подтвердить изображение на консоли. Статус `hardware-verified` появляется только после controlled hardware test с вашей Switch. Публичная проблема с Vulkan texture sampler остаётся известным риском. [1]

## Что поддерживается

| Возможность | Результат |
|---|---|
| Lazurite + `bgfx-mcbe shaderc` | Сборка `material.bin` профиля `switch` с платформой `Vulkan`. |
| User-owned baseline | Сравнение имени, format version, платформы, стадий и вариантов до установки. |
| `overlay extract` / `overlay apply` | Извлечение baseline из локального RomFS-дампа и создание дерева LayeredFS. |
| GitHub Actions | Python-тесты и `smoke-build-only` артефакты без игровых файлов. |

## Быстрый старт

Установите пакет и подготовьте проверенный toolchain. Скрипт закрепляет revision BGFX и проверяет SHA-256 доступного Linux toolchain.

```bash
python -m pip install -e .
python3 scripts/fetch_toolchain.py
mss doctor
```

Затем используйте `SunMoon` как первый реальный тест. Извлеките baseline из RomFS **своей** установленной версии Minecraft; не публикуйте ванильные `.material.bin` и не загружайте их в CI.

```bash
# 1. Извлечь нужный baseline из локального RomFS-дампа.
mss overlay extract /путь/к/romfs_dump -o vanilla -p SunMoon
mss material inspect vanilla/SunMoon.material.bin

# 2. Собрать и структурно проверить texture probe.
mss compile examples/texture-probe \
  -o examples/texture-probe/materials \
  --baseline vanilla/SunMoon.material.bin \
  -d "TEXTURE_PROBE_STRENGTH 0.25"
mss material compare \
  --baseline vanilla/SunMoon.material.bin \
  --candidate examples/texture-probe/materials/SunMoon.material.bin

# 3. Создать содержимое корня SD-карты.
mss overlay apply examples/texture-probe/materials -o sd_output
```

Скопируйте **содержимое** `sd_output/` на SD-карту. Ожидаемый путь — `atmosphere/contents/0100D71004694000/romfs/renderer/materials/SunMoon.material.bin`. LayeredFS зеркалирует путь файла из RomFS; удерживание `L` при запуске временно отключает моды и позволяет выполнить rollback. [2]

| Наблюдение на Switch | Следующее действие |
|---|---|
| Диск Sun/Moon виден с cyan-сдвигом | Сохраните hash, версии игры/Atmosphère/Lazurite/shaderc и отчёты `inspect/compare`. |
| Текстура отсутствует, чёрная/белая либо игра не запускается | Удерживайте `L`, удалите последний overlay и сохраните отчёты как репродуктор. |
| CI собрал файл | Это только `smoke-build-only`; его нельзя устанавливать на Switch. |

После успешного texture probe можно аналогично собрать `examples/first-light`, передав `Sky.material.bin` как `--baseline`.

## GitHub Actions

Каждый push и pull request в `main` запускает Python-тесты и smoke-сборки `first-light`/`texture-probe`. Во вкладке **Actions → CI** можно запустить workflow вручную и скачать артефакты `mss-smoke-*` на 7 дней.

> Артефакты Actions используют открытые reference metadata, не содержат файлов игры и **не являются пакетами для консоли**. Финальная сборка выполняется локально с вашим baseline.

## Основные команды

```text
mss doctor
mss material inspect <material.bin>
mss material compare --baseline <switch.material.bin> --candidate <built.material.bin>
mss overlay extract <romfs_dump> -o <output_dir> [-p SunMoon]
mss overlay apply <materials> -o <sd_root>
mss compile <project> --baseline <switch.material.bin>
mss build <pack> --minecraft-version <v> --atmosphere-version <v> [--allow-untested]
mss validate <pack>
```

## Разработка

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall -q src scripts tests
```

Проект не связан с Mojang, Microsoft, Nintendo или Atmosphère-NX. Используйте только законно полученные файлы своей игры; не публикуйте ключи, RomFS-дампы или ванильные `material.bin`.

## References

[1]: https://github.com/veka0/lazurite/issues/6 "Lazurite issue #6 — broken textures on Vulkan"
[2]: https://switch.hacks.guide/extras/game_modding.html "NH Switch Guide — Game modding with LayeredFS"
