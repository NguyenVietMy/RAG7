"""
GitHub Repository Scraping Service

Simplified GitHub repository scraping that extracts code and documentation,
chunks them with context, and stores in ChromaDB (similar to web scraping).
"""
import os
import logging
import subprocess
import shutil
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path
import re

from dotenv import load_dotenv

# Load environment variables
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH if _ENV_PATH.exists() else None)

logger = logging.getLogger(__name__)

# Code file extensions to process
CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.clj', '.sh',
    '.sql', '.r', '.m', '.mm', '.dart', '.lua', '.pl', '.pm', '.hs', '.elm'
}

# Documentation file extensions
DOC_EXTENSIONS = {
    '.md', '.txt', '.rst', '.adoc', '.org', '.wiki'
}

# Directories to exclude
EXCLUDE_DIRS = {
    'node_modules', '.git', 'venv', 'env', '__pycache__', '.pytest_cache',
    'build', 'dist', '.next', '.nuxt', 'target', 'bin', 'obj', '.idea',
    '.vscode', '.vs', 'coverage', '.coverage', 'htmlcov', '.mypy_cache',
    '.tox', '.cache', 'vendor', 'bower_components', '.gradle', '.mvn'
}

# Files to exclude
EXCLUDE_FILES = {
    'package-lock.json', 'yarn.lock', 'poetry.lock', 'Pipfile.lock',
    'go.sum', 'composer.lock', '.DS_Store', 'Thumbs.db'
}


