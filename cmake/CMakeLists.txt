cmake_minimum_required(VERSION 3.16)
project(omni_app C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Path to the .c file emitted by `omni build app.omni --target c`.
set(OMNI_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/app.c" CACHE STRING "Emitted OmniScript C source")

# Flecs is fetched on first configure when not installed system-wide.
include(FetchContent)
FetchContent_Declare(
  flecs
  GIT_REPOSITORY https://github.com/SanderMertens/flecs.git
  GIT_TAG v4.0.4
)
FetchContent_MakeAvailable(flecs)

add_executable(omni_app ${OMNI_SOURCE})
target_compile_definitions(omni_app PRIVATE OMNI_HAVE_FLECS=1)
target_link_libraries(omni_app PRIVATE flecs)
target_include_directories(omni_app PRIVATE ${flecs_SOURCE_DIR})