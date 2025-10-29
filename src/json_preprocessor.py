import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class JSONPreprocessor:
    """
    FIXED JSON preprocessing with child-based extraction approach
    Filters GROUP contents but extracts individual vector children as separate SVG files
    """
    
    def __init__(self):
        self.stats = {
            'total_nodes_scanned': 0,
            'groups_analyzed': 0,
            'vector_children_found': 0,
            'individual_vectors_found': 0,
            'text_nodes_filtered': 0,
            'image_shapes_filtered': 0,
            'empty_groups_skipped': 0,
            'total_vector_exports': 0
        }
        
        # Store analysis results - FIXED: Individual vector children, not groups
        self.individual_vector_children = {}  # Each vector child gets its own SVG
        self.standalone_vectors = {}          # Standalone vectors not in groups
    
    def preprocess_figma_json(self, raw_figma_data: Dict, output_path: Optional[Path] = None) -> Dict:
        """
        FIXED: Main preprocessing function with child-based extraction approach
        """
        logger.info("🔧 Starting FIXED JSON preprocessing with child-based extraction...")
        
        # Reset stats
        self._reset_stats()
        
        # Step 1: Content-first group analysis with child-based extraction
        logger.info("🔍 Step 1: Content-first analysis with child-based extraction...")
        self._analyze_groups_for_individual_children(raw_figma_data)
        
        # Step 2: Generate optimized JSON structure for child-based extraction
        logger.info("⚡ Step 2: Generating child-based optimized JSON structure...")
        optimized_data = self._generate_child_based_json(raw_figma_data)
        
        # Step 3: Add preprocessing metadata
        self._add_preprocessing_metadata(optimized_data)
        
        # Step 4: Save optimized JSON if path provided
        if output_path:
            self._save_optimized_json(optimized_data, output_path)
        
        # Print preprocessing summary
        self._print_preprocessing_summary()
        
        logger.info("✅ FIXED child-based JSON preprocessing completed successfully")
        return optimized_data
    
    def _reset_stats(self):
        """Reset processing statistics"""
        for key in self.stats:
            self.stats[key] = 0
        self.individual_vector_children.clear()
        self.standalone_vectors.clear()
    
    def _analyze_groups_for_individual_children(self, figma_data: Dict):
        """
        FIXED: Content-first analysis that extracts individual vector children
        Each vector child becomes its own SVG file instead of being combined into groups
        """
        
        def analyze_node(node: Dict, path: str = "", parent_group: Optional[Dict] = None):
            self.stats['total_nodes_scanned'] += 1
            
            node_type = node.get('type', '')
            node_id = node.get('id', '')
            node_name = node.get('name', 'Unnamed')
            current_path = f"{path}/{node_name}" if path else node_name
            
            # FIXED: When we find a GROUP, extract each vector child individually
            if node_type == 'GROUP':
                self.stats['groups_analyzed'] += 1
                group_analysis = self._analyze_group_content(node, current_path)
                
                if group_analysis['vector_children']:
                    logger.debug(f"📦 Found GROUP: {node_name} with {len(group_analysis['vector_children'])} vector children")
                    
                    # FIXED: Store each vector child individually for separate SVG export
                    for vector_child in group_analysis['vector_children']:
                        child_id = vector_child['id']
                        child_name = vector_child['name']
                        
                        self.individual_vector_children[child_id] = {
                            'id': child_id,
                            'name': child_name,
                            'type': vector_child['type'],
                            'path': f"{current_path}/{child_name}",
                            'bounds': vector_child.get('bounds', {}),
                            'parent_group_id': node_id,
                            'parent_group_name': node_name,
                            'extraction_reason': 'VECTOR_CHILD_FROM_GROUP'
                        }
                        
                        self.stats['vector_children_found'] += 1
                        logger.debug(f"   ✅ Individual vector child: {child_name} (ID: {child_id})")
                else:
                    self.stats['empty_groups_skipped'] += 1
                    logger.debug(f"   ⭕ Skipped group with no vectors: {node_name}")
                
                # Don't traverse children of analyzed groups to avoid duplicates
                return
            
            # Check for standalone vectors (not in groups)
            elif self._is_pure_vector(node) and parent_group is None:
                self.standalone_vectors[node_id] = {
                    'id': node_id,
                    'name': node_name,
                    'type': node_type,
                    'path': current_path,
                    'bounds': node.get('absoluteBoundingBox', {}),
                    'extraction_reason': 'STANDALONE_VECTOR'
                }
                self.stats['individual_vectors_found'] += 1
                logger.debug(f"   🎨 Standalone vector: {node_name}")
            
            # Recursively process children (except for GROUP containers already analyzed)
            if node_type != 'GROUP' and 'children' in node:
                current_group = parent_group
                if node_type in ['FRAME', 'COMPONENT', 'INSTANCE']:
                    current_group = {'id': node_id, 'name': node_name}
                
                for child in node['children']:
                    analyze_node(child, current_path, current_group)
        
        # Start traversal from document root
        if 'document' in figma_data:
            for page in figma_data['document'].get('children', []):
                logger.info(f"📄 Analyzing page: {page.get('name', 'Unnamed')}")
                analyze_node(page)
        
        # Calculate total exports
        self.stats['total_vector_exports'] = len(self.individual_vector_children) + len(self.standalone_vectors)
        
        logger.info(f"🔍 Child-based analysis complete:")
        logger.info(f"   • Groups analyzed: {self.stats['groups_analyzed']}")
        logger.info(f"   • Vector children found: {self.stats['vector_children_found']}")
        logger.info(f"   • Standalone vectors: {self.stats['individual_vectors_found']}")
        logger.info(f"   • Total individual SVG exports: {self.stats['total_vector_exports']}")
        logger.info(f"   • Empty groups skipped: {self.stats['empty_groups_skipped']}")
    
    def _analyze_group_content(self, group_node: Dict, path: str) -> Dict:
        """
        FIXED: Analyze GROUP content and return individual vector children
        """
        vector_children = []
        non_vector_children = []
        
        def examine_child(child: Dict, depth: int = 0):
            if depth > 5:  # Prevent deep recursion in complex groups
                return
            
            child_type = child.get('type', '')
            child_id = child.get('id', '')
            child_name = child.get('name', 'Vector')
            
            # EXACT FILTERING RULES FROM MASTER_PROMPT:
            
            # ✅ INCLUDE in SVG Export:
            if child_type == 'VECTOR' and self._has_solid_fills(child) and not child.get('isMask', False):
                vector_children.append({
                    'id': child_id,
                    'name': child_name,
                    'type': child_type,
                    'bounds': child.get('absoluteBoundingBox', {})
                })
                logger.debug(f"      ✅ Including VECTOR: {child_name}")
            
            # ❌ EXCLUDE from SVG Export:
            elif child_type == 'TEXT':
                self.stats['text_nodes_filtered'] += 1
                non_vector_children.append('TEXT')
                logger.debug(f"      ❌ Excluding TEXT: {child_name}")
            
            elif child_type in ['RECTANGLE', 'ELLIPSE']:
                self.stats['image_shapes_filtered'] += 1
                non_vector_children.append('SHAPE')
                logger.debug(f"      ❌ Excluding shape {child_type}: {child_name}")
            
            elif child.get('isMask', False):
                self.stats['image_shapes_filtered'] += 1
                non_vector_children.append('MASK')
                logger.debug(f"      ❌ Excluding mask element: {child_name}")
            
            else:
                # Other elements that don't match criteria
                non_vector_children.append(child_type)
                logger.debug(f"      ⚠️ Other element excluded: {child_type} - {child_name}")
            
            # Recursively examine children
            for grandchild in child.get('children', []):
                examine_child(grandchild, depth + 1)
        
        # Examine all children of the group
        for child in group_node.get('children', []):
            examine_child(child)
        
        return {
            'vector_children': vector_children,
            'filtered_content': ', '.join(set(non_vector_children)) if non_vector_children else 'none',
            'vector_count': len(vector_children)
        }
    
    def _is_pure_vector(self, node: Dict) -> bool:
        """
        FIXED: Exact filtering criteria from MASTER_PROMPT
        """
        node_type = node.get('type', '')
        
        # Only VECTOR types (not RECTANGLE, ELLIPSE, etc.)
        if node_type != 'VECTOR':
            return False
        
        # Must have solid fills (not image fills)
        if not self._has_solid_fills(node):
            return False
        
        # Must not be a mask
        if node.get('isMask', False):
            return False
        
        return True
    
    def _has_solid_fills(self, node: Dict) -> bool:
        """Check if node has solid fills (not image fills)"""
        fills = node.get('fills', [])
        
        for fill in fills:
            if isinstance(fill, dict) and fill.get('type') == 'SOLID':
                return True
        
        return False
    
    def _generate_child_based_json(self, original_data: Dict) -> Dict:
        """
        FIXED: Generate optimized JSON with child-based individual extraction
        """
        # Create a copy of the original data
        optimized_data = json.loads(json.dumps(original_data))
        
        # Create child-based _svgDownloads section
        child_based_svg_downloads = {}
        
        # FIXED: Add individual vector children (each gets its own SVG file)
        for child_id, child_data in self.individual_vector_children.items():
            child_based_svg_downloads[child_id] = {
                'node_id': child_id,
                'type': 'VECTOR',
                'is_group': False,
                'component_name': child_data['name'],
                'path': child_data['path'],
                'filename': self._generate_filename(child_id),
                'extraction_reason': child_data['extraction_reason'],
                'parent_group_id': child_data.get('parent_group_id'),
                'parent_group_name': child_data.get('parent_group_name'),
                'bounds': child_data.get('bounds', {})
            }
        
        # Add standalone vectors
        for vector_id, vector_data in self.standalone_vectors.items():
            child_based_svg_downloads[vector_id] = {
                'node_id': vector_id,
                'type': 'VECTOR',
                'is_group': False,
                'component_name': vector_data['name'],
                'path': vector_data['path'],
                'filename': self._generate_filename(vector_id),
                'extraction_reason': vector_data['extraction_reason'],
                'bounds': vector_data.get('bounds', {})
            }
        
        # Replace the _svgDownloads section with child-based structure
        optimized_data['_svgDownloads'] = child_based_svg_downloads
        
        # Create _svgMapping for URLReplacer compatibility
        svg_mapping = {}
        for node_id, svg_info in child_based_svg_downloads.items():
            safe_node_id = node_id.replace(':', '_')
            svg_mapping[safe_node_id] = {
                'filename': svg_info['filename'],
                'is_group': False,  # All are individual now
                'component_name': svg_info['component_name']
            }
        
        optimized_data['_svgMapping'] = svg_mapping
        
        logger.info(f"⚡ Generated child-based structure:")
        logger.info(f"   • Total individual SVG exports: {len(child_based_svg_downloads)}")
        logger.info(f"   • Vector children from groups: {len(self.individual_vector_children)}")
        logger.info(f"   • Standalone vectors: {len(self.standalone_vectors)}")
        
        return optimized_data
    
    def _generate_filename(self, node_id: str) -> str:
        """Generate filename compatible with URLReplacer expectations"""
        return f"{node_id.replace(':', '_')}.svg"
    
    def _add_preprocessing_metadata(self, optimized_data: Dict):
        """Add preprocessing metadata to the optimized JSON"""
        if '_metadata' not in optimized_data:
            optimized_data['_metadata'] = {}
        
        optimized_data['_metadata']['preprocessing'] = {
            'processed_at': datetime.now().isoformat(),
            'preprocessing_version': '3.0_child_based_extraction_fixed',
            'approach': 'child_based_individual_extraction',
            'statistics': self.stats.copy(),
            'filtering_criteria': {
                'vector_types_included': ['VECTOR'],
                'content_excluded': ['TEXT', 'SHAPES', 'MASKS'],
                'fill_types_required': ['SOLID'],
                'extraction_strategy': 'individual_vector_children'
            }
        }
        
        # Mark as preprocessing applied
        optimized_data['_metadata']['preprocessing_applied'] = True
    
    def _save_optimized_json(self, optimized_data: Dict, output_path: Path):
        """Save the optimized JSON to file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(optimized_data, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Child-based optimized JSON saved to: {output_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save optimized JSON: {e}")
            raise
    
    def _print_preprocessing_summary(self):
        """Print a summary of the preprocessing results"""
        logger.info("\n" + "="*70)
        logger.info("🎯 FIXED CHILD-BASED PREPROCESSING SUMMARY")
        logger.info("="*70)
        logger.info(f"📊 Total Nodes Scanned: {self.stats['total_nodes_scanned']}")
        logger.info(f"🔍 Groups Analyzed: {self.stats['groups_analyzed']}")
        logger.info(f"🎨 Vector Children Found: {self.stats['vector_children_found']}")
        logger.info(f"🎨 Standalone Vectors: {self.stats['individual_vectors_found']}")
        logger.info(f"📄 Total Individual SVG Exports: {self.stats['total_vector_exports']}")
        logger.info(f"🚫 TEXT Nodes Filtered: {self.stats['text_nodes_filtered']}")
        logger.info(f"🚫 Shape/Mask Elements Filtered: {self.stats['image_shapes_filtered']}")
        logger.info(f"⭕ Empty Groups Skipped: {self.stats['empty_groups_skipped']}")
        logger.info("")
        logger.info("🔧 EXTRACTION APPROACH: Child-Based Individual Vector Extraction")
        logger.info("📋 KEY IMPROVEMENTS:")
        logger.info("   • No more multi-icon strips (each vector child = separate SVG)")
        logger.info("   • Individual file naming (262_48.svg not 12_171.svg)")
        logger.info("   • Clean vector-only filtering (no TEXT/SHAPE content)")
        logger.info("   • URLReplacer compatible (child ID mappings)")
        logger.info("   • No composition/splitting logic needed")
        logger.info("="*70)
    
    def get_preprocessing_stats(self) -> Dict:
        """Get preprocessing statistics"""
        return self.stats.copy()
    
    def get_filtered_structure_info(self) -> Dict:
        """FIXED: Method that returns child-based structure info"""
        return {
            'total_svg_exports': len(self.individual_vector_children) + len(self.standalone_vectors),
            'vector_children_from_groups': len(self.individual_vector_children),
            'standalone_vectors': len(self.standalone_vectors),
            'vector_children_details': [
                {
                    'id': child_id,
                    'name': info['name'],
                    'filename': self._generate_filename(child_id),
                    'parent_group': info.get('parent_group_name', 'None'),
                    'extraction_reason': info['extraction_reason']
                }
                for child_id, info in self.individual_vector_children.items()
            ],
            'standalone_details': [
                {
                    'id': vector_id,
                    'name': info['name'],
                    'filename': self._generate_filename(vector_id),
                    'extraction_reason': info['extraction_reason']
                }
                for vector_id, info in self.standalone_vectors.items()
            ]
        }
    
    # ALIAS for backward compatibility
    def get_optimized_structure_info(self) -> Dict:
        """Alias for get_filtered_structure_info for backward compatibility"""
        return self.get_filtered_structure_info()