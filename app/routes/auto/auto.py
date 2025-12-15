import pandas as pd
import numpy as np
from flask import Blueprint, render_template, request, url_for, redirect, flash, jsonify
from werkzeug.utils import secure_filename
import os, uuid
from app.models import auto_pipeline
from app.paths import *
from app.model.auto_models.auto_model_train import load_dataset
from app.utils import get_csv_path
from app.tasks.train_tasks import train_pipeline_task
from app.celery_app import celery_app
from celery.result import AsyncResult
from app.renamemap import rename_map

auto_bp = Blueprint('auto', __name__)

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auto_bp.route('/auto', methods=["GET"])
def auto_home():
    return render_template('auto/index.html')

@auto_bp.route('/auto/upload', methods=["POST"])
def auto_upload():
    if 'file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('auto.auto_home'))
    
    file = request.files['file']
    filename_str = file.filename or ""

    if filename_str == '' or not allowed_file(filename_str):
        flash('Please select a valid CSV file', 'error')
        return redirect(url_for('auto.auto_home'))

    filename = secure_filename(filename_str)
    
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_FOLDER_PATH, job_id)
    os.makedirs(job_dir, exist_ok=True)
    save_path = os.path.join(job_dir, filename)
    file.save(save_path)
    flash(f'File saved to {save_path}')

    return redirect(url_for('auto.auto_preview', job_id=job_id))

@auto_bp.route('/auto/<job_id>', methods=["GET", "POST"])
def auto_preview(job_id):
    csv_path = get_csv_path(job_id)
    try:
        df = load_dataset(csv_path)
        flash(f"Dataset loaded: {df.shape[0]} rows × {df.shape[1]} cols")
    except Exception as e:
        df = pd.DataFrame() # Fallback empty DF
        flash(f"Error loading dataset: {e}", "error")

    if request.method == "POST":
        target = request.form.get("target")
        return redirect(url_for('auto.auto_train', job_id=job_id, target=str(target)))

    return render_template('auto/preview.html',
                           job_id=job_id,
                           column=df.columns,
                           tables=[df.head().to_html(classes='data', index=False)])

@auto_bp.route('/auto/<job_id>/<target>/train', methods=['GET', 'POST'])
def auto_train(job_id, target):
    task = train_pipeline_task.delay(job_id, target)
    return render_template('auto/loading.html', job_id=job_id, target=target, task_id=task.id)

@auto_bp.route('/auto/status/<task_id>', methods=['GET'])
def task_status(task_id):
    res = AsyncResult(task_id, app=celery_app)
    return jsonify({'state': res.state, 'ready': res.state == 'SUCCESS'})

@auto_bp.route('/auto/<job_id>/<target>/<task_id>/predict', methods=["GET", "POST"])
def auto_predict(job_id, target, task_id):
    res = AsyncResult(task_id, app=celery_app)
    result = res.get()
    
    if not result:
        flash("Error retrieving training results.")
        return redirect(url_for('auto.auto_home'))

    renamed_target = rename_map.get(target, target)
    selected_features = result.get('selected_features', [])

    return render_template('auto/predict.html',
                           target=renamed_target,
                           features=selected_features,
                           job_id = job_id,
    )

@auto_bp.route('/auto/result', methods=["POST"])
def auto_result():
    job_id = request.form['job_id']
    selected_features = request.form.getlist('features')

    data = {}
    for feat in selected_features:
        raw_val = request.form.get(feat)
        
        # Check if raw_val is None before converting
        if raw_val is None:
            # Handle missing input
            data[feat] = np.nan
        else:
            try:
                data[feat] = float(raw_val)
            except (ValueError, TypeError):
                data[feat] = raw_val

    df_user = pd.DataFrame([data])
    pipeline = auto_pipeline(job_id)

    try:
        # Check if model is classification (has probabilities) or regression
        if hasattr(pipeline, "predict_proba"):
            # Class 1 probability
            pred_val = pipeline.predict_proba(df_user)[0, 1] 
            result = f"{pred_val:.1%}"
        else:
            # Regression numeric output
            pred_val = pipeline.predict(df_user)[0]
            result = f"{pred_val:.2f}"
    except Exception as e:
        print(f"Prediction Error: {e}")
        result = "Error calculating prediction. Please check inputs."

    return render_template('auto/result.html', result=result)