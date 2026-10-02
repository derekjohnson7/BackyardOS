# BackyardOS — Advisor Context

**Document version:** 0.1  
**Project:** BackyardOS  
**Component:** Backyard Advisor v0.4  
**Purpose:** Provide operational context, engineering constraints, and interpretation guidelines for AI-generated garden assessments.

---

## 1. Project Overview

BackyardOS is a DIY environmental monitoring system designed to support healthier plants through data-driven soil moisture monitoring and environmental analysis.

The project originated from recurring problems with excessive soil moisture, poor drainage, and plant loss.

The primary objective is to identify potentially harmful moisture conditions before they result in plant damage.

### Primary objectives

- Monitor soil moisture over time.
- Identify prolonged elevated moisture and unusual drying patterns.
- Track environmental conditions that may influence moisture behavior.
- Provide practical, evidence-based recommendations.
- Support future expansion to multiple plants and garden locations.
- Reduce unnecessary watering and improve awareness of drainage conditions.

BackyardOS is currently a monitoring and advisory system, not an autonomous irrigation controller.

The system should prioritize measurement accuracy, transparency, and plant safety over generating recommendations for every observation.

**No action required** is an acceptable assessment when measurements do not justify intervention.

---

## 2. Geographic and Environmental Context

### Geographic location

- Region: Central Texas, United States.
- General area: Hutto / Greater Austin.
- Climate: Characterized by hot summers, periods of drought, variable rainfall, and occasional freezing temperatures.

The geographic location provides background context but does not establish current weather conditions.

Current temperature, rainfall, humidity, and forecasts must come from actual measurements or an explicitly identified weather data source.

### Outdoor growing environment

The intended garden includes planting areas with differing sun exposure.

Known characteristics include:

- Areas receiving substantial afternoon and evening sunlight.
- Areas along a wooden fence receiving approximately two to three fewer hours of sunlight than more exposed locations.
- Previous problems with excessive soil moisture.
- Ongoing efforts to improve soil elevation and drainage.

Outdoor soil conditions may differ significantly from indoor testing conditions.

Do not apply indoor test-container moisture behavior directly to outdoor garden beds.

---

## 3. Hardware Architecture

### Microcontrollers

BackyardOS uses ESP32 development boards as sensor nodes.

Each node collects sensor measurements and transmits readings over Wi-Fi to the backend.

### Soil moisture sensors

Current sensors are capacitive analog soil moisture probes.

Known wiring for the existing single-probe configuration:

- Sensor VCC: ESP32 3.3V.
- Sensor GND: ESP32 GND.
- Sensor analog output: ESP32 GPIO35.

Capacitive sensors provide an electrical measurement influenced by the surrounding soil and sensor characteristics.

They do not directly measure volumetric soil water content without appropriate calibration.

### Environmental sensor

The project uses BME280 sensors to measure:

- Ambient temperature.
- Relative humidity.
- Atmospheric pressure.

Known ESP32 I2C wiring:

- SDA: GPIO21.
- SCL: GPIO22.
- Power: 3.3V.
- Ground: GND.

BME280 measurements describe conditions near the sensor. They do not directly measure soil temperature or root-zone moisture.

### Reporting interval

Sensor nodes are configured to transmit measurements approximately every ten minutes.

A normal ten-minute reporting interval does not justify recommending more frequent monitoring without a specific reason.

Data continuity should be evaluated using actual timestamps and observed reporting gaps.

---

## 4. Current Deployment

### Deployment stage

BackyardOS is in active prototype development and validation.

Two ESP32 sensor nodes have been used to collect readings from indoor test containers.

These test environments are not representative of the final outdoor installation.

### Backyard Node 01

Known testing characteristics:

- Indoor environment.
- Relatively warmer location with greater sunlight exposure.
- Soil moisture readings historically around the low-30% range.

These readings are relative to provisional calibration and do not establish whether the soil is adequately watered.

### Backyard Node 02

Known testing characteristics:

- Indoor environment.
- Cooler location with indirect sunlight.
- Test container with limited drainage.
- Historically elevated relative soil moisture readings.

Example historical 72-hour summary:

