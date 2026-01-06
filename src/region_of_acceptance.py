"""
This is implementation of Region of Acceptance (RoA) from
"Dealing with Uncertainty in pWCET Estimations" paper, link:

https://dl.acm.org/doi/abs/10.1145/3396234

It's aimed to estimate uncertaintry in probabilistic worst case
execution time. For a given dataset it computes goodness of fit
tests and then draws an uncertainty region.
"""

import numpy as np
from scipy import stats
from scipy.stats import linregress
from statsmodels.tsa.stattools import kpss, bds
from scipy.optimize import minimize
from dataclasses import dataclass
from typing import Tuple, List, Optional
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import warnings
import logging


class EVTValidator:
    """
    Validates if time series data meets the statistical assumptions required
    for Probabilistic Worst-Case Execution Time (pWCET) analysis using
    Extreme Value Theory (EVT)

    References:
    - [cite_start]Reghenzani et al., "Probabilistic-WCET Reliability: On the experimental validation of EVT hypotheses" [cite: 17]
    """

    def __init__(self, local_alpha: float = 0.05):
        """
        Args:
            local_alpha (float): The significance level for EACH individual test
        """
        self.num_tests = 3
        self.local_alpha = local_alpha

        # [cite_start]Calculate Global Alpha based on Equation 5 in the paper[cite: 176]:
        # alpha_global = 1 - (1 - alpha_local)^n
        # [cite_start]For local_alpha=0.05 and n=3, global_alpha is approx 0.14 [cite: 179]
        self.global_alpha = 1 - (1 - self.local_alpha) ** self.num_tests

        # Suppress warnings for cleaner output (KPSS often throws p-value warnings)
        warnings.filterwarnings("ignore")

    def validate_single_series(self, data):
        """
        Performs the 3 hypothesis tests on a single time series using local_alpha.
        Returns table of passed tests (Table 1 replication)
        """
        # Ensure input is 1D array
        data = np.array(data, dtype=float).flatten()
        n = len(data)

        failures = {"kpss": False, "bds": False, "rs": False, "any": False}

        # [cite_start]1. Stationarity (KPSS) [cite: 147]
        # H0: Stationary. Reject H0 if p < local_alpha.
        try:
            kpss_stat, p_kpss, _, _ = kpss(data, regression="c", nlags="auto")
            if p_kpss < self.local_alpha:
                failures["kpss"] = True
        except:
            failures["kpss"] = True

        # [cite_start]2. Short-Range Independence (BDS) [cite: 150]
        # H0: i.i.d. Reject H0 if p < local_alpha.
        try:
            if n >= 50:
                _, p_bds_output = bds(data, max_dim=2)

                p_bds_array = np.atleast_1d(p_bds_output)

                p_bds = p_bds_array[0]
                if p_bds < self.local_alpha:
                    failures["bds"] = True
            else:
                failures["bds"] = True
        except Exception as e:
            # print(f"BDS Error: {e}")
            failures["bds"] = True

        # [cite_start]3. Long-Range Independence (Hurst via R/S) [cite: 161]
        # H0: No long-range dependency.
        try:
            hurst = self._calculate_hurst(data)
            # [cite_start]Threshold: H should be near 0.5. [cite: 159]
            # We use a tolerance window. If H is extreme (<0.35 or >0.65), we assume dependency.
            if not (0.35 <= hurst <= 0.65):
                failures["rs"] = True
        except:
            failures["rs"] = True

        if failures["kpss"] or failures["bds"] or failures["rs"]:
            failures["any"] = True

        return failures

    def validate_multiple_runs(self, data_matrix: np.ndarray):
        """
        Validates multiple execution runs to characterize the archetecture.

        Args:
            data_matrix (np.ndarray): A 2D array of shape (n_runs, n_samples)
                                      Each ro is a separate time series

        Returns:
            Tuple: (is_compliant, statistics_dict)
        """
        # Ensure input is a 2D numpy array
        if not isinstance(data_matrix, np.ndarray) or data_matrix.ndim != 2:
            raise ValueError(
                "Input must be a 2D numpy array with shape (n_runs, n_samples)"
            )

        total_runs = data_matrix.shape[0]
        rejections = 0

        # Iterate over rows (each row is a run)
        result = [
            self.validate_single_series(data_matrix[i, :]) for i in range(total_runs)
        ]

        return result

        # rejection_ratio = rejections / total_runs

        # [cite_start]According to the paper, we compare rejection ratio to the global alpha[cite: 183].
        # A ratio near alpha identifies a compliant architecture.
        # We allow a tolerance (e.g., 1.5x) to account for statistical variance.
        # is_compliant = rejection_ratio <= (self.global_alpha * 1.5)

        # return is_compliant, {
        #     "total_runs": total_runs,
        #     "rejections": rejections,
        #     "rejection_ratio": rejection_ratio,
        #     "local_alpha": self.local_alpha,
        #     "expected_global_alpha": self.global_alpha,
        #     "compliant": is_compliant,
        # }

    def _calculate_hurst(self, data):
        """[cite_start]Helper to calc Hurst via R/S statistics [cite: 161]"""
        n = len(data)
        min_chunk, max_chunk = 8, n // 2
        scales, rs_values = [], []
        chunk_size = min_chunk

        while chunk_size <= max_chunk:
            num_chunks = n // chunk_size
            chunks = np.array_split(data[: num_chunks * chunk_size], num_chunks)
            chunk_rs = []
            for chunk in chunks:
                std = np.std(chunk, ddof=1)
                if std == 0:
                    continue
                z = np.cumsum(chunk - np.mean(chunk))
                R = np.max(z) - np.min(z)
                chunk_rs.append(R / std)

            if chunk_rs:
                scales.append(chunk_size)
                rs_values.append(np.mean(chunk_rs))
            chunk_size *= 2

        if len(scales) > 2:
            slope, _, _, _, _ = linregress(np.log10(scales), np.log10(rs_values))
            return slope

        return 0.5


# @dataclass
# class GEVParameters:
#     """GEV distribution parameters: location, scale, shape"""

#     mu: float  # location
#     sigma: float  # scale
#     xi: float  # shape

#     def __repr__(self):
#         return f"GEV(μ={self.mu:.3f}, σ={self.sigma:.3f}, ξ={self.xi:.3f})"


# class GEVDistribution:
#     """
#     Numerically stable GEV implementation using NumPy.
#     Corrects sign errors and tail precision issues.
#     """

