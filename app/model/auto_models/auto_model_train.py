import pandas as pd
import numpy as np
import os
import joblib

from app.paths import AUTO_MODELS_FOLDER_PATH
from app.renamemap import rename_map
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.utils.multiclass import type_of_target

def load_dataset(save_path):
    return pd.read_csv(save_path)

def clean_dataset(df, target):
    # Rename if it matches our known heart disease dataset
    df = df.rename(columns=rename_map)

    if target in rename_map:
        target = rename_map[target]
    
    # Drop rows where target is missing
    df = df.dropna(subset=[target])
    
    return df, target

def get_column_types(df, target):
    feature_cols = [col for col in df.columns if col != target]
    
    cont_cols = []
    cat_cols = []

    for col in feature_cols:
        # If it's a number but has very few unique values (like 1, 2, 3), treat as category
        if pd.api.types.is_numeric_dtype(df[col]):
            if df[col].nunique() < 15:
                cat_cols.append(col)
            else:
                cont_cols.append(col)
        else:
            cat_cols.append(col)
            
    return feature_cols, cont_cols, cat_cols

def run_pipeline(csv_path, target, job_id):
    # Load and Clean
    df = load_dataset(csv_path)
    df, target = clean_dataset(df, target)
    
    # Dynamic Feature Selection and Type Detection
    feature_cols, cont_cols, cat_cols = get_column_types(df, target)
    
    # Filter continuous features by correlation
    if cont_cols:
        corrs = df[cont_cols].corrwith(df[target]).abs()
        cont_cols = corrs[corrs > 0.01].index.tolist()
        
    # Convert categorical columns to string.
    if cat_cols:
        df[cat_cols] = df[cat_cols].astype(str)

    selected_features = cont_cols + cat_cols
    if not selected_features:
        raise ValueError("No valid features found after filtering.")

    X = df[selected_features]
    y = df[target]
    y_type = type_of_target(y)

    # Preprocessing Pipeline
    transformers = []
    
    if cont_cols:
        num_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='mean')),
            ('scaler', StandardScaler())
        ])
        transformers.append(("num", num_pipeline, cont_cols))

    if cat_cols:
        cat_pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
            ('ohe', OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False))
        ])
        transformers.append(("cat", cat_pipeline, cat_cols))

    preprocessor = ColumnTransformer(transformers, remainder="drop")

    # Pipeline
    if y_type == "continuous":
        Model = MLPRegressor
        scoring = "neg_mean_squared_error"
    else:
        Model = MLPClassifier
        scoring = "accuracy"

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('model', Model(random_state=42, max_iter=500, early_stopping=True))
    ])

    # Grid Search
    param_grid = {
        "model__hidden_layer_sizes": [(100,), (64, 32)],
        "model__learning_rate_init": [1e-3],
        "model__alpha": [1e-4, 1e-3],
    }

    grid = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        cv=3,
        n_jobs=1, 
        scoring=scoring,
        verbose=1
    )

    print(f"Starting generic AutoML training for Job {job_id}...")
    grid.fit(X, y)
    
    # Save
    best_model = grid.best_estimator_
    model_dir = os.path.join(AUTO_MODELS_FOLDER_PATH, job_id)
    os.makedirs(model_dir, exist_ok=True)
    path = os.path.join(str(model_dir), 'model.pkl')
    
    joblib.dump(best_model, path)
    print(f"Model saved to {path}")
    
    return path, selected_features