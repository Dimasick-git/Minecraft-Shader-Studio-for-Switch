# Актуальный статус пользовательских RenderDragon-шейдеров на Nintendo Switch

**Дата проверки:** 11 августа 2026 года.  
**Статус:** исследование публичных индексируемых исходников, репозиториев, документации и обсуждений; не является аппаратным отчётом.

## Вывод

На момент исследования **не найден воспроизводимый публичный проект с аппаратно подтверждённой работой современного текстурного пользовательского RenderDragon/Vulkan-шейдера на Nintendo Switch**. Публичная экосистема даёт необходимые составные части: Lazurite распознаёт `Vulkan` как платформу Switch, `bgfx-mcbe shaderc` компилирует BGFX SC на host-машине, а LayeredFS Atmosphère подменяет файлы RomFS при запуске из CFW. Однако эти факты не доказывают, что конкретный пересобранный текстурный `material.bin` будет корректно загружен игрой на консоли. [1] [2] [3] [4]

> **Инженерная позиция MSS:** успешная сборка — это `built-and-inspected`, но не `hardware-verified`. Второй статус должен появляться только после контролируемого запуска на принадлежащей пользователю Switch.

## Что подтверждено

| Компонент | Подтверждённый факт | Значение для MSS |
|---|---|---|
| Платформа материала | Документация Lazurite сопоставляет platform tag `Vulkan` с Switch; `Nvn` также указан для Switch, но отмечен как удалённый в 1.26.40.30. [1] | Единственный поддерживаемый практический таргет MSS — `Vulkan`. NVN остаётся исследовательским треком и не должен выдаваться за способ загрузки Minecraft. |
| Формат и версии | Lazurite документирует format version 23 от Bedrock 1.26.0.2 и version 25 от 1.26.10.4. При этом одинаковый номер формата не всегда означает идентичную структуру между эпохами игры. [5] | Нельзя «переводить» готовый материал между версиями и ожидать работы. Нужен baseline из RomFS той же версии игры. |
| Компиляция | `lazurite build` поддерживает profile, `shaderc`, defines и merge source; документация рекомендует `shaderc` из `veka0/bgfx-mcbe`. [2] [6] | MSS использует Lazurite как основной компилятор и сохраняет project/profile workflow. |
| Доставка файлов | LayeredFS подменяет ресурсы игры из `sd:/atmosphere/contents/<title_id>/romfs/…` при запуске в CFW. Руководство также описывает отключение модов удержанием `L` при старте. [4] | Установка `material.bin` возможна без перепаковки игры; rollback должен входить в каждый тестовый протокол. |

## Главный непроверенный участок: текстуры в Vulkan

Открытая задача Lazurite #6 сообщает, что `s_MatTexture` некорректно работает в Vulkan-материалах, собранных Lazurite, хотя ранее пользовательский отчёт указывал на работу через MaterialBinTool. Сопровождающий прямо предлагает сравнить ванильные Switch-материалы с пересобранными и допускает как изменения игры, так и регрессию в патчах `shaderc`. На дату исследования задача открыта. [7]

Это ограничение существенно: эффект без текстуры может показать, что LayeredFS-путь и базовый Vulkan blob загрузились, но не подтверждает, что серьёзные материалы, включая `RenderChunk`, будут работать. По этой причине MSS содержит отдельный `examples/texture-probe`: минимальный `SunMoon`-материал с `s_SunMoonTexture`, который позволяет получить однозначное наблюдение прежде, чем трогать сложные terrain-шейдеры.

| Результат `texture-probe` на Switch | Обоснованный вывод | Нельзя заключать |
|---|---|---|
| Обычная текстура Sun/Moon и контролируемый cyan-сдвиг | Текстурный binding этого конкретного baseline и этой версии игры прошёл через сборку и загрузился на устройстве. | Что `RenderChunk`, PBR или все версии Bedrock совместимы. |
| Чёрная/белая/отсутствующая текстура либо crash | Есть полезный репродуктор текстурной проблемы либо несовпадение baseline/версии. | Что причина наверняка в Lazurite, а не в пути LayeredFS или неподходящем дампе. |
| Команда собрала `.material.bin`, но тест не запускался | Материал только структурно подготовлен. | Что шейдер «работает на Switch». |

## Что уже делало сообщество — и почему этого недостаточно

Старый MaterialBinTool умел распаковывать, упаковывать и собирать `.sc`-источники, но в его публичном README перечислены только ESSL, Direct3D и Metal; Vulkan/Switch там не заявлены. Он полезен как историческая контрольная точка для сравнения артефактов, но не как современный Switch toolchain. [8]