#     @staticmethod
#     def cdf(x: np.ndarray, params: GEVParameters) -> np.ndarray:
#         z = (x - params.mu) / params.sigma

#         # Branch handling for Xi ~ 0
#         if abs(params.xi) < 1e-10:
#             return np.exp(-np.exp(-z))

#         # Standard GEV
#         # We must handle the support boundary: 1 + xi*z > 0
#         t = 1 + params.xi * z

#         # Initialize result array
#         res = np.zeros_like(z, dtype=float)

#         # Mask for valid support
#         mask = t > 0

#         # Calculate only on valid support
#         # F(x) = exp( - t^(-1/xi) )
#         res[mask] = np.exp(-np.power(t[mask], -1.0 / params.xi))

#         # Handle boundaries
#         # If xi > 0 (Frechet): x < lower_bound -> F(x) = 0
#         # If xi < 0 (Weibull): x > upper_bound -> F(x) = 1
#         if params.xi < 0:
#             res[~mask] = 1.0
#         # For xi > 0, res[~mask] remains 0.0, which is correct

#         return res

#     @staticmethod
#     def ccdf(x: np.ndarray, params: GEVParameters) -> np.ndarray:
#         """
#         Calculates P(X > x) reliably even for very small probabilities.
#         Uses -expm1(-y) instead of 1 - exp(-y).
#         """
#         z = (x - params.mu) / params.sigma

#         if abs(params.xi) < 1e-10:
#             # Gumbel: 1 - exp(-exp(-z))
#             # Let y = exp(-z). We want 1 - exp(-y) = -expm1(-y)
#             return -np.expm1(-np.exp(-z))

#         t = 1 + params.xi * z
#         mask = t > 0
#         res = np.zeros_like(z, dtype=float)

#         # CCDF = 1 - exp( - t^(-1/xi) )
#         # Let y = t^(-1/xi). We want 1 - exp(-y) -> -expm1(-y)
#         val = np.power(t[mask], -1.0 / params.xi)
#         res[mask] = -np.expm1(-val)

#         # Boundary handling for CCDF
#         # If xi > 0: x < lower_bound -> CDF=0 -> CCDF=1
#         if params.xi > 0:
#             res[~mask] = 1.0
#         # If xi < 0: x > upper_bound -> CDF=1 -> CCDF=0 (already 0)

#         return res

#     @staticmethod
#     def iccdf(p: float, params: GEVParameters) -> float:
#         """
#         Inverse CCDF (Return Level).
#         Input p is Probability of Exceedance (e.g., 0.01 for 100-year event).
#         """
#         # Input validation
#         if not (0 < p < 1):
#             raise ValueError("Probability p must be between 0 and 1")

#         # Use log1p(-p) instead of log(1-p) for better precision if p is small
#         # Though usually p is small, so 1-p is close to 1.
#         # Actually, if p is small (tail), -ln(1-p) ~ p.
#         # But if p is large, 1-p is small.
#         # Let's stick to standard log for simplicity unless p is extremely close to 1.

#         y_p = -np.log(1 - p)

#         if abs(params.xi) < 1e-10:
#             return params.mu - params.sigma * np.log(y_p)
#         else:
#             # x = mu - (sigma/xi) * [1 - y_p^(-xi)]
#             return params.mu - (params.sigma / params.xi) * (
#                 1 - np.power(y_p, -params.xi)
#             )


class BlockMaxima:
    """
    Preprocessing utility for Extreme Value Theory (EVT).
    Converts raw time-series data into Block Maxima.
    """

    @staticmethod
    def extract(data: np.ndarray, block_size: int = 20) -> np.ndarray:
        """
        Extracts block maxima from time-series data.

        Args:
            data: 1D array of measurements (e.g. latencies)
            block_size: Number of items per block.
                       WARNING: Small blocks (<20) may not converge to GEV.

        Returns:
            np.ndarray: Array of maximum values for each block.
        """
        n_total = len(data)
        if n_total < block_size:
            raise ValueError(
                f"Data length ({n_total}) is smaller than block size ({block_size})"
            )

        n_blocks = n_total // block_size
        remainder = n_total % block_size

        # Engineering Safety: Log if we are dropping significant recent data
        if remainder > 0:
            logging.info(
                f"BlockMaxima: Dropping last {remainder} data points to ensure equal block sizes."
            )

        # Vectorized reshaping (Zero-copy view if possible)
        # We perform truncation [: n_blocks * block_size] to ignore the remainder
        reshaped_data = data[: n_blocks * block_size].reshape(n_blocks, block_size)

        # Compute Max along the row axis
        return np.max(reshaped_data, axis=1)


# class MLEEstimator:
#     """Maximum Likelihood Estimator for GEV distribution"""

#     @staticmethod
#     def estimate(data: np.ndarray) -> GEVParameters:
#         """
#         Estimate GEV parameters using MLE

#         Args:
#             data: Block maxima data

#         Returns:
#             Estimated GEV parameters
#         """
#         # Use scipy's genextreme (note: scipy uses c = -xi convention)
#         shape, loc, scale = stats.genextreme.fit(data)

#         return GEVParameters(
#             mu=loc,
#             sigma=scale,
#             xi=-shape,  # Convert scipy convention to paper convention
#         )


# class GoodnessOfFitTest:
#     """Base class for Goodness-of-Fit tests"""

#     def __init__(self, alpha: float = 0.05):
#         """
#         Args:
#             alpha: Significance level (default 0.05)
#         """
#         self.alpha = alpha

#     def statistic(self, data: np.ndarray, params: GEVParameters) -> float:
#         """Compute test statistic"""
#         raise NotImplementedError

#     def critical_value(self, n: int) -> float:
#         """Get critical value for sample size n"""
#         raise NotImplementedError

#     def test(self, data: np.ndarray, params: GEVParameters) -> Tuple[bool, float]:
#         """
#         Perform the test

#         Returns:
#             (reject, statistic): reject is True if null hypothesis is rejected
#         """
#         stat = self.statistic(data, params)
#         cv = self.critical_value(len(data))
#         reject = stat >= cv
#         return reject, stat


# class KolmogorovSmirnovTest(GoodnessOfFitTest):
#     """Kolmogorov-Smirnov test for GEV distribution"""

#     def statistic(self, data: np.ndarray, params: GEVParameters) -> float:
#         """Compute KS statistic: D = sup|F_n(x) - F(x)|"""
#         sorted_data = np.sort(data)
#         n = len(sorted_data)

