import torch

from mani_skill2 import PACKAGE_ASSET_DIR, format_path
from mani_skill2.agents.base_agent import BaseAgent
from mani_skill2.agents.controllers import *
from mani_skill2.utils.sapien_utils import (
    apply_urdf_config,
    check_urdf_config,
    parse_urdf_config,
)
from mani_skill2.utils.structs.articulation import Articulation


class ANYmalC(BaseAgent):
    uid = "anymal-c"
    urdf_path = f"{PACKAGE_ASSET_DIR}/robots/anymal-c/urdf/anymal.urdf"
    urdf_config = dict()

    def __init__(self, *args, **kwargs):
        self.joint_names = [
            "LF_HAA",
            "RF_HAA",
            "LH_HAA",
            "RH_HAA",
            "LF_HFE",
            "RF_HFE",
            "LH_HFE",
            "RH_HFE",
            "LF_KFE",
            "RF_KFE",
            "LH_KFE",
            "RH_KFE",
        ]
        super().__init__(*args, fix_root_link=False, **kwargs)

    @property
    def controller_configs(self):
        # isaac parameters
        # self.arm_stiffness = 85.0
        # self.arm_damping = 2.0
        # self.arm_force_limit = 100
        self.arm_stiffness = 1000.0
        self.arm_damping = 100
        self.arm_force_limit = 100
        # import ipdb;ipdb.set_trace()
        pd_joint_delta_pos = PDJointPosControllerConfig(
            self.joint_names,
            None,
            None,
            self.arm_stiffness,
            self.arm_damping,
            self.arm_force_limit,
            normalize_action=True,
            use_delta=True,
        )
        pd_joint_pos = PDJointPosControllerConfig(
            self.joint_names,
            None,
            None,
            self.arm_stiffness,
            self.arm_damping,
            self.arm_force_limit,
            normalize_action=False,
            use_delta=False,
        )
        controller_configs = dict(
            pd_joint_delta_pos=pd_joint_delta_pos, pd_joint_pos=pd_joint_pos
        )
        return controller_configs

    def _after_init(self):
        pass

    def _load_articulation(self):
        """
        Load the robot articulation
        """
        loader = self.scene.create_urdf_loader()
        loader.name = self.uid
        if self._agent_idx is not None:
            loader.name = f"{self.uid}-agent-{self._agent_idx}"
        loader.fix_root_link = self.fix_root_link

        urdf_path = format_path(str(self.urdf_path))

        urdf_config = parse_urdf_config(self.urdf_config, self.scene)
        check_urdf_config(urdf_config)

        # TODO(jigu): support loading multiple convex collision shapes
        apply_urdf_config(loader, urdf_config)
        loader.disable_self_collisions = True
        self.robot: Articulation = loader.load(urdf_path)
        assert self.robot is not None, f"Fail to load URDF from {urdf_path}"

    def is_standing(self):
        """This quadruped is considered standing if it is face up and body is at least 0.5m off the ground"""
        target_q = torch.tensor([1, 0, 0, 0], device=self.device)
        inner_prod = (self.robot.pose.q * target_q).sum(axis=1)
        # angle_diff = 1 - (inner_prod ** 2) # computes a distance from 0 to 1 between 2 quaternions
        angle_diff = torch.arccos(
            2 * (inner_prod**2) - 1
        )  # computes an angle between 2 quaternions
        # about 20 degrees
        aligned = angle_diff < 0.349
        high_enough = self.robot.pose.p[:, 2] > 0.5
        return torch.logical_and(aligned, high_enough)

    sensor_configs = []