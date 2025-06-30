#!/usr/bin/env python3
"""
Distribute books from public/books/ to citizen houses and scientific buildings.

This script creates RESOURCES of type 'books' and places them in BUILDINGS 
of category 'home' owned by citizens. It also ensures all science books are
present in all house_of_natural_sciences buildings.

Usage:
    python distribute_books.py <book_name> <number_of_copies>
    python distribute_books.py --sync-science-houses
    
Example:
    python distribute_books.py "The_Merchant_of_Venice" 50
    python distribute_books.py --sync-science-houses
"""

import sys
import os
import random
import json
from datetime import datetime
from typing import List, Dict, Any
from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Airtable tables
api_key = os.environ.get('AIRTABLE_API_KEY')
base_id = os.environ.get('AIRTABLE_BASE_ID')

if not api_key or not base_id:
    print("Error: Missing AIRTABLE_API_KEY or AIRTABLE_BASE_ID environment variables")
    sys.exit(1)

# Use the new API format
api = Api(api_key)
base = api.base(base_id)
buildings_table = base.table('BUILDINGS')
citizens_table = base.table('CITIZENS')
resources_table = base.table('RESOURCES')

def get_available_books(subdirectory: str = '') -> List[str]:
    """Get list of available books from public/books/ directory or subdirectory."""
    books_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'public', 'books')
    if subdirectory:
        books_dir = os.path.join(books_dir, subdirectory)
    
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

def get_all_available_books() -> Dict[str, str]:
    """Get all available books from public/books/ including subdirectories.
    Returns a dict with book_name -> relative_path mapping."""
    books_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'public', 'books')
    
    if not os.path.exists(books_dir):
        return {}
    
    books = {}
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(books_dir):
        # Get relative path from books_dir
        rel_path = os.path.relpath(root, books_dir)
        if rel_path == '.':
            rel_path = ''
        
        for file in files:
            if file.endswith('.md') or file.endswith('.txt'):
                # Remove extension for book name
                if file.endswith('.md'):
                    book_name = file[:-3]
                else:
                    book_name = file[:-4]
                
                # Store with relative path
                if rel_path:
                    books[book_name] = rel_path
                else:
                    books[book_name] = ''
    
    return books

def get_science_books() -> List[str]:
    """Get list of all books in public/books/science/ directory."""
    return get_available_books('science')

def get_science_houses() -> List[Dict[str, Any]]:
    """Get all house_of_natural_sciences buildings."""
    print("Fetching houses of natural sciences...")
    
    # Get all buildings of type 'house_of_natural_sciences'
    science_houses = buildings_table.all(formula="{Type} = 'house_of_natural_sciences'")
    print(f"Found {len(science_houses)} houses of natural sciences")
    
    return science_houses

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
    """Get list of book titles already in a building (using BuildingId)."""
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

def create_book_resource(book_name: str, asset_id: str, owner_id: str, asset_type: str = 'building', is_science_book: bool = False, subdirectory: str = '') -> Dict[str, Any]:
    """Create a book resource with proper attributes.
    
    Args:
        book_name: Name of the book file (without extension)
        asset_id: Either building_id or citizen username depending on asset_type
        owner_id: The citizen who owns the book
        asset_type: 'building' or 'citizen' - determines where the book is stored
        is_science_book: Whether this is a science book
        subdirectory: Subdirectory in public/books/ where the book is located
    """
    # Check which file extension exists
    books_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'public', 'books')
    
    if is_science_book and not subdirectory:
        subdirectory = 'science'
    
    if subdirectory:
        md_path = os.path.join(books_dir, subdirectory, f'{book_name}.md')
        txt_path = os.path.join(books_dir, subdirectory, f'{book_name}.txt')
        
        if os.path.exists(md_path):
            content_path = f'public/books/{subdirectory}/{book_name}.md'
        elif os.path.exists(txt_path):
            content_path = f'public/books/{subdirectory}/{book_name}.txt'
        else:
            content_path = f'public/books/{subdirectory}/{book_name}.md'
    else:
        md_path = os.path.join(books_dir, f'{book_name}.md')
        txt_path = os.path.join(books_dir, f'{book_name}.txt')
        
        if os.path.exists(md_path):
            content_path = f'public/books/{book_name}.md'
        elif os.path.exists(txt_path):
            content_path = f'public/books/{book_name}.txt'
        else:
            content_path = f'public/books/{book_name}.md'
    
    # Create the book resource
    resource_data = {
        'ResourceId': f'resource-book-{datetime.now().strftime("%Y%m%d%H%M%S")}-{random.randint(1000, 9999)}',
        'Type': 'books',
        'Name': 'Books',  # Generic name for the resource type
        'Asset': asset_id,  # Either building ID or citizen username
        'AssetType': asset_type,  # 'building' or 'citizen'
        'Owner': owner_id,  # The citizen who owns the book
        'Count': 1.0,  # Number of books (as float)
        'Attributes': json.dumps({
            'title': book_name.replace('_', ' ').replace('-', ' '),  # Convert underscores and hyphens to spaces for display
            'content_path': content_path,
            'distributed_at': datetime.now().isoformat(),
            'is_science_book': is_science_book
        }),
        'CreatedAt': datetime.now().isoformat()
    }
    
    return resources_table.create(resource_data)