def clone_repo(repo_url: str, target_dir: str) -> str:
    """
    Clone a GitHub repository to a target directory.
    
    Args:
        repo_url: GitHub repository URL (https://github.com/user/repo or https://github.com/user/repo.git)
        target_dir: Target directory to clone into
    
    Returns:
        Path to cloned repository
    """
    logger.info(f"Cloning repository: {repo_url}")
    
    # Ensure repo_url ends with .git for git clone
    if not repo_url.endswith('.git'):
        repo_url = repo_url + '.git'
    
    # Remove existing directory if it exists
    if os.path.exists(target_dir):
        logger.info(f"Removing existing directory: {target_dir}")
        try:
            def handle_remove_readonly(func, path, exc):
                try:
                    if os.path.exists(path):
                        os.chmod(path, 0o777)
                        func(path)
                except PermissionError:
                    logger.warning(f"Could not remove {path} - file in use, skipping")
                    pass
            shutil.rmtree(target_dir, onerror=handle_remove_readonly)
        except Exception as e:
            logger.warning(f"Could not fully remove {target_dir}: {e}. Proceeding anyway...")
    
    # Clone repository (shallow clone for speed)
    logger.info(f"Running git clone from {repo_url}")
    try:
        subprocess.run(
            ['git', 'clone', '--depth', '1', repo_url, target_dir],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Repository cloned successfully")
        return target_dir
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone repository: {e.stderr}")
        raise


def get_repo_files(repo_path: str, include_patterns: Optional[List[str]] = None, 
                   exclude_patterns: Optional[List[str]] = None,
                   max_file_size_kb: int = 100) -> List[Dict[str, str]]:
    """
    Get all code and documentation files from a repository.
    
    Args:
        repo_path: Path to cloned repository
        include_patterns: Optional list of file patterns to include (e.g., ['*.py', '*.md'])
        exclude_patterns: Optional list of patterns to exclude (e.g., ['test_*.py', '*/tests/*'])
        max_file_size_kb: Maximum file size in KB to process (default: 100KB)
    
    Returns:
        List of dictionaries with 'path', 'content', 'type' (code/doc), 'language'
    """
    repo_path_obj = Path(repo_path)
    files = []
    
    # Convert patterns to regex if provided
    include_regex = None
    if include_patterns:
        include_regex = re.compile('|'.join(
            pattern.replace('*', '.*').replace('.', r'\.') for pattern in include_patterns
        ))
    
    exclude_regex = None
    if exclude_patterns:
        exclude_regex = re.compile('|'.join(
            pattern.replace('*', '.*').replace('.', r'\.') for pattern in exclude_patterns
        ))
    
    for root, dirs, filenames in os.walk(repo_path):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        
        for filename in filenames:
            # Skip excluded files
            if filename in EXCLUDE_FILES or filename.startswith('.'):
                continue
            
            file_path = Path(root) / filename
            relative_path = str(file_path.relative_to(repo_path))
            
            # Check exclude patterns
            if exclude_regex and exclude_regex.search(relative_path):
                continue
            
            # Check include patterns (if provided)
            if include_regex and not include_regex.search(relative_path):
                continue
            
            # Check file extension
            ext = file_path.suffix.lower()
            file_type = None
            language = None
            
            if ext in CODE_EXTENSIONS:
                file_type = 'code'
                language = ext[1:]  # Remove the dot
            elif ext in DOC_EXTENSIONS:
                file_type = 'doc'
                language = 'markdown' if ext == '.md' else 'text'
            else:
                continue  # Skip files we don't recognize
            
            # Check file size
            try:
                file_size_kb = file_path.stat().st_size / 1024
                if file_size_kb > max_file_size_kb:
                    logger.debug(f"Skipping large file: {relative_path} ({file_size_kb:.1f}KB)")
                    continue
            except Exception as e:
                logger.warning(f"Could not check size of {relative_path}: {e}")
                continue
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                files.append({
                    'path': relative_path,
                    'content': content,
                    'type': file_type,
                    'language': language,
                    'size_kb': file_size_kb
                })
            except Exception as e:
                logger.warning(f"Could not read {relative_path}: {e}")
                continue
    
    logger.info(f"   Scanned repository: found {len(files)} files to process")
    if files:
        logger.info(f"   Sample files found:")
        for f in files[:5]:  # Show first 5 files
            logger.info(f"      - {f['path']} ({f['type']}, {f.get('size_kb', 0):.1f}KB)")
        if len(files) > 5:
            logger.info(f"      ... and {len(files) - 5} more files")
    return files


def chunk_code_with_context(content: str, file_path: str, language: str, chunk_size: int = 5000) -> List[Dict[str, str]]:
    """
    Chunk code files with context (file path, language).
    
    Args:
        content: File content
        file_path: Relative file path in repository
        language: Programming language
        chunk_size: Target chunk size in characters
    
    Returns:
        List of dictionaries with 'content', 'chunk_index', 'metadata'
    """
    chunks = []
    
    # For code files, try to chunk at function/class boundaries
    if language == 'py':  # Python
        # Try to split at class/function definitions
        pattern = r'(?=^(?:class|def|async def)\s+\w+)'
        parts = re.split(pattern, content, flags=re.MULTILINE)
    elif language in ['js', 'ts', 'jsx', 'tsx']:  # JavaScript/TypeScript
        # Try to split at function/class definitions
        pattern = r'(?=^(?:class|function|const\s+\w+\s*=\s*(?:async\s+)?\(|export\s+(?:class|function|const)))'
        parts = re.split(pattern, content, flags=re.MULTILINE)
    else:
        # For other languages, just split by lines
        parts = content.split('\n')
    
    current_chunk = []
    current_size = 0
    
    for part in parts:
        part_size = len(part)
        
        # If adding this part would exceed chunk_size, finalize current chunk
        if current_size + part_size > chunk_size and current_chunk:
            chunk_content = '\n'.join(current_chunk)
            if chunk_content.strip():
                chunks.append({
                    'content': chunk_content,
                    'chunk_index': len(chunks),
                    'metadata': {
                        'file_path': file_path,
                        'language': language,
                        'type': 'code'
                    }
                })
            current_chunk = [part]
            current_size = part_size
        else:
            current_chunk.append(part)
            current_size += part_size
    
    # Add remaining content
    if current_chunk:
        chunk_content = '\n'.join(current_chunk)
        if chunk_content.strip():
            chunks.append({
                'content': chunk_content,
                'chunk_index': len(chunks),
                'metadata': {
                    'file_path': file_path,
                    'language': language,
                    'type': 'code'
                }
            })
    
    return chunks


def chunk_doc_with_context(content: str, file_path: str, chunk_size: int = 5000) -> List[Dict[str, str]]:
    """
    Chunk documentation files with context (file path).
    Uses similar logic to web_scraper's smart_chunk_markdown.
    
    Args:
        content: File content
        file_path: Relative file path in repository
        chunk_size: Target chunk size in characters
    
    Returns:
        List of dictionaries with 'content', 'chunk_index', 'metadata'
    """
    from web_scraper import smart_chunk_markdown
    
    # Use the same chunking logic as web scraper
    text_chunks = smart_chunk_markdown(content, chunk_size=chunk_size)
    
    chunks = []
    for i, chunk_text in enumerate(text_chunks):
        chunks.append({
            'content': chunk_text,
            'chunk_index': i,
            'metadata': {
                'file_path': file_path,
                'type': 'doc'
            }
        })
    
    return chunks


async def scrape_github_repo(
    repo_url: str,
    collection_name: str,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    max_file_size_kb: int = 100,
    chunk_size: int = 5000,
    include_readme: bool = True,
    include_code: bool = True
) -> Dict[str, Any]:
    """
    Scrape a GitHub repository and store in ChromaDB.
    
    Args:
        repo_url: GitHub repository URL
        collection_name: ChromaDB collection name to store in
        include_patterns: Optional list of file patterns to include
        exclude_patterns: Optional list of patterns to exclude
        max_file_size_kb: Maximum file size in KB to process
        chunk_size: Chunk size for text splitting
        include_readme: Whether to include README files
        include_code: Whether to include code files
    
    Returns:
        Dictionary with success status, statistics, and any errors
    """
    from chroma_client import get_chroma_client
    from web_scraper import create_embeddings_batch_with_retry
    
    logger.info("=" * 80)
    logger.info(f"🚀 Starting GitHub repository scrape")
    logger.info(f"   Repository: {repo_url}")
    logger.info(f"   Collection: {collection_name}")
    logger.info(f"   Max file size: {max_file_size_kb}KB")
    logger.info(f"   Chunk size: {chunk_size}")
    logger.info(f"   Include README: {include_readme}")
    logger.info(f"   Include code: {include_code}")
    logger.info("=" * 80)
    
    temp_dir = None
    try:
        # Create temporary directory for cloning
        temp_dir = tempfile.mkdtemp(prefix='github_repo_')
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        clone_path = os.path.join(temp_dir, repo_name)
        
        logger.info(f"📦 Step 1/5: Cloning repository '{repo_name}'...")
        # Clone repository
        clone_repo(repo_url, clone_path)
        logger.info(f"✅ Repository cloned successfully to {clone_path}")
        
        # Get files from repository
        logger.info(f"📂 Step 2/5: Scanning repository for files...")
        files = get_repo_files(
            clone_path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_file_size_kb=max_file_size_kb
        )
        
        logger.info(f"   Found {len(files)} files to process")
        
        # Filter based on include_readme and include_code
        if not include_readme:
            files = [f for f in files if not (f['type'] == 'doc' and 'readme' in f['path'].lower())]
        if not include_code:
            files = [f for f in files if f['type'] != 'code']
        
        if not files:
            logger.error("❌ No files found to process after filtering")
            return {
                "success": False,
                "error": "No files found to process"
            }
        
        code_count = sum(1 for f in files if f['type'] == 'code')
        doc_count = sum(1 for f in files if f['type'] == 'doc')
        logger.info(f"✅ File scan complete: {code_count} code files, {doc_count} doc files")
        
        # Process files into chunks
        logger.info(f"✂️  Step 3/5: Processing files into chunks...")
        all_chunks = []
        processed_count = 0
        for file_data in files:
            processed_count += 1
            if processed_count % 10 == 0 or processed_count == 1:
                logger.info(f"   Processing file {processed_count}/{len(files)}: {file_data['path']} ({file_data['type']}, {file_data.get('size_kb', 0):.1f}KB)")
            if file_data['type'] == 'code':
                chunks = chunk_code_with_context(
                    file_data['content'],
                    file_data['path'],
                    file_data['language'],
                    chunk_size=chunk_size
                )
            else:  # doc
                chunks = chunk_doc_with_context(
                    file_data['content'],
                    file_data['path'],
                    chunk_size=chunk_size
                )
            all_chunks.extend(chunks)
            if chunks:
                logger.info(f"      → Created {len(chunks)} chunks from {file_data['path']}")
        
        logger.info(f"✅ Chunking complete: {len(all_chunks)} total chunks created")
        
        if not all_chunks:
            logger.error("❌ No chunks created from files")
            return {
                "success": False,
                "error": "No chunks created from files"
            }
        
        # Generate embeddings
        logger.info(f"🧠 Step 4/5: Generating embeddings for {len(all_chunks)} chunks...")
        texts = [chunk['content'] for chunk in all_chunks]
        logger.info(f"   Calling OpenAI API to generate embeddings...")
        embeddings = create_embeddings_batch_with_retry(texts)
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        
        if len(embeddings) != len(all_chunks):
            logger.warning(f"Embedding count mismatch: {len(embeddings)} vs {len(all_chunks)}")
            # Pad with zero vectors if needed
            while len(embeddings) < len(all_chunks):
                embeddings.append([0.0] * 1536)
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(all_chunks):
            # Create unique ID: repo_name_filepath_chunkindex
            repo_name_safe = repo_name.replace('/', '_').replace('.', '_')
            file_path_safe = chunk['metadata']['file_path'].replace('/', '_').replace('.', '_')
            chunk_id = f"{repo_name_safe}_{file_path_safe}_{chunk['chunk_index']}_{i}"
            ids.append(chunk_id)
            documents.append(chunk['content'])
            
            # Add metadata
            metadata = chunk['metadata'].copy()
            metadata['repo_url'] = repo_url
            metadata['repo_name'] = repo_name
            metadata['chunk_index'] = chunk['chunk_index']
            metadatas.append(metadata)
        
        # Store in ChromaDB
        logger.info(f"💾 Step 5/5: Storing {len(ids)} chunks in ChromaDB collection: {collection_name}")
        chroma_client = get_chroma_client()
        collection = chroma_client.get_or_create_collection(name=collection_name)
        logger.info(f"   Upserting chunks to ChromaDB...")
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        logger.info(f"✅ Successfully stored all chunks in ChromaDB")
        
        # Statistics
        code_files = sum(1 for f in files if f['type'] == 'code')
        doc_files = sum(1 for f in files if f['type'] == 'doc')
        
        logger.info("=" * 80)
        logger.info(f"🎉 Scraping completed successfully!")
        logger.info(f"   Repository: {repo_name}")
        logger.info(f"   Files scraped: {len(files)} ({code_files} code, {doc_files} docs)")
        logger.info(f"   Chunks created: {len(all_chunks)}")
        logger.info(f"   Chunks stored: {len(ids)}")
        logger.info(f"   Collection: {collection_name}")
        logger.info("=" * 80)
        
        return {
            "success": True,
            "repo_url": repo_url,
            "repo_name": repo_name,
            "files_scraped": len(files),
            "code_files": code_files,
            "doc_files": doc_files,
            "chunks_created": len(all_chunks),
            "chunks_stored": len(ids),
            "collection_name": collection_name
        }
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ Error scraping GitHub repository: {e}", exc_info=True)
        logger.error("=" * 80)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            logger.info(f"Cleaning up temporary directory: {temp_dir}")
            try:
                def handle_remove_readonly(func, path, exc):
                    try:
                        if os.path.exists(path):
                            os.chmod(path, 0o777)
                            func(path)
                    except PermissionError:
                        pass
                shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}. Directory may remain at {temp_dir}")

