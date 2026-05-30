cmake_minimum_required(VERSION 3.8)
project(robot_description_ur3)

# Paquete puramente de recursos (URDF/Xacro, mallas, modelos SDF, launch, RViz, licencias)
find_package(ament_cmake REQUIRED)

# Instalar directorios SOLO si existen (para no romper en distintos repos)
foreach(dir IN ITEMS launch meshes models rviz urdf worlds LICENSES)
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${dir}")
    install(
      DIRECTORY ${dir}
      DESTINATION share/${PROJECT_NAME}
      PATTERN "*~" EXCLUDE
    )
  endif()
endforeach()

# Instalar archivos sueltos (creditos/licencias), tambien de forma segura
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/CREDITS-THIRDPARTY.md")
  install(
    FILES CREDITS-THIRDPARTY.md
    DESTINATION share/${PROJECT_NAME}
  )
endif()

ament_package()