Активный проект Newb X Legacy показывает, что community workflow на Lazurite жизнеспособен для Android, Windows, iOS и merged-профилей. Но публичная документация этого пака не заявляет проверенной Switch/Vulkan-доставки. Следовательно, перенос его проекта на Switch без ванильного Switch baseline был бы неподтверждённой гипотезой. [9]

Репозиторий `mcbe-shader-codebase` предоставляет извлечённые GLSL и реконструированный BGFX SC. Автор предупреждает, что восстановленный код иногда требует ручной коррекции матричных операций и может содержать приближённые macro conditions. Это полезный источник для изучения сигнатур и вариантов, но не «готовый точный исходник» для произвольного `material.bin`. [10]

Наконец, популярные Reddit-посты 2022–2023 о «working shaders on Switch» оказались историческим исключением: автор позднее указал, что обход был исправлен, когда RenderDragon вернулся на Switch. Эти сообщения описывают временное состояние старой версии игры, а не современный Vulkan workflow. [11] [12]

## Что меняет этот репозиторий

MSS больше не предлагает рассматривать выход `mss compile` как достаточный результат. Для профиля `switch` CLI требует `--baseline` с ванильным Switch/Vulkan `.material.bin` из RomFS той же версии игры. MSS временно копирует этот файл только в игнорируемую папку `vanilla/`, выполняет Lazurite-сборку и сопоставляет результат с baseline по имени, format version, платформе `Vulkan`, стадиям и наличию шейдерных вариантов.

Команды ниже создают воспроизводимые диагностические данные без распространения файлов игры:

```bash
mss material inspect /путь/к/SunMoon.material.bin
mss compile examples/texture-probe \
  -o examples/texture-probe/materials \
  --shaderc toolchains/bin/shadercRelease \
  --baseline /путь/к/SunMoon.material.bin
mss material compare \
  --baseline /путь/к/SunMoon.material.bin \
  --candidate examples/texture-probe/materials/SunMoon.material.bin
```

Для автоматических тестов допускается `--unsafe-no-baseline`, но CLI явно маркирует этот режим как `smoke-build-only`; такой результат нельзя устанавливать на Switch. После аппаратного теста следует сохранить версии игры, Atmosphère, Lazurite и `shaderc`, SHA-256 baseline/кандидата и наблюдение. При отрицательном результате эти данные образуют корректный минимальный репродуктор для upstream-задачи Lazurite.

## Границы исследования

Исследование охватывает публично индексируемые GitHub-репозитории и issue tracker, документацию Lazurite и Switch homebrew, а также доступные Reddit-обсуждения. Закрытые Discord-серверы, приватные чаты и неиндексируемые публикации не могли быть проверены. Поэтому отсутствие найденного проекта не означает, что ни у кого нет закрытого решения; оно означает, что **публичного, проверяемого и современного рецепта я не нашёл**.

## References

[1]: https://veka0.github.io/lazurite/platforms/ "Lazurite — Platforms"
[2]: https://veka0.github.io/lazurite/commands/ "Lazurite — Commands"
[3]: https://github.com/veka0/bgfx-mcbe/releases/tag/binaries "veka0/bgfx-mcbe — binaries"
[4]: https://switch.hacks.guide/extras/game_modding.html "NH Switch Guide — Game modding with LayeredFS"
[5]: https://veka0.github.io/lazurite/supported_versions/ "Lazurite — Supported Versions"
[6]: https://veka0.github.io/lazurite/project/ "Lazurite — Projects"
[7]: https://github.com/veka0/lazurite/issues/6 "Lazurite issue #6 — broken textures on Vulkan"
[8]: https://github.com/Quoty0/MaterialBinTool-EnglishTranslated "MaterialBinTool English Translated"
[9]: https://github.com/devendrn/newb-x-mcbe "Newb X Legacy"
[10]: https://github.com/veka0/mcbe-shader-codebase "MCBE Shader Codebase"
[11]: https://www.reddit.com/r/MinecraftSwitch/comments/znquwe/i_found_working_shaders_for_minecraft_nintendo/ "Reddit — I FOUND WORKING SHADERS FOR MINECRAFT NINTENDO SWITCH"
[12]: https://www.reddit.com/r/minecraftshaders/comments/10m7yej/the_render_dragon_graphics_engine_got_disabled_on/ "Reddit — Render Dragon disabled on Switch"
