"""English prompt templates for robot manipulation video annotation."""

from .vocabulary import (
    ACTION_VOCABULARY,
    ACTION_FINE_GRAINED_GUIDANCE,
    FEW_SHOT_EXAMPLES,
)
from .robot_type import get_robot_type_prompt
from .analysis import (
    ANALYSIS_SYSTEM_PROMPT,
    ANALYSIS_PROMPT_TEMPLATE,
)
from .refinement import (
    REFINEMENT_SYSTEM_PROMPT,
    REFINEMENT_PROMPT_TEMPLATE,
)
from .detail_refinement import (
    DETAIL_REFINEMENT_SYSTEM_PROMPT,
    DETAIL_REFINEMENT_PROMPT_TEMPLATE,
)
