cmake_minimum_required(VERSION 3.16)
project(Lab2 VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Quick)

qt_standard_project_setup()

qt_add_executable(appLab2
    main.cpp
)

qt_add_qml_module(appLab2
    URI Lab2
    VERSION 1.0
    QML_FILES
        Main.qml
    SOURCES
        VaultController.h
        VaultItem.h
)

target_link_libraries(appLab2 PRIVATE Qt6::Quick)