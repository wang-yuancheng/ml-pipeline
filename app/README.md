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
## Request → Prediction Flow

Below is an improved sequence diagram that clearly shows each step from uploading a CSV to receiving a prediction. It groups component interactions and labels each arrow more consistently.

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
```
## Summary of the Workflow
1. **Flask (Web Server)**  
   - Receives user requests (e.g., file upload, form submission).  
   - Enqueues long-running tasks in Celery via RabbitMQ.  
   - Polls Redis for task status and retrieves results.  
   - Renders HTML pages and returns responses to the browser.

2. **RabbitMQ (Broker)**  
   - Acts as a FIFO queue for Celery tasks.  
   - Buffers tasks when workers are busy.  
   - Ensures reliable delivery of each training job message to a Celery worker.

3. **Celery (Worker Manager)**  
   - Consumes tasks from RabbitMQ.  
   - Executes Python functions asynchronously (`train_pipeline_task`, etc.).  
   - Pushes results and task state updates into Redis.

4. **Redis (Result Backend)**  
   - Stores each task’s current state (`PENDING`, `STARTED`, `SUCCESS`, `FAILURE`).  
   - Keeps the return value (e.g., model path and selected features) for Flask to fetch.  
---
# Full scikit-learn pipeline
### **Dataset to use: [cardio_train.csv](../data/cardio_train.csv)**

## Full scikit-learn pipeline

```mermaid
graph TD
    A["Read raw CSV into a DataFrame"] --> B["Rename columns and drop rows with invalid vitals"]
    B --> C["Remove outliers and select features based on correlation with the target"]
    C --> D["Split selected features into numeric vs. categorical"]
    D --> E["Scale numeric features and one‐hot encode categorical features"]
    E --> F["Train an MLPClassifier for classification targets or an MLPRegressor for continuous targets."] 
    F --> G["Perform hyperparameter tuning with GridSearchCV"]
    G --> H["Build and fit pipeline combining preprocessing and trained model"]
    H --> I["Saves trained models with joblib under a UUID"]
```
