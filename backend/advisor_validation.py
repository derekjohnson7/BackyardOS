import re


def evidence_for_finding(finding):
    """Return the authoritative fields an interpretation must preserve."""
    return {key: value for key, value in finding.items()
            if key not in ("id", "observation")}


def validate_advisor_response(response, verified_findings):
    """
    Validate Backyard Advisor's evidence-referenced response.

    Checks:
    1. Required response structure
    2. Valid evidence references
    3. Exactly one interpretation per verified finding
    4. Numeric duration consistency
    5. Specific contradictions involving moisture trends

    This validator does not establish scientific accuracy.
    """

    errors = []

    # 1. Validate response structure.
    if not isinstance(response, dict):
        return ["Response must be a JSON object"]

    required_fields = {
        "interpretations": list,
        "hypotheses_to_test": list,
        "unknowns": list,
        "confidence": dict,
    }

    for field, expected_type in required_fields.items():
        if not isinstance(response.get(field), expected_type):
            errors.append(f"Invalid or missing field: {field}")

    if errors:
        return errors

    findings_by_id = {
        finding["id"]: finding
        for finding in verified_findings
    }

    valid_ids = set(findings_by_id)

    # 2. Validate evidence references.
    for section in ("interpretations", "hypotheses_to_test"):
        for item in response[section]:
            if not isinstance(item, dict):
                errors.append(f"Invalid item in {section}")
                continue

            ids = item.get("finding_ids")

            if not isinstance(ids, list):
                errors.append(
                    f"Missing finding_ids in {section}"
                )
                continue

            for finding_id in ids:
                if not isinstance(finding_id, str):
                    errors.append("Evidence ID must be a string")
                    continue

                if finding_id not in valid_ids:
                    errors.append(
                        f"Unknown evidence ID: {finding_id}"
                    )

    # 3. Require exactly one interpretation per finding.
    interpretation_counts = {
        finding_id: 0
        for finding_id in valid_ids
    }

    for item in response["interpretations"]:
        if not isinstance(item, dict):
            continue

        ids = item.get("finding_ids")

        if not isinstance(ids, list):
            continue

        if len(ids) != 1:
            errors.append(
                "Each interpretation must reference "
                "exactly one finding ID"
            )
            continue

        finding_id = ids[0]

        if (
            isinstance(finding_id, str)
            and finding_id in valid_ids
        ):
            interpretation_counts[finding_id] += 1

    for finding_id, count in sorted(
        interpretation_counts.items()
    ):
        if count == 0:
            errors.append(
                f"Missing interpretation: {finding_id}"
            )
        elif count > 1:
            errors.append(
                f"Duplicate interpretation: {finding_id}"
            )

    # 4. Check numeric durations.
    for item in response["interpretations"]:
        if not isinstance(item, dict):
            continue

        ids = item.get("finding_ids", [])
        explanation = item.get("explanation", "")

        if (
            not isinstance(ids, list)
            or not isinstance(explanation, str)
        ):
            continue

        for finding_id in ids:
            if not isinstance(finding_id, str):
                continue

            finding = findings_by_id.get(finding_id)

            if (
                not finding
                or "daily_days_analyzed" not in finding
            ):
                continue

            expected_days = finding["daily_days_analyzed"]

            for match in re.finditer(
                r"\b(\d+)\s+(days?|intervals?)\b",
                explanation,
                flags=re.IGNORECASE,
            ):
                stated_number = int(match.group(1))
                unit = match.group(2).lower()

                expected = (
                    expected_days - 1
                    if unit.startswith("interval")
                    else expected_days
                )

                if stated_number != expected:
                    errors.append(
                        f"Duration mismatch for {finding_id}: "
                        f"stated {stated_number} {unit}, "
                        f"expected {expected}"
                    )

    # 5. Detect a specific unsupported decline claim.
    #
    # This catches claims such as:
    # "The moisture decline in both nodes..."
    #
    # It only applies when the claim references multiple
    # trend findings and at least one is not classified
    # as consistently decreasing.

    for section, text_field in (
        ("interpretations", "explanation"),
        ("hypotheses_to_test", "hypothesis"),
    ):
        for item in response[section]:
            if not isinstance(item, dict):
                continue

            ids = item.get("finding_ids", [])
            statement = item.get(text_field, "")

            if (
                not isinstance(ids, list)
                or not isinstance(statement, str)
            ):
                continue

            trend_findings = [
                findings_by_id[finding_id]
                for finding_id in ids
                if isinstance(finding_id, str)
                and finding_id in findings_by_id
                and "daily_direction"
                in findings_by_id[finding_id]
            ]

            if len(trend_findings) < 2:
                continue

            claims_shared_decline = re.search(
                r"\b(?:moisture|soil moisture)\s+"
                r"(?:decline|decrease|reduction|drop)\s+"
                r"in\s+(?:both|all)\s+nodes\b",
                statement,
                flags=re.IGNORECASE,
            )

            if not claims_shared_decline:
                continue

            for finding in trend_findings:
                if (
                    finding["daily_direction"]
                    != "consistently_decreasing"
                ):
                    errors.append(
                        "Trend contradiction: "
                        f"{finding['id']} has daily direction "
                        f"'{finding['daily_direction']}', "
                        "but the response claims moisture "
                        "declined in both/all nodes"
                    )

    # 6. Require exact structured evidence, independently of model prose.
    for item in response["interpretations"]:
        if not isinstance(item, dict):
            continue
        ids = item.get("finding_ids")
        if (not isinstance(ids, list) or len(ids) != 1
                or not isinstance(ids[0], str) or ids[0] not in findings_by_id):
            continue
        finding_id = ids[0]
        expected = evidence_for_finding(findings_by_id[finding_id])
        evidence = item.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"Missing structured evidence: {finding_id}")
        else:
            if set(evidence) != set(expected):
                errors.append(f"Evidence fields mismatch: {finding_id}")
            for key, value in expected.items():
                actual = evidence.get(key)
                # Python treats True == 1; explicitly reject booleans as numbers.
                numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
                correct_type = (
                    isinstance(actual, (int, float)) and not isinstance(actual, bool)
                    if numeric else type(actual) is type(value)
                )
                if key not in evidence or not correct_type or actual != value:
                    errors.append(f"Evidence mismatch: {finding_id}.{key}")
        explanation = item.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            errors.append(f"Missing explanation: {finding_id}")
        elif "daily_analysis_start" in expected and re.search(
            r"\b(?:over\s+)?(?:the\s+)?(?:past|last)\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+days?\b",
            explanation, flags=re.IGNORECASE,
        ):
            errors.append(f"Use explicit historical dates instead of relative days: {finding_id}")

    return errors