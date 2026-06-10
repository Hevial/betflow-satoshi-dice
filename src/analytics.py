import networkx as nx
import pandas as pd

def isolate_bet_transactions(tx: pd.DataFrame, outputs: pd.DataFrame, mapping: pd.DataFrame, satoshi_dice: pd.DataFrame) -> pd.DataFrame:
    """
    Isolates and annotates the transactions DataFrame (tx) by adding a boolean flag 
    indicating whether the transaction represents a bet toward SatoshiDice.
    """
    satoshi_addresses = satoshi_dice['Address']
    sd_address_ids = mapping[mapping['hash'].isin(satoshi_addresses)]['addressId']
    
    satoshi_dice_outputs = outputs[outputs['addressId'].isin(sd_address_ids)]
    bet_tx_ids = satoshi_dice_outputs['txId'].unique()
    
    # Create a copy to avoid SettingWithCopyWarning
    tx_annotated = tx.copy()
    tx_annotated['is_satoshi_bet'] = tx_annotated['txId'].isin(bet_tx_ids)
    
    return tx_annotated

def aggregate_network_saturation(tx_annotated: pd.DataFrame, period: str = 'M') -> pd.DataFrame:
    """
    Aggregates transactions over time to calculate the network saturation 
    percentage caused by SatoshiDice.
    
    Args:
        tx_annotated: Transactions DataFrame with 'is_satoshi_bet' flag
        period: 'M' for Monthly, 'W' for Weekly
    """
    df = tx_annotated.copy()
    # Timeline creation
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    df['period_group'] = df['datetime'].dt.to_period(period)
    
    # Aggregation
    stats = df.groupby('period_group').agg(
        total_tx=('txId', 'count'),
        satoshi_bets=('is_satoshi_bet', 'sum')
    ).reset_index()
    
    # Metric calculation
    stats['bet_percentage'] = (stats['satoshi_bets'] / stats['total_tx']) * 100
    stats['date_plot'] = stats['period_group'].dt.to_timestamp()
    
    return stats

def compute_address_popularity(outputs: pd.DataFrame, mapping: pd.DataFrame, satoshi_dice: pd.DataFrame, sort_by: str = 'bet_count', ascending: bool = False) -> pd.DataFrame:
    """
    Computes popularity metrics (transaction count and BTC volume) for each SatoshiDice address.
    
    Args:
        outputs: Outputs DataFrame
        mapping: Mapping DataFrame
        satoshi_dice: SatoshiDice metadata DataFrame
        sort_by: Column to sort the results by (e.g., 'bet_count', 'total_volume', 'WinOdds')
        ascending: Sorting order
    """
    # Filter mapping for SatoshiDice addresses only
    satoshi_addresses = satoshi_dice['Address']
    sd_mapping = mapping[mapping['hash'].isin(satoshi_addresses)]
    
    # Merge with outputs to get transaction data
    merged = pd.merge(outputs, sd_mapping, on='addressId')
    
    # Aggregate by address hash
    popularity = merged.groupby('hash').agg(
        bet_count=('txId', 'count'),
        total_volume=('amount', 'sum')
    ).reset_index()

    # Calculate average bet size (Satoshi)
    popularity['avg_bet_size'] = popularity['total_volume'] / popularity['bet_count']
    
    # Merge with metadata to get the human-readable 'Name' and 'WinOdds' for sorting
    popularity = pd.merge(
        popularity, 
        satoshi_dice[['Address', 'Name', 'WinOdds']], 
        left_on='hash', 
        right_on='Address'
    ).drop(columns=['Address'])
    
    if sort_by in popularity.columns:
        return popularity.sort_values(by=sort_by, ascending=ascending)
    
    return popularity

