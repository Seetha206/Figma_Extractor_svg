# import json
# import logging
# from pathlib import Path
# from typing import Dict, Any, Union

# logger = logging.getLogger(__name__)

# class URLReplacer:
#     """Replace image references in Figma JSON with DigitalOcean URLs (supports both bitmap and SVG)"""
    
#     def __init__(self):
#         self.url_mapping = {}
#         self.replacement_count = 0
#         self.svg_replacement_count = 0
    
#     def load_url_mapping(self, urls_json_path: str) -> bool:
#         """
#         Load URL mapping from the DigitalOcean URLs JSON file
        
#         Args:
#             urls_json_path: Path to the JSON file containing uploaded URLs
            
#         Returns:
#             bool: True if successful, False otherwise
#         """
#         try:
#             with open(urls_json_path, 'r', encoding='utf-8') as f:
#                 urls_data = json.load(f)
            
#             # Extract URL mapping from the structure
#             if 'files' in urls_data:
#                 for file_info in urls_data['files']:
#                     filename = file_info['filename']
#                     # Extract reference from filename (remove extension)
#                     file_ref = Path(filename).stem
                    
#                     # Store both regular URL and CDN URL
#                     self.url_mapping[file_ref] = {
#                         'url': file_info['url'],
#                         'cdn_url': file_info['cdn_url'],
#                         'filename': filename,
#                         'size_mb': file_info['size_mb'],
#                         'file_type': 'svg' if filename.lower().endswith('.svg') else 'bitmap'
#                     }
            
#             logger.info(f"Loaded {len(self.url_mapping)} URL mappings")
            
#             # Log breakdown by type
#             svg_count = sum(1 for mapping in self.url_mapping.values() if mapping['file_type'] == 'svg')
#             bitmap_count = len(self.url_mapping) - svg_count
#             logger.info(f"  - {bitmap_count} bitmap image URLs")
#             logger.info(f"  - {svg_count} SVG icon URLs")
            
#             return True
            
#         except Exception as e:
#             logger.error(f"Error loading URL mapping from {urls_json_path}: {e}")
#             return False
    
#     def replace_image_references(self, figma_data: Dict[str, Any], use_cdn: bool = True) -> Dict[str, Any]:
#         """
#         Replace all image references in Figma JSON with DigitalOcean URLs
        
#         Args:
#             figma_data: The original Figma JSON data
#             use_cdn: Whether to use CDN URLs (default) or regular URLs
            
#         Returns:
#             Dict: Updated Figma JSON with replaced URLs
#         """
#         self.replacement_count = 0
#         self.svg_replacement_count = 0
        
#         # Create a deep copy to avoid modifying original data
#         updated_data = json.loads(json.dumps(figma_data))
        
#         # Recursively replace image references
#         self._replace_recursive(updated_data, use_cdn)
        
#         # Add replacement metadata
#         if '_metadata' not in updated_data:
#             updated_data['_metadata'] = {}
        
#         updated_data['_metadata']['url_replacement'] = {
#             'total_bitmap_replacements': self.replacement_count,
#             'total_svg_replacements': self.svg_replacement_count,
#             'total_replacements': self.replacement_count + self.svg_replacement_count,
#             'use_cdn_urls': use_cdn,
#             'available_mappings': len(self.url_mapping),
#             'replacement_timestamp': self._get_timestamp()
#         }
        
#         # Update existing image downloads section
#         if '_imageDownloads' in updated_data:
#             self._update_image_downloads_section(updated_data['_imageDownloads'], use_cdn)
        
#         # Update SVG downloads section
#         if '_svgDownloads' in updated_data:
#             self._update_svg_downloads_section(updated_data['_svgDownloads'], use_cdn)
        
#         logger.info(f"Completed URL replacement:")
#         logger.info(f"  - {self.replacement_count} bitmap image references replaced")
#         logger.info(f"  - {self.svg_replacement_count} SVG icon references replaced")
#         logger.info(f"  - {self.replacement_count + self.svg_replacement_count} total replacements")
        
#         return updated_data
    
