import os
import datetime
from pathlib import Path
import json

class SimpleLineSplitter:
    def __init__(self):
        pass
    
    def get_timestamp(self):
        """Generate timestamp in format YYYYMMDD_HHMMSS"""
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def create_batch_folder(self, base_path, original_filename):
        """Create batch folder with naming convention: batch-{original_filename}"""
        folder_name = f"batch-{original_filename}"
        folder_path = Path(base_path) / folder_name
        folder_path.mkdir(exist_ok=True)
        return folder_path
    
    def split_file_by_sections(self, file_path, output_base_path=None):
        """Split a file into chunks by section based on JSON data"""
        file_path = Path(file_path)
        
        if output_base_path is None:
            output_base_path = file_path.parent
        
        print(f"Processing: {file_path.name}")
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as input_file:
                lines = input_file.readlines()
            
            # Parse JSON content
            data = [json.loads(line) for line in lines if line.strip()]
            
            # Group by section
            sections = {}
            for item in data:
                section = item.get("section", "default")
                if section not in sections:
                    sections[section] = []
                sections[section].append(json.dumps(item))
            
            # Create batch files for each section
            original_filename = file_path.stem
            timestamp = self.get_timestamp()
            batch_folder = self.create_batch_folder(output_base_path, original_filename)
            
            for section, content in sections.items():
                batch_filename = f"{original_filename}-{section}-{timestamp}.json"
                batch_file_path = batch_folder / batch_filename
                with open(batch_file_path, 'w', encoding='utf-8') as batch_file:
                    batch_file.write("\n".join(content))
                print(f"    ✓ {batch_filename}")
                print(f"      Lines: {len(content):,}")
                print(f"      Size: {batch_file_path.stat().st_size:,} bytes")
            
            print(f"  ✓ Successfully created batches in {batch_folder}")
            
        except json.JSONDecodeError as e:
            print(f"  ✗ Error: Invalid JSON in {file_path.name}: {str(e)}")
        except Exception as e:
            print(f"  ✗ Error processing {file_path.name}: {str(e)}")
    
    def process_directory(self, directory_path):
        """Process all files in a directory"""
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            print(f"Error: Directory '{directory_path}' does not exist!")
            return
        
        # Look for any text files (JSON, TXT, etc.)
        file_extensions = ["*.json", "*.txt", "*.csv", "*.xml"]
        files = []
        for ext in file_extensions:
            files.extend(directory_path.glob(ext))
        
        if not files:
            print(f"No files found in '{directory_path}'")
            return
        
        print(f"Found {len(files)} file(s) to process:")
        print("=" * 80)
        
        for file in files:
            self.split_file_by_sections(file, directory_path)
            print("=" * 80)
        
        print("✓ All files processed successfully!")

def main():
    """Main function to run the simple line splitter"""
    
    DEFAULT_PATH = r"/home/seetha/Downloads/python/Figma_extractor/output"
    
    print("Simple Section-Based File Splitter")
    print("=" * 80)
    print("Features:")
    print("  ✓ Split JSON files by section")
    print("  ✓ Creates separate files for each section")
    print("  ✓ Works with JSON files")
    print("=" * 80)
    
    # Get user input
    user_path = input(f"Directory path (Enter for default: {DEFAULT_PATH}): ").strip()
    if not user_path:
        user_path = DEFAULT_PATH
    
    print(f"Configuration:")
    print(f"  Directory: {user_path}")
    print("=" * 80)
    
    # Process files
    splitter = SimpleLineSplitter()
    splitter.process_directory(user_path)

if __name__ == "__main__":
    main()