def get_behavioral_data(tx_annotated: pd.DataFrame, target_address_hash: str, outputs: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts granular behavioral data for a specific target address.
    """
    # 1. Get addressId for the hash
    addr_id = mapping[mapping['hash'] == target_address_hash]['addressId'].iloc[0]
    
    # 2. Get all bet transactions directed to this address
    target_tx_ids = outputs[outputs['addressId'] == addr_id]['txId'].unique()
    target_bets = tx_annotated[tx_annotated['txId'].isin(target_tx_ids)].copy()
    
    # 3. Time features
    target_bets['datetime'] = pd.to_datetime(target_bets['timestamp'], unit='s')
    target_bets['hour'] = target_bets['datetime'].dt.hour
    target_bets['day_of_week'] = target_bets['datetime'].dt.dayofweek # 0=Monday
    
    # 4. Get amount for these bets (from outputs)
    amounts = outputs[outputs['txId'].isin(target_tx_ids) & (outputs['addressId'] == addr_id)][['txId', 'amount']]
    target_bets = pd.merge(target_bets, amounts, on='txId')
    
    # 5. Inter-bet intervals (sorted by timestamp)
    target_bets = target_bets.sort_values(by='timestamp')
    target_bets['time_delta'] = target_bets['timestamp'].diff()
    
    return target_bets

def compute_payout_latency(tx_annotated: pd.DataFrame, inputs: pd.DataFrame) -> pd.DataFrame:
    """
    Identifies payout transactions by linking them to bet transactions via inputs.
    Calculates the distance in blocks and seconds.
    """
    # 1. Prepare bets with explicit names
    bets = tx_annotated[tx_annotated['is_satoshi_bet'] == True][['txId', 'blockId', 'timestamp']].copy()
    bets.columns = ['bet_txId', 'bet_blockId', 'bet_timestamp']
    
    # 2. Prepare inputs
    # We only need txId (which is the potential payout) and prevTxId (the source bet)
    payout_inputs = inputs[['txId', 'prevTxId']].copy()
    payout_inputs.columns = ['payout_txId', 'bet_txId']
    
    # 3. Join inputs with bets to link them
    links = pd.merge(payout_inputs, bets, on='bet_txId')
    
    # 4. Join with tx_annotated to get the metadata of the payout transaction
    payout_metadata = tx_annotated[['txId', 'blockId', 'timestamp']].copy()
    payout_metadata.columns = ['payout_txId', 'payout_blockId', 'payout_timestamp']
    
    payouts = pd.merge(links, payout_metadata, on='payout_txId')
    
    # 5. Calculate distances
    payouts['block_distance'] = payouts['payout_blockId'] - payouts['bet_blockId']
    payouts['time_distance'] = payouts['payout_timestamp'] - payouts['bet_timestamp']
    
    return payouts[['bet_txId', 'payout_txId', 'block_distance', 'time_distance']]

def reconstruct_bet_chains(
    inputs: pd.DataFrame,
    outputs: pd.DataFrame,
    mapping: pd.DataFrame,
    satoshi_dice: pd.DataFrame,
    target_name: str = None,
) -> tuple[pd.DataFrame, str]:
    """
    Reconstructs bet chains (sessions) for a target SatoshiDice address using graph analysis.
    Returns a tuple: (chains_df, identified_target_name)
    """
    # 1. Identify Target Address
    if target_name is None:
        popularity = compute_address_popularity(outputs, mapping, satoshi_dice)
        if popularity.empty:
            raise ValueError("No target address found.")
        target_name = popularity.iloc[0]["Name"]

    try:
        target_hash = satoshi_dice.loc[
            satoshi_dice["Name"] == target_name, "Address"
        ].iloc[0]
        target_addr_id = mapping.loc[
            mapping["hash"] == target_hash, "addressId"
        ].iloc[0]
    except IndexError:
        raise ValueError(
            f"Target name '{target_name}' not found in mapping tables."
        )

    # 2. Filter for 'Simple Bets' using native Pandas Index operations (Fast)
    tx_with_1_input = inputs["txId"].value_counts()
    tx_with_1_input = tx_with_1_input[tx_with_1_input == 1].index

    tx_with_2_outputs = outputs["txId"].value_counts()
    tx_with_2_outputs = tx_with_2_outputs[tx_with_2_outputs == 2].index

    # Intersection directly in C-speed via Pandas
    simple_candidates = tx_with_1_input.intersection(tx_with_2_outputs)

    # Filter outputs using a fast boolean mask
    simple_outputs = outputs[outputs["txId"].isin(simple_candidates)]

    # Locate transactions touching the target address
    has_target = simple_outputs.loc[
        simple_outputs["addressId"] == target_addr_id, "txId"
    ].unique()
    simple_bets_ids = set(has_target)

    # 3. Identify Change Outputs
    simple_bets_outputs = simple_outputs[
        simple_outputs["txId"].isin(simple_bets_ids)
    ]
    change_outputs = simple_bets_outputs.loc[
        simple_bets_outputs["addressId"] != target_addr_id,
        ["txId", "position", "addressId"],
    ].rename(columns={"txId": "prevTxId", "position": "prevTxpos"})

    # 4. Optimized Graph Construction
    # Pre-filter inputs to reduce merge overhead significantly
    relevant_inputs = inputs[inputs["txId"].isin(simple_bets_ids)][
        ["txId", "prevTxId", "prevTxpos"]
    ]

    edges_df = pd.merge(
        relevant_inputs, change_outputs, on=["prevTxId", "prevTxpos"]
    )

    # Attach actual address hashes to edges for de-anonymization (Step 6)
    edges_df = pd.merge(edges_df, mapping, on="addressId", how="left")

    # Create graph directly from edgelist (Much faster)
    G = nx.from_pandas_edgelist(
        edges_df,
        source="prevTxId",
        target="txId",
        edge_attr=["hash"],
        create_using=nx.DiGraph,
    )
    # Add isolated bets that didn't generate edges
    G.add_nodes_from(simple_bets_ids)

    # 5. Extract Chains
    chains = []
    for comp in nx.weakly_connected_components(G):
        subgraph = G.subgraph(comp)
        # Extract unique connecting addresses (labels) from edges
        connecting_addresses = set(
            nx.get_edge_attributes(subgraph, "hash").values()
        )
        
        chains.append({
            "nodes": list(comp),
            "length": len(comp),
            "edges_count": subgraph.number_of_edges(),
            "connecting_addresses": list(connecting_addresses)
        })

    return pd.DataFrame(chains), target_name

def analyze_chain_wallets(chains_df: pd.DataFrame, mapping_file: str = '../data/wallet_mapping.csv', force_refresh: bool = False) -> pd.DataFrame:
    """
    Analyzes the wallets associated with the addresses in the provided chains.
    Computes all required metrics for Section 6 of the project:
    - Unique chain identifier
    - Chain length
    - Total number of involved addresses
    - Number of distinct wallets identified
    - Percentage of addresses linked to the predominant wallet
    - Predominant wallet identifier
    - Traceability Conclusion (Single vs Multiple Wallets)
    """
    from src.scraper import build_wallet_mapping

    # 1. Extract all unique addresses present in these chains
    all_addresses = set()
    for addrs in chains_df['connecting_addresses']:
        all_addresses.update(addrs)

    # 2. Call the scraper to get the mapping (with caching)
    wallet_dict = build_wallet_mapping(list(all_addresses), mapping_file=mapping_file, force_refresh=force_refresh)

    # 3. Calculate KPIs for each individual chain
    results = []

    for idx, row in chains_df.iterrows():
        addrs = row['connecting_addresses']

        # Filter the valid addresses we found
        wallets = [wallet_dict.get(a) for a in addrs if wallet_dict.get(a) not in [None, "Unknown"]]

        total_addresses = len(addrs)
        # Use the original DataFrame index for unique identification
        chain_id = f"Chain_{idx}"

        if not wallets:
            results.append({
                "Chain_ID": chain_id,
                "Length": row['length'],
                "Total_Addresses": total_addresses,
                "Distinct_Wallets": 0,
                "Predominant_Wallet": "Unknown",
                "Predominant_Percentage": 0.0,
                "Traceability_Conclusion": "Inconclusive (No Wallets Found)"
            })
            continue

        wallet_counts = pd.Series(wallets).value_counts()
        distinct_wallets = len(wallet_counts)
        predominant_wallet = wallet_counts.index[0]
        predominant_count = wallet_counts.iloc[0]

        # Percentage calculation based on total connecting addresses
        predominant_percentage = (predominant_count / total_addresses) * 100

        # Determine qualitative conclusion as per requirements
        conclusion = "Single Entity (Traceable)" if (distinct_wallets == 1 and predominant_percentage >= 99.0) else "Multiple Entities (Fragmented)"

        results.append({
            "Chain_ID": chain_id,
            "Length": row['length'],
            "Total_Addresses": total_addresses,
            "Distinct_Wallets": distinct_wallets,
            "Predominant_Wallet": predominant_wallet,
            "Predominant_Percentage": round(predominant_percentage, 2),
            "Traceability_Conclusion": conclusion
        })

    return pd.DataFrame(results)