# Roadmap

## R0 — Foundation ✅

Строгая проверка manifest, детерминированная LayeredFS-структура, хеши, матрица совместимости, CI и безопасная подготовка toolchain реализованы.

## R1 — Vulkan material workflow ✅

Lazurite-проекты для профиля `switch`, обязательный ванильный Vulkan baseline, `material inspect/compare`, `texture-probe`, автоматизация RomFS/LayeredFS и smoke-артефакты GitHub Actions реализованы.

## R2 — Hardware validation

Следующая обязательная веха — контролируемый тест на собственной Switch: `SunMoon` texture probe, проверка handheld/docked, rollback удержанием `L`, измерение времени кадра и сохранение отчёта с версиями игры, Atmosphère, Lazurite и `shaderc`.

## R3 — Versioned regression fixtures

После появления законно полученных пользователем baseline-отчётов проект сможет добавить обезличенные metadata fixtures и регрессионные проверки format version, platform tag, stages и variants для конкретных версий игры.

> MSS не будет объявлять поддержку конкретной версии Minecraft, пока она не прошла воспроизводимую аппаратную проверку.

Автор: **Dimasick-git**.
