#!/usr/bin/env python3
"""
Distribute books from public/books/ to citizen houses.

This script creates RESOURCES of type 'books' and places them in BUILDINGS 
of category 'home' owned by citizens. It allows for rapid diffusion of manuscripts.

Usage:
    python distribute_books.py <book_name> <number_of_copies>
    
Example:
    python distribute_books.py "The_Merchant_of_Venice" 50
"""

import sys
import os
import random
import json
from datetime import datetime
from typing import List, Dict, Any
from pyairtable import Table
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Airtable tables
api_key = os.environ.get('AIRTABLE_API_KEY')
base_id = os.environ.get('AIRTABLE_BASE_ID')

if not api_key or not base_id:
    print("Error: Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID environment variables")
    sys.exit(1)

buildings_table = Table(api_key, base_id, 'BUILDINGS')
citizens_table = Table(api_key, base_id, 'CITIZENS')
resources_table = Table(api_key, base_id, 'RESOURCES')

def get_available_books() -> List[str]:
    """Get list of available books from public/books/ directory."""
    books_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'public', 'books')
    if not os.path.exists(books_dir):
        return []
    
    # Get all .md and .txt files in the books directory
    books = []
    for file in os.listdir(books_dir):
        if file.endswith('.md'):
            # Remove .md extension for book name
            book_name = file[:-3]
            books.append(book_name)
        elif file.endswith('.txt'):
            # Remove .txt extension for book name
            book_name = file[:-4]
            books.append(book_name)
    
    return books

def get_citizen_houses() -> List[Dict[str, Any]]:
    """Get all houses (buildings of category 'home') with occupants."""
    print("Fetching citizen houses...")
    
    # Get all buildings of category 'home'
    houses = buildings_table.all(formula="{Category} = 'home'")
    print(f"Found {len(houses)} total homes")
    
    # Filter to only include houses with occupants (residents)
    citizen_houses = []
    for house in houses:
        occupant = house['fields'].get('Occupant')
        if occupant:
            # House has an occupant, include it
            citizen_houses.append(house)
    
    print(f"Found {len(citizen_houses)} occupied citizen houses")
    return citizen_houses

def get_books_in_building(building_id: str) -> List[str]:
    """Get list of book titles already in a building."""
    # Get all resources of type 'books' in this building
    formula = f"AND({{Type}} = 'books', {{Asset}} = '{building_id}', {{AssetType}} = 'building')"
    books = resources_table.all(formula=formula)
    
    book_titles = []
    for book in books:
        attributes = book['fields'].get('Attributes', {})
        if isinstance(attributes, dict) and 'title' in attributes:
            book_titles.append(attributes['title'])
        elif isinstance(attributes, str):
            # Try to parse as JSON
            try:
                import json
                attrs = json.loads(attributes)
                if 'title' in attrs:
                    book_titles.append(attrs['title'])
            except:
                pass
    
    return book_titles

def create_book_resource(book_name: str, building_id: str, owner_id: str) -> Dict[str, Any]:
    """Create a book resource with proper attributes."""
    # Check which file extension exists
    books_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'public', 'books')
    md_path = os.path.join(books_dir, f'{book_name}.md')
    txt_path = os.path.join(books_dir, f'{book_name}.txt')
    
    if os.path.exists(md_path):
        content_path = f'public/books/{book_name}.md'
    elif os.path.exists(txt_path):
        content_path = f'public/books/{book_name}.txt'
    else:
        # Default to .md if neither exists (shouldn't happen if used correctly)
        content_path = f'public/books/{book_name}.md'
    
    # Create the book resource
    resource_data = {
        'ResourceId': f'resource-book-{datetime.now().strftime("%Y%m%d%H%M%S")}-{random.randint(1000, 9999)}',
        'Type': 'books',
        'Name': 'Books',  # Generic name for the resource type
        'Asset': building_id,  # The building where the book is stored
        'AssetType': 'building',
        'Owner': owner_id,  # The citizen who owns the book
        'Count': 1.0,  # Number of books (as float)
        'Attributes': json.dumps({
            'title': book_name.replace('_', ' '),  # Convert underscores to spaces for display
            'content_path': content_path,
            'distributed_at': datetime.now().isoformat()
        }),
        'CreatedAt': datetime.now().isoformat()
    }
    
    return resources_table.create(resource_data)

def distribute_books(book_name: str, num_copies: int):
    """Distribute specified number of book copies to citizen houses."""
    # Verify the book exists
    available_books = get_available_books()
    if book_name not in available_books:
        print(f"Error: Book '{book_name}' not found in public/books/")
        print(f"Available books: {', '.join(available_books)}")
        return
    
    # Get all citizen houses
    houses = get_citizen_houses()
    if not houses:
        print("No citizen houses found!")
        return
    
    # Track distribution
    distributed = 0
    skipped_houses = []
    
    # Shuffle houses for random distribution
    random.shuffle(houses)
    
    for house in houses:
        if distributed >= num_copies:
            break
            
        house_id = house['id']
        house_name = house['fields'].get('Name', 'Unknown')
        occupant = house['fields'].get('Occupant')
        
        if not occupant:
            # Skip houses without occupants
            continue
            
        owner_id = occupant  # The occupant owns the book
        
        # Check if this house already has this book
        existing_books = get_books_in_building(house_id)
        book_title = book_name.replace('_', ' ')
        
        if book_title in existing_books:
            skipped_houses.append(house_name)
            continue
        
        # Create the book resource
        try:
            book = create_book_resource(book_name, house_id, owner_id)
            distributed += 1
            print(f"[{distributed}/{num_copies}] Placed '{book_title}' in {house_name}")
        except Exception as e:
            print(f"Error placing book in {house_name}: {e}")
    
    # Summary
    print(f"\nDistribution complete!")
    print(f"Books distributed: {distributed}/{num_copies}")
    if skipped_houses:
        print(f"Skipped {len(skipped_houses)} houses that already had this book")
    
    if distributed < num_copies:
        print(f"\nNote: Only {distributed} copies were distributed because:")
        if len(houses) <= distributed + len(skipped_houses):
            print("- Not enough houses available")
        else:
            print("- Some houses already had this book")

def main():
    if len(sys.argv) != 3:
        print("Usage: python distribute_books.py <book_name> <number_of_copies>")
        print("\nExample: python distribute_books.py The_Merchant_of_Venice 50")
        print("\nAvailable books:")
        books = get_available_books()
        for book in books:
            print(f"  - {book}")
        sys.exit(1)
    
    book_name = sys.argv[1]
    try:
        num_copies = int(sys.argv[2])
        if num_copies <= 0:
            raise ValueError("Number must be positive")
    except ValueError:
        print("Error: number_of_copies must be a positive integer")
        sys.exit(1)
    
    print(f"Distributing {num_copies} copies of '{book_name}'...")
    distribute_books(book_name, num_copies)

if __name__ == "__main__":
    main()