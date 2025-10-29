# import boto3
# import os
# import mimetypes
# import json
# import logging
# from pathlib import Path
# from botocore.exceptions import ClientError, NoCredentialsError
# from typing import List, Dict, Optional
# from datetime import datetime

# logger = logging.getLogger(__name__)

# class DigitalOceanUploader:
#     """Enhanced DigitalOcean Spaces uploader with better error handling"""
    
#     def __init__(self, access_key: str, secret_key: str, region: str, space_name: str):
#         self.space_name = space_name
#         self.region = region
#         self.access_key = access_key
#         self.secret_key = secret_key
        
#         # Create boto3 client for DigitalOcean Spaces
#         self.client = boto3.client(
#             's3',
#             region_name=region,
#             endpoint_url=f'https://{region}.digitaloceanspaces.com',
#             aws_access_key_id=access_key,
#             aws_secret_access_key=secret_key
#         )
        
#         logger.info(f"Initialized DigitalOcean Spaces client for {space_name} in {region}")
    
#     def test_connection(self) -> bool:
#         """Test connection to DigitalOcean Spaces"""
#         try:
#             self.client.head_bucket(Bucket=self.space_name)
#             logger.info("Successfully connected to DigitalOcean Spaces")
#             return True
#         except ClientError as e:
#             logger.error(f"Failed to connect to DigitalOcean Spaces: {e}")
#             return False
    
#     def upload_file(self, local_file_path: str, remote_path: str, public_read: bool = True) -> Dict:
#         """Upload a single file to DigitalOcean Spaces"""
#         try:
#             file_path = Path(local_file_path)
#             if not file_path.exists():
#                 return {
#                     'success': False,
#                     'error': f'File not found: {local_file_path}',
#                     'url': None
#                 }
            
#             # Determine content type
#             content_type, _ = mimetypes.guess_type(local_file_path)
#             if content_type is None:
#                 content_type = 'application/octet-stream'
            
#             # Set up extra arguments
#             extra_args = {'ContentType': content_type}
#             if public_read:
#                 extra_args['ACL'] = 'public-read'
            
#             # Upload the file
#             logger.info(f"Uploading {file_path.name} to {remote_path}")
#             self.client.upload_file(
#                 local_file_path,
#                 self.space_name,
#                 remote_path,
#                 ExtraArgs=extra_args
#             )
            
#             # Generate URLs
#             url = self.get_file_url(remote_path)
#             cdn_url = self.get_cdn_url(remote_path)
            
#             logger.info(f"Successfully uploaded: {url}")
            
#             return {
#                 'success': True,
#                 'local_path': local_file_path,
#                 'remote_path': remote_path,
#                 'url': url,
#                 'cdn_url': cdn_url,
#                 'content_type': content_type,
#                 'file_size': file_path.stat().st_size
#             }
            
#         except ClientError as e:
#             error_msg = f'AWS Client Error: {e}'
#             logger.error(error_msg)
#             return {
#                 'success': False,
#                 'error': error_msg,
#                 'url': None
#             }
#         except Exception as e:
#             error_msg = f'Upload failed: {e}'
#             logger.error(error_msg)
#             return {
#                 'success': False,
#                 'error': error_msg,
#                 'url': None
#             }
    
#     def upload_directory(self, local_dir_path: str, remote_folder: str = "", 
#                         file_extensions: List[str] = None, 
#                         public_read: bool = True) -> Dict:
#         """Upload all files from a local directory to DigitalOcean Spaces"""
#         local_path = Path(local_dir_path)
#         if not local_path.exists() or not local_path.is_dir():
#             return {
#                 'success': False,
#                 'error': f'Directory not found: {local_dir_path}',
#                 'uploaded_files': [],
#                 'failed_uploads': [],
#                 'total_uploaded': 0,
#                 'total_failed': 0
#             }
        
#         # Ensure remote_folder ends with / if not empty
#         if remote_folder and not remote_folder.endswith('/'):
#             remote_folder += '/'
        
#         uploaded_files = []
#         failed_uploads = []
        
#         # Get all files in directory
#         for file_path in local_path.rglob('*'):
#             if file_path.is_file():
#                 # Check file extension if specified
#                 if file_extensions:
#                     if file_path.suffix.lower() not in [ext.lower() for ext in file_extensions]:
#                         continue
                
#                 # Calculate relative path from base directory
#                 relative_path = file_path.relative_to(local_path)
#                 remote_path = remote_folder + str(relative_path).replace('\\', '/')
                