#     def _replace_recursive(self, obj: Union[Dict, list, Any], use_cdn: bool):
#         """Recursively traverse and replace image references"""
#         if isinstance(obj, dict):
#             # Check for image fills
#             if 'fills' in obj and isinstance(obj['fills'], list):
#                 for fill in obj['fills']:
#                     if isinstance(fill, dict) and fill.get('type') == 'IMAGE':
#                         self._replace_image_ref_in_fill(fill, use_cdn)
            
#             # Check for background fills
#             if 'backgrounds' in obj and isinstance(obj['backgrounds'], list):
#                 for bg in obj['backgrounds']:
#                     if isinstance(bg, dict) and bg.get('type') == 'IMAGE':
#                         self._replace_image_ref_in_fill(bg, use_cdn)
            
#             # Check for background property (single fill)
#             if 'background' in obj and isinstance(obj['background'], list):
#                 for bg in obj['background']:
#                     if isinstance(bg, dict) and bg.get('type') == 'IMAGE':
#                         self._replace_image_ref_in_fill(bg, use_cdn)
            
#             # Recursively process all values
#             for value in obj.values():
#                 self._replace_recursive(value, use_cdn)
        
#         elif isinstance(obj, list):
#             for item in obj:
#                 self._replace_recursive(item, use_cdn)
    
#     def _replace_image_ref_in_fill(self, fill: Dict[str, Any], use_cdn: bool):
#         """Replace imageRef in a fill/background object"""
#         if 'imageRef' in fill:
#             image_ref = fill['imageRef']
#             if image_ref in self.url_mapping:
#                 url_key = 'cdn_url' if use_cdn else 'url'
#                 new_url = self.url_mapping[image_ref][url_key]
#                 file_type = self.url_mapping[image_ref]['file_type']
                
#                 # Replace imageRef with the actual URL
#                 fill['imageUrl'] = new_url  # Add new field
#                 fill['originalImageRef'] = image_ref  # Keep original reference
#                 fill['_imageReplaced'] = True  # Mark as replaced
#                 fill['_imageType'] = file_type  # Mark the type
                
#                 # Update scaleMode to FILL if it was using imageRef
#                 if 'scaleMode' not in fill:
#                     fill['scaleMode'] = 'FILL'
                
#                 if file_type == 'svg':
#                     self.svg_replacement_count += 1
#                 else:
#                     self.replacement_count += 1
                    
#                 logger.debug(f"Replaced {file_type} {image_ref} with {new_url}")
#             else:
#                 logger.warning(f"No URL mapping found for image reference: {image_ref}")
    
#     def _update_image_downloads_section(self, image_downloads: Dict[str, Any], use_cdn: bool):
#         """Update the _imageDownloads section with URLs"""
#         url_key = 'cdn_url' if use_cdn else 'url'
        
#         for image_ref, img_data in image_downloads.items():
#             if isinstance(img_data, dict) and image_ref in self.url_mapping:
#                 img_data['uploaded_url'] = self.url_mapping[image_ref][url_key]
#                 img_data['uploaded_cdn_url'] = self.url_mapping[image_ref]['cdn_url']
#                 img_data['uploaded_regular_url'] = self.url_mapping[image_ref]['url']
#                 img_data['uploaded_size_mb'] = self.url_mapping[image_ref]['size_mb']
#                 img_data['_url_replaced'] = True
    
#     def _update_svg_downloads_section(self, svg_downloads: Dict[str, Any], use_cdn: bool):
#         """Update the _svgDownloads section with URLs"""
#         url_key = 'cdn_url' if use_cdn else 'url'
        
#         for node_id, svg_data in svg_downloads.items():
#             if isinstance(svg_data, dict):
#                 # Create mapping key for SVG lookup (node ID becomes filename)
#                 safe_node_id = node_id.replace(':', '_')
                
#                 # Check if we have URL mapping for this SVG
#                 if safe_node_id in self.url_mapping:
#                     svg_data['uploaded_url'] = self.url_mapping[safe_node_id][url_key]
#                     svg_data['uploaded_cdn_url'] = self.url_mapping[safe_node_id]['cdn_url']
#                     svg_data['uploaded_regular_url'] = self.url_mapping[safe_node_id]['url']
#                     svg_data['uploaded_size_mb'] = self.url_mapping[safe_node_id]['size_mb']
#                     svg_data['_url_replaced'] = True
#                     logger.debug(f"Updated SVG download {node_id} with CDN URL")
#                 else:
#                     logger.warning(f"No URL mapping found for SVG node ID: {node_id} (looking for: {safe_node_id})")
    
