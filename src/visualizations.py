import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import seaborn as sns
import pandas as pd
import numpy as np

def _format_k_m(x, pos):
    """Helper to format large numbers for labels (e.g. 1.2M, 50k)"""
    if x >= 1e6:
        return f'{x*1e-6:.1f}M'
    elif x >= 1e3:
        return f'{x*1e-3:.0f}k'
    return f'{x:.0f}'

def _convert_to_btc(satoshi_value,pos):
    """Helper to convert Satoshi to BTC"""
    return f'{satoshi_value * 1e-8:,.4f}'.rstrip('0').rstrip('.')

def plot_dual_saturation_panel(monthly_stats: pd.DataFrame, weekly_stats: pd.DataFrame, start_date: str = '2012-02-01'):
    """
    Renders an enhanced dual-panel plot showing adoption on macro and micro granularities.
    Includes area fills, peak annotations, and historical markers.
    """
    plot_start_date = pd.Timestamp(start_date)
    monthly_plot = monthly_stats[monthly_stats['date_plot'] >= plot_start_date].copy()
    weekly_plot = weekly_stats[weekly_stats['date_plot'] >= plot_start_date].copy()

    # Calculate Moving Average for the weekly plot (4 weeks)
    weekly_plot['rolling_bet_pct'] = weekly_plot['bet_percentage'].rolling(window=4, min_periods=1).mean()

    fig, axes = plt.subplots(1, 2, figsize=(18, 6), sharey=True)
    sns.set_style("whitegrid")

    # --- MONTHLY PLOT ---
    sns.lineplot(data=monthly_plot, x='date_plot', y='bet_percentage', marker='o', color='maroon', ax=axes[0], linewidth=2.5, label='Monthly Saturation')
    axes[0].fill_between(monthly_plot['date_plot'], monthly_plot['bet_percentage'], color='maroon', alpha=0.15)
    
    # Peak Annotation
    max_m = monthly_plot.loc[monthly_plot['bet_percentage'].idxmax()]
    axes[0].annotate(f"Peak: {max_m['bet_percentage']:.1f}%", 
                     xy=(max_m['date_plot'], max_m['bet_percentage']),
                     xytext=(10, 10), textcoords='offset points',
                     arrowprops=dict(arrowstyle='->', color='black'),
                     fontsize=10, fontweight='bold')

    axes[0].set_title("Network Saturation (Monthly Aggregation)", fontsize=14, fontweight='bold', pad=15)
    
    # --- WEEKLY PLOT ---
    # Area fill on RAW data (Primary)
    axes[1].fill_between(weekly_plot['date_plot'], weekly_plot['bet_percentage'], color='navy', alpha=0.1)
    
    # Peak Annotation
    max_w = weekly_plot.loc[weekly_plot['bet_percentage'].idxmax()]
    axes[1].annotate(f"Peak: {max_w['bet_percentage']:.1f}%", 
                     xy=(max_w['date_plot'], max_w['bet_percentage']),
                     xytext=(18, 4), textcoords='offset points',
                     arrowprops=dict(arrowstyle='->', color='black'),
                     fontsize=10, fontweight='bold')


    # RAW Line: Navy, Bold, with Markers
    sns.lineplot(data=weekly_plot, x='date_plot', y='bet_percentage', color='navy', ax=axes[1], linewidth=2, marker='o', markersize=4, label='Raw Weekly (Impact)')
    
    # SMA Line: Steelblue, thinner, for smooth trend
    sns.lineplot(data=weekly_plot, x='date_plot', y='rolling_bet_pct', color='steelblue', ax=axes[1], linewidth=2, label='4-Week SMA (Trend)')

    axes[1].set_title("Network Saturation (Weekly Impact & Trend)", fontsize=14, fontweight='bold', pad=15)
    
    # --- COMMON FORMATTING ---
    halving_date = pd.Timestamp('2012-11-28')
    for i, ax in enumerate(axes):
        ax.set_xlabel("Timeline", fontsize=12)
        ax.set_ylabel("Bet Transactions / Total (%)", fontsize=12)
        
        if i == 0:
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        else:
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %Y'))
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, which='major', axis='both', linestyle='--', alpha=0.4)
        
        # Percentage formatter for Y axis
        ax.yaxis.set_major_formatter(ticker.PercentFormatter())

    plt.tight_layout()
    plt.show()

