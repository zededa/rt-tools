import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import genextreme, probplot


def lineplot(df: pd.DataFrame, x_col: str, y_col: str, tag: str):
    # Sort by sample number (important for proper line plotting)
    df = df.sort_values(x_col)

    # Plot
    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=df,
        x=x_col,
        y=y_col,
        # palette="tab10",
        linewidth=2.0,
        alpha=0.9,
    )

    plt.title(f"SessionJitter over Samples for Each Condition {tag}")
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    # plt.legend(title="Condition", loc="upper right")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.show()


def fit_and_plot_gev(
    df: pd.DataFrame,
    column_name: str,
    quantile: float = 0.999999,
    save_fig: bool = False,
):
    """
    Fits a GEV distribution to a specified column in a DataFrame and plots the result,
    including a Q-Q plot and a Return Level plot.

    Args:
        df: The pandas DataFrame containing the data.
        column_name: The name of the column to analyze.
        quantile: The quantile for which to calculate the return value (default: 0.9999).
    """
    # --- 1. Get Data ---
    # Extract the data from the specified DataFrame column
    # .dropna() removes any missing values
    # .values converts it to a numpy array, which scipy expects
    data = df[column_name].dropna().values

    if len(data) == 0:
        print(f"Error: No data found in column '{column_name}' after dropping NaNs.")
        return

    # Ensure all data is positive, as CPU cycles cannot be negative
    data = data[data > 0]

    if len(data) < 10:  # GEV fit is unreliable with very few data points
        print(
            f"Error: Too few positive data points ({len(data)}) in column '{column_name}' for a reliable GEV fit."
        )
        return

    print(f"Analyzing {len(data)} data points from column '{column_name}'.")
    print("-" * 30)

    # --- 2. Fit GEV Distribution ---
    # Fit the Generalized Extreme Value distribution to the data.
    # This returns the three parameters:
    # c: The shape parameter (xi).
    #    c > 0: Heavy tail (Fréchet type)
    #    c = 0: Light tail (Gumbel type)
    #    c < 0: Bounded upper tail (Weibull type)
    # loc: The location parameter (mu).
    # scale: The scale parameter (sigma), must be positive.
    try:
        c, loc, scale = genextreme.fit(data)

        print("GEV Fit Parameters:")
        print(f"  Shape (c):   {c:.4f}")
        print(f"  Location (loc): {loc:.4f}")
        print(f"  Scale (scale): {scale:.4f}")
        print("-" * 30)

        # --- 2b. Calculate and Print Return Value ---
        return_value = genextreme.ppf(quantile, c, loc, scale)
        print(
            f"Return Value at {quantile*100:.4f}% quantile: {return_value:.2f} CPU cycles"
        )
        print("-" * 30)

        # --- 3. Plotting with Seaborn (Histogram + PDF) ---
        sns.set_theme(style="whitegrid")

        # Create the figure and axes
        fig_hist, ax_hist = plt.subplots(figsize=(12, 7))

        # Plot the histogram of the data
        # 'stat="density"' normalizes the histogram so the area sums to 1,
        # allowing it to be compared directly to the probability density function (PDF).
        sns.histplot(
            data,
            bins=30,
            stat="density",
            kde=True,
            ax=ax_hist,
            label="Data Histogram & KDE",
            color="steelblue",
            line_kws={"linestyle": "dashed", "lw": 2, "alpha": 0.7},
        )

        # Generate x-values for the fitted PDF plot
        # Go from the 0.1th percentile to the 99.9th percentile
        xmin = genextreme.ppf(0.001, c, loc, scale)
        xmax = genextreme.ppf(0.999, c, loc, scale)

        x_values = np.linspace(xmin, xmax, 200)

        # Calculate the GEV PDF for the x-values using the fitted parameters
        pdf_values = genextreme.pdf(x_values, c, loc, scale)

        # Plot the fitted GEV PDF as a line
        # We use ax.plot from matplotlib, which seaborn is built on
        ax_hist.plot(
            x_values,
            pdf_values,
            "r-",
            lw=3,
            alpha=0.8,
            label=f"Fitted GEV PDF (c={c:.2f})",
        )

        # --- 4. Final Plot Customization (Histogram) ---
        title = f"GEV Distribution Fit to {column_name.title()} Data"
        ax_hist.set_title(title, fontsize=16)
        ax_hist.set_xlabel(f"Maximal {column_name.title()} (CPU Cycles)", fontsize=12)
        ax_hist.set_ylabel("Density", fontsize=12)
        ax_hist.legend()

        plt.tight_layout()

        # Save the figure
        #
        if save_fig:
            filename_hist = f"{column_name}_gev_fit.png"
            plt.savefig(filename_hist)
            print(f"\nHistogram/PDF plot saved to {filename_hist}")

        # Display the plot
        plt.show()

        # --- 5. Q-Q Plot ---
        fig_qq, ax_qq = plt.subplots(figsize=(8, 6))
        # Create the probability plot (Q-Q plot)
        # It compares data quantiles to the theoretical quantiles of the fitted distribution
        probplot(data, dist=genextreme(c, loc, scale), plot=ax_qq)

        ax_qq.set_title(
            f"Q-Q Plot for {column_name.title()} vs. Fitted GEV", fontsize=14
        )
        ax_qq.set_xlabel("Theoretical GEV Quantiles", fontsize=12)
        ax_qq.set_ylabel("Data Quantiles", fontsize=12)
        plt.tight_layout()

        # Save the figure
        if save_fig:
            filename_qq = f"{column_name}_gev_qq_plot.png"
            plt.savefig(filename_qq)
            print(f"Q-Q plot saved to {filename_qq}")

        plt.show()

        # --- 6. Return Level Plot ---
        fig_rl, ax_rl = plt.subplots(figsize=(10, 7))

        # --- Calculate theoretical return levels ---
        # Generate return periods (e.g., from 1.1 to 1000 events) on a log scale
        T_periods = np.logspace(np.log10(1.1), np.log10(1000), 100)
        # Convert return periods to non-exceedance probabilities (quantiles)
        quantiles_T = 1 - (1 / T_periods)
        # Calculate the return level (the value) for each period
        return_levels = genextreme.ppf(quantiles_T, c, loc, scale)

        # Plot the theoretical fitted line
        ax_rl.plot(
            T_periods, return_levels, "r-", lw=2, label="Fitted GEV Return Level"
        )

        # --- Calculate observed return levels ---
        data_sorted = np.sort(data)
        N = len(data_sorted)
        # Use Gringorten plotting position for empirical probabilities
        p_empirical = (np.arange(1, N + 1) - 0.44) / (N + 0.12)
        # Convert empirical probabilities to empirical return periods
        T_empirical = 1 / (1 - p_empirical)

        # Plot the observed data points
        ax_rl.scatter(
            T_empirical,
            data_sorted,
            alpha=0.6,
            s=10,
            color="steelblue",
            label="Observed Data",
        )

        # --- Customize the return level plot ---
        ax_rl.set_xscale("log")
        ax_rl.set_title(f"Return Level Plot for {column_name.title()}", fontsize=16)
        ax_rl.set_xlabel("Return Period (Log Scale)", fontsize=12)
        ax_rl.set_ylabel("Return Level (CPU Cycles)", fontsize=12)
        ax_rl.legend()
        ax_rl.grid(True, which="both", linestyle="--")
        plt.tight_layout()

        # Save the figure
        if save_fig:
            filename_rl = f"{column_name}_gev_return_level.png"
            plt.savefig(filename_rl)
            print(f"Return Level plot saved to {filename_rl}")

        plt.show()

    except (ValueError, RuntimeError) as e:
        print(f"Error during GEV fit or plotting for column '{column_name}': {e}")
        print(
            "This can sometimes happen if the data is not suitable "
            "or the fit algorithm fails to converge."
        )


