# Model integration with Flask

## Base Blueprint (`/`)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/`  | Landing page – choose **AutoML** or **Custom** mode. |
| `POST` | `/`  | Form action from the buttons above. |

## Custom Blueprint (`/cardio…`)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/cardio` | Static form that feeds the *pre-trained* model. |
| `POST` | `/cardio_predict`| Returns CVD probability. |

## Auto Blueprint (`/auto…`)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/auto` | Upload UI for a CSV dataset. |
| `POST` | `/auto/upload` | Saves CSV under a UUID and redirects to preview. |
| `GET`  | `/auto/<job_id>` | DataFrame preview; pick target column. |
| `POST` | `/auto/<job_id>` | Queues training task and shows loading page. |
| `GET`  | `/auto/status/<task_id>` | JSON `{state, ready}` – polled by JS. |
| `GET`  | `/auto/<job_id>/<target>/<task_id>/predict` | Auto-generated form for the selected features. |
| `POST` | `/auto/result` | Renders probability from the freshly trained model. |

## Dataset Requirements

The AutoML pipeline requires datasets to meet the following specifications:

### 1. File Format
* **Format:** Standard CSV (comma-delimited) only. Semicolons, tabs, or Excel files are not supported.
* **Header:** The first row must contain valid string column names.
* **Consistency:** Duplicate column names are not permitted.

### 2. Sizing
* **Rows:** Minimum of 15 rows required to support 3-fold cross-validation.
* **Columns:** Minimum of 2 columns required (1 target + at least 1 feature).

### 3. Content Constraints
* **Target Validity:** The selected target column must contain non-null values.
* **Feature Correlation:** Numeric features with less than 1% (`< 0.01`) correlation to the target are automatically dropped. Training will fail if no features meet this threshold.
* **Categorical Data:** All categorical columns are retained regardless of correlation.

### 4. Data Type Processing
The pipeline automatically detects data types based on the following logic:
* **Text / String:** Treated as **Categorical** (One-Hot Encoded).
* **Numeric (< 15 unique values):** Treated as **Categorical** (e.g., month, grade).
* **Numeric (≥ 15 unique values):** Treated as **Continuous** (scaled).

### 5. Limitations
* **Time Series:** Not supported; rows are treated as independent observations.
* **Unstructured Data:** Images, audio, or long-form text fields are not supported.
* **Multi-Label:** Only single-column prediction targets are supported.

## Request → Prediction Flow

```mermaid
sequenceDiagram
    participant Browser
    participant Flask
    participant Celery
    participant Redis
    participant Model

    Note over Browser,Flask: 1. User uploads dataset
    Browser->>Flask: POST /auto (CSV file)
    activate Flask
    Flask-->>Browser: HTTP 200 → preview page (choose target)
    deactivate Flask

    Note over Browser,Flask: 2. User selects target column
    Browser->>Flask: POST /auto/<job_id> (target)
    activate Flask
    Flask->>Celery: queue train_pipeline_task(job_id, target)
    deactivate Flask

    Note over Celery,Redis: 3. Celery worker picks up task
    activate Celery
    Celery->>Redis: mark task state = PENDING
    Celery->>Celery: run_pipeline(csv_path, target, job_id)
    Celery->>Redis: save trained model path + selected features
    deactivate Celery

    Note over Browser,Flask: 4. Browser polls training status
    loop every 2 seconds
      Browser->>Flask: GET /auto/status/<task_id>
      Flask->>Redis: query task state
      Flask-->>Browser: JSON { state, ready }
    end

    Note over Flask,Browser: 5. Once ready, Flask redirects to prediction form
    Flask-->>Browser: Redirect → /auto/<job_id>/<target>/<task_id>/predict

    Note over Browser,Flask: 6. User submits patient data
    Browser->>Flask: POST /auto/result (patient fields + job_id)
    activate Flask
    Flask->>Model: load pipeline via auto_pipeline(job_id)
    Flask->>Model: pipeline.predict_proba(patient_DataFrame)
    Model-->>Flask: probability
    Flask-->>Browser: HTML page displaying probability
    deactivate Flask