def plot_address_popularity(popularity: pd.DataFrame, top_n: int = 5):
    """
    Plots horizontal bar charts comparing address popularity by frequency and volume.
    Conversion from Satoshi to BTC (1e-8) is applied for economic clarity.
    """
    plot_df = popularity.head(top_n).copy()
    
    fig, axd = plt.subplot_mosaic([['freq', 'vol'],
                                   ['ratio', 'ratio']],
                                  figsize=(20, 12))
    
    axes = [axd['freq'], axd['vol'], axd['ratio']]
    sns.set_style("whitegrid")

    # Chart 1: Frequency (Count)
    sns.barplot(data=plot_df, y='Name', x='bet_count', palette='viridis', ax=axes[0], hue='Name', legend=False)
    axes[0].set_title('Frequency Distribution by Address Category (Number of Bets)', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Total Number of Bets (Units)', fontsize=12)
    axes[0].set_ylabel('SatoshiDice Address Name', fontsize=12)
    axes[0].xaxis.set_major_formatter(ticker.FuncFormatter(_format_k_m))
    axes[0].xaxis.set_major_locator(ticker.MaxNLocator(nbins=12))

    # Chart 2: Volume (BTC)
    sns.barplot(data=plot_df, y='Name', x='total_volume', palette='magma', ax=axes[1], hue='Name', legend=False)
    axes[1].set_title('Volume Distribution by Address Category (Total BTC) - Square Root Scale', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Total Volume (BTC)', fontsize=12)
    axes[1].set_ylabel('')
    axes[1].set_xscale("function", functions=(lambda x: np.sqrt(x), lambda x: x**2))

    axes[1].set_xticks([0, 1*1e11, 5*1e12 , 1*1e12, 1*1e13, 2*1e13, 3* 1e13, 4*1e13, 5*1e13])
    axes[1].xaxis.set_major_formatter(ticker.FuncFormatter(_convert_to_btc))
    
   
    # Chart 3: Average Bet Size (BTC)
    sns.barplot(data=plot_df, y='Name', x='avg_bet_size', palette='coolwarm', ax=axes[2], hue='Name', legend=False)
    axes[2].set_title('Average Bet Size Distribution by Address Category (BTC per Bet)', fontsize=14, fontweight='bold')
    axes[2].set_xlabel('Average Amount per Bet (BTC)', fontsize=12)
    axes[2].set_ylabel('SatoshiDice Address Name', fontsize=12)
    axes[2].xaxis.set_major_formatter(ticker.FuncFormatter(_convert_to_btc))

    plt.tight_layout()
    plt.show()

def plot_payout_latency(payouts: pd.DataFrame):
    """
    Plots the distribution of block and time distances between bets and payouts.
    """
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    sns.set_style("whitegrid")

    # Plot 1: Block Distance
    block_counts = payouts['block_distance'].value_counts().sort_index().head(10)
    sns.barplot(x=block_counts.index, y=block_counts.values, ax=axes[0], palette='viridis', hue=block_counts.index, legend=False)
    axes[0].set_title('Distribution of Block Latency - Log Scale', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Block Distance (Blocks)', fontsize=12)
    axes[0].set_ylabel('Number of Payouts', fontsize=12)
    
    axes[0].set_yscale("log")
    axes[0].yaxis.set_major_formatter(ticker.FuncFormatter(_format_k_m))
    axes[0].yaxis.set_major_locator(ticker.LogLocator(base=10.0, subs=[1,2,3,5], numticks=10))

    # Plot 2: Time Distance
    clean_time = payouts[payouts['time_distance'] < 7200]['time_distance'] / 60 
    sns.histplot(clean_time, bins=50, color='teal', ax=axes[1])
    axes[1].set_title('Distribution of Time Latency (Minutes) - Log Scale', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Time Distance (Minutes)', fontsize=12)
    axes[1].set_ylabel('Number of Payouts', fontsize=12)

    axes[1].set_yscale("log")
    axes[1].yaxis.set_major_formatter(ticker.FuncFormatter(_format_k_m))
    axes[1].yaxis.set_major_locator(ticker.LogLocator(base=10.0, subs=[1,2,3,5], numticks=10))

    plt.tight_layout()
    plt.show()

def plot_behavioral_profiling(behavioral_dict: dict):
    """
    Plots a multi-panel comparison of behavior for top addresses.
    behavioral_dict: { 'AddressName': DataFrame from get_behavioral_data }
    """
    n_addr = len(behavioral_dict)
    fig, axes = plt.subplots(n_addr, 3, figsize=(22, 6 * n_addr))
    sns.set_style("whitegrid")
    
    for i, (name, data) in enumerate(behavioral_dict.items()):
        # Column 1: Hourly Distribution
        sns.histplot(data['hour'], bins=24, kde=True, ax=axes[i, 0], color='skyblue')
        axes[i, 0].set_title(f'{name}: Hourly Bet Distribution', fontweight='bold')
        axes[i, 0].set_xlabel('Hour of Day (0-23)')
        
        # Column 2: Fee-Amount Correlation (Convert Satoshi to BTC)
        sns.scatterplot(x=data['amount'], y=data['fee'], ax=axes[i, 1], alpha=0.5, color='salmon')
        axes[i, 1].set_title(f'{name}: Fee vs Amount Correlation', fontweight='bold')
        axes[i, 1].set_xlabel('Bet Amount (BTC)')
        axes[i, 1].set_ylabel('Transaction Fee (BTC)')
        axes[i, 1].xaxis.set_major_formatter(ticker.FuncFormatter(_convert_to_btc))
        axes[i, 1].yaxis.set_major_formatter(ticker.FuncFormatter(_convert_to_btc))

        # Column 3: Inter-bet Intervals
        clean_deltas = data[data['time_delta'] < 3600]['time_delta'] / 60 # minutes
        sns.histplot(clean_deltas, bins=50, ax=axes[i, 2], color='teal')
        axes[i, 2].set_title(f'{name}: Inter-bet Intervals - Log Scale', fontweight='bold')
        axes[i, 2].set_xlabel('Minutes between consecutive bets')
        axes[i, 2].set_yscale("log")
        axes[i, 2].yaxis.set_major_formatter(ticker.ScalarFormatter())
        axes[i, 2].yaxis.set_major_locator(ticker.LogLocator(base=10.0, subs=[1,2,5], numticks=10))
        
    plt.tight_layout()
    plt.show()

def plot_chain_length_distribution(chains_df: pd.DataFrame, target_name: str):
    """
    Plots the distribution of session lengths (bet chains) for a specific target address.
    Uses a scatter plot with log scale on Y to highlight the frequency of different chain lengths.
    Annotates key statistics and highlights the median and average chain lengths.
    """
    

    sns.set_style("whitegrid")

    sessions = chains_df[chains_df['length'] > 1].copy()

    if sessions.empty:
        print(f"No multi-transaction sessions found for {target_name}.")
        return

    # Frequency distribution
    freq = sessions['length'].value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(14, 7))

    # SCATTER PLOT 
    ax.scatter(
        freq.index,
        freq.values,
        s=25,
        color='teal',
        alpha=0.8
    )

    # Log scale only on Y 
    ax.set_yscale('log')
    ax.yaxis.set_major_formatter(ticker.ScalarFormatter())

    # Stats
    avg_len = sessions['length'].mean()
    med_len = sessions['length'].median()

    top_5 = sessions['length'].nlargest(5).tolist()

    stats_text = (
        f"--- GLOBAL STATS ---\n"
        f"Total Sessions: {len(sessions):,}\n"
        f"Average Length: {avg_len:.2f}\n"
        f"Median Length: {med_len:.0f}\n\n"
        f"--- LONGEST CHAINS ---\n"
        f"1. {top_5[0]} bets\n"
        f"2. {top_5[1]} bets\n"
        f"3. {top_5[2]} bets\n"
        f"4. {top_5[3]} bets\n"
        f"5. {top_5[4]} bets"
    )

    props = dict(
        boxstyle='round,pad=0.8',
        facecolor='ghostwhite',
        alpha=0.9,
        edgecolor='teal'
    )

    ax.text(
        0.98, 0.86,
        stats_text,
        transform=ax.transAxes,
        fontsize=11,
        fontfamily='monospace',
        verticalalignment='top',
        horizontalalignment='right',
        bbox=props
    )

    # Reference lines
    ax.axvline(med_len, color='crimson', linestyle='--', label=f'Median: {med_len:.0f}')
    ax.axvline(avg_len, color='navy', linestyle='--', label=f'Average: {avg_len:.2f}')

    ax.set_title(f"Session Length Distribution for {target_name}", fontsize=16, fontweight='bold')
    ax.set_xlabel("Session Length (Number of Bets)")
    ax.set_ylabel("Number of Sessions (log scale)")

    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.show()