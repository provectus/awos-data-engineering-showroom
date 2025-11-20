def model(dbt, session):
    import pandas as pd
    import numpy as np
    from sklearn.cluster import KMeans

    # Configuration
    dbt.config(
        materialized='table',
        packages=['scikit-learn', 'pandas', 'numpy']
    )

    # Load dim_stations reference
    stations_df = dbt.ref('dim_stations').df()

    # Filter stations with valid coordinates
    stations_df = stations_df[
        stations_df['latitude'].notna() &
        stations_df['longitude'].notna()
    ].copy()

    # Extract coordinates array
    coords = stations_df[['latitude', 'longitude']].values

    # Run k-means clustering
    kmeans = KMeans(n_clusters=30, random_state=42, n_init=10)
    stations_df['cluster_id'] = kmeans.fit_predict(coords)

    # Calculate cluster centroids from k-means
    centroids = pd.DataFrame(
        kmeans.cluster_centers_,
        columns=['centroid_lat', 'centroid_lon']
    )
    centroids['cluster_id'] = range(30)

    # Merge stations with centroids
    result_df = stations_df.merge(centroids, on='cluster_id', how='left')

    # Calculate Haversine distance (vectorized)
    lat1 = np.radians(result_df['latitude'])
    lon1 = np.radians(result_df['longitude'])
    lat2 = np.radians(result_df['centroid_lat'])
    lon2 = np.radians(result_df['centroid_lon'])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    result_df['distance_from_centroid_km'] = 6371 * c  # Earth radius in km

    # Select and order final columns
    final_columns = [
        'station_id', 'station_name', 'latitude', 'longitude',
        'cluster_id', 'centroid_lat', 'centroid_lon', 'distance_from_centroid_km'
    ]
    return result_df[final_columns].sort_values(['cluster_id', 'distance_from_centroid_km'])
