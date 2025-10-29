import os
import sys
import argparse
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

from src.config import Config
from src.figma_extractor import FigmaExtractor
from src.digitalocean_uploader import DigitalOceanUploader
from src.json_processor import JSONProcessor
from src.URLReplacer import URLReplacer
from src.json_preprocessor import JSONPreprocessor
from src.utils import setup_logging, sanitize_filename

def get_user_input():
    """
    Collect required information from the user.
    """
    print("=== 🚀 FIXED Figma to DigitalOcean Spaces Extractor (Child-Based) ===\n")
    
    # Get document name
    document_name = input("Enter the document name (for the output file): ").strip()
    if not document_name:
        document_name = "figma_export"
    
    # Sanitize document name
    document_name = sanitize_filename(document_name)
    
    # Get file key
    print("\nTo find your file key:")
    print("1. Open your Figma file in browser")
    print("2. Copy the URL: https://www.figma.com/file/FILE_KEY/...")
    print("3. The FILE_KEY is the string after '/file/' and before the next '/'")
    print("Example: In 'https://www.figma.com/file/abc123def456/My-Design'")
    print("         The file key is 'abc123def456'\n")
    
    file_key = input("Enter the Figma file key: ").strip()
    if not file_key:
        print("Error: File key is required!")
        return None, None, None, None, None, None
    
    # Ask about extraction mode
    print("\n=== Extraction Mode ===")
    print("1. Extract entire file (all pages and frames)")
    print("2. Extract specific pages/frames only")
    
    mode_choice = input("Choose extraction mode (1 or 2): ").strip()
    extraction_mode = "full" if mode_choice == "1" else "selective"
    
    # Ask about bitmap images
    download_images = input("\nDownload bitmap images from fills/backgrounds? (Y/n): ").strip().lower()
    download_images = download_images != 'n'
    
    # Ask about SVG icons with FIXED child-based extraction
    print("\n=== 🔧 FIXED SVG Icon Extraction (Child-Based Individual Vectors) ===")
    print("Extract SVG icons/vectors with CHILD-BASED approach:")
    print("• Individual Vector Files: Each vector child becomes its own SVG file")
    print("• No Composition: No more multi-icon strips (262_48.svg not 12_171.svg)")
    print("• Content Filtering: Only pure VECTOR content (no TEXT/shape contamination)")
    print("• Clean Naming: Child-based filenames (262_48.svg, 262_49.svg, etc.)")
    print("• URLReplacer Ready: Compatible with existing URL replacement system")
    extract_svg_icons = input("Extract SVG icons with FIXED child-based approach? (Y/n): ").strip().lower()
    extract_svg_icons = extract_svg_icons != 'n'
    
    # SVG extraction options
    svg_include_all = True
    if extract_svg_icons:
        print("\nFIXED SVG Extraction Options:")
        print("1. Extract all exportable elements (comprehensive child-based)")
        print("2. Extract only components and keyword-matching elements (selective)")
        svg_choice = input("Choose FIXED SVG extraction mode (1 or 2): ").strip()
        svg_include_all = svg_choice != "2"
    
    return document_name, file_key, download_images, extract_svg_icons, extraction_mode, svg_include_all

