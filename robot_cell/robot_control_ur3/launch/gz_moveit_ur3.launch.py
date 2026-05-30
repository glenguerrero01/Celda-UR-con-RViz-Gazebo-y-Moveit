# Launch grande de simulacion: Gazebo + UR3 + MoveIt + RViz + caja + basurero.
#
# Incluye:
#  - Bridge para los topics del DetachableJoint:
#      /gripper/attach   (ROS -> Gazebo)  para enganchar la caja al gripper
#      /gripper/detach   (ROS -> Gazebo)  para soltar la caja
#  - Detach automatico al arrancar, porque el plugin DetachableJoint crea
#    la union por defecto al iniciar (la caja arrancaria pegada al brazo).

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    SetEnvironmentVariable,
    OpaqueFunction,
    TimerAction,
    IncludeLaunchDescription,
    ExecuteProcess,
)
from launch_ros.actions import SetParameter, Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
import os


def generate_launch_description():
    ur_type = LaunchConfiguration("ur_type")

    pkg_robot_desc = FindPackageShare("robot_description_ur3")
    pkg_robot_control = FindPackageShare("robot_control_ur3")
    pkg_moveit = FindPackageShare("robot_cell_moveit_ur3")

    xacro_file = PathJoinSubstitution([pkg_robot_control, "urdf", "robot_cell_control.urdf.xacro"])

    robot_description = ParameterValue(
        Command(["xacro", " ", xacro_file, " ", "ur_type:=", ur_type]),
        value_type=str,
    )

    def launch_setup(context, *args, **kwargs):
        share_robot_desc = FindPackageShare("robot_description_ur3").perform(context)
        share_root = os.path.dirname(share_robot_desc)
        share_ur_desc = FindPackageShare("ur_description").perform(context)
        share_root_ur = os.path.dirname(share_ur_desc)

        model_path = os.pathsep.join([share_root, share_root_ur, share_robot_desc, share_ur_desc])

        os.environ["GZ_SIM_MODEL_PATH"] = model_path
        os.environ["GZ_SIM_RESOURCE_PATH"] = model_path
        os.environ["GZ_FILE_PATH"] = model_path
        os.environ["IGN_FILE_PATH"] = model_path

        world_path = os.path.join(share_robot_desc, "worlds", "cell_world.sdf")
        caja_sdf_path = os.path.join(share_robot_desc, "models", "caja", "caja.sdf")
        basurero_sdf_path = os.path.join(share_robot_desc, "models", "basurero", "basurero.sdf")

        return [
            SetParameter(name="use_sim_time", value=True),

            SetEnvironmentVariable(name="GZ_SIM_MODEL_PATH", value=model_path),
            SetEnvironmentVariable(name="GZ_SIM_RESOURCE_PATH", value=model_path),
            SetEnvironmentVariable(name="GZ_FILE_PATH", value=model_path),
            SetEnvironmentVariable(name="IGN_FILE_PATH", value=model_path),

            # --- Gazebo server (headless) ---
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
                ]),
                launch_arguments={
                    "gz_args": ["-r -s -v 4 ", world_path]
                }.items()
            ),

            # --- Gazebo client (GUI) ---
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
                ]),
                launch_arguments={
                    "gz_args": [" -g "]
                }.items()
            ),

            # --- Robot State Publisher ---
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                parameters=[{
                    "robot_description": robot_description,
                    "use_sim_time": True
                }],
                output="screen",
            ),

            # --- Spawn del robot ---
            TimerAction(
                period=3.0,
                actions=[
                    Node(
                        package="ros_gz_sim",
                        executable="create",
                        arguments=[
                            "-name", "robot_cell",
                            "-topic", "/robot_description",
                            "-x", "0", "-y", "0", "-z", "0",
                        ],
                        parameters=[{"use_sim_time": True}],
                        output="screen"
                    )
                ]
            ),

            # --- Spawn de la caja ---
            TimerAction(
                period=4.0,
                actions=[
                    Node(
                        package="ros_gz_sim",
                        executable="create",
                        arguments=[
                            "-name", "caja",
                            "-file", caja_sdf_path,
                            "-x", "0.3", "-y", "0.3", "-z", "0.91",
                        ],
                        parameters=[{"use_sim_time": True}],
                        output="screen"
                    )
                ]
            ),

            # --- Spawn del basurero ---
            TimerAction(
                period=4.5,
                actions=[
                    Node(
                        package="ros_gz_sim",
                        executable="create",
                        arguments=[
                            "-name", "basurero",
                            "-file", basurero_sdf_path,
                            "-x", "-0.4", "-y", "-0.15", "-z", "1.0",
                            "-R", "1.55",
                        ],
                        parameters=[{"use_sim_time": True}],
                        output="screen"
                    )
                ]
            ),

            # --- Bridge Gazebo <-> ROS ---
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                arguments=[
                    "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
                ],
                parameters=[{"use_sim_time": True}],
                output="screen"
            ),

            # --- Spawner joint_state_broadcaster ---
            TimerAction(
                period=5.0,
                actions=[
                    Node(
                        package="controller_manager",
                        executable="spawner",
                        arguments=["joint_state_broadcaster", "--param-file", PathJoinSubstitution([
                            FindPackageShare("robot_control_ur3"), "config", "controller.yaml"
                        ])],
                        parameters=[{"use_sim_time": True}],
                        output="screen"
                    )
                ]
            ),

            # --- Spawner brazo (ur_arm_controller) ---
            TimerAction(
                period=6.0,
                actions=[
                    Node(
                        package="controller_manager",
                        executable="spawner",
                        arguments=["ur_arm_controller", "--param-file", PathJoinSubstitution([
                            FindPackageShare("robot_control_ur3"), "config", "controller.yaml"
                        ])],
                        parameters=[{"use_sim_time": True}],
                        output="screen"
                    )
                ]
            ),

            # --- Spawner gripper ---
            TimerAction(
                period=7.0,
                actions=[
                    Node(
                        package="controller_manager",
                        executable="spawner",
                        arguments=["gripper_controller", "--param-file", PathJoinSubstitution([
                            FindPackageShare("robot_control_ur3"), "config", "controller.yaml"
                        ])],
                        parameters=[{"use_sim_time": True}],
                        output="screen"
                    )
                ]
            ),

            # --- MoveGroup ---
            TimerAction(
                period=9.0,
                actions=[
                    IncludeLaunchDescription(
                        PythonLaunchDescriptionSource([
                            PathJoinSubstitution([pkg_moveit, "launch", "move_group.launch.py"])
                        ]),
                        launch_arguments={"use_sim_time": "true"}.items()
                    )
                ]
            ),

            # --- RViz ---
            TimerAction(
                period=10.0,
                actions=[
                    Node(
                        package="rviz2",
                        executable="rviz2",
                        name="rviz2",
                        arguments=["-d", PathJoinSubstitution([
                            pkg_moveit, "config", "moveit.rviz"
                        ])],
                        parameters=[{"use_sim_time": True}],
                        output="screen"
                    )
                ]
            ),

            
        ]

    return LaunchDescription([
        DeclareLaunchArgument("ur_type", default_value="ur3"),
        OpaqueFunction(function=launch_setup),
    ])