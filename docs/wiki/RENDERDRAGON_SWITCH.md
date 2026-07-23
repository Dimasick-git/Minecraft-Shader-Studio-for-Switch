# Разработка шейдеров для Minecraft Bedrock (RenderDragon) на Nintendo Switch

Этот документ содержит техническую информацию о том, как работает графический движок RenderDragon на Nintendo Switch и как разрабатывать для него кастомные шейдеры.

## Архитектура RenderDragon на Switch

RenderDragon — это современный графический движок Minecraft, который заменил старый пайплайн. На Nintendo Switch он использует два основных графических API в зависимости от версии игры:

1.  **NVN (NVIDIA Native)**: Низкоуровневый API от NVIDIA, оптимизированный специально для чипа Tegra X1. Использовался в ранних версиях RenderDragon.
2.  **Vulkan**: Современный кроссплатформенный API. В последних обновлениях Minecraft Bedrock на Switch стал основным для унификации кода с другими платформами.

## Форматы файлов

### 1. .material.bin
Это основной контейнер для материалов в RenderDragon. Он содержит:
- Скомпилированные бинарные шейдеры для разных платформ.
- Описание параметров материала (render states, samplers, inputs).
- Метаданные о вариантах шейдера (flags).

Для работы с этим форматом используйте **MaterialBinTool** или **Lazurite**.

### 2. Бинарные форматы шейдеров
- **Maxwell ISA (NVN)**: Нативный машинный код для GPU NVIDIA Maxwell. Обычно имеет заголовок SPH (Shader Program Header).
- **SPIR-V (Vulkan)**: Промежуточный байт-код, который компилируется драйвером Vulkan на лету.

## Инструментарий

Для полноценной разработки вам понадобятся:

| Инструмент | Назначение |
| :--- | :--- |
| **uam-nvn** | Компиляция GLSL в Maxwell ISA (для NVN) |
| **glslangValidator** | Компиляция GLSL в SPIR-V (для Vulkan) |
| **MaterialBinTool** | Распаковка и сборка `.material.bin` |
| **Lazurite** | Продвинутый анализ и декомпиляция материалов |
| **shader-compiler-rs** | Исследование и декомпиляция Maxwell бинарников |

## Процесс разработки (Workflow)

1.  **Получение оригиналов**: Извлеките `.material.bin` из вашей копии игры (используя дампы или LayeredFS).
2.  **Распаковка**: Используйте `mss unpack` (через Lazurite) для получения исходного кода шейдеров.
3.  **Модификация**: Отредактируйте GLSL код.
4.  **Компиляция**:
    - Для Vulkan: `mss vulkan compile`
    - Для NVN: `mss nvn compile`
5.  **Сборка**: Соберите новый `.material.bin` с помощью `MaterialBinTool`.
6.  **Инъекция**: Поместите готовый файл в `atmosphere/contents/<TitleID>/romfs/renderer/materials/`.

## Полезные ссылки
- [Newb X Legacy](https://github.com/devendrn/newb-x-mcbe) — пример высококачественного шейдера.
- [MCBE Shader Codebase](https://github.com/veka0/mcbe-shader-codebase) — база восстановленного кода ванильных шейдеров.
- [RenderDragon Shader List](https://github.com/DominoKorean/Render-dragon-shader-list) — каталог инструментов и шейдеров.