#                 # Upload file
#                 result = self.upload_file(str(file_path), remote_path, public_read)
                
#                 if result['success']:
#                     uploaded_files.append(result)
#                     logger.info(f"✅ Uploaded: {file_path.name}")
#                 else:
#                     failed_uploads.append({
#                         'file': str(file_path),
#                         'error': result['error']
#                     })
#                     logger.error(f"❌ Failed: {file_path.name} - {result['error']}")
        
#         return {
#             'success': len(failed_uploads) == 0,
#             'uploaded_files': uploaded_files,
#             'failed_uploads': failed_uploads,
#             'total_uploaded': len(uploaded_files),
#             'total_failed': len(failed_uploads)
#         }
    
#     def get_file_url(self, remote_path: str) -> str:
#         """Get the public URL for a file in DigitalOcean Spaces"""
#         return f'https://{self.space_name}.{self.region}.digitaloceanspaces.com/{remote_path}'
    
#     def get_cdn_url(self, remote_path: str) -> str:
#         """Get the CDN URL for a file in DigitalOcean Spaces"""
#         return f'https://{self.space_name}.{self.region}.cdn.digitaloceanspaces.com/{remote_path}'
    
#     def list_files(self, folder_path: str = "", max_files: int = 1000, files_only: bool = True) -> List[Dict]:
#         """List files in a specific folder in the space"""
#         try:
#             if folder_path and not folder_path.endswith('/'):
#                 folder_path += '/'
            
#             response = self.client.list_objects_v2(
#                 Bucket=self.space_name,
#                 Prefix=folder_path,
#                 MaxKeys=max_files
#             )
            
#             files = []
#             if 'Contents' in response:
#                 for obj in response['Contents']:
#                     if files_only and obj['Key'].endswith('/'):
#                         continue
                    
#                     if obj['Key'] == folder_path:
#                         continue
                    
#                     file_info = {
#                         'key': obj['Key'],
#                         'filename': obj['Key'].split('/')[-1],
#                         'full_path': obj['Key'],
#                         'relative_path': obj['Key'].replace(folder_path, '', 1),
#                         'size': obj['Size'],
#                         'size_mb': round(obj['Size'] / (1024 * 1024), 2),
#                         'last_modified': obj['LastModified'].isoformat(),
#                         'etag': obj['ETag'].strip('"'),
#                         'storage_class': obj.get('StorageClass', 'STANDARD'),
#                         'folder': folder_path.rstrip('/'),
#                         'url': self.get_file_url(obj['Key']),
#                         'cdn_url': self.get_cdn_url(obj['Key'])
#                     }
#                     files.append(file_info)
            
#             return files
            
#         except ClientError as e:
#             logger.error(f"Error listing files: {e}")
#             return []
#         except Exception as e:
#             logger.error(f"Unexpected error listing files: {e}")
#             return []
    
#     def export_urls_to_json(self, folder_path: str = "", output_file: str = "urls.json") -> bool:
#         """Export all file URLs from a folder to a JSON file"""
#         try:
#             files = self.list_files(folder_path)
            
#             urls_data = {
#                 'space_name': self.space_name,
#                 'region': self.region,
#                 'folder': folder_path,
#                 'generated_at': datetime.now().isoformat(),
#                 'total_files': len(files),
#                 'files': []
#             }
            
#             for file_info in files:
#                 urls_data['files'].append({
#                     'filename': file_info['filename'],
#                     'remote_path': file_info['full_path'],
#                     'size_mb': file_info['size_mb'],
#                     'url': file_info['url'],
#                     'cdn_url': file_info['cdn_url'],
#                     'last_modified': file_info['last_modified']
#                 })
            
#             with open(output_file, 'w', encoding='utf-8') as f:
#                 json.dump(urls_data, f, indent=2, ensure_ascii=False)
            
#             logger.info(f"URLs exported to {output_file}")
#             return True
            
#         except Exception as e:
#             logger.error(f"Error exporting URLs: {e}")
#             return False


