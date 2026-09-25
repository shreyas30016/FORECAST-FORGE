"""Phase 5F: Weather Regime Discovery & Train/Serve Validation for Mumbai."""

import asyncio
from datetime import date
import pandas as pd
import numpy as np
import logging

from sklearn.metrics import silhouette_score, confusion_matrix

from forecast_forge.core.models import Location, WeatherVariable
from forecast_forge.historical.extraction import extract_historical_dataset
from forecast_forge.evaluation.regimes import RegimeDiscoveryPipeline, RegimeAssigner

# Reduce noisy logs from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

async def main():
    print("Starting Weather Regime Discovery (Phase 5F)...")
    
    # 1. Fetch Mumbai historical data
    mumbai = Location(latitude=19.0760, longitude=72.8777, name="Mumbai")
    start_date = date(2024, 5, 1)
    end_date = date(2024, 7, 31) # 92 days
    
    print("Extracting historical data from Open-Meteo...")
    models_df, ref_df = await extract_historical_dataset(
        location=mumbai,
        start_date=start_date,
        end_date=end_date,
        lead_time_days=[1, 2, 3] # Fetch fewer days to speed up script
    )
    
    if ref_df.empty or models_df.empty:
        print("Failed to fetch sufficient data.")
        return
        
    print(f"Extracted {len(ref_df)} reference records and {len(models_df)} forecast records.")
    
    # Chronological Split
    ref_df["valid_date"] = ref_df["valid_time"].dt.date
    train_ref = ref_df[ref_df["valid_date"] <= date(2024, 6, 24)].copy()
    val_ref = ref_df[(ref_df["valid_date"] > date(2024, 6, 24)) & (ref_df["valid_date"] <= date(2024, 7, 12))].copy()
    test_ref = ref_df[ref_df["valid_date"] > date(2024, 7, 12)].copy()
    
    print(f"Splits - Train: {len(train_ref)}, Val: {len(val_ref)}, Test: {len(test_ref)}")
    
    # Evaluate K=2..5 on Train
    best_k = 3
    best_pipeline = None
    
    print("\n--- Evaluating K values on Train Split (Reference State) ---")
    for k in range(2, 6):
        pipeline = RegimeDiscoveryPipeline(n_clusters=k, random_state=42)
        try:
            regimes = pipeline.fit(train_ref, training_period="2024-05-01_2024-06-24")
            X = train_ref[["ref_temperature_2m", "ref_relative_humidity_2m", "ref_precipitation", "ref_wind_speed_10m", "ref_cloud_cover"]].dropna().values
            X_scaled = pipeline.scaler.transform(X)
            preds = pipeline.model.predict(X_scaled)
            sil = silhouette_score(X_scaled, preds)
            print(f"\nK={k} | Silhouette: {sil:.3f}")
            for r in regimes:
                print(f"  Regime {r.regime_id} ({r.sample_count} samples) -> {r.description}")
                
            if k == best_k:
                best_pipeline = pipeline
        except Exception as e:
            print(f"Failed K={k}: {e}")
            
    # Persist the selected model
    model_path = ".model_cache/regimes/mumbai_k3.joblib"
    best_pipeline.save(model_path)
    print(f"\nPersisted K={best_k} pipeline to {model_path}")
    
    # Train/Serve Validation on Test Split
    print("\n--- CRITICAL TRAIN/SERVE VALIDATION (Test Split) ---")
    
    # 1. True reference regime
    test_ref_assigned = best_pipeline.transform(test_ref)
    
    # 2. Forecast regime
    test_models = models_df[(models_df["valid_time"].dt.date > date(2024, 7, 12)) & (models_df["lead_time_hours"] == 24.0) & (models_df["model"] == "ecmwf_ifs025")].copy()
    
    assigner = RegimeAssigner(best_pipeline)
    test_models_assigned = assigner.assign_forecast_df(test_models)
    
    # Merge and compare
    merged = pd.merge(test_ref_assigned[["valid_time", "regime_id"]], test_models_assigned[["valid_time", "regime_id"]], on="valid_time", suffixes=("_ref", "_fcst")).dropna()
    
    total = len(merged)
    agreed = (merged["regime_id_ref"] == merged["regime_id_fcst"]).sum()
    print(f"Total Test Samples (24h lead): {total}")
    print(f"Forecast-Reference Regime Agreement: {agreed}/{total} ({agreed/total*100:.1f}%)")
    
    if total > 0:
        cm = confusion_matrix(merged["regime_id_ref"].astype(int), merged["regime_id_fcst"].astype(int), labels=range(best_k))
        print("Confusion Matrix (Row=True ERA5, Col=Fcst IFS):")
        print(cm)
        
    print("\nPhase 5F Discovery Done.")

if __name__ == "__main__":
    asyncio.run(main())
