# Celda-UR-con-RViz-Gazebo-y-Moveit
Repositorio modificado de la celda robótica para preparación de la práctica de laboratorio
## Pick-and-place con UR3 en ROS 2 Jazzy

Simulación de una celda robótica con un **Universal Robots UR3** y un gripper paralelo de 2 dedos, planificada con **MoveIt 2** y simulada en **Gazebo Harmonic**. El proyecto implementa una tarea de pick-and-place entre una mesa con una caja y un basurero como destino.

# Vide funcionamiento y explicación
https://youtu.be/Y9if-JQWyHw

## Recursos usados
- **ROS 2 Jazzy Jalisco**
- **MoveIt 2**
- **Gazebo Harmonic** con `gz_ros2_control`
- **Ubuntu 24.04** (sobre VirtualBox)
- Contenedor Docker para el entorno de desarrollo

## Estructura de paquetes

El proyecto se organiza en tres paquetes ROS 2 dentro del workspace:

```
src/robot_cell/
├── robot_description_ur3/   # URDF del UR3 + celda + meshes + modelos SDF
├── robot_cell_moveit_ur3/   # Configuración de MoveIt para el UR3
└── robot_control_ur3/       # Control en Gazebo (URDF de control + launch + controllers)
```

Cada paquete tiene un rol independiente para mantener separadas las capas de descripción, planificación y control.

## 1. Paquete `robot_description_ur3`

Contiene la descripción geométrica completa de la celda, se modificó la suministrada por el profesor del UR30 al UR3:

- **URDF/Xacro** del UR3 con la celda alrededor (mesa, paredes, pedestal, robot mount, gripper).
- **Mallas** de los componentes en `meshes/`.
- **Modelos SDF independientes** en `models/` para los objetos manipulables:
  - `models/caja/` — cubo de 50×50×50 mm con masa de 150 g, colisión `<box>` y mesh visual.
  - `models/basurero/` — destino estático del pick-and-place, con malla y colisión cilíndrica.
- **Mundo de Gazebo** en `worlds/cell_world.sdf`.

El UR3 se instancia mediante el macro oficial de Universal Robots, configurado para el tipo `ur3` y con todos los parámetros de joint limits, kinematics, physical y visual cargados desde `ur_description`.

El `CMakeLists.txt` instala todos los recursos:

```cmake
foreach(dir IN ITEMS launch meshes models rviz urdf worlds LICENSES)
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${dir}")
    install(DIRECTORY ${dir} DESTINATION share/${PROJECT_NAME})
  endif()
endforeach()
```

## 2. Paquete `robot_cell_moveit_ur3`

Generado con **MoveIt Setup Assistant** a partir del URDF del UR3 + gripper. Configuración:

### Planning Groups

- **`ur_arm`** — grupo del brazo, con los 6 joints `ur3_*` (shoulder_pan, shoulder_lift, elbow, wrist_1, wrist_2, wrist_3). Kinematic solver: `kdl_kinematics_plugin/KDLKinematicsPlugin`.
- **`gripper`** — grupo del gripper con `g_left_joint` (el `g_right_joint` es passive, mimic del izquierdo).

### Robot Poses (en el SRDF)

Poses guardadas para la tarea de pick-and-place:

| Pose | Descripción |
|------|-------------|
| `init` | Pose inicial neutra del robot |
| `home` | Pose elevada de reposo, segura |
| `cerca_B` | Aproximación sobre la caja (pre-grasp y post-grasp) |
| `cerca_C` | Pose de agarre, gripper a ambos lados de la caja |
| `drop_off` | Pose de soltado sobre el basurero |
| `open` / `close` | Apertura y cierre del gripper |

Las poses se capturaron en RViz moviendo el TCP, anotando los valores articulares (en grados desde la pestaña Joints), convirtiéndolos a radianes y añadiéndolos manualmente al SRDF como `<group_state>`.

### Configuración refinada

- **`kinematics.yaml`** — timeout y resolution ajustados (`kinematics_solver_timeout: 0.05`, `kinematics_solver_attempts: 3`) para mejorar la tasa de éxito de IK.
- **`joint_limits.yaml`** — `has_acceleration_limits: true` con valores razonables (5-10 rad/s²) para que `AddTimeOptimalParameterization` pueda calcular el perfil temporal de las trayectorias.

## 3. Paquete `robot_control_ur3`

Paquete basado en el suministrado por el profesor que se encarga de la simulación en Gazebo. Contiene:

### `urdf/robot_cell_control.urdf.xacro`

URDF de simulación que extiende el de descripción añadiendo:

