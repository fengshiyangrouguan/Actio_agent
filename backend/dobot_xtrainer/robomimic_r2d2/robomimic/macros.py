"""
Set of global variables shared across robomimic
"""
# Sets debugging mode. Should be set at top-level script so that internal
# debugging functionalities are made active
DEBUG = False

# Whether to visualize the before & after of an observation randomizer
VISUALIZE_RANDOMIZER = False

# wandb entity (eg. username or team name)
WANDB_ENTITY = None

# wandb api key (obtain from https://wandb.ai/authorize)
# alternatively, set up wandb from terminal with `wandb login`
WANDB_API_KEY = None

try:
    from backend.dobot_xtrainer.robomimic_r2d2.robomimic.macros_private import *
except ImportError:
    from backend.dobot_xtrainer.robomimic_r2d2.robomimic.utils.log_utils import log_warning
    import backend.dobot_xtrainer.robomimic_r2d2.robomimic
    log_warning(
        "No private macro file found!"\
        "\nIt is recommended to use a private macro file"\
        "\nTo setup, run: python {}/scripts/setup_macros.py".format(backend.dobot_xtrainer.robomimic_r2d2.robomimic.__path__[0])
    )
