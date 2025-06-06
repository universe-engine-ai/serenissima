# La Serenissima Project Map Structure

This document provides an overview of the `map.json` file structure, which serves as a navigation guide for the La Serenissima codebase.

## Top-Level Structure

The `map.json` file contains the following top-level keys:

- `project_name`: The name of the project ("La Serenissima")
- `description`: A brief description of the project and the purpose of the map
- `last_updated`: The date when the map was last updated
- `structure`: The main object containing the codebase structure

## Structure Organization

The `structure` object is organized into several main sections:

1. **Frontend App Types** (`frontend_app_types`)
   - TypeScript type definitions for frontend components

2. **Frontend Components** (`frontend_components`)
   - React components organized by functionality
   - Includes specialized UI components, articles, and map-related components

3. **Backend** (`backend`)
   - Server-side logic, game engine scripts, and AI behaviors
   - Includes documentation, core engine scripts, and AI decision-making modules

4. **Libraries and Utilities** (`libraries_and_utilities`)
   - Shared services, utilities, and state management

5. **AI System Core Files** (`ai_system_core_files`)
   - Core operational parameters and persona definitions for AI citizens

6. **AI Dynamic Data Storage** (`ai_dynamic_data_storage`)
   - Persistent storage for AI memories and knowledge

7. **AI Strategic Planning Storage** (`ai_strategic_planning_storage`)
   - Storage for AI strategic plans and decision trees

## File Structure Format

Each section in the structure follows this format:

```json
{
  "path": "path/to/directory/",
  "description": "Description of the directory's purpose",
  "important_files": [
    {
      "path": "path/to/file.ext",
      "role": "Description of the file's purpose"
    }
  ],
  "sub_directories": {
    // Optional nested directories
  }
}
```

This structured approach makes it easier to navigate the codebase and understand the relationships between different components of the La Serenissima project.
