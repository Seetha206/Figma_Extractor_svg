# Enhanced JSON processor for Figma extraction tool
# Add this to your existing project structure

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)

class JSONProcessor:
    """
    Enhanced JSON processor that replaces image references with hosted CDN URLs
    """
    
    def __init__(self):
        self.image_reference_pattern = re.compile(r'^[a-f0-9]{40}$')  # SHA-1 hash pattern
        self.replacement_stats = {
            'total_references_found': 0,
            'successful_replacements': 0,
            'missing_urls': []
        }
    
    def process_json_with_url_replacement(self, 
                                        json_data: Dict[Any, Any], 
                                        uploaded_images: Dict[str, Dict],
                                        use_cdn_urls: bool = True) -> Dict[Any, Any]:
        """
        Process the JSON data and replace image references with hosted URLs
        
        Args:
            json_data: The original Figma JSON data
            uploaded_images: Dictionary mapping image references to upload info
            use_cdn_urls: Whether to use CDN URLs (True) or direct URLs (False)
            
        Returns:
            Enhanced JSON data with URLs replaced
        """
        logger.info("Starting JSON processing with URL replacement...")
        
        # Reset stats
        self.replacement_stats = {
            'total_references_found': 0,
            'successful_replacements': 0,
            'missing_urls': []
        }
        
        # Create URL mapping
        url_mapping = self._create_url_mapping(uploaded_images, use_cdn_urls)
        
        # Process the JSON recursively
        processed_data = self._replace_image_references_recursive(json_data, url_mapping)
        
        # Add enhanced metadata
        processed_data['_urlReplacements'] = {
            'processed_at': self._get_timestamp(),
            'use_cdn_urls': use_cdn_urls,
            'statistics': self.replacement_stats,
            'url_mapping_count': len(url_mapping)
        }
        
        logger.info(f"JSON processing completed:")
        logger.info(f"  - Found {self.replacement_stats['total_references_found']} image references")
        logger.info(f"  - Successfully replaced {self.replacement_stats['successful_replacements']} references")
        logger.info(f"  - Missing URLs for {len(self.replacement_stats['missing_urls'])} references")
        
        return processed_data
    
    def _create_url_mapping(self, uploaded_images: Dict[str, Dict], use_cdn_urls: bool) -> Dict[str, str]:
        """Create mapping from image references to URLs"""
        url_mapping = {}
        
        for image_ref, image_data in uploaded_images.items():
            if use_cdn_urls and 'cdn_url' in image_data:
                url_mapping[image_ref] = image_data['cdn_url']
            elif 'url' in image_data:
                url_mapping[image_ref] = image_data['url']
            elif 'figma_url' in image_data:
                # Fallback to original Figma URL if hosted URL not available
                url_mapping[image_ref] = image_data['figma_url']
                logger.warning(f"Using Figma URL for {image_ref} - hosted URL not available")
        
        logger.info(f"Created URL mapping for {len(url_mapping)} images")
        return url_mapping
    
    def _replace_image_references_recursive(self, obj: Any, url_mapping: Dict[str, str]) -> Any:
        """Recursively traverse and replace image references"""
        
        if isinstance(obj, dict):
            new_obj = {}
            for key, value in obj.items():
                
                # Check for imageRef fields
                if key == 'imageRef' and isinstance(value, str):
                    self.replacement_stats['total_references_found'] += 1
                    
                    if value in url_mapping:
                        # Replace with hosted URL
                        new_obj[key] = value  # Keep original reference
                        new_obj['imageUrl'] = url_mapping[value]  # Add hosted URL
                        new_obj['_imageReplaced'] = True  # Mark as replaced
                        self.replacement_stats['successful_replacements'] += 1
                        
                        logger.debug(f"Replaced image reference: {value}")
                    else:
                        new_obj[key] = value  # Keep original
                        new_obj['_imageMissing'] = True  # Mark as missing
                        self.replacement_stats['missing_urls'].append(value)
                        
                        logger.warning(f"No hosted URL found for image reference: {value}")
                
                # Special handling for image fills
                elif key == 'fills' and isinstance(value, list):
                    new_obj[key] = self._process_fills(value, url_mapping)
                
                # Special handling for backgrounds
                elif key == 'backgrounds' and isinstance(value, list):
                    new_obj[key] = self._process_backgrounds(value, url_mapping)
                
                else:
                    # Recursively process other values
                    new_obj[key] = self._replace_image_references_recursive(value, url_mapping)
            
            return new_obj
        
        elif isinstance(obj, list):
            return [self._replace_image_references_recursive(item, url_mapping) for item in obj]
        
        else:
            return obj
    
    def _process_fills(self, fills: List[Dict], url_mapping: Dict[str, str]) -> List[Dict]:
        """Process fills array for image references"""
        processed_fills = []
        
        for fill in fills:
            new_fill = fill.copy()
            
            if (fill.get('type') == 'IMAGE' and 'imageRef' in fill):
                image_ref = fill['imageRef']
                self.replacement_stats['total_references_found'] += 1
                
                if image_ref in url_mapping:
                    new_fill['imageUrl'] = url_mapping[image_ref]
                    new_fill['_imageReplaced'] = True
                    self.replacement_stats['successful_replacements'] += 1
                    
                    logger.debug(f"Replaced image reference in fill: {image_ref}")
                else:
                    new_fill['_imageMissing'] = True
                    self.replacement_stats['missing_urls'].append(image_ref)
                    
                    logger.warning(f"No hosted URL found for fill image reference: {image_ref}")
            
            processed_fills.append(new_fill)
        
        return processed_fills
    
    def _process_backgrounds(self, backgrounds: List[Dict], url_mapping: Dict[str, str]) -> List[Dict]:
        """Process backgrounds array for image references"""
        processed_backgrounds = []
        
        for bg in backgrounds:
            new_bg = bg.copy()
            
            if (bg.get('type') == 'IMAGE' and 'imageRef' in bg):
                image_ref = bg['imageRef']
                self.replacement_stats['total_references_found'] += 1
                
                if image_ref in url_mapping:
                    new_bg['imageUrl'] = url_mapping[image_ref]
                    new_bg['_imageReplaced'] = True
                    self.replacement_stats['successful_replacements'] += 1
                    
                    logger.debug(f"Replaced image reference in background: {image_ref}")
                else:
                    new_bg['_imageMissing'] = True
                    self.replacement_stats['missing_urls'].append(image_ref)
                    
                    logger.warning(f"No hosted URL found for background image reference: {image_ref}")
            
            processed_backgrounds.append(new_bg)
        
        return processed_backgrounds
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def save_processed_json(self, 
                           processed_data: Dict[Any, Any], 
                           output_path: Path, 
                           pretty_print: bool = True) -> bool:
        """Save the processed JSON to file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty_print:
                    json.dump(processed_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(processed_data, f, ensure_ascii=False)
            
            logger.info(f"Processed JSON saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving processed JSON: {e}")
            return False
    
    def create_reference_mapping_report(self, 
                                      processed_data: Dict[Any, Any], 
                                      output_path: Path) -> bool:
        """Create a detailed report of image reference mappings"""
        try:
            report = {
                'summary': processed_data.get('_urlReplacements', {}),
                'image_references': [],
                'missing_references': self.replacement_stats['missing_urls']
            }
            
            # Extract all image references and their URLs
            self._extract_image_references_for_report(processed_data, report['image_references'])
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Reference mapping report saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating reference mapping report: {e}")
            return False
    
    def _extract_image_references_for_report(self, obj: Any, references_list: List[Dict]) -> None:
        """Extract all image references for reporting"""
        if isinstance(obj, dict):
            if 'imageRef' in obj and 'imageUrl' in obj:
                references_list.append({
                    'imageRef': obj['imageRef'],
                    'imageUrl': obj['imageUrl'],
                    'replaced': obj.get('_imageReplaced', False),
                    'missing': obj.get('_imageMissing', False)
                })
            
            for value in obj.values():
                self._extract_image_references_for_report(value, references_list)
        
        elif isinstance(obj, list):
            for item in obj:
                self._extract_image_references_for_report(item, references_list)


# Enhanced main.py additions
def enhance_main_with_json_processing():
    """
    Add this code to your main.py file to integrate JSON processing
    """
    
    # Add this import at the top of main.py
    # from src.json_processor import JSONProcessor
    
    # Add this code after the JSON is saved (around line 200 in your main.py)
    
    enhanced_main_code = '''
    # Enhanced JSON processing with URL replacement
    if downloaded_images:
        logger.info("Processing JSON with URL replacements...")
        
        # Initialize JSON processor
        json_processor = JSONProcessor()
        
        # Process JSON with URL replacements
        processed_json = json_processor.process_json_with_url_replacement(
            json_data=file_data,
            uploaded_images=downloaded_images,
            use_cdn_urls=True  # Use CDN URLs for better performance
        )
        
        # Save enhanced JSON file
        enhanced_json_filename = f"{document_name}_enhanced.json"
        enhanced_json_path = output_dir / enhanced_json_filename
        
        success = json_processor.save_processed_json(
            processed_data=processed_json,
            output_path=enhanced_json_path,
            pretty_print=True
        )
        
        if success:
            logger.info(f"Enhanced JSON saved to: {enhanced_json_path}")
            
            # Create reference mapping report
            report_filename = f"{document_name}_reference_report.json"
            report_path = output_dir / report_filename
            
            json_processor.create_reference_mapping_report(
                processed_data=processed_json,
                output_path=report_path
            )
            
            # Upload enhanced JSON to DigitalOcean
            if not args.skip_upload:
                enhanced_upload_result = do_uploader.upload_file(
                    str(enhanced_json_path),
                    f"{args.remote_folder}/{enhanced_json_filename}",
                    public_read=True
                )
                
                if enhanced_upload_result['success']:
                    logger.info(f"Enhanced JSON uploaded: {enhanced_upload_result['url']}")
        
        # Update summary output
        print(f"🔗 Enhanced JSON: {enhanced_json_path}")
        print(f"📊 Reference Report: {report_path}")
        print(f"✅ Image references replaced: {json_processor.replacement_stats['successful_replacements']}")
        
        if json_processor.replacement_stats['missing_urls']:
            print(f"⚠️  Missing URLs: {len(json_processor.replacement_stats['missing_urls'])}")
    '''
    
    return enhanced_main_code


# Utility function for testing
def test_json_processing():
    """Test the JSON processing functionality"""
    
    # Sample data for testing
    sample_json = {
        "name": "Test File",
        "document": {
            "children": [
                {
                    "id": "test-node",
                    "fills": [
                        {
                            "type": "IMAGE",
                            "imageRef": "dbf399a8332532b32ad9b3f557ec48ce54958c55"
                        }
                    ],
                    "backgrounds": [
                        {
                            "type": "IMAGE", 
                            "imageRef": "275a0daee60e09660ef4b047a9f00de52101fe0a"
                        }
                    ]
                }
            ]
        }
    }
    
    sample_uploaded_images = {
        "dbf399a8332532b32ad9b3f557ec48ce54958c55": {
            "url": "https://in-cdn1.blr1.digitaloceanspaces.com/figma-images/dbf399a8332532b32ad9b3f557ec48ce54958c55.png",
            "cdn_url": "https://in-cdn1.blr1.cdn.digitaloceanspaces.com/figma-images/dbf399a8332532b32ad9b3f557ec48ce54958c55.png",
            "filename": "dbf399a8332532b32ad9b3f557ec48ce54958c55.png"
        },
        "275a0daee60e09660ef4b047a9f00de52101fe0a": {
            "url": "https://in-cdn1.blr1.digitaloceanspaces.com/figma-images/275a0daee60e09660ef4b047a9f00de52101fe0a.png",
            "cdn_url": "https://in-cdn1.blr1.cdn.digitaloceanspaces.com/figma-images/275a0daee60e09660ef4b047a9f00de52101fe0a.png",
            "filename": "275a0daee60e09660ef4b047a9f00de52101fe0a.png"
        }
    }
    
    # Test processing
    processor = JSONProcessor()
    result = processor.process_json_with_url_replacement(
        sample_json, 
        sample_uploaded_images, 
        use_cdn_urls=True
    )
    
    print("Test Results:")
    print(json.dumps(result, indent=2))
    
    return result


if __name__ == "__main__":
    # Run test
    test_json_processing()