def sync_science_houses():
    """Ensure all science books are present in all house_of_natural_sciences buildings."""
    science_books = get_science_books()
    science_houses = get_science_houses()
    
    if not science_books:
        print("No science books found in public/books/science/")
        return
    
    if not science_houses:
        print("No houses of natural sciences found!")
        return
    
    print(f"\nFound {len(science_books)} science books to distribute to {len(science_houses)} houses of natural sciences")
    
    total_added = 0
    
    for house in science_houses:
        house_id = house['id']
        house_name = house['fields'].get('Name', 'Unknown Science House')
        building_id = house['fields'].get('BuildingId', house_id)
        
        # Get the owner/manager of the science house
        owner = house['fields'].get('Owner')
        run_by = house['fields'].get('RunBy')
        owner_id = run_by or owner or 'ConsiglioDeiDieci'  # Default to ConsiglioDeiDieci if no owner
        
        print(f"\nChecking {house_name} (managed by {owner_id})...")
        
        # Get existing books in this building
        existing_books = get_books_in_building(building_id)  # Use BuildingId here
        existing_titles = [title.lower() for title in existing_books]
        
        # Check each science book
        books_added = 0
        for book_name in science_books:
            book_title = book_name.replace('_', ' ').replace('-', ' ')
            
            if book_title.lower() not in existing_titles:
                # Add this book
                try:
                    book = create_book_resource(book_name, building_id, owner_id, asset_type='building', is_science_book=True)  # Use BuildingId here
                    books_added += 1
                    total_added += 1
                    print(f"  + Added '{book_title}'")
                except Exception as e:
                    print(f"  ! Error adding '{book_title}': {e}")
            else:
                print(f"  ✓ Already has '{book_title}'")
        
        if books_added == 0:
            print(f"  All science books already present.")
        else:
            print(f"  Added {books_added} new books.")
    
    print(f"\nSync complete! Added {total_added} books total across all houses of natural sciences.")

def distribute_books(book_name: str, num_copies: int):
    """Distribute specified number of book copies to citizen houses."""
    # Verify the book exists
    all_books = get_all_available_books()
    if book_name not in all_books:
        print(f"Error: Book '{book_name}' not found in public/books/")
        print(f"Available books:")
        # Group by subdirectory
        books_by_dir = {}
        for book, subdir in all_books.items():
            if subdir not in books_by_dir:
                books_by_dir[subdir] = []
            books_by_dir[subdir].append(book)
        
        # Print grouped
        for subdir, books in sorted(books_by_dir.items()):
            if subdir:
                print(f"\n  In {subdir}/:")
            else:
                print(f"\n  In main directory:")
            for book in sorted(books):
                print(f"    - {book}")
        return
    
    subdirectory = all_books[book_name]
    
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
        building_id = house['fields'].get('BuildingId', house_id)  # Get BuildingId, fallback to record ID
        occupant = house['fields'].get('Occupant')
        
        if not occupant:
            # Skip houses without occupants
            continue
            
        owner_id = occupant  # The occupant owns the book
        
        # Check if this house already has this book
        existing_books = get_books_in_building(building_id)  # Use BuildingId here
        book_title = book_name.replace('_', ' ')
        
        if book_title in existing_books:
            skipped_houses.append(house_name)
            continue
        
        # Create the book resource
        try:
            book = create_book_resource(book_name, building_id, owner_id, asset_type='building', subdirectory=subdirectory)  # Use BuildingId here
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

