import re
from typing import Dict

# ── Layer 1: Automotive-specific hard rules ───────────────────────────────────
# These are manually curated complex→simple substitutions for automotive manuals.
# Complex technical words → simpler equivalents that NLLB translates more accurately.

AUTOMOTIVE_SIMPLIFICATION: Dict[str, str] = {

    # ── Mechanical Actions ────────────────────────────────────────────────────
    "depress":          "press down",
    "depressing":       "pressing down",
    "depressed":        "pressed down",
    "actuate":          "activate",
    "actuating":        "activating",
    "actuated":         "activated",
    "disengage":        "release",
    "disengaging":      "releasing",
    "disengaged":       "released",
    "engage":           "connect",
    "engaging":         "connecting",
    "engaged":          "connected",
    "oscillate":        "vibrate",
    "oscillating":      "vibrating",
    "attenuate":        "reduce",
    "attenuating":      "reducing",
    "lubricate":        "apply oil to",
    "lubricating":      "applying oil to",
    "pressurize":       "apply pressure to",
    "pressurizing":     "applying pressure to",
    "deteriorate":      "wear out",
    "deteriorating":    "wearing out",
    "illuminate":       "light up",
    "illuminating":     "lighting up",
    "ascertain":        "find out",
    "ascertaining":     "finding out",
    "verify":           "confirm",
    "verifying":        "confirming",
    "inspect":          "check",
    "inspecting":       "checking",
    "ensure":           "make sure",
    "ensuring":         "making sure",
    "commence":         "start",
    "commencing":       "starting",
    "terminate":        "stop",
    "terminating":      "stopping",
    "accelerate":       "speed up",
    "decelerating":     "slowing down",
    "decelerate":       "slow down",
    "tighten":          "fasten",
    "loosen":           "undo",
    "disconnect":       "detach",
    "reconnect":        "reattach",

    # ── Component Names ───────────────────────────────────────────────────────
    "accumulator":      "storage tank",
    "actuator":         "control motor",
    "solenoid":         "electric switch",
    "manifold":         "pipe junction",
    "throttle":         "accelerator",
    "alternator":       "generator",
    "rectifier":        "power converter",
    "condenser":        "cooling coil",
    "capacitor":        "charge storage unit",
    "resistor":         "current limiter",
    "transducer":       "sensor",
    "strainer":         "filter screen",
    "dowel":            "guide pin",
    "gasket":           "seal ring",
    "retainer":         "holding clip",
    "circlip":          "snap ring",
    "bushing":          "sleeve bearing",
    "shim":             "spacer plate",

    # ── Descriptive / Qualifying Words ───────────────────────────────────────
    "permissible":      "allowed",
    "excessive":        "too much",
    "insufficient":     "not enough",
    "nominal":          "normal",
    "adjacent":         "next to",
    "subsequent":       "next",
    "prior":            "before",
    "initial":          "first",
    "optimum":          "best",
    "adequate":         "enough",
    "defective":        "faulty",
    "deteriorated":     "worn out",
    "obstructed":       "blocked",
    "contaminated":     "dirty",
    "corroded":         "rusted",
    "fractured":        "cracked",
    "misaligned":       "out of alignment",
    "intermittent":     "on and off",
    "erratic":          "irregular",
    "gradual":          "slow",
    "simultaneous":     "at the same time",
    "approximate":      "about",
    "approximately":    "about",
    "mandatory":        "required",
    "optional":         "not required",
    "periodically":     "from time to time",
    "immediately":      "right away",
    "temporarily":      "for a short time",

    # ── Diagnostic / Service Terms ────────────────────────────────────────────
    "malfunction":      "fault",
    "malfunctioning":   "not working correctly",
    "diagnostic":       "fault check",
    "diagnostics":      "fault checking",
    "calibrate":        "adjust",
    "calibrating":      "adjusting",
    "calibration":      "adjustment",
    "initialize":       "set up",
    "initializing":     "setting up",
    "initialization":   "setup",
    "recalibrate":      "readjust",
    "reset":            "restart",
    "troubleshoot":     "find the fault",
    "troubleshooting":  "finding the fault",

    # ── Measurement / Specification Terms ─────────────────────────────────────
    "specification":    "required value",
    "specifications":   "required values",
    "tolerance":        "allowed range",
    "clearance":        "gap size",
    "torque":           "tightening force",
    "viscosity":        "thickness of oil",
    "pressure":         "force",
    "velocity":         "speed",
    "temperature":      "heat level",
    "gradient":         "slope",
    "resistance":       "opposition to flow",
    "conductivity":     "ability to carry current",
}


def simplify_text(text: str) -> str:
    """
    Replace complex English automotive words with simpler equivalents
    before sending to the translation model.

    This improves translation quality because NLLB-200 handles common
    words much better than rare technical terms.

    Applied BEFORE protect_terms() so the glossary can still protect
    the simplified versions if needed.

    Example:
        Input:  "Depress the clutch pedal to disengage the gearbox."
        Output: "Press down the clutch pedal to release the gearbox."

    Args:
        text: Raw English sentence from the document

    Returns:
        Sentence with complex words replaced by simpler equivalents
    """
    result = text

    # Sort by length descending — replace longer phrases first
    # e.g. "wearing out" before "wear" to avoid partial matches
    sorted_terms = sorted(
        AUTOMOTIVE_SIMPLIFICATION.keys(),
        key=len,
        reverse=True
    )

    for complex_word in sorted_terms:
        simple_word = AUTOMOTIVE_SIMPLIFICATION[complex_word]
        # Word boundary match, case-insensitive
        pattern = re.compile(
            r'\b' + re.escape(complex_word) + r'\b',
            re.IGNORECASE
        )

        def replace_preserving_case(match):
            original = match.group(0)
            # Preserve capitalization of first letter
            if original[0].isupper():
                return simple_word[0].upper() + simple_word[1:]
            return simple_word

        result = pattern.sub(replace_preserving_case, result)

    return result