- **Bloque `<ros2_control>`** con `gz_ros2_control/GazeboSimSystem` declarando los 7 joints actuados (6 del UR3 + `g_left_joint` del gripper). Cada joint usa interfaz de comando `position` y reporta `position` y `velocity`. Los `initial_value` definen la pose inicial del robot al arrancar la simulación.
- **Plugin `gz_ros2_control`** que arranca el `controller_manager` dentro de Gazebo:

```xml
<gazebo>
  <plugin filename="libgz_ros2_control-system.so"
          name="gz_ros2_control::GazeboSimROS2ControlPlugin">
    <parameters>$(arg controllers_file)</parameters>
  </plugin>
</gazebo>
```

### `config/controller.yaml`

Define dos controladores que reciben las trayectorias de MoveIt:

- **`ur_arm_controller`** — `joint_trajectory_controller/JointTrajectoryController` para los 6 joints del UR3.
- **`gripper_controller`** — `joint_trajectory_controller/JointTrajectoryController` para `g_left_joint`.

El nombre `ur_arm_controller` coincide con lo definido en el `moveit_controllers.yaml` del paquete `robot_cell_moveit_ur3`.

### `launch/gz_moveit_ur3.launch.py`

Launch unificado que arranca toda la pila en orden con `TimerAction`:

1. Variables de entorno de Gazebo (`GZ_SIM_MODEL_PATH`, etc.) para resolver `package://`.
2. Servidor y cliente de Gazebo Harmonic.
3. `robot_state_publisher` con el URDF procesado por xacro.
4. Spawn del robot en Gazebo desde `/robot_description`.
5. Spawn de la caja como modelo SDF independiente en `(0.3, 0.3, 0.91)`.
6. Spawn del basurero en `(-0.4, -0.15, 1.0)` con rotación `R=1.55` rad.
7. Bridge `ros_gz_bridge` para `/clock`.
8. Spawners de `joint_state_broadcaster`, `ur_arm_controller` y `gripper_controller`.
9. `move_group` de MoveIt.
10. RViz con la configuración generada por Setup Assistant.

## Uso

### Compilar el workspace

```bash
cd ~/ros2_ws
colcon build --packages-select robot_description_ur3 robot_cell_moveit_ur3 robot_control_ur3
source install/setup.bash
```

### Lanzar el sistema completo

```bash
ros2 launch robot_control_ur3 gz_moveit_ur3.launch.py
```

Se abrirán Gazebo (servidor + cliente) y RViz con MoveIt cargado.

### Verificar el estado del sistema

En otra terminal:

```bash
ros2 control list_controllers
```

Debe mostrar tres controladores en estado `active`:

```
joint_state_broadcaster   joint_state_broadcaster/JointStateBroadcaster   active
ur_arm_controller         joint_trajectory_controller/JointTrajectoryController   active
gripper_controller        joint_trajectory_controller/JointTrajectoryController   active
```

### Ejecutar la secuencia de pick-and-place desde RViz

En el panel **MotionPlanning** de RViz:

1. Planning Group `ur_arm`, Goal State `init` → Plan & Execute.
2. Goal State `home` → Plan & Execute.
3. Goal State `cerca_B` → Plan & Execute.
4. Planning Group `gripper`, Goal State `open` → Plan & Execute.
5. Planning Group `ur_arm`, Goal State `cerca_C` → Plan & Execute.
6. Planning Group `gripper`, Goal State `close` → Plan & Execute.
7. Planning Group `ur_arm`, Goal State `cerca_B` → Plan & Execute *(transporte de la caja)*.
8. Goal State `drop_off` → Plan & Execute.
9. Planning Group `gripper`, Goal State `open` → Plan & Execute *(la caja cae en el basurero)*.
10. Planning Group `ur_arm`, Goal State `home` → Plan & Execute.

Para el transporte se recomienda bajar **Velocity Scaling** y **Acceleration Scaling** a `0.05` en el panel de MotionPlanning, para minimizar las fuerzas inerciales sobre la caja.

## Detalles físicos del gripper

El gripper paralelo simulado tiene:

- Dedos con masa 0.25 kg cada uno.
- Joint prismático `g_left_joint` con `effort=500` N y `velocity=0.30` m/s.
- Dedo derecho como **mimic** del izquierdo (movimiento simétrico automático).
- Bloques `<gazebo reference="g_left_finger">` y `<gazebo reference="g_right_finger">` con coeficiente de fricción `mu=3.0` para maximizar el agarre por fricción.

Estos parámetros, junto con `mu=3.0` también en la caja, permiten que el agarre se mantenga durante el transporte sin necesidad de un plugin de unión rígida adicional.

## Capturas

<img width="500"  src="https://github.com/user-attachments/assets/408c7bc1-6e2a-4fb0-b249-acd9d393f767" />

<img width="500" src="https://github.com/user-attachments/assets/ee30653e-baf3-4fcb-a2c6-1640dbca340e" />



