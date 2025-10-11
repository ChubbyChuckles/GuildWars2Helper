cmake_minimum_required(VERSION 3.20)
project(gw2helper C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

set(SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR}/src)
set(SOURCES
    ${SRC_DIR}/main.c
    ${SRC_DIR}/gui/gui.c
    ${SRC_DIR}/gui/nk_core.c
    ${SRC_DIR}/render/render.c
    ${SRC_DIR}/utils/utils.c
)

add_executable(${PROJECT_NAME} ${SOURCES})

target_include_directories(${PROJECT_NAME}
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${SRC_DIR}
        ${SRC_DIR}/gui
        ${SRC_DIR}/render
        ${SRC_DIR}/utils
        ${CMAKE_CURRENT_SOURCE_DIR}/scripts/deps/glfw/include
)

if(WIN32)
    set(GLFW_LIB_DIR ${CMAKE_CURRENT_SOURCE_DIR}/scripts/deps/glfw/build/src/Release)
    if(NOT EXISTS ${GLFW_LIB_DIR})
        set(GLFW_LIB_DIR ${CMAKE_CURRENT_SOURCE_DIR}/scripts/deps/glfw/build/src)
    endif()
    target_link_directories(${PROJECT_NAME} PRIVATE ${GLFW_LIB_DIR})
    target_link_libraries(${PROJECT_NAME}
        PRIVATE
            glfw3
            opengl32
            gdi32
            shell32
            user32
    )
else()
    set(GLFW_LIB_DIR ${CMAKE_CURRENT_SOURCE_DIR}/scripts/deps/glfw/build/src)
    target_link_directories(${PROJECT_NAME} PRIVATE ${GLFW_LIB_DIR})
    target_link_libraries(${PROJECT_NAME}
        PRIVATE
            glfw3
            m
            dl
            pthread
    )
    if(APPLE)
        target_link_libraries(${PROJECT_NAME} PRIVATE
            "-framework Cocoa"
            "-framework IOKit"
            "-framework CoreVideo"
            "-framework OpenGL"
        )
    else()
        target_link_libraries(${PROJECT_NAME} PRIVATE GL)
    endif()
endif()