def plot_meminfo(df: pd.DataFrame):
    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    # --------------------------------------------
    # 1️⃣  Memory trends over time (key metrics)
    # --------------------------------------------
    plt.figure(figsize=(12, 6))
    cols = ["MemFree", "Cached", "Buffers", "Active", "Inactive"]
    sns.lineplot(data=df[cols].set_index(df["timestamp"]))
    plt.title("Memory Dynamics Over Time (1s sampling)")
    plt.xlabel("Time")
    plt.ylabel("kB")
    plt.legend(cols)
    plt.tight_layout()
    plt.show()

    # --------------------------------------------
    # 2️⃣  Used vs Free memory
    # --------------------------------------------
    df["Used"] = df["MemTotal"] - df["MemFree"]

    plt.figure(figsize=(10, 5))
    sns.lineplot(data=df, x="timestamp", y="MemFree", label="MemFree")
    sns.lineplot(data=df, x="timestamp", y="Used", label="Used")
    plt.title("Used vs Free Memory Over Time")
    plt.xlabel("Time")
    plt.ylabel("kB")
    plt.tight_layout()
    plt.show()

    # --------------------------------------------
    # 3️⃣  Kernel vs User memory (aggregated)
    # --------------------------------------------
    kernel_cols = ["Slab", "PageTables", "KReclaimable", "SReclaimable", "SUnreclaim"]
    user_cols = ["Active(anon)", "Inactive(anon)", "Cached", "Buffers"]

    df["Kernel_mem"] = df[kernel_cols].sum(axis=1)
    df["User_mem"] = df[user_cols].sum(axis=1)

    plt.figure(figsize=(10, 5))
    sns.lineplot(data=df, x="timestamp", y="Kernel_mem", label="Kernel_mem")
    sns.lineplot(data=df, x="timestamp", y="User_mem", label="User_mem")
    plt.title("Kernel vs User Memory Over Time")
    plt.xlabel("Time")
    plt.ylabel("kB")
    plt.tight_layout()
    plt.show()

    # --------------------------------------------
    # 4️⃣  Volatility / Stability Check (exclude timestamp)
    # --------------------------------------------
    num_df = df.select_dtypes(include="number")  # drops timestamp safely
    stds = num_df.std().sort_values(ascending=False).head(15)

    plt.figure(figsize=(10, 6))
    sns.barplot(x=stds.values, y=stds.index, palette="crest")
    plt.title("Most Volatile Memory Metrics (RT Stability Check)")
    plt.xlabel("Standard Deviation (kB)")
    plt.ylabel("")
    plt.tight_layout()
    plt.show()

    # --------------------------------------------
    # 5️⃣  Correlation Heatmap
    # --------------------------------------------
    plt.figure(figsize=(12, 10))
    corr = num_df.corr(numeric_only=True)
    sns.heatmap(corr, cmap="coolwarm", center=0)
    plt.title("Correlation Heatmap of Memory Metrics")
    plt.tight_layout()
    plt.show()

    # --------------------------------------------
    # 6️⃣  Pairplot (sampled for speed)
    # --------------------------------------------
    sampled = df[["MemFree", "Cached", "Active", "Inactive", "Buffers"]].sample(
        min(300, len(df))
    )
    sns.pairplot(sampled, kind="scatter", diag_kind="kde")
    plt.suptitle("Pairwise Relationships Between Key Memory Metrics", y=1.02)
    plt.show()

    # --------------------------------------------
    # 7️⃣  Rolling Average Trend
    # --------------------------------------------
    window = 10  # seconds
    df["MemFree_avg"] = df["MemFree"].rolling(window).mean()

    plt.figure(figsize=(10, 5))
    sns.lineplot(data=df, x="timestamp", y="MemFree", label="MemFree")
    sns.lineplot(
        data=df, x="timestamp", y="MemFree_avg", label=f"{window}s Rolling Avg"
    )
    plt.title(f"MemFree with {window}s Rolling Average (RT Fit)")
    plt.xlabel("Time")
    plt.ylabel("kB")
    plt.tight_layout()
    plt.show()


def plot_avg_cpu_temp(cpu_monitor_df: pd.DataFrame, window_size: int = 150):
    cpu_monitor_df["timestamp"] = pd.to_datetime(cpu_monitor_df["timestamp"])
    cpu_monitor_df = cpu_monitor_df.set_index("timestamp")
    cpu_monitor_df["average"] = cpu_monitor_df.mean(axis=1)

    cpu_monitor_df["average_rolling"] = (
        cpu_monitor_df["average"].rolling(window=window_size, min_periods=1).mean()
    )

    # Plot
    plt.figure(figsize=(12, 6))
    sns.lineplot(
        data=cpu_monitor_df,
        x=cpu_monitor_df.index,
        y="average_rolling",
        linewidth=2,
        color="tab:blue",
    )

    plt.title(
        f"Rolling Mean (window={window_size}) of Average CPU Temperature",
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel("Timestamp")
    plt.ylabel("Rolling Average CPU Temperature")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()
