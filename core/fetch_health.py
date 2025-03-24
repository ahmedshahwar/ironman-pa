from datetime import datetime

def fetch_health(data):
    """Extracts and processes health metrics data from the given input dictionary."""
    
    # Initialize a dictionary to store processed health data
    processed_data = {
        "timestamp": None,
        "flights_climbed": None,
        "active_energy": None,
        "basal_energy_burned": None,
        "step_count": None,
        "walking_running_distance": None,
        "headphone_audio_exposure": None,
        "walking_step_length": None,
        "walking_speed": None,
        "walking_asymmetry_percentage": None,
        "walking_double_support_percentage": None,
        "hr": None,
        "message": None
    }
    
    first_metric_date = None  # Variable to store the date of the first recorded metric
    metrics = data.get("data", {}).get("metrics", [])

    # Iterate through available metrics
    for metric in metrics:
        name = metric.get("name", "").lower()
        unit = metric.get("units", "")

        if not metric.get("data"):
            continue  # Skip empty metrics

        latest_entry = metric["data"][0]
        value = latest_entry.get("qty")
        metric_date = latest_entry.get("date", "").split(" ")[0]  # Extract only the date part

        # Store the first recorded metric date
        if first_metric_date is None:
            first_metric_date = metric_date

        # Convert value to float and round to 2 decimal places if valid
        if value is not None:
            try:
                value = round(float(value), 2)
            except ValueError:
                value = None  # Handle invalid values gracefully
        
        # Store values in the processed data dictionary
        if name in processed_data:
            processed_data[name] = f"{value} {unit}" if value is not None else None
        elif any(keyword in name for keyword in ["heart", "heart_rate"]):
            processed_data["hr"] = f"{value} {unit}" if value is not None else None

    # Set timestamp to the first metric's date or default to today's date
    processed_data["timestamp"] = first_metric_date if first_metric_date else datetime.now().strftime("%Y-%m-%d")
    
    return processed_data
