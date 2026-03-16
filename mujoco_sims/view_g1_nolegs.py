import mujoco
import mujoco.viewer

# path to the Unitree model
MODEL_PATH = "./unitree_ros/robots/g1_nolegs/g1_23dof.xml"

model = mujoco.MjModel.from_xml_path(MODEL_PATH)
data = mujoco.MjData(model)

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
