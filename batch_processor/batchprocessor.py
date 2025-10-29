import os
import datetime
from pathlib import Path

class SimpleLineSplitter:
    def __init__(self, max_lines_per_batch=5000):
        self.max_lines_per_batch = max_lines_per_batch
    
    def get_timestamp(self):
        """Generate timestamp in format YYYYMMDD_HHMMSS"""
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def get_file_line_count(self, file_path):
        """Get the actual line count of a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
    
    def create_batch_folder(self, base_path, original_filename):
        """Create batch folder with naming convention: batch-{original_filename}"""
        folder_name = f"batch-{original_filename}"
        folder_path = Path(base_path) / folder_name
        folder_path.mkdir(exist_ok=True)
        return folder_path
    
    def split_file_by_lines(self, file_path, output_base_path=None):
        """Split a file into chunks by line count"""
        file_path = Path(file_path)
        
        if output_base_path is None:
            output_base_path = file_path.parent
        
        print(f"Processing: {file_path.name}")
        
        try:
            # Get file metrics
            file_size = file_path.stat().st_size
            line_count = self.get_file_line_count(file_path)
            
            print(f"  File size: {file_size:,} bytes")
            print(f"  Line count: {line_count:,} lines")
            
            # Check if splitting is needed
            if line_count <= self.max_lines_per_batch:
                print(f"  File is within limit ({self.max_lines_per_batch:,} lines). Skipping...")
                return
            
            # Calculate number of batches needed
            num_batches = (line_count + self.max_lines_per_batch - 1) // self.max_lines_per_batch
            print(f"  Will create {num_batches} batches of ~{self.max_lines_per_batch:,} lines each")
            
            # Create output folder
            original_filename = file_path.stem
            batch_folder = self.create_batch_folder(output_base_path, original_filename)
            timestamp = self.get_timestamp()
            
            # Split the file
            with open(file_path, 'r', encoding='utf-8') as input_file:
                batch_num = 1
                lines_written = 0
                current_batch_lines = 0
                
                # Read all lines into memory for easier chunking
                all_lines = input_file.readlines()
                
                for i in range(0, len(all_lines), self.max_lines_per_batch):
                    # Get chunk of lines
                    chunk_lines = all_lines[i:i + self.max_lines_per_batch]
                    
                    # Create batch file
                    batch_filename = f"{original_filename}-batch{batch_num:03d}-{timestamp}.json"
                    batch_file_path = batch_folder / batch_filename
                    
                    # Write chunk to file
                    with open(batch_file_path, 'w', encoding='utf-8') as batch_file:
                        batch_file.writelines(chunk_lines)
                    
                    # Get actual metrics
                    actual_lines = len(chunk_lines)
                    actual_size = batch_file_path.stat().st_size
                    lines_written += actual_lines
                    
                    # Report batch details
                    print(f"    ✓ {batch_filename}")
                    print(f"      Lines: {actual_lines:,}")
                    print(f"      Size: {actual_size:,} bytes")
                    
                    batch_num += 1
            
            # Summary
            print(f"\n  📊 Summary:")
            print(f"    Input: {line_count:,} lines → Output: {lines_written:,} lines")
            print(f"    Batches created: {num_batches}")
            print(f"    Average lines per batch: {lines_written // num_batches:,}")
            print(f"  ✓ Successfully created batches in {batch_folder}")
            
        except Exception as e:
            print(f"  ✗ Error processing {file_path.name}: {str(e)}")
            import traceback
            print(f"  Debug: {traceback.format_exc()}")
    
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
            self.split_file_by_lines(file, directory_path)
            print("=" * 80)
        
        print("✓ All files processed successfully!")

def main():
    """Main function to run the simple line splitter"""
    
    DEFAULT_PATH = r"/home/seetha/Downloads/python/Figma_extractor/output"
    DEFAULT_MAX_LINES = 5000
    
    print("Simple Line-Based File Splitter")
    print("=" * 80)
    print("Features:")
    print("  ✓ Split any text file by line count")
    print("  ✓ No complex parsing - just raw line splitting")
    print("  ✓ Works with JSON, TXT, CSV, XML files")
    print("  ✓ Preserves original file content exactly")
    print("=" * 80)
    
    # Get user input
    user_path = input(f"Directory path (Enter for default: {DEFAULT_PATH}): ").strip()
    if not user_path:
        user_path = DEFAULT_PATH
    
    max_lines_input = input(f"Max lines per batch (Enter for default: {DEFAULT_MAX_LINES}): ").strip()
    if max_lines_input:
        try:
            max_lines = int(max_lines_input)
        except ValueError:
            print("Invalid number, using default.")
            max_lines = DEFAULT_MAX_LINES
    else:
        max_lines = DEFAULT_MAX_LINES
    
    print(f"Configuration:")
    print(f"  Directory: {user_path}")
    print(f"  Max lines per batch: {max_lines:,}")
    print("=" * 80)
    
    # Process files
    splitter = SimpleLineSplitter(max_lines_per_batch=max_lines)
    splitter.process_directory(user_path)

if __name__ == "__main__":
    main()