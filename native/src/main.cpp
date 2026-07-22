// Minecraft Shader Studio native CLI
// Author: Dimasick-git
#include "mss/pack.hpp"
#include <iostream>
#include <stdexcept>

namespace {
void usage(){std::cout<<"Minecraft Shader Studio 0.2.0\nUsage:\n  minecraft-shader-studio version\n  minecraft-shader-studio validate <pack>\n  minecraft-shader-studio plan <pack> <title-id>\n";}
}
int main(int argc,char** argv){
    try{
        if(argc<2){usage();return 1;}
        const std::string command=argv[1];
        if(command=="version"){std::cout<<"0.2.0\n";return 0;}
        if(command=="validate" && argc==3){mss::validate_pack(argv[2]);const auto m=mss::load_manifest(argv[2]);std::cout<<"OK: "<<m.name<<" "<<m.version.str()<<"\n";return 0;}
        if(command=="plan" && argc==4){mss::validate_pack(argv[2]);if(!mss::is_title_id(argv[3]))throw std::runtime_error("invalid title id");const auto m=mss::load_manifest(argv[2]);std::cout<<"atmosphere/contents/"<<argv[3]<<"/romfs/"<<m.materials_destination.generic_string()<<"\n";return 0;}
        usage();return 1;
    }catch(const std::exception& e){std::cerr<<"error: "<<e.what()<<'\n';return 2;}
}
