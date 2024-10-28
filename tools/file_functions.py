from pathlib import Path

def save_file(file_path: Path, data: str):
    """Save data to a file
    
    Args:
        file_path: Path to the file
        data: Data to write to the file

    Returns:
        Status message indicating the file save operation
    
    """
    with open(file_path, "w") as f:
        f.write(data)

    return f"Data saved to: {file_path}"
