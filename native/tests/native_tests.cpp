// Minecraft Shader Studio native tests
// Author: Dimasick-git
#include "mss/pack.hpp"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
int main(){
    assert(mss::Version::parse("26.33").str()=="26.33");
    bool rejected=false;try{(void)mss::Version::parse("v26.33;rm");}catch(...){rejected=true;}assert(rejected);
    assert(mss::is_title_id("0123456789ABCDEF")); assert(!mss::is_title_id("../BAD"));
    assert(mss::is_safe_relative_path("data/renderer/materials")); assert(!mss::is_safe_relative_path("../../escape"));
    const auto root=std::filesystem::temp_directory_path()/"mss-native-test";std::filesystem::remove_all(root);std::filesystem::create_directories(root/"materials");
    std::ofstream(root/"shader.json")<<R"({"schema":1,"id":"test-pack","name":"Test","version":"0.1.0","author":"Dimasick-git","description":"fixture","materials_destination":"data/materials"})";
    std::ofstream(root/"materials"/"Sky.material.bin")<<"PUBLIC TEST FIXTURE";
    mss::validate_pack(root);const auto manifest=mss::load_manifest(root);assert(manifest.id=="test-pack");
    std::filesystem::remove_all(root);std::cout<<"native tests: OK\n";return 0;
}
