from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.algo import register_algo_factory_func, algo_name_to_factory_func, algo_factory, Algo, PolicyAlgo, ValueAlgo, PlannerAlgo, HierarchicalAlgo, RolloutPolicy

# note: these imports are needed to register these classes in the global algo registry
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.bc import BC, BC_Gaussian, BC_GMM, BC_VAE, BC_RNN, BC_RNN_GMM
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.bcq import BCQ, BCQ_GMM, BCQ_Distributional
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.cql import CQL
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.iql import IQL
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.gl import GL, GL_VAE, ValuePlanner
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.hbc import HBC
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.iris import IRIS
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.td3_bc import TD3_BC
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.diffusion_policy import DiffusionPolicyUNet
from backend.dobot_xtrainer.robomimic_r2d2.robomimic.algo.act import ACT
