import json
import os
import re
import requests
import time
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

class FigmaExtractor:
    """FIXED Figma API extractor with child-based individual vector extraction"""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.figma.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'X-Figma-Token': self.api_token,
            'Content-Type': 'application/json',
            'User-Agent': 'Fixed-Child-Based-Figma-Extractor/3.0'
        })
        
        # Rate limiting for enhanced extraction
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Processing statistics
        self.stats = {
            'api_calls': 0,
            'downloads': 0,
            'errors': 0,
            'individual_vectors_downloaded': 0,
            'bitmap_images_found': 0,
            'fill_images_found': 0
        }
    
    def _rate_limit(self):
        """Rate limiting to avoid overwhelming Figma API"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def validate_token(self) -> bool:
        """Validate the API token"""
        try:
            self._rate_limit()
            response = self.session.get(f"{self.base_url}/me", timeout=10)
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"Authenticated as: {user_info.get('email', 'Unknown user')}")
                return True
            else:
                logger.error(f"Token validation failed: {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Error validating token: {e}")
            return False
    
    def get_file_data(self, file_key: str, include_images: bool = False) -> Optional[Dict]:
        """Extract complete file data from Figma"""
        try:
            endpoint = f"{self.base_url}/files/{file_key}"
            params = {}
            if include_images:
                params['include_images'] = 'true'
            
            logger.info(f"Fetching file data for: {file_key}")
            self._rate_limit()
            response = self.session.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched file: {data.get('name', 'Unknown')}")
                return data
            elif response.status_code == 403:
                logger.error("Access denied. Check your API token and file permissions.")
                return None
            elif response.status_code == 404:
                logger.error("File not found. Check your file key.")
                return None
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching file data: {e}")
            return None
    
    def get_file_image_fills(self, file_key: str) -> Optional[Dict]:
        """Get original image fills from Figma file"""
        try:
            endpoint = f"{self.base_url}/image_fills/{file_key}"
            
            logger.info("Fetching original image files...")
            self._rate_limit()
            response = self.session.get(endpoint, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Successfully received image fills data")
                return result
            else:
                logger.warning(f"Image fills request failed: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching image fills: {e}")
            return None
    
    def get_file_images(self, file_key: str, node_ids: Optional[List[str]] = None) -> Optional[Dict]:
        """Get rendered image URLs from Figma file"""
        try:
            endpoint = f"{self.base_url}/images/{file_key}"
            
            params = {
                'format': 'png',
                'scale': '2'
            }
            
            if node_ids:
                clean_node_ids = [str(node_id).strip() for node_id in node_ids if ':' in str(node_id)]
                if not clean_node_ids:
                    logger.error("No valid node IDs found")
                    return None
                
                params['ids'] = ','.join(clean_node_ids)
                logger.info(f"Fetching rendered images for {len(clean_node_ids)} nodes")
            
            self._rate_limit()
            response = self.session.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Successfully received rendered image URLs")
                return result
            else:
                logger.error(f"Images request failed: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching image URLs: {e}")
            return None
    
    def download_image(self, url: str, filepath: Path, max_retries: int = 3) -> bool:
        """Download a single image with enhanced retry logic and progress tracking"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, stream=True, timeout=30)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    self.stats['downloads'] += 1
                    return True
                else:
                    logger.warning(f"Download failed: HTTP {response.status_code}")
                    return False
                    
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {filepath.name}: {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Download failed after {max_retries} attempts: {e}")
                    self.stats['errors'] += 1
                    return False
        
        return False
    
    def find_image_references_and_nodes(self, data) -> Tuple[Set[str], Set[str]]:
        """Find all image references and their containing nodes"""
        image_refs = set()
        image_nodes = set()
        
        def traverse(obj, current_node_id=None):
            if isinstance(obj, dict):
                if 'id' in obj and ':' in str(obj['id']):
                    current_node_id = obj['id']
                
                # Check for image fills
                if 'fills' in obj:
                    for fill in obj['fills']:
                        if fill.get('type') == 'IMAGE' and 'imageRef' in fill:
                            image_refs.add(fill['imageRef'])
                            if current_node_id:
                                image_nodes.add(current_node_id)
                
                # Check for background fills
                if 'backgrounds' in obj:
                    for bg in obj['backgrounds']:
                        if bg.get('type') == 'IMAGE' and 'imageRef' in bg:
                            image_refs.add(bg['imageRef'])
                            if current_node_id:
                                image_nodes.add(current_node_id)
                
                for value in obj.values():
                    traverse(value, current_node_id)
                    
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item, current_node_id)
        
        traverse(data)
        return image_refs, image_nodes
    
    def download_images_from_file(self, file_key: str, file_data: Dict, output_dir: Path) -> Dict[str, Dict]:
        """Enhanced image download with better progress tracking and error handling"""
        image_refs, image_nodes = self.find_image_references_and_nodes(file_data)
        
        if not image_refs:
            logger.info("No fill/background images found in the file")
            return {}
        
        logger.info(f"Found {len(image_refs)} unique image references:")
        for i, ref in enumerate(list(image_refs)[:5], 1):
            logger.info(f"   {i}. {ref}")
        if len(image_refs) > 5:
            logger.info(f"   ... and {len(image_refs) - 5} more")
        
        self.stats['fill_images_found'] = len(image_refs)
        
        # Try original image fills first - this should map imageRef to download URL
        image_fills_response = self.get_file_image_fills(file_key)
        
        if image_fills_response and 'images' in image_fills_response:
            logger.info("Using original image fills method (preferred)")
            return self._download_original_images(image_fills_response['images'], image_refs, output_dir)
        else:
            logger.info("Original image fills not available, falling back to node rendering")
            if image_nodes:
                images_response = self.get_file_images(file_key, list(image_nodes))
                if images_response and 'images' in images_response:
                    return self._download_rendered_images(images_response['images'], image_nodes, file_data, output_dir)
        
        return {}
    
    def _download_original_images(self, image_urls: Dict, image_refs: Set[str], output_dir: Path) -> Dict[str, Dict]:
        """Download original images using their Figma image references with progress tracking"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Filter to only include image references that we found in the JSON AND have download URLs
        valid_image_mapping = {}
        for image_ref in image_refs:
            if image_ref in image_urls and image_urls[image_ref]:
                valid_image_mapping[image_ref] = image_urls[image_ref]
        
        if not valid_image_mapping:
            logger.warning("No valid download URLs found for the image references in the file")
            return {}
        
        logger.info(f"📥 Downloading {len(valid_image_mapping)} fill/background images...")
        
        downloaded_images = {}
        successful_downloads = 0
        
        for i, (image_ref, download_url) in enumerate(valid_image_mapping.items(), 1):
            # Determine file extension from URL
            parsed_url = urlparse(download_url)
            path_parts = parsed_url.path.split('.')
            extension = path_parts[-1].lower() if len(path_parts) > 1 and path_parts[-1].lower() in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'] else 'png'
            
            # Use the actual image reference as filename
            filename = f"{image_ref}.{extension}"
            filepath = output_dir / filename
            
            logger.info(f"[{i}/{len(valid_image_mapping)}] Downloading: {image_ref}")
            
            if self.download_image(download_url, filepath):
                # Store using image reference as key
                downloaded_images[image_ref] = {
                    'local_path': str(filepath),
                    'figma_url': download_url,
                    'filename': filename,
                    'file_size': filepath.stat().st_size,
                    'extension': extension,
                    'image_ref': image_ref
                }
                successful_downloads += 1
                file_size = filepath.stat().st_size / 1024
                logger.info(f"✅ Downloaded: {image_ref} → {filename} ({file_size:.1f} KB)")
            else:
                logger.error(f"❌ Failed to download: {image_ref}")
            
            time.sleep(0.2)  # Be respectful to servers
        
        logger.info(f"Successfully downloaded {successful_downloads}/{len(valid_image_mapping)} images using image references")
        return downloaded_images
    
    def _download_rendered_images(self, image_urls: Dict, image_nodes: Set[str], file_data: Dict, output_dir: Path) -> Dict[str, Dict]:
        """Download rendered images as fallback, mapping them to their image references"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        valid_image_urls = {node_id: url for node_id, url in image_urls.items() if url}
        
        if not valid_image_urls:
            logger.warning("No valid rendered image URLs available")
            return {}
        
        logger.info(f"📥 Downloading {len(valid_image_urls)} rendered images and mapping to image references")
        
        downloaded_images = {}
        successful_downloads = 0
        
        for i, (node_id, image_url) in enumerate(valid_image_urls.items(), 1):
            # Find the actual image reference for this node
            image_ref = self._find_image_ref_for_node(file_data, node_id)
            
            if image_ref:
                filename = f"{image_ref}.png"
                logger.info(f"[{i}/{len(valid_image_urls)}] Found image reference {image_ref} for node {node_id}")
            else:
                image_ref = f"node_{node_id.replace(':', '_')}"
                filename = f"{image_ref}.png"
                logger.warning(f"[{i}/{len(valid_image_urls)}] No image reference found for node {node_id}, using: {image_ref}")
            
            filepath = output_dir / filename
            
            if self.download_image(image_url, filepath):
                downloaded_images[image_ref] = {
                    'local_path': str(filepath),
                    'figma_url': image_url,
                    'filename': filename,
                    'file_size': filepath.stat().st_size,
                    'extension': 'png',
                    'node_id': node_id,
                    'source': 'rendered',
                    'image_ref': image_ref
                }
                successful_downloads += 1
                file_size = filepath.stat().st_size / 1024
                logger.info(f"✅ Downloaded: {image_ref} → {filename} ({file_size:.1f} KB)")
            else:
                logger.error(f"❌ Failed to download: {image_ref}")
            
            time.sleep(0.2)
        
        logger.info(f"Successfully downloaded {successful_downloads}/{len(valid_image_urls)} rendered images")
        return downloaded_images
    
    def _find_image_ref_for_node(self, data, target_node_id):
        """Find the image reference for a specific node ID."""
        def traverse(obj):
            if isinstance(obj, dict):
                if obj.get('id') == target_node_id:
                    # Check fills for image refs
                    if 'fills' in obj:
                        for fill in obj['fills']:
                            if fill.get('type') == 'IMAGE' and 'imageRef' in fill:
                                return fill['imageRef']
                    # Check backgrounds for image refs
                    if 'backgrounds' in obj:
                        for bg in obj['backgrounds']:
                            if bg.get('type') == 'IMAGE' and 'imageRef' in bg:
                                return bg['imageRef']
                
                # Recursively check children
                for value in obj.values():
                    result = traverse(value)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = traverse(item)
                    if result:
                        return result
            return None
        
        return traverse(data)
    
    # ============================================================================
    # FIXED: CHILD-BASED INDIVIDUAL SVG EXTRACTION (NO MORE COMPOSITION/STRIPS)
    # ============================================================================
    
    def download_svg_icons_from_preprocessed(self, file_key: str, preprocessed_data: Dict, output_dir: Path) -> Dict[str, Dict]:
        """
        FIXED: Child-based SVG download - each vector child becomes its own SVG file
        No more composition, no more strips, clean individual files
        """
        
        # Check if we have preprocessed SVG structure
        if '_svgDownloads' not in preprocessed_data or not preprocessed_data['_svgDownloads']:
            logger.warning("No preprocessed SVG structure found, falling back to standard extraction")
            return self.download_svg_icons_fallback(file_key, preprocessed_data, output_dir)
        
        svg_downloads_structure = preprocessed_data['_svgDownloads']
        
        logger.info(f"🎨 Using child-based filtered structure with {len(svg_downloads_structure)} individual SVG exports")
        
        # Create SVG output directory
        svg_dir = output_dir / "svg_icons"
        svg_dir.mkdir(parents=True, exist_ok=True)
        
        # FIXED: All entries are now individual vectors (no groups)
        individual_vectors = []
        
        for node_id, svg_info in svg_downloads_structure.items():
            individual_vectors.append({
                'id': node_id,
                'name': svg_info['component_name'],
                'type': svg_info['type'],
                'filename': svg_info['filename'],
                'path': svg_info.get('path', ''),
                'extraction_reason': svg_info.get('extraction_reason', 'INDIVIDUAL_VECTOR'),
                'parent_group': svg_info.get('parent_group_name', 'None')
            })
        
        downloaded_svgs = {}
        successful_downloads = 0
        
        logger.info(f"🎨 Processing {len(individual_vectors)} individual vector children...")
        
        # FIXED: Process individual vectors in batches (no composition needed)
        batch_size = 10
        for i in range(0, len(individual_vectors), batch_size):
            batch = individual_vectors[i:i + batch_size]
            node_ids = [vector['id'] for vector in batch]
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(individual_vectors)-1)//batch_size + 1} ({len(batch)} vectors)")
            
            # Export batch as individual SVGs
            svg_urls = self.export_svg_batch(file_key, node_ids)
            if not svg_urls:
                logger.warning("Failed to export this SVG batch")
                continue
            
            # FIXED: Download each vector individually (no composition)
            for vector in batch:
                node_id = vector['id']
                
                if node_id in svg_urls and svg_urls[node_id]:
                    # Download individual SVG content
                    svg_content = self.download_svg_content(svg_urls[node_id])
                    
                    if svg_content:
                        # FIXED: Use child ID for filename (262_48.svg not 12_171.svg)
                        filename = vector['filename']
                        filepath = svg_dir / filename
                        
                        # Save individual SVG file
                        try:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(svg_content)
                            
                            # Store download info using child node ID as key
                            downloaded_svgs[node_id] = {
                                'local_path': str(filepath),
                                'figma_url': svg_urls[node_id],
                                'filename': filename,
                                'component_name': vector['name'],
                                'file_size': filepath.stat().st_size,
                                'node_id': node_id,
                                'type': vector['type'],
                                'extraction_reason': vector['extraction_reason'],
                                'path': vector['path'],
                                'parent_group': vector['parent_group'],
                                'is_group': False  # Always false now
                            }
                            
                            successful_downloads += 1
                            file_size = filepath.stat().st_size / 1024
                            parent_info = f" (from group: {vector['parent_group']})" if vector['parent_group'] != 'None' else ""
                            logger.info(f"✅ Downloaded individual vector: {vector['name']} → {filename} ({file_size:.1f} KB){parent_info}")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to save individual SVG {filename}: {e}")
                    else:
                        logger.error(f"❌ Failed to download individual SVG: {vector['name']}")
                else:
                    logger.warning(f"⚠️ No SVG URL for: {vector['name']}")
            
            # Rate limiting between batches
            time.sleep(1)
        
        # Save enhanced mapping file using child-based data
        if downloaded_svgs:
            mapping_file = svg_dir / "svg_mapping.json"
            mapping_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'figma_file_key': file_key,
                    'total_components': len(svg_downloads_structure),
                    'successful_downloads': successful_downloads,
                    'extraction_approach': 'child_based_individual_vectors',
                    'no_composition': True,
                    'no_strips': True,
                    'filtering_approach': 'content_first_with_child_based_extraction'
                },
                'components': {}
            }
            
            for node_id, svg_data in downloaded_svgs.items():
                safe_node_id = node_id.replace(':', '_')
                
                component_info = {
                    'original_node_id': node_id,
                    'filename': svg_data['filename'],
                    'component_name': svg_data['component_name'],
                    'type': svg_data['type'],
                    'extraction_reason': svg_data['extraction_reason'],
                    'path': svg_data['path'],
                    'parent_group': svg_data.get('parent_group', 'None'),
                    'is_individual': True,
                    'file_size_kb': round(svg_data.get('file_size', 0) / 1024, 2)
                }
                
                mapping_data['components'][safe_node_id] = component_info
            
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📋 Child-based SVG mapping saved to: {mapping_file}")
        
        logger.info(f"🎨 FIXED child-based SVG download completed: {successful_downloads}/{len(svg_downloads_structure)} successful")
        logger.info(f"   ✅ All vectors exported as individual SVG files")
        logger.info(f"   ✅ No multi-icon strips created")
        logger.info(f"   ✅ Clean child-based naming (e.g., 262_48.svg)")
        
        # Update stats
        self.stats['individual_vectors_downloaded'] = successful_downloads
        
        return downloaded_svgs
    
    def download_svg_icons(self, file_key: str, file_data: Dict, output_dir: Path, 
                          include_all_exportable: bool = True, batch_size: int = 10) -> Dict[str, Dict]:
        """
        FIXED: Main SVG download method with child-based extraction integration
        """
        
        # Check if we have preprocessed data and use it instead
        if '_metadata' in file_data and file_data['_metadata'].get('preprocessing_applied', False):
            logger.info("🔧 Using child-based filtered JSON structure for SVG extraction")
            return self.download_svg_icons_from_preprocessed(file_key, file_data, output_dir)
        
        # FALLBACK: Use standard method if no preprocessing
        logger.info("📊 No child-based filtering detected, using fallback SVG extraction")
        return self.download_svg_icons_fallback(file_key, file_data, output_dir, include_all_exportable, batch_size)
    
    def download_svg_icons_fallback(self, file_key: str, file_data: Dict, output_dir: Path, 
                                   include_all_exportable: bool = True, batch_size: int = 10) -> Dict[str, Dict]:
        """Fallback SVG download method for non-preprocessed data"""
        
        # Find all SVG components using fallback logic
        components = self.find_svg_components_fallback(file_data, include_all_exportable)
        
        if not components:
            logger.info("No SVG components found in the file")
            return {}
        
        logger.info(f"🎨 Starting fallback SVG download for {len(components)} components...")
        
        # Create SVG output directory
        svg_dir = output_dir / "svg_icons"
        svg_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_svgs = {}
        successful_downloads = 0
        
        # Process components in batches
        for i in range(0, len(components), batch_size):
            batch = components[i:i + batch_size]
            node_ids = [comp['id'] for comp in batch]
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(components)-1)//batch_size + 1}")
            
            # Export batch as SVG
            svg_urls = self.export_svg_batch(file_key, node_ids)
            if not svg_urls:
                logger.warning("Failed to export this SVG batch")
                continue
            
            # Download each SVG in the batch
            for component in batch:
                node_id = component['id']
                
                if node_id in svg_urls and svg_urls[node_id]:
                    # Download SVG content
                    svg_content = self.download_svg_content(svg_urls[node_id])
                    
                    if svg_content:
                        # Generate filename using node ID that URLReplacer expects
                        filename = self.sanitize_svg_filename(node_id, component['name'])
                        filepath = svg_dir / filename
                        
                        # Save SVG file
                        try:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(svg_content)
                            
                            # Store download info using node ID as key
                            downloaded_svgs[node_id] = {
                                'local_path': str(filepath),
                                'figma_url': svg_urls[node_id],
                                'filename': filename,
                                'component_name': component['name'],
                                'file_size': filepath.stat().st_size,
                                'node_id': node_id,
                                'type': component['type'],
                                'reason': component['reason'],
                                'path': component['path'],
                                'is_group': False
                            }
                            
                            successful_downloads += 1
                            file_size = filepath.stat().st_size / 1024
                            logger.info(f"✅ Downloaded fallback component: {component['name']} → {filename} ({file_size:.1f} KB)")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to save fallback SVG {filename}: {e}")
                    else:
                        logger.error(f"❌ Failed to download fallback SVG: {component['name']}")
                else:
                    logger.warning(f"⚠️ No SVG URL for: {component['name']}")
            
            # Rate limiting between batches
            time.sleep(1)
        
        logger.info(f"🎨 Fallback SVG download completed: {successful_downloads}/{len(components)} successful")
        return downloaded_svgs
    
    def find_svg_components_fallback(self, file_data: Dict, include_all_exportable: bool = True) -> List[Dict]:
        """Fallback component finder for non-preprocessed data"""
        components = []
        
        def traverse_node(node, path=""):
            current_path = f"{path}/{node.get('name', 'Unnamed')}" if path else node.get('name', 'Unnamed')
            
            node_type = node.get('type', '')
            node_name = node.get('name', '').lower()
            node_id = node.get('id', '')
            
            # Basic component detection
            should_export = False
            reason = ""
            
            if include_all_exportable:
                if node_type == 'COMPONENT':
                    should_export = True
                    reason = "COMPONENT"
                elif node_type in ['VECTOR']:
                    should_export = True
                    reason = f"SHAPE_{node_type}"
                elif node_type == 'INSTANCE':
                    should_export = True
                    reason = "INSTANCE"
            else:
                if node_type == 'COMPONENT':
                    should_export = True
                    reason = "COMPONENT"
            
            # Add to components list if exportable
            if should_export and node.get('visible', True):
                component_info = {
                    'id': node_id,
                    'name': node.get('name', 'Unnamed'),
                    'path': current_path,
                    'type': node_type,
                    'reason': reason,
                    'absoluteBoundingBox': node.get('absoluteBoundingBox', {}),
                    'visible': node.get('visible', True),
                    'is_group': False
                }
                components.append(component_info)
            
            # Recursively check children
            if 'children' in node:
                for child in node['children']:
                    traverse_node(child, current_path)
        
        # Start traversal from document root
        if 'document' in file_data:
            for page in file_data['document'].get('children', []):
                traverse_node(page)
        
        return components
    
    def export_svg_batch(self, file_key: str, node_ids: List[str], max_retries: int = 3) -> Optional[Dict]:
        """Enhanced SVG export with better error handling and progress tracking"""
        endpoint = f"{self.base_url}/images/{file_key}"
        params = {
            'ids': ','.join(node_ids),
            'format': 'svg',
            'svg_outline_text': 'false',
            'svg_include_id': 'true',
            'svg_simplify_stroke': 'true'
        }
        
        logger.info(f"🎨 Exporting {len(node_ids)} components as individual SVGs...")
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                response = self.session.get(endpoint, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if data.get('err'):
                    logger.error(f"API Error: {data['err']}")
                    return None
                
                self.stats['api_calls'] += 1
                return data.get('images', {})
                
            except requests.RequestException as e:
                logger.warning(f"SVG export attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("Max retries reached for SVG export")
                    self.stats['errors'] += 1
                    return None
    
    def download_svg_content(self, url: str) -> Optional[str]:
        """Download SVG content from URL with error handling"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error downloading SVG from {url}: {e}")
            self.stats['errors'] += 1
            return None
    
    def sanitize_svg_filename(self, node_id: str, name: str = "") -> str:
        """Create safe filename from node ID and name - FIXED TO MATCH URLReplacer EXPECTATIONS"""
        # FIXED: Generate filename that URLReplacer can find
        # URLReplacer expects: 262_48.svg for node ID 262:48
        safe_id = node_id.replace(':', '_')
        return f"{safe_id}.svg"
    
    # ============================================================================
    # PRESERVED EXISTING METHODS FOR COMPATIBILITY
    # ============================================================================
    
    def list_pages_and_frames(self, file_key: str) -> List[Dict]:
        """Get list of pages and frames for selective extraction"""
        file_data = self.get_file_data(file_key, include_images=False)
        if not file_data or 'document' not in file_data:
            return []
        
        pages_and_frames = []
        document = file_data['document']
        
        pages_and_frames.append({
            'id': document['id'],
            'name': f"📄 {document.get('name', 'Document Root')}",
            'type': 'DOCUMENT',
            'level': 0
        })
        
        if 'children' in document:
            for page in document['children']:
                pages_and_frames.append({
                    'id': page['id'],
                    'name': f"📑 {page.get('name', 'Unnamed Page')}",
                    'type': page.get('type', 'Unknown'),
                    'level': 1
                })
                
                if 'children' in page:
                    for frame in page['children']:
                        pages_and_frames.append({
                            'id': frame['id'],
                            'name': f"   🖼️ {frame.get('name', 'Unnamed Frame')}",
                            'type': frame.get('type', 'Unknown'),
                            'level': 2
                        })
        
        return pages_and_frames
    
    def extract_specific_nodes(self, file_key: str, node_ids: List[str]) -> Optional[Dict]:
        """Extract specific nodes and build filtered document structure"""
        full_data = self.get_file_data(file_key, include_images=False)
        if not full_data:
            return None
        
        nodes_data = self.get_file_nodes(file_key, node_ids)
        if not nodes_data:
            return None
        
        # Build filtered structure
        filtered_data = {
            'name': full_data.get('name', 'Unknown'),
            'lastModified': full_data.get('lastModified'),
            'thumbnailUrl': full_data.get('thumbnailUrl'),
            'version': full_data.get('version'),
            'role': full_data.get('role'),
            'editorType': full_data.get('editorType'),
            'linkAccess': full_data.get('linkAccess'),
            'document': {
                'id': 'filtered-document',
                'name': 'Filtered Export',
                'type': 'DOCUMENT',
                'children': []
            },
            'components': full_data.get('components', {}),
            'styles': full_data.get('styles', {}),
            'schemaVersion': full_data.get('schemaVersion', 0)
        }
        
        for node_id in node_ids:
            if node_id in nodes_data.get('nodes', {}):
                node = nodes_data['nodes'][node_id]['document']
                filtered_data['document']['children'].append(node)
        
        return filtered_data
    
    def get_file_nodes(self, file_key: str, node_ids: List[str]) -> Optional[Dict]:
        """Extract specific nodes from a Figma file"""
        try:
            endpoint = f"{self.base_url}/files/{file_key}/nodes"
            params = {'ids': ','.join(node_ids)}
            
            logger.info(f"Fetching specific nodes from Figma API...")
            self._rate_limit()
            response = self.session.get(endpoint, params=params, timeout=30)
            
            if response.status_code == 200:
                self.stats['api_calls'] += 1
                return response.json()
            else:
                logger.error(f"Error fetching nodes: {response.status_code}")
                self.stats['errors'] += 1
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching node data: {e}")
            self.stats['errors'] += 1
            return None
    
    # ============================================================================
    # STATISTICS AND UTILITY METHODS
    # ============================================================================
    
    def get_extraction_stats(self) -> Dict[str, any]:
        """Get extraction statistics"""
        return {
            'api_calls': self.stats['api_calls'],
            'total_downloads': self.stats['downloads'],
            'total_errors': self.stats['errors'],
            'individual_vectors_downloaded': self.stats['individual_vectors_downloaded'],
            'bitmap_images_found': self.stats['bitmap_images_found'],
            'fill_images_found': self.stats['fill_images_found'],
            'success_rate': round((self.stats['downloads'] / max(self.stats['downloads'] + self.stats['errors'], 1)) * 100, 2)
        }
    
    def print_extraction_summary(self):
        """Print extraction summary"""
        stats = self.get_extraction_stats()
        
        logger.info("\n" + "="*50)
        logger.info("🎯 FIXED CHILD-BASED EXTRACTION SUMMARY")
        logger.info("="*50)
        logger.info(f"📡 API Calls: {stats['api_calls']}")
        logger.info(f"📥 Total Downloads: {stats['total_downloads']}")
        logger.info(f"❌ Errors: {stats['total_errors']}")
        logger.info(f"📈 Success Rate: {stats['success_rate']}%")
        logger.info("")
        logger.info("🎨 Assets Found:")
        logger.info(f"   🎨 Individual Vectors: {stats['individual_vectors_downloaded']}")
        logger.info(f"   🖼️ Bitmap Images: {stats['bitmap_images_found']}")
        logger.info(f"   🌈 Fill/Background Images: {stats['fill_images_found']}")
        logger.info("")
        logger.info("✅ FIXED Features:")
        logger.info("   • Child-based extraction (no composition)")
        logger.info("   • Individual SVG files (no strips)")
        logger.info("   • Clean naming (262_48.svg)")
        logger.info("   • URLReplacer compatible")
        logger.info("="*50)