#         # Empirical CDF values
#         ecdf = np.arange(1, n + 1) / n

#         # Theoretical CDF values
#         theoretical_cdf = GEVDistribution.cdf(sorted_data, params)

#         # KS statistic
#         d = np.max(np.abs(ecdf - theoretical_cdf))
#         return d

#     def critical_value(self, n: int) -> float:
#         """Critical value for KS test (approximate)"""
#         return stats.ksone.ppf(1 - self.alpha, n)


# class CramerVonMisesTest(GoodnessOfFitTest):
#     """Cramér-von Mises test for GEV distribution"""

#     def statistic(self, data: np.ndarray, params: GEVParameters) -> float:
#         """
#         Compute CvM statistic (discrete version from paper):
#         D = 1/(12n) + sum((2i-1)/(2n) - F(x_i))^2
#         """
#         sorted_data = np.sort(data)
#         n = len(sorted_data)

#         # Theoretical CDF values
#         theoretical_cdf = GEVDistribution.cdf(sorted_data, params)

#         # CvM statistic (discrete version)
#         i = np.arange(1, n + 1)
#         differences = (2 * i - 1) / (2 * n) - theoretical_cdf
#         stat = 1 / (12 * n) + np.sum(differences**2)

#         return stat

#     def critical_value(self, n: int) -> float:
#         """Critical value for CvM test (approximate)"""
#         # Critical values from literature for alpha=0.05
#         # These are approximations and may need refinement
#         if self.alpha == 0.05:
#             return 0.461 / np.sqrt(n) + 0.26 / n
#         elif self.alpha == 0.01:
#             return 0.743 / np.sqrt(n) + 0.26 / n
#         else:
#             # Default approximation
#             return 0.461 / np.sqrt(n) + 0.26 / n


# class AndersonDarlingTest(GoodnessOfFitTest):
#     """Anderson-Darling test for GEV distribution"""

#     def statistic(self, data: np.ndarray, params: GEVParameters) -> float:
#         """Compute AD statistic"""
#         sorted_data = np.sort(data)
#         n = len(sorted_data)

#         # Theoretical CDF values
#         F = GEVDistribution.cdf(sorted_data, params)
#         F = np.clip(F, 1e-10, 1 - 1e-10)  # Avoid log(0)

#         # AD statistic
#         i = np.arange(1, n + 1)
#         stat = -n - np.sum((2 * i - 1) * (np.log(F) + np.log(1 - F[::-1]))) / n

#         return stat

#     def critical_value(self, n: int) -> float:
#         """Critical value for AD test (approximate)"""
#         # Adjust for sample size
#         if self.alpha == 0.05:
#             cv = 2.492
#         elif self.alpha == 0.01:
#             cv = 3.857
#         else:
#             cv = 2.492

#         # Adjust for finite sample
#         return cv * (1 + 0.75 / n + 2.25 / n**2)


# class RegionOfAcceptance:
#     """
#     Region of Acceptance calculator for pWCET analysis
#     Based on the paper's methodology
#     """

#     def __init__(self, data: np.ndarray, test: GoodnessOfFitTest, block_size: int = 20):
#         """
#         Args:
#             data: Raw execution time measurements
#             test: Goodness-of-fit test to use
#             block_size: Block size for Block-Maxima filtering
#         """
#         self.raw_data = data
#         self.block_size = block_size
#         self.test = test

#         # Apply Block-Maxima
#         self.bm_data = BlockMaxima.filter(data, block_size)

#         # Estimate initial distribution (Best Fit Point)
#         self.bfp = MLEEstimator.estimate(self.bm_data)

#         # Check if BFP passes the test
#         reject, stat = self.test.test(self.bm_data, self.bfp)
#         self.bfp_valid = not reject
#         self.bfp_statistic = stat

#         # Region will be computed
#         self.region_points: List[GEVParameters] = []
#         self.region_statistics: List[float] = []
#         self.bsp: Optional[GEVParameters] = None

#     def explore_region(
#         self, n_points: int = 40, range_pct: float = 0.10, max_iterations: int = 10
#     ) -> None:
#         """
#         Explore the parameter space to find the Region of Acceptance

#         Args:
#             n_points: Number of points to explore per dimension
#             range_pct: Initial range as percentage of parameter value
#             max_iterations: Max iterations to expand search if needed
#         """
#         print(f"Exploring region around BFP: {self.bfp}")
#         print(f"BFP valid: {self.bfp_valid}, statistic: {self.bfp_statistic:.6f}")

#         # Get critical value for reference
#         cv = self.test.critical_value(len(self.bm_data))
#         print(f"Critical value: {cv:.6f}")

#         # Define search ranges - use absolute values for robustness
#         mu_range = max(abs(self.bfp.mu) * range_pct, 10)  # Minimum absolute range
#         sigma_range = max(abs(self.bfp.sigma) * range_pct, 1)
#         xi_range = max(abs(self.bfp.xi) * range_pct, 0.2)  # Wider initial range for xi

#         for iteration in range(max_iterations):
#             print(
#                 f"\nIteration {iteration + 1}: Exploring ranges μ±{mu_range:.2f}, σ±{sigma_range:.2f}, ξ±{xi_range:.3f}"
#             )

#             # Create parameter grid
#             mu_vals = np.linspace(
#                 self.bfp.mu - mu_range, self.bfp.mu + mu_range, n_points
#             )
#             sigma_vals = np.linspace(
#                 max(0.1, self.bfp.sigma - sigma_range),
#                 self.bfp.sigma + sigma_range,
#                 n_points,
#             )
#             xi_vals = np.linspace(
#                 self.bfp.xi - xi_range, self.bfp.xi + xi_range, n_points
#             )

#             # Explore grid
#             points_found = 0
#             min_stat_seen = float("inf")

#             for mu in mu_vals:
#                 for sigma in sigma_vals:
#                     if sigma <= 0:  # Skip invalid sigma values
#                         continue
#                     for xi in xi_vals:
#                         try:
#                             params = GEVParameters(mu, sigma, xi)
#                             reject, stat = self.test.test(self.bm_data, params)

#                             # Track minimum statistic to guide search
#                             if stat < min_stat_seen:
#                                 min_stat_seen = stat

#                             if not reject:  # Point is in region
#                                 self.region_points.append(params)
#                                 self.region_statistics.append(stat)
#                                 points_found += 1
#                         except (ValueError, RuntimeError, FloatingPointError):
#                             # Skip points that cause numerical issues
#                             continue

