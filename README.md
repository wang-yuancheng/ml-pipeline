# Machine Learning Pipeline

This repository contains code and materials for a web app that predicts cardiovascular disease risk and provides an automated ML training pipeline for generic datasets.

## Tech Stack
![My Skills](https://skillicons.dev/icons?i=python,flask,redis,sklearn)

## Data Science Workflow

The full workflow walks through the end-to-end development of the prediction model, including:

- **Dataset Overview:** Understanding the cardiovascular dataset and problem framing
- **Data Preparation:** Cleaning, transforming, and engineering medically relevant features
- **Exploratory Data Analysis:** Investigating patterns across age, BMI, blood pressure, cholesterol, glucose levels, and lifestyle factors
- **Feature Selection:** Identifying the variables most predictive of cardiovascular disease
- **Modelling:** Training and evaluating multiple scikit-learn models using accuracy, recall, and ROC-AUC to select the final approach

View the complete workflow with visuals, feature reasoning, and model comparison results:  
**[Data Science Workflow](data/EDA%20and%20Model%20Comparison/README.md#data-science-workflow)**

### App Features

- **CustomML:** A functional interface using a pre-trained model to estimate cardiovascular disease risk.
- **AutoML Pipeline:** A fully functional asynchronous training system. Upload any CSV dataset, select a target, and the system will automatically preprocess data, tune hyperparameters, and train a model in the background.  
  **⚠️ [View Strict Dataset Requirements](app/README.md#dataset-requirements)**

For details on the system architecture (Flask + Celery + Redis):  
**[Async ML Pipeline Architecture](app/README.md#model-integration-with-flask)**

## Quick Start

```bash
# 1 Clone & install Python dependencies
git clone git@github.com:wang-yuancheng/ml-pipeline.git
cd ml-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2 Set up environment variables
cp .env.example .env
# Then edit .env and add:
# SECRET_KEY="something-super-secret-and-random"

# 3 Start the Background Services
# Open a new terminal for Redis (Acts as both Broker and Result Backend):
redis-server

# Open a new terminal for the Celery Worker:
celery -A app.celery_app worker --loglevel=info

# 4 Run the Web Server
# Open a new terminal for Flask:
python run.py

# 5 Open localhost:5555 in your browser
# - Use "CustomML" for the heart disease demo
# - Use "AutoML" to train on your own CSV files