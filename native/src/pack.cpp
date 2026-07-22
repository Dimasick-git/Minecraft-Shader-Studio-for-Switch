// Minecraft Shader Studio core
// Author: Dimasick-git
#include "mss/pack.hpp"
#include <algorithm>
#include <charconv>
#include <cctype>
#include <fstream>
#include <regex>
#include <sstream>
#include <stdexcept>

namespace {
std::string read_all(const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("cannot open " + path.string());
    std::ostringstream out; out << file.rdbuf();
    if (!file.good() && !file.eof()) throw std::runtime_error("cannot read " + path.string());
    return out.str();
}
std::string json_string(const std::string& json, std::string_view key) {
    const std::regex expression("\\\"" + std::string(key) + "\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"");
    std::smatch match;
    if (!std::regex_search(json, match, expression)) throw std::runtime_error("missing string field: " + std::string(key));
    return match[1].str();
}
unsigned json_unsigned(const std::string& json, std::string_view key) {
    const std::regex expression("\\\"" + std::string(key) + "\\\"\\s*:\\s*([0-9]+)");
    std::smatch match;
    if (!std::regex_search(json, match, expression)) throw std::runtime_error("missing integer field: " + std::string(key));
    unsigned result{}; const auto value=match[1].str();
    auto [ptr, ec]=std::from_chars(value.data(), value.data()+value.size(), result);
    if (ec != std::errc{} || ptr != value.data()+value.size()) throw std::runtime_error("invalid integer field");
    return result;
}
}

namespace mss {
Version Version::parse(std::string_view input) {
    if (input.empty()) throw std::invalid_argument("empty version");
    Version result; std::size_t start=0;
    while (start < input.size()) {
        const auto end=input.find('.',start); const auto stop=end==std::string_view::npos?input.size():end;
        const auto token=input.substr(start,stop-start);
        if (token.empty() || (token.size()>1 && token.front()=='0')) throw std::invalid_argument("invalid version");
        unsigned part{}; auto [ptr,ec]=std::from_chars(token.data(),token.data()+token.size(),part);
        if (ec!=std::errc{} || ptr!=token.data()+token.size()) throw std::invalid_argument("invalid version");
        result.parts.push_back(part); if(end==std::string_view::npos) break; start=end+1;
    }
    if (result.parts.size()<2 || result.parts.size()>4) throw std::invalid_argument("version needs 2-4 components");
    return result;
}
std::string Version::str() const {
    std::ostringstream out; for(std::size_t i=0;i<parts.size();++i){if(i)out<<'.';out<<parts[i];} return out.str();
}
bool is_safe_relative_path(const std::filesystem::path& path) {
    if (path.empty() || path.is_absolute() || path.has_root_name() || path.has_root_directory()) return false;
    return std::none_of(path.begin(),path.end(),[](const auto& part){return part==".." || part.empty();});
}
bool is_title_id(std::string_view value) {
    return value.size()==16 && std::all_of(value.begin(),value.end(),[](unsigned char c){return std::isxdigit(c)!=0;});
}
PackManifest load_manifest(const std::filesystem::path& pack_directory) {
    const auto json=read_all(pack_directory/"shader.json");
    PackManifest m{json_unsigned(json,"schema"),json_string(json,"id"),json_string(json,"name"),Version::parse(json_string(json,"version")),json_string(json,"author"),json_string(json,"description"),json_string(json,"materials_destination")};
    if(m.schema!=1) throw std::runtime_error("unsupported schema");
    if(m.id.size()<2 || m.id.size()>63 || !std::all_of(m.id.begin(),m.id.end(),[](unsigned char c){return std::islower(c)||std::isdigit(c)||c=='-';})) throw std::runtime_error("invalid pack id");
    if(!is_safe_relative_path(m.materials_destination)) throw std::runtime_error("unsafe materials_destination");
    return m;
}
std::vector<std::filesystem::path> discover_materials(const std::filesystem::path& pack_directory) {
    const auto dir=pack_directory/"materials"; std::vector<std::filesystem::path> result;
    if(!std::filesystem::is_directory(dir)) return result;
    for(const auto& entry:std::filesystem::directory_iterator(dir)) {
        if(entry.is_symlink()) throw std::runtime_error("symlinks are forbidden");
        const auto name=entry.path().filename().string();
        if(entry.is_regular_file() && name.size()>=13 && name.ends_with(".material.bin")) result.push_back(entry.path());
    }
    std::sort(result.begin(),result.end()); return result;
}
void validate_pack(const std::filesystem::path& pack_directory) {
    if(!std::filesystem::is_directory(pack_directory)) throw std::runtime_error("pack directory does not exist");
    (void)load_manifest(pack_directory);
    if(discover_materials(pack_directory).empty()) throw std::runtime_error("no *.material.bin files");
}
} // namespace mss
