"""Chinese prompt templates for robot manipulation video annotation.

This package mirrors ``prompts`` while keeping constant names, placeholders,
and JSON field names compatible with the existing AnnotationPipeline code.
"""

from .vocabulary import (
    ACTION_VOCABULARY,
    ACTION_FINE_GRAINED_GUIDANCE,
    FEW_SHOT_EXAMPLES,
)
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
