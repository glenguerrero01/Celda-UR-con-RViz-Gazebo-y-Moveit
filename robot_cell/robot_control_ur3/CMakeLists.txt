cmake_minimum_required(VERSION 3.8)
project(robot_control_ur3)

find_package(ament_cmake REQUIRED)

# Instalar directorios de recursos
foreach(dir IN ITEMS launch urdf config)
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${dir}")
    install(
      DIRECTORY ${dir}
      DESTINATION share/${PROJECT_NAME}
      PATTERN "*~" EXCLUDE
    )
  endif()
endforeach()

ament_package()
