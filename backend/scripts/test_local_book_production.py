#!/usr/bin/env python3
"""
Test script to verify the local book production system works correctly.
This script tests the book selection functions without actually creating activities.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from pathlib import Path
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

# Import the functions we want to test
from backend.engine.activity_processors.production_processor import _get_local_books, _select_book_randomly

def test_local_book_discovery():
    """Test that we can discover books in the local filesystem."""
    print("\n=== Testing Local Book Discovery ===")
    
    books = _get_local_books(log)
    
    print(f"\nFound {len(books)} books in total")
    
    # Group books by author
    books_by_author = {}
    for book in books:
        author = book['author']
        if author not in books_by_author:
            books_by_author[author] = []
        books_by_author[author].append(book)
    
    # Display books organized by author
    for author, author_books in sorted(books_by_author.items()):
        print(f"\n{author}:")
        for book in author_books:
            print(f"  - {book['title']} ({book['path']})")
    
    return books

def test_random_book_selection():
    """Test random book selection."""
    print("\n=== Testing Random Book Selection ===")
    
    # Select a few random books
    for i in range(5):
        book = _select_book_randomly(log)
        if book:
            print(f"\nSelection {i+1}:")
            print(f"  Title: {book['title']}")
            print(f"  Author: {book['author']}")
            print(f"  Path: {book['path']}")
            
            # Show what the attributes JSON would look like
            attributes = {
                "title": book["title"],
                "author_username": book["author"],
                "local_path": book["path"]
            }
            print(f"  Attributes JSON: {json.dumps(attributes, indent=2)}")
        else:
            print(f"\nSelection {i+1}: No book selected (error)")

def test_content_reading():
    """Test that we can read content from selected books."""
    print("\n=== Testing Book Content Reading ===")
    
    # Import the local book content reader
    from backend.engine.activity_processors.read_book_processor import _get_local_book_content
    
    # Get a sample book
    book = _select_book_randomly(log)
    if book:
        print(f"\nTesting content read for: {book['title']}")
        
        # Try to read its content
        content_path = f"public/books/{book['path']}"
        content = _get_local_book_content(content_path)
        
        if content:
            print(f"  Successfully read {len(content)} characters")
            print(f"  First 200 characters: {content[:200]}...")
        else:
            print(f"  Failed to read content from {content_path}")

if __name__ == "__main__":
    # Run tests
    books = test_local_book_discovery()
    
    if books:
        test_random_book_selection()
        test_content_reading()
    else:
        print("\nNo books found. Please ensure books exist in public/books/")