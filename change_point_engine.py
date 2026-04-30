import numpy as np


def pettitt_change_point_vectorized(data, min_segment_length=1):
    """
    Pixel-wise Pettitt change point test for a 2D raster time-series array.

    Parameters
    ----------
    data : ndarray
        2D array with shape (time, pixels). Each column is one pixel time series.
        The function expects no NaN values in the provided data.
    min_segment_length : int
        Minimum number of observations required before and after the detected
        change point. If the requested value is too high for the stack length, it is automatically reduced to the maximum feasible value.

    Returns
    -------
    change_step : ndarray
        First post-change time step using 1-based indexing. Example: if the
        split is between layer 5 and layer 6, change_step = 6.
    k_stat : ndarray
        Pettitt K statistic, the maximum absolute U statistic.
    p_value : ndarray
        Approximate two-tailed p-value for the Pettitt test.
    direction : ndarray
        +1 if the post-change mean is greater than the pre-change mean,
        -1 if lower, 0 if unchanged.
    magnitude : ndarray
        Difference between post-change mean and pre-change mean.
    before_mean : ndarray
        Mean value before the detected change point.
    after_mean : ndarray
        Mean value after the detected change point.
    """
    try:
        from scipy.stats import rankdata
    except Exception as exc:
        raise ImportError(
            "TrendShift requires SciPy. SciPy is normally bundled with QGIS. "
            "Please check your QGIS Python installation."
        ) from exc

    if data.ndim != 2:
        raise ValueError("Input data must be 2D with shape (time, pixels).")

    n_time, n_pixels = data.shape
    if n_time < 2:
        raise ValueError("At least 2 time steps are required.")

    min_segment_length = int(max(1, min_segment_length))
    max_feasible = max(1, n_time // 2)
    if min_segment_length > max_feasible:
        min_segment_length = max_feasible

    # Rank each pixel's time series independently. Ties are assigned average ranks.
    ranks = rankdata(data, axis=0, method="average").astype(np.float64)

    # Pettitt U_t = 2 * cumulative_rank_t - t * (n + 1)
    t = np.arange(1, n_time + 1, dtype=np.float64)[:, None]
    cumulative_ranks = np.cumsum(ranks, axis=0)
    u = 2.0 * cumulative_ranks - t * (n_time + 1.0)

    # Candidate split t means: before segment = 0..t-1, after segment = t..n-1.
    # Therefore t can range from min_segment_length to n_time - min_segment_length.
    # We evaluate U at row t-1.
    candidate_start = min_segment_length - 1
    candidate_end = n_time - min_segment_length - 1

    candidate_u = u[candidate_start:candidate_end + 1, :]
    abs_u = np.abs(candidate_u)
    max_pos = np.argmax(abs_u, axis=0)
    k_stat = abs_u[max_pos, np.arange(n_pixels)]

    split_t = max_pos + min_segment_length  # number of observations before split
    change_step = split_t + 1               # first post-change step, 1-based

    # Approximate p-value for Pettitt test.
    denom = (n_time ** 3 + n_time ** 2)
    p_value = 2.0 * np.exp((-6.0 * (k_stat ** 2)) / denom)
    p_value = np.clip(p_value, 0.0, 1.0)

    before_mean = np.empty(n_pixels, dtype=np.float64)
    after_mean = np.empty(n_pixels, dtype=np.float64)

    for pix in range(n_pixels):
        s = int(split_t[pix])
        before_mean[pix] = np.mean(data[:s, pix])
        after_mean[pix] = np.mean(data[s:, pix])

    magnitude = after_mean - before_mean
    direction = np.sign(magnitude).astype(np.int8)

    return (
        change_step.astype(np.float64),
        k_stat.astype(np.float64),
        p_value.astype(np.float64),
        direction.astype(np.int8),
        magnitude.astype(np.float64),
        before_mean.astype(np.float64),
        after_mean.astype(np.float64),
    )
