from collections import defaultdict

from environment_metrics import (
    safe_correlation,
    consecutive_changes,
)

MIN_DAILY_READINGS = 140


def build_moisture_findings(summaries, histories):
    """
    Build moisture findings using net changes
    and daily average patterns.
    """

    history_by_device = {
        history["device_id"]: history
        for history in histories
    }

    findings = []

    for index, summary in enumerate(
        sorted(summaries, key=lambda item: item["device_id"]),
        start=1,
    ):
        device_id = summary["device_id"]
        change = summary["net_change_percentage_points"]

        daily_averages = history_by_device[
            device_id
        ]["daily_averages"]

        daily = analyze_daily_trend(daily_averages)

        covered_days = [
            day
            for day in daily_averages
            if day["reading_count"] >= MIN_DAILY_READINGS
        ]

        analysis_dates = sorted(
            day["date"]
            for day in covered_days
        )

        direction = daily["direction"]

        if direction == "consistently_decreasing":
            observation = (
                "Daily average soil moisture decreased "
                "on every successive observed calendar date."
            )
        elif direction == "consistently_increasing":
            observation = (
                "Daily average soil moisture increased "
                "on every successive observed calendar date."
            )
        elif direction == "unchanged":
            observation = (
                "Daily average soil moisture values were unchanged."
            )
        elif direction == "mixed":
            observation = (
                "Daily average soil moisture showed "
                "both increases and decreases."
            )
        else:
            observation = (
                "Insufficient daily measurements "
                "to characterize the trend."
            )

        findings.append({
            "id": f"N{index:02d}-TREND",
            "daily_analysis_start": (
                analysis_dates[0] if analysis_dates else None
            ),
            "daily_analysis_end": (
                analysis_dates[-1] if analysis_dates else None
            ),
            "daily_days_analyzed": len(analysis_dates),
            "daily_coverage_min_readings": MIN_DAILY_READINGS,
            "device": device_id,
            "observation": observation,
            "net_change_percentage_points": change,
            "daily_direction": direction,
            "daily_range_percentage_points": daily[
                "daily_range_points"
            ],
            "increasing_intervals": daily[
                "increasing_intervals"
            ],
            "decreasing_intervals": daily[
                "decreasing_intervals"
            ],
        })

    return findings


def analyze_daily_trend(daily_averages):
    """
    Analyze the direction and range of daily moisture averages.

    Does not apply an arbitrary stability threshold.
    """
    values = [
        float(day["average_moisture_pct"])
        for day in daily_averages
        if day["reading_count"] >= MIN_DAILY_READINGS
    ]

    if len(values) < 2:
        return {
            "direction": "insufficient_data",
            "daily_range_points": None,
            "increasing_intervals": 0,
            "decreasing_intervals": 0,
            "unchanged_intervals": 0,
        }

    differences = consecutive_changes(values)

    increasing = sum(change > 0 for change in differences)
    decreasing = sum(change < 0 for change in differences)
    unchanged = sum(change == 0 for change in differences)

    if increasing == len(differences):
        direction = "consistently_increasing"
    elif decreasing == len(differences):
        direction = "consistently_decreasing"
    elif unchanged == len(differences):
        direction = "unchanged"
    else:
        direction = "mixed"

    return {
        "direction": direction,
        "daily_range_points": round(
            max(values) - min(values), 2
        ),
        "increasing_intervals": increasing,
        "decreasing_intervals": decreasing,
        "unchanged_intervals": unchanged,
    }


def build_temperature_findings(readings):
    """
    Generate temperature/moisture correlation findings
    directly from historical sensor readings.

    Correlation describes association, not causation.
    """

    devices = defaultdict(list)

    for reading in readings:
        device_id = reading.get("device_id")

        if device_id is not None:
            devices[device_id].append(reading)

    findings = []

    for index, (device_id, records) in enumerate(
        sorted(devices.items()),
        start=1,
    ):
        records = sorted(
            records,
            key=lambda record: record["timestamp"],
        )

        valid = [
            record
            for record in records
            if record.get("soil_moisture_pct") is not None
            and record.get("temperature_c") is not None
        ]

        moisture = [
            float(record["soil_moisture_pct"])
            for record in valid
        ]

        temperature = [
            float(record["temperature_c"])
            for record in valid
        ]

        overall = safe_correlation(
            moisture,
            temperature,
        )

        change_correlation = safe_correlation(
            consecutive_changes(moisture),
            consecutive_changes(temperature),
        )

        findings.append({
            "id": f"N{index:02d}-TEMP",
            "device": device_id,
            "valid_readings": len(valid),
            "overall_correlation": (
                round(overall, 3)
                if overall is not None else None
            ),
            "consecutive_change_correlation": (
                round(change_correlation, 3)
                if change_correlation is not None else None
            ),
            "observation": (
                "Historical soil moisture and temperature "
                "associations were measured using Pearson "
                "correlation. The overall correlation and "
                "consecutive-change correlation are reported "
                "separately. These measurements do not "
                "establish causation."
                if overall is not None
                else
                "Insufficient variation or valid readings "
                "to calculate an overall moisture-temperature "
                "correlation."
            ),
        })

    return findings