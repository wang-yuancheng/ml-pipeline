# Machine Learning Pipeline

This repository contains code and materials for a web app that predicts cardiovascular disease risk based on user input.

### Data Science Workflow

The full workflow walks through the end-to-end development of the prediction model, including:

- **Dataset Overview:** Understanding the cardiovascular dataset and problem framing
- **Data Preparation:** Cleaning, transforming, and engineering medically relevant features
- **Exploratory Data Analysis:** Investigating patterns across age, BMI, blood pressure, cholesterol, glucose levels, and lifestyle factors
- **Feature Selection:** Identifying the variables most predictive of cardiovascular disease
- **Modelling:** Training and evaluating multiple scikit-learn models using accuracy, recall, and ROC-AUC to select the final approach

View the complete workflow with visuals, feature reasoning, and model comparison results:  
**[Data Science Workflow](data/EDA%20and%20Model%20Comparison/README.md#data-science-workflow)**

### Project Status

The **AutoML pipeline** portion of the project is not currently functional. This feature was experimental. There are no plans to fix or update it.
However, the **CustomML** page of the web app remains fully functional and can still be used to estimate cardiovascular disease risk.

For historical reference on the AutoML implementation:  
**[Async ML Pipeline](app/README.md#model-integration-with-flask)**

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

# 3 Run the development server
python run.py

# 4 Open the CustomML page in your browser and enter your health measurements
# to estimate cardiovascular disease risk.
```