def main():
    """FIXED: Main orchestration function with child-based extraction integration"""
    
    # Load environment variables
    env_loaded = False
    
    if os.path.exists('.env'):
        load_dotenv('.env')
        env_loaded = True
    elif os.path.exists('.env.'):
        load_dotenv('.env.')
        env_loaded = True
    else:
        print("⚠️ Warning: No .env file found. Make sure to set environment variables.")
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    if env_loaded:
        logger.info("Environment variables loaded successfully")
    else:
        logger.warning("No environment file found - using system environment variables")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='FIXED Figma extractor with child-based individual vector extraction')
    parser.add_argument('--file-key', help='Figma file key (will prompt if not provided)')
    parser.add_argument('--document-name', help='Document name for output files (will prompt if not provided)')
    parser.add_argument('--remote-folder', default='figma-assets', help='Remote folder in DO Spaces')
    parser.add_argument('--output-dir', default='./output', help='Local output directory')
    parser.add_argument('--skip-upload', action='store_true', help='Skip upload to DigitalOcean')
    parser.add_argument('--cleanup', action='store_true', help='Clean up local files after upload')
    parser.add_argument('--selective', action='store_true', help='Force selective extraction mode')
    parser.add_argument('--no-interactive', action='store_true', help='Skip interactive prompts (requires --file-key)')
    parser.add_argument('--no-bitmap', action='store_true', help='Skip bitmap image download')
    parser.add_argument('--no-svg', action='store_true', help='Skip SVG icon extraction')
    parser.add_argument('--svg-selective', action='store_true', help='Use selective SVG extraction mode')
    
    args = parser.parse_args()
    
    # Get user input if not provided via command line
    if args.no_interactive:
        if not args.file_key:
            logger.error("--file-key is required when using --no-interactive mode")
            return 1
        
        document_name = args.document_name or f"figma_export_{args.file_key[:8]}"
        file_key = args.file_key
        download_images = not args.no_bitmap
        extract_svg_icons = not args.no_svg
        extraction_mode = "selective" if args.selective else "full"
        svg_include_all = not args.svg_selective
    else:
        # Interactive mode - get user input
        result = get_user_input()
        
        if not result[1]:  # file_key is None
            logger.error("File key is required. Exiting.")
            return 1
        
        document_name, file_key, download_images, extract_svg_icons, extraction_mode, svg_include_all = result
        
        # Override with command line arguments if provided
        if args.selective:
            extraction_mode = "selective"
        if args.document_name:
            document_name = args.document_name
        if args.no_bitmap:
            download_images = False
        if args.no_svg:
            extract_svg_icons = False
        if args.svg_selective:
            svg_include_all = False
    
    try:
        # Initialize configuration
        config = Config()
        
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed. Check your environment variables.")
            return 1
        
        # Initialize FIXED services
        figma = FigmaExtractor(config.figma_token)
        do_uploader = DigitalOceanUploader(
            config.do_access_key,
            config.do_secret_key,
            config.do_region,
            config.do_space_name
        )
        
        # Validate connections
        logger.info("🔍 Validating API connections...")
        if not figma.validate_token():
            logger.error("Invalid Figma API token")
            return 1
        
        # Set document name
        document_name = sanitize_filename(document_name)
        
        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🚀 Starting FIXED child-based extraction for file: {file_key}")
        logger.info(f"📄 Document name: {document_name}")
        logger.info(f"📁 Output directory: {output_dir}")
        logger.info(f"☁️ Remote folder: {args.remote_folder}")
        logger.info(f"🎯 Extraction mode: {extraction_mode}")
        logger.info(f"🖼️ Download bitmap images: {download_images}")
        logger.info(f"🎨 Extract SVG icons (CHILD-BASED): {extract_svg_icons}")
        if extract_svg_icons:
            logger.info(f"🔧 SVG extraction mode: {'comprehensive (child-based)' if svg_include_all else 'selective (child-based)'}")
        
        # Extract data from Figma
        if extraction_mode == "selective":
            selected_nodes = select_pages_and_frames(figma, file_key)
            if not selected_nodes:
                logger.error("No nodes selected for extraction")
                return 1
            file_data = figma.extract_specific_nodes(file_key, selected_nodes)
        else:
            file_data = figma.get_file_data(file_key, include_images=True)
        
        if not file_data:
            logger.error("Failed to extract file data from Figma")
            return 1

        # ============================================================================
        # FIXED: CHILD-BASED JSON PREPROCESSING LAYER
        # ============================================================================
        if extract_svg_icons:
            logger.info("🔧 Starting FIXED JSON preprocessing with child-based extraction...")
            
            # Initialize FIXED JSON preprocessor
            json_preprocessor = JSONPreprocessor()
            
            # Generate optimized JSON path
            optimized_json_filename = f"{document_name}_optimized.json"
            optimized_json_path = output_dir / optimized_json_filename
            
            # FIXED: Preprocess the JSON with child-based extraction
            file_data = json_preprocessor.preprocess_figma_json(
                raw_figma_data=file_data,
                output_path=optimized_json_path
            )
            
            # FIXED: Get preprocessing statistics using correct method name
            preprocessing_stats = json_preprocessor.get_preprocessing_stats()
            structure_info = json_preprocessor.get_filtered_structure_info()  # FIXED: Correct method name
            
            logger.info(f"✅ FIXED child-based JSON preprocessing completed:")
            logger.info(f"   🔍 Groups analyzed: {preprocessing_stats['groups_analyzed']}")
            logger.info(f"   🎨 Vector children found: {preprocessing_stats['vector_children_found']}")
            logger.info(f"   🎨 Standalone vectors: {preprocessing_stats['individual_vectors_found']}")
            logger.info(f"   📄 Total individual SVG exports: {preprocessing_stats['total_vector_exports']}")
            logger.info(f"   🚫 TEXT nodes filtered: {preprocessing_stats['text_nodes_filtered']}")
            logger.info(f"   🚫 Shape/mask elements filtered: {preprocessing_stats['image_shapes_filtered']}")
            logger.info(f"   💾 Optimized JSON saved: {optimized_json_path}")
            
            # FIXED: Show child-based extraction results
            logger.info(f"🔧 Child-Based Extraction Results:")
            logger.info(f"   • Total individual SVG exports: {structure_info['total_svg_exports']}")
            logger.info(f"   • Vector children from groups: {structure_info['vector_children_from_groups']}")
            logger.info(f"   • Standalone vectors: {structure_info['standalone_vectors']}")
            
            # Show sample individual vectors with parent info
            if structure_info['vector_children_details']:
                logger.info(f"🎨 Sample Individual Vector Children:")
                for child in structure_info['vector_children_details'][:3]:  # Show first 3
                    parent_info = f" (from {child['parent_group']})" if child['parent_group'] != 'None' else ""
                    logger.info(f"   • {child['id']} → {child['filename']}{parent_info}")
            
            # Update file_data metadata to reflect FIXED preprocessing
            if '_metadata' not in file_data:
                file_data['_metadata'] = {}
            file_data['_metadata']['preprocessing_applied'] = True
            file_data['_metadata']['child_based_extraction'] = True
            
        else:
            logger.info("⭕ Skipping JSON preprocessing (SVG extraction disabled)")
        # ============================================================================
        # END: FIXED CHILD-BASED PREPROCESSING LAYER
        # ============================================================================

        # Download bitmap images from Figma
        downloaded_images = {}
        if download_images:
            logger.info("🖼️ Starting bitmap image download...")
            images_dir = output_dir / "images"
            downloaded_images = figma.download_images_from_file(file_key, file_data, images_dir)
            
            if not downloaded_images:
                logger.warning("No bitmap images were downloaded from Figma")
            else:
                logger.info(f"✅ Downloaded {len(downloaded_images)} bitmap images")
        else:
            logger.info("⭕ Skipping bitmap image download as requested")
        
        # ============================================================================
        # FIXED: CHILD-BASED INDIVIDUAL SVG EXTRACTION
        # ============================================================================
        downloaded_svgs = {}
        if extract_svg_icons:
            logger.info("🔧 Starting FIXED child-based individual SVG extraction...")
            # NOTE: Now using the FIXED preprocessed file_data with child-based structure
            downloaded_svgs = figma.download_svg_icons(
                file_key=file_key,
                file_data=file_data,  # Contains FIXED preprocessed structure with child-based extraction
                output_dir=output_dir,
                include_all_exportable=svg_include_all
            )
            
            if downloaded_svgs:
                # All are individual vectors now (no groups)
                total_individual_vectors = len(downloaded_svgs)
                
                logger.info(f"✅ Downloaded {total_individual_vectors} FIXED individual SVG files:")
                logger.info(f"   🎨 Individual Vector Files: {total_individual_vectors}")
                logger.info(f"   ✅ No multi-icon strips created")
                logger.info(f"   ✅ Clean child-based naming (e.g., 262_48.svg)")
                logger.info(f"   ✅ URLReplacer compatible filenames")
                
                # Show sample individual vectors with parent context
                sample_vectors = list(downloaded_svgs.values())[:5]
                if sample_vectors:
                    logger.info(f"🔧 Sample Individual Vector Files:")
                    for i, vector in enumerate(sample_vectors, 1):
                        file_size = vector.get('file_size', 0) / 1024
                        parent_info = f" (from group: {vector.get('parent_group', 'None')})" if vector.get('parent_group', 'None') != 'None' else ""
                        logger.info(f"   {i}. {vector['filename']}: {file_size:.1f} KB{parent_info}")
                    if len(downloaded_svgs) > 5:
                        logger.info(f"   ... and {len(downloaded_svgs) - 5} more individual SVG files")
                
                # Add FIXED SVG info to file metadata
                if '_metadata' not in file_data:
                    file_data['_metadata'] = {}
                
                file_data['_metadata']['fixed_svg_extraction'] = {
                    'total_individual_svgs': total_individual_vectors,
                    'extraction_mode': 'child_based_individual_vectors',
                    'no_composition': True,
                    'no_strips': True,
                    'clean_naming': True,
                    'urlreplacer_compatible': True,
                    'extraction_approach': 'individual_vector_children',
                    'extracted_at': datetime.now().isoformat()
                }
                
                # Add SVG downloads section to JSON
                file_data['_svgDownloads'] = downloaded_svgs
                
                # Create FIXED SVG mapping for quick lookups
                file_data['_svgMapping'] = {
                    svg_data['node_id'].replace(':', '_'): {
                        'filename': svg_data['filename'],
                        'is_individual': True,
                        'component_name': svg_data['component_name'],
                        'parent_group': svg_data.get('parent_group', 'None'),
                        'child_based_extraction': True
                    }
                    for node_id, svg_data in downloaded_svgs.items()
                }
                
                logger.info("FIXED child-based SVG information added to JSON:")
                sample_count = 0
                for node_id, svg_data in downloaded_svgs.items():
                    if sample_count < 3:
                        file_size = svg_data.get('file_size', 0) / 1024
                        logger.info(f"   🎨 {node_id} → {svg_data['filename']} ({file_size:.1f} KB)")
                        sample_count += 1
                    else:
                        break
                if len(downloaded_svgs) > 3:
                    logger.info(f"   ... and {len(downloaded_svgs) - 3} more individual vector files")
            else:
                logger.info("ℹ️ No SVG icons were found or downloaded")
        else:
            logger.info("⭕ Skipping SVG icon extraction as requested")
        
        # Save JSON data with FIXED metadata
        json_filename = f"{document_name}.json"
        json_path = output_dir / json_filename
        
        # Add FIXED metadata to JSON
        file_data['_metadata'] = file_data.get('_metadata', {})
        file_data['_metadata'].update({
            'extracted_at': datetime.now().isoformat(),
            'figma_file_key': file_key,
            'document_name': document_name,
            'total_bitmap_images': len(downloaded_images),
            'total_individual_svg_files': len(downloaded_svgs),
            'remote_folder': args.remote_folder,
            'extraction_mode': extraction_mode,
            'download_images': download_images,
            'extract_svg_icons': extract_svg_icons,
            'extractor_version': 'fixed_v3.0_child_based_extraction',
            'features': ['child_based_extraction', 'individual_vector_files', 'no_composition', 'no_strips', 'clean_naming'],
            'fixes_applied': [
                'child_based_individual_extraction',
                'no_multi_icon_strips', 
                'clean_child_naming',
                'no_composition_logic',
                'urlreplacer_compatible_filenames'
            ]
        })
        
        # Add detailed image information to JSON
        if downloaded_images:
            file_data['_imageDownloads'] = downloaded_images
            file_data['_imageMapping'] = {
                image_ref: img_data['local_path'] 
                for image_ref, img_data in downloaded_images.items()
            }
            
            logger.info("Bitmap image reference mapping added to JSON:")
            for i, image_ref in enumerate(list(downloaded_images.keys())[:3]):
                logger.info(f"   🖼️ {image_ref} → {downloaded_images[image_ref]['filename']}")
            if len(downloaded_images) > 3:
                logger.info(f"   ... and {len(downloaded_images) - 3} more images")
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 FIXED JSON data saved to: {json_path}")
        
        # Upload to DigitalOcean Spaces
        urls_filename = f"{document_name}_urls.json"
        urls_path = output_dir / urls_filename
        
        upload_needed = (downloaded_images or downloaded_svgs) and not args.skip_upload
        
        if upload_needed:
            logger.info("☁️ Uploading FIXED assets to DigitalOcean Spaces...")
            
            total_uploaded = 0
            total_failed = 0
            
            # Upload bitmap images directory if exists
            if downloaded_images:
                images_dir = output_dir / "images"
                if images_dir.exists():
                    logger.info("📤 Uploading bitmap images...")
                    images_upload_result = do_uploader.upload_directory(
                        local_dir_path=str(images_dir),
                        remote_folder=f"{args.remote_folder}/images",
                        file_extensions=['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
                        public_read=True
                    )
                    total_uploaded += images_upload_result['total_uploaded']
                    total_failed += images_upload_result['total_failed']
            
            # Upload FIXED individual SVG files directory if exists
            if downloaded_svgs:
                svg_dir = output_dir / "svg_icons"
                if svg_dir.exists():
                    logger.info("📤 Uploading FIXED individual SVG files...")
                    svg_upload_result = do_uploader.upload_directory(
                        local_dir_path=str(svg_dir),
                        remote_folder=f"{args.remote_folder}/svg_icons",
                        file_extensions=['.svg', '.json'],
                        public_read=True
                    )
                    total_uploaded += svg_upload_result['total_uploaded']
                    total_failed += svg_upload_result['total_failed']
            
            logger.info(f"☁️ Upload completed: {total_uploaded} successful, {total_failed} failed")
            
            # Export URLs to JSON
            do_uploader.export_urls_to_json(args.remote_folder, str(urls_path))
            
            # Also upload the main JSON file
            json_upload_result = do_uploader.upload_file(
                str(json_path),
                f"{args.remote_folder}/{json_filename}",
                public_read=True
            )
            
            if json_upload_result['success']:
                logger.info(f"📄 JSON file uploaded: {json_upload_result['url']}")
        elif not (download_images or extract_svg_icons):
            logger.info("⭕ Skipping upload - no assets were downloaded")
        elif args.skip_upload:
            logger.info("⭕ Skipping upload to DigitalOcean as requested")
        
        # ============================================================
        # FIXED URL REPLACEMENT STEP
        # ============================================================
        if upload_needed and urls_path.exists():
            logger.info("🔗 Starting FIXED URL replacement process...")
            
            try:
                # Initialize URL replacer
                url_replacer = URLReplacer()
                
                # Create FIXED JSON with replaced URLs
                enhanced_json_filename = f"{document_name}_with_urls.json"
                enhanced_json_path = output_dir / enhanced_json_filename
                
                # Use the URL replacer to create the FIXED JSON
                enhanced_json_created = url_replacer.create_url_replaced_json(
                    original_json_path=str(json_path),
                    urls_json_path=str(urls_path),
                    output_path=str(enhanced_json_path),
                    use_cdn=True
                )
                
                logger.info(f"✅ FIXED enhanced JSON created: {enhanced_json_created}")
                
                # Upload the FIXED JSON to DigitalOcean
                if not args.skip_upload:
                    enhanced_upload_result = do_uploader.upload_file(
                        enhanced_json_created,
                        f"{args.remote_folder}/{enhanced_json_filename}",
                        public_read=True
                    )
                    
                    if enhanced_upload_result['success']:
                        logger.info(f"📤 FIXED enhanced JSON uploaded: {enhanced_upload_result['url']}")
                
                # Generate replacement report
                replacement_report = url_replacer.generate_replacement_report()
                report_filename = f"{document_name}_replacement_report.json"
                report_path = output_dir / report_filename
                
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(replacement_report, f, indent=2, ensure_ascii=False)
                
                logger.info(f"📊 FIXED replacement report saved: {report_path}")
                logger.info(f"📄 Replaced {replacement_report['summary']['bitmap_replacements_made']} bitmap image references")
                logger.info(f"📄 Replaced {replacement_report['summary']['svg_replacements_made']} SVG file references")
                logger.info(f"📄 Total replacements: {replacement_report['summary']['total_replacements_made']}")
                
                # Create comprehensive asset mapping
                if downloaded_images or downloaded_svgs:
                    logger.info("📋 Creating comprehensive FIXED asset mapping...")
                    comprehensive_mapping_path = url_replacer.create_comprehensive_mapping(
                        figma_json_path=str(enhanced_json_path),
                        output_dir=output_dir
                    )
                    logger.info(f"📋 Comprehensive FIXED mapping saved: {comprehensive_mapping_path}")
                
            except Exception as e:
                logger.error(f"❌ URL replacement failed: {e}")
                logger.info("Original files are still available without URL replacement")
        else:
            if not upload_needed:
                logger.info("⭕ Skipping URL replacement - no assets were uploaded")
            elif not urls_path.exists():
                logger.warning("⚠️ URLs file not found, skipping URL replacement")
        
        # Print FIXED extraction statistics
        if hasattr(figma, 'get_extraction_stats'):
            stats = figma.get_extraction_stats()
            logger.info("\n📈 FIXED Child-Based Extraction Statistics:")
            logger.info(f"   📡 API Calls: {stats['api_calls']}")
            logger.info(f"   📥 Downloads: {stats['total_downloads']}")
            logger.info(f"   ❌ Errors: {stats['total_errors']}")
            logger.info(f"   🎨 Individual Vectors: {stats['individual_vectors_downloaded']}")
            logger.info(f"   📈 Success Rate: {stats['success_rate']}%")
        
        # Cleanup local files if requested
        if args.cleanup and (downloaded_images or downloaded_svgs):
            logger.info("🧹 Cleaning up local asset files...")
            import shutil
            
            if downloaded_images:
                images_dir = output_dir / "images"
                if images_dir.exists():
                    shutil.rmtree(images_dir)
                    logger.info("🧹 Local bitmap image files cleaned up")
            
            if downloaded_svgs:
                svg_dir = output_dir / "svg_icons"
                if svg_dir.exists():
                    shutil.rmtree(svg_dir)
                    logger.info("🧹 Local SVG files cleaned up")
        
        logger.info("🎉 FIXED child-based extraction process completed successfully!")
        
        # Print FIXED summary of results
        print("\n" + "="*70)
        print("🎉 FIXED CHILD-BASED EXTRACTION COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"📄 Document: {document_name}")
        print(f"🗂️ JSON File: {json_path}")
        
        if downloaded_images:
            print(f"🖼️ Bitmap Images Downloaded: {len(downloaded_images)}")
            print(f"📁 Images Directory: {output_dir / 'images'}")
        
        if downloaded_svgs:
            total_individual_vectors = len(downloaded_svgs)
            
            print(f"🎨 FIXED Individual SVG Files Downloaded: {total_individual_vectors}")
            print(f"   ✅ Each vector child = separate SVG file")
            print(f"   ✅ No multi-icon strips created")
            print(f"   ✅ Clean child-based naming (e.g., 262_48.svg)")
            print(f"📁 SVG Files Directory: {output_dir / 'svg_icons'}")
            
            # Show FIXED SVG results
            print("\n🔧 FIXED Child-Based Extraction Results:")
            sample_vectors = list(downloaded_svgs.values())[:5]
            for i, vector in enumerate(sample_vectors, 1):
                file_size = vector.get('file_size', 0) / 1024
                parent_info = f" (from {vector.get('parent_group', 'None')})" if vector.get('parent_group', 'None') != 'None' else ""
                print(f"   • File {i}: {vector['filename']} - {file_size:.1f} KB{parent_info}")
            
            if len(downloaded_svgs) > 5:
                print(f"   ... and {len(downloaded_svgs) - 5} more individual SVG files")
        
        if upload_needed and not args.skip_upload:
            print(f"\n☁️ Uploaded to: {args.remote_folder}/")
            print(f"🔗 URLs File: {urls_path}")
            
            if downloaded_images:
                print(f"📤 Bitmap Images: {args.remote_folder}/images/")
            if downloaded_svgs:
                print(f"📤 FIXED Individual SVG Files: {args.remote_folder}/svg_icons/")
                print(f"🗺️ FIXED SVG Mapping: {args.remote_folder}/svg_icons/svg_mapping.json")
            
            # Check if FIXED enhanced JSON was created
            enhanced_json_path = output_dir / f"{document_name}_with_urls.json"
            if enhanced_json_path.exists():
                print(f"✨ FIXED Enhanced JSON (with CDN URLs): {enhanced_json_path}")
                
                # Show replacement stats if available
                report_path = output_dir / f"{document_name}_replacement_report.json"
                if report_path.exists():
                    try:
                        with open(report_path, 'r') as f:
                            report = json.load(f)
                        total_replacements = report['summary']['total_replacements_made']
                        print(f"📄 URL Replacements: {total_replacements} figma URLs → CDN URLs")
                    except:
                        pass
        
        if not downloaded_images and not downloaded_svgs:
            print("ℹ️ No assets were found or downloaded")
        
        print(f"\n💡 FIXED Features Applied:")
        print(f"   🔧 Child-based individual extraction (no composition)")
        print(f"   🎨 Each vector child = separate SVG file")
        print(f"   ✂️ No multi-icon strips (clean individual files)")
        print(f"   📝 Child-based naming (262_48.svg not 12_171.svg)")
        print(f"   🔗 URLReplacer compatible filenames")
        print(f"   📊 Enhanced progress tracking")  
        print(f"   ⚡ Rate limiting")
        print(f"   🛡️ Enhanced error handling")
        
        print(f"\n🎯 FIXED Results Summary:")
        if extract_svg_icons and downloaded_svgs:
            # Calculate average file size
            svg_sizes = [s.get('file_size', 0) for s in downloaded_svgs.values()]
            avg_size = sum(svg_sizes) / len(svg_sizes) if svg_sizes else 0
            print(f"   ✅ Average SVG file size: {avg_size/1024:.1f} KB")
            print(f"   ✅ Individual SVG files created: {len(downloaded_svgs)}")
            print(f"   ✅ No strips/composition needed")
            print(f"   ✅ Child-based naming applied")
            if hasattr(preprocessing_stats, 'get') or 'preprocessing_stats' in locals():
                print(f"   ✅ TEXT nodes filtered: {preprocessing_stats.get('text_nodes_filtered', 0)}")
                print(f"   ✅ Shape/mask elements filtered: {preprocessing_stats.get('image_shapes_filtered', 0)}")
        
        print(f"\n💡 Next Steps:")
        print(f"   1. Check your JSON file for the complete Figma structure")
        if downloaded_images:
            print(f"   2. Use '_imageDownloads' section for bitmap image info")
        if downloaded_svgs:
            print(f"   3. Use '_svgDownloads' section for individual SVG file info")
            print(f"   4. 🎨 Each vector child is now a separate SVG file")
            print(f"   5. 🔧 Files use child-based naming (262_48.svg)")
            print(f"   6. 🔗 URLReplacer will map using child IDs")
        if upload_needed and not args.skip_upload:
            enhanced_json_path = output_dir / f"{document_name}_with_urls.json"
            if enhanced_json_path.exists():
                print(f"   7. 🌟 Use the enhanced JSON file for production (CDN URLs ready!)")
        print("="*70)
        
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

def select_pages_and_frames(figma, file_key):
    """Interactive selection of pages and frames"""
    pages_and_frames = figma.list_pages_and_frames(file_key)
    
    if not pages_and_frames:
        print("❌ Could not fetch pages and frames from the file")
        return []
    
    print("\n=== Available Pages and Frames ===")
    for i, item in enumerate(pages_and_frames, 1):
        print(f"{i:2d}. {item['name']} (ID: {item['id']})")
    
    print("\nSelection Options:")
    print("• Enter numbers separated by commas (e.g., 1,3,5)")
    print("• Enter ranges with dashes (e.g., 2-4)")
    print("• Combine both (e.g., 1,3-5,7)")
    print("• Enter 'all' to select everything")
    
    selection = input("\nEnter your selection: ").strip()
    
    if selection.lower() == 'all':
        return [item['id'] for item in pages_and_frames]
    
    selected_indices = []
    
    try:
        parts = selection.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                selected_indices.extend(range(start, end + 1))
            else:
                selected_indices.append(int(part))
        
        selected_nodes = []
        for idx in selected_indices:
            if 1 <= idx <= len(pages_and_frames):
                selected_nodes.append(pages_and_frames[idx - 1]['id'])
            else:
                print(f"⚠️ Warning: Index {idx} is out of range, skipping...")
        
        if selected_nodes:
            print(f"\n✅ Selected {len(selected_nodes)} items:")
            for idx in selected_indices:
                if 1 <= idx <= len(pages_and_frames):
                    item = pages_and_frames[idx - 1]
                    print(f"   • {item['name']}")
        
        return selected_nodes
        
    except ValueError:
        print("❌ Invalid selection format. Please use numbers, ranges, or 'all'")
        return []

if __name__ == "__main__":
    sys.exit(main())