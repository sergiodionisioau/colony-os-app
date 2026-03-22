"""
Colony OS - Task Manager
SQLite-backed task scheduling and execution.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from models.task import Task, TaskStatus, TaskComplexity, TaskType


class TaskManager:
    """Manages tasks with SQLite backend (migratable to Postgres)"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path.home() / ".openclaw" / "colony_os_tasks.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    complexity INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    assigned_to TEXT,
                    preferred_model TEXT,
                    actual_model TEXT,
                    estimated_duration_minutes INTEGER,
                    actual_duration_minutes INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    due_date TIMESTAMP,
                    tags TEXT,  -- JSON array
                    dependencies TEXT,  -- JSON array
                    project_id TEXT,
                    roi_score REAL,
                    prediction_confidence REAL,
                    command TEXT,
                    workdir TEXT,
                    output TEXT,
                    error TEXT,
                    tokens_input INTEGER DEFAULT 0,
                    tokens_output INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0
                )
            """)
            
            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assigned ON tasks(assigned_to)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_project ON tasks(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON tasks(created_at)")
            
            # Task dependencies junction table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT,
                    depends_on_task_id TEXT,
                    PRIMARY KEY (task_id, depends_on_task_id),
                    FOREIGN KEY (task_id) REFERENCES tasks(id),
                    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id)
                )
            """)
            
            conn.commit()
    
    def create_task(self, task: Task) -> Task:
        """Create a new task"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO tasks (
                    id, title, description, type, status, priority, complexity,
                    created_by, assigned_to, preferred_model, estimated_duration_minutes,
                    due_date, tags, dependencies, project_id, command, workdir
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.title, task.description, task.type.value, task.status.value,
                task.priority, task.complexity.value, task.created_by, task.assigned_to,
                task.preferred_model, task.estimated_duration_minutes,
                task.due_date.isoformat() if task.due_date else None,
                json.dumps(task.tags), json.dumps(task.dependencies),
                task.project_id, task.command, task.workdir
            ))
            conn.commit()
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return Task.from_dict(dict(row))
            return None
    
    def update_task(self, task: Task) -> Task:
        """Update existing task"""
        data = task.to_dict()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE tasks SET
                    status = ?, assigned_to = ?, actual_model = ?,
                    started_at = ?, completed_at = ?, actual_duration_minutes = ?,
                    output = ?, error = ?, tokens_input = ?, tokens_output = ?, cost_usd = ?
                WHERE id = ?
            """, (
                data["status"], data["assigned_to"], data["actual_model"],
                data["started_at"], data["completed_at"], data["actual_duration_minutes"],
                data["output"], data["error"], data["tokens_input"],
                data["tokens_output"], data["cost_usd"], task.id
            ))
            conn.commit()
        return task
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with given status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY priority, created_at",
                (status.value,)
            )
            return [Task.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_tasks_for_agent(self, agent_id: str, status: TaskStatus = None) -> List[Task]:
        """Get tasks assigned to an agent"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                cursor = conn.execute(
                    """SELECT * FROM tasks 
                       WHERE assigned_to = ? AND status = ? 
                       ORDER BY priority, created_at""",
                    (agent_id, status.value)
                )
            else:
                cursor = conn.execute(
                    """SELECT * FROM tasks 
                       WHERE assigned_to = ? 
                       ORDER BY priority DESC, created_at""",
                    (agent_id,)
                )
            return [Task.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks ready to execute (no incomplete dependencies)"""
        # Get all TODO tasks
        todo_tasks = self.get_tasks_by_status(TaskStatus.TODO)
        
        ready = []
        for task in todo_tasks:
            if self._dependencies_complete(task):
                ready.append(task)
        
        return ready
    
    def _dependencies_complete(self, task: Task) -> bool:
        """Check if all dependencies are complete"""
        if not task.dependencies:
            return True
        
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join('?' * len(task.dependencies))
            cursor = conn.execute(
                f"SELECT status FROM tasks WHERE id IN ({placeholders})",
                task.dependencies
            )
            statuses = [row[0] for row in cursor.fetchall()]
            return all(s == TaskStatus.DONE.value for s in statuses)
    
    def schedule_task(self, task_id: str) -> Optional[Task]:
        """Move task from BACKLOG to TODO (if dependencies met)"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        if task.status == TaskStatus.BACKLOG and self._dependencies_complete(task):
            task.status = TaskStatus.TODO
            self.update_task(task)
            return task
        
        return None
    
    def start_task(self, task_id: str, agent_id: str, model: str) -> Optional[Task]:
        """Mark task as in progress"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        task.start(agent_id, model)
        self.update_task(task)
        return task
    
    def complete_task(self, task_id: str, output: str = None, 
                      tokens_in: int = 0, tokens_out: int = 0) -> Optional[Task]:
        """Mark task as complete"""
        task = self.get_task(task_id)
        if not task:
            return None
        
        task.complete(output, tokens_in, tokens_out)
        self.update_task(task)
        return task
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count,
                       SUM(tokens_input) as total_input,
                       SUM(tokens_output) as total_output,
                       SUM(cost_usd) as total_cost
                FROM tasks
                GROUP BY status
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = {
                    "count": row[1],
                    "tokens_input": row[2] or 0,
                    "tokens_output": row[3] or 0,
                    "cost_usd": row[4] or 0
                }
            
            # Total counts
            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            total = cursor.fetchone()[0]
            
            return {
                "by_status": stats,
                "total_tasks": total,
                "timestamp": datetime.now().isoformat()
            }
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def export_to_postgres_sql(self) -> str:
        """Generate Postgres-compatible SQL for migration"""
        # This would generate CREATE TABLE statements for Postgres
        # with proper types (UUID, JSONB, etc.)
        pass


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Colony OS Task Manager")
    parser.add_argument("--db", help="Database path")
    subparsers = parser.add_subparsers(dest="command")
    
    # Create task
    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("title", help="Task title")
    create_parser.add_argument("--desc", default="", help="Description")
    create_parser.add_argument("--type", default="coding", choices=[t.value for t in TaskType])
    create_parser.add_argument("--complexity", default="simple", choices=[c.name.lower() for c in TaskComplexity])
    create_parser.add_argument("--priority", type=int, default=3, help="1-5 (1=highest)")
    create_parser.add_argument("--assign", help="Assign to agent")
    create_parser.add_argument("--model", help="Preferred model")
    
    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", choices=[s.value for s in TaskStatus], help="Filter by status")
    list_parser.add_argument("--agent", help="Filter by assigned agent")
    
    # Stats
    subparsers.add_parser("stats", help="Show statistics")
    
    args = parser.parse_args()
    
    tm = TaskManager(args.db)
    
    if args.command == "create":
        task = Task.create(
            title=args.title,
            description=args.desc,
            task_type=TaskType(args.type),
            complexity=TaskComplexity[args.complexity.upper()],
            priority=args.priority,
            assigned_to=args.assign,
            preferred_model=args.model
        )
        tm.create_task(task)
        print(f"Created task: {task.id}")
        print(f"  Title: {task.title}")
        print(f"  Status: {task.status.value}")
        print(f"  Priority: {task.priority}")
        
    elif args.command == "list":
        if args.status:
            tasks = tm.get_tasks_by_status(TaskStatus(args.status))
        elif args.agent:
            tasks = tm.get_tasks_for_agent(args.agent)
        else:
            # Get all tasks
            import sqlite3
            with sqlite3.connect(tm.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM tasks ORDER BY priority, created_at")
                tasks = [Task.from_dict(dict(row)) for row in cursor.fetchall()]
        
        print(f"\n{'ID':<36} {'Status':<12} {'Priority':<8} {'Title':<40}")
        print("-" * 100)
        for task in tasks:
            print(f"{task.id:<36} {task.status.value:<12} {task.priority:<8} {task.title[:40]:<40}")
    
    elif args.command == "stats":
        stats = tm.get_stats()
        print(json.dumps(stats, indent=2))
    
    else:
        parser.print_help()