#     def _get_timestamp(self) -> str:
#         """Get current timestamp"""
#         from datetime import datetime
#         return datetime.now().isoformat()
    
#     def create_url_replaced_json(self, original_json_path: str, urls_json_path: str, 
#                                 output_path: str = None, use_cdn: bool = True) -> str:
#         """
#         Complete workflow to create a new JSON with replaced URLs (supports both bitmap and SVG)
        
#         Args:
#             original_json_path: Path to original Figma JSON
#             urls_json_path: Path to URLs JSON from DigitalOcean
#             output_path: Output path for new JSON (optional)
#             use_cdn: Whether to use CDN URLs
            
#         Returns:
#             str: Path to the created file
#         """
#         try:
#             # Load URL mapping
#             if not self.load_url_mapping(urls_json_path):
#                 raise Exception("Failed to load URL mapping")
            
#             # Load original Figma JSON
#             with open(original_json_path, 'r', encoding='utf-8') as f:
#                 figma_data = json.load(f)
            
#             # Replace image references (both bitmap and SVG)
#             updated_data = self.replace_image_references(figma_data, use_cdn)
            
#             # Determine output path
#             if output_path is None:
#                 original_path = Path(original_json_path)
#                 suffix = "_with_urls"
#                 output_path = original_path.parent / f"{original_path.stem}{suffix}.json"
            
#             # Save updated JSON
#             with open(output_path, 'w', encoding='utf-8') as f:
#                 json.dump(updated_data, f, indent=2, ensure_ascii=False)
            
#             logger.info(f"Created URL-replaced JSON: {output_path}")
#             logger.info(f"Replaced {self.replacement_count} bitmap image references")
#             logger.info(f"Replaced {self.svg_replacement_count} SVG icon references")
#             logger.info(f"Total replacements: {self.replacement_count + self.svg_replacement_count}")
            
#             return str(output_path)
            
#         except Exception as e:
#             logger.error(f"Error creating URL-replaced JSON: {e}")
#             raise
    
#     def generate_replacement_report(self) -> Dict[str, Any]:
#         """Generate a comprehensive report of the replacement process"""
        
#         # Separate mappings by type
#         bitmap_mappings = {k: v for k, v in self.url_mapping.items() if v['file_type'] == 'bitmap'}
#         svg_mappings = {k: v for k, v in self.url_mapping.items() if v['file_type'] == 'svg'}
        
#         return {
#             'summary': {
#                 'total_available_mappings': len(self.url_mapping),
#                 'bitmap_mappings': len(bitmap_mappings),
#                 'svg_mappings': len(svg_mappings),
#                 'total_replacements_made': self.replacement_count + self.svg_replacement_count,
#                 'bitmap_replacements_made': self.replacement_count,
#                 'svg_replacements_made': self.svg_replacement_count
#             },
#             'bitmap_images': {
#                 'available_refs': list(bitmap_mappings.keys()),
#                 'mapping_details': {
#                     ref: {
#                         'filename': data['filename'],
#                         'size_mb': data['size_mb'],
#                         'has_cdn_url': 'cdn_url' in data,
#                         'has_regular_url': 'url' in data
#                     }
#                     for ref, data in bitmap_mappings.items()
#                 }
#             },
#             'svg_icons': {
#                 'available_refs': list(svg_mappings.keys()),
#                 'mapping_details': {
#                     ref: {
#                         'filename': data['filename'],
#                         'size_mb': data['size_mb'],
#                         'has_cdn_url': 'cdn_url' in data,
#                         'has_regular_url': 'url' in data
#                     }
#                     for ref, data in svg_mappings.items()
#                 }
#             },
#             'replacement_timestamp': self._get_timestamp()
#         }
    
#     def create_comprehensive_mapping(self, figma_json_path: str, output_dir: Path) -> str:
#         """
#         Create a comprehensive mapping file showing all asset relationships
        
