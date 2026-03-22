"""
Colony OS - Web API Wrapper
Flask-based REST API for the task manager.
"""

import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from task_manager import TaskManager

app = Flask(__name__)
task_manager = TaskManager(db_path=os.getenv('DATABASE_PATH', '/app/data/colony_os_tasks.db'))

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "app": "colony-os"})

@app.route('/tasks', methods=['GET'])
def list_tasks():
    """List all tasks"""
    tasks = task_manager.list_tasks()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    data = request.json
    task = task_manager.create_task(
        title=data.get('title'),
        description=data.get('description'),
        task_type=data.get('type', 'general'),
        priority=data.get('priority', 3),
        complexity=data.get('complexity', 2),
        created_by=data.get('created_by', 'system'),
        tags=data.get('tags', [])
    )
    return jsonify(task.to_dict()), 201

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task"""
    task = task_manager.get_task(task_id)
    if task:
        return jsonify(task.to_dict())
    return jsonify({"error": "Task not found"}), 404

@app.route('/tasks/<task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task as complete"""
    success = task_manager.complete_task(task_id)
    if success:
        return jsonify({"status": "completed"})
    return jsonify({"error": "Task not found"}), 404

@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        "app": "Colony OS",
        "version": "0.1.0",
        "endpoints": [
            "/health",
            "/tasks",
            "/tasks/<id>",
            "/tasks/<id>/complete"
        ]
    })

if __name__ == '__main__':
    port = int(os.getenv('APP_PORT', 8080))
    app.run(host='0.0.0.0', port=port)
