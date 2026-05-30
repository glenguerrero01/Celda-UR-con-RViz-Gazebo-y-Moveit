from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
import os

def generate_launch_description():
    ur_type = LaunchConfiguration("ur_type")

    pkg_robot_desc = FindPackageShare("robot_description")
    xacro_file = PathJoinSubstitution([pkg_robot_desc, "urdf", "robot_cell_entry.xacro"])
    world_file = PathJoinSubstitution([pkg_robot_desc, "worlds", "cell_world.sdf"])

    # xacro: recuerda poner espacios explícitos
    robot_description = ParameterValue(
        Command(["xacro", " ", xacro_file, " ", "ur_type:=", ur_type]),
        value_type=str,
    )

    # Rutas para gz:
    #   - share_robot_desc: .../install/share/robot_description
    #   - share_root:       .../install/share  (¡IMPORTANTE para model://ur_description y model://robot_description!)
    def launch_setup(context, *args, **kwargs):
        share_robot_desc = FindPackageShare("robot_description").perform(context)
        share_root = os.path.dirname(share_robot_desc)  # sube de .../share/robot_description a .../share

        # Resuelve también ur_description
        share_ur_desc = FindPackageShare("ur_description").perform(context)
        share_root_ur = os.path.dirname(share_ur_desc)

        # Une paths (por si difieren)
        model_path = os.pathsep.join({share_root, share_root_ur, share_robot_desc, share_ur_desc})
        resource_path = model_path  # mismo set para resource/file paths

        return [
            # Clave para model://ur_description y model://robot_description
            SetEnvironmentVariable(name="GZ_SIM_MODEL_PATH", value=model_path),
            # Compatibilidad
            SetEnvironmentVariable(name="GZ_SIM_RESOURCE_PATH", value=resource_path),
            SetEnvironmentVariable(name="GZ_FILE_PATH", value=resource_path),
            SetEnvironmentVariable(name="IGN_FILE_PATH", value=resource_path),

            ExecuteProcess(cmd=["gz", "sim", "-r", world_file], output="screen"),

            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                parameters=[{"robot_description": robot_description}],
                output="screen",
            ),

            ExecuteProcess(
                cmd=[
                    "ros2", "run", "ros_gz_sim", "create",
                    "-name", "robot_cell",
                    "-topic", "/robot_description",
                    "-x", "0", "-y", "0", "-z", "0",
                ],
                output="screen"
            ),



            
        ]

    return LaunchDescription([
        DeclareLaunchArgument("ur_type", default_value="ur30"),
        OpaqueFunction(function=launch_setup),
    ])
