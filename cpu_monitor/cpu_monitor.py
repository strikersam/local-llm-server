import psutil
import time
import pandas as pd
from datetime import datetime

def get_cpu_usage():
    """Get current CPU usage percentage."""
    return psutil.cpu_percent(interval=1)

def format_data(cpu_usage):
    """Format data with timestamp."""
    return {
        'timestamp': datetime.now().isoformat(),
        'cpu_usage': cpu_usage
    }

def save_to_csv(data, filename='cpu_usage.csv'):
    """Save CPU usage data to CSV file."""
    df = pd.DataFrame([data])
    
    # Check if file exists for appending
    try:
        existing_df = pd.read_csv(filename)
        df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        pass
    
    df.to_csv(filename, index=False)

def main():
    """Main monitoring loop."""
    print("Starting CPU monitor...")
    interval = 60  # seconds
    while True:
        try:
            cpu_usage = get_cpu_usage()
            data = format_data(cpu_usage)
            save_to_csv(data)
            print(f"Logged CPU usage: {cpu_usage}%")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopping CPU monitor...")
            break
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    main()