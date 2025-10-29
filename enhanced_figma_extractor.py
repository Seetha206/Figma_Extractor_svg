"""
Enhanced Figma Extractor - Group-based SVG extraction with comprehensive asset support
Downloads vector GROUPS as single combined SVGs + handles all asset types
"""

import requests
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class EnhancedFigmaExtractor:
    """Enhanced Figma extractor with group-based SVG extraction and comprehensive asset support"""
    
    def __init__(self, figma_token: str):
        self.figma_token = figma_token
        self.base_url = "https://api.figma.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'X-Figma-Token': figma_token,
            'User-Agent': 'Enhanced-Figma-Extractor/2.0'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Processing statistics
        self.stats = {
            'api_calls': 0,
            'downloads': 0,
            'errors': 0,
            'groups_found': 0,
            'individual_vectors_found': 0,
            'direct_images_found': 0,
            'fill_images_found': 0
        }
    
    def _rate_limit(self):
        """Simple rate limiting to avoid overwhelming Figma API"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with rate limiting and error handling"""
        
        self._rate_limit()
        self.stats['api_calls'] += 1
        
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limited - wait and retry once
                logger.warning("Rate limited by Figma API, waiting 60 seconds...")
                time.sleep(60)
                response = self.session.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    return response.json()
            
            logger.error(f"API request failed: {response.status_code} - {response.text}")
            self.stats['errors'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Request error: {e}")
            self.stats['errors'] += 1
            return None
    
    def validate_token(self) -> bool:
        """Validate Figma API token"""
        
        try:
            result = self._make_request("me")
            return result is not None and 'id' in result
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False
    
    def get_file_data(self, file_key: str, include_images: bool = True) -> Optional[Dict]:
        """Get complete file data from Figma"""
        
        logger.info(f"📥 Fetching file data for: {file_key}")
        
        params = {}
        if include_images:
            params['plugin_data'] = 'shared'
        
        file_data = self._make_request(f"files/{file_key}", params)
        
        if file_data and 'document' in file_data:
            logger.info(f"✅ File data retrieved: {file_data['name']}")
            return file_data
        else:
            logger.error("❌ Failed to retrieve file data")
            return None
    
    # =========================================================================
    # GROUP-BASED SVG EXTRACTION
    # =========================================================================
    
    def find_groups_with_vectors(self, file_data: Dict) -> List[Dict]:
        """Find GROUP nodes that contain vector children"""
        
        logger.info("🔍 Finding vector groups in file...")
        
        vector_groups = []
        
        def traverse_node(node: Dict, path: str = "", parent_groups: List[str] = None):
            if parent_groups is None:
                parent_groups = []
            
            node_type = node.get('type', '')
            node_id = node.get('id', '')
            node_name = node.get('name', 'Unnamed')
            current_path = f"{path}/{node_name}" if path else node_name
            
            # Check if this is a GROUP with vector children
            if node_type == 'GROUP':
                vector_children = self._get_vector_children(node)
                
                if vector_children:
                    # This group contains vectors - add it to our list
                    group_info = {
                        'id': node_id,
                        'name': node_name,
                        'path': current_path,
                        'vector_children': vector_children,
                        'vector_count': len(vector_children),
                        'bounds': node.get('absoluteBoundingBox', {}),
                        'parent_groups': parent_groups.copy()
                    }
                    vector_groups.append(group_info)
                    
                    logger.debug(f"📦 Found vector group: {node_name} ({len(vector_children)} vectors)")
                    
                    # Add this group to parent_groups for nested traversal
                    new_parent_groups = parent_groups + [node_id]
                else:
                    # Group without vectors - continue traversal normally
                    new_parent_groups = parent_groups
                
                # Continue traversing children for nested groups
                for child in node.get('children', []):
                    traverse_node(child, current_path, new_parent_groups)
            
            else:
                # Not a group - continue normal traversal
                for child in node.get('children', []):
                    traverse_node(child, current_path, parent_groups)
        
        # Start traversal from document root
        document = file_data.get('document', {})
        for page in document.get('children', []):
            traverse_node(page)
        
        self.stats['groups_found'] = len(vector_groups)
        logger.info(f"✅ Found {len(vector_groups)} vector groups")
        
        return vector_groups
    
    def _get_vector_children(self, group_node: Dict) -> List[Dict]:
        """Get all vector children from a group node"""
        
        vector_children = []
        
        def find_vectors(node: Dict, depth: int = 0):
            if depth > 10:  # Prevent infinite recursion
                return
            
            node_type = node.get('type', '')
            
            # Check if this node is a vector
            if node_type in ['VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'POLYGON']:
                vector_children.append({
                    'id': node.get('id'),
                    'name': node.get('name', 'Vector'),
                    'type': node_type,
                    'bounds': node.get('absoluteBoundingBox', {})
                })
            
            # Recursively check children
            for child in node.get('children', []):
                find_vectors(child, depth + 1)
        
        # Start from group's children
        for child in group_node.get('children', []):
            find_vectors(child)
        
        return vector_children
    
    def download_group_svgs(self, file_key: str, vector_groups: List[Dict], output_dir: Path) -> Dict[str, Dict]:
        """Download vector groups as combined SVG files"""
        
        if not vector_groups:
            logger.info("No vector groups to download")
            return {}
        
        logger.info(f"📦 Downloading {len(vector_groups)} group SVGs...")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_groups = {}
        
        # Get export URLs for all groups at once
        group_ids = [group['id'] for group in vector_groups]
        export_urls = self._get_svg_export_urls(file_key, group_ids)
        
        if not export_urls:
            logger.error("❌ Failed to get export URLs for groups")
            return {}
        
        # Download each group SVG
        for i, group in enumerate(vector_groups, 1):
            group_id = group['id']
            
            if group_id not in export_urls:
                logger.warning(f"⚠️  No export URL for group: {group['name']}")
                continue
            
            # Create safe filename
            safe_name = self._sanitize_filename(group['name'])
            filename = f"group_{group_id.replace(':', '_')}_{safe_name}.svg"
            file_path = output_dir / filename
            
            # Download SVG
            export_url = export_urls[group_id]
            if self._download_file(export_url, file_path):
                downloaded_groups[group_id] = {
                    'local_path': str(file_path),
                    'filename': filename,
                    'group_name': group['name'],
                    'path': group['path'],
                    'vector_count': group['vector_count'],
                    'file_size': file_path.stat().st_size if file_path.exists() else 0,
                    'node_id': group_id,
                    'type': 'GROUP_SVG',
                    'vector_children': group['vector_children'],
                    'bounds': group['bounds']
                }
                
                logger.info(f"✅ [{i}/{len(vector_groups)}] Downloaded group: {group['name']} ({group['vector_count']} vectors)")
                self.stats['downloads'] += 1
            else:
                logger.error(f"❌ [{i}/{len(vector_groups)}] Failed to download group: {group['name']}")
                self.stats['errors'] += 1
            
            # Brief pause between downloads
            time.sleep(0.1)
        
        logger.info(f"📦 Group SVG download completed: {len(downloaded_groups)} successful")
        return downloaded_groups
    
    # =========================================================================
    # INDIVIDUAL VECTOR EXTRACTION
    # =========================================================================
    
    def find_individual_vectors(self, file_data: Dict) -> List[Dict]:
        """Find individual vector nodes that are NOT in groups"""
        
        logger.info("🔍 Finding individual vectors (not in groups)...")
        
        individual_vectors = []
        group_member_ids = set()
        
        # First, collect all vector IDs that are inside groups
        def collect_group_members(node: Dict):
            node_type = node.get('type', '')
            
            if node_type == 'GROUP':
                # This is a group - collect all vector children
                vector_children = self._get_vector_children(node)
                for vector_child in vector_children:
                    group_member_ids.add(vector_child['id'])
            
            # Continue traversal
            for child in node.get('children', []):
                collect_group_members(child)
        
        # Now find vectors that are NOT in groups
        def find_standalone_vectors(node: Dict, path: str = ""):
            node_type = node.get('type', '')
            node_id = node.get('id', '')
            node_name = node.get('name', 'Unnamed')
            current_path = f"{path}/{node_name}" if path else node_name
            
            # Check if this is a vector that's not in a group
            if node_type in ['VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'POLYGON']:
                if node_id not in group_member_ids:
                    individual_vectors.append({
                        'id': node_id,
                        'name': node_name,
                        'type': node_type,
                        'path': current_path,
                        'bounds': node.get('absoluteBoundingBox', {})
                    })
            
            # Continue traversal (skip groups to avoid duplicates)
            if node_type != 'GROUP':
                for child in node.get('children', []):
                    find_standalone_vectors(child, current_path)
        
        # Start traversal from document root
        document = file_data.get('document', {})
        
        # First pass: collect group members
        for page in document.get('children', []):
            collect_group_members(page)
        
        # Second pass: find standalone vectors
        for page in document.get('children', []):
            find_standalone_vectors(page)
        
        self.stats['individual_vectors_found'] = len(individual_vectors)
        logger.info(f"✅ Found {len(individual_vectors)} individual vectors")
        
        return individual_vectors
    
    def download_individual_svgs(self, file_key: str, individual_vectors: List[Dict], output_dir: Path) -> Dict[str, Dict]:
        """Download individual vector SVG files"""
        
        if not individual_vectors:
            logger.info("No individual vectors to download")
            return {}
        
        logger.info(f"🎨 Downloading {len(individual_vectors)} individual SVGs...")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_vectors = {}
        
        # Get export URLs for all vectors at once
        vector_ids = [vector['id'] for vector in individual_vectors]
        export_urls = self._get_svg_export_urls(file_key, vector_ids)
        
        if not export_urls:
            logger.error("❌ Failed to get export URLs for individual vectors")
            return {}
        
        # Download each vector SVG
        for i, vector in enumerate(individual_vectors, 1):
            vector_id = vector['id']
            
            if vector_id not in export_urls:
                logger.warning(f"⚠️  No export URL for vector: {vector['name']}")
                continue
            
            # Create safe filename
            safe_name = self._sanitize_filename(vector['name'])
            filename = f"{vector_id.replace(':', '_')}_{safe_name}.svg"
            file_path = output_dir / filename
            
            # Download SVG
            export_url = export_urls[vector_id]
            if self._download_file(export_url, file_path):
                downloaded_vectors[vector_id] = {
                    'local_path': str(file_path),
                    'filename': filename,
                    'component_name': vector['name'],
                    'path': vector['path'],
                    'file_size': file_path.stat().st_size if file_path.exists() else 0,
                    'node_id': vector_id,
                    'type': vector['type'],
                    'bounds': vector['bounds']
                }
                
                logger.info(f"✅ [{i}/{len(individual_vectors)}] Downloaded vector: {vector['name']}")
                self.stats['downloads'] += 1
            else:
                logger.error(f"❌ [{i}/{len(individual_vectors)}] Failed to download vector: {vector['name']}")
                self.stats['errors'] += 1
            
            # Brief pause between downloads
            time.sleep(0.1)
        
        logger.info(f"🎨 Individual SVG download completed: {len(downloaded_vectors)} successful")
        return downloaded_vectors
    
    # =========================================================================
    # DIRECT IMAGE NODE EXTRACTION
    # =========================================================================
    
    def find_direct_image_nodes(self, file_data: Dict) -> List[Dict]:
        """Find IMAGE nodes directly placed in design"""
        
        logger.info("🔍 Finding direct image nodes...")
        
        image_nodes = []
        
        def traverse_node(node: Dict, path: str = ""):
            node_type = node.get('type', '')
            node_id = node.get('id', '')
            node_name = node.get('name', 'Unnamed')
            current_path = f"{path}/{node_name}" if path else node_name
            
            if node_type == 'IMAGE':
                image_nodes.append({
                    'id': node_id,
                    'name': node_name,
                    'path': current_path,
                    'bounds': node.get('absoluteBoundingBox', {}),
                    'image_ref': node.get('imageRef', ''),
                    'image_transform': node.get('imageTransform', [])
                })
            
            # Continue traversal
            for child in node.get('children', []):
                traverse_node(child, current_path)
        
        # Start traversal from document root
        document = file_data.get('document', {})
        for page in document.get('children', []):
            traverse_node(page)
        
        self.stats['direct_images_found'] = len(image_nodes)
        logger.info(f"✅ Found {len(image_nodes)} direct image nodes")
        
        return image_nodes
    
    def download_direct_images(self, file_key: str, image_nodes: List[Dict], output_dir: Path) -> Dict[str, Dict]:
        """Download direct image nodes"""
        
        if not image_nodes:
            logger.info("No direct image nodes to download")
            return {}
        
        logger.info(f"🖼️  Downloading {len(image_nodes)} direct images...")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_images = {}
        
        # Get export URLs for all image nodes at once
        image_ids = [img['id'] for img in image_nodes]
        export_urls = self._get_image_export_urls(file_key, image_ids)
        
        if not export_urls:
            logger.error("❌ Failed to get export URLs for direct images")
            return {}
        
        # Download each image
        for i, image_node in enumerate(image_nodes, 1):
            image_id = image_node['id']
            
            if image_id not in export_urls:
                logger.warning(f"⚠️  No export URL for image: {image_node['name']}")
                continue
            
            # Determine file extension from URL
            export_url = export_urls[image_id]
            file_extension = self._get_file_extension_from_url(export_url)
            
            # Create safe filename
            safe_name = self._sanitize_filename(image_node['name'])
            filename = f"{image_id.replace(':', '_')}_{safe_name}{file_extension}"
            file_path = output_dir / filename
            
            # Download image
            if self._download_file(export_url, file_path):
                downloaded_images[image_id] = {
                    'local_path': str(file_path),
                    'filename': filename,
                    'image_name': image_node['name'],
                    'path': image_node['path'],
                    'file_size': file_path.stat().st_size if file_path.exists() else 0,
                    'node_id': image_id,
                    'type': 'DIRECT_IMAGE',
                    'bounds': image_node['bounds'],
                    'image_ref': image_node['image_ref']
                }
                
                logger.info(f"✅ [{i}/{len(image_nodes)}] Downloaded image: {image_node['name']}")
                self.stats['downloads'] += 1
            else:
                logger.error(f"❌ [{i}/{len(image_nodes)}] Failed to download image: {image_node['name']}")
                self.stats['errors'] += 1
            
            # Brief pause between downloads
            time.sleep(0.1)
        
        logger.info(f"🖼️  Direct image download completed: {len(downloaded_images)} successful")
        return downloaded_images
    
    # =========================================================================
    # FILL/BACKGROUND IMAGE EXTRACTION
    # =========================================================================
    
    def download_images_from_file(self, file_key: str, file_data: Dict, output_dir: Path) -> Dict[str, Dict]:
        """Download fill/background images from file"""
        
        logger.info("🌈 Finding and downloading fill/background images...")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all image references
        image_refs = self._extract_image_references(file_data)
        
        if not image_refs:
            logger.info("No fill/background images found")
            return {}
        
        self.stats['fill_images_found'] = len(image_refs)
        logger.info(f"✅ Found {len(image_refs)} fill/background image references")
        
        # Get image URLs from Figma
        image_urls = self._get_image_urls(file_key, list(image_refs))
        
        if not image_urls:
            logger.error("❌ Failed to get image URLs")
            return {}
        
        downloaded_images = {}
        
        # Download each image
        for i, image_ref in enumerate(image_refs, 1):
            if image_ref not in image_urls:
                logger.warning(f"⚠️  No URL found for image reference: {image_ref}")
                continue
            
            # Get file extension from URL
            image_url = image_urls[image_ref]
            file_extension = self._get_file_extension_from_url(image_url)
            
            # Create filename
            filename = f"{image_ref}{file_extension}"
            file_path = output_dir / filename
            
            # Download image
            if self._download_file(image_url, file_path):
                downloaded_images[image_ref] = {
                    'local_path': str(file_path),
                    'filename': filename,
                    'image_ref': image_ref,
                    'file_size': file_path.stat().st_size if file_path.exists() else 0,
                    'type': 'FILL_IMAGE'
                }
                
                logger.info(f"✅ [{i}/{len(image_refs)}] Downloaded fill image: {filename}")
                self.stats['downloads'] += 1
            else:
                logger.error(f"❌ [{i}/{len(image_refs)}] Failed to download: {filename}")
                self.stats['errors'] += 1
            
            # Brief pause between downloads
            time.sleep(0.1)
        
        logger.info(f"🌈 Fill image download completed: {len(downloaded_images)} successful")
        return downloaded_images
    
    def _extract_image_references(self, file_data: Dict) -> set:
        """Extract all image references from file data"""
        
        image_refs = set()
        
        def traverse_node(node: Dict):
            # Check fills
            if 'fills' in node:
                for fill in node['fills']:
                    if isinstance(fill, dict) and fill.get('type') == 'IMAGE':
                        image_ref = fill.get('imageRef')
                        if image_ref:
                            image_refs.add(image_ref)
            
            # Check backgrounds
            if 'backgrounds' in node:
                for bg in node['backgrounds']:
                    if isinstance(bg, dict) and bg.get('type') == 'IMAGE':
                        image_ref = bg.get('imageRef')
                        if image_ref:
                            image_refs.add(image_ref)
            
            # Check background property
            if 'background' in node and isinstance(node['background'], list):
                for bg in node['background']:
                    if isinstance(bg, dict) and bg.get('type') == 'IMAGE':
                        image_ref = bg.get('imageRef')
                        if image_ref:
                            image_refs.add(image_ref)
            
            # Recursively process children
            for child in node.get('children', []):
                traverse_node(child)
        
        # Start from document root
        document = file_data.get('document', {})
        traverse_node(document)
        
        return image_refs
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _get_svg_export_urls(self, file_key: str, node_ids: List[str]) -> Dict[str, str]:
        """Get SVG export URLs for multiple nodes"""
        
        if not node_ids:
            return {}
        
        params = {
            'ids': ','.join(node_ids),
            'format': 'svg'
        }
        
        result = self._make_request(f"images/{file_key}", params)
        
        if result and 'images' in result:
            return result['images']
        else:
            logger.error("Failed to get SVG export URLs")
            return {}
    
    def _get_image_export_urls(self, file_key: str, node_ids: List[str]) -> Dict[str, str]:
        """Get image export URLs for multiple nodes"""
        
        if not node_ids:
            return {}
        
        params = {
            'ids': ','.join(node_ids),
            'format': 'png',
            'scale': '2'
        }
        
        result = self._make_request(f"images/{file_key}", params)
        
        if result and 'images' in result:
            return result['images']
        else:
            logger.error("Failed to get image export URLs")
            return {}
    
    def _get_image_urls(self, file_key: str, image_refs: List[str]) -> Dict[str, str]:
        """Get image URLs for image references"""
        
        if not image_refs:
            return {}
        
        # For fill images, we need to use the file's images endpoint
        result = self._make_request(f"files/{file_key}/images")
        
        if result and 'meta' in result and 'images' in result['meta']:
            return result['meta']['images']
        else:
            logger.error("Failed to get fill image URLs")
            return {}
    
    def _download_file(self, url: str, file_path: Path) -> bool:
        """Download file from URL to local path"""
        
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
            
        except Exception as e:
            logger.error(f"Download failed for {file_path.name}: {e}")
            return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing invalid characters"""
        
        # Remove invalid characters
        invalid_chars = r'[<>:"/\\|?*&]'
        sanitized = re.sub(invalid_chars, '_', filename)
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = "unnamed"
        
        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        return sanitized
    
    def _get_file_extension_from_url(self, url: str) -> str:
        """Get file extension from URL"""
        
        try:
            # Try to determine from URL
            if '.png' in url.lower():
                return '.png'
            elif '.jpg' in url.lower() or '.jpeg' in url.lower():
                return '.jpg'
            elif '.gif' in url.lower():
                return '.gif'
            elif '.webp' in url.lower():
                return '.webp'
            elif '.svg' in url.lower():
                return '.svg'
            else:
                return '.png'  # Default to PNG
        except:
            return '.png'
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        
        return {
            'api_calls': self.stats['api_calls'],
            'total_downloads': self.stats['downloads'],
            'total_errors': self.stats['errors'],
            'groups_found': self.stats['groups_found'],
            'individual_vectors_found': self.stats['individual_vectors_found'],
            'direct_images_found': self.stats['direct_images_found'],
            'fill_images_found': self.stats['fill_images_found'],
            'success_rate': round((self.stats['downloads'] / max(self.stats['downloads'] + self.stats['errors'], 1)) * 100, 2)
        }
    
    def print_extraction_summary(self):
        """Print extraction summary"""
        
        stats = self.get_extraction_stats()
        
        print("\n" + "="*50)
        print("🎯 ENHANCED EXTRACTION SUMMARY")
        print("="*50)
        print(f"📡 API Calls: {stats['api_calls']}")
        print(f"📥 Total Downloads: {stats['total_downloads']}")
        print(f"❌ Errors: {stats['total_errors']}")
        print(f"📈 Success Rate: {stats['success_rate']}%")
        print()
        print("🎨 Assets Found:")
        print(f"   📦 Vector Groups: {stats['groups_found']}")
        print(f"   🎨 Individual Vectors: {stats['individual_vectors_found']}")
        print(f"   🖼️  Direct Images: {stats['direct_images_found']}")
        print(f"   🌈 Fill/Background Images: {stats['fill_images_found']}")
        print("="*50)