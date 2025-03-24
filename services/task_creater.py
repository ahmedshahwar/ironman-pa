import uuid

def create_task(task_details, identifier):
    """Creates task with a unique task_id."""
    task_id = str(uuid.uuid4)
    task_data = {
        "task_id": task_id,
        **identifier,
        "what": task_details.get("what"),
        "when": task_details.get("when"),
        "how": task_details.get("how"),
        "where": task_details.get("where"),
        "with_whom": task_details.get("with_whom"),
        "status": "pending",
        "priority": task_details.get("priority"),
    }
    
    return task_data