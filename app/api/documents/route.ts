import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DOCUMENTS_BASE_PATH = path.join(process.cwd(), 'public');
const ALLOWED_DIRECTORIES = ['books', 'papers'];
const ALLOWED_EXTENSIONS = ['.md', '.pdf', '.tex'];

interface DocumentInfo {
  name: string;
  path: string;
  type: 'markdown' | 'pdf' | 'tex';
  size: number;
  modified: string;
  category: 'books' | 'papers';
}

function getFileType(extension: string): 'markdown' | 'pdf' | 'tex' {
  switch (extension.toLowerCase()) {
    case '.md':
      return 'markdown';
    case '.pdf':
      return 'pdf';
    case '.tex':
      return 'tex';
    default:
      return 'markdown';
  }
}

function scanDocuments(): DocumentInfo[] {
  const documents: DocumentInfo[] = [];

  for (const category of ALLOWED_DIRECTORIES) {
    const categoryPath = path.join(DOCUMENTS_BASE_PATH, category);
    
    if (!fs.existsSync(categoryPath)) {
      continue;
    }

    try {
      const files = fs.readdirSync(categoryPath);
      
      for (const file of files) {
        const filePath = path.join(categoryPath, file);
        const extension = path.extname(file);
        
        if (!ALLOWED_EXTENSIONS.includes(extension.toLowerCase())) {
          continue;
        }

        const stats = fs.statSync(filePath);
        
        if (stats.isFile()) {
          documents.push({
            name: path.basename(file, extension),
            path: `${category}/${file}`,
            type: getFileType(extension),
            size: stats.size,
            modified: stats.mtime.toISOString(),
            category: category as 'books' | 'papers'
          });
        }
      }
    } catch (error) {
      console.error(`Error scanning ${category} directory:`, error);
    }
  }

  return documents;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const documentPath = searchParams.get('path');
    const action = searchParams.get('action') || 'list';

    // List all documents
    if (action === 'list' || !documentPath) {
      const documents = scanDocuments();
      
      return NextResponse.json({
        success: true,
        documents,
        total: documents.length
      });
    }

    // Serve specific document
    if (action === 'serve' && documentPath) {
      // Validate path to prevent directory traversal
      const normalizedPath = path.normalize(documentPath);
      if (normalizedPath.includes('..') || normalizedPath.startsWith('/')) {
        return NextResponse.json(
          { success: false, error: 'Invalid document path' },
          { status: 400 }
        );
      }

      const [category, filename] = normalizedPath.split('/');
      
      if (!ALLOWED_DIRECTORIES.includes(category)) {
        return NextResponse.json(
          { success: false, error: 'Invalid document category' },
          { status: 400 }
        );
      }

      const fullPath = path.join(DOCUMENTS_BASE_PATH, normalizedPath);
      
      if (!fs.existsSync(fullPath)) {
        return NextResponse.json(
          { success: false, error: 'Document not found' },
          { status: 404 }
        );
      }

      const extension = path.extname(filename).toLowerCase();
      
      if (!ALLOWED_EXTENSIONS.includes(extension)) {
        return NextResponse.json(
          { success: false, error: 'File type not allowed' },
          { status: 400 }
        );
      }

      try {
        if (extension === '.pdf') {
          // Serve PDF files as binary
          const fileBuffer = fs.readFileSync(fullPath);
          
          return new NextResponse(fileBuffer, {
            headers: {
              'Content-Type': 'application/pdf',
              'Content-Disposition': `inline; filename="${filename}"`,
              'Cache-Control': 'public, max-age=3600'
            }
          });
        } else {
          // Serve text files (markdown, tex) as UTF-8
          const fileContent = fs.readFileSync(fullPath, 'utf-8');
          
          const contentType = extension === '.md' ? 'text/markdown' : 'text/plain';
          
          return new NextResponse(fileContent, {
            headers: {
              'Content-Type': `${contentType}; charset=utf-8`,
              'Content-Disposition': `inline; filename="${filename}"`,
              'Cache-Control': 'public, max-age=3600'
            }
          });
        }
      } catch (error) {
        console.error('Error reading file:', error);
        return NextResponse.json(
          { success: false, error: 'Error reading document' },
          { status: 500 }
        );
      }
    }

    return NextResponse.json(
      { success: false, error: 'Invalid action' },
      { status: 400 }
    );

  } catch (error) {
    console.error('Documents API error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}