#         Args:
#             figma_json_path: Path to the Figma JSON file
#             output_dir: Directory to save mapping file
            
#         Returns:
#             str: Path to the created mapping file
#         """
#         try:
#             # Load Figma JSON
#             with open(figma_json_path, 'r', encoding='utf-8') as f:
#                 figma_data = json.load(f)
            
#             mapping_data = {
#                 'metadata': {
#                     'generated_at': self._get_timestamp(),
#                     'figma_file_key': figma_data.get('_metadata', {}).get('figma_file_key', 'unknown'),
#                     'document_name': figma_data.get('_metadata', {}).get('document_name', 'unknown')
#                 },
#                 'bitmap_images': {},
#                 'svg_icons': {},
#                 'summary': {
#                     'total_bitmap_images': 0,
#                     'total_svg_icons': 0,
#                     'bitmap_with_urls': 0,
#                     'svg_with_urls': 0
#                 }
#             }
            
#             # Process bitmap images
#             if '_imageDownloads' in figma_data:
#                 for image_ref, img_data in figma_data['_imageDownloads'].items():
#                     mapping_data['bitmap_images'][image_ref] = {
#                         'filename': img_data.get('filename', ''),
#                         'local_path': img_data.get('local_path', ''),
#                         'cdn_url': img_data.get('uploaded_cdn_url', ''),
#                         'regular_url': img_data.get('uploaded_regular_url', ''),
#                         'file_size_mb': round(img_data.get('file_size', 0) / (1024 * 1024), 2),
#                         'has_uploaded_url': img_data.get('_url_replaced', False)
#                     }
#                     mapping_data['summary']['total_bitmap_images'] += 1
#                     if img_data.get('_url_replaced', False):
#                         mapping_data['summary']['bitmap_with_urls'] += 1
            
#             # Process SVG icons
#             if '_svgDownloads' in figma_data:
#                 for node_id, svg_data in figma_data['_svgDownloads'].items():
#                     safe_node_id = node_id.replace(':', '_')
#                     mapping_data['svg_icons'][safe_node_id] = {
#                         'original_node_id': node_id,
#                         'component_name': svg_data.get('component_name', ''),
#                         'filename': svg_data.get('filename', ''),
#                         'local_path': svg_data.get('local_path', ''),
#                         'cdn_url': svg_data.get('uploaded_cdn_url', ''),
#                         'regular_url': svg_data.get('uploaded_regular_url', ''),
#                         'file_size_mb': round(svg_data.get('file_size', 0) / (1024 * 1024), 2),
#                         'component_type': svg_data.get('type', ''),
#                         'component_path': svg_data.get('path', ''),
#                         'has_uploaded_url': svg_data.get('_url_replaced', False)
#                     }
#                     mapping_data['summary']['total_svg_icons'] += 1
#                     if svg_data.get('_url_replaced', False):
#                         mapping_data['summary']['svg_with_urls'] += 1
            
#             # Save mapping file
#             mapping_file = output_dir / "comprehensive_asset_mapping.json"
#             with open(mapping_file, 'w', encoding='utf-8') as f:
#                 json.dump(mapping_data, f, indent=2, ensure_ascii=False)
            
#             logger.info(f"Comprehensive asset mapping saved to: {mapping_file}")
#             logger.info(f"  - {mapping_data['summary']['total_bitmap_images']} bitmap images ({mapping_data['summary']['bitmap_with_urls']} with URLs)")
#             logger.info(f"  - {mapping_data['summary']['total_svg_icons']} SVG icons ({mapping_data['summary']['svg_with_urls']} with URLs)")
            
#             return str(mapping_file)
            
#         except Exception as e:
#             logger.error(f"Error creating comprehensive mapping: {e}")
#             raise


# def replace_urls_in_figma_json(original_json_path: str, urls_json_path: str, 
#                               output_path: str = None, use_cdn: bool = True) -> str:
#     """
#     Convenience function to replace URLs in Figma JSON (supports both bitmap and SVG)
    
#     Args:
#         original_json_path: Path to original Figma JSON file
#         urls_json_path: Path to DigitalOcean URLs JSON file
#         output_path: Output path for new JSON (optional)
#         use_cdn: Whether to use CDN URLs (default: True)
        