#             print(
#                 f"Found {points_found} valid points (min statistic seen: {min_stat_seen:.6f})"
#             )

#             if points_found > 100:  # Good coverage
#                 break
#             elif points_found > 0:  # Some points found, try to expand slightly
#                 if iteration < max_iterations - 1:
#                     range_pct *= 1.3
#                     mu_range = max(abs(self.bfp.mu) * range_pct, 10)
#                     sigma_range = max(abs(self.bfp.sigma) * range_pct, 1)
#                     xi_range = max(abs(self.bfp.xi) * range_pct, 0.2)
#                 else:
#                     break
#             else:
#                 # No points found, expand search more aggressively
#                 range_pct *= 2.0
#                 mu_range = max(abs(self.bfp.mu) * range_pct, 10)
#                 sigma_range = max(abs(self.bfp.sigma) * range_pct, 1)
#                 xi_range = max(abs(self.bfp.xi) * range_pct, 0.2)

#                 # Also try a different center point based on data
#                 if iteration == max_iterations // 2:
#                     print("  Trying alternative estimation method...")
#                     # Use method of moments as alternative
#                     alt_params = self._alternative_estimation()
#                     if alt_params:
#                         self.bfp = alt_params
#                         print(f"  Switched to alternative BFP: {self.bfp}")

#         if len(self.region_points) == 0:
#             print("\n" + "=" * 70)
#             print("WARNING: No valid points found in region!")
#             print("=" * 70)
#             print("Possible reasons:")
#             print("1. Sample size too small (need more data)")
#             print("2. Data violates EVT hypotheses (check i.i.d. with EVT tests)")
#             print("3. Block size inappropriate (try different block_size)")
#             print("4. Test is too strict (try different significance level)")
#             print(f"\nBFP statistic: {self.bfp_statistic:.6f}")
#             print(f"Critical value: {cv:.6f}")
#             print(f"Ratio: {self.bfp_statistic/cv:.2f}x critical value")
#             return

#         # Find Best Statistic Point (BSP)
#         min_idx = np.argmin(self.region_statistics)
#         self.bsp = self.region_points[min_idx]
#         print(f"\n" + "=" * 70)
#         print("REGION FOUND SUCCESSFULLY")
#         print("=" * 70)
#         print(f"Best Statistic Point: {self.bsp}")
#         print(f"BSP statistic: {self.region_statistics[min_idx]:.6f}")
#         print(f"Total points in region: {len(self.region_points)}")

#         # Analyze distribution types
#         xi_vals = [p.xi for p in self.region_points]
#         has_weibull = sum(1 for xi in xi_vals if xi < -0.01)
#         has_gumbel = sum(1 for xi in xi_vals if abs(xi) <= 0.01)
#         has_frechet = sum(1 for xi in xi_vals if xi > 0.01)

#         print(f"\nDistribution types in region:")
#         print(
#             f"  Weibull (ξ<0):  {has_weibull} points ({100*has_weibull/len(xi_vals):.1f}%)"
#         )
#         print(
#             f"  Gumbel (ξ≈0):   {has_gumbel} points ({100*has_gumbel/len(xi_vals):.1f}%)"
#         )
#         print(
#             f"  Fréchet (ξ>0):  {has_frechet} points ({100*has_frechet/len(xi_vals):.1f}%)"
#         )

#     def _alternative_estimation(self) -> Optional[GEVParameters]:
#         """Try probability weighted moments estimation as alternative to MLE"""
#         try:
#             # Simple PWM estimator for GEV
#             sorted_data = np.sort(self.bm_data)
#             n = len(sorted_data)

#             # Compute probability weighted moments
#             b0 = np.mean(sorted_data)
#             weights = np.arange(1, n + 1) / (n + 1)
#             b1 = np.mean(sorted_data * weights)
#             b2 = np.mean(sorted_data * weights * (np.arange(1, n + 1) - 1) / (n))

#             # Estimate parameters (simplified PWM formulas)
#             c = (2 * b1 - b0) / (3 * b2 - b0) - np.log(2) / np.log(3)

#             if abs(c) < 1e-6:
#                 # Gumbel
#                 xi = 0.0
#                 sigma = (2 * b1 - b0) / np.log(2)
#                 mu = b0 - 0.5772 * sigma
#             else:
#                 # Weibull or Fréchet
#                 xi = 7.8590 * c + 2.9554 * c**2
#                 gamma_1 = np.exp(
#                     np.log(abs(xi)) + np.log(abs(1 + xi))
#                 )  # Simplified gamma
#                 sigma = (2 * b1 - b0) * xi / (gamma_1 * (1 - 2 ** (-xi)))
#                 mu = b0 - sigma * (1 - gamma_1) / xi

#             return GEVParameters(mu, sigma, xi)
#         except:
#             return None

#     def compute_bounds(
#         self, wcet_range: Optional[np.ndarray] = None
#     ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
#         """
#         Compute pessimistic and tightest pWCET curves

#         Args:
#             wcet_range: WCET values to evaluate (if None, auto-generated)

#         Returns:
#             (wcet_values, pessimistic_curve, tightest_curve)
#         """
#         if len(self.region_points) == 0:
#             raise ValueError("Region not explored yet. Call explore_region() first.")

#         if wcet_range is None:
#             # Auto-generate range
#             min_val = np.min(self.bm_data)
#             max_val = np.max(self.bm_data)
#             wcet_range = np.linspace(min_val, max_val * 1.5, 1000)

#         # Compute CCDF for all points in region
#         pessimistic = np.zeros_like(wcet_range)
#         tightest = np.ones_like(wcet_range)

#         for params in self.region_points:
#             ccdf = GEVDistribution.ccdf(wcet_range, params)
#             pessimistic = np.maximum(pessimistic, ccdf)
#             tightest = np.minimum(tightest, ccdf)

#         return wcet_range, pessimistic, tightest

#     def compute_uncertainty_area(self) -> float:
#         """
#         Compute area of uncertainty between pessimistic and tightest curves

#         Returns:
#             Area value (may be infinite)
#         """
#         wcet_vals, pess, tight = self.compute_bounds()

#         # Numerical integration
#         area = np.trapz(pess - tight, wcet_vals)

#         return area

#     def robustness_ratio(self, params: GEVParameters, prob: float) -> float:
#         """
#         Compute robustness ratio for a point at given probability

