from airflow.models.dag import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime
import os

# Get the host machine's current directory to mount volumes correctly
HOST_DOCUMENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'documents'))
HOST_ENV_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))

with DAG(
    dag_id='doc_reporter_pipeline',
    start_date=datetime(2025, 1, 1),
    schedule_interval=None,  # We will trigger it manually
    catchup=False,
    tags=['doc-reporter'],
) as dag:

    # Task 1: Run the 'process-app' container
    task_process = DockerOperator(
        task_id='run_processing_service',
        image='process-app:latest', # Assumes image is built locally
        container_name='task_process_pdf',
        command='python process_pdf.py /app/documents/input/sample.pdf /app/documents/output/vector_database.json',
        mounts=[f'{HOST_DOCUMENTS_DIR}:/app/documents'],
        auto_remove=True,
        docker_url='unix://var/run/docker.sock', # Connects to Docker on host
        network_mode='bridge'
    )

    # Task 2: Run the 'analyst-app' container
    task_analyze = DockerOperator(
        task_id='run_analysis_service',
        image='analyst-app:latest',
        container_name='task_analyze_report',
        command='python analyst.py /app/documents/output/vector_database.json /app/documents/output/analyst_report.json',
        mounts=[f'{HOST_DOCUMENTS_DIR}:/app/documents'],
        env_file=HOST_ENV_FILE, # Pass the .env file
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge'
    )

    # Task 3: Run the 'report-app' container
    task_report = DockerOperator(
        task_id='run_reporting_service',
        image='report-app:latest',
        container_name='task_generate_report',
        command='python generate_report.py /app/documents/output/analyst_report.json /app/documents/output/final_report.pdf',
        mounts=[f'{HOST_DOCUMENTS_DIR}:/app/documents'],
        auto_remove=True,
        docker_url='unix://var/run/docker.sock',
        network_mode='bridge'
    )

    # Define the dependency chain
    task_process >> task_analyze >> task_report