#     Returns:
#         str: Path to the created file with replaced URLs
#     """
#     replacer = URLReplacer()
#     return replacer.create_url_replaced_json(
#         original_json_path, 
#         urls_json_path, 
#         output_path, 
#         use_cdn
#     )

import json
import logging
from pathlib import Path
from typing import Dict, Any, Union

logger = logging.getLogger(__name__)

class URLReplacer:
    """Replace image references in Figma JSON with DigitalOcean URLs (supports both bitmap and SVG)"""
    
    def __init__(self):
        self.url_mapping = {}
        self.replacement_count = 0
        self.svg_replacement_count = 0
    
    def load_url_mapping(self, urls_json_path: str) -> bool:
        """
        Load URL mapping from the DigitalOcean URLs JSON file
        
        Args:
            urls_json_path: Path to the JSON file containing uploaded URLs
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(urls_json_path, 'r', encoding='utf-8') as f:
                urls_data = json.load(f)
            
            # Extract URL mapping from the structure
            if 'files' in urls_data:
                for file_info in urls_data['files']:
                    filename = file_info['filename']
                    # Extract reference from filename (remove extension)
                    file_ref = Path(filename).stem
                    
                    # Store both regular URL and CDN URL
                    self.url_mapping[file_ref] = {
                        'url': file_info['url'],
                        'cdn_url': file_info['cdn_url'],
                        'filename': filename,
                        'size_mb': file_info['size_mb'],
                        'file_type': 'svg' if filename.lower().endswith('.svg') else 'bitmap'
                    }
            
            logger.info(f"Loaded {len(self.url_mapping)} URL mappings")
            
            # Log breakdown by type
            svg_count = sum(1 for mapping in self.url_mapping.values() if mapping['file_type'] == 'svg')
            bitmap_count = len(self.url_mapping) - svg_count
            logger.info(f"  - {bitmap_count} bitmap image URLs")
            logger.info(f"  - {svg_count} SVG icon URLs")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading URL mapping from {urls_json_path}: {e}")
            return False
    
    def replace_image_references(self, figma_data: Dict[str, Any], use_cdn: bool = True) -> Dict[str, Any]:
        """
        Replace all image references in Figma JSON with DigitalOcean URLs
        
        Args:
            figma_data: The original Figma JSON data
            use_cdn: Whether to use CDN URLs (default) or regular URLs
            
        Returns:
            Dict: Updated Figma JSON with replaced URLs
        """
        self.replacement_count = 0
        self.svg_replacement_count = 0
        
        # Create a deep copy to avoid modifying original data
        updated_data = json.loads(json.dumps(figma_data))
        
        # Recursively replace image references
        self._replace_recursive(updated_data, use_cdn)
        
        # Add replacement metadata
        if '_metadata' not in updated_data:
            updated_data['_metadata'] = {}
        
        updated_data['_metadata']['url_replacement'] = {
            'total_bitmap_replacements': self.replacement_count,
            'total_svg_replacements': self.svg_replacement_count,
            'total_replacements': self.replacement_count + self.svg_replacement_count,
            'use_cdn_urls': use_cdn,
            'available_mappings': len(self.url_mapping),
            'replacement_timestamp': self._get_timestamp()
        }
        
        # Update existing image downloads section
        if '_imageDownloads' in updated_data:
            self._update_image_downloads_section(updated_data['_imageDownloads'], use_cdn)
        
        # Update SVG downloads section - FIXED VERSION
        if '_svgDownloads' in updated_data:
            self._update_svg_downloads_section(updated_data['_svgDownloads'], use_cdn)
        
        logger.info(f"Completed URL replacement:")
        logger.info(f"  - {self.replacement_count} bitmap image references replaced")
        logger.info(f"  - {self.svg_replacement_count} SVG icon references replaced")
        logger.info(f"  - {self.replacement_count + self.svg_replacement_count} total replacements")
        
        return updated_data
    
    def _replace_recursive(self, obj: Union[Dict, list, Any], use_cdn: bool):
        """Recursively traverse and replace image references"""
        if isinstance(obj, dict):
            # Check for image fills
            if 'fills' in obj and isinstance(obj['fills'], list):
                for fill in obj['fills']:
                    if isinstance(fill, dict) and fill.get('type') == 'IMAGE':
                        self._replace_image_ref_in_fill(fill, use_cdn)
            
            # Check for background fills
            if 'backgrounds' in obj and isinstance(obj['backgrounds'], list):
                for bg in obj['backgrounds']:
                    if isinstance(bg, dict) and bg.get('type') == 'IMAGE':
                        self._replace_image_ref_in_fill(bg, use_cdn)
            
            # Check for background property (single fill)
            if 'background' in obj and isinstance(obj['background'], list):
                for bg in obj['background']:
                    if isinstance(bg, dict) and bg.get('type') == 'IMAGE':
                        self._replace_image_ref_in_fill(bg, use_cdn)
            
            # Recursively process all values
            for value in obj.values():
                self._replace_recursive(value, use_cdn)
        
        elif isinstance(obj, list):
            for item in obj:
                self._replace_recursive(item, use_cdn)
    
    def _replace_image_ref_in_fill(self, fill: Dict[str, Any], use_cdn: bool):
        """Replace imageRef in a fill/background object"""
        if 'imageRef' in fill:
            image_ref = fill['imageRef']
            if image_ref in self.url_mapping:
                url_key = 'cdn_url' if use_cdn else 'url'
                new_url = self.url_mapping[image_ref][url_key]
                file_type = self.url_mapping[image_ref]['file_type']
                
                # Replace imageRef with the actual URL
                fill['imageUrl'] = new_url  # Add new field
                fill['originalImageRef'] = image_ref  # Keep original reference
                fill['_imageReplaced'] = True  # Mark as replaced
                fill['_imageType'] = file_type  # Mark the type
                
                # Update scaleMode to FILL if it was using imageRef
                if 'scaleMode' not in fill:
                    fill['scaleMode'] = 'FILL'
                
                if file_type == 'svg':
                    self.svg_replacement_count += 1
                else:
                    self.replacement_count += 1
                    
                logger.debug(f"Replaced {file_type} {image_ref} with {new_url}")
            else:
                logger.warning(f"No URL mapping found for image reference: {image_ref}")
    
    def _update_image_downloads_section(self, image_downloads: Dict[str, Any], use_cdn: bool):
        """Update the _imageDownloads section with URLs"""
        url_key = 'cdn_url' if use_cdn else 'url'
        
        for image_ref, img_data in image_downloads.items():
            if isinstance(img_data, dict) and image_ref in self.url_mapping:
                img_data['uploaded_url'] = self.url_mapping[image_ref][url_key]
                img_data['uploaded_cdn_url'] = self.url_mapping[image_ref]['cdn_url']
                img_data['uploaded_regular_url'] = self.url_mapping[image_ref]['url']
                img_data['uploaded_size_mb'] = self.url_mapping[image_ref]['size_mb']
                img_data['_url_replaced'] = True
    
    def _update_svg_downloads_section(self, svg_downloads: Dict[str, Any], use_cdn: bool):
        """Update the _svgDownloads section with URLs - FIXED VERSION"""
        url_key = 'cdn_url' if use_cdn else 'url'
        
        for node_id, svg_data in svg_downloads.items():
            if isinstance(svg_data, dict):
                # FIXED: Convert node ID to safe filename format that matches uploaded files
                # Original node ID format: "48:55" -> Safe format: "48_55"
                safe_node_id = node_id.replace(':', '_')
                
                # Check if we have URL mapping for this SVG using the safe format
                if safe_node_id in self.url_mapping:
                    svg_data['uploaded_url'] = self.url_mapping[safe_node_id][url_key]
                    svg_data['uploaded_cdn_url'] = self.url_mapping[safe_node_id]['cdn_url']
                    svg_data['uploaded_regular_url'] = self.url_mapping[safe_node_id]['url']
                    svg_data['uploaded_size_mb'] = self.url_mapping[safe_node_id]['size_mb']
                    svg_data['_url_replaced'] = True
                    self.svg_replacement_count += 1
                    logger.debug(f"Updated SVG download {node_id} -> {safe_node_id} with CDN URL")
                else:
                    logger.warning(f"No URL mapping found for SVG node ID: {node_id} (looking for: {safe_node_id})")
                    
                    # ADDITIONAL FIX: Try alternative lookup methods
                    # Sometimes the filename might have additional info, so try partial matches
                    found_alternative = False
                    for mapping_key in self.url_mapping.keys():
                        if mapping_key.startswith(safe_node_id) and self.url_mapping[mapping_key]['file_type'] == 'svg':
                            svg_data['uploaded_url'] = self.url_mapping[mapping_key][url_key]
                            svg_data['uploaded_cdn_url'] = self.url_mapping[mapping_key]['cdn_url']
                            svg_data['uploaded_regular_url'] = self.url_mapping[mapping_key]['url']
                            svg_data['uploaded_size_mb'] = self.url_mapping[mapping_key]['size_mb']
                            svg_data['_url_replaced'] = True
                            self.svg_replacement_count += 1
                            logger.info(f"✅ Found alternative mapping: {node_id} -> {mapping_key}")
                            found_alternative = True
                            break
                    
                    if not found_alternative:
                        logger.error(f"❌ Could not find any URL mapping for SVG: {node_id}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def create_url_replaced_json(self, original_json_path: str, urls_json_path: str, 
                                output_path: str = None, use_cdn: bool = True) -> str:
        """
        Complete workflow to create a new JSON with replaced URLs (supports both bitmap and SVG)
        
        Args:
            original_json_path: Path to original Figma JSON
            urls_json_path: Path to URLs JSON from DigitalOcean
            output_path: Output path for new JSON (optional)
            use_cdn: Whether to use CDN URLs
            
        Returns:
            str: Path to the created file
        """
        try:
            # Load URL mapping
            if not self.load_url_mapping(urls_json_path):
                raise Exception("Failed to load URL mapping")
            
            # Load original Figma JSON
            with open(original_json_path, 'r', encoding='utf-8') as f:
                figma_data = json.load(f)
            
            # Replace image references (both bitmap and SVG)
            updated_data = self.replace_image_references(figma_data, use_cdn)
            
            # Determine output path
            if output_path is None:
                original_path = Path(original_json_path)
                suffix = "_with_urls"
                output_path = original_path.parent / f"{original_path.stem}{suffix}.json"
            
            # Save updated JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created URL-replaced JSON: {output_path}")
            logger.info(f"Replaced {self.replacement_count} bitmap image references")
            logger.info(f"Replaced {self.svg_replacement_count} SVG icon references")
            logger.info(f"Total replacements: {self.replacement_count + self.svg_replacement_count}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating URL-replaced JSON: {e}")
            raise
    
    def generate_replacement_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of the replacement process"""
        
        # Separate mappings by type
        bitmap_mappings = {k: v for k, v in self.url_mapping.items() if v['file_type'] == 'bitmap'}
        svg_mappings = {k: v for k, v in self.url_mapping.items() if v['file_type'] == 'svg'}
        
        return {
            'summary': {
                'total_available_mappings': len(self.url_mapping),
                'bitmap_mappings': len(bitmap_mappings),
                'svg_mappings': len(svg_mappings),
                'total_replacements_made': self.replacement_count + self.svg_replacement_count,
                'bitmap_replacements_made': self.replacement_count,
                'svg_replacements_made': self.svg_replacement_count
            },
            'bitmap_images': {
                'available_refs': list(bitmap_mappings.keys()),
                'mapping_details': {
                    ref: {
                        'filename': data['filename'],
                        'size_mb': data['size_mb'],
                        'has_cdn_url': 'cdn_url' in data,
                        'has_regular_url': 'url' in data
                    }
                    for ref, data in bitmap_mappings.items()
                }
            },
            'svg_icons': {
                'available_refs': list(svg_mappings.keys()),
                'mapping_details': {
                    ref: {
                        'filename': data['filename'],
                        'size_mb': data['size_mb'],
                        'has_cdn_url': 'cdn_url' in data,
                        'has_regular_url': 'url' in data
                    }
                    for ref, data in svg_mappings.items()
                }
            },
            'replacement_timestamp': self._get_timestamp()
        }
    
    def create_comprehensive_mapping(self, figma_json_path: str, output_dir: Path) -> str:
        """
        Create a comprehensive mapping file showing all asset relationships
        
        Args:
            figma_json_path: Path to the Figma JSON file
            output_dir: Directory to save mapping file
            
        Returns:
            str: Path to the created mapping file
        """
        try:
            # Load Figma JSON
            with open(figma_json_path, 'r', encoding='utf-8') as f:
                figma_data = json.load(f)
            
            mapping_data = {
                'metadata': {
                    'generated_at': self._get_timestamp(),
                    'figma_file_key': figma_data.get('_metadata', {}).get('figma_file_key', 'unknown'),
                    'document_name': figma_data.get('_metadata', {}).get('document_name', 'unknown')
                },
                'bitmap_images': {},
                'svg_icons': {},
                'summary': {
                    'total_bitmap_images': 0,
                    'total_svg_icons': 0,
                    'bitmap_with_urls': 0,
                    'svg_with_urls': 0
                }
            }
            
            # Process bitmap images
            if '_imageDownloads' in figma_data:
                for image_ref, img_data in figma_data['_imageDownloads'].items():
                    mapping_data['bitmap_images'][image_ref] = {
                        'filename': img_data.get('filename', ''),
                        'local_path': img_data.get('local_path', ''),
                        'cdn_url': img_data.get('uploaded_cdn_url', ''),
                        'regular_url': img_data.get('uploaded_regular_url', ''),
                        'file_size_mb': round(img_data.get('file_size', 0) / (1024 * 1024), 2),
                        'has_uploaded_url': img_data.get('_url_replaced', False)
                    }
                    mapping_data['summary']['total_bitmap_images'] += 1
                    if img_data.get('_url_replaced', False):
                        mapping_data['summary']['bitmap_with_urls'] += 1
            
            # Process SVG icons
            if '_svgDownloads' in figma_data:
                for node_id, svg_data in figma_data['_svgDownloads'].items():
                    safe_node_id = node_id.replace(':', '_')
                    mapping_data['svg_icons'][safe_node_id] = {
                        'original_node_id': node_id,
                        'component_name': svg_data.get('component_name', ''),
                        'filename': svg_data.get('filename', ''),
                        'local_path': svg_data.get('local_path', ''),
                        'cdn_url': svg_data.get('uploaded_cdn_url', ''),
                        'regular_url': svg_data.get('uploaded_regular_url', ''),
                        'file_size_mb': round(svg_data.get('file_size', 0) / (1024 * 1024), 2),
                        'component_type': svg_data.get('type', ''),
                        'component_path': svg_data.get('path', ''),
                        'has_uploaded_url': svg_data.get('_url_replaced', False)
                    }
                    mapping_data['summary']['total_svg_icons'] += 1
                    if svg_data.get('_url_replaced', False):
                        mapping_data['summary']['svg_with_urls'] += 1
            
            # Save mapping file
            mapping_file = output_dir / "comprehensive_asset_mapping.json"
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Comprehensive asset mapping saved to: {mapping_file}")
            logger.info(f"  - {mapping_data['summary']['total_bitmap_images']} bitmap images ({mapping_data['summary']['bitmap_with_urls']} with URLs)")
            logger.info(f"  - {mapping_data['summary']['total_svg_icons']} SVG icons ({mapping_data['summary']['svg_with_urls']} with URLs)")
            
            return str(mapping_file)
            
        except Exception as e:
            logger.error(f"Error creating comprehensive mapping: {e}")
            raise


def replace_urls_in_figma_json(original_json_path: str, urls_json_path: str, 
                              output_path: str = None, use_cdn: bool = True) -> str:
    """
    Convenience function to replace URLs in Figma JSON (supports both bitmap and SVG)
    
    Args:
        original_json_path: Path to original Figma JSON file
        urls_json_path: Path to DigitalOcean URLs JSON file
        output_path: Output path for new JSON (optional)
        use_cdn: Whether to use CDN URLs (default: True)
        
    Returns:
        str: Path to the created file with replaced URLs
    """
    replacer = URLReplacer()
    return replacer.create_url_replaced_json(
        original_json_path, 
        urls_json_path, 
        output_path, 
        use_cdn
    )