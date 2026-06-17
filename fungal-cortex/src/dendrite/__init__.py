"""③ Dendritic Integration — multi-source signal coincidence detection + temporal integration.

Inspired by:
- Cortical pyramidal neuron dendritic trees (fractal branching structure)
- NMDA receptors as coincidence detectors (pre/post-synaptic separation)
- bAP (back-propagating action potential) probability gate
- Spine neck resistance as tunable knob (EPSP shaping)
- Plateau potentials as sequence detectors
- Bilinear gating: burst probability = G(g)·Y(s) for zero-shot generalization
- BMP-style temporal integration (not instantaneous, but weighted window)
"""

from src.dendrite.dendritic_tree import DendriticTree, DendriticNode, DendriticSignal
from src.dendrite.coincidence_detector import CoincidenceDetector, CoincidenceEvent, NMDASynapse
from src.dendrite.temporal_integrator import TemporalIntegrator, IntegrationWindow, BMPIntegration

__all__ = [
    "DendriticTree",
    "DendriticNode",
    "DendriticSignal",
    "CoincidenceDetector",
    "CoincidenceEvent",
    "NMDASynapse",
    "TemporalIntegrator",
    "IntegrationWindow",
    "BMPIntegration",
]
