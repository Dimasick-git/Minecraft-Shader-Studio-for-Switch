cmake_minimum_required(VERSION 3.20)
project(MinecraftShaderStudio VERSION 0.2.0 LANGUAGES CXX)

option(MSS_BUILD_TESTS "Build native tests" ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(mss_core STATIC
    native/src/pack.cpp
)
target_include_directories(mss_core PUBLIC native/include)
target_compile_features(mss_core PUBLIC cxx_std_20)
if(MSVC)
  target_compile_options(mss_core PRIVATE /W4 /WX /permissive-)
else()
  target_compile_options(mss_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

add_executable(minecraft-shader-studio native/src/main.cpp)
target_link_libraries(minecraft-shader-studio PRIVATE mss_core)

install(TARGETS minecraft-shader-studio RUNTIME DESTINATION bin)

if(MSS_BUILD_TESTS)
  enable_testing()
  add_executable(mss_native_tests native/tests/native_tests.cpp)
  target_link_libraries(mss_native_tests PRIVATE mss_core)
  add_test(NAME mss_native_tests COMMAND mss_native_tests)
endif()
