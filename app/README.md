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

Strict requirements for datasets uploaded to the AutoML pipeline:

### 1. File Format Requirements
* **Must be a standard CSV:** The file must use commas (`,`) as separators.
    * *Will Fail:* Files using semicolons (`;`), tabs (`\t`), or Excel (`.xlsx`) files.
* **Must have a Header Row:** The first row of the file must contain column names.
    * *Will Fail:* A file that starts directly with data (e.g., `50, 160, 80...`) because the first row will be treated as the column names.
* **Column Names:** Column names must be strings. Duplicate column names will likely cause pandas or scikit-learn to crash or behave unpredictably.

### 2. Data Size Requirements
* **Minimum Rows:** You need at least **10-15 rows** of data.
    * *Reason:* The code uses `GridSearchCV` with `cv=3` (3-fold cross-validation). If you have fewer than 3 samples per fold, the math breaks.
* **Minimum Columns:** You need at least **2 columns**: 1 Target + 1 Feature.

### 3. Data Content Requirements
* **Target Column:**
    * You must select a target column that actually exists.
    * The target column **cannot be empty** (all nulls). The code executes `df.dropna(subset=[target])`, so if every row has a missing target, you end up with 0 rows -> Crash.
* **Feature Correlation (The "Silent Killer"):**
    * For **Numeric Columns**, the pipeline discards any feature with **less than 1% correlation** (`< 0.01`) to the target.
    * *Strict Rule:* If your dataset is purely numeric and **none** of the columns are even slightly correlated with the target, the pipeline will crash with `ValueError: No valid features found`.
    * *Categorical columns are always kept.*

### 4. Data Type Logic (How it decides)
The system uses "Heuristics" (rules of thumb) to decide how to treat your data. You must understand these to get good results:
* **The "Rule of 15":**
    * If a column is **Text**, it is treated as a **Category** (One-Hot Encoded).
    * If a column is **Number**...
        * ...and has **< 15 unique values**: It becomes a **Category** (e.g., "Month: 1-12", "Grade: 1-5").
        * ...and has **>= 15 unique values**: It stays a **Number** (Continuous).
    * *Why this matters:* If you have a numeric category with 20 classes (e.g., "Zip Code"), the system might mistakenly treat it as a continuous number (like "Age"), which is mathematically wrong for Zip Codes.

### 5. What it CANNOT Do (Limitations)
* **No Time Series:** It treats every row as independent. It cannot predict "Sales tomorrow" based on "Sales yesterday."
* **No Unstructured Data:** It cannot handle images, long blocks of text (like reviews), or audio files.
* **No "Multi-Label" Targets:** You can only predict **one** column at a time.

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