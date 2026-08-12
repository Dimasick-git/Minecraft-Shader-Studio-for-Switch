# Установка и откат LayeredFS-пака на Nintendo Switch

Этот документ описывает **только** путь для материалов Minecraft Bedrock через LayeredFS. Он не подтверждает работоспособность конкретного шейдера на устройстве: перед установкой требуются `mss material inspect`, baseline-сравнение и controlled hardware test.

> LayeredFS зеркалирует путь файла внутри RomFS в `sdmc:/atmosphere/contents/<title-id>/romfs/…`. Для Minecraft Bedrock MSS по умолчанию использует Title ID `0100D71004694000`. [1]

## Автоматический путь

Сначала создайте baseline из RomFS **своей** копии игры. Не загружайте дампы или ванильные `.material.bin` в GitHub Actions, issues или releases.

```bash
# Извлечь нужные материалы из локального дампа RomFS.
mss overlay extract /путь/к/romfs_dump -o vanilla_materials -p SunMoon -p Sky

# Проверить и собрать свой material с локальным baseline.
mss material inspect vanilla_materials/SunMoon.material.bin
mss compile examples/texture-probe \
  -o examples/texture-probe/materials \
  --baseline vanilla_materials/SunMoon.material.bin

# Сформировать содержимое корня SD-карты.
mss overlay apply examples/texture-probe/materials -o sd_output
```

После этого в `sd_output` будет создано следующее дерево:

```text
atmosphere/
└── contents/
    └── 0100D71004694000/
        └── romfs/
            └── renderer/
                └── materials/
                    └── SunMoon.material.bin
```

Скопируйте **содержимое** `sd_output/` в корень SD-карты, полностью закройте Minecraft и запустите его снова.

## Безопасный откат

| Ситуация | Действие |
|---|---|
| Игра не запускается после подмены | Удерживайте `L` при запуске, чтобы временно пропустить LayeredFS-моды, затем удалите последний `.material.bin` из overlay. [1] |
| Игра запускается, но эффект отсутствует | Проверьте путь `romfs/renderer/materials/`, SHA-256 из `MSS-MANIFEST.json`, версию baseline и `TEXTURE_PROBE_STRENGTH`. |
| Текстура чёрная/белая или возник crash | Не распространяйте артефакт. Сохраните `material inspect/compare`, версии toolchain и наблюдение как минимальный репродуктор. |

## Ограничения

GitHub Actions создаёт только `smoke-build-only` артефакты из открытых reference metadata. Такие файлы полезны для проверки CI и структуры каталогов, но **не предназначены для установки** на консоль. Финальный пакет должен быть собран локально с baseline из RomFS той же версии игры.

## References

[1]: https://switch.hacks.guide/extras/game_modding.html "NH Switch Guide — Game modding with LayeredFS"