def get_books_on_citizen(username: str) -> List[str]:
    """Get list of book titles already owned by a citizen (using username)."""
    # Get all resources of type 'books' owned by this citizen
    formula = f"AND({{Type}} = 'books', {{Asset}} = '{username}', {{AssetType}} = 'citizen')"
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

def distribute_books_to_citizens(book_name: str, citizen_usernames: List[str]):
    """Distribute a book to specific citizens by username."""
    # Verify the book exists
    all_books = get_all_available_books()
    if book_name not in all_books:
        print(f"Error: Book '{book_name}' not found in public/books/")
        return
    
    subdirectory = all_books[book_name]
    
    # Track distribution
    distributed = 0
    skipped_citizens = []
    
    for username in citizen_usernames:
        # Check if citizen exists
        citizen_records = citizens_table.all(formula=f"{{Username}} = '{username}'")
        if not citizen_records:
            print(f"Warning: Citizen '{username}' not found, skipping...")
            continue
            
        citizen = citizen_records[0]
        citizen_id = citizen['fields'].get('CitizenId', username)
        
        # Check if this citizen already has this book
        existing_books = get_books_on_citizen(username)
        book_title = book_name.replace('_', ' ').replace('-', ' ')
        
        if book_title in existing_books:
            skipped_citizens.append(username)
            print(f"  ✓ {username} already has '{book_title}'")
            continue
        
        # Create the book resource
        try:
            book = create_book_resource(
                book_name, 
                username,  # Asset is the username
                username,  # Owner is also the username
                asset_type='citizen',  # AssetType is 'citizen'
                subdirectory=subdirectory
            )
            distributed += 1
            print(f"  + Gave '{book_title}' to {username}")
        except Exception as e:
            print(f"  ! Error giving book to {username}: {e}")
    
    # Summary
    print(f"\nDistribution complete!")
    print(f"Books distributed: {distributed}/{len(citizen_usernames)}")
    if skipped_citizens:
        print(f"Skipped {len(skipped_citizens)} citizens who already had this book")

def main():
    if len(sys.argv) < 2:
        print("Usage: python distribute_books.py <book_name> <number_of_copies>")
        print("       python distribute_books.py <book_name> --to-citizens <username1> <username2> ...")
        print("       python distribute_books.py --sync-science-houses")
        print("\nExample: python distribute_books.py The_Merchant_of_Venice 50")
        print("         python distribute_books.py The_Whispered_Prophecy --to-citizens canon_philosopher divine_economist scholar_priest")
        print("         python distribute_books.py chronicles-of-change 1")
        print("         python distribute_books.py --sync-science-houses")
        
        all_books = get_all_available_books()
        print("\nAvailable books:")
        # Group by subdirectory
        books_by_dir = {}
        for book, subdir in all_books.items():
            if subdir not in books_by_dir:
                books_by_dir[subdir] = []
            books_by_dir[subdir].append(book)
        
        # Print grouped
        for subdir, books in sorted(books_by_dir.items()):
            if subdir:
                print(f"\n  In {subdir}/:")
            else:
                print(f"\n  In main directory:")
            for book in sorted(books):
                print(f"    - {book}")
        sys.exit(1)
    
    # Check for sync science houses command
    if sys.argv[1] == '--sync-science-houses':
        sync_science_houses()
        return
    
    # Check for citizen distribution
    if len(sys.argv) >= 4 and sys.argv[2] == '--to-citizens':
        book_name = sys.argv[1]
        citizen_usernames = sys.argv[3:]
        print(f"Distributing '{book_name}' to {len(citizen_usernames)} specific citizens...")
        distribute_books_to_citizens(book_name, citizen_usernames)
        return
    
    # Normal book distribution
    if len(sys.argv) != 3:
        print("Error: Please provide both book name and number of copies")
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