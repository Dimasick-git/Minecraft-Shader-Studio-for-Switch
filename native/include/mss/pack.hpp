#pragma once
// Minecraft Shader Studio
// Author: Dimasick-git
#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

namespace mss {
struct Version {
    std::vector<unsigned> parts;
    static Version parse(std::string_view input);
    [[nodiscard]] std::string str() const;
    auto operator<=>(const Version&) const = default;
};

struct PackManifest {
    unsigned schema{};
    std::string id;
    std::string name;
    Version version;
    std::string author;
    std::string description;
    std::filesystem::path materials_destination;
};

[[nodiscard]] bool is_safe_relative_path(const std::filesystem::path& path);
[[nodiscard]] bool is_title_id(std::string_view value);
[[nodiscard]] PackManifest load_manifest(const std::filesystem::path& pack_directory);
[[nodiscard]] std::vector<std::filesystem::path> discover_materials(const std::filesystem::path& pack_directory);
void validate_pack(const std::filesystem::path& pack_directory);
} // namespace mss
