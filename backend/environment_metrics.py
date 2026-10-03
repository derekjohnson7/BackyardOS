from statistics import correlation


def safe_correlation(x, y):
    """
    Calculate Pearson correlation when sufficient
    variation exists in both datasets.
    """

    if len(x) != len(y) or len(x) < 2:
        return None

    if len(set(x)) < 2 or len(set(y)) < 2:
        return None

    return correlation(x, y)


def consecutive_changes(values):
    """Calculate changes between adjacent readings."""

    return [
        current - previous
        for previous, current in zip(values, values[1:])
    ]