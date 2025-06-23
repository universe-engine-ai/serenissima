#!/usr/bin/env python3
"""
Distribute books from public/books/ to citizen houses.

This script creates RESOURCES of type 'books' and places them in BUILDINGS 
of category 'house' owned by citizens. It allows for rapid diffusion of manuscripts.

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

# Add the parent directory to the path so we can import the backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyairtable import Table
from app.airtable_config import (
    airtable, buildings_table, citizens_table, resources_table
)

def get_available_books() -> List[str]:
    """Get list of available books from public/books/ directory."""
    books_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'public', 'books')
    if not os.path.exists(books_dir):
        return []
    
    # Get all .md files in the books directory
    books = []
    for file in os.listdir(books_dir):
        if file.endswith('.md'):
            # Remove .md extension for book name
            book_name = file[:-3]
            books.append(book_name)
    
    return books

def get_citizen_houses() -> List[Dict[str, Any]]:
    """Get all houses (buildings of category 'house') with their owners."""
    print("Fetching citizen houses...")
    
    # Get all buildings of category 'house'
    houses = buildings_table.all(formula="AND({Category} = 'house', {Owner} != '')")
    
    # Filter to only include houses owned by citizens (not guilds or other entities)
    citizen_houses = []
    for house in houses:
        owner = house['fields'].get('Owner', [])
        if owner and len(owner) > 0:
            # Check if owner is a citizen (has IsAI field)
            try:
                citizen = citizens_table.get(owner[0])
                if 'IsAI' in citizen['fields']:
                    citizen_houses.append(house)
            except:
                # Skip if we can't verify it's a citizen
                pass
    
    print(f"Found {len(citizen_houses)} citizen houses")
    return citizen_houses

def get_books_in_building(building_id: str) -> List[str]:
    """Get list of book titles already in a building."""
    # Get all resources of type 'books' in this building
    formula = f"AND({{Type}} = 'books', {{Building}} = '{building_id}')"
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
    # Create the book resource
    resource_data = {
        'Type': 'books',
        'Quantity': 1,
        'Building': [building_id],
        'Owner': [owner_id],
        'Attributes': json.dumps({
            'title': book_name.replace('_', ' '),  # Convert underscores to spaces for display
            'content_path': f'public/books/{book_name}.md',
            'distributed_at': datetime.now().isoformat()
        })
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
        owner_id = house['fields']['Owner'][0]
        
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