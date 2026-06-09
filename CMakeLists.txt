cmake_minimum_required(VERSION 3.20)

project(TransformerSim
    VERSION     1.0.0
    DESCRIPTION "Single-Phase Transformer Educational Simulator"
    LANGUAGES   CXX
)

# ── C++ standard ──────────────────────────────────────────────────────────────
# STANDARD     : use C++17 features (complex numbers, structured bindings, etc.)
# REQUIRED     : hard-fail if the compiler does not support C++17
# EXTENSIONS   : OFF keeps us strictly standard — no compiler-specific extras
set(CMAKE_CXX_STANDARD          17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS        OFF)

# ── Default build type ────────────────────────────────────────────────────────
# If you run cmake without -DCMAKE_BUILD_TYPE=Release, Debug is assumed.
# Debug    : no optimisation, full debug symbols  → use while developing
# Release  : full optimisation, no debug symbols  → use for distribution
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type" FORCE)
endif()

# ── Output location ───────────────────────────────────────────────────────────
# The compiled .exe lands in build/bin/ instead of scattered through build/
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# ── Source files ──────────────────────────────────────────────────────────────
# GLOB_RECURSE  : find ALL .cpp files inside src/, including subdirectories
# CONFIGURE_DEPENDS : re-run CMake automatically when you add/remove a .cpp file
file(GLOB_RECURSE SRC_FILES CONFIGURE_DEPENDS
    "${CMAKE_SOURCE_DIR}/src/*.cpp"
)

# ── Executable target ─────────────────────────────────────────────────────────
# "transformer_sim" is the name of the .exe that gets built
add_executable(transformer_sim ${SRC_FILES})

# ── Header search path ────────────────────────────────────────────────────────
# PRIVATE means only transformer_sim uses this path (not any linked libraries)
# This is what makes #include "transformer/CircuitSolver.h" resolve correctly
target_include_directories(transformer_sim PRIVATE
    ${CMAKE_SOURCE_DIR}/include
)

# ── Compiler flags ────────────────────────────────────────────────────────────
# -Wall      : enable all standard warnings
# -Wextra    : enable extra warnings beyond -Wall
# -Wpedantic : strict ISO C++ conformance warnings
# -Wshadow   : warn when a variable shadows another (common bug source)
# -O2        : optimisation level 2 — good balance of speed vs compile time
target_compile_options(transformer_sim PRIVATE
    -Wall -Wextra -Wpedantic -Wshadow -O2
)

# ── Status messages printed during cmake configure ────────────────────────────
message(STATUS "Build type : ${CMAKE_BUILD_TYPE}")
message(STATUS "Compiler   : ${CMAKE_CXX_COMPILER}")
message(STATUS "C++ std    : C++${CMAKE_CXX_STANDARD}")
message(STATUS "Output bin : ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}")