#         Args:
#             params: GEV parameters to evaluate
#             prob: Violation probability

#         Returns:
#             Robustness ratio r ∈ [-1, 1]
#         """
#         wcet_p = GEVDistribution.iccdf(prob, params)

#         # Find WCET from pessimistic and tightest at this probability
#         wcet_vals, pess, tight = self.compute_bounds()

#         # Find closest WCET value in range
#         idx = np.argmin(np.abs(pess - prob))
#         wcet_pessimistic = wcet_vals[idx]

#         idx = np.argmin(np.abs(tight - prob))
#         wcet_tightest = wcet_vals[idx]

#         # Compute distances
#         d_down = abs(wcet_p - wcet_tightest)
#         d_up = abs(wcet_pessimistic - wcet_p)

#         if d_down + d_up < 1e-10:
#             return 0.0

#         r = (d_down - d_up) / (d_down + d_up)
#         return r

#     def plot_region_3d(self):
#         """Plot the 3D Region of Acceptance"""
#         if len(self.region_points) == 0:
#             print("No region to plot. Run explore_region() first.")
#             return

#         fig = plt.figure(figsize=(12, 5))

#         # 3D scatter plot
#         ax1 = fig.add_subplot(121, projection="3d")

#         mu_vals = [p.mu for p in self.region_points]
#         sigma_vals = [p.sigma for p in self.region_points]
#         xi_vals = [p.xi for p in self.region_points]

#         scatter = ax1.scatter(
#             mu_vals,
#             sigma_vals,
#             xi_vals,
#             c=self.region_statistics,
#             cmap="RdYlGn_r",
#             s=20,
#             alpha=0.6,
#         )

#         # Mark BFP and BSP
#         ax1.scatter(
#             [self.bfp.mu],
#             [self.bfp.sigma],
#             [self.bfp.xi],
#             c="red",
#             s=100,
#             marker="*",
#             label="BFP",
#             edgecolors="black",
#         )
#         if self.bsp:
#             ax1.scatter(
#                 [self.bsp.mu],
#                 [self.bsp.sigma],
#                 [self.bsp.xi],
#                 c="blue",
#                 s=100,
#                 marker="*",
#                 label="BSP",
#                 edgecolors="black",
#             )

#         ax1.set_xlabel("μ (location)")
#         ax1.set_ylabel("σ (scale)")
#         ax1.set_zlabel("ξ (shape)")
#         ax1.set_title("Region of Acceptance (3D)")
#         ax1.legend()
#         plt.colorbar(scatter, ax=ax1, label="Test Statistic")

#         # 2D projection (μ vs ξ, collapsing σ)
#         ax2 = fig.add_subplot(122)
#         scatter2 = ax2.scatter(
#             mu_vals, xi_vals, c=self.region_statistics, cmap="RdYlGn_r", s=20, alpha=0.6
#         )
#         ax2.scatter(
#             [self.bfp.mu],
#             [self.bfp.xi],
#             c="red",
#             s=100,
#             marker="*",
#             label="BFP",
#             edgecolors="black",
#         )
#         if self.bsp:
#             ax2.scatter(
#                 [self.bsp.mu],
#                 [self.bsp.xi],
#                 c="blue",
#                 s=100,
#                 marker="*",
#                 label="BSP",
#                 edgecolors="black",
#             )

#         # Mark distribution types
#         ax2.axhline(y=0, color="k", linestyle="--", alpha=0.3, label="Gumbel (ξ=0)")
#         ax2.fill_between(
#             [min(mu_vals), max(mu_vals)],
#             0,
#             max(xi_vals),
#             alpha=0.1,
#             color="red",
#             label="Fréchet (ξ>0)",
#         )
#         ax2.fill_between(
#             [min(mu_vals), max(mu_vals)],
#             min(xi_vals),
#             0,
#             alpha=0.1,
#             color="blue",
#             label="Weibull (ξ<0)",
#         )

#         ax2.set_xlabel("μ (location)")
#         ax2.set_ylabel("ξ (shape)")
#         ax2.set_title("Region of Acceptance (μ vs ξ projection)")
#         ax2.legend()
#         ax2.grid(True, alpha=0.3)
#         plt.colorbar(scatter2, ax=ax2, label="Test Statistic")

#         plt.tight_layout()
#         plt.show()

#     def plot_pwcet_curves(self):
#         """Plot pWCET curves with uncertainty area"""
#         if len(self.region_points) == 0:
#             print("No region to plot. Run explore_region() first.")
#             return

#         wcet_vals, pess, tight = self.compute_bounds()

#         fig, ax = plt.subplots(figsize=(10, 6))

#         # Plot uncertainty area
#         ax.fill_between(
#             wcet_vals, pess, tight, alpha=0.3, color="gray", label="Uncertainty Area"
#         )

#         # Plot bounds
#         ax.plot(wcet_vals, pess, "r-", linewidth=2, label="Pessimistic (pWCET↑)")
#         ax.plot(wcet_vals, tight, "g-", linewidth=2, label="Tightest (pWCET↓)")

#         # Plot BFP and BSP curves
#         bfp_ccdf = GEVDistribution.ccdf(wcet_vals, self.bfp)
#         ax.plot(wcet_vals, bfp_ccdf, "r--", linewidth=1.5, label="BFP", alpha=0.7)

#         if self.bsp:
#             bsp_ccdf = GEVDistribution.ccdf(wcet_vals, self.bsp)
#             ax.plot(wcet_vals, bsp_ccdf, "b--", linewidth=1.5, label="BSP", alpha=0.7)

#         ax.set_xlabel("WCET")
#         ax.set_ylabel("Exceedance Probability P(X > WCET)")
#         ax.set_yscale("log")
#         ax.set_title("pWCET Curves with Uncertainty")
#         ax.legend()
#         ax.grid(True, alpha=0.3)

#         plt.tight_layout()
#         plt.show()

#     def summary(self) -> dict:
#         """Generate summary statistics"""
#         summary = {
#             "n_raw_samples": len(self.raw_data),
#             "n_bm_samples": len(self.bm_data),
#             "block_size": self.block_size,
#             "bfp": self.bfp,
#             "bfp_valid": self.bfp_valid,
#             "bfp_statistic": self.bfp_statistic,
#             "n_region_points": len(self.region_points),
#         }

#         if self.bsp:
#             summary["bsp"] = self.bsp
#             summary["bsp_statistic"] = min(self.region_statistics)

