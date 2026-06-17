"""⑨ Morphogen Patterning — global gradient + local Turing reaction-diffusion → guided self-organization.

Inspired by developmental biology:
- Global morphogen gradient provides "positional information" (where you are)
- Local Turing reaction-diffusion generates "pattern" (what you should become)
- Guided self-organization (Caltech 2026): boundary conditions + mechanical constraints guide Turing
- BMP time integration: cells integrate signals over time, not instantaneous concentration
- Marr's 3-level framework: Computational → Algorithmic → Implementation
"""

from src.morphogen.morphogen_gradient import MorphogenGradient, GradientField
from src.morphogen.turing_patterning import TuringPatterning, TuringPattern, TuringParameters
from src.morphogen.guided_selforg import GuidedSelfOrganization, PatternConstraint, RootAgentRole

__all__ = [
    "MorphogenGradient",
    "GradientField",
    "TuringPatterning",
    "TuringPattern",
    "TuringParameters",
    "GuidedSelfOrganization",
    "PatternConstraint",
    "RootAgentRole",
]
