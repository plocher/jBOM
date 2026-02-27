"""Constants and enums for jBOM component types, scores, and field mappings."""
from __future__ import annotations


# Component type constants
class ComponentType:
    """Component type constants for standardized type identification"""

    RESISTOR = "RES"
    CAPACITOR = "CAP"
    INDUCTOR = "IND"
    DIODE = "DIO"
    LED = "LED"
    INTEGRATED_CIRCUIT = "IC"
    MICROCONTROLLER = "MCU"
    TRANSISTOR = "Q"
    CONNECTOR = "CON"
    SWITCH = "SWI"
    RELAY = "RLY"
    REGULATOR = "REG"
    OSCILLATOR = "OSC"
    ANALOG = "ANA"
    SILK_SCREEN = "SLK"


# Diagnostic issue type constants
class DiagnosticIssue:
    """Diagnostic issue type constants"""

    TYPE_UNKNOWN = "type_unknown"
    NO_TYPE_MATCH = "no_type_match"
    NO_VALUE_MATCH = "no_value_match"
    PACKAGE_MISMATCH = "package_mismatch"
    PACKAGE_MISMATCH_GENERIC = "package_mismatch_generic"
    NO_MATCH = "no_match"


# Common inventory field constants
class CommonFields:
    """Common field name constants"""

    VOLTAGE = "V"
    AMPERAGE = "A"
    WATTAGE = "W"
    TOLERANCE = "Tolerance"
    POWER = "Power"
    TEMPERATURE_COEFFICIENT = "Temperature Coefficient"


# SMD field constants
class SMDType:
    """SMD type indicator constants"""

    SMD_VALUES = ["SMD", "Y", "YES", "TRUE", "1"]
    PTH_VALUES = ["PTH", "THT", "TH", "THROUGH-HOLE", "N", "NO", "FALSE", "0"]
    UNKNOWN_VALUES = ["", "UNKNOWN", "N/A"]


# Scoring constants
class ScoreWeights:
    """Scoring weight constants for inventory matching"""

    TOLERANCE_EXACT = 15
    TOLERANCE_BETTER = 12
    VOLTAGE_MATCH = 10
    CURRENT_MATCH = 10
    POWER_MATCH = 10
    LED_WAVELENGTH = 8
    LED_INTENSITY = 8
    OSC_FREQUENCY = 12
    OSC_STABILITY = 8
    LED_ANGLE = 5
    OSC_LOAD = 5
    CON_PITCH = 10
    MCU_FAMILY = 8
    GENERIC_PROPERTY = 3


# Precision threshold for resistor matching
PRECISION_THRESHOLD = 1.0


# Category-specific inventory field mappings for comprehensive property extraction
COMMON_FIELDS = [
    "IPN",  # User provided Inventory Part Number
    "Value",  # Value - usually ohms, farads... or part number
    "Description",  # Human readable
    "SMD",  # is this a Surface Mount part?
    "Manufacturer",  # Human readable
    "MFGPN",  # Human readable
    "Package",  # EIA nomenclature
    "Symbol",  # KiCad Symbol
    "Footprint",  # KiCad Footprint
    "Datasheet",  # URL
]

DEFAULT_CATEGORY_FIELDS = COMMON_FIELDS + [
    CommonFields.VOLTAGE,
    CommonFields.AMPERAGE,
    CommonFields.WATTAGE,
    CommonFields.TOLERANCE,
    CommonFields.TEMPERATURE_COEFFICIENT,
]

# Category-specific field mappings with value interpretation semantics
# Note: "Value:X" means the component's Value field represents quantity X
CATEGORY_FIELDS = {
    ComponentType.ANALOG: COMMON_FIELDS + [CommonFields.VOLTAGE],
    ComponentType.CAPACITOR: COMMON_FIELDS
    + [
        CommonFields.VOLTAGE,
        "Voltage",
        "Type",
        CommonFields.TOLERANCE,
    ],  # Value:Capacitance
    ComponentType.CONNECTOR: COMMON_FIELDS + ["Pitch"],
    ComponentType.DIODE: COMMON_FIELDS + [CommonFields.VOLTAGE, CommonFields.AMPERAGE],
    ComponentType.LED: COMMON_FIELDS
    + [
        CommonFields.VOLTAGE,
        CommonFields.AMPERAGE,
        "mcd",
        "Wavelength",
        "Angle",
    ],  # Value:Color
    ComponentType.RESISTOR: COMMON_FIELDS
    + [
        CommonFields.VOLTAGE,
        CommonFields.WATTAGE,
        CommonFields.POWER,
        CommonFields.TOLERANCE,
    ],  # Value:Resistance
    ComponentType.INTEGRATED_CIRCUIT: COMMON_FIELDS + [CommonFields.VOLTAGE],
    ComponentType.INDUCTOR: COMMON_FIELDS
    + [CommonFields.AMPERAGE, CommonFields.WATTAGE],  # Value:Inductance
    ComponentType.TRANSISTOR: COMMON_FIELDS
    + [CommonFields.VOLTAGE, CommonFields.AMPERAGE, CommonFields.WATTAGE],
    ComponentType.MICROCONTROLLER: COMMON_FIELDS + ["Family"],
    ComponentType.REGULATOR: COMMON_FIELDS
    + [CommonFields.VOLTAGE, CommonFields.AMPERAGE, CommonFields.WATTAGE],
    ComponentType.OSCILLATOR: COMMON_FIELDS + ["Frequency", "Stability", "Load"],
    ComponentType.SILK_SCREEN: COMMON_FIELDS + ["Form"],
    ComponentType.RELAY: COMMON_FIELDS + ["Form"],
    ComponentType.SWITCH: COMMON_FIELDS + ["Form"],
}

# Define how Value:X field should be interpreted for each category
VALUE_INTERPRETATION = {
    ComponentType.CAPACITOR: "Capacitance",  # Value represents capacitance
    ComponentType.RESISTOR: "Resistance",  # Value represents resistance
    ComponentType.INDUCTOR: "Inductance",  # Value represents inductance
    ComponentType.LED: "Color",  # Value represents color/wavelength
}

# Global type mapping for component type normalization
COMPONENT_TYPE_MAPPING = {
    "RESISTOR": ComponentType.RESISTOR,
    "R": ComponentType.RESISTOR,
    "CAPACITOR": ComponentType.CAPACITOR,
    "C": ComponentType.CAPACITOR,
    "DIODE": ComponentType.DIODE,
    "D": ComponentType.DIODE,
    "INDUCTOR": ComponentType.INDUCTOR,
    "L": ComponentType.INDUCTOR,
    "TRANSISTOR": ComponentType.TRANSISTOR,
    "MICROCONTROLLER": ComponentType.MICROCONTROLLER,
    "REGULATOR": ComponentType.REGULATOR,
    "OSCILLATOR": ComponentType.OSCILLATOR,
    "SWITCH": ComponentType.SWITCH,
    "RELAY": ComponentType.RELAY,
    "CONNECTOR": ComponentType.CONNECTOR,
    "ANALOG": ComponentType.ANALOG,
}


__all__ = [
    "ComponentType",
    "DiagnosticIssue",
    "CommonFields",
    "SMDType",
    "ScoreWeights",
    "PRECISION_THRESHOLD",
    "COMMON_FIELDS",
    "DEFAULT_CATEGORY_FIELDS",
    "CATEGORY_FIELDS",
    "VALUE_INTERPRETATION",
    "COMPONENT_TYPE_MAPPING",
]