#         if len(self.region_points) > 0:
#             summary["uncertainty_area"] = self.compute_uncertainty_area()

#             # Distribution type analysis
#             xi_vals = [p.xi for p in self.region_points]
#             summary["has_weibull"] = any(xi < 0 for xi in xi_vals)
#             summary["has_gumbel"] = any(abs(xi) < 0.01 for xi in xi_vals)
#             summary["has_frechet"] = any(xi > 0 for xi in xi_vals)

#         return summary

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from dataclasses import dataclass
from typing import Tuple, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)


@dataclass
class GEVParameters:
    mu: float
    sigma: float
    xi: float

    def __repr__(self):
        return f"GEV(μ={self.mu:.3f}, σ={self.sigma:.3f}, ξ={self.xi:.3f})"


class GEVDistribution:
    """Numerically stable GEV implementation."""

    @staticmethod
    def cdf(x: np.ndarray, params: GEVParameters) -> np.ndarray:
        # Ensure inputs are at least 1D for vectorization
        x = np.atleast_1d(x)
        z = (x - params.mu) / params.sigma

        # Branch handling for Xi ~ 0 (Gumbel)
        if abs(params.xi) < 1e-10:
            return np.exp(-np.exp(-z))

        # Standard GEV (Frechet/Weibull)
        t = 1 + params.xi * z
        res = np.zeros_like(z, dtype=float)

        # Mask valid support (1 + xi*z > 0)
        mask = t > 0

        # Vectorized calculation
        res[mask] = np.exp(-np.power(t[mask], -1.0 / params.xi))

        # Handle boundaries: xi < 0 (Weibull) upper bound -> 1.0
        if params.xi < 0:
            res[~mask] = 1.0

        return res

    @staticmethod
    def ccdf(x: np.ndarray, params: GEVParameters) -> np.ndarray:
        """
        Complementary CDF (Survival Function): P(X > x).

        NOTE: We do NOT use (1 - cdf) because of catastrophic cancellation
        when probabilities are small (e.g., < 1e-16).
        We use -expm1(-y) instead.
        """
        x = np.atleast_1d(x)
        z = (x - params.mu) / params.sigma

        # 1. Handle Gumbel Case (xi ~ 0)
        if abs(params.xi) < 1e-10:
            # CDF = exp(-exp(-z))
            # CCDF = 1 - exp(-exp(-z)) = -expm1(-exp(-z))
            return -np.expm1(-np.exp(-z))

        # 2. Standard GEV (Frechet / Weibull)
        t = 1 + params.xi * z

        # Initialize result array
        # Default 0.0 is correct for upper bound of Weibull (xi<0, t<0)
        res = np.zeros_like(z, dtype=float)

        # Valid support mask
        mask = t > 0

        # Calculate robustly on valid support
        # Let y = t^(-1/xi). CDF = exp(-y).
        # CCDF = 1 - exp(-y) = -expm1(-y)
        val = np.power(t[mask], -1.0 / params.xi)
        res[mask] = -np.expm1(-val)

        # 3. Handle Lower Bound of Frechet (xi > 0)
        # If xi > 0 and t < 0, then x is below lower bound.
        # The probability of being greater than x is 1.0.
        if params.xi > 0:
            res[~mask] = 1.0

        return res

    @staticmethod
    def iccdf(p: float, params: GEVParameters) -> float:
        """Inverse CCDF (Return Level) used for pWCET curves[cite: 127]."""
        y_p = -np.log(1 - p)
        if abs(params.xi) < 1e-10:
            return params.mu - params.sigma * np.log(y_p)
        else:
            return params.mu - (params.sigma / params.xi) * (
                1 - np.power(y_p, -params.xi)
            )


class MLEEstimator:
    @staticmethod
    def estimate(data: np.ndarray) -> GEVParameters:
        # Scipy uses c = -xi
        shape, loc, scale = stats.genextreme.fit(data)
        return GEVParameters(mu=loc, sigma=scale, xi=-shape)


class PWMEstimator:
    """
    Probability Weighted Moments Estimator.
    Paper suggests using this when MLE fails to find a valid region point.
    """

    @staticmethod
    def estimate(data: np.ndarray) -> GEVParameters:
        data = np.sort(data)
        n = len(data)

        # Moments calculation
        indices = np.arange(1, n + 1)
        b0 = np.mean(data)
        b1 = np.mean(data * (indices - 1) / (n - 1))
        b2 = np.mean(data * (indices - 1) * (indices - 2) / ((n - 1) * (n - 2)))

        # Hosking's algorithm for GEV parameters
        c = (2 * b1 - b0) / (3 * b2 - b0) - np.log(2) / np.log(3)
        xi = 7.8590 * c + 2.9554 * c**2  # Approximation for shape

        gam = np.exp(
            np.log(abs(xi)) + np.log(abs(1 + xi))
        )  # simplified Gamma function approx part
        # Note: Proper implementation would use scipy.special.gamma
        from scipy.special import gamma

        g1 = gamma(1 + xi)

        sigma = (2 * b1 - b0) * xi / (g1 * (1 - 2 ** (-xi)))
        mu = b0 - sigma * (g1 - 1) / xi

        return GEVParameters(mu, sigma, xi)


class CramerVonMisesTest:
    """
    CvM Test. Paper confirms statistic is correct and converges[cite: 946].
    """

    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha

    def statistic(self, data: np.ndarray, params: GEVParameters) -> float:
        """Equation from Appendix B.2."""
        sorted_data = np.sort(data)
        n = len(sorted_data)
        cdf_vals = GEVDistribution.cdf(sorted_data, params)

        i = np.arange(1, n + 1)
        # Vectorized sum calculation
        diffs = ((2 * i - 1) / (2 * n)) - cdf_vals
        return 1 / (12 * n) + np.sum(diffs**2)

    def critical_value(self, n: int) -> float:
        # Stephens (1970) approximation table for alpha=0.05
        # Note: This assumes KNOWN parameters. Estimated parameters usually
        # result in lower critical values, making this test conservative (safe).
        return 0.461 / np.sqrt(n) + 0.26 / n

    def test(self, data: np.ndarray, params: GEVParameters) -> bool:
        stat = self.statistic(data, params)
        cv = self.critical_value(len(data))
        return stat >= cv  # Reject if statistic > critical value