import boto3
import os
import mimetypes
import json
import logging
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DigitalOceanUploader:
    """Enhanced DigitalOcean Spaces uploader with better error handling and SVG URL tracking"""
    
    def __init__(self, access_key: str, secret_key: str, region: str, space_name: str):
        self.space_name = space_name
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        
        # Track all uploaded files for URL mapping
        self.uploaded_files = []
        
        # Create boto3 client for DigitalOcean Spaces
        self.client = boto3.client(
            's3',
            region_name=region,
            endpoint_url=f'https://{region}.digitaloceanspaces.com',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        logger.info(f"Initialized DigitalOcean Spaces client for {space_name} in {region}")
    
    def test_connection(self) -> bool:
        """Test connection to DigitalOcean Spaces"""
        try:
            self.client.head_bucket(Bucket=self.space_name)
            logger.info("Successfully connected to DigitalOcean Spaces")
            return True
        except ClientError as e:
            logger.error(f"Failed to connect to DigitalOcean Spaces: {e}")
            return False
    
    def upload_file(self, local_file_path: str, remote_path: str, public_read: bool = True) -> Dict:
        """Upload a single file to DigitalOcean Spaces"""
        try:
            file_path = Path(local_file_path)
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'File not found: {local_file_path}',
                    'url': None
                }
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(local_file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            # Set up extra arguments
            extra_args = {'ContentType': content_type}
            if public_read:
                extra_args['ACL'] = 'public-read'
            
            # Upload the file
            logger.info(f"Uploading {file_path.name} to {remote_path}")
            self.client.upload_file(
                local_file_path,
                self.space_name,
                remote_path,
                ExtraArgs=extra_args
            )
            
            # Generate URLs
            url = self.get_file_url(remote_path)
            cdn_url = self.get_cdn_url(remote_path)
            
            # Store upload info for URL mapping
            upload_info = {
                'success': True,
                'local_path': local_file_path,
                'remote_path': remote_path,
                'url': url,
                'cdn_url': cdn_url,
                'content_type': content_type,
                'file_size': file_path.stat().st_size,
                'filename': file_path.name
            }
            
            # Add to uploaded files list for URL mapping
            self.uploaded_files.append(upload_info)
            
            logger.info(f"Successfully uploaded: {url}")
            
            return upload_info
            
        except ClientError as e:
            error_msg = f'AWS Client Error: {e}'
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'url': None
            }
        except Exception as e:
            error_msg = f'Upload failed: {e}'
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'url': None
            }
    
    def upload_directory(self, local_dir_path: str, remote_folder: str = "", 
                        file_extensions: List[str] = None, 
                        public_read: bool = True) -> Dict:
        """Upload all files from a local directory to DigitalOcean Spaces"""
        local_path = Path(local_dir_path)
        if not local_path.exists() or not local_path.is_dir():
            return {
                'success': False,
                'error': f'Directory not found: {local_dir_path}',
                'uploaded_files': [],
                'failed_uploads': [],
                'total_uploaded': 0,
                'total_failed': 0
            }
        
        # Ensure remote_folder ends with / if not empty
        if remote_folder and not remote_folder.endswith('/'):
            remote_folder += '/'
        
        uploaded_files = []
        failed_uploads = []
        
        # Get all files in directory
        for file_path in local_path.rglob('*'):
            if file_path.is_file():
                # Check file extension if specified
                if file_extensions:
                    if file_path.suffix.lower() not in [ext.lower() for ext in file_extensions]:
                        continue
                
                # Calculate relative path from base directory
                relative_path = file_path.relative_to(local_path)
                remote_path = remote_folder + str(relative_path).replace('\\', '/')
                
                # Upload file
                result = self.upload_file(str(file_path), remote_path, public_read)
                
                if result['success']:
                    uploaded_files.append(result)
                    logger.info(f"✅ Uploaded: {file_path.name}")
                else:
                    failed_uploads.append({
                        'file': str(file_path),
                        'error': result['error']
                    })
                    logger.error(f"❌ Failed: {file_path.name} - {result['error']}")
        
        return {
            'success': len(failed_uploads) == 0,
            'uploaded_files': uploaded_files,
            'failed_uploads': failed_uploads,
            'total_uploaded': len(uploaded_files),
            'total_failed': len(failed_uploads)
        }
    
    def get_file_url(self, remote_path: str) -> str:
        """Get the public URL for a file in DigitalOcean Spaces"""
        return f'https://{self.space_name}.{self.region}.digitaloceanspaces.com/{remote_path}'
    
    def get_cdn_url(self, remote_path: str) -> str:
        """Get the CDN URL for a file in DigitalOcean Spaces"""
        return f'https://{self.space_name}.{self.region}.cdn.digitaloceanspaces.com/{remote_path}'
    
    def list_files(self, folder_path: str = "", max_files: int = 1000, files_only: bool = True) -> List[Dict]:
        """List files in a specific folder in the space"""
        try:
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'
            
            response = self.client.list_objects_v2(
                Bucket=self.space_name,
                Prefix=folder_path,
                MaxKeys=max_files
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if files_only and obj['Key'].endswith('/'):
                        continue
                    
                    if obj['Key'] == folder_path:
                        continue
                    
                    file_info = {
                        'key': obj['Key'],
                        'filename': obj['Key'].split('/')[-1],
                        'full_path': obj['Key'],
                        'relative_path': obj['Key'].replace(folder_path, '', 1),
                        'size': obj['Size'],
                        'size_mb': round(obj['Size'] / (1024 * 1024), 2),
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"'),
                        'storage_class': obj.get('StorageClass', 'STANDARD'),
                        'folder': folder_path.rstrip('/'),
                        'url': self.get_file_url(obj['Key']),
                        'cdn_url': self.get_cdn_url(obj['Key'])
                    }
                    files.append(file_info)
            
            return files
            
        except ClientError as e:
            logger.error(f"Error listing files: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing files: {e}")
            return []
    
    def export_urls_to_json(self, folder_path: str = "", output_file: str = "urls.json") -> bool:
        """
        FIXED: Export all file URLs from a folder to a JSON file
        Now properly includes uploaded SVG files from the current session
        """
        try:
            # Get files from DigitalOcean (existing files)
            remote_files = self.list_files(folder_path)
            
            # Combine with files uploaded in this session
            all_files = []
            
            # Add files from current upload session first (these are guaranteed to exist)
            for upload_info in self.uploaded_files:
                # Extract filename and path info
                filename = upload_info['filename']
                remote_path = upload_info['remote_path']
                
                # Create file info matching the expected format
                file_info = {
                    'filename': filename,
                    'remote_path': remote_path,
                    'size_mb': round(upload_info['file_size'] / (1024 * 1024), 2),
                    'url': upload_info['url'],
                    'cdn_url': upload_info['cdn_url'],
                    'last_modified': datetime.now().isoformat(),
                    'source': 'current_session'
                }
                
                all_files.append(file_info)
                logger.debug(f"Added from current session: {filename}")
            
            # Add files from remote listing (if not already included)
            current_session_paths = {info['remote_path'] for info in self.uploaded_files}
            
            for remote_file in remote_files:
                if remote_file['full_path'] not in current_session_paths:
                    file_info = {
                        'filename': remote_file['filename'],
                        'remote_path': remote_file['full_path'],
                        'size_mb': remote_file['size_mb'],
                        'url': remote_file['url'],
                        'cdn_url': remote_file['cdn_url'],
                        'last_modified': remote_file['last_modified'],
                        'source': 'existing'
                    }
                    all_files.append(file_info)
            
            # Create the URLs data structure
            urls_data = {
                'space_name': self.space_name,
                'region': self.region,
                'folder': folder_path,
                'generated_at': datetime.now().isoformat(),
                'total_files': len(all_files),
                'current_session_uploads': len(self.uploaded_files),
                'existing_files': len(remote_files),
                'files': all_files
            }
            
            # Save to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(urls_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"URLs exported to {output_file}")
            logger.info(f"  - Current session: {len(self.uploaded_files)} files")
            logger.info(f"  - Existing remote: {len(remote_files)} files")
            logger.info(f"  - Total: {len(all_files)} files")
            
            # Debug: Show SVG files specifically
            svg_files = [f for f in all_files if f['filename'].lower().endswith('.svg')]
            logger.info(f"  - SVG files included: {len(svg_files)}")
            
            if svg_files:
                logger.info("  SVG files in URL mapping:")
                for i, svg_file in enumerate(svg_files[:5], 1):  # Show first 5
                    file_key = Path(svg_file['filename']).stem
                    logger.info(f"    {i}. Key: '{file_key}' -> {svg_file['filename']}")
                if len(svg_files) > 5:
                    logger.info(f"    ... and {len(svg_files) - 5} more SVG files")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting URLs: {e}")
            return False
    
    def get_upload_summary(self) -> Dict:
        """Get summary of files uploaded in this session"""
        svg_files = [f for f in self.uploaded_files if f['filename'].lower().endswith('.svg')]
        image_files = [f for f in self.uploaded_files if f['filename'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
        
        return {
            'total_uploaded': len(self.uploaded_files),
            'svg_files': len(svg_files),
            'image_files': len(image_files),
            'other_files': len(self.uploaded_files) - len(svg_files) - len(image_files),
            'svg_filenames': [f['filename'] for f in svg_files],
            'image_filenames': [f['filename'] for f in image_files]
        }
    
    def clear_upload_history(self):
        """Clear the upload history (useful for new sessions)"""
        self.uploaded_files.clear()
        logger.info("Upload history cleared")