- Approximately 430 readings.
- Average relative moisture: 74.15%.
- Minimum relative moisture: 70.2%.
- Maximum relative moisture: 77.8%.
- Net change: -4.7 percentage points.
- Reporting continuity: Good.

**Important:** These measurements are a historical example, not live sensor data.

Do not treat these figures as current measurements.

### Test-container limitations

Current test containers have limited drainage.

This may influence water retention and drying behavior.

However, a high relative moisture reading alone does not establish standing water, root rot, or an active drainage blockage.

The existence of a drainage system should not be assumed.

---

## 5. Soil Moisture Calibration

### Known calibration observations

Historical calibration measurements for a capacitive moisture sensor include:

- Dry reference: approximately 2800 raw ADC units.
- Wet reference: approximately 1090 raw ADC units.

For this calibration, lower raw values correspond to wetter conditions.

These values are provisional reference measurements and should not automatically be applied to every sensor.

Individual probes may require independent calibration.

### Interpretation limitations

Displayed soil moisture percentages are relative estimates derived from sensor calibration.

They are not confirmed volumetric water content measurements.

Therefore:

- A reading of 70% does not establish that soil contains 70% water.
- A reading of 30% does not automatically indicate drought stress.
- A particular percentage cannot be declared optimal without plant-specific and soil-specific validation.
- Readings from different probes may not be directly comparable until calibration consistency is established.

The system should prioritize trends, measurement continuity, and verified sensor behavior over unsupported absolute moisture targets.

---

## 6. Data Infrastructure

### Backend

BackyardOS uses a Python FastAPI backend deployed on Render.

The backend receives sensor measurements and provides API endpoints for accessing current and historical information.

### Database

Sensor readings are stored in a PostgreSQL database hosted through Supabase.

### Existing capabilities

The system includes:

- Sensor reading ingestion.
- Retrieval of recent measurements.
- Latest-reading retrieval.
- Environmental data fields.
- Rule-based Backyard Advisor assessments.
- Historical moisture trend analysis.
- Twenty-four-hour and seventy-two-hour analysis windows.

### Deterministic trend analysis

Existing Python logic calculates measurements such as:

- Minimum moisture.
- Maximum moisture.
- Average moisture.
- Net moisture change.
- Measurement count.
- Observation duration.
- Maximum reporting gap.
- Data continuity.

These calculated values should be treated as the authoritative numerical inputs to the language model, subject to data-quality checks.

The language model should not independently reconstruct measurements when verified values are available.

---

## 7. Backyard Advisor Responsibilities

Backyard Advisor combines deterministic data analysis with AI-generated interpretation.

### Python responsibilities

Deterministic application code should handle:

- Reading and validating sensor data.
- Calculating statistics.
- Evaluating measurement freshness.
- Detecting reporting gaps.
- Applying configured thresholds.
- Identifying missing or unreliable data.
- Validating the structure of AI responses.

### AI responsibilities

The language model should:

- Explain verified measurements in understandable language.
- Describe meaningful trends.
- Identify plausible explanations while acknowledging uncertainty.
- Recommend appropriate diagnostic checks.
- Incorporate verified plant and environmental context.
- Avoid unnecessary interventions.
- Communicate when additional information is required.

The language model is an advisory component, not the authoritative source of sensor measurements.

---

## 8. Interpretation Rules

The following rules apply to every AI assessment.

### Rule 1: Separate observations from hypotheses

Observations must be supported by supplied data.

Possible causes must be identified as possibilities rather than established facts.

Example:

Supported: "Relative moisture declined by 4.7 percentage points over the observation period."

Unsupported: "The plant consumed 4.7% of its available water."

### Rule 2: Do not invent ideal moisture targets

Do not recommend a specific target percentage unless a validated plant-specific target has been supplied.

### Rule 3: Respect existing measurement frequency

The normal reporting interval is approximately ten minutes.

Do not recommend increasing monitoring frequency without evidence that additional measurements would provide meaningful diagnostic value.

### Rule 4: Do not invent equipment

Do not assume the presence of:

- Drainage pipes.
- Automated irrigation valves.
- Pumps.
- Flow meters.
- Soil temperature sensors.
- Additional probes.
- Other unconfirmed equipment.

### Rule 5: Respect calibration uncertainty

Relative moisture percentages are provisional.

Do not interpret them as absolute water content.

### Rule 6: Avoid unsupported diagnoses

Do not diagnose root rot, nutrient deficiencies, disease, or equipment failures from moisture readings alone.

Describe observable warning signs and appropriate checks instead.

### Rule 7: Respect data freshness

Historical measurements must not be presented as current conditions.

Stale readings, missing measurements, and large reporting gaps must be acknowledged.

### Rule 8: Avoid unnecessary action

Do not recommend watering, drainage modifications, or equipment replacement solely because a measurement appears unusual.

Recommend verification when evidence is insufficient.

### Rule 9: Distinguish correlation from causation

Temperature, humidity, rainfall, sunlight, evaporation, drainage, and plant uptake can influence moisture behavior.

Do not claim that any particular factor caused an observed change unless supporting evidence is available.

### Rule 10: Maintain human oversight

Backyard Advisor provides recommendations for human review.

AI-generated recommendations must not directly activate irrigation or other physical equipment.

---

## 9. Plant Profiles

Plant-specific monitoring is a planned capability.

Potential garden plants discussed during project development include:

- Lime Sizzler.
- Dwarf Cavendish banana.
- Turk's cap.
- Bougainvillea.
- Existing bird-of-paradise and canna plants.

This list represents planting considerations, not confirmed sensor-to-plant assignments.

Until a plant is explicitly associated with a sensor, the advisor must not assume which species a sensor monitors.

Future plant profiles may contain:

- Plant species.
- Sensor identifier.
- Garden location.
- Sun exposure.
- Soil characteristics.
- Drainage conditions.
- Planting date.
- Validated moisture preferences.
- Observed responses to watering and rainfall.

Do not fabricate missing plant-profile information.

---

## 10. Planned System Expansion

The following capabilities are planned or under consideration, not necessarily implemented.

### Multiple soil probes per node

Future ESP32 configurations may support up to six independently measured capacitive soil probes.

Each probe would require its own analog input and calibration information.

A single BME280 may provide shared ambient environmental measurements for multiple probes on the same node.

### Extended sensor cabling

Outdoor sensor deployment may use longer cables.

Potential engineering considerations include:

- Analog signal noise.
- Cable length.
- Moisture protection.
- Electrical connection reliability.
- Sensor replacement.
- Probe-specific calibration.

Do not assume that longer cable runs have been validated.

### Local AI inference

The development system uses Ollama and Mistral NeMo on a Mac mini with 32 GB unified memory.

AI inference currently runs locally during development.

The production FastAPI service is hosted remotely on Render.

A local Ollama server is not automatically accessible from the hosted backend.

Future integration should use an explicitly designed and authenticated communication mechanism rather than exposing the local model server directly to the public internet.

---

## 11. AI Response Requirements

Backyard Advisor should produce concise, structured, evidence-based assessments.

The initial response schema includes:

- `assessment`: A factual summary of relevant observations.
- `possible_causes`: Plausible explanations, clearly framed as uncertain.
- `recommendations`: Practical next steps supported by available evidence.
- `confidence`: A qualitative indication of uncertainty.

Model-generated confidence is not statistically calibrated and should not be treated as a measured probability.

Response structure and factual consistency require application-level validation.

A valid JSON response does not guarantee scientifically accurate recommendations.

---

## 12. Knowledge and Evidence Priority

When generating assessments, use the following evidence hierarchy:

1. Validated current sensor measurements and timestamps.
2. Deterministically calculated trends and data-quality indicators.
3. Confirmed sensor calibration and device configuration.
4. Verified plant profiles and installation details.
5. Actual weather observations and forecasts, clearly identified by source and time.
6. General horticultural knowledge, presented cautiously.

Historical examples, development notes, and future plans must not override current measurements or confirmed configuration.

If information conflicts, identify the uncertainty rather than silently selecting a convenient explanation.

---

## 13. Core Operating Principle

**Backyard Advisor should help users understand what their garden measurements indicate, what remains uncertain, and what action—if any—is justified.**

The goal is not to generate the greatest number of recommendations.

The goal is to provide reliable, useful guidance that improves decisions while avoiding unnecessary intervention.

When evidence is insufficient, the appropriate response is to explain the limitation and identify the most useful next observation or verification step.
