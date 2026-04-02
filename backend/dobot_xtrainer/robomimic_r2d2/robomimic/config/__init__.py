from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.config import Config
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.base_config import config_factory, get_all_registered_configs

# note: these imports are needed to register these classes in the global config registry
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.bc_config import BCConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.bcq_config import BCQConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.cql_config import CQLConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.iql_config import IQLConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.gl_config import GLConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.hbc_config import HBCConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.iris_config import IRISConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.td3_bc_config import TD3_BCConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.diffusion_policy_config import DiffusionPolicyConfig
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.config.act_config import ACTConfig