class RegionOfAcceptance:
    """
    Implements the Region of Acceptance R(X) definition[cite: 221].
    """

    def __init__(self, data: np.ndarray, block_size: int = 20):
        self.data = data
        self.block_size = block_size
        self.bm_data = self._block_maxima(data, block_size)
        self.test_method = CramerVonMisesTest(alpha=0.05)

        # 1. Try MLE First
        self.bfp = MLEEstimator.estimate(self.bm_data)

        # 2. Check if MLE is valid (Paper Section 6.1 D2 issue)
        self.is_mle_valid = not self.test_method.test(self.bm_data, self.bfp)

        # 3. Fallback to PWM if MLE is invalid
        if not self.is_mle_valid:
            logging.warning(
                "MLE point rejected by CvM test. Attempting PWM fallback..."
            )
            try:
                self.bfp = PWMEstimator.estimate(self.bm_data)
            except Exception as e:
                logging.error(f"PWM failed: {e}")

        self.region_points = []
        self.region_stats = []

    def _block_maxima(self, data, block_size):
        n = len(data) // block_size
        return np.max(data[: n * block_size].reshape(n, block_size), axis=1)

    def explore(self, resolution: int = 40, range_pct: float = 0.15):
        """
        Explores the Region R(X).
        Vectorized for performance (Paper explores 64000 points < 10s).
        """
        # Create grid ranges
        mus = np.linspace(
            self.bfp.mu * (1 - range_pct), self.bfp.mu * (1 + range_pct), resolution
        )
        sigmas = np.linspace(
            self.bfp.sigma * (1 - range_pct),
            self.bfp.sigma * (1 + range_pct),
            resolution,
        )
        # Fixed range for Xi often better for stability
        xis = np.linspace(self.bfp.xi - 0.2, self.bfp.xi + 0.2, resolution)

        # Create 3D Meshgrid
        M, S, X = np.meshgrid(mus, sigmas, xis, indexing="ij")

        # Flatten for vectorization
        flat_mu = M.ravel()
        flat_sigma = S.ravel()
        flat_xi = X.ravel()

        logging.info(f"Checking {len(flat_mu)} points...")

        # Pre-calculate Critical Value
        cv = self.test_method.critical_value(len(self.bm_data))

        sorted_data = np.sort(self.bm_data)
        n = len(sorted_data)
        term1 = (2 * np.arange(1, n + 1) - 1) / (2 * n)
        const_term = 1 / (12 * n)

        # Batch processing to prevent memory overflow
        batch_size = 5000  # Reduced slightly to be safe
        for i in range(0, len(flat_mu), batch_size):
            end = min(i + batch_size, len(flat_mu))

            # Extract batch parameters
            b_mu = flat_mu[i:end]
            b_sigma = flat_sigma[i:end]
            b_xi = flat_xi[i:end]

            # Broadcasting CDF: (Batch, N_data)
            # z = (x - mu) / sigma
            z = (sorted_data[None, :] - b_mu[:, None]) / b_sigma[:, None]

            # 1. Calculate 't'
            t = 1 + b_xi[:, None] * z

            # 2. Identify Valid Support
            valid_mask = t > 0

            # 3. Prepare xi values matching the shape of valid_mask
            # We repeat xi for every column to match (Batch, N)
            xi_grid = np.repeat(b_xi, n).reshape(len(b_xi), n)

            # 4. Compute CDF values
            # Initialize with 0.0 (Correct for Frechet lower bound)
            cdf_vals = np.zeros_like(z)

            # --- FIX IS HERE ---
            # We select valid 't' and valid 'xi' values. Both are 1D arrays of the same length 'K'.
            # We assign them to the masked slice of cdf_vals, which is also 1D length 'K'.
            # No reshaping is needed or allowed here.
            valid_t = t[valid_mask]
            valid_xi = xi_grid[valid_mask]

            cdf_vals[valid_mask] = np.exp(-np.power(valid_t, -1.0 / valid_xi))
            # -------------------

            # Handle boundaries (Weibull upper bound)
            # If xi < 0 and we are invalid (t < 0), it means x > upper_bound, so CDF = 1.0
            weibull_mask = (b_xi[:, None] < 0) & (~valid_mask)
            cdf_vals[weibull_mask] = 1.0

            # Calculate CvM Statistic (Batch)
            # D = 1/12n + sum((term1 - cdf)^2) axis=1
            stats_batch = const_term + np.sum((term1[None, :] - cdf_vals) ** 2, axis=1)

            # Filter
            accepted_indices = stats_batch < cv

            if np.any(accepted_indices):
                acc_mu = b_mu[accepted_indices]
                acc_sigma = b_sigma[accepted_indices]
                acc_xi = b_xi[accepted_indices]
                acc_stat = stats_batch[accepted_indices]

                for j in range(len(acc_mu)):
                    self.region_points.append(
                        GEVParameters(acc_mu[j], acc_sigma[j], acc_xi[j])
                    )
                    self.region_stats.append(acc_stat[j])

        logging.info(
            f"Region construction complete. Found {len(self.region_points)} valid points."
        )

    def plot_roa(self):
        if not self.region_points:
            print("No points found.")
            return

        mus = [p.mu for p in self.region_points]
        xis = [p.xi for p in self.region_points]

        plt.figure(figsize=(8, 6))
        plt.scatter(mus, xis, c=self.region_stats, cmap="RdYlGn_r", s=10)
        plt.plot(self.bfp.mu, self.bfp.xi, "b*", markersize=15, label="BFP")
        plt.xlabel("Mu")
        plt.ylabel("Xi")
        plt.title("Region of Acceptance (Projection)")
        plt.colorbar(label="CvM Statistic")
        plt.legend()
        plt.show()

    def plot_3d(self):
        """
        Plots the 3D Region of Acceptance (Mu, Sigma, Xi).
        """
        if not self.region_points:
            print("No points to plot. Run explore() first.")
            return

        # Extract coordinates
        mus = np.array([p.mu for p in self.region_points])
        sigmas = np.array([p.sigma for p in self.region_points])
        xis = np.array([p.xi for p in self.region_points])
        stats = np.array(self.region_stats)

        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")

        # Scatter plot: x=Mu, y=Sigma, z=Xi
        # We use the Statistic value for color (darker = better fit)
        img = ax.scatter(mus, sigmas, xis, c=stats, cmap="viridis_r", s=20, alpha=0.6)

        # Plot the Best Fit Point (BFP) in Red
        ax.scatter(
            [self.bfp.mu],
            [self.bfp.sigma],
            [self.bfp.xi],
            color="red",
            s=100,
            marker="*",
            label="BFP (MLE/PWM)",
        )

        # Labels
        ax.set_xlabel(r"Location ($\mu$)")
        ax.set_ylabel(r"Scale ($\sigma$)")  # This is likely your "Epsilon"
        ax.set_zlabel(r"Shape ($\xi$)")

        # Title and Colorbar
        ax.set_title(
            "Region of Acceptance $R(\mathbb{X})$\n(Valid GEV Parameter Space)"
        )
        cbar = fig.colorbar(img, ax=ax, shrink=0.6)
        cbar.set_label("Test Statistic (Lower is better)")

        ax.legend()
        plt.show()

    def compute_bounds(
        self, wcet_range: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Computes the Pessimistic (Upper) and Tightest (Lower) pWCET curves.
        Fixed broadcasting for vectorization.
        """
        if not self.region_points:
            raise ValueError("Region not explored yet. Call explore() first.")

        # 1. Determine WCET range for evaluation if not provided
        if wcet_range is None:
            min_val = np.min(self.bm_data)
            max_val = np.max(self.bm_data)
            wcet_range = np.linspace(min_val * 0.9, max_val * 1.5, 1000)

        # 2. Vectorized calculation
        # Extract parameters into arrays
        mus = np.array([p.mu for p in self.region_points])
        sigmas = np.array([p.sigma for p in self.region_points])
        xis = np.array([p.xi for p in self.region_points])

        # Reshape for broadcasting (N_points, 1)
        mu = mus[:, None]
        sigma = sigmas[:, None]
        xi = xis[:, None]

        # Prepare WCET range (1, N_wcet)
        x = wcet_range[None, :]

        # Calculate Z-scores and t matrix (N_points, N_wcet)
        z = (x - mu) / sigma
        t = 1 + xi * z

        # Initialize result grid
        ccdf_grid = np.zeros_like(t)

        # Mask valid support (t > 0)
        valid_mask = t > 0

        # --- FIX: Broadcast xi to match the shape of t ---
        # We explicitly expand xi from (N, 1) to (N, 1000) to match valid_mask
        xi_expanded = np.broadcast_to(xi, t.shape)

        # For valid spots:
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            # Now both arrays match the mask shape
            val = np.power(t[valid_mask], -1.0 / xi_expanded[valid_mask])
            ccdf_grid[valid_mask] = -np.expm1(-val)

        # Handle Frechet boundary (xi > 0 and t <= 0 => x < lower_bound => CCDF = 1)
        frechet_boundary_mask = (xi > 0) & (t <= 0)
        ccdf_grid[frechet_boundary_mask] = 1.0

        # 3. Compute Bounds
        pessimistic_curve = np.max(ccdf_grid, axis=0)
        tightest_curve = np.min(ccdf_grid, axis=0)

        return wcet_range, pessimistic_curve, tightest_curve

    def compute_uncertainty_area(self) -> float:
        """
        Calculates the Area of Uncertainty (Definition 4.3).

        A = Integral(pWCET_up(x) - pWCET_down(x)) dx

        Returns:
            float: The area value.
            Note: Returns infinity if any distribution in the region has xi >= 1.
        """
        # Check for infinite mean condition (xi >= 1) mentioned in paper [cite: 455]
        xis = [p.xi for p in self.region_points]
        if any(xi >= 1.0 for xi in xis):
            return float("inf")

        # Compute curves
        wcet_vals, pess, tight = self.compute_bounds()

        # Numerical Integration (Trapezoidal rule)
        # Area = Sum of (Difference_height * dx)
        area = np.trapz(y=(pess - tight), x=wcet_vals)

        return area

    def plot_uncertainty_area(self):
        """
        Plots the Area of Uncertainty, Pessimistic/Tightest curves, and BFP/BSP.
        Visualizes the trade-off described in Definition 4.3 and Figure 7 of the paper.
        """
        if not self.region_points:
            print("No region to plot. Run explore() first.")
            return

        # 1. Get the Bounds and Area
        wcet_vals, pess_curve, tight_curve = self.compute_bounds()
        area_val = self.compute_uncertainty_area()

        # 2. Setup Plot
        plt.figure(figsize=(10, 6))

        # A. Plot the Shaded Uncertainty Area (Gray)
        # This represents the integral A (Definition 4.3) [cite: 440]
        label_area = (
            f"Uncertainty Area (A={area_val:.2e})"
            if area_val != float("inf")
            else "Uncertainty Area (A=∞)"
        )
        plt.fill_between(
            wcet_vals,
            tight_curve,
            pess_curve,
            color="lightgray",
            alpha=0.5,
            label=label_area,
        )

        # B. Plot the Bounds
        # Pessimistic pWCET (Definition 4.1) [cite: 426]
        plt.plot(
            wcet_vals,
            pess_curve,
            "k-",
            linewidth=2,
            label=r"Pessimistic ($pWCET^{\uparrow}$)",
        )
        # Tightest pWCET (Definition 4.2) [cite: 432]
        plt.plot(
            wcet_vals,
            tight_curve,
            "k--",
            linewidth=1,
            label=r"Tightest ($pWCET_{\downarrow}$)",
        )

        # C. Plot BFP (Best Fit Point) - The MLE/PWM result
        # This shows where the estimator landed relative to the bounds
        bfp_ccdf = GEVDistribution.ccdf(wcet_vals, self.bfp)
        plt.plot(wcet_vals, bfp_ccdf, "r-", linewidth=1.5, label="BFP (Estimator)")

        # D. Plot BSP (Best Statistic Point) - The standard reference
        # We find the point in the region with the lowest test statistic
        if self.region_stats:
            best_idx = np.argmin(self.region_stats)
            bsp_params = self.region_points[best_idx]
            bsp_ccdf = GEVDistribution.ccdf(wcet_vals, bsp_params)
            plt.plot(
                wcet_vals, bsp_ccdf, "b-.", linewidth=1.5, label="BSP (Best Statistic)"
            )

        # Formatting
        plt.yscale("log")  # Log scale is standard for pWCET [cite: 125]
        plt.xlabel("Execution Time (WCET)")
        plt.ylabel("Exceedance Probability (log scale)")
        plt.title("pWCET Uncertainty Analysis")
        plt.grid(True, which="both", ls="-", alpha=0.2)
        plt.legend()